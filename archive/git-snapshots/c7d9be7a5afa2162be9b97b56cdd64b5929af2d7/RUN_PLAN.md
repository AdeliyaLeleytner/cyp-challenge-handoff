# Prepared corrected native reference — not launched

Experiment31f8a64a-174d-4f92-95e8-2ada73c2176d is a child of the completed native outer-holdout reference1346e303-7733-44ce-b2d8-ffe26eab8a61, parent commit28933f89075ad51b9583b7ca69fffa0b9e921dfb. Its inherited run command remains **bash run.sh**.

## Controlled change

Remove only the12 approved stereo-preserving tautomer-equivalent external rows: own750 union18=4, own7502d6isoform6=2, briford529 union18=3, briford5292d6isoform6=3. The4broader stereo-related analog rows are retained.

Retain original row order and numeric CSV bytes for all remaining rows. Preserve outer query/truth files, model hyperparameters, task weights, native training/assembly/scoring source and original validation-fold assignments. Delete and reindex the outer rows; within each original inner fold, remove only training-side counterparts from the13approved strict equivalence groups. This yields62additional fold-training exclusions (14/14/18/16 respectively), with validation membership unchanged apart from the globally removed rows. Do not regenerate scaffold folds.

These exclusions change the fitted reference. Historical scores remain historical; no corrected score is available until training is run.

## Reuse versus retrain

Retrain20fits: union18 and2d6isoform6, five folds, two outer cohorts. The wrapper calls the unchanged `night.briford_native --worker` implementation. All pinned files under vendor/briford_native and the original adapter are unchanged.

Reuse20fits: mtaux8 and2d6single. Their data and specification hashes are identical to the source; no inner exclusions are required. The preflight verifies each fold's original checkpoint, prediction, metadata and job hashes, matches OOF IDs to the original validation indices and test IDs to the original query, checks native hyperparameters, and independently recomputes original outer ID/parent/InChI-connectivity exclusions for these reused pools. Historical job.json is copied unchanged because its hash is part of the completion record. The runner does not invoke native.run, which would overwrite those job files.

Full-fold source artifacts and certificates are in the staging bundle. The child recomputes ensemble aggregation and native placement using unchanged source code after the20newfits finish. Raw and placed ST-RAE, MAE,R²,Spearman,Kendall are reported separately.

## Preflight already performed

- Deterministic source/row/fold checks and exact retained-value comparisons.
- All20reuse checkpoint/prediction/metadata hashes verified.
- Unchanged-component outer structural purges recomputed.
- Every inner fold checked for zero overlap under the approved strict-equivalence groups.
- Historical cached predictions rescored: all four raw/placed macro ST-RAE values reproduce exactly (absolute error0). This is a scorer check, not a new experiment result.
- Syntax checks only; zero model fits and zero paid compute launches.

## Parent-controlled launch

The full stage is at the sibling directory `../stage` (about395MB), with a recursive asset-manifest.json. Upload it unchanged to `/workspace/cyp-strict-reference/stage` on a newly verified authorized host. The committed config pins its manifest hash. The parent's live offer/budget decision is still required; this helper did not rent or connect to a machine.

The runtime must match the historical recorded packages: torch2.6.0+cu124, chemprop2.2.1, lightning2.5.5, rdkit2026.9.1, numpy2.2.6, pandas2.3.3, scikit-learn1.7.2; the inherited setup also pins scipy1.16.2. Select a compatible image before renting. The setup fails rather than silently using another torch version or CPU fallback.

The config currently schedules the20fits across eight visible GPUs, with heavier union18 jobs first. If the parent selects a different GPU count, edit only the operational gpus list in strict_reference_config.json and commit the provisional child before launch. Do not change hyperparameters or use launch-time environment overrides. Historical timing is about4.87GPU-hours for these affected fits; current offer pricing and wall time must be checked rather than assumed.

Launch only through ORX after the parent has staged/verified assets and selected compute:

```text
ORX_DATA_DIR=/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store orx exp run 31f8a64a-174d-4f92-95e8-2ada73c2176d --backend ssh --host <verified-host> --no-container
```

The selected-host placeholder must be replaced with the parent's actual verified host. No launch has occurred. Recover all output/checkpoint/prediction/log files, verify hashes, and terminate rented compute after the run before interpreting/qualifying feature models.
