# Briford historical recipe re-execution

User request: reproduce briford as closely as possible and approach its leaderboard score. Native algorithm execution uses the original published four-member18/8/6/1-head recipe, not the previous train-only adaptation. No score is promised.

| Step | Current execution |
|---|---|
| Data | Native cyp_aux_features.py and cyp_union_features.py; local storage adapters preserve the pandas operations and source row order. Native InChIKey connectivity joining, public overlaps and Veith clipping are retained. |
| Members | union18:31670rows; mtaux8:4905; CYP2D6 six-head:23264; CYP2D6 single-head:1493. |
| Splits | Native get_split_indices on each member's own complete trainable pool, five scaffold folds,seed42. |
| Loss weights | Unchanged native model scripts calculate global task weights before folds. |
| Training | Native train_chemprop_fold and build_mpnn_model,400maxepochs,40patience, batch64, hidden700,depth5,dropout.1, MAE; original best-validation checkpoint. |
| Inference | Native fp32 predict_ensemble helper; average five fold models. |
| Model ensemble | Native flat mean of two members for1A2/2C9/3A4 and four for2D6. No second initialization seed, learned stack or TRAIN-only affine calibration. |
| Placement | Native oof_pearson from common labelled IDs, published OOF_TO_BLIND multipliers, place(strae=True), recalibrate includingfloor1.0. |
| Submission | One explicit upload of verified real-model CSV, same account/ledger as previous attempt, no earlier than2026-10-24T12:10:10UTC (15:10Moscow). |

Source hashes and revisions: sources/native-source-manifest.json. The18-head model script is pinned to971f6a7; other functions8c72c75. Later same-name union-model files already declare26heads despite stale18-head docstrings; they are not substituted for the documented0.4378recipe.

Preparation succeeded in ORXrun3f276a29-e9f5-4ab9-9362-52cfca2793cb, commitb230a63. A synthetic storage-adapter test also exercised the native averaging, OOF retrieval, placement, flooring and official validator. Its outputs live only in synthetic_adapter_test and are never eligible for submission.

Limits: historical ChEMBL/PubChem object bytes, original cloud FeatureSet row order, original trained checkpoints/OOF and original environment lock are not available. Public objects have later Last-Modified timestamps, which does not itself prove content changed. The native union count matches the documented31670. Exact byte/score reproduction cannot be certified. This is native-recipe re-execution on the available pinned assets, with these limits retained in final provenance.

Native joining retains one public Veith connectivity group overlapping actual TEST. This is a public historical auxiliary readout, not a hidden challenge label. Its identity is recorded in prepared/native_overlap_audit.json; no silent purge changes the requested recipe.

Operational adaptations: local files replace Workbench cloud transport; unused descriptor generation/UQ/SHAP are omitted from this SMILES-only mean-prediction path. Independent folds run in parallel with2dataloaderworkers and4torchthreads per worker. Native modelling functions remain unchanged.

Compute: initial two8RTX3090leases57495501/57496050failed provider bootstrap DNS and were destroyed before any data upload/model fit. Replacement57496410is4RTX3090 inFinland at1.19556USD/h. Guard reserve1.50USD,3hdeadline, per-completed-fold export; do not touch unrelated instance55892464. Prior standing Vast spending authorization remains in force; no top-up or payment-method changes.
