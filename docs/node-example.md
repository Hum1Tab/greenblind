# Node example: an ANSI control-sequence fix

This is a focused behavior check of [chalk/ansi-regex's colon-parameter change](https://github.com/chalk/ansi-regex/commit/df7d75f488cc937fe1e13d75449bcfdd2b11ac61), using Node's built-in assertions. It is **not the upstream AVA suite** and does not claim the whole library is validated.

The original project test command needs development dependencies. Fresh Greenblind snapshots omit ignored `node_modules`, so merely pointing at an uninstalled AVA CLI fails its baseline. A plan can preview the change without installing or executing anything:

```sh
git clone https://github.com/chalk/ansi-regex.git .greenblind/ansi-regex
python -m greenblind plan --repo .greenblind/ansi-regex --base 827322a26097791c663a3688d5d938d197519a0f --head df7d75f488cc937fe1e13d75449bcfdd2b11ac61 --include "*.js" --exclude test.js
```

Observed plan: one region in `index.js`, `test.js` intentionally excluded, five command executions, no omitted regions.

For a quick check without third-party dependencies, use [the example script](../examples/ansi-regex-check.mjs). Replace `/absolute/path/to/greenblind` with your checkout's absolute path:

```sh
python -m greenblind check --repo .greenblind/ansi-regex --base 827322a26097791c663a3688d5d938d197519a0f --head df7d75f488cc937fe1e13d75449bcfdd2b11ac61 --include "*.js" --exclude test.js -- node /absolute/path/to/greenblind/examples/ansi-regex-check.mjs
```

Quote the script path if it contains spaces. The script imports `index.js` from its current working directory, so it checks the disposable snapshot rather than the original checkout. It checks matching and stripping a colon-separated ANSI color sequence.

Observed on Windows, 2026-09-14 Japan time: both pristine baselines and the final baseline passed; restoring the changed region caused both probe runs to exit 1. The report was complete, with the intentional exclusion visible. This validates the example behavior and exclusion handling, not general test coverage or adoption.

For full-suite checks, provide your own wrapper that installs/builds inside each snapshot. Greenblind still does not solve dependency provisioning; plan mode only avoids spending test time before you have checked the scope.
