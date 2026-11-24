# Answer-key reconciliation and reflection

*Fictional company — simulated ITGC audit. Results below come from `Answer_Key_Reconciliation.xlsx`, produced by `reconcile_answer_key.py`.*

## Result

| Outcome | Count |
|---|---|
| Planted exceptions in the answer key | 18 |
| Exceptions detected by the audit | 18 |
| Found by sampling or 100% testing | 7 |
| Found only by full-population analytics | 11 |
| Missed | 0 |
| False positives | 0 |

## Where each method found exceptions

| Control | Testing method | Planted | Found by sample / 100% test | Found only by analytics |
|---|---|---|---|---|
| APD-01 New user access | Sample 10 of 39 | 2 | 0 | 2 |
| APD-02 Leaver removal | Sample 10 of 38 | 3 | 0 | 3 |
| APD-03 Access review | All 4 quarters | 1 | 1 | – |
| APD-04 Privileged access | Full listing (11) | 1 | 1 | – |
| APD-05 Generic accounts | Full listing (396) | 1 | 1 | – |
| PC-01 / PC-02 / PC-03 Change | Sample 25 of 141 | 4 | 0 | 4 |
| PC-04 Emergency change | Sample 10 of 12 | 1 | 0 | 1 |
| PD-02 UAT before go-live | Whole project | 1 | 1 | – |
| CO-01 Backup failures | All 10 failures | 2 | 2 | – |
| CO-02 Restore tests | All 4 quarters | 1 | 1 | – |
| CO-03 Batch failures | Sample 10 of 15 | 1 | 0 | 1 |

## What this taught me

1. **Sampling risk is real.** Every exception in a sampled population fell outside the random sample. With a 2-in-39 error rate, a sample of 10 has roughly a 55% chance of finding nothing. The formal sample results for seven controls said "operating effectively" — all seven were wrong.
2. **Where data is system-generated and validated, test 100%.** Once the populations had passed completeness checks, running the same attribute tests on every record cost almost nothing and gave a complete answer. Sampling remains the right tool where evidence must be inspected manually.
3. **Choose the population from the most complete source.** Building the change population from the deployment log rather than the ticket list is what surfaced the deployment with no ticket (DEP-30069). A ticket-based population would never have contained it.
4. **Small populations and listings should be tested in full.** All seven exceptions in quarterly controls, privileged listings, the project file and backup failures were found because those populations were tested completely.
5. **Zero false positives depended on precise criteria.** Defining "1 business day" exactly (Friday to Monday = 1) avoided flagging compliant weekend cases. Where NovaLend had no criterion (batch failure resolution time), timeliness could not be tested at all — which is why it was raised as a design gap.

## Limitation of this reconciliation

The planted exceptions were designed from the same control criteria the tests check, so detecting all of them shows the test logic works — not that real-world exceptions would all be this clear-cut. Real evidence is messier, and many exceptions need judgement rather than a rule.
