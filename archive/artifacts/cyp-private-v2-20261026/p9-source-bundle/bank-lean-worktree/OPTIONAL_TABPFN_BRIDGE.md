# Optional final TabPFN bridge — preparation only

The original CPU final node90b061ad / commitfe093c2 is preserved. Two new provisional children close the TabPFN final-fit gap without running models:

| Child | Role | Parent |
|---|---|---|
| `b9257d11-ca3c-4cef-a649-5b481b6a86f9` | CPU selection plus optional external-query export | CPU final90b061ad |
| `0304b2a7-6fdb-493a-93c3-7ee89f822243` | TabPFN full-training OOF; query-phase code also prepared | TabPFN evaluation4d577549, source4f2a84c |

Both keep fixed `bash run.sh`. Neither has been launched. All final snapshot/native companion pins remain null and `training_enabled=false`.

## Exact pipeline

1. **Full-goal gate first.** All32,421 terminal ADMET outcomes, their full audit/eligibility ledger, all5,655 approved finite official inputs, the actual completed native8421 companion and final fold manifest must be pinned. The earlier18,460 snapshot cannot unlock either final stage. Explicit external failures/exclusions are not fabricated features.
2. **TabPFN OOF stage:**20 endpoint contexts =five official folds ×four CYPs. Scientific settings are unchanged from evaluated4f2a84c: v3.5 checkpoint SHA`ece4d67…`, eight estimators, seed42, ADMET120 only, per-endpoint train-only median+StandardScaler, noPCA. The isolated runtime is Python3.11.13 / Torch2.8.0+cu128 / TabPFN9.2.0 / NumPy2.2.6 / sklearn1.7.2. No blind query predictions are made. It writes4,905-row OOF predictions, all five training-OOF metrics, context timing/cache receipts and a completion receipt.
3. Bind the completed stage with `tools/pin_external_tabpfn_result.py --kind oof`, using its **actual** ORX experiment/run UUID and source commit. This hashes the receipt and predictions; it does not infer success from a path or fabricate run metadata.
4. **CPU selector child:**ingests that complete hash-pinned OOF candidate alongside the existing CPU portfolio. It verifies identical content hashes/folds/model/checkpoint/runtime and exact row/request identities. It applies the same standalone/global/per-CYP blend selection using full official raw training OOF. No new grid is added. No CPU-side TabPFN call is permitted.
5. If a CPU/native option wins, the existing final-refit/export path completes normally. **If TabPFN wins**, the selector performs no TabPFN query fit and emits `tabpfn-query-request.json`, a locked selection and `complete.json` status`awaiting_tabpfn_query`. This is not a completed prediction/submission. Pin a selection bundle using `--kind selection`.
6. Only then create a **query child from the frozen TabPFN OOF node**, copy`tabpfn_query_config.template.json` to its active config, set its actual new experiment UUID, pin the same full inputs and selection bundle, choose a new output directory, and enable/commit it after the existing budget review. Its four contexts refit on each CYP's full observed official labels and predict exactly750 inputs. It verifies the selected option and reconstructs the locked OOF blend before accessing the model. The query receipt is bound to the exact request/selection, data, folds and model. Pin it using`--kind query`.
7. Create an **export-only child from the CPU selector**, use`external_export_config.template.json`, set the child's actual UUID, pin the selection bundle and query receipt, and preserve all full-goal inputs. This phase fits no model. It verifies the returned750 predictions, reconstructs the selected blend, reapplies the fixed published placement and validates the exact submission CSV. It does not rerun selection or use blind outcomes.

Do not edit a completed/frozen ORX node to change phases. Query/export children are created only if needed; their implementation and config templates are ready now. The helper accepts no partial or failed producer receipt, and requires actual producer metadata before a cross-stage artifact can be consumed.

## Matching and leakage safeguards

- Exact final feature folds are the already frozen`cc471dcf9b632e61d197a4d2a497b3932766b90b201e2946fe630981d8c9d680`:five981-row validation groups, train-side parent/strict purges. Neither runtime invents its own folds. Native component folds remain different and are joined rowwise by official identity.
- Cross-host binding uses file content hashes and ordered120 feature columns, allowing Mac/Linux staging paths to differ without changing scientific inputs. The native companion and full chemistry approvals are included. The optional frozen CheMeleon checkpoint is excluded from the TabPFN content identity because it is not a TabPFN input.
- OOF files must contain all4,905 official IDs/SMILES/request IDs and four finite predictions. Query files require the exact750 identities. Model/runtime/checkpoint/preprocessing changes, altered folds, missing producer evidence or mismatched selection hashes are rejected.
- The export stage mathematically reconstructs the selected training-OOF blend from pinned native and TabPFN vectors; it rejects a CSV inconsistent with the locked convex weights. There is no outer/hidden-label selection and no silent substitution of a CPU learner.
- Serving stays `native_published_placement`, fixed before new feature results. Raw export and poor local placed diagnostics remain visible. Undefined placement, parity failure or invalid schema blocks export; no silent raw fallback.

## Runtime and spending

The final wrapper runs its full-input/cache/selection preflight and disabled-training guard **before** any runtime bootstrap. It uses a separate`/workspace/cyp-tabpfn-final` environment and existing cached weights, never the native Torch2.6 environment. The base image digest is pinned to`sha256:417bd75df6365104c283ea4c1651fb3530d9eb5a4c2fafa51943cff2a94e6385`; actual package/CUDA checks run before model access. No weights are downloaded.

Historical40-context timing gives approximately15.11min for the20-context OOF stage and3.02min for four query contexts, or18.13min total, excluding staging/bootstrap. These are uncertain historical proxies, not measured new runtimes or spending authorization. Query compute is avoided entirely if TabPFN loses. The existing$5 goal cap and actual remaining balance still govern launch.

