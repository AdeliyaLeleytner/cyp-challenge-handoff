# P1 — operator sensitivity measured; no hidden-score rescue established

ORX node `732b1d76-e80b-4d41-88f0-6450b2081b0d`, run `9e74bd11-c97c-4dc1-828c-a438f4ce953f`, source `b55a9e8`; local pipeline33.7seconds. All operators were frozen before scoring. No model, coefficient or map parameter was fitted to target values. No paid compute, network, publication or submission.

The exact original incumbent is the anchor. The primary experiment applies identity, moment and fixed tie-aware empirical-quantile maps to **served inputs**, anchoring to the original served vector in the same context. The secondary experiment does the same with raw inputs. The54 output vectors include unscored blinded variants. All18 original→original controls are byte-identical to their source CSVs, including349165 for the original blinded served output.

| Input lane / H6 operator | Own750 ST-RAE | Briford529 ST-RAE |
|---|---:|---:|
| Served identity |1.102332|1.059550|
| Served moment |1.089937|1.032411|
| Served quantile |1.079792|1.034925|
| Original served anchor |1.062888|1.069202|
| Raw identity |0.615706|0.579888|
| Raw moment |0.620080|0.602826|
| Raw quantile |0.617813|0.604089|

Anchoring improves the H6 served diagnostic in both cohorts but does not beat the original anchor on own750. The same maps worsen H6 raw ST-RAE in both cohorts. This operator-dependent reversal is a sensitivity result, not evidence that a map improves hidden performance. Moment maps introduce no new ranking information; quantile maps preserve candidate ordering subject to their declared ties. No additional map tuning was performed.

## Why served ST-RAE is around1.1 while raw is around0.6

The inherited calibration source is `vendor/briford_native/cyp_recalibrate.py`, SHA `7f8834425973369531cb21805fe54c966e72e47a5c764c49395a1d7dc7a9aec6`. Its constants describe the author's inferred **live-half** population, not these local training-derived cohorts:

| Endpoint | Destination mean | Dispersion rule |
|---|---:|---|
|CYP1A2|4.412|OOF Pearson ×1.32 ×1.553|
|CYP2C9|4.830|OOF Pearson ×1.23 ×1.101|
|CYP2D6|3.570|Fixed sampleSD0.900 ST-RAE override; base blind-moment3.107/1.599 is not used for this lane|
|CYP3A4|4.880|OOF Pearson ×1.07 ×1.272|

The map centers/scales **all query predictions** and then floors at1. Local scores instead use a sparse, target-dependent subset with different activity/interval distributions. Therefore comparing a destination mean directly with the local observed-label mean is insufficient; the scored-subset prediction mean must also be inspected.

For example, original own750 CYP3A4 has observed truth mean4.191 and raw scored prediction mean4.148, but served scored mean4.770; MAE rises0.436→0.711. Original own2D6 MAE rises0.538→0.909; its overall served mean is3.57, while its scored-subset served mean is4.557 against truth4.768. Both shifts and spread/mask interactions matter. Exact measurements for both original/H6 are in [serving-vs-local-population.csv](serving-vs-local-population.csv), and constants/scope are in [calibration-constants-and-scope.json](calibration-constants-and-scope.json).

Thus this is an **exact replay of the operator but a population-mismatched local assessment**. Its absolute served macro is not a faithful estimate of deployment performance. Even paired signs can depend on that mismatch. Conversely, raw improvements did not validate the chosen served pipeline. Matching the full750 blinded distribution also does not ensure matching its unknown series-split scored half. Neither calibration-only causation nor a hidden-score improvement is established.

## Paired evidence and verification

Relative to H6 served identity, moment-map ST deltas are−0.012394 (own;95%CI[−0.015622,−0.009979]) and−0.027139 (briford;[−0.034759,−0.021097]). Quantile deltas are−0.022540 and−0.024625. These remain descriptive conditional bootstrap intervals on reused cohorts, without selection correction.

All five macro and per-CYP metrics are in [results/all-metrics.csv](results/all-metrics.csv) and [results/per-cyp-metrics.csv](results/per-cyp-metrics.csv). Paired macro intervals include comparisons to both original identity and the same candidate's identity operator. The requested original→H6 and mapping-increment per-CYP intervals are in [verification/H6-paired-per-cyp-bootstrap.csv](verification/H6-paired-per-cyp-bootstrap.csv),400 rows. An independent implementation reconstructed all54 vectors, reproduced every point score (maximum macro discrepancy0), all18 exact controls and H6 macro intervals. [Verification certificate](verification/certificate.json).
