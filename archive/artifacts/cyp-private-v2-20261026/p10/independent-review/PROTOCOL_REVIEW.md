# P10 objective/data review — protocol observations, source inspection pending

The planned within-parent contrast is identifiable as removal of auxiliary gradient terms versus an otherwise matched low-learning-rate continuation. At the same parameters/batch, letD be the count of finite labels among the ORIGINAL18real targets. ThenL18=sum(realmasked standardizedMAE)/D andL4=sum(primary-fourmasked standardizedMAE)/D. UsingD in both arms preserves each primary term's coefficient. RecomputingD after masking auxiliary labels would confound the test by increasing primary loss weight.

The fixed common dataset has31,641rows, including26,736without a primary label, and0without any of the18real targets. Every nonemptybatch therefore has a valid original denominator. Trainfolds contain2905/2873/2920/2964/3045primary-labeled rows. Remainders atbatch128 are6/59/63/56/3, so shortlastbatches can lack primary observations.

Material implementation checks:

- Compute originalfinite mask/denominator before zeroing auxiliary numerator. Exclude8boundcarrier columns from both counts andloss; preserve missing-target masking and targetscaledMAE semantics.
- A no-primarybatch must yield a differentiablezero primary numerator with the positiveoriginaldenominator. Do not skip thosebatches only inonearm. With Adam history, a zero currentgradient need not mean zero parameterupdate; BatchNorm also updates on these molecules. This is still consistent with removing auxiliary supervision while preserving chemicalinputexposure, but must be reported accurately. Do not manufacture labels to make abatch supervised.
- Load the exactsame parent parameters andBatchNorm state within eachpair; preserve feature/target transforms and originalrows/folds. Optimizerreset and constant1e-4LR must be implementedidentically, withno restored optimizerstate or inheritedschedule differences.
- Epoch0 is an eligiblecandidate evaluated on the same primary stoppingmetric beforetraining. Saveits actualweightstate immutably, not a mutable state_dict reference. Training-mode probes must not alter BatchNorm beforeepoch0. Selectepoch0 if subsequent stoppingmetrics neverimprove; neveruse testmetrics forselection.
- Bounds remain atoriginalP7R positions18:22and22:26; the unrelatedP8c22-task offsets must not be imported.

Interpretation limits:

- Within-parentL4versusL18 tests loss routing during continuation. It doesnot prove biochemical mechanism, teacher-data validity or universally harmful auxiliarydata.
- Parentzero andunit-repairedmodels have different learnedhistories. Cross-parentdifferences include thathistory; the causalcontinuation comparison is within eachparent. The parent's untouchedpredictions remain a useful thirdreference against “simply trainlonger.”
- Primary-only continuation mayforgetauxiliaryprediction, changeBN/calibration or improveoneCYPwhileharminganother. Keepallfive metrics/perCYP, fittedtrainingerror, stopping/testerror anddispersion.
- Reusing the existingstop/testcohorts after many experiments remains development evidence, not freshindependentconfirmation. No gain threshold or guaranteedblind-scoregain is inferred.

This file introduces no newprotocolfactor orspendingrequirement. Source/unit checks will bind the implementation when it is ready; no model fit orrental is performed bythis reviewer.
