"""Portable reports. Source and command output are always escaped."""
from collections import Counter
from html import escape
import json
from pathlib import Path

NOTE = ("Unnoticed means the selected command still exited 0 after one change was removed. "
        "It can indicate a test gap, a deliberate refactor, or a command that does not run tests. "
        "Rejected means a nonzero exit, including build/import errors; it does not prove an assertion caught a bug. "
        "Changes are tested independently, not in combination. Repeat runs do not rule out flakiness.")


def markdown(report):
    rows = ["# Greenblind report", "", f"Status: **{report['status']}**", "",
            f"Base: `{report['base']}`  ", f"Head: `{report['head']}`", "",
            "| Change | Command outcome after removal |", "| --- | --- |"]
    for item in report["results"]:
        name = item['file'].replace('|', '\\|').replace('\n', ' ')
        rows.append(f"| {name}:{item['start']} | {item['outcome']} |")
    rows += ["", f"{report['omitted_probes']} probes omitted by the budget. {len(report['skipped'])} files skipped.", "", NOTE, ""]
    return "\n".join(rows)


def html(report):
    counts = Counter(r["outcome"] for r in report["results"])
    cards = "".join(f'<div class="stat {key}"><b>{counts[key]}</b><span>{key}</span></div>'
                    for key in ("unnoticed", "rejected", "unstable", "inconclusive"))
    changes = []
    for row in sorted(report["results"], key=lambda r: r['outcome'] != 'unnoticed'):
        logs = "".join(f'<details><summary>Run {i+1}: exit {run["exit_code"]} · {run["seconds"]}s</summary>'
                       f'<pre>{escape(run.get("log", "Logs omitted. Use --include-logs to export them."))}</pre></details>'
                       for i, run in enumerate(row["runs"]))
        changes.append(f'<article data-outcome="{row["outcome"]}"><div class="row"><h2>{escape(row["file"])}'
                       f'<small>:{row["start"]}–{row["end"]}</small></h2><span class="badge {row["outcome"]}">{row["outcome"]}</span></div>'
                       f'<div class="diff"><section><label>Current change</label><pre>{escape(row["after"] or "(deleted)")}</pre></section>'
                       f'<section><label>Restored for this probe</label><pre>{escape(row["before"] or "(removed)")}</pre></section></div>{logs}</article>')
    skip = "".join(f'<li>{escape(item["file"])}: {escape(item["reason"])}</li>' for item in report['skipped'])
    baselines = ''.join(f'<details><summary>{label} {i+1}: {escape(run["status"])} · exit {run["exit_code"]} · {run["seconds"]}s</summary>'
                        f'<pre>{escape(run.get("log", "Logs omitted. Use --include-logs to export them."))}</pre></details>'
                        for label, runs in [('Baseline', report['baseline']), ('Final baseline', report['final_baseline'])]
                        for i, run in enumerate(runs))
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'none'">
<title>Greenblind · Change audit</title><style>
:root{color-scheme:dark;font:16px/1.6 system-ui,sans-serif;background:#101412;color:#e9eee9}*{box-sizing:border-box}
body{margin:0 auto;max-width:1100px;padding:48px 24px 80px}header{border-top:3px solid #a6f59e;padding-top:24px}
.brand{color:#a6f59e;font:700 14px monospace;letter-spacing:.14em}h1{font-size:clamp(32px,5vw,58px);line-height:1.08;max-width:780px;letter-spacing:-.04em;margin:24px 0}
.intro{font-size:18px;color:#b0bfb3;max-width:750px}.meta{font:13px monospace;overflow-wrap:anywhere;color:#8fa394;padding:18px 0}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:28px 0}.stat{border:1px solid #344138;border-radius:12px;padding:20px}
.stat b{display:block;font-size:38px;line-height:1.2}.stat span{font-size:13px;text-transform:uppercase;letter-spacing:.08em}
.unnoticed{color:#ffc978}.rejected{color:#a6f59e}.unstable,.inconclusive{color:#c8b8ff}.notice{border-left:3px solid #ffc978;padding:12px 20px;background:#1d241f;color:#c4d0c6}
article{border:1px solid #344138;border-radius:12px;margin-top:18px;padding:24px}.row{display:flex;justify-content:space-between;gap:16px;align-items:center}h2{font:600 17px monospace;overflow-wrap:anywhere;margin:0}small{color:#92a396}
.badge{font:13px monospace;border:1px solid currentColor;border-radius:30px;padding:4px 12px}.diff{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:24px 0}
section{min-width:0}label{font-size:12px;color:#9aac9d;text-transform:uppercase;letter-spacing:.08em}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0b0f0d;border-radius:8px;padding:16px;font:14px/1.6 ui-monospace,monospace}
details{font-size:13px;color:#a6b8aa}summary{cursor:pointer;padding:7px 0}footer{margin-top:40px;color:#8fa394;font-size:13px}
@media(max-width:640px){body{padding:24px 16px}.stats{grid-template-columns:1fr 1fr}.diff{grid-template-columns:1fr}.row{align-items:flex-start;flex-direction:column}article{padding:18px}}
</style><header><div class="brand">GREENBLIND / CHANGE AUDIT</div><h1>Green tests.<br>What did they miss?</h1><p class="intro">Remove one change. Run the same command. See what stays green.</p></header>''' + (
        f'<div class="meta">{escape(report["base"][:12])} → {escape(report["head"][:12])} · status: {escape(report["status"])}'
        f'<br>Command: {escape(json.dumps([report["command"][0].replace(chr(92), "/").split("/")[-1], *report["command"][1:]]))}</div><div class="stats">{cards}</div>'
        f'<p class="notice">{escape(NOTE)}</p><details><summary>Baseline checks</summary>{baselines}</details>{"".join(changes)}'
        f'<footer>{report["omitted_probes"]} probes omitted by budget. {len(report["skipped"])} files skipped.<ul>{skip}</ul>'
        'Generated locally by Greenblind. No external scripts, fonts, or analytics.</footer></html>')


def write(report, output: Path, include_logs=False):
    report = json.loads(json.dumps(report))
    if not include_logs:
        for group in [report["baseline"], report["final_baseline"], *[r["runs"] for r in report["results"]]]:
            for run in group:
                run.pop("log", None)
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "report.md").write_text(markdown(report), encoding="utf-8")
    (output / "report.html").write_text(html(report), encoding="utf-8")
