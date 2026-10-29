# Execution plan

## Acquisition prerequisite

Use100-molecule batches with an auditable50-molecule fallback after exhausted unknown-response recovery. This supersedes the earlier200-molecule plan:200 worked in the official subset but later external batches repeatedly lost their responses. Earlier unknown400 and200 request sets are now completely covered by saved smaller-batch results; their original attempts remain recorded as unknown.

Maintain four-second minimum HTTP start spacing and one in-flight batch. Preserve explicit429 and unknown-response distinctions. Recover a known result URL by GET rather than another POST. Merge successful CSVs only after exact request identity checks; never enqueue a cached molecule again. This is an acquisition reliability policy, not proof of a fixed service batch limit or invalid chemistry.

## Chemical audit

Audit a stable raw/features/manifest snapshot against official IDs and original/request/service SMILES. Check parse validity, exact input matching, graph/stereo/protonation/salt transformations, duplicates with stereochemistry preserved, finite endpoint values, and independent raw-to-numeric reconstruction. Keep source transformations explicit; do not claim teacher predictions are experimentally correct.

## Model hypotheses (provisional until independent audit/critique)

- H1: ADMET-only tabular learners blended with the full native ensemble. Teacher features supply activity-related information complementary to graph models. Pilot evidence supports a possible ST-RAE reduction; full-cohort benefit is unproven. Tune only with trainingOOF predictions; failure means no practical advantage on the fixed diagnostics.
- H2: ECFP/RDKit+ADMET learns residual structure-dependent effects unavailable to teacher-only models. Compare against matched structure-only and ADMET-only variants; preserve negative cases.
- H3: Frozen CheMeleon embeddings+ADMET with regularized heads can combine transfer features efficiently. Compare against matched encoder-only heads.
- H4: Feature-augmented fine-tuned graph models, only if simpler models leave an actionable gap and compute authority/budget are documented. Use the existing native/CheMeleon recipes rather than treating architecture changes as pure pretraining effects.
- Reuse previous failed loss experiments as evidence; do not repeat an unchanged negative recipe just to inflate the experiment count.

Selection must report all5 official metrics and raw/placed lanes separately. Our own750 and reconstructed briford529 remain fixed diagnostics; the latter is not the recovered original author holdout, and both have previously influenced decisions. Separate inner-model selection from final outer diagnostics. Use the official scorer and preserve cohort overlap and uncertainty.

## Submission

Recheck current challenge rules, deadline, cooldown and submission schema. Select the best supported recipe, refit on permissible complete training data, produce all blinded-test predictions, validate schema/IDs/finiteness, provide a valid public model report and submit through the existing user account. Do not substitute a different source-mode feature vector. Best available model may remain the native baseline; do not invent an improvement.


Scope update: user explicitly chose all32421 molecules. H0b collection-efficiency prerequisite: expand the pending index to the complete existing pool while preserving the immutable official queue and all cached rows. Optimize the CSV parser index/schema allocation only with output-equivalence checks, so repeated full-pool merges remain practical. No prediction features or chemical structures are changed by this optimization.

H0c acquisition reliability: cache each batch's prepared form while the cookie jar remains unchanged, so explicit429 retries reuse the exact payload instead of fetching another form. Every POST is still checked against the frozen batch SMILES. Record response-lost inference attempts as unknown; permit at most two explicit, auditable reissues of a cache-missing batch under the user's instruction to resend the same set when no result arrives. A known result URL always triggers download recovery, never another POST. Cap a stalled inference request at180seconds. This may repeat server computation after lost replies, but must never duplicate saved labels or claim the original request was rejected.

## Source-provenance disposition after raw-source review

See data-policy/DISPOSITION.json. Official-only readouts can test ADMET information conditional on the same qualified frozen native expert; this does not require repeating the reference merely to make its historical pretraining representation perfect. Its strict leakage-purge certificate remains scoped to the declared equivalence policy. The final legacy-native companion must use that same qualified source policy if used as that expert.

Fresh full-pool supervised feature experiments must instead apply the conservative28-request quarantine identically to their native control and feature candidate. Four ambiguous metal-parent cases remain flagged. Do not claim an incremental feature effect by comparing a newly curated fusion model only with an uncurated historical expert. All raw source records and all requested-graph ADMET outputs remain preserved; no fragment output is silently reused as a full-complex prediction.

## Explicit service-outcome and feature-identity exceptions

Reviewed intermediate18460-row audit: one externalCl terminal rejection, one externalSb finite-output but unresolvedservicegraph. See data-policy/OUTPUT_DISPOSITION.json and exact manifests. Preserve both outcomes; no retry, invented values or graphrepair. Freshfullpool matchedcontrol/candidate excludes union29; source28 remains separately recorded. Official-only5655 inputs allfinite/eligible in this snapshot. Final completeoutcome audit must verify these exact cases and stop for additional unreviewed anomalies. Schema-aware handling separates120basefeatures from sparsecategoryflags. This updates input eligibility, not target values or outcome scope.

## Evaluation dependency optimization — complete official inputs, acquisition still full-scope

