# Changelog

## 0.2.0

- Preview region IDs, scope, exclusions, and command count with `greenblind plan`; add `--json` for scripts. Planning executes no repository code.
- Fix intentional exclusions incorrectly making otherwise complete checks partial.
- Skip test execution when there are no selected regions.
- Explain dependency/command checks when the baseline fails.
- Add a dependency-free, focused Node example against ansi-regex history.

## 0.1.0

First experimental release: committed-region probes, fresh snapshots, repeated command observations, baseline drift checks, execution budgets, local HTML/JSON/Markdown reports, and a dependency-free demo.
