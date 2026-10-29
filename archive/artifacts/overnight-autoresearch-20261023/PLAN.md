# Preregistered initial experiment matrix
No productioncode editedbeforethisplan. Independentmodelaxes are tested as hypotheses, notassumedimprovements. Numericalexpectedmoves below are rough planningpriors frompriorcomparisons, NOT successcutoffs or evidence; observecontinuousdelta includingadversecases.
Metric: officialmacroST-RAE lower. Primaryreferencecomparisons: ourfixed750 and brifordpublished529reconstruction; sameevalIDs, parent-purgefitcounterpartonbothmethods. Additionalstress: Jeremy5Butina and feasibleotherpublishedsplits. Preserveexistingmetrics; no silent replacementofbest-open gate.
|ID|Angle|Hypothesis andmechanism|Planningexpectedmove|Falsification/diagnostic|Source|
|R0|baseline|Freshhistoricalbriford4memberrecipe; establishactualtrain-onlyreferenceonbothholdouts|unknown|source/config mismatch or identityleak invalidatesreference|SuperCowPowers source inDEEPRESEARCH|
|C0|C|TabICLv2 onADME/CheMeleon PCA50/100: differenttabularprior→complementaryerrors→betterblend|rough−.005 to−.02; mayworsen|noimprovement/complementarityacrossinternalvalidation andouterreadouts|soda-inria/tabicl|
|C1|I|Monroe720d+TabPFN/TabICL: stereo/quantum/bioactivityrepresentation→differenterrors|rough−.01 to−.03; uncertain|alignmentfailure orpoorincrementalblendgain|Monroe|
|D0|D|DedicatedTox21CYPqHTS auxiliarydomains: matchingenzymebiology→morelocalactivitysupervision|rough−.005 to−.03; uncertain|no net-newcoverage or worsematchedablation|PubChem1671196/98/99/1201|
|D1|D|BindingDBnativearticle/patentIC50 andexpandedChEMBL/censoring: provenance-awareadditionalpotencies|rough−.005 to−.02; uncertain|duplicate/heterogeneousdata dominates ornoablationgain|BindingDBofficialdownloads;ChEMBL37API|
|E0|E|MAE/interval-awareloss vsMSE atfixedGNN: aligngradientswithsoftabsoluteerror|rough−.005 to−.02|metricgainnotreproduced orrankingcollapse|officialscorer; brifordMAEtemplate|
|B0|B|CatBoostMAE/Huber andExtraTrees smoothedleaves onmultifamilyfeatures: differentbias/variance→complementarity|rough0 to−.015|worseOOFandnoensembleweight|CatBoost/sklearnprimarydocs|
|G0|G|TanimotoKRR andsimilarity-weightedOOFresidualcorrection: localanalogstructure→queryspecificcorrection|rough−.005 to−.02|benefitconfinedtoleakedanchors orbadstructuralshift|TanimotoRFcode;MolPAIR|
|F0|F|Sharedimmutablefeaturecache/vectorizedkernels: identicalpredictionswithlessruntime→moreverifiedtrials|metric≈0;runtimeimproves|numericalmismatch ornoresourcesaving|RDKit/scikitprimarydocs|
|K0|K|TFM n_estimators8→32 orseedensemble atfixedfeatures: lowerinferencevariance|rough0 to−.005|gainunstableagainstpairedseedcontrol|TabPFN/TabICLsource|
|A0|A|Lowerfine-tuningLR withbest-valcheckpoint ondescriptorfoundation: reduceoverfitobservedbefore|rough0 to−.015|bestepoch/methodqualitynotimproved|priorCheMeleontrajectory;CheMeleonsource|
|C2|C|MoLFormer/UniMol2 frozenrepresentations: sequence/geometryview→diverseerrors|unknown;rough−.005 to−.02|truncation/conformerfailures ornoincrementalgain|officialHF/toolkitdocs|
Nextgenerations: useboardevidence tochooseunderexploredaxis; do notrepeatidenticaltweaks. Hypothesis candidates can be retained asensemblecomponents evenifstandaloneworse, ifinnerOOFcombinationhelps. No outer-label-fitting ofblends/calibration. Promotionrequiresheldoutverification; submissionrequiresuser'stwo-datasetconditionandactualTESTpredictions, notcachedlocalholdoutoutputs.

