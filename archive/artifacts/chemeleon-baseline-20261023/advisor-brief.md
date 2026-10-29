# Independent Claude consultation
Round: 1

## User request
Давай обучим бейзлайн: chameleon на трейне и посмотрим что получается. Сделав только хороший сплит
Prior context: user means CheMeleon. She asked for simple Russian explanations and now explicitly authorizes a bounded baseline on official training data, with a good split. No auxiliary or external activity data, model sweep or submission requested.

## Authoritative context and constraints
2026-10-23 Europe/Moscow, root CYP Inhibition workspace. Local machine Apple M3,24GiB RAM; orx default local. An asynchronous question asks local Mac / LAB23 / paid GPU budget; pending. No spending or VPN access without user choice. User requires independent advice and verification. No new literature search needed; source and audit files below are authoritative evidence. Do not broaden task.

## Current state
No trained baseline or frozen split yet. All public train/test structures and interval targets downloaded. Prior structural audit executed. Need choose defensible one-run split and evaluation design before inspecting model outcomes. Project is an empty-initial-history Git repo with untracked artifact reports. Will use immutable source/run logs.

## Evidence and source map
- artifacts/chemical-space-audit-20261023/report.md, summary.json, controls_summary.json, verification.json, test_coverage.csv, similarity_matrices.npz, all_molecule_structures.csv and analyze.py/controls.py: audited data geometry.
- 4905 train,750 blind test. Observed direct labels 1A2=1412,2C9=1285,2D6=1493,3A4=2335; only41 train molecules have all4.
- 4519 exact nonempty Murcko train scaffolds;4354 singleton molecule groups. At most375 molecules can be held out while retaining a same-scaffold representative for every query. Test has546 scaffolds;184/750 seen in train.
- Test NN median to fulltrain .587; per-labelled-endpoint .517/.518/.471/.538. Random80/20 val median .437. SAME reference pool control gives test .570,val .437. Murcko group almost same as random. Within Butina0.6 holdout gives167 molecules median .663, with only~27/22/25/122 labels across endpoints. Cannot blindly call ordinary scaffold split a test mimic or a tiny within-series cohort a full validation.
- similarity_matrices.npz contains train_train and test_train float32 matrices. The primary fingerprint is Morgan radius2,2048bit,chiralityFalse on RDKit Cleanup+FragmentParent; no cross identity overlap. Stereo-stripped parent keys have4 duplicate train rows; keep those grouped or explicitly justify treatment.
- artifacts/cyp-review/sources/cyp-challenge-TRAIN_inhibition.csv and official scoring functions/config: interval distance normalized by evaluated-set constant-mean interval error; arithmetic macro; 1000 compound bootstrap replicates. Bounds only for scoring targets, not inference features. Missing labels masked.
- Official authors' fine-tuning notebook https://raw.githubusercontent.com/JacksonBurns/CheMeleon/main/finetuning_demo.ipynb read this turn: checkpoint https://zenodo.org/records/15460715/files/chemeleon_mp.pt, torch.load weights_only=True, nn.BondMessagePassing(**hyper_parameters), load state_dict; SimpleMoleculeMolGraphFeaturizer; MeanAggregation; new RegressionFFN(input_dim=mp.output_dim); MPNN batch_norm=False; train-only target scaler; example max_epochs20.

## Work already performed
Reviewed audit, verified local hardware and orx backend configuration, read current authors' notebook. No training launched. Preparing environment and split independently of pending resource response.

## Questions for independent assessment
1. What is a defensible concrete split and checkpoint/evaluation protocol for ONE CheMeleon baseline in this geometry, without a sweep or pretending exact test-distribution matching?
2. What minimal implementation choices and checks are necessary to ensure we train the intended pretrained model and obtain meaningful macro ST-RAE, while respecting the requested scope?
Return a compact answer. Do not propose remote expenditure, additional model families or an unbounded experiment queue.

## Known missing or inaccessible information
Test labels and intervals hidden; no historical75seed map; actual MPS/CUDA throughput not tested; compute choice pending. No model results for split selection.

## Codex position
withheld for independent first-round assessment.

## Confidentiality check
Public scientific data and task only; no credentials, secrets or unrelated personal information.
