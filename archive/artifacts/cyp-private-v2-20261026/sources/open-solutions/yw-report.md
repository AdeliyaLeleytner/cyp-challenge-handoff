---
tags:
- chemistry
- openadmet
- cyp-inhibition
---
# yw — OpenADMET CYP direct-inhibition method report

Updated: 2026-10-17T10:49:06.757590+00:00

## Submission

This report describes the latest best-scored public challenge submission under the
anonymous leaderboard alias **yw**. It uses no proprietary training data.

Prediction file SHA-256: `1799926f3d09c069ea9b348d024a2abd72efac544a631cfd78d05410d2adc2b0`.
Model revision: `06e1089342f4ec8297830b103935684e73668812`.

## Data and method

Interval-bound LightGBM champion with a CYP2D6 assay-tagged screen nonhit probability correction

Features: Morgan radius-2 count fingerprints with chirality, RDKit descriptors, a CYP2D6 screen nonhit classifier and separate hit/nonhit L1 response models

Data sources:
- OpenADMET direct-inhibition training data (champion)
- OpenADMET single-concentration log2 fold change under TDI condition
- Local screen-multitask-features champion predictions

Validation: Controller molecule-grouped random, scaffold, test-like direct splits and five-fold screen splits; all screen data from held-out canonical molecules excluded

Compounds were separated before fitting any model component or generating
out-of-fold assay features. Direct, TDI, and screening readouts were treated
as distinct assay observations. CYP2D6 direct measurements are selected
from screening hits, limiting what random-fold direct validation establishes.

## Live leaderboard result

Overall MA-ST-RAE: **0.797**.

| Enzyme | ST-RAE |
| --- | ---: |
| CYP1A2 | 0.887 |
| CYP2C9 | 0.5562 |
| CYP2D6 | 1.172 |
| CYP3A4 | 0.5728 |

The live leaderboard uses a blinded subset. The report will be updated when
the final prediction is selected.
