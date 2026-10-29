# All-endpoint ADMETlab feature increment

Status: executable feature runner is connected to the fixed `bash run.sh` contract; no real feature model has been trained or launched by this helper. This provisional child is rooted at source commit `166ef5cc04d9a13ae0fddeb2fa1a52559bed23b8`. The first configured feature experiment is explicitly **native scratch Chemprop + MAE + all ADMETlab web-default inputs**, compared with the completed native scratch-MAE control. It is not silently presented as a CheMeleon feature run. A CheMeleon follow-up requires its own child and declared initialization. Actual execution waits for the full, verified `web_default` batch cache. The API route is rate-limited and its probe vectors are not mixed with this regime.

## Question and comparison

Does the complete external ADMETlab predicted/calculated property profile improve the same native four-component CYP ensemble, on the same frozen molecular pools and folds? Retain the CYP outputs: the user explicitly requested every endpoint. Do not treat them as observed challenge labels or as new independent experimental supervision.

Recommended first comparison: same selected encoder initialization (CheMeleon or scratch), same newly initialized graph prediction head, same data/folds/loss/optimizer/epoch budget. `build_with_zero_extended_fresh_head` constructs the native graph-only initialization, copies all its model parameters and buffers into the descriptor model, and appends zero columns to its first FFN weight. The new feature model initially represents the same function and acquires feature contributions through training. This separates the feature addition from extra continuation training. CPU RNG state is restored to the original graph-only construction state after building the expanded copy.

Optional later continuation: `copy_graph_model_weights` can start from a trained fold checkpoint, copy its first-layer graph columns and all remaining state, retain the new descriptor scaler, and set new input columns to zero. In that case compare with a **graph-only continuation from the same checkpoint and with the same extra training budget**, not only the previously stopped baseline. Reset the optimizer in both arms: old first-layer optimizer state has the wrong shape for the widened input. This is a practical alternative, not an additional mandatory sweep.

The graph encoder itself stays trainable. The graph BatchNorm width stays 700 or 2048; descriptor columns are concatenated **after** graph aggregation and graph BatchNorm, exactly as Chemprop's `fingerprint` implements it. The effective first FFN input width becomes encoder width plus descriptor count.

## Frozen data contract

Read these three inputs, freeze their SHA256 values before launch, and include them in each fold's specification/job identity:

- `stage/admetlab-id-map.csv`: original `Molecule_Name`, original `SMILES`, `source`, canonical `request_smiles`, and `request_id` (SHA256 of canonical request SMILES).
- `admetlab_web_all/features.csv` (or a separately declared complete subset snapshot): one row per request ID. Metadata columns are `request_id`, `SMILES`, `priority`, `service_smiles`, `taskid`.
- `admetlab_web_all/feature-schema.json`: explicit `feature_columns`, in frozen order. The acquisition route is the documented web batch backend with `source_mode=web_default`, consistent across all molecules. The earlier API probe client (`6652e7ae63835e6f3ff2ca749b7936df6959f0c9`) supplied schema context only; its numeric vectors are excluded. The exporter reports names prefixed by `ADMETLAB::`, including all actually returned web endpoint values, any actual uncertainty fields, and count-only rule representations. Raw list items are preserved by the acquisition client but are not one-hot encoded because their semantics are unverified. Do not select columns by numeric dtype: priority, task IDs, and user labels must not enter the model.

`AdmetFeatureCache.align(frame)` binds the exact original `(molecule ID, SMILES)` pair to request ID, then retrieves the matching feature row. It preserves input row order and IDs. A shuffled cache cannot permute molecule features. Duplicate/ambiguous mappings, duplicate request rows, unknown schema columns, absent requested endpoints, and absent requested molecule rows fail explicitly. Equivalent source structures can share one request ID. Nonfinite values other than NaN fail; missing values are handled explicitly below.

Do not silently shrink a member's training pool when its ADMET cache is incomplete. Wait for the required cache, or define and label a different missing-source experiment. A row explicitly present with missing endpoint values is distinct from an absent request row.

## Inner-fold preprocessing and native call interface

