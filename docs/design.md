# Design

Greenblind asks a counterfactual question: with all other HEAD files fixed, what happens if one changed region returns to its base contents?

1. Resolve both input refs to immutable commit SHAs.
2. Enumerate tracked blobs using `git ls-tree` and read them through `git cat-file --batch`. Read exact bytes without Git attributes changing the export.
3. Match explicit includes/excludes; identify contiguous changed regions with `difflib.SequenceMatcher` on byte lines.
4. Run the selected command repeatedly on fresh HEAD snapshots. Stop if these baselines do not consistently exit 0.
5. For each region, construct `HEAD prefix + BASE region + HEAD suffix` in a fresh snapshot. Keep all other regions and tests at HEAD. Repeat the command.
6. Run a final pristine HEAD baseline. Record every status, exit code, duration, skipped file, and budget omission.

No model judges the code. No working-tree Git command runs. No subprocess shell is involved.

The experiment is narrower than an AST mutation engine and different from delta debugging a failure: it starts with a passing command and highlights what it cannot distinguish. It does not compute a minimum patch and never applies suggested deletions.

## Cost

`repeats × (probes + 1) + 1` command executions. Fresh snapshots trade speed for avoiding stale build outputs. Start with narrow production paths and focused tests. A fast command that does not actually test the snapshot produces meaningless results.

## Interpreting evidence

Exit codes are observations, not semantic failure classes. An import error and an assertion failure can both return 1. Reports therefore say `rejected`, never “regression proved.” Future structured test adapters should improve this without silently changing the schema's meaning.

Even two equal exit codes can hide different test outcomes. Flakiness, external services, mutable global state, nondeterministic order, package resolution, and interacting changes limit the inference. A successful run only applies to the specified commits, command, includes, environment, and repeat count.
