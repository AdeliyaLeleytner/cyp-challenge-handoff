# Models in the Working Package

The owner selected a working package containing research code, data, results, and selected model weights. See the [retained model inventory](../manifest/retained-models.json) and [other checkpoint inventory](../manifest/omitted-models.json).

- **Direct incumbent:** 20 checkpoints in [incumbent-artifact-copy](../archive/artifacts/cyp-private-v2-20261026/model-audit/incumbent-artifact-copy/): union18, mtaux8, 2d6isoform6, and 2d6single, each with five folds. [Provenance](../archive/artifacts/cyp-private-v2-20261026/model-audit/incumbent_preservation.json). These are the preserved models underlying the 0.4424575 submission.
- **H6:** four `head.joblib` files, portable `booster.txt` files, imputation/feature-order metadata, and query predictions in [final-models](../archive/artifacts/goal-20261026/final-locked-h6-output/final-models/). These support analysis of the saved results. Full H6 inference on new molecules also requires corrected-native refits, which are outside this smaller model set. Exact native vectors and raw/served CSVs are retained for the original 750 queries.
- **Jeremy TDI:** full-training seed42 LightGBM models and fitted transforms in [baseline/results/full/seed42](../archive/artifacts/tdi-20261024/remote/baseline/results/full/seed42/), together with the preserved TabICL classifier checkpoint.
- **Hauser TDI:** `remote/baseline/hauser_native/full/final_tdi.joblib` contains the final serialized baseline ensemble.
- **Dependencies:** the frozen ADME encoder `chemprop_medium.pt`, TabICL classifier, and CheMeleon foundation checkpoint. Original licenses and source references are retained. Other pretrained checkpoints can be obtained from the recorded upstream revisions when needed.

Identical hashes may appear under several historical paths but are downloaded once. Restore weights with `python3 tools/restore_assets.py --download`; the tool verifies their hashes before installation into the archive.
