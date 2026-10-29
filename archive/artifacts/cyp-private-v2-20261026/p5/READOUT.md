# P5 — base replacement changes the feature contrast, without identifying hidden-score causation

ORX node `07f7e391-0bc2-465b-8b91-454cbeb66f03`, run `75f89f21-ec7a-42a3-8943-4d8034d43052`, source `1bb14d1`; local pipeline19.6seconds. This is a fixed historical-artifact replay. No base models, weights or maps were fitted; no paid compute, network, publication or submission.

The design crosses original versus corrected native with feature absence/presence. Each context uses the same saved H6 **pure head** and its previously fitted per-CYP feature coefficients. The absent control is the unattenuated native vector. The controlled served lane applies one original-context affine map and floor to every arm, with the original raw reference mean/scale/offset held fixed. It does not recalculate H6's placement.

| Raw arm | Own750 ST-RAE | Briford529 ST-RAE |
|---|---:|---:|
|Original, feature absent|0.626205|0.622655|
|Original, same feature added|0.619657|0.577447|
|Corrected, feature absent|0.620777|0.642309|
|Corrected, same feature added|0.615706|0.579888|

The large briford feature gain is therefore not solely an artifact of comparing against the weakened corrected baseline: it also appears conditional on the original counterpart. The raw native change without features is−0.005428 on own but+0.019654 on briford. With features it becomes−0.003951 and+0.002441. The briford feature contribution is larger when the corrected base is used; the same fixed feature bank largely attenuates that particular local base difference.

The raw base×feature interaction (difference of feature increments) is+0.001477 on own,95%CI[−0.004216,+0.007075], and−0.017213 on briford,[−0.026206,−0.009664]. These are descriptive paired structural-bootstrap intervals on reused cohorts, not a causal estimate of the strict purge and not a hidden-score decomposition.

All five metrics remain relevant. On own750, adding features to the original base lowers ST-RAE but worsens MAE0.524829→0.529176 and R²0.468910→0.454548; rank correlations improve slightly. On briford, all five point metrics improve on both bases. Preserve these tradeoffs rather than declaring one universal gain.

## Fixed-original-map served lane

| Fixed-map arm | Own750 ST-RAE | Briford529 ST-RAE |
|---|---:|---:|
|Original, feature absent|1.062888|1.069202|
|Original, same feature added|1.003640|0.901887|
|Corrected, feature absent|1.084417|1.088757|
|Corrected, same feature added|1.019220|0.895873|

These large local improvements are **not a demonstrated deployment rescue**. The original map carries blind/live-population assumptions into training-derived, sparsely labeled cohorts; holding it fixed allows the feature blend to change dispersion rather than renormalizing every arm. This differs both from the actually submitted H6 operator and from P1's moment/quantile restoration. Local target-population and scoring-mask mismatch still applies; see [P1's explanation](../p1/READOUT.md). A large gain in this artificial served comparison is not evidence of a large hidden gain.

Controls passed: original/no-feature reproduces the original served anchor, while corrected+feature reproduces saved H6 raw. The original baseline CSVs are byte-identical. Blinded counterfactual vectors are saved **unscored**, and no candidate was selected from their appearance or proximity to the incumbent.

An independent implementation reconstructed all24 vectors, reproduced all point metrics (maximum macro discrepancy2.8e−17) and all500 macro/per-CYP paired CI rows. [Verification certificate](verification/certificate.json). Complete evidence: [all metrics](results/all-metrics.csv), [per-CYP metrics](results/per-cyp-metrics.csv), [paired main effects and interactions](results/paired-contrasts.csv), [fixed coefficients](results/fixed-coefficients.json), [identity controls](results/identity-controls.json), and [ORX identity](EXPERIMENT.json).

The conclusion is narrower than assigning blame: artifact identity is a material control, but the observed local feature gain survives the original counterpart. The unscored corrected-native hidden outcome and the population mismatch still prevent assigning the public0.4425→0.4616 loss to a single factor.
