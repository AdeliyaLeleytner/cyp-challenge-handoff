# Experiments and Decisions

The values below come from preserved runs, not retraining during this handoff. Lower ST-RAE is better; higher TDI MCC is better.

| Direction | Result or decision | Evidence under `archive/artifacts/` |
|---|---|---|
| Native reproduction | Best preserved submission: 0.4424575; 20 models, four task sets × five folds | `briford-native-reproduction-20261024/REPORT_RU.md`; `cyp-private-v2-20261026/p11/evidence/native-csv.csv` |
| CheMeleon, early ensembles, reciprocal comparisons | Earlier baselines and comparisons; retain their identities separately from the later native reference | `chemeleon-baseline-20261023/`, `reciprocal-comparison-20261023/`, `overnight-autoresearch-20261023/` |
| H6 | Raw own750 ST-RAE: 0.615706 vs corrected-native 0.620777; briford529: 0.579888 vs 0.642309. Leaderboard worsened to 0.4616 | `goal-20261026/submission-preparation/MODEL_REPORT_FINAL_LOCAL.md`; `goal-20261026/submission-publication/README.md` |
| H7 | Not promoted; preserved alternative simplex branch | `goal-20261026/h7-simplex/` |
| P1/P2 | Serving-map replay did not consistently rescue performance; local cohorts differ from the dense blinded-query geometry | `cyp-private-v2-20261026/p1/`, `p2/` |
| P3 | MAE/uniform: 0.656206; interval/uniform: 0.661896; MAE/CI: 0.700939; interval/CI: 0.701533 | `cyp-private-v2-20261026/p3/RESULTS.md` |
| P4/P6 | Assay-context/censoring and direct/active-condition audits; limited comparability and descriptive conclusions | `cyp-private-v2-20261026/p4-data/REPORT.md`; `p6/RESULTS.md` |
| P5/P5b | Separated native-base and feature contributions; the anchored candidate still worsened the leaderboard score to 0.4679 | `cyp-private-v2-20261026/p5b/candidate/READOUT.md` and dispatch receipt |
| P7 | Direct ADMET120 fusion: OOF ST-RAE 0.674456 → 0.702571; all five macro metrics worsened | `cyp-private-v2-20261026/p7/RESULTS.md` |
| P7D | Inference-only checkpoint diagnosis measures dependence under an input shift, not established causality | `cyp-private-v2-20261026/p7/diagnosis/DIAGNOSIS_SYNTHESIS.md` |
| P7R | Fresh control: 0.672018; original fusion: 0.715618; masked: 0.712342; repaired: 0.707574. Repair did not close the gap | `cyp-private-v2-20261026/p7r/RESULTS.md` |
| P8a/P8b/P8c | Training-only observation maps prepared; P8c graph condition-routing trial deferred in favor of P7R | `cyp-private-v2-20261026/p8a/`, `p8b/`, `p8c/` |
| P9 | Atom-JEPA/ADME banks, standalone readouts, and nested ensembles: small, heterogeneous effects; no promotion | `cyp-private-v2-20261026/p9-tabicl/READOUT.md`, `p9-source-bundle/READOUT.md`, `p9-nested/READOUT.md` |
| P10 | Continuation with all18 vs primary4: zero controls approximately 0.6586/0.6577; repaired fusion approximately 0.7074/0.7092. No rescue established by this contrast | `cyp-private-v2-20261026/p10/readout/READOUT.json` |
| P11 | Validation/calibration audit; provisional own750 raw MAE proxy; no new base-model training | `cyp-private-v2-20261026/p11/VALIDATION_PROTOCOL.json` and `report.html` |
| TDI | Jeremy baseline MCC: 0.300550 / 0.262583 across the two cohorts. No candidate improved both; no submission | `tdi-20261024/REPORT.md`; `validation-final.json` |

The P7, P7R, and P10 controls belong to different frozen runs and must not be pooled as a single paired comparison. Scaffold-bootstrap intervals condition on saved predictions and do not cover all model-selection or training-seed uncertainty.

The P9 post-final-normalization/PCA96 branch is not equivalent to the published pre-normalization/PCA128 route. A separate source-fidelity audit documents this distinction. A negative result for one branch does not establish that the representation can never help.
