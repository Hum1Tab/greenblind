import argparse
from pathlib import Path
import sys

from .core import audit
from .report import write


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find changes your passing command does not notice.")
    sub = parser.add_subparsers(dest="action", required=True)
    demo = sub.add_parser("demo", help="Run a real, disposable example with Python and Git")
    demo.add_argument("--output", type=Path, default=Path(".greenblind/demo"))
    run = sub.add_parser("check", help="Probe two committed revisions; run only trusted code")
    run.add_argument("--repo", type=Path, default=Path.cwd())
    run.add_argument("--base", required=True, help="Exact base revision (use a merge-base for PRs)")
    run.add_argument("--head", default="HEAD")
    run.add_argument("--include", action="append", required=True, help="Production file/glob to probe, repeatable; quote globs")
    run.add_argument("--exclude", action="append", default=[], help="Files/globs to leave unchanged")
    run.add_argument("--repeats", type=int, default=2)
    run.add_argument("--timeout", type=float, default=60)
    run.add_argument("--limit", type=int, default=30, help="Maximum changed regions to probe")
    run.add_argument("--output", type=Path, default=Path(".greenblind"))
    run.add_argument("--include-logs", action="store_true")
    run.add_argument("--fail-on-unnoticed", action="store_true")
    run.add_argument("command", nargs=argparse.REMAINDER, help="Command argv after -- (no shell)")
    args = parser.parse_args(argv)
    try:
        if args.action == "demo":
            from .demo import demo as run_demo
            report = run_demo(args.output)
        else:
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if not command:
                parser.error("Provide a command after --")
            report = audit(args.repo.resolve(), args.base, args.head, args.include, args.exclude,
                           command, args.repeats, args.timeout, args.limit,
                           progress=lambda s: print(s, file=sys.stderr, flush=True))
            write(report, args.output, args.include_logs)
        print(f"\nGreenblind: {report['status']}")
        for result in report["results"]:
            print(f"  {result['outcome']:12} {result['file']}:{result['start']}")
        print(f"Report: {(args.output / 'report.html').resolve()}")
        if report["status"] in ("baseline_failed", "baseline_drift", "no_probes", "partial"):
            return 2
        if any(r['outcome'] in ('inconclusive', 'unstable') for r in report['results']):
            return 2
        if getattr(args, "fail_on_unnoticed", False) and any(r['outcome'] == 'unnoticed' for r in report['results']):
            return 1
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"greenblind: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("greenblind: interrupted; no complete report was produced", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
