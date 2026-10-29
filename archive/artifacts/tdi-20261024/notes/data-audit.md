# TDI data/protocol audit, 2026-10-24

Read-only source audit; no training or paid compute launched by this agent.

## Authoritative sources
- Live HF dataset CSV checked in memory: https://huggingface.co/datasets/openadmet/cyp-challenge-train-test/resolve/main/cyp-challenge-TRAIN_TDI.csv
- SHA256: b458f599a792412292664386e8f18adc5d4a4129d6bd212ae80a60fb9b96bb60, 1,218,524 bytes, 6,145 rows, 36 columns.
- Live FAQ checked: https://huggingface.co/spaces/openadmet/cyp-challenge/raw/main/config.py (lines 373-384).
- Existing equivalent Workbench-normalized CSV: `/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/reference_audit/public_data/tdi.csv`; same shape/class counts, lower-case names, CI suffix differs. Source URL recorded in sibling manifest.json: https://workbench-public-data.s3.us-west-2.amazonaws.com/comp_chem/openadmet/cyp/training/tdi.csv
- Official test: `/Users/adeliyaleleytner/.cache/cyp-inhibition/data/cyp-challenge-TEST-BLINDED.csv`.
- Official regression train: sibling `cyp-challenge-TRAIN_inhibition.csv`.

## Labels and evaluation
| Endpoint | Positive | Negative | Missing | Known |
|---|---:|---:|---:|---:|
| CYP2D6 |324|1173|4648|1497|
| CYP3A4 |764|2820|2561|3584|

4,822 molecules have at least one scored TDI label; 1,323 have neither. Each endpoint positivity is ~21.5%. Missing labels are unknown, never negative. Official output must have all 750 test rows, columns SMILES, Molecule_Name, CYP2D6_is_TDI, CYP3A4_is_TDI, with booleans (not continuous probabilities). Scoring is per-endpoint Matthews correlation then equal macro mean. Constant predictions score zero MCC. Secondary accuracy/precision/recall/F1, 1000 bootstraps in locally vendored reference. Reference code paths relative to main code repo:
- `vendor/reference/validation/tdi_validation.py`
- `vendor/reference/evaluation/config.py`
- `vendor/reference/evaluation/evaluate_predictions.py`

FAQ: positive above reliable direct pIC50=4 with TDI-direct shift>log10(2)≈.301; inferred positive when direct<4 and TDI>4.301; negative above4 when shift fails; assigned negative when both<4. **Use given class labels. They cannot be fully reconstructed from exposed pIC50 columns alone:** 4 CYP2D6 negatives and1,249 CYP3A4 negatives have missing direct pIC50; one3A4 negative lacks TDI pIC50. Another18/159 negatives are low-direct grey-region TDI values[4,4.301]. No contradiction found where all operands and documented categories resolve.

## Structure overlap
RDKit InChIKey first block (connectivity): 6,141 unique train parents /6,145 molecule IDs; zero overlap with official750test parent keys. 4,905 train IDs also occur in regression train (4,901 parents). Four duplicate parent groups, each size2, with no conflicting available labels:
- LOUPRKONTZGTKE: OCNT-0494161, OCNT-1911794
- LEBVLXFERQHONN: OCNT-1965934, OCNT-2328651
- MJIHNNLFOKEZEW: OCNT-2328781, OCNT-2328911
- CBLVEVRERGRBQK: OCNT-2395305, OCNT-2395406

Strict validation should keep these groups together and exclude all labels of held-out structures from any auxiliary/pretrained-on-challenge fit.

## Existing holdouts
IDs from `/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/remote/assets/cohorts.json`, `cohorts.{name}.test_ids`:
| Holdout | CYP2D6 positive/negative/missing | CYP3A4 positive/negative/missing |
|---|---|---|
| own750 |35/115/600|151/364/235|
| briford529 |28/147/354|88/183/258|

These have few2D6 positives; report both endpoints and uncertainty. They were designed for direct inhibition, not a published briford TDI validation protocol.

## Reusable Jeremy code and pitfalls
Main repo `/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023`:
- `vendor/scripts/02_baseline_lgb.py`: ECFP4 2048+all RDKit2D,500trees,lr.05,31leaves,class_weight balanced; Butina5fold.
- `vendor/scripts/03_embed_frozen_encoders.py`: frozen chemprop_medium and chemprop_chemeleon extraction for all6145TDItrain,750test.
- `vendor/scripts/05_run_tabicl_tdi.py`: TabICLClassifier(n_estimators=8,device=cuda,random_state42) on frozen adme_pretrain embeddings, PCA200.
- `vendor/src/cyp_submission/tabular_cv.py`: exact recipe median imputation/scaling/PCA is fitted once to all train inputs **before**CV (transductive covariate preprocessing). Exact reproduce can preserve this, but strict evaluation should fit transforms inside training folds.
- Both LGB andTabICL sources save **hard labels via predict**, not probabilities. Final recipe Caruana combines these hard votes and scans37thresholds [.05,.95]. In `vendor/scripts/07_build_submission.py`, weights/threshold are fitted and scored on the sameOOF labels; its claimedOOF score is selection-optimistic. Evaluate improvement on locked outerholdout with calibration fitted insideoutertrain.
- `vendor/src/cyp_submission/splits.py`: Butina MorganR2/2048 similarity cutoff.6, greedy size balancing,seed42; not Bemis-Murcko scaffold.
- README reports kitOOF MCC.283 versus larger author's ensemble.312; these are source claims, not reproduced scores or currentLB.
- Existing feature cache `OLD/remote/assets/feature_manifest.json` covers5655rows (4905direct+750test) for foundationCheMeleon/MolFormer/Monroe/UniMol; missing1240TDI-only train rows. Do not align caches byrow or assume completeTDIcoverage.
- TDI-arm continuous regression labels are legal auxiliary training tasks, but values for validation/test structures must never be fed as observed features. Existing full-data briford weights sawholdoutauxiliary data and cannot be used as leak-free outerholdout pretrained features.
