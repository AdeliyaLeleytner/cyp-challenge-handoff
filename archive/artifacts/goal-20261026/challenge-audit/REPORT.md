# CYP challenge audit — 26 October 2026

Snapshot: **25 October 2026 22:59:59 UTC / 26 October 01:59:59 Moscow**. Public read-only sources and local prior receipts were inspected. No account changes, training, publication, messages, or submissions were performed.

## Decision-relevant findings

The Direct Inhibition track remains open. Final submissions close **3 November 2026 at 23:59 UTC**, or **4 November at 02:59 Moscow**. The Space is in phase 2. External data and pretrained models are allowed, with proprietary-data disclosure. Submissions are limited to once per 12 hours per track, and the latest valid entry counts. The team should use its existing Hugging Face identity. A method-report URL is required before the deadline for the final board. [Pinned official rules](https://huggingface.co/spaces/openadmet/cyp-challenge/blob/7f3873d820029457d722da25dac088a0d64c9fcf/config.py)

Our incumbent is **AdeliyaLL-CYP**, currently **rank 26/267**, MA-ST-RAE **0.4424575393669513**. Its report field is invalid because a descriptive sentence, rather than a URL, was submitted. This is directly repairable when the next model is submitted; it does not require changing models solely to repair the link. See [full-precision public CSV](sources/live-regression-full-precision.csv) and [repair diagnosis](report-link-repair.json).

The supplied `lachrymator/openadmet-cyp-challenge-public` repository belongs to **stir_bar**, not briford. It explicitly contains a method write-up rather than training code. Its pinned head is `6afb664e6fb22c516952e020273ba91442f426db`, dated 27 September. Its current live entry is0.4435 / rank 29. It describes representation-diverse ensembles, auxiliary pretraining, cluster-disjoint validation and constrained nonnegative stacking, but cannot serve as an exact executable reproduction from the repository alone. [Pinned write-up](https://github.com/lachrymator/openadmet-cyp-challenge-public/blob/6afb664e6fb22c516952e020273ba91442f426db/README.md)

## Current public comparators

| Entry | Live rank | MA-ST-RAE | What is actually available |
|---|---:|---:|---|
| preheat-to-450 |1|0.3415|No linked report; Open Code=No|
| rasayan-labs |8|0.4154|Linked GitHub repository has size0; no contents available; Open Code=No|
| AdeliyaLL-CYP |26|0.4424575394|Our historical native reproduction; report-field repair needed|
| stir_bar |29|0.4435|Write-up/figures, no training code in linked repository|
| briford |58|0.4973151906|Actual public Workbench code; newly updated submission|
| JacksonBurns |61|0.5133|Substantial code repository at linked revision|
| jeremy |65|0.5185|Compact reproduction kit and checkpoints|

There are 17 entries declaring Open Code=Yes and 33 HTTP report links. These flags alone do not establish reproducibility. [Live snapshot](live-regression.csv), [retrieval receipt](sources/leaderboard-retrieval.json), [official board](https://huggingface.co/spaces/openadmet/cyp-challenge).

**Do not substitute briford's latest entry for our frozen historical reference.** His article still describes a four-Chemprop-member flat average and historical0.4378 live score. Current source has additional Tox21 and Monroe/TabICL members and confidence-weighted combination; the latest leaderboard submission at25October20:28UTC scores0.497315. The exact source/weights producing that newer submission are not recoverable from the leaderboard alone. The last commit touching the CYP directory is `873bd9ed872ff89427128f68f210889ffa21ae68` (18October); ensemble-script blob is `a073ef362c219f84b5b1a7f1f203c8ca3fbd667f`. Use the already frozen historical implementation and holdout predictions as the scientific control. [Article](https://supercowpowers.github.io/workbench/blogs/cyp_challenge/), [current pinned ensemble source](https://github.com/SuperCowPowers/workbench/blob/873bd9ed872ff89427128f68f210889ffa21ae68/ml_pipelines/OpenADMET/cyp/scripts/cyp_ensemble_submit.py).

## Evaluation and data contract

The public tutorial/scorer is pinned at `832ae6d6447b07c2c71059de34d07f1130388247`. For each endpoint, ST-RAE divides the summed distance of predictions outside the experimental credible intervals by the same interval-distance error of the constant predictor `mean(y_true)`. There is **no explicit hard clipping at pIC50=4** in this function. The official evaluator uses 1,000 bootstrap resamples, excludes missing ground-truth cells separately by endpoint, and averages the four endpoint metrics per bootstrap sample. MAE, R², Spearman and Kendall are also reported. Point-score and bootstrap-mean results should be distinguished. [Scorer](https://github.com/OpenADMET/CYP-Challenge-Tutorial/blob/832ae6d6447b07c2c71059de34d07f1130388247/evaluation/custom_scoring_functions.py), [evaluation driver](https://github.com/OpenADMET/CYP-Challenge-Tutorial/blob/832ae6d6447b07c2c71059de34d07f1130388247/evaluation/evaluate_predictions.py).

The live board evaluates half the blinded test, with chemisimilar parent series kept together. The interim board is a one-time full-test snapshot for entries received by 24 September; it does not update with our later submissions. No test labels have been released in this stage. [Official announcement](https://openadmet.ghost.io/announcing-openadmets-cyp-inhibition-blind-challenge/).

Dataset revision: `d7eb3c973dca01aad8e33c91c29e5123fd925d8f`, last modified 24 October. Direct train contains 4,905 unique IDs and **byte-matches the pilot's frozen official train**. Blinded test contains 750 unique IDs and only identifiers/SMILES. Train SHA256: `b8f79addd266fb6f9f4c222c5e4e73d926362328b6a8d2841871a54e46bd2278`; test SHA256: `a342f8444a8dcb531ca12f3685293f0bd6c36ae9073f491e44a9bc1cc4b741f9`. [Dataset snapshot](https://huggingface.co/datasets/openadmet/cyp-challenge-train-test/tree/d7eb3c973dca01aad8e33c91c29e5123fd925d8f), [local receipt](sources/dataset-file-receipt.json).

## Submission preflight and link repair

Submit 750 rows with `SMILES`, `Molecule_Name` and these four finite prediction columns:

```
CYP1A2_pIC50_direct_inhibition
CYP2C9_pIC50_direct_inhibition
CYP2D6_pIC50_direct_inhibition
CYP3A4_pIC50_direct_inhibition
```

Use the tutorial validator with the exact expected ID set, plus explicit checks for the official ID-to-SMILES mapping, no duplicate IDs, full finite predictions, and per-endpoint sample standard deviation ≥0.01. The tutorial validator itself does not implement the frontend's near-constant-prediction rejection. Preserve original test order for reproducibility even though scoring joins by ID. [Validator](https://github.com/OpenADMET/CYP-Challenge-Tutorial/blob/832ae6d6447b07c2c71059de34d07f1130388247/validation/activity_validation.py), [Space submission implementation](https://huggingface.co/spaces/openadmet/cyp-challenge/blob/7f3873d820029457d722da25dac088a0d64c9fcf/submission.py), [machine-readable contract](submission-contract.json).

The current public submission endpoint takes 13 arguments. It checks that a supplied HF username exists; it is not an OAuth identity proof. Keep the established identity/alias and disclosure choices rather than inventing new ones. The public API and UI expose no metadata-edit operation. Normal link repair therefore requires a new valid submission containing a reachable `https://` report URL; organizer-mediated correction is another possibility, but no such request was made. Our 24 October 12:11 UTC submission is already outside the 12-hour cooldown.

The incumbent report field is a plain-text description of the historical 18/8/6/1 D-MPNN recipe, five folds, seed42 and published placement.

The exact original, including whitespace, is retained in [report-link-repair.json](report-link-repair.json). `make_tag_clickable` maps this non-URL text to `Invalid link`; the displayed failure is not evidence of a broken hosted page. The new report should describe the actual selected model, source data, frozen holdouts, ADMETlab feature generation and its limitations. Do not point to someone else's method as if it documents our implementation. A received/upload acknowledgement alone is not proof of scored acceptance: verify the eventual leaderboard timestamp and receipt/score, allowing the documented processing window of up to 2 hours.

## ADMETlab feature use

External-model outputs are compatible with the broad external-data/pretrained-model permission; no special pseudolabel prohibition was found in the official rules inspected. This is not proof about undisclosed teacher training membership. Identify these columns as ADMETlab predictions/features, not experimentally measured challenge labels. Disclose the source, generation mode/date, chemical processing and unknown teacher-training overlap. Paid proxy access is not, by itself, proprietary scientific training data; the proprietary-data checkbox should reflect the actual data used. Do not claim the teacher's training data are fully public or leakage-free without evidence.

No new stronger executable recipe was established among the currently better publicly linked entries. Retain the frozen native baseline and compare new feature models on the same complete outer holdouts, reporting all five metrics, while keeping holdout selection and public-test calibration provenance explicit.

## Evidence index

`sources/` holds official Space/config/validator/scorer snapshots, dataset metadata/files, live board responses and GitHub metadata. `source-sha256.json` fingerprints the saved sources. Public endpoint calls used here were leaderboard refresh/download functions only; `submit_predictions` was never called.
