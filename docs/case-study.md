# A real history: tests learning to notice a guard

We ran Greenblind against two historical commits in [more-itertools](https://github.com/more-itertools/more-itertools). This is a reproducible tool evaluation, not a newly discovered upstream bug, an endorsement, or evidence of user adoption.

The [implementation commit](https://github.com/more-itertools/more-itertools/commit/d032cab7798c7a072ecbb8ade4dfa50030c75cb5) adds validation for nonpositive `max_count` values in `constrained_batches`, plus a docstring change. The immediately following [test commit](https://github.com/more-itertools/more-itertools/commit/87d12578c3e558c57fbfbe663be63259c1fce56f) adds tests for that validation.

We compared both against the same base, `19ddb972845ab0e5b9b7449d3fd5930781407441`, while keeping each selected head's tests unchanged.

| Region removed | Implementation commit, before added tests | Following commit, with added tests |
| --- | --- | --- |
| Docstring wording | Unnoticed | Unnoticed |
| Input-validation guard | Unnoticed | Rejected |
| Pristine baseline suite | 912 tests passed | 914 tests passed |

Both repetitions agreed for every region. All initial and final baselines exited 0. Removing the guard after the test addition produced four failing subtests in `ConstrainedBatchesTests.test_nonpositive_max_count`, each with `AssertionError: ValueError not raised`. That assertion detail was checked in the logs; the general tool still reports only `rejected` because it does not parse assertion semantics.

The useful distinction is visible: the unchanged outcome for documentation is expected; the changed outcome for validation demonstrates what the added tests now detect. Neither green result would justify deleting the corresponding code.

## Reproduce

From a Greenblind source checkout, with Python 3.11+ and Git:

```sh
git clone https://github.com/more-itertools/more-itertools.git .greenblind/more-itertools
python -m greenblind check --repo .greenblind/more-itertools --base 19ddb972845ab0e5b9b7449d3fd5930781407441 --head d032cab7798c7a072ecbb8ade4dfa50030c75cb5 --include more_itertools/more.py --timeout 90 --output .greenblind/before-tests -- python -m unittest discover -s tests
python -m greenblind check --repo .greenblind/more-itertools --base 19ddb972845ab0e5b9b7449d3fd5930781407441 --head 87d12578c3e558c57fbfbe663be63259c1fce56f --include more_itertools/more.py --timeout 90 --output .greenblind/after-tests -- python -m unittest discover -s tests
```

Evaluation environment: Windows, Python 3.12, 2026-09-14 Japan time. Seven test executions per comparison, approximately 11–12 seconds each. Other environments may differ. We did not modify or submit anything to the upstream project.

Observed reports, with logs omitted:

- [Before tests: JSON](evidence/before/report.json) / [Markdown](evidence/before/report.md)
- [After tests: JSON](evidence/after/report.json) / [Markdown](evidence/after/report.md)

Report source excerpts originate from more-itertools, which is [MIT licensed](https://github.com/more-itertools/more-itertools/blob/master/LICENSE).
