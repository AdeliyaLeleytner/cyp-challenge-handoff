# TDI validation and reuse audit

Read-only audit, 2026-10-24. No source changes, paid jobs, or submissions made by this audit.

## Verified available labels and splits

Source: `/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/remote/assets/reference/public_data/tdi.csv`; 6,145 molecules. This is the existing snapshot; root should compare its checksum and schema with the current official TDI release before training.

| Population | CYP2D6 positive / negative / missing | CYP3A4 positive / negative / missing |
|---|---:|---:|
| All 6,145 | 324 / 1,173 / 4,648 | 764 / 2,820 / 2,561 |
| own750 | 35 / 115 / 600 | 151 / 364 / 235 |
| briford529 | 28 / 147 / 354 | 88 / 183 / 258 |

The existing `cohorts.json` outer ID lists are usable for TDI comparisons, but their training IDs and inner folds are based on the 4,905-row direct-inhibition pool. There are **1,240 additional TDI rows**: 1,238 have negative CYP3A4 labels and two have negative CYP2D6 labels. Using the old training IDs verbatim would silently discard these observations and substantially change class balance. Keep frozen outer IDs, construct the TDI development pool from all 6,145 rows minus the outer exclusions, and create new training-only folds. These counts were calculated directly with CSV parsing, not inferred from prior prose.

The old own750 and briford529 are inherited direct-inhibition holdouts, not yet evidence that they reproduce any published TDI author's exact validation design. Label them accurately. Root's solution audit should establish any additional author's exact holdout if available. They overlap and must not be described as independent replications.

## Reusable code and limitations

Repository: `/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023`.

- `night/features.py` has deterministic Morgan, feature-Morgan, atom-pair, torsion, path fingerprints and RDKit descriptors; ID-aligned precomputed matrices require hashes. Reuse directly.
- `night/tabular.py` has train-only imputation/scaling/PCA and masked per-target fits, but accepts only direct-inhibition targets and instantiates regressors. Add an explicit TDI classifier implementation, not renamed continuous outputs by accident.
- `night/neural.py` has CheMeleon weight hash verification, graph caching, checkpoint persistence, seed/epoch logging and masked regression training. It scales targets and instantiates `RegressionFFN`: binary TDI requires a classification head, binary loss, no regression target scaling, and preserved NaN masks. Check the installed Chemprop API for probabilities versus logits before thresholds.
- `night/cohorts.py:10-47` provides frozen IDs, Murcko scaffold groups and normalized-parent purging, but is tied to the direct dataset and balances fold row counts, not binary class counts.
- `night/briford_holdouts.py:28-58` has the strongest existing exclusion pattern: remove outer IDs, normalized parent keys, and connectivity InChIKey from every auxiliary source. Extend that to all supervised pretraining stages as well as final TDI fit.
- Existing full-data briford models are **not leakage-safe frozen feature encoders for either outer holdout**: they saw these molecular identities and some TDI-condition/direct/single-concentration labels. Fine-tuning does not erase this. Generic external CheMeleon weights are a clean default; the 40 old holdout-specific models are eligible only for their matching outer split, whose identities were purged.

## Minimal evaluation contract

1. Pin exact official TDI data, target names, official scorer, class interpretation and submission schema. Do not derive binary labels from pIC50 when official `is_tdi` labels exist. Missing means unknown, never negative. Map textual `True`/`False` explicitly (Python `bool('False')` is true).
2. Freeze outer IDs before running TDI models. Remove all held-out molecular identities, normalized parents and connectivity matches from every supervised source, including direct-inhibition and TDI-condition auxiliary tasks. Preserve an exclusion audit for each data stage. All split assignment and preprocessing must be deterministic and recorded.
3. On each outer training pool, construct five scaffold/identity-grouped inner folds with approximate balance of the two tasks' observed positives and negatives. Check that both classes are present in every training and validation fold. Identity grouping must be consistent across target/source rows. Acyclic molecules sharing an empty Murcko scaffold must not be accidentally treated as unrelated duplicates; record handling.
4. Obtain out-of-fold **probabilities** for each declared model and each observed task. Choose model hyperparameters, mixture weights and one threshold per target using only training-side OOF labels. For a simple fixed ensemble, average probabilities and then select thresholds; do not average already thresholded labels unless explicitly reproducing that recipe.
5. Optimize each threshold over the distinct OOF score cut points with deterministic tie handling; save the threshold, comparison direction, OOF confusion matrix and score. Baseline report also includes threshold 0.5. Model/threshold selection on OOF makes that OOF score a development score, not an unbiased final performance estimate.
6. Freeze the chosen recipe and thresholds before reading outer outcomes. Score only known labels separately for CYP2D6 and CYP3A4 with the official implementation, then arithmetic mean of the two MCCs if confirmed by scorer. Include TP/TN/FP/FN, counts, positive prediction rate, ROC-AUC and average precision as diagnostics. Do not pool two tasks' confusion matrices as a replacement for macro-MCC.
7. Run exactly the same published baseline and candidate under this contract. Evaluate frozen candidates on both inherited outer cohorts; report the actual deltas and opposite target-level trends. A useful uncertainty interval can be estimated by paired resampling of molecule/scaffold groups, but no arbitrary significance gate is needed. Never choose new thresholds or ensemble weights from these holdout outcomes.
8. Select a submission candidate according to the declared local comparison, without claiming public improvement in advance. Retrain its recipe on full TDI training data, generate fresh full-training OOF probabilities for final threshold selection, then predict actual TEST. This preserves the evaluation procedure rather than copying outer-holdout-fitted thresholds. Public-board feedback must be recorded separately and cannot retroactively become holdout evidence.

A cheap strong first batch is fingerprint RandomForest/ExtraTrees and gradient boosting, plus masked two-task Chemprop and CheMeleon. Main controlled additions are auxiliary direct/TDI-condition heads and their predicted difference, only with split-safe labels/features. Experimental TDI-condition values cannot be used as test input unless the challenge actually releases them at prediction time. If predicting those values as features, training features must also be OOF; in-sample predictions would produce a train/test mismatch and potential leakage.

## Submission transport audit

`night/submit_candidate.py` supplies useful immutable intent/CSV hashing, exact ID/SMILES alignment, file locking, one-attempt receipts and no retries after ambiguous dispatch. It is **not** a generic TDI sender:

- `TARGETS` and `_validate_csv` enforce four pIC50 columns, six total columns and near-nonconstant continuous predictions.
- `_check_gate` is ST-RAE/regression-specific.
- `send_prepared` writes `track='regression'` at line 300.
- `_guard_ledger` lines 267-282 scans every attempt without track filtering, despite its per-track cooldown message.

Implement a TDI-specific wrapper/validator and a distinct TDI ledger, or make track an explicit validated parameter and filter ledger reconciliation/cooldown by track. Do not send through the direct-regression manifest unchanged. Verify current API schema and official output encoding at point of use. Keep exact model tag + timestamp + alias when matching a new TDI leaderboard record. The direct-track `.44246` must never reconcile a TDI attempt.

## Provenance note

Memory was consulted only to locate the established CYP project and earlier leakage-aware validation guidance (`MEMORY.md:166-169,221-222`, rollout `01a1638b-3184-7551-9f97-c9cbe330c7c9`). All concrete code and data counts above were inspected in this audit.
