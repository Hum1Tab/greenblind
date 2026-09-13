"""Read Git objects, remove one change, observe a command. No working-tree edits."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import difflib
import fnmatch
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import tempfile
import time

MAX_BYTES = 256 * 1024 * 1024


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def revision(repo: Path, ref: str) -> str:
    return git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()


def safe_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or "\\" in name or ":" in name
            or any(p == ".." or p.casefold() == ".git" for p in path.parts)):
        raise ValueError(f"Unsupported repository path: {name!r}")
    if os.name == "nt":
        reserved = {"con", "prn", "aux", "nul", *[f"com{i}" for i in range(1, 10)], *[f"lpt{i}" for i in range(1, 10)]}
        if any(p.endswith((".", " ")) or p.split('.')[0].casefold() in reserved
               or any(c in p for c in '<>"|?*') for p in path.parts):
            raise ValueError(f"Unsupported Windows path: {name!r}")
    return path


def snapshot(repo: Path, commit: str) -> dict[str, tuple[bytes, int]]:
    """Read exact blobs, including export-ignored files, without checkout filters."""
    entries = []
    seen = set()
    for record in git(repo, "ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if not record:
            continue
        meta, raw_name = record.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        name = raw_name.decode("utf-8")
        safe_path(name)
        key = name.casefold() if os.name == "nt" else name
        if key in seen:
            raise ValueError(f"Case-colliding path: {name}")
        seen.add(key)
        if kind != "blob" or mode not in ("100644", "100755"):
            raise ValueError(f"Symlinks/submodules are not supported yet: {name}")
        entries.append((name, mode, oid))
    # Stream one object at a time so large repositories fail before buffering them.
    files = {}
    total = 0
    with subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
        try:
            for name, mode, oid in entries:
                proc.stdin.write((oid + "\n").encode())
                proc.stdin.flush()
                header = proc.stdout.readline().decode().split()
                if len(header) != 3 or header[1] != "blob":
                    raise ValueError("Git returned an invalid blob header")
                size = int(header[2])
                total += size
                if total > MAX_BYTES:
                    raise ValueError("Snapshot exceeds the 256 MiB limit")
                data = proc.stdout.read(size)
                if len(data) != size or proc.stdout.read(1) != b"\n":
                    raise ValueError("Git returned a truncated blob")
                files[name] = (data, int(mode, 8) & 0o777)
        finally:
            proc.stdin.close()
            proc.terminate() if proc.poll() is None else None
    return files


@dataclass
class Probe:
    id: str
    file: str
    start: int
    end: int
    before: str
    after: str
    replacement: bytes | None

    def public(self):
        return {k: v for k, v in asdict(self).items() if k != "replacement"}


def plan(base, head, includes, excludes):
    probes, skipped = [], []
    for name in sorted(base.keys() | head.keys()):
        old, new = base.get(name), head.get(name)
        if old == new:
            continue
        if not any(fnmatch.fnmatchcase(name, p) for p in includes):
            continue
        if any(fnmatch.fnmatchcase(name, p) for p in excludes):
            skipped.append({"file": name, "reason": "excluded"})
            continue
        a, b = old[0] if old else b"", new[0] if new else b""
        try:
            if b"\0" in a or b"\0" in b:
                raise UnicodeError()
            a.decode("utf-8"), b.decode("utf-8")
        except UnicodeError:
            skipped.append({"file": name, "reason": "binary or non-UTF-8"})
            continue
        if old and new and old[1] != new[1]:
            skipped.append({"file": name, "reason": "file mode changed"})
            continue
        aa, bb = a.splitlines(keepends=True), b.splitlines(keepends=True)
        operations = ([('replace', 0, len(aa), 0, len(bb))] if old is None or new is None
                      else difflib.SequenceMatcher(None, aa, bb, autojunk=False).get_opcodes())
        for tag, i, j, k, l in operations:
            if tag == "equal":
                continue
            replacement = None if old is None else b"".join(bb[:k] + aa[i:j] + bb[l:])
            identity = hashlib.sha256(name.encode() + b"\0" + str((i,j,k,l)).encode() + a + b).hexdigest()[:12]
            probes.append(Probe(identity, name, k + 1, max(k + 1, l),
                                b"".join(aa[i:j]).decode(), b"".join(bb[k:l]).decode(), replacement))
    return probes, skipped


def materialize(files, target: Path):
    for name, (data, mode) in files.items():
        path = target.joinpath(*safe_path(name).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode)


def run_command(command, cwd, timeout):
    started = time.monotonic()
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Logs go to disk rather than an unbounded PIPE. Only an opt-in tail is exported.
    with tempfile.TemporaryFile() as log:
        try:
            proc = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=os.name != "nt")
        except OSError as exc:
            return {"status": "error", "exit_code": None, "seconds": 0, "log": str(exc)}
        status = "completed"
        try:
            proc.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            status = "timeout"
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
            else:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            proc.kill() if proc.poll() is None else None
            proc.wait()
            if isinstance(exc, KeyboardInterrupt):
                raise
        log.seek(0, 2)
        log.seek(max(0, log.tell() - 16000))
        output = log.read().decode("utf-8", "replace")
    return {"status": status, "exit_code": proc.returncode,
            "seconds": round(time.monotonic() - started, 3), "log": output}


def classify(runs):
    if any(r["status"] != "completed" for r in runs):
        return "inconclusive"
    codes = {r["exit_code"] for r in runs}
    if len(codes) != 1:
        return "unstable"
    return "unnoticed" if codes == {0} else "rejected"


def prepare(repo, base_ref, head_ref, includes, excludes, repeats=2, timeout=60, limit=30):
    """Build the same immutable plan for preview and execution."""
    if repeats < 2 or not math.isfinite(timeout) or timeout <= 0 or limit < 1:
        raise ValueError("Require repeats >= 2, timeout > 0, and limit >= 1")
    base_sha, head_sha = revision(repo, base_ref), revision(repo, head_ref)
    base, head = snapshot(repo, base_sha), snapshot(repo, head_sha)
    probes, skipped = plan(base, head, includes, excludes)
    report = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
              "base": base_sha, "head": head_sha,
              "includes": includes, "excludes": excludes,
              "repeats": repeats, "timeout": timeout, "total_probes": len(probes),
              "omitted_probes": max(0, len(probes) - limit), "skipped": skipped,
              "baseline": [], "final_baseline": [], "results": [], "status": "complete"}
    return report, base, head, probes


def preview(repo, base_ref, head_ref, includes, excludes, repeats=2, timeout=60, limit=30):
    report, _, _, probes = prepare(repo, base_ref, head_ref, includes, excludes, repeats, timeout, limit)
    count = min(len(probes), limit)
    executions = repeats * (count + 1) + 1 if count else 0
    return {"schema_version": 1, "status": "planned", "base": report['base'], "head": report['head'],
            "includes": includes, "excludes": excludes, "repeats": repeats,
            "total_probes": len(probes), "omitted_probes": report['omitted_probes'],
            "command_executions": executions, "command_timeout_ceiling_seconds": executions * timeout,
            "skipped": report['skipped'], "probes": [p.public() for p in probes[:limit]]}


def audit(repo, base_ref, head_ref, includes, excludes, command, repeats=2,
          timeout=60, limit=30, progress=lambda message: None):
    report, base, head, probes = prepare(repo, base_ref, head_ref, includes, excludes, repeats, timeout, limit)
    report['command'] = command
    if not probes:
        report['status'] = 'no_probes'
        return report

    def execute(probe=None):
        with tempfile.TemporaryDirectory(prefix="greenblind-") as tmp:
            folder = Path(tmp)
            materialize(head, folder)
            if probe:
                file = folder.joinpath(*safe_path(probe.file).parts)
                if probe.replacement is None:
                    file.unlink()
                else:
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes(probe.replacement)
                    file.chmod((head.get(probe.file) or base[probe.file])[1])
            return run_command(command, folder, timeout)

    for n in range(repeats):
        progress(f"Baseline {n+1}/{repeats}")
        report["baseline"].append(execute())
    if classify(report["baseline"]) != "unnoticed":
        report["status"] = "baseline_failed"
        return report
    for index, probe in enumerate(probes[:limit]):
        progress(f"Probe {index+1}/{min(limit,len(probes))}: {probe.file}:{probe.start}")
        runs = [execute(probe) for _ in range(repeats)]
        report["results"].append({**probe.public(), "outcome": classify(runs), "runs": runs})
    progress("Final baseline")
    report["final_baseline"] = [execute()]
    if classify(report["final_baseline"]) != "unnoticed":
        report["status"] = "baseline_drift"
    elif report["omitted_probes"] or any(item['reason'] != 'excluded' for item in report['skipped']):
        report["status"] = "partial"
    return report
