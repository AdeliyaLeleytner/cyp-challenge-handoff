# Original native expert used in the nested test

The test uses the preserved **original-recipe outer-holdout refits**, not the corrected native reference and not a full-training model evaluated on its own training labels. The deployed incumbent and its weights are untouched.

The stage reconstructed each outer-training OOF vector from original component OOF files. It checked all 40 component-fold prediction receipts across the two cohorts: job, OOF, query-prediction and metadata hashes; exact validation IDs against the saved component folds; uniqueness; and agreement between fold predictions and component aggregates. Primary labels in those aggregates match the official table. Checkpoint binaries were not loaded or rehashed for this inference-free reconstruction.

For each observed primary label, the original ensemble has two component predictions for 1A2, 2C9 and 3A4, and four for 2D6. The rowwise means use those original members. Reconstructing query means from the same components reproduces the preserved original raw query vectors within 1e-12. Those vectors also match the previously verified P5 original reference. Sources and hashes are pinned in `stage/manifest.json`.

The new TabICL inner folds are wholly inside the actual outer-training pools: 4,155 molecules for own750, 4,375 for briford529. Their validation rows cover each outer-training pool once. Full outer-query exclusion, normalized-parent/connectivity exclusion, and the existing 13 audited strict-tautomer groups were checked against every inner fit. No additional official rows needed removal beyond the frozen cohort definitions and their existing parent purges.

This does **not** retroactively make the historical native expert perfectly clean. The later strict-reference preparation documented 12 outer-training component rows removed from its corrected version (own: union4 + isoform2; briford: union3 + isoform3), and 62 train-side exclusions across native inner folds. The original expert retains these historical limitations. Its component folds are also different from one another and from the new tabular folds, so the native bank is rowwise OOF rather than one universal shared-fold matrix.

The broader source audit proposed 28 public prepared-row quarantines because the experimental source entity could differ from the retained representation. Those historical associations are not silently recertified here. New TabICL conditioning uses only official primary labels, with no fresh public auxiliary-label objective; the frozen pretrained encoders still have their own incompletely known pretraining overlap.

Accordingly, the experiment asks whether a low-capacity, properly nested addition improves a **fixed historical expert** under the two reused development cohorts. It is not a causal test of data cleaning, a new unbiased benchmark, or independent confirmation of a future leaderboard gain. The 143-molecule overlap between the two outer cohorts is also retained and disclosed.