## Readiness and verification

Prepared: both stage implementations, shared selector support, real-result manifest binder, selection-bound query and export-only paths, phase config templates, fixed model/runtime/source pins and complete-goal guards. Pending: real full-goal/native inputs; running20-context OOF; actual shared selection; and conditional query/export child creation. No implementation substitution is needed if TabPFN wins.

No-real-fit checks:15 existing CPU executor tests,9 bridge/artifact tests and4 isolated-stage context tests pass. They cover fold/data/runtime/checkpoint mismatch, missing producer provenance, blind inference prohibited during OOF, losing-model query rejection, exact20/4 call contexts, per-target missing-label masks, content identity across staging hosts, locked blend reconstruction and selection-bound query receipts. Both final preflights reject unpinned inputs with fits_started0. No model constructor, fit, model inference, rental, publication or submission occurred.

## Minimal H5/H6 extension after the initial ADMET120 commits

Initial ADMET120-only versions remain preserved at CPU`d9bdde93caa49bd4eae7e24b0c6c9672058afcd3` and TabPFN`d7e1a5500262b641011425a93821fd57221b5eb6`. The provisional extension adds only the two subsequently authorized representations:

- H5, evaluated source`704407a62fa9824a741dbde359c6103bc56de0ef`:TabPFN`tabpfn35__adme600` (`adme`) or`tabpfn35__adme600_admet120` (`adme_admet`). Exact evaluated predictor/helper copied, including noPCA, train-only scaling and the representation-specific cache identity. The final lease deadline/margin must be supplied anew; today's evaluation lease is not copied.
- H6, evaluated source`61a00bd673e421b026f2f7c1d630d86c24c841fd`:LightGBM`lightgbm__adme600` or`lightgbm__adme720`, same inherited two-setting grid/learner. The CPU model helper is byte-identical to H6; no other family is added. H6 templates explicitly disable the external TabPFN prerequisite.

The600 block is the exact frozen ADME cache, float32[4905,600], SHA`e0216aea…`, aligned to the original challenge row-map SHA`b7391fb2…` and encoder checkpoint SHA`b8137a0d…`. The720 view is lossless float64 concatenation `[ADME600, sorted ADMET120]` before the model's original preprocessing. Seven embedding source/provenance/runtime assets are pinned. Unknown encoder pretraining membership and the unestablished participant-weight redistribution license remain disclosed; no checkpoint is redistributed by these artifacts.

**Only4,905 training embeddings exist.** Neither H5 nor H6 is allowed to invent a5,655-row bank or derive blind embeddings with another encoder/routine. A750-row blind bank must first be generated by the exact frozen `MPNN.fingerprint` routine/runtime specified in the producing team's unchanged `adme_blind_receipt.template.json`, then sealed with actual run/source, checkpoint, input/output/order and shape/finiteness evidence. The ordered-identity hash is SHA256 of UTF8 JSON records containing Molecule_Name/SMILES in official order, sorted JSON keys and compact comma/colon separators. The wrapper additionally checks request IDs. No blind-bank generation or encoder inference is implemented/executed by this extension; the source routine and receipt contract are supplied, and this remains an explicit prerequisite if an embedding view is chosen.

For H5 the bank manifest is bound to the locked TabPFN query request. For H6 it is bound to a predeclared, hash-pinned final-recipe decision; bank acquisition may precede final CPU OOF because the encoder is frozen and reads no challenge labels. Both reject changed runtime, checkpoint, protocol, IDs/order or view metadata. All full-goal/native/fold gates remain mandatory.

Config templates are examples, **not a final winner decision**. There are explicit600 and720 templates for H5 selector/final stages and H6 final CPU stages. Their producer UUIDs, final inputs, blind bank and lease fields remain unpinned/disabled. Root will choose the validated recipe; no current result is claimed by preparation. Existing default ADMET120 config stays unchanged in scientific settings.

Additional synthetic checks cover600-versus720 identity, altered encoder/runtime rejection, missing blind-bank rejection, and exact H6 view routing through a no-model stub. No new experiment or GPU run was launched by this work.

## Final bounded H7 and predeclared validated-pair routes

The optional H7 route copies exactly`night/simplex_strae.py` from evaluated source`e533fd9259bc4e6766ce6f1b8dcfe8f6b29853dc` (helper SHA`4737adba…`). It selects the existing two-setting grid for primaryADMET120LightGBM and H6ADME720LightGBM from full official OOF, then fits one global3-weight simplex with experts ordered `[native, primaryADMET120, H6ADME720]`. It adds no intercept, per-CYP coefficients, grid or family. The final refit produces the two existing readouts'750 predictions and applies those same three weights. Solver/runtime pins are NumPy2.5.4 and SciPy1.18.1, matching the verified H7 evaluation.

`h7_final_config.template.json` is an **optional, disabled** route, not a promotion decision. Root's H7 diagnostics are mixed; this preparation does not choose it or report its development scores as new confirmation.

A separate `validated_primary_pair_config.template.json` supports root explicitly locking one validated existing recipe plus its global native blend. It repeats only that recipe's two-setting grid and weight fit on full official training OOF; it cannot silently reselect a standalone/per-CYP/other-family procedure. A hash-pinned pre-final-fit decision is required. This does not add another experiment family, and the template is not an actual model-choice decision.

The completed native companion is now bound from independently verified certificate`94ab1407…`, run`91132654…`, source`ed1ab383…`. The final reader verified its4,905 OOF and750 query vectors and reproduced placed vectors to max2.66e-15 without model inference. Native assets are populated in these optional templates; full feature snapshot/audit and all runtime-enabling fields remain unpinned.