The frozen18460-outcome intermediate snapshot already contains every4905officialtrain and750officialtest request, all120basefeatures finite and chemically eligible, with the two reviewed exceptions external-only. H1–H3 readouts fit official experimental labels only and use an already-completed fixednativeexpert; they have no dependency on yet-uncollected externalfeature rows. Therefore permit this exact evaluation on an explicitly scoped and hashed complete5655official model-input snapshot while full32421acquisition continues. Do not call the18460snapshot fullycollected32421 or relax officialcoverage/identity/finite/eligibility/reference checks. Preserve the same hypothesis grid, folds, transforms, metrics and selection. This is an executiondependency change, not new scientific selection or a reduced usergoal. Full32421terminaloutcomes and finalwholepoolaudit remain mandatory for finalrefit/submission; freshfullpoolfeaturefusion cannot use incomplete externalfeatures.

## Independent native companion prerequisite

The prepared correctednativefullfit8421e31b has complete experimental inputs and does not use ADMETfeatures. Execute its10affectedrefits+10auditedreuses whileexternalfeatureacquisitioncontinues, preserving qualifiedlegacyparent/sourcepolicy and32strictinnerexclusions. This supplies fullofficialOOF+blindnativevectors needed by laterfeatureblending. It doesnot open the featurefinalfit/export/submission gate: those stillrequire all32421terminaloutcomes+finalaudit. Separate1.10USDphasecap andtaskownedcleanup apply.

## H5 — nonlinear pretrained ADME representation with teacher features

Source: the prior Jeremy open-recipe reproduction and current challenge-audit/tabpfn-feasibility inventory (cached pretrainedADME600 encoder/matrix, exact source/checkpoint pins). Current ADMET120-only TabPFN is weaker than the native+LightGBMteacher blend; this does not test whether a richer molecular representation makes the same nonlinear learner useful. Mechanism: pretrainedADME embedding retains molecular information absent the120teacher endpoints; concatenating both may improve calibrated complementary residuals. Expected direction: lower rawST-RAE after train-OOF blending; size unknown, not assumed successful. Falsification: the augmented720representation fails to improve its matchedADME600 control and native-blend diagnostic, retaining all adverse metrics.

One bounded child after completedADMET120node: ADME600-only and ADME600+ADMET120 (720) with identicalTabPFN3.5/8estimators/seed/folds/observedlabels/preprocessing andglobal/per-CYP blends. No hyperparametergrid expansion, no blindlabels, no pooling outerlabels for weights. Preserve official-onlycompleteinputscope and exactencoder/source/rowhashes. No automatic PCA/substitution. All5metrics onbothfrozendevelopmentcohorts; any new improvement remains conditional on reused diagnostics and unknown teacherpretraining membership. This uses remaining existingTabPFN1.10USD/120minlease authority, includingrecovery; no newrental or capincrease authorized forH5. Keep currentADMET120results immutable.

## H6 — targeted ADME embeddings in the successful shallow-tree learner

Motivation: the completed CPU experiment supportsADMET120+nativecomplementarity, while H5 verified a cached600-dimensional target-relevant ADME representation from the earlier Jeremyrecipe. Compare pretrainedADME600-only withADME600+ADMET120 using exactly the existing shallowLightGBM grid, folds, seed, global/per-CYP OOF blending andall5metrics. Mechanism: task-relevant latent molecular information may improve residual predictions more than generic fingerprints or a linear frozenCheMhead. Expecteddirection lowerST-RAE; effectsizeunknown. Falsification: addingADMETdoesnotimprove itsmatchedembeddingcontrol or the priorprimaryteacherblend in thedevelopmentdiagnostics. Preserveadversemetrics andallpriorresults.

One new child of completedCPUportfolioea7f1cb9, localCPU only. No newparametergrid, no newteacher, no paidresource, noPCA. Reuse exact H5 verified4905×600 matrix/ID/SMILES/provenance; blind750encoderfeatures remainunavailable untilseparatelygenerated if needed forfinal. Newreadouts useofficialexperimentaltargetsonly. Goal32421coverage/finalaudit unchanged.

## H7 — final bounded blend of the complementary existing CPU experts

Evidence: the priorprimaryADMET120LightGBMglobal/native blend gives rawST .613328/.598232; H6ADME720LightGBMglobal/native gives .617911/.578549. This cohort-dependent tradeoff motivates combining their existing information rather than adding anotherfamily. Hypothesis: a global convex mixture of correctednative, primaryADMET120LightGBM andH6ADME720LightGBM can preserve the strongerown signal while improving the othercohort. ExpectedST direction down; magnitudeunknown. Falsification: training-OOF-learned3way mixture fails to improve thediagnostic tradeoff; retainthatresult andsimplerarms.

One final localCPU meta-fitting experiment: fixedthreeexperts, nonnegativeweights summing1 shared across4CYPs, exactmacroST-RAE objective withtraining-onlyCI/denominators. No intercept, no per-CYPweights, no additionalfamily/seed/hypergrid. For eachcohort useeachbaselearner's existing training-OOF-chosenhyperparameters andnativeOOF; no newbasefits. Audit allinputvectors first; weights must neverseeoutertruth. Reportall5metrics andpairedscaffolduncertainty againstnative andprimarypairwiseblend; preservefull development-selection/reusedholdoutcaveat. Fulltrainingrefit, ifchosen, mustrepeat thisexactfixedexpert/OOFweightprocedure, witha verifiedblindADMEbank. AfterH7, selectfrom thecompletedboundedcandidates andfinalize, ratherthan expanding thisround further.
