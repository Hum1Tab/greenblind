# Greenblind 0.1.0 — experimental

Find which regions of a committed change your passing test command does not notice.

- Fresh snapshots; no checkout, reset, or stash of your working tree.
- Repeated region-removal probes with baseline checks and execution budgets.
- Standalone HTML, JSON, and Markdown reports.
- No runtime Python dependencies, model, account, or API key.
- Runnable demo plus a reproducible more-itertools history comparison.

Validation: 20 tests; CI on Linux, Windows, and macOS with Python 3.11, 3.12, and 3.13; installed-wheel demo.

Try from source:

```sh
git clone --branch v0.1.0 https://github.com/Hum1Tab/greenblind.git
cd greenblind
python -m greenblind demo
```

Or download the wheel attached to this release and install it with `python -m pip install greenblind-0.1.0-py3-none-any.whl`.

This is an early review aid. Exit 0 does not establish test discovery or correctness; nonzero exits include setup and build failures. Read the README's boundaries before using it in CI.
