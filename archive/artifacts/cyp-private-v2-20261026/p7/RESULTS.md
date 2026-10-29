# P7 direct ADMET120 fusion: private five-fold result

The tested direct-feature fusion is worse than its fresh matched zero-feature control on all five macro metrics. This is a result for this fixed architecture/training recipe, not evidence that every possible feature integration must fail. Neither model has been published or submitted.

| Metric | Matched zero control | ADMET120 fusion | Fusion minus control | Paired descriptive 95% interval |
|---|---:|---:|---:|---|
| ST-RAE | 0.674456 | 0.702571 | +0.028115 | [+0.011602, +0.043123] |
| MAE | 0.537914 | 0.556678 | +0.018764 | [+0.010893, +0.026176] |
| R2 | 0.394981 | 0.346449 | -0.048532 | [-0.066453, -0.030868] |
| Spearman | 0.612771 | 0.572605 | -0.040166 | [-0.054929, -0.025166] |
| Kendall | 0.442480 | 0.410951 | -0.031529 | [-0.042965, -0.020192] |

Per-CYP ST-RAE also worsens in every point estimate: CYP1A2 +0.062681, CYP2C9 +0.012042, CYP2D6 +0.023601 and CYP3A4 +0.014135. The accompanying CSV retains every endpoint and metric, including adverse cases and intervals. Pearson is an additional diagnostic, not an official-metric replacement.

Both arms use the same 31,641 curated rows and 18 real output heads. All 4,905 official training molecules are scored once out of fold. The five stored folds rotate a separate stopping cohort. Four stopping rows equivalent to test compounds were removed using previously approved structural groups, without consulting outcomes. Training and test indices remained fixed. There are no train/stopping/test overlaps under that equivalence policy. This is a fresh comparison on reused development data, not the old own-750 or reconstructed-briford-529 holdout, and not prospective blind confirmation.

Both networks use a scratch graph encoder with width 2,048 and depth 4, a two-layer 1,024-wide FFN, dropout 0.2, and identical 2,168-dimensional FFN inputs. The 26 outputs comprise 18 real tasks and eight masked confidence-bound carriers. ADMET descriptors enter after graph pooling; the encoder and head train together. The 120 descriptor weight columns start at zero in both arms. Initial parameter hashes and batch-normalization buffers match within each fold, initial predictions match exactly, and real-batch checks confirm graph gradients in both arms and descriptor-weight gradients in the fusion arm. The control always receives 120 zeros. It is a fresh matched control, not the original rank-27/native-700 model.

All 120 numeric features exactly match the audited web-default ADMET snapshot by request ID. Imputation and scaling use training rows only. Potency labels, confidence intervals and IDs are never features. Both arms use unweighted MAE, the same optimizer and precision, and the same raw primary ST-RAE stopping criterion, with a maximum of 200 epochs and patience 30. No blind-population placement or ensemble weights were fitted. The teacher's pretraining membership remains unknown; independence from all public assays is not certified.

The independent readout checks the exact official ID set and original target values, finite ordered bounds, every fold's prediction ID/order/hash, and every runtime per-fold metric before pooling. Its ST-RAE implementation matches the frozen official scorer. The intervals use 1,000 paired Bemis–Murcko scaffold-group resamples within the frozen folds, seed 20261026, shared across arms and endpoints, with percentile 95% bounds. They describe uncertainty conditional on these OOF predictions. Overlapping training sets and previous development use limit generalization claims. No significance or promotion cutoff was invented.

Execution: node e0344f06-88e4-465f-acda-2caeaadce80a; successful run 6deeddf6-471e-4ac3-b225-194215cbec15; source 6084499. The preceding run 2df48e1 failed before training because Chemprop received a duplicated `drop_last` keyword; its logs remain available. The repaired evaluation loader was checked on 129 rows, yielding batches of 128 and 1, without changing the learning rule.

Evidence: `readout/READOUT.json`, `readout/point-metrics.csv`, `readout/paired-deltas.csv`, both chemical-join review certificates, and `recovered/metric-snapshot`. Both model sets are retained. All 10 full checkpoint binaries and all result files are now locally hash-verified against the immutable remote manifest; see `RECOVERY_CERTIFICATE.json`.

Decision: do not promote this fusion recipe over its matched control. Continue the already authorized P3 loss-by-weighting factorial. This negative result does not automatically expand the search to more fusion architectures or hyperparameters.
