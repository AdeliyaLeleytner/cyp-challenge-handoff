# Private candidate for review — no submission authorized

This candidate preserves the exact original native ensemble that previously scored0.4425, adds the existing frozen H6 LightGBM feature expert, and fits four convex coefficients on the original ensemble's training OOF predictions. It uses the original frozen serving operator. No native model, feature value or calibration parameter was retrained.

## What validation says

| Raw ST-RAE, lower is better | Original native | Anchored mixture |
|---|---:|---:|
| Our750 development holdout |0.626205|0.620861|
| Reconstructed briford529 |0.622655|0.577113|

Our holdout remains mixed: MAE0.524829→0.529889 and R²0.468910→0.454110 worsen, while rank correlations improve slightly. Its ST difference interval includes zero. Briford improves allfive metrics, with a conditional ST difference interval[−0.072880,−0.021151]. These reused, overlapping development cohorts do not establish a blind-score improvement.

The deployed prediction spread becomes narrower in every CYP even with the operator held fixed. That is an explicit risk, not a claim that preserving the old operator guarantees the old calibration remains optimal.

## Exact artifact

Candidate: [750 served predictions](results/incumbent-anchored-H6-served-PRIVATE.csv)

SHA256:6807263f0ccadcb31aa28a5c54653608e12271939a2490a2404d4353aeb0e16d

All750 IDs, exact SMILES and order, finite values, required column structure and minimum prediction spread pass the pinned official validator. Independent arithmetic reconstruction passed. With feature weight zero, the operator reproduces the original incumbent numerically to3.55e−15 and the preserved control file has the exact original349165... hash. No per-row corrections or hidden labels were used.

The candidate's actual leaderboard score is unknown. It is not the direct Chemprop+ADMET P7 experiment and not the last0.4616 submission: the latter changed native checkpoints and used a different serving calibration.

## Possible next action, only after explicit human approval

Upload only this exact prediction file to the LIVE challenge under the existing identity and consent settings, with an empty method-report field and open-code=false. No code, weights, report or new public gist would be published. The leaderboard score/entry would be public, and an accepted submission would use the challenge's12-hour submission window. Fresh endpoint/rule/cooldown checks are required before any dispatch.

The current project instructions prohibit automatic leaderboard dispatch. This document and the CSV are private preparation, not approval. The independent primary-task continuation experiment can proceed whether submission is approved or deferred.

Evidence: ../READOUT.md, ../VERIFICATION.json, VERIFICATION.json and results/{COMPLETE,VALIDATION,LAMBDA0_CONTROL,COEFFICIENTS,SERVING_OPERATOR}.json.

