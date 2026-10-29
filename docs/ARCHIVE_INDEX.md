# Archive Directory Guide

Directories retain their historical names and relative organization. Restore release assets before using large files.

| Directory | Purpose |
|---|---|
| [cyp-private-v2-20261026](../archive/artifacts/cyp-private-v2-20261026/) | Latest private P1–P11 campaign, restoration receipts, chemistry and validation audits |
| [goal-20261026](../archive/artifacts/goal-20261026/) | ADMETlab audit, corrected-native, H6/H7, final readouts, and submission evidence |
| [tdi-20261024](../archive/artifacts/tdi-20261024/) | TDI classification: baselines, candidates, GNN, and assay-feature stacking |
| [briford-native-reproduction-20261024](../archive/artifacts/briford-native-reproduction-20261024/) | Historical native reproduction, full-data fitting, and the 0.4425 submission |
| [briford-native-holdouts-20261024](../archive/artifacts/briford-native-holdouts-20261024/) | Paired native evaluation on own750 and reconstructed529 |
| [chemeleon-native-next-20261024](../archive/artifacts/chemeleon-native-next-20261024/) | Loss, precision, and feature experiments; ADMETlab preparation |
| [overnight-autoresearch-20261023](../archive/artifacts/overnight-autoresearch-20261023/) | Early broad search, references, calibration, and source assets |
| [admetlab-auto](../archive/artifacts/admetlab-auto/) | Collector source; network collection requires a separate decision |
| [admet500-pilot-20261025](../archive/artifacts/admet500-pilot-20261025/) | Initial ADMETlab pilot using 500 molecules |
| [admetlab-labeling-skill-check](../archive/artifacts/admetlab-labeling-skill-check/) | Batch validation and merged outputs |
| [smiles-500](../archive/artifacts/smiles-500/) | Prepared batches of 500 structures |
| [strategy-20261024](../archive/artifacts/strategy-20261024/) | Preserved private candidates and strategy analysis |
| [chemical-space-audit-20261023](../archive/artifacts/chemical-space-audit-20261023/) | Chemical-space geometry and analogue-series analysis |
| [data-comparison-20261024](../archive/artifacts/data-comparison-20261024/) | Source comparison, tables, HTML report, and workbook |
| [cyp-review](../archive/artifacts/cyp-review/) | Scientific review of endpoints, datasets, and ESM |
| [leaderboard-review-20261023](../archive/artifacts/leaderboard-review-20261023/) | Historical review of public solutions |
| [reciprocal-comparison-20261023](../archive/artifacts/reciprocal-comparison-20261023/) | Reciprocal comparisons on aligned development cohorts |
| [ensemble-add-chemeleon-20261023](../archive/artifacts/ensemble-add-chemeleon-20261023/) | CheMeleon contribution to the ensemble |
| [chemeleon-baseline-20261023](../archive/artifacts/chemeleon-baseline-20261023/) | Initial standalone CheMeleon baseline |

[Raw ADMETlab collection records](../archive/admetlab-collection/) were added from the original collection directory. Authentication material is excluded.

Use [files.jsonl](../manifest/files.jsonl) for file hashes and [path-map.json](../manifest/path-map.json) for original machine-path mappings. Multiple source versions are retained; select the version associated with the relevant run manifest.

Additional [committed Git snapshots](../archive/git-snapshots/) and [local ORX run snapshots](../archive/local-orx-runs/) preserve execution provenance. [git-snapshots.json](../manifest/git-snapshots.json) maps revisions to their working trees. Model availability is defined separately by [retained-models.json](../manifest/retained-models.json).