`prepare_fold_descriptors(cache, train_frame, validation_frame, query_frame)`:

1. Aligns all three frames; reports ordered ID hashes and request-ID overlap counts. Strict disjointness is the default for our outer-holdout experiments. A production recipe that intentionally retains a documented public-data overlap with actual TEST must explicitly permit query overlap and retain the overlap audit; train/validation request-ID overlap always fails. No automatic row deletion occurs.
2. Fits one median per declared feature on **inner-fold training rows only**. Validation/query values and all target/interval columns are ignored during fitting.
3. Adds one missing indicator per feature, including features with no missing training values. Thus a schema with F source columns yields 2F descriptor columns.
4. Retains endpoints absent from every fitting row as constant value 0 / missing flag 1 across all partitions. Their columns are not removed, but an unseen held-row value cannot activate an untrained input weight. Raw service values remain preserved in the cache.
5. Does **not** standardize. `core.train_chemprop_fold` fits its native descriptor StandardScaler on the training dataset and applies it to validation. The model stores the corresponding `X_d_transform` for raw-input prediction.

Integration sketch (inside the isolated feature worker, after selecting its exact train/validation rows):

```python
cache = AdmetFeatureCache.from_files(id_map, feature_csv, schema_json,
                                    expected_sha256=frozen_input_hashes)
fd = prepare_fold_descriptors(cache, train_df, validation_df, query_df)
fs = fd.configure_spec(fs)  # use_extra_features=True, n_extra_descriptors=2F
save(fold_dir / 'admet-feature-audit.json', fd.audit)
# In this worker only, wrap the native builder to use the paired fresh head.
original_builder = core.build_mpnn_model

def feature_builder(hp, **kwargs):
    model, initialization = build_with_zero_extended_fresh_head(original_builder, hp, **kwargs)
    model.admet_feature_initialization = initialization
    return model

core.build_mpnn_model = feature_builder
model, val_pred = core.train_chemprop_fold(
    fs, train_df, validation_df, y_train, y_validation,
    fold_idx=fold, checkpoint_dir=str(fold_dir / 'checkpoints'),
    **fd.native_training_kwargs(),
)
query_pred = core.predict_chemprop_frame(model, fs, query_df, extra=fd.query.copy())
```

The training kwargs provide independent **raw imputed** copies for `train_extra`, `val_extra`, and `val_extra_raw`. Despite the legacy native docstring calling the first two “scaled”, the code itself normalizes them internally. Pre-scaling these arrays would double-scale features. Persist the imputer state/column order alongside the checkpoint; inference reconstructs the same imputed raw arrays and lets the saved model's descriptor transform scale them once.

The configured output is `/workspace/cyp-repro/results/scratch_mae_admetlab_web_all`. Use a distinct output directory per recipe, and bind feature-table/schema/map hashes and preprocessing audit to fold completion evidence. Never reuse graph-only outputs merely because their checkpoint files pass their own hashes.

## Interpretation

All-feature coverage is not a guarantee of predictive benefit. The external teacher's historical training membership is unknown. Our own molecular holdouts and fold-local preprocessing prevent local fitting on their labels, but cannot establish end-to-end independence of ADMETlab's predictions. Keep all CYP outputs as requested and state this qualification in any reported feature-arm result.

The current helper does not implement self-training on extra molecules or replace experimental pIC50 with ADMETlab predictions. It tests external predicted properties as inputs. Those are different experiments.

## Verification

CPU functional tests cover request-key/row-order invariance, mapping/schema/cache failures, preservation of CYP columns, invariance to hidden-label changes, train-only imputation and missing flags, serialized preprocessing roundtrip, single native scaling, and numerical forward parity for both 700- and 2048-wide graph encoders. Zero-initialized descriptor weights receive nonzero gradients; no optimizer step or scientific model fitting is performed. The paired fresh-head builder also preserves the original CPU RNG state. Both encoder widths pass ordinary Chemprop save/load reconstruction with the expanded predictor input dimension, saved descriptor transform, and unchanged predictions; this is not merely a state_dict-only forward test.

