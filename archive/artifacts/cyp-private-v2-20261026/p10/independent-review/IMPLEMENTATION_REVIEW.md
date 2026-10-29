# P10 bounded independent implementation review

**PASS for staged-data identity and the intended loss intervention. No material objective/mapping bug found in the inspected source.** No predictive fit, optimizer step, rental or data edit was performed by this reviewer. IMPLEMENTATION_CERTIFICATE.json pins the inspected code/config and records the checks below.

## Verified

- All57 staged asset hashes match the manifest. The common table and repaired fold manifest are byte-identical to P7R. Exact row IDs, request IDs and SMILES agree with the feature row map;18real targets remain unchanged.
- All10model-only exports match their pinned predictive tensor hashes and original-parent checkpoint references. Each retains17predictive tensors including BatchNorm running mean/variance/count and the exact26-output unscale transform. The means/scales match the parent's saved initial metadata, with original8carrier transforms0/1. Objective/metric buffers are excluded so installing a parent cannot silently restore18-task weights over the primary-only objective. This independently verifies staged export pins; actual runtime prediction parity is also required in the runner before fitting.
- ContinuationMAE counts finite values in the original18real columns for its denominator, then applies either18-task orfour-primary taskweights to the numerator. Carrier columns18:26are excluded. Uniform rowweights are asserted.
- An independent mixed-mask arithmetic/autograd check gave identical primary gradients across objectives, zero auxiliary/carrier gradients in primary-only mode, and the same42-original-observation denominator. A no-primary batch returned a differentiablezero with zero current supervised gradients. No model or optimizer was used in this check.
- FreshAdam is constructed withlr1e-4,weight_decay0 andno scheduler. Runtime callback checks emptyoptimizer state andstep0 atstart andconstantLRthrough training. No trainingbatch is skipped according to primary-label availability; batches and no-primary batches are counted.
- Runner reinstalls the same parent predictive state within eachpair, uses its saved feature/target transforms, chooses the same parent-dependent zero/repairedinputmatrix, and reuses identical train/stop/test lists. No source data/scaler refitting is introduced.
- Epoch0 evaluation sets validation/eval mode, verifies predictive tensor/BN state remains unchanged, and checks parent prediction parity beforetraining. RNG is reset beforefit. Early-stopping bestscore begins at the epoch0 primaryST-RAE value; finalselection compares the bestcontinuation stoppingmetric againstepoch0, withties/worsevalues retainingtheparent. Testoutcomes are used only forreportedfinalmetrics, not epoch/parentselection. Parentpredictions are used forparity, not outcome-based tuning.
- Primary bounds retainP7R offsets18:22and22:26. The unrelatedP8c22-task offsets are not imported.

## One measurement-coverage note sent to the owner

At inspection the runner exported selectedtestpredictions/allprimarytestmetrics, epoch0stoppingST-RAE andbestcontinuationstoppingST-RAE, but did not yet emit selectedmodel training/stopping primaryerrors or auxiliarybehavior. Those diagnostics are requested in PLAN and matter for the proposed underfitting/auxiliary-competition interpretation. Overalltrainingloss cannot substitute because its numerator differs bydesign. The owner was asked to save matched selectedtrain/stop primary andauxiliaryreadouts, or explicitlyretain a recoverableposthoc inference path. This is requiredmeasurement coverage, not a new experimental factor or anotherapprovalbarrier.

## Interpretation to retain

The experiment removes auxiliary **current supervised gradients** while keeping primarycoefficients andchemicalinputexposure fixed. A no-primary batch can still alterBatchNorm and, after earlierupdates, Adam-momentum state/parameters. Thus “zero primary loss” must not be described as “no model update.” This behavior is explicitly documented and consistent with the matched continuation question.

The causalcomparison is within each frozenparent: original18-taskcontinuation versusprimary-onlycontinuation. Cross-parentzero/repaired comparisons include their different learnedhistories. Improvedprimarytrainingfit would not alone prove improvedtestgeneralization or a biochemicalmechanism; auxiliaryforgetting, calibration/dispersion and per-CYP adverseeffects must remain visible. These reused stopping/testcohorts provide development evidence, not freshindependentconfirmation. No extra protocolfactor, success threshold, data filter or spendingrequest is introduced by this review.

Files: DATA_PRECHECK.json; PROTOCOL_REVIEW.md; check_implementation.py; IMPLEMENTATION_CERTIFICATE.json. RuntimeGPUparity andpaired RNG evidence will be produced by the authorized training owner, not claimed already observed here.

## Bounded diagnostic addition reviewed

The owner resolved the measurement note: epoch0 and selectedmodel primary predictions/metrics are now saved for the same observed training/stopping IDs, and all18test-head errors are saved for epoch0/selectedmodels to assess forgetting. Added baseline passes are eval-only with a predictive-statehash check afterward. Selecteddiagnostics run only after stopping-based selection. The objectivecore is byte-unchanged; the newrunner hash is in DIAGNOSTIC_ADDITION_REBIND.json. No newexperimental factor or unresolvedcoveragegap remains from this review.
