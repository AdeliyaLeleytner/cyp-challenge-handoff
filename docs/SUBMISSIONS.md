# Submission History and the Preserved Incumbent

| Variant | Observed MA-ST-RAE | Exact CSV in P11 evidence |
|---|---:|---|
| Early ensemble + OOF calibration | 0.7521205 | `adapted-csv.csv` |
| Original Briford-native | **0.4424575** | `native-csv.csv` |
| Corrected/refitted native + H6 | 0.4616 | `H6-csv.csv` |
| Original native + H6 | 0.4679 | `anchored-csv.csv` |
| Original native restored on 27 October | 0.4425 | The same `native-csv.csv` |

[Prediction files and receipts](../archive/artifacts/cyp-private-v2-20261026/p11/evidence/), [local-versus-leaderboard comparison](../archive/artifacts/cyp-private-v2-20261026/p11/submission-local-comparison.csv), and [restoration receipt](../archive/artifacts/cyp-private-v2-20261026/restore-20261027/processed-result.json).

SHA256 hashes:

- Native: `349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37`.
- H6: `91fa8bf0870f68071b04183166b1507c20001d04f3ae3fb5f4d055618fff98c7`.
- Anchored: `6807263f0ccadcb31aa28a5c54653608e12271939a2490a2404d4353aeb0e16d`.

The leaderboard evaluates a subset of the hidden test set. These observations are not full-test estimates. Public rows do not expose uploaded file hashes: the association rests on local immutable intent/receipt records together with the participant alias and submission time. Ranks are historical and may change.

This repository does not restore the deleted public gist. Historical requirements for a public report link belong to the earlier submission contract. Before a future submission, check the actual rules and discuss any required disclosure with the owner. This private handoff does not authorize additional leaderboard submissions or public publication.
