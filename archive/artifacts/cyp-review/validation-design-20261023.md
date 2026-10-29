# Validation informed by the public test structures

Status: proposed design, not an executed split or a model result. Date: 2026-10-23.

## Available information

Official train: 4,905 molecules, sparse direct-inhibition labels. Counted from the downloaded CSV: 3,596 molecules have one measured CYP, 1,039 have two, 229 have three, and only 41 have all four. Test: 750 publicly available structures, hidden experimental answers. Primary dataset and tutorial copies are in `sources/`.

The official tutorial describes ECFP4 Tanimoto comparison of test structures with training structures. Its reported similarity distribution has not been independently recalculated in this project. Original parent identities have not been established.

## Objective

Construct a local validation set whose structural relationship to its remaining training set approximates the relationship of the competition test to the full official training set. Use test structures, never hidden outcomes or leaderboard feedback, to define this relationship. Matching structure does not guarantee matching the test's activity distribution or selection process.

## Procedure

1. Standardize structures using a recorded, consistent policy. Keep original identifiers, stereochemistry and source provenance. Group duplicate molecular identities so they cannot cross folds. Calculate one fixed fingerprint representation for all structures.
2. For each test molecule and each CYP, measure similarities to training molecules with an observed label for that CYP. Record the nearest and several nearest similarities, local neighbor counts, and broad molecular descriptors. Record structure coverage from auxiliary-only molecules separately from direct target-label coverage.
3. Form several candidate train/validation partitions of official training molecules. Approximately 80/20 is a starting point, not an invariant. Candidate mechanisms can combine within-series holdout and whole-group holdout. Do not require identifying the original 75 parents or imposing exactly 10 validation molecules per inferred parent.
4. For each candidate, recalculate validation-to-remaining-training similarities separately for each CYP. Remove the entire validation molecule from all supervised training targets. A molecule with only one observed CYP contributes a scored validation example only for that CYP.
5. Compare each candidate's structural coverage profiles with the reference test-to-full-training profiles. Prefer close profiles while retaining enough observed validation labels per endpoint and representation across chemical regions. Specify this comparison before any model scores are inspected. Do not select a split because it produces favorable model performance. Do not choose validation activity values to imitate an assumed hidden-test activity distribution.
6. Freeze a small number of repeat partitions with the same selection criteria; evaluate every model on the same partitions with official per-endpoint and macro ST-RAE. Keep a whole-cluster holdout as a separate stress test rather than averaging two different evaluation questions into an unexplained single score.
7. If external data or auxiliary tasks are added, enforce molecular-identity exclusions for the validation compounds across these supervised sources. Reassess reference label coverage if the final training pool materially changes. Unlabeled pretraining exposure is a separate provenance question, not equivalent to supervised leakage.

## Interpretation boundaries

- Full train and each fold's smaller training pool differ. Recomputing neighbors after holdout is mandatory; inability to reproduce the full-pool profile is a limitation to report, not conceal.
- Nearest-neighbor similarity alone is insufficient: two compounds can have the same nearest similarity while occupying different chemical regions or having different local coverage.
- The dense hidden test cannot be fully replicated using the 41 complete-label training molecules. Keep per-endpoint masks and report the missing-label/selection limitation.
- This split design can make local comparisons more relevant; it cannot establish an unbiased numerical estimate of the final leaderboard score under unknown test labels and experimental selection effects.
- No split, model, public submission, or paid compute has been executed for this design.

## Advisory assessment

Consultation `20261023T143545Z-485e776e` completed with wrapper exit 0 and a substantive structured response. Actual primary model `claude-opus-5`, automatic fallback from requested Fable. Retained recommendations: use structure-based coverage profiles, remove validation molecules from all supervised auxiliary sources, freeze splits before model comparisons, pool sufficient molecules for official per-endpoint ST-RAE, and avoid interpreting local scores as guaranteed leaderboard values.

Codex independently inspected the official tutorial and scorer and counted training label coverage. The advisor's mandatory whole-cluster split, expected exactly ~75 structural clusters, inferred seed membership from identifiers, and claimed effective sample size near 75 are not adopted: these are not established by the available evidence. Purchase-parent groups need not coincide with clusters under a chosen fingerprint/threshold. Both within-series and whole-group candidate splits remain possible, selected by measured coverage rather than their names. Test interval widths and potency distributions are hidden; they cannot be matched from structures alone. No arbitrary similarity cap or numerical calibration threshold is prescribed. Per-bin ST-RAE ratios must not be averaged as though they were the official pooled ratio; bin analyses are diagnostics.
