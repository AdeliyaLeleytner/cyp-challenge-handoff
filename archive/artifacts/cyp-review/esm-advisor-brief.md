# Independent Claude consultation

Round: 1

## User request

стоит ли использовать как-то белковую репрезентацию, может через ESM?

Prior constraints: user wants to compete in OpenADMET CYP Direct Inhibition Track and understand the reasoning in simple, sequential Russian. Earlier questions covered data construction, metrics, Chemprop vs CheMeleon, external data and auxiliary tasks. No training has started.

## Authoritative context and constraints

2026-10-23, Europe/Moscow. Workspace is the current CYP Inhibition directory. Deadline Nov 3 2026 23:59 UTC. This is an advisory/explanation request, not authorization for paid compute or submission. Follow the user's Claude advisory protocol: independent advice, no approval/veto, actual model/id recorded. Keep this consultation lightweight; no broad new literature search is needed.

## Current state

Official files and a prior evidence audit are in artifacts/cyp-review/sources/ and artifacts/cyp-review/evidence-notes.md. The latter contains prior Codex recommendations; avoid its recommendation sections for independence. No models trained, no measured local performance. Four fixed endpoints in both train and test: CYP1A2, CYP2C9, CYP2D6, CYP3A4. Sparse train: 4905 molecules / 6525 observed direct pIC50 cells; per endpoint n=1412,1285,1493,2335. Test 750 molecules, all four endpoints, structures disclosed and outcomes hidden. Test was selected as analogues of potent seeds for three of these CYPs. External/pretrained data allowed. Primary score equal-weight macro interval-distance ST-RAE. Single-concentration, Emax and TDI are additional training outputs, not available test covariates.

## Evidence and source map

- sources/dataset_README.md and sources/config.py: data and task.
- sources/tutorial_evaluation_custom_scoring_functions.py: actual interval scorer.
- https://github.com/facebookresearch/esm official ESM-2 implementation: both per-residue and averaged sequence embeddings; protein-only pretraining, separate downstream heads. ESM-2 does not itself take a small-molecule ligand as an input for pIC50 prediction.
- https://arxiv.org/html/2506.15792v2 CheMeleon descriptor-pretrained D-MPNN; can be used as molecular encoder and fine-tuned on these outputs.
- https://www.nature.com/articles/s42256-025-01124-5 Resolving data bias improves generalization in binding affinity prediction: search retrieval describes language-model feature gains depending on split. Full HTML access failed; not yet used as full-paper evidence. It concerns heterogeneous protein-ligand affinity, not this four-CYP assay.

## Work already performed

Read official ESM documentation and local ESM skill entry/source; reviewed task counts and setup. No ESM weights downloaded, no sequences fetched or embeddings calculated. Previous consultation discussed general competition strategy; this question specifically concerns protein representation and has not been independently assessed.

## Questions for independent assessment

1. What value, limitations and priority would protein representations have for this fixed-four-target task, including if external training data are added?
2. What small controlled comparison would distinguish useful protein-sequence information from generic target identity or extra modeling capacity?

## Known missing or inaccessible information

No empirical comparison of target IDs versus sequence embeddings, no compute budget, no curated external protein-ligand dataset. Exact experimental construct sequences have not been verified. No evidence of performance gain in this challenge.

## Codex position

withheld for independent first-round assessment.

## Confidentiality check

Only public scientific information and current user request; no secrets or unrelated personal information.