## Queued metamodel and confirmation design before gate results
Public pretraining audit disqualifies UNKNOWN-membership CYP-adapted weights from clean gate. R0 seed142 scheduled symmetrically. Prediction-side candidates: interval-endpoint forest on4baseOOFfeatures, and LP convex stacking (simplex+intercept) with L1shrinkage[0,.01,.1,1] toreference/uniform, choice onlydevelopmentcrossfit. Frozen model lists, no silent dropping. Final gate requires4targets, bothcohorts, bothseeds42/142, exactIDs/finitevalues and completedrunproofs. Both meanpairedseedscoredelta andscoreofmeanseedpredictiondelta must be<0 oneachcohort, noarbitraryeffect-sizeorbootstrapcutoff.

## New orthogonal angle P0: structure-only target-population placement
Before implementation/evaluation: a transductive domain classifier may estimate train-to-query structural density ratios; use these only to weight train-OOF interval-affine calibration. Actual query structures allowed, never query activity/interval labels. Compare fixed clipping/weight strength choices through development pseudoqueryfolds, thenapplyfrozenmethod toouter. Motivation: sourceauthor identifies analogue-enriched population shift, global calibration misses it. Reportthisasanexplicittransductivecandidate withallfeature/label boundaries; no claimofgainyet.

## Generation2 feature retention (afterC0 readout)
Originalfoundation TabICLPCA50/100 scores0.7806/0.7618 own750; no improvementovercheapstructurestack0.7339. Hypothesis: aggressive100dimcompression maydiscard endpoint-relevantinformation. Beforeevaluation compareTabPFN originalfoundation PCA512scaled/unscaled, PCA1024scaled, rawMolFormer768 andrawRDKit217. Keepknown-provenanceencoders; no claimthatdimensioncausesgainuntilobserved. Fixedrecipes, noquerylabel-preprocessing.

## Generation2 clean supervised representation transfer
Before any evaluation: reuse each fold's own trained neural encoder (officialaux/cleanTox21) as frozen representation, then fit TabPFN on thatfold'sofficialprimarytraininglabels. This tests the mechanismbehindstrongCYP-adaptedTFMresultswithoutunknowninheritedtrainingmembership. Never use anencoder from anotherfoldorfulltrain; verifyparentIDs/checkpoint/sourceconfig andouterexclusions. Comparemessage-passingfingerprint vsFFNlatent onlyifAPI clear; no extra neuralpretrainingneeded. Parentcheckpointselectionusesinnervalidation asalreadydeclared, outerclean.

## Generation2 metric-aligned target weighting
Before evaluation: existing direct/official_aux variants useequalperlabel weights, whereasofficialmacroST-RAE giveseachendpoint equalweight afteritsownsoft-distance denominator. Compareinverse-count MAE, inverse-count interval-MAE, andexactrelative interval weights sigma_j / sum_i distance(mean_training_y_j,CI_ij), normalizedmean1 acrossprimaryheads; auxweightsremain0.3. Allstatisticsfit-only. Thisisananalyticobjective-mismatch hypothesis, notameasuredgain.

## Generation2 clean3D representation control
Monroe iscurrentlystrong(roughly0.676/0.695) butsupervisedPCBA provenancepending. Test Uni-Mol2 84M self-supervised3Dfeatures (onlyafterverifyingpretrainingobjectivesandpinnedweights), then sameTFMlearners. Thisaskswhether3DpretrainingbenefitpersistswithoutinheritedCYPactivitysupervision; doesnotassumeMonroegaincausedby3D. Freezeversion/assets, exact5655IDalignment, conformerfailuresreported.

## Generation2 anchor residual correction
Beforeevaluation: useknowntraininganalogs tocorrect globalmodel bias. Anchorresidual=projectionofitsOOFpredictionontoexperimentalCI minusprediction (zeroinsideCI); Tanimoto-countneighbors transfer residuals. FixedgridK[5,20], powers[2,4], blend[0,.25,.5,1], selectiontrainingdevelopmentfoldsonly; optionallyfixedneutralK5,p4,blend.5 controlpredeclared. MolPAIR-inspiredlocalcorrection, notpaperreproduction. Noouterlabels enterfitting; exposecoverage/negativecases.
