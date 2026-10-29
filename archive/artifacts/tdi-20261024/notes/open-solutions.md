# TDI public solution audit — 24 October 2026

This is an audit of public methods and code, not our model-training results. Live source: [official challenge](https://huggingface.co/spaces/openadmet/cyp-challenge), fetched from verified Gradio API `/partial_5`; raw response and CSV saved in `../sources/tdi-live-response.sse` and `../sources/tdi-live.csv`. All HTTP-linked rows were inspected regardless of the Open Code checkbox. Top ten currently have no report link; nova leads at macro MCC 0.5751818771. No briford TDI row exists in this snapshot; its linked blog concerns direct inhibition, with TDI only an auxiliary label source.

## Ranked public candidates and accessibility

| Live rank | Entrant | Macro MCC | Public evidence |
|---:|---|---:|---|
| 11 | [450nm](https://openadmet-cyp-dashboard.vercel.app/operating_dashboard) | 0.409132 | Linked dashboard and site root both HTTP 404; not reproducible from available link. |
| 14 | [jeremy](https://github.com/jeremycheminf/openadmet_scripts/tree/main/CYP_Challenge) | 0.402470 | Runnable public reproduction kit + 2 encoder checkpoints. Highest verified runnable public TDI recipe. |
| 17 | [Nomad-link-id](https://huggingface.co/Nomad-link-id/openadmet-cyp-methods) | 0.398655 | Methods-only Hugging Face repo: README + .gitattributes, no code/weights. |
| 20 | [stir_bar](https://github.com/lachrymator/openadmet-cyp-challenge-public) | 0.391827 | Explicit writeup-only repo, README/images/LICENSE; no training code. |
| 29 | [rasayan-labs](https://github.com/whis9/rasayan-cyp) | 0.365325 | GitHub metadata accessible; tree request HTTP409 (empty repository). |
| 36 | [JacksonBurns](https://github.com/JacksonBurns/cyp-challenge/tree/86213d34157eeeea7635b6943c3f8c3798548514) | 0.342242 | Detailed source + OOF/test prediction caches; final submission rebuild supported, fresh GPU model retraining not packaged end-to-end. |
| 48 | [happy-halloween-scott](https://github.com/HauserGroup/spooky-cyp-challenge/blob/master/README.md) | 0.320545 | Runnable training/inference with retained fitted TDI ensemble and frozen settings. |
| 55 | [CompChem Magicano](https://github.com/mokhalaf22/openadmet-cyp-public) | 0.309655 | Public code, pinned data, detailed report/experiments; classifier shares D-MPNN regression trunk. |
| 62 | [talindrew](https://github.com/Arnab28122000/openadmet-cyp-challenge) | 0.296400 | Public code and detailed experiments/report; no stronger TDI result than Jeremy. |
| 70 | [jyamvwa](https://github.com/Jackson-yamvwa/DrugDiscovery-Py/blob/main/openadmet-cyp-challenge/METHOD_REPORT.md) | 0.287478 | Public code and method report; LGBM + Tanimoto-neighbour TDI. |
| 79 | [Woong](https://gist.github.com/ByungwoongYoo/4904441a9b30db077fbb784f9c22e423) | 0.277442 | Methods-only gist; full package retained locally by author, not published. |
| 80 | [adlvdl](https://github.com/adlvdl/cyp_competition) | 0.276766 | Public experiment code; nested scaffold-CV tree baseline and extensions. |
| 84 | [Lizard Wizard Gizzard](https://github.com/doctawho42/CYPChallenge/blob/main/docs/method_report.md) | 0.270095 | Public code and detailed method report; mechanism-inspired potency/shift conjunction. |
| 95 | [FreeT4-CYP](https://huggingface.co/spaces/momo00798/freet4-cyp-method) | 0.254461 | Public methods HTML only (HF Space contains README/index.html/style.css). |
| 109 | [ademmanlincoln07](https://github.com/AdemolaTolulope/cyp-inhibition-profiler) | 0.232000 | Public repo, scaffold CV tree ensemble; README primarily regression. |
| 124 | [nkwork](https://github.com/nkwork9999/mollibra-challenges/blob/main/reports/openadmet_method.md) | 0.174788 | Public code/report; random holdout tree/linear baseline, weak TDI. |
| 127 | [HBI](https://huggingface.co/buildingpeps/hbi-cyp-challenge-v2) | 0.155726 | HF method card describing fixed linear/ExtraTrees model selection; weak TDI. |
| 137 | [dargason](https://admet-cyp.aetherark.com/classification-submissions.html) | 0.040691 | Linked classification report HTTP403; not verified/reproducible from accessible report. |

## 1. Jeremy: primary reproducible baseline

[Code](https://github.com/jeremycheminf/openadmet_scripts/tree/d3a5549e0c98167435cbf8f5115c68a9a184ed7a/CYP_Challenge), current commit `d3a5549e0c98167435cbf8f5115c68a9a184ed7a`.

**Two TDI members:** (i) LightGBM on radius-2 2048-bit Morgan fingerprints and RDKit2D descriptors, 500 trees, learning_rate .05, 31 leaves, subsample .8, feature_fraction .8, random_state42, class_weight balanced; (ii) TabICLClassifier(n_estimators=8, device=cuda, random_state42) on frozen `chemprop_medium` encoder embeddings, median imputation + StandardScaler + PCA200. Frozen encoder is publicly supplied and pretrained on external ADME/CYP data; this is not a model trained only on official TDI labels.

**Validation:** Butina Morgan similarity cutoff .6; five whole-cluster folds, largest clusters placed into smallest fold, seeded tie breaking42. LightGBM and TabICL fit separately per enzyme. Test prediction comes from one all-labelled-data refit per member/endpoint, not averaging fold models.

**Ensemble:** both members save hard class predictions, NOT probabilities. Caruana bagging defaults20bags, half candidate library, seed42, max50 iterations; with exactly2 candidates bag size is1, so no within-bag learner selection actually occurs. Final hard-vote mixture threshold is selected on pooled OOF MCC over .05,.075,...,.95. Threshold/ensemble fitted on same OOF rows reported as final OOF score; that score is selection-optimistic. PCA also fit globally before CV, an unsupervised transductive preprocessing choice; strict evaluation should fit transformations inside each development partition/fold, with native-recipe and corrected-comparison labels distinguished.

**Critical score caveat:** README reports kit OOF macro MCC .283 versus full research ensemble .312. The live Jeremy .4024704 and official Interim .3868 are official submission results, NOT demonstrated exact scores for this trimmed two-member current kit. Do not claim that reproducing this kit necessarily reproduces the leaderboard binary file. README regression true-blind section itself distinguishes broad research ensemble from kit. Public external encoder label membership needs audit before calling local holdouts completely unseen.

**Useful improvements:** probabilities instead of hard votes; fold-local preprocessing; inner-only threshold/blend selection followed by locked outer evaluation; frozen second encoder/alternative tree or kernel representation only if it adds genuine signal.

## 2. Nomad: strong transferable idea, no code

[Method](https://huggingface.co/Nomad-link-id/openadmet-cyp-methods). Official challenge measurements only; pretrained CheMeleon indirectly through potency predictions. Five Murcko-grouped folds common to all models. TDI is class-balanced LightGBM on ECFP4/descriptors plus OOF blended pIC50 features; test gets blind-set potency predictions. The author explicitly corrected earlier in-sample potency feature leakage. Must regenerate features within outer training splits; globally OOF potency is insufficient if its training includes outer-validation measurements.

Reported local MCC CYP2D6 .133 / CYP3A4 .435 at final thresholds .42 / .50. CYP3A4 maximum OOF MCC .490 occurred at .13-.14, but implied ~60% test positives; author chose .50 with ~34% positives. CYP2D6 ~7.1% test positives. This is a method-level reconstruction opportunity, not exact code reproduction.

## 3. Stir_bar / lachrymator: best-known writeup with diverse encoders

[Report](https://github.com/lachrymator/openadmet-cyp-challenge-public). Explicitly writeup only, no source or checkpoints. Public bioactivity masked multitask pretraining, sequence-transformer / message-passing / 3D / frozen-embedding tabular / fingerprint / additive-fragment members. Butina cluster-disjoint folds; nonnegative per-endpoint stacking. Retrieved88,683 public near-neighbours of test, admitted4,999 with computed properties only; not extra measured TDI labels. Computed-property heads downweighted.

Author reports historical CV MCC .270 CYP2D6 / .554 CYP3A4 and Interim .256/.504 (macro .380, rank6). Current live .3918274 is a later snapshot. Exact architecture hyperparameters, seeds, thresholds, training code and artifact-to-submission mapping are absent, so cannot promise exact reproduction. Their direct encoder heads reportedly outranked tabular legs on classification; indiscriminately adding correlated tabular learners harmed an endpoint. Useful hypotheses, not independently verified causal facts.

## 4. JacksonBurns: richest public cached research pipeline

[Pinned repo](https://github.com/JacksonBurns/cyp-challenge/tree/86213d34157eeeea7635b6943c3f8c3798548514), [reproduction instructions](https://github.com/JacksonBurns/cyp-challenge/blob/86213d34157eeeea7635b6943c3f8c3798548514/docs/REPRODUCTION.md). TDI v5: classical/frozen embedding LGBM, TabICL classic/chemprop/external representations, four UMTM `is_TDI` families. Five scaffold folds, nested weights, max family weight .5. Standardize member probabilities then weighted sum. Final target positive fractions .15 CYP2D6/.24 CYP3A4 (112/180 positives), chosen using public-board prevalence prior. Reported nested capped MCC .3404; official live .3422420. Trained member OOF/test caches public, GPU retraining explicitly not packaged end-to-end. Copying cached full-train predictions into our holdout evaluation is invalid; can only reproduce final existing-panel file or reimplement/train leakage-safe members.

## 5. HauserGroup: best complete additional recipe, cheap CPU reproduction

[Code](https://github.com/HauserGroup/spooky-cyp-challenge/tree/06e1e1fcf7341333e4623ce353c65c6b4b6e71f3), commit `06e1e1fcf7341333e4623ce353c65c6b4b6e71f3`. **No external/pretrained component in TDI.** Uses ALL observed official binary labels:2D6 n1497/324 positives;3A4 n3584/764 positives. Do not restrict to paired potency-arm rows.

Structure branch: LightGBM 200trees, lr.03, depth7,63leaves,min_child20,colsample.4,L2.5,unweighted; features MACCS167+torsion1024+AtomPair1024+Avalon1024+RDKitPattern1024+16descriptors. Screen branch: HistGradientBoosting150iter,lr.1,31leaves,min_leaf20,L2=0 using16descriptors+one predicted same-enzyme primary screen response. Auxiliary LGBM regressor200trees,lr.05,15leaves,colsample.5 predicts screen from descriptors. All screen inputs are predictions; nested threefold cross-fitting inside each outer train; outer heldout compounds lose all measured auxiliary labels.

3repetitions x5 compound folds seeds0,1,2, canonical duplicate structures grouped, joint label pattern stratification (NOT scaffold folds). Mean OOF probabilities over3heldout fits; test probabilities average15folds. Fixed structural weights .95/.60 for2D6/3A4; MCC-optimized OOF thresholds .277519153/.308474826;90/234 test positives. Local calibrated macro .2860 (same OOF labels used for thresholds), official live .3205448. Full training/inference scripts and retained TDI model exist. Reproduce algorithm on our frozen splits, with inner threshold selection, rather than treating their threshold-fitted OOF score as independent performance.

## Lower-scoring approaches and constraints

- Mokhalaf `bbf1c364369efa6df97acd1c8ef9db16655ee6c1`: shared D-MPNN regression encoder + binary classifier superior to deriving TDI from predicted positive potency shift; final cutoffs .30/.45. Report excludes missing direct arms, which discards useful official binary labels. It also documents public same-lab Octant test-compound contamination: quarantine those overlaps before ingestion. Code exists; live .3096554.
- Jy­amvwa `722ca519a3773904b355ab013cece8c069496f14`:2D6 ten-neighbour Tanimoto classifier threshold.26;3A4 LightGBM threshold.18; selected on random OOF then scaffold stress. Live .2874782. Useful independent cheap representation.
- Woong gist revision`f920368fa62f855b162df149a1e97bde9eebe28f`:five tree/kernel/SVC/multi-assay branches, Platt+nonnegative logloss stacking, smoothed-MCC thresholds, nested cluster splits. Package private/local; report only. Live .2774425.
- FreeT4 report only: Morgan counts+RDKit, MLP512/256, dropout.15, multitask targets, scaffold development/holdout, thresholds.21/.21; holdout macro .2159. Live .2544609.
- HBI method card: parent/scaffold/similarity connected-component60/15/15/10partition, linear/ExtraTrees menu, independent calibration/policy selection; no competitive score.
- Other lower-scoring links and raw sources are retained in sources. Do not reproduce every weak method just because source exists; strongest useful set is Jeremy native baseline + Hauser structure/screen + genuinely distinct probability/kernel/encoder candidates.

## Practical comparison protocol

Keep our outer holdout, public-recipe split, inner model-selection and final full-data refit distinct. Every molecule's auxiliary endpoints follow its outer group; unknown labels stay missing. Fit ensembles/calibration/thresholds on inner OOF only. Report per-enzyme MCC and macro MCC, AUROC/PR and positive-call counts; compare frozen methods on identical rows. Target-prevalence/rank thresholds are a separate transductive hypothesis, not an automatic consequence of high training MCC. Public leaderboard results are bootstrap means and may differ from direct point MCC. A successful local improvement does not guarantee ranking versus a public entry whose actual full ensemble is unavailable.

Primary source for Interim: [official halfway post](https://openadmet.ghost.io/halfway-through-the-openadmet-cyp-challenge/) lists Jeremy #3 .3868, stir_bar #6 .3796,450nm #22 .3457; all Tier1. Live ranks alone should not erase that broader evaluation.
