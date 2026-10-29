# Data Entry Points

Start with the [data guide](../docs/DATA.md).

- [Official Direct training data](../archive/artifacts/cyp-private-v2-20261026/p11/evidence/official_train.csv) and [blinded queries](../archive/artifacts/cyp-private-v2-20261026/p11/evidence/official_blind.csv).
- [Audited ADMETlab table covering all 32,421 outcomes](../archive/artifacts/goal-20261026/audited-dataset/admetlab-32421-audited-features.csv), its [manifest](../archive/artifacts/goal-20261026/audited-dataset/manifest.json), and [data notes](../archive/artifacts/goal-20261026/audited-dataset/README.txt).
- [Prepared native datasets](../archive/artifacts/cyp-private-v2-20261026/model-audit/incumbent-artifact-copy/prepared/): exact inputs for the four native components.
- [Prepared TDI baseline data](../archive/artifacts/tdi-20261024/remote/baseline/prepared/); label counts and provenance are documented in the [TDI report](../archive/artifacts/tdi-20261024/REPORT.md).
- [Raw ADMETlab responses and merged outputs](../archive/admetlab-collection/results/). Preserve missing, rejected, and ineligible outcomes; predicted properties are not experimental labels.

Large tables and arrays are restored from the private release. Official Direct training data, TDI training data, and the external pool are different populations. Audit molecular identities before transferring splits between them.
