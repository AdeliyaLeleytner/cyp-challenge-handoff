# H7 completed: the extra expert did not resolve the cohort tradeoff

H7 does not warrant automatic promotion over the simpler H6 global blend on the primary ST-RAE evidence. On own750 it assigns zero weight to the primary ADMET120-only LightGBM expert, exactly reproducing the H6 native/ADME720 mixture. On briford529 it assigns that expert a small positive weight, but raw ST-RAE is slightly worse than H6. Against the original primary ADMET120/native blend, all five own750 point metrics worsen while all five briford529 point metrics improve. This is the mixed result the bounded experiment was designed to expose; no additional model search was started.

Experiment `cf0d2eb8-e0a3-4d0a-87d7-90adc8351878`, run `91b8e4ae-48f9-48e6-91d1-08d1937b280e`, frozen source `e533fd9259bc4e6766ce6f1b8dcfe8f6b29853dc`. The local run took 11.24 seconds of pipeline time, about 15 seconds overall. No base models, GPU rentals, final refit or submission were added.

## Raw diagnostic results

|Cohort / procedure|ST-RAE↓|MAE↓|R²↑|Spearman↑|Kendall↑|
|---|---:|---:|---:|---:|---:|
|own750 / native|0.620777|0.523427|0.470486|0.673245|0.495502|
|own750 / primary_global|0.613328|0.527423|0.465871|0.677346|0.498215|
|own750 / h7_simplex|0.617911|0.530050|0.455354|0.671692|0.493247|
|own750 / H6 global|0.617911|0.530050|0.455354|0.671692|0.493247|
|briford529 / native|0.642309|0.475777|0.384635|0.653092|0.477189|
|briford529 / primary_global|0.598232|0.465544|0.410188|0.660476|0.482656|
|briford529 / h7_simplex|0.579055|0.460659|0.418212|0.670982|0.493175|
|briford529 / H6 global|0.578549|0.460474|0.418409|0.672234|0.494477|

Expert order is native / primary ADMET120 LightGBM / H6 ADME720 LightGBM. The fitted global weights are:

- own750: **0.556841 / 0 / 0.443159**.
- briford529: **0.587253 / 0.059642 / 0.353105**.

Each vector is shared across all four CYPs and was fitted using only that cohort's outer-training OOF predictions, observed targets and confidence bounds. Base hyperparameters were the existing inner-OOF-selected settings. No outer labels fitted weights. Nevertheless these cohorts have already influenced model development: they are reused diagnostics, share 143 molecules, and briford529 is reconstructed rather than author-certified. The result is not an unbiased estimate after model selection.

## Paired uncertainty and contrary metrics

H7 minus primary-global raw ST-RAE:

- own750: **+0.004582**, paired scaffold95% interval **[−0.005354,+0.014523]**.
- briford529: **−0.019176**, interval **[−0.029971,−0.009652]**.

Own750 R² also worsens against primary-global, with interval [−0.019033,−0.001360]. All five briford529 intervals against primary-global point toward improvement and exclude zero in this conditional bootstrap. These are exploratory intervals conditional on the fitted predictions, without selection or multiplicity correction; they do not make the two reused cohorts independent confirmation.

Against native, H7 lowers ST-RAE on both point estimates, but own750's interval includes zero and its other four point metrics worsen. Relative to H6 global, own750 ST-RAE is equal and briford529 increases from 0.578549 to 0.579055. The extra expert therefore does not deliver the intended primary-metric tradeoff improvement.

## Placement is a separate lane

H7's published-placement diagnostic ST-RAE is **1.110775 / 1.065006**, versus native's **1.058445 / 1.087466** and primary-global's **1.075741 / 1.097408**. Placement worsens the own750 comparison but improves briford529. These published leaderboard-derived constants are not independently calibrated hidden-test evidence. Both raw and placed vectors are retained without choosing a lane by these diagnostics.

## Verification

Nine focused tests passed: two-expert LP parity with the weighted-median optimizer, interval-valued optima, simplex bounds/sum, tied experts, no intercept, missing labels, invalid observed values/bounds and exact ID/SMILES alignment. Real-data two-expert LP objective parity also passed for both cohorts.

[Independent verification](verification/certificate.json) checked 19 direct input pins, 37 inherited snapshot/reference pins and seven embedding pins; all 12 outer prediction files, six training-OOF files and 300 outer metric cells; the reconstruction of every saved mixture; both training objectives; and all 20 paired-bootstrap intervals. Macro rescore discrepancy was exactly zero. All 1,000 bootstrap samples per comparison were valid. Verification performed no new optimization.

Inputs and outputs remain at [results](results). The reproducible independent checker is [verify.py](verify.py), and the tested LP is [worktree/night/simplex_strae.py](worktree/night/simplex_strae.py). The unchanged primary and H6 results remain available for the parent's final development-based recipe choice. Full 32,421-outcome acquisition and audit still gate feature final fitting and submission.
