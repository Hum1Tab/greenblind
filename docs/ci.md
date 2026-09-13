# CI recipe

Run on trusted branches in a disposable runner, with read-only repository permissions and no deployment secrets. The tool executes repository code, so a temporary snapshot does not make an untrusted pull request safe.

1. Fetch both compared revisions (a shallow checkout may omit the base).
2. Install Greenblind from a pinned release or reviewed commit in a virtual environment.
3. Install the test environment. Avoid editable installs referencing the original checkout.
4. Pass the merge-base SHA and explicit production paths.
5. Upload `.greenblind/report.html`, `.greenblind/report.json`, and `.greenblind/report.md` as artifacts after reviewing your source/log exposure policy.

For a dependency-free Python project:

```sh
greenblind check --base BASE_SHA --head HEAD_SHA --include "src/*" -- python -m unittest discover -s tests
```

Replace `BASE_SHA` and `HEAD_SHA` with actual SHAs. Commands needing installation/build should use a checked-in script that operates on its current snapshot directory. Copying host `node_modules` or reusing an editable installation can make the command test the wrong code.

Start in advisory mode. Exit 2 means the run is incomplete or untrustworthy and should be investigated, even without `--fail-on-unnoticed`. Exit 0 means the selected probes completed, not that every change was tested or correct.
