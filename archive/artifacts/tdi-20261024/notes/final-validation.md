# Independent final TDI validation

Checked 2026-10-24T15:42:58.084916+00:00. Read saved class predictions by Molecule_Name, masked missing official labels, recomputed integer confusion matrices and MCC independently; confirmed against sklearn. Campaign evaluator was not imported.

All available reported MCC values reproduced within 1e-12. Exact values, confusion counts, source hashes and prediction paths are in `validation-final.json`. Saved prediction locks (or native Hauser completion hashes plus class equality) also matched.

| Recipe / stage | own750 CYP2D6 | own750 CYP3A4 | own750 macro | briford529 CYP2D6 | briford529 CYP3A4 | briford529 macro |
|---|---:|---:|---:|---:|---:|---:|
| Jeremy native seed42 | 0.258846390 | 0.342254500 | 0.300550445 | 0.182523632 | 0.342642941 | 0.262583287 |
| Jeremy two-seed reference | 0.150826681 | 0.362855687 | 0.256841184 | 0.149539028 | 0.334211209 | 0.241875119 |
| Hauser native | 0.049968521 | 0.319791200 | 0.184879861 | 0.251232063 | 0.247403969 | 0.249318016 |
| baseline candidate | 0.258846390 | 0.392480158 | 0.325663274 | 0.099717465 | 0.365794843 | 0.232756154 |
| candidate candidate | 0.121636899 | 0.376938215 | 0.249287557 | 0.216028602 | 0.299462884 | 0.257745743 |
| fixed_soft candidate | 0.218521287 | 0.391532339 | 0.305026813 | 0.199712707 | 0.309957478 | 0.254835092 |
| gnn candidate | 0.121636899 | 0.376938215 | 0.249287557 | 0.216028602 | 0.299462884 | 0.257745743 |
| gnn_standalone candidate | 0.074245899 | 0.168295983 | 0.121270941 | 0.066610040 | 0.163133562 | 0.114871801 |
| assay_stack candidate | 0.060088984 | 0.342254500 | 0.201171742 | 0.065492104 | 0.342642941 | 0.204067523 |

## Interpretation

No candidate qualifies on both frozen holdouts at this snapshot: True. This is a statement about the declared submission comparison, not a claim that every new method is uniformly worse.

All requested stages, including assay_stack, are now independently checked. No submission qualifies.

Label counts: own750: CYP2D6 150 observed /35positive, CYP3A4 515 /151positive. briford529: CYP2D6 175 /28positive, CYP3A4 271 /88positive.

- Inherited own750/briford529 holdouts have been reused to decide additional campaign stages. They are not a fresh untouched confirmation of the whole adaptive search.
- Outer holdouts overlap by 143 molecules; their results are correlated.
- CYP2D6 has only35positive labels in own750 and28in briford529, so individual mistakes have a substantial effect.
- Training OOF thresholds/ensembles are fitted calibration scores, not independent validation.
- No public leaderboard claim is implied by these local results.
- Pending stages not scored until actual saved predictions are available.

Final E5 verification at 2026-10-24T15:45:41.274470+00:00: all MCC values, IDs/order and four lock hashes passed; no mismatch. CYP3A4 calls are exactly the native seed42 baseline. E5 stacking CV is not strictly nested, as native assay-model OOF folds differ from TDI folds and use validation assays for early stopping; outer identity purging remains the relevant independent boundary.
