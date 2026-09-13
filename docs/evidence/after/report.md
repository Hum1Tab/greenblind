# Greenblind report

Status: **complete**

Base: `19ddb972845ab0e5b9b7449d3fd5930781407441`

Head: `87d12578c3e558c57fbfbe663be63259c1fce56f`

| Change | Command outcome after removal |
| --- | --- |
| more_itertools/more.py:4941 | unnoticed |
| more_itertools/more.py:4955 | rejected |

0 probes omitted by the budget. 0 files skipped.

Unnoticed means the selected command still exited 0 after one change was removed. It can indicate a test gap, a deliberate refactor, or a command that does not run tests. Rejected means a nonzero exit, including build/import errors; it does not prove an assertion caught a bug. Changes are tested independently, not in combination. Repeat runs do not rule out flakiness.
