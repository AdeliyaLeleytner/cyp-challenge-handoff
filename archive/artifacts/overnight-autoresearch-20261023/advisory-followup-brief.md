# Independent Claude consultation

Round: 2 — new evidence since consultation20261023T205706Z-653191c2 (wrapper reported automatic fallback, actual primary claude-opus-5).

## User request

“используй https://github.com/AlexWortega/claude-autoresearch-skill этот скилл для решения челленджа, я ухожу на ночь. снимай gpu на vast.ai. пробуй различные фичи, доп данные из всех возможных открытых источников и баз данных, и различные архитектуры и пайпланы. сравнивайся на нашем холдауте и на холдаутах открытых решений челленджа, засылай решение как только найдешь сеттинг, на котором мы лучше и на нашем холдауте, и на холдауте самого лучшего открытого решения”
Prior authorization: “Арендуй что и сколько нужно для максимально быстрой работы на vast.ai”.

## Authoritative context and constraints

Current UTC date2026-10-23 late evening (Moscow2026-10-24 night). Active scientific campaign root is this directory; logical workspace is /Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition. User authorized GPU rental and conditional challenge submission without another permission question. No unrelated code publication, invented identity, or contacting people. Initial campaign spending tranche$10.50, two owned4xRTX3090 rentals, credit/deadline stop guards; no new payment method/topup. Target morning08:00Moscow. Read-only advice only.

## Current state

Many source/feature/learner/loss trials completed. Fresh strongest-open briford four-member recipe was reconstructed on own750 and briford529, with fixed five scaffold inner folds and seeds42/142. The selected candidate changes train-OOF ensemble weights/affine placement only; it uses the same4scratch neural components, public official/ChEMBL/Veith data, and no inherited CYP-adapted or Monroe weights. A frozen qualification certificate passes both the mean paired-seed criterion AND the score-of-averaged-predictions criterion on both cohorts. Full TRAIN fits foractualTEST are underway forbothseeds; no submission CSV/receipt yet.

## Evidence and source map

- gate_bundle_v1/certificate.json: official metric, allfourtargets, bothcohorts/seeds, hashes, per-seed scores, averaged-vector scores and pairedbootstrap.
- gate_bundle_v1/manifest.json + qualified_recipe.json: exact candidate and8predictionfiles, source runs and recipe. Individual source-run JSONs in samefolder are direct read-only ORX database snapshots, statusdone (SSH backend leaves exit_code null; no nonzeroexit).
- review-code/night/{promotion_gate,evaluation,stacking,metamodel_runner,reference_views,final_training,neural,reference,submit_candidate}.py plus final_config.json andofficialscorer: frozen source snapshots. Gate check lines163–255; stacking fit_stack at~117 onward; final_training preparesfolds/workers/collection.
- notes/submit-candidate-protocol.md and sources/gradio-info-refresh-presubmit.json: actual API has13arguments, track_select=Regression Prediction, anonymousalias, optionalidentityblank, publication/proprietary/open-code flagsFalse. No methoddescription14thargument. Officialsource app.py/submission.py/config.py remain under sources/.
- reference_audit/reference_recipe.json + manifest.json: reconstructed529 testIDs, one trainingparentpurge, exact publicdata/version/head counts and known source adaptations. Historical0.4378 checkpoint/OOF were not published; do not call local replication identicalto historicalboardentry.
- notes/monroe_pcba_exact_cyp_audit.md: same-target public assay overlaps inMonroe upstreamPCBA, exacthistoricaltraining/headretentionunknown; excluded from automatic candidate.
- FINDINGS.md/PLAN.md/EXPERIMENTS.md andRUN_REGISTRY.json: broader campaign.

Primary challenge https://huggingface.co/spaces/openadmet/cyp-challenge ; live API https://openadmet-cyp-challenge.hf.space/gradio_api/info . Code/date/rules snapshots are local; --web is enabled if currentexternalverification is material.

## Work already performed

Observed score ofaveragedseedvectors: reference0.6042028704 ->candidate0.6023806342 onown750; reference0.6289306012 ->candidate0.6267819269 onbriford529. Per-seed deltas are also negative inallfourcomparisons. Meanpaired-seeddeltas: −0.00150740 own,−0.00200453 briford.95%% pairedmoleculeCI: own[−0.0036442,0.0009083], briford[−0.0059556,0.0022973]. Thus small observed gains, not established statistical superiority. Gate criterion wasfixed before these results; no significance/effect-size threshold was invented.

Bothcohorts have been inspected duringdevelopment and overlap143molecules. OOFneural checkpoints use their inner validation labels forearlystop; calibrationCV isnot fullynested, and singlefoldOOF differs fromfivebagoutervariance. Outerlabels neverfit model weights/calibration; the qualification preserves these caveats.

Your earlier oof_pearson suggestion was inspected againstsource: it itself multipliesboard-derived OOF_TO_BLIND and usesBLIND_MOMENTS. All such constants wereexcluded. Baseline uses train-only selectedraw/LP/R2affineplacement. Exact reference corpuscurrentCSV is31,730trainableunion rows ratherthanblog~32,900 dueversion/identitypurges. The referencefirstseed0.6088/0.6227 isstronger than priorJeremyproxy; specialistcomponentbenefits vary bycohort, asmeasured.

Some concurrentGPU fitsOOMed; repeated only interruptedfolds withunchanged scientificparameters andexclusiveGPU routing. Candidate/reference qualification uses only completedrun evidence. Newlarge-corpushash/downloadissues were resolved orreported; not included unverifieddata.

## Questions for independent assessment

1. What conclusions and limitations follow from the new qualification evidence and the user's explicit conditional submission request?
2. What decision-critical implementation/provenance issues, ifany, remain between the qualified algorithm and the in-progress full-TRAIN actualTEST pipeline?
3. Which concrete checks should precede one authorized submission, and what should the final user-facing interpretation say?

## Known missing or inaccessible information

True challengeTEST activities areclosed. Finaltrainedpredictions are notreadyyet, so actualCSV variance/schema/hash andfinal recipe match remain tocheck. No officialscorecanbeclaimedbefore submission/scoring. The currentstrongest-opencodehistoricalweights wereunavailable; source-faithfuladaptedreproduction isexplicit. RemoteGPUs cannotbequeried bythisreadonlyadvisor; root willverify anynecessaryfacts.

## Codex position

Preliminary decision: the user's numerical condition is met under the preregistered paired protocol, so proceed with one authorized submission after fulltraining, CSV validation, exactrecipe/provenance checks and currentAPI/cooldown checks. Describe it as a small observed improvement overourreconstruction, not a proven generalizationgain or overallchallengewin. Material new evidence: bothseeds complete, confidenceintervals crosszero, exactcandidate uses only knownpublicdata, qualification code andcurrent13-argAPI areaudited. Main uncertainty is scientific interpretability of a tinygain aftermanydevelopmentcomparisons and whether any finalpipeline mismatch is missed; no userapproval is inferrednecessarymerelyfromuncertainty.

## Confidentiality check

No credentials, private keys, tokens, .env contents or unnecessary personaldata included. Onlypublicscientificdata, scoped code/artifact pointers and relevant protocol/budget information.
