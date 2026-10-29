# Data and Units of Analysis

| Dataset | Size and meaning | Location |
|---|---|---|
| Official Direct training set | 4,905 molecules; endpoint-specific missing labels | `archive/artifacts/cyp-private-v2-20261026/p11/evidence/official_train.csv` |
| Blinded query set | 750 molecules; hidden labels unavailable | `archive/artifacts/cyp-private-v2-20261026/p11/evidence/official_blind.csv` |
| Full prepared pool | 32,421 unique official and external structures | `archive/artifacts/goal-20261026/audited-dataset/` |
| ADMETlab feature-eligible rows | 32,418 rows with 120 predicted properties | `admetlab-32421-audited-features.csv` in the audited dataset |
| Source-supervision eligible rows | 32,392 after the separate source policy | `source-supervision-policy.json` and quarantine records |
| P7/P7R staged matrix | 31,641 rows in the specific experimental input | `archive/artifacts/cyp-private-v2-20261026/p7*/stage/` and manifests |
| Official TDI training set | 6,145 molecules; two partially observed binary endpoints | `archive/artifacts/tdi-20261024/remote/` and its DATA.md |

These counts refer to different entities and eligibility policies. The 32,421 requested structures are not 32,421 experimental pIC50 labels and are not the training size of every model. The four added H6 readouts used 1,412, 1,285, 1,493, and 2,335 observed official labels for 1A2, 2C9, 2D6, and 3A4, respectively.

The service explicitly rejected Cl and N. One external antimony structure has numerical outputs but an unverified returned graph and is feature-ineligible. A separate exact internal proton-transfer transformation was accepted as a feature representation after review; this does not establish the assay microstate or authorize merging experimental identities. All 5,655 official inputs passed the feature audit.

Request and returned SMILES, aliases, outcome records, provenance, flags, and missingness are retained. Do not replace missing labels with zeros. Raw ADMETlab responses are under `archive/admetlab-collection/`; audited exports are under `goal-20261026/audited-dataset/`. Use the audited exports for routine analysis and the raw responses for provenance checks.

The P7R unit repair changes a derived feature matrix, leaving the raw service cache intact. Exact rules and row/cell hashes are recorded in `cyp-private-v2-20261026/p7r/` and the associated chemical review. Do not replace that correction with an arbitrary normalization.

Own750 and reconstructed-briford529 are reused development cohorts sharing 143 molecules. The second is our reconstruction, not the original author's recovered split. Preserve the distinction between original native and corrected-native. Historical components retain their own fold assignments and supervision limitations; clean downstream nesting does not retroactively resolve upstream limitations.

Key sources: [biochemical data audit](../archive/artifacts/cyp-private-v2-20261026/BIOCHEM_DATA_AUDIT.md), [external measurement availability](../archive/artifacts/cyp-private-v2-20261026/EXTERNAL_MEASUREMENT_AVAILABILITY.md), [data policy](../archive/artifacts/goal-20261026/audited-dataset/README.txt), and [TDI report](../archive/artifacts/tdi-20261024/REPORT.md).
