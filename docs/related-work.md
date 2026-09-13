# Related work

Greenblind is an original implementation of a small counterfactual review workflow. The underlying ideas of mutation testing, patch ablation, and delta debugging have substantial prior art. We do not claim to have invented them.

| Project | Its focus | Greenblind's initial focus |
| --- | --- | --- |
| [Stryker](https://github.com/stryker-mutator/stryker-js) | Mutation testing for JavaScript and related languages. | Actual changed regions, without a language parser. |
| [mutmut](https://github.com/boxed/mutmut) | Mutation testing for Python. | Committed diffs and command outcomes across languages. |
| [FixWitness](https://github.com/adondada/fixwitness) | Checking a regression test against a removed implementation patch. | Separate observations for each contiguous region. |
| [testbump](https://github.com/ivoputzer/testbump) | Test contracts used to inform version bumps. | A review report, without deciding a version. |
| [diffbisect](https://github.com/PrecisionUtilityGuild/diffbisect) | Finding which hunks caused a failing command. | Starting green and finding regions a command does not notice. |

This comparison is based on project READMEs reviewed on 2026-09-14, not a full feature audit or benchmark. Established mutation tools have mature capabilities Greenblind does not yet offer.
