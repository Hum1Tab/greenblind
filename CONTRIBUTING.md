# Contributing

Useful contributions start with a small reproducible repository and the exact command, base/head SHAs, operating system, and expected interpretation. Remove private code, arguments, and logs before sharing.

Run `python -m unittest discover -s tests -v`. Keep the core dependency-free. Add behavioral tests for fixes involving Git snapshots, process execution, path handling, or result semantics.

Current priorities:

- Structured test results to separate assertion failures from setup errors.
- Practical dependency/build setup without stale-code reuse.
- Real examples where an unnoticed change exposed a useful missing test.
- Better handling of coupled changes and transparent execution budgets.

Do not describe `unnoticed` code as dead or safe to delete. Do not describe a nonzero exit as proof of regression detection.
