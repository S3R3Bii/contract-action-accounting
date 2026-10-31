# Implementation exercise: retain the measurement boundary

Start with the fixed source cases and return a current transaction-count or signed-obligation account. Keep unsupported interpretations explicit.

~~~powershell
python src/exercise.py
python -m unittest discover -s tests -v
~~~

The [seven input requests](data/exercise_inputs.json) use cases fixed before outcomes. Their [complete outputs](results/exercise.json) return C01's seven eligible current source records and C03's USD 3,585 signed obligation account. Five other requests seek staff hours, vendor risk, pre-award features, dollars as an action count or future modifications. Each is rejected.

Call interpret(request, accounts) in [exercise.py](src/exercise.py) with the verified account export. The function describes known case accounts and refuses unsupported measure conversions. It does not certify upstream data or arbitrary caller-provided accounts. An accepted description is not proof of historical publication, legal-modification identity, staffing effort or production readiness.

The [accounting implementation](src/accounting.py) preserves complete source-row accounting, whole duplicate-key groups, missing and signed amounts, explicit window exclusions, exact decimal sums and fixed tie rules. Its 33 authored fixture methods include adversarial identity, money, calendar, empty-window and exact-rank boundaries. The independent checker reconstructs every actual saved case, row classification, probe, rank and request without importing those production functions.

For integration, validate the source/freeze hashes first and retain both counts and financial measures in the consumer's data contract. A staffing application needs measured tasks and review time. A pre-award classifier needs verified feature availability and a separate protected evaluation. No deployment or measured benefit is claimed here.
