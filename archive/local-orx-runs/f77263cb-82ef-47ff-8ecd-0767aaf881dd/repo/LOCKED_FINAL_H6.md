# Locked final H6 executor — provisional, not run

Node`b64f3a0f-3bb5-4e17-95c1-3fff9342a6a9` is a new child of the optional bridge, preserving the original CPU/TabPFN/H7 branches. Its fixed command remains`bash run.sh`, now entering`night.locked_h6_final`. Only`lightgbm__adme720` with the two evaluated H6 settings and per-target native blending is allowed. The parent decision is copied unchanged in`FINAL_RECIPE_DECISION.json`. No further family/mode selection, TabPFN, H7, intercept or additional grid is permitted.

## Exact execution

1. Check the H6 CPU package versions: NumPy2.5.4, pandas3.1.0, scikit-learn1.9.1, LightGBM4.6.0, RDKit2026.9.1, PyTorch2.8.0, Chemprop2.2.1. This is deliberately distinct from the encoder's historical GPU environment.
2. Validate the full32,421 terminal-outcome snapshot, new Cl/N/Sb/proton-transfer outcome policy, complete chemical/eligibility audit, all5,655 finite approved official inputs, fixed full-training folds, and actual native8421 companion. Null inputs/approvals still block fitting. The approved output-policy SHA is`81baaa7f…`; old proofs remain unchanged. No unreviewed exception is accepted.
3. Build720 features from the original4,905-row ADME cache (`e0216aea…`) plus120 sorted ADMET columns. The checked750-row blind bank (`43b136e8…`) supplies query embeddings only. The replayed training canary (`29b498e…`) is never a model input.
4. Generate full official fivefold OOF for the two existing H6 settings:40 endpoint fits. Choose one setting by macro ST-RAE, then fit four convex native/readout weights using the existing exact interval-distance optimizer. Always retain the declared per-CYP blend, including boundary weights0/1.
5. Refit the selected LightGBM setting once on all observed labels per CYP:four heads. Save each head, its fitted median imputer, full feature order, context/parameter hashes and native-blend weights. Reload each saved head and verify exactly identical750 raw head predictions without another fit. Reconstruct the raw blend from saved-head vectors and the pinned native vector, checking equality.
6. Apply the already locked published-placement function/constants; retain raw predictions and adverse placed diagnostics separately. Validate exact750 IDs/SMILES/order, finiteness and spread with the official validator. No report publication or leaderboard upload occurs inside this node.

## Serialization-only learning adapter

`night/admet_full_models.py` gains optional access to the already fitted preprocessor and optional persistence. Its learner constructor, target masks, median fitting, lack of scaling for LightGBM, seed, grid and training/prediction operations are unchanged. CV uses the original path. Final heads are persisted by`night/final_model_artifacts.py`; a context-identical existing saved head is reloaded rather than refit. A partial/mismatched model artifact blocks reuse.

Outputs under`final-models/<CYP>/` include`head.joblib`, portable`booster.txt`, `feature-order.json`, `query-predictions.npy` and a verification receipt. `final-models/manifest.json` binds all four heads, per-CYP blend weights, exact raw reconstruction and source selection. Native checkpoints remain in their separately verified companion archive. Model artifacts are private; the public report contains method/provenance/aggregate metrics, not private paths or weights.

## Inputs already verified without fitting

- Native companion certificate`94ab1407…`, run`91132654…`, source`ed1ab383…`:final reader matched4,905 OOF/750 query rows and reproduced native placed vectors to max2.66e-15.
- Blind bank from verified frozen-encoder run`f9a8d969…`, source`c2cad808…`:750×600 float32, finite, original IDs/SMILES/request order. Full4,905-row replay passed fixed1e-5 tolerances, maxdifference5.96e-08. Final feature construction independently checked that the training600-prefix remains exactly the original cached values.
- Final full-data folds SHA`cc471dcf…`:five981-row validation folds, four total training-side removals. Native component folds are different and only their rowwise OOF vectors are aligned.

## Remaining launch requirements

The final recipe, native vectors, blind bank and updated exact exception policy are ready. Complete32,421 raw/numeric/outcome/eligibility audit, immutable final snapshot and full-goal approval must still be pinned by root. `training_enabled=false`; both manifest pins remain null. Root will commit the pins/enabling flag and launch through ORX only after these gates pass. This preparation performs no final model fit or inference, no spending, publication or submission.

`MODEL_REPORT_DRAFT.md` and sanitized macro/per-CYP metric tables in the parent folder now describe the actual selected method and preserve its adverse/mixed results. Final setting/weights/hashes must come from the eventual run before publication.

Pinning utility: `tools/pin_locked_final_inputs.py --snapshot <completed-schema2-manifest> --final-manifest <completed-final-companion-manifest> [--enable]` validates every gate before writing the config, and never launches training. The parent must commit the resulting exact pins/config before the ORX run. Do not use the inherited older evaluation snapshot-pinning script for this final node.

Final-only policy update: the sealed Cl/N/Sb/proton-transfer policy SHA is`81baaa7f…`; standardizations manifest`ca9b558d…`, reviewed raw-row binding`34a58ace…`. The gate now requires final-output-v3 and a separately pinned`reviewed_standardizations` asset. Only exact request`c144a5ae…`, its recorded request/service strings and raw-row SHA`23581c…` are accepted as this feature-representation convention. It remains eligible and external-only, never a rejection/exclusion or identity/source-supervision merge. Other changed rows/kinds/IDs still block. Cl/N rejection and Sb exclusion remain intact. The numerical/graph audit and full32,421 scope remain mandatory; frozen evaluation gates are unchanged.

Final launch input binding completed: schema2 snapshot SHA`eddc54fa…`, final companion manifest SHA`26f48f5a…`, full-goal approval SHA`affae021…`. Independent equality certificate SHA`aef558c0…` confirms all678,600 official ADMET values exactly match evaluation, with unchanged identities/roles and zero unreviewed anomalies. Full v3 audit covers32,421 terminal outcomes (32,419 numeric;32,418 eligible), including all5,655 official inputs. The config is now enabled under root's explicit local-run authorization. Publication/submission remain outside this executor.