Run: `python -m unittest discover -s tests -p test_admet_features.py -v` using the existing CYP Python environment.


## Executable runner and launch contract

`run.sh` now runs the standard-library-only `night.admet_feature_contract` gate first, before environment setup or CUDA training. It then invokes the existing pinned setup and `night.admet_feature_runner`. The run command remains `bash run.sh`.

`admet_feature_config.json` binds the frozen queue and source-ID-map hashes, the expected 119 canonical endpoint identities plus the additional `Other_assay_interference` endpoint (120 actual identities), both outer cohorts, their exact 750/529 query sizes, the scratch initialization, the unique output directory, and GPU slots 0–7. All additional numeric columns actually present in the completed schema remain included; there is no fixed feature-count truncation or CYP filter. The web route omits three always-empty legacy API fields (`cl-int`, `LM-mouse`, `LM-rat`); no fabricated columns are added for them. Their unexpected appearance triggers explicit schema review, not silent filtering. `Toxicophores` is the verified canonical alias of the web column `FAF-Drugs4 Rule`.

Readiness requires all of the following from `/workspace/cyp-repro/admetlab_web_all`:

- Completion, status and feature-schema manifests must all declare `source_mode=web_default`, `backend=documented_web_batch`, and `api_probe_vectors_used=false`. Mixing API vectors with web-default vectors is prohibited.
- `complete.json` and `status.json` both declare completion of the exact full acquisition queue, with all rows successful and zero remaining.
- The feature-table SHA256 matches completion evidence; queue/map hashes match the committed configuration and acquisition map provenance.
- `missing-or-pending.csv` is present and contains only its header.
- The explicit schema contains every expected endpoint and matches the exact feature-table header; numeric values are finite or explicitly missing.
- Request IDs are unique, match canonical request SMILES, and cover the entire acquisition queue. Missing schemas, incomplete coverage, stale hashes, or wrong identities fail before model training.

The priority-0 export alone is deliberately insufficient for this four-member experiment: the public-data union members require the full queue. A core-only probe is a different declared experiment and must not silently shrink these training pools.

Preparation freezes table/schema/map/queue and source manifests under the recipe output, then checks feature alignment for every member and both queries before any worker launches. Every original data CSV, target list, hyperparameter and inner fold is retained; only descriptor configuration is added. The producer's local cache is read, never contacted through the network by this runner.

Workers share `/workspace/cyp-repro/gpu-slots/gpu-N.lock` with the campaign's other ORX queues. A free device is leased before spawning, its lock FD is inherited by the worker, and its process group is terminated before releasing the slot on failure/cancellation. No worker silently falls back to CPU when its CUDA device is unavailable. The runner trains 40 models, performs unchanged native flat averaging and published placement, writes raw/placed official scores for both holdouts, and records their differences from `control-scores.json`.

All descriptors, including other CYP predictions, are supplied to every component. Thus the CYP2D6 specialists retain their original targets but now receive cross-CYP external profile inputs intentionally. External teacher membership remains unknown in every output report.

## Additional integration verification

The expanded suite has 13 CPU tests. Mock complete/partial exports exercise manifest, checksum, schema, missing-row and wrong-recipe gates; preparation preserves exact frozen rows/folds/hyperparameters. A forward-only mock of the training call exercises the real feature worker, descriptor normalization interface, prediction, checkpoint metadata and completion hashes without optimizer steps. Cross-process file-lock tests confirm shared-slot exclusion without a GPU. Existing 700/2048 save/load and forward-parity tests remain included. No synthetic results are eligible for a leaderboard or scientific score claim.


## Source-regime decision

The verified official web batch response exposes 120 actual endpoint identities and explicit raw/input SMILES for row binding. Some returned values differ from the earlier API `feature=true` probe, so those are treated as different prediction regimes. This experiment uses the same `web_default` regime for the entire 32,421-request queue. The three old API CSV fields were empty and are absent from web output; keeping every actual web endpoint does not mean fabricating empty legacy columns. Every feature model records the source regime and frozen table/schema/map hashes.
