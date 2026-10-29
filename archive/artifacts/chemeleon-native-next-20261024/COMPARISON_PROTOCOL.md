# CheMeleon, ST-RAE objective, ADMETlab comparison

This campaign follows the user's three specified interventions. It is not an unrestricted architecture search.

## Common data and evaluation

The native briford reproduction is the control. The four component pools use 18, 8, 6 and 1 tasks, respectively, from the official challenge data and the existing public ChEMBL/Veith augmentation. The exact outer-purged prepared tables and inner folds from the completed native holdout run are reused byte-for-byte. All models are retrained independently for own750 and briford529; these outer cohorts overlap in 143 molecules. They are two validation views, not two independent confirmation samples.

No outer molecule, parent-equivalent or connectivity-equivalent molecule is retained in any component training pool, including auxiliary tasks. Missing labels remain missing. Five inner folds per component and four components produce 20 fits per outer cohort, 40 fits per experimental recipe.

Evaluation uses the stored official scorer (SHA256 c0ee287c06c0301d4b3bfd74559b90eb1bd85db68b75b7d018ae92280c0e1dd3). Lower macro ST-RAE is better. A score of 1 is the constant mean-truth baseline under this scorer. Raw predictions and the author's placement procedure with fixed published constants are reported separately. The placement was designed for the challenge test distribution. Its numerical affine coefficients are recomputed from each recipe's inner-OOF correlations and query prediction distribution using unchanged published constants; outer holdout labels do not fit these coefficients.

## Recipes

1. Native control: four Chemprop components initialized from scratch, native MAE objective, original optimizer and flat component/fold averaging.
2. CheMeleon MAE: same data, inner folds, auxiliary tasks, FFN and optimizer settings. Replace the native message-passing block with the pretrained CheMeleon block and fine-tune all its parameters. Encoder width/depth/aggregation also change; this comparison does not isolate pretraining alone. Pretrained checkpoint SHA256 c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651.
3. Scratch ST-RAE recipe: primary interval-distance objective with fit-only target denominators and target scales; per-auxiliary-head mean MAE with explicit nominal task budgets; primary validation ST-RAE checkpoint selection.
4. CheMeleon ST-RAE recipe: recipe 3 with the same CheMeleon replacement as recipe 2.

The first FP16 GPU attempts of recipes 3–4 produced nonfinite validation predictions and no complete ensemble result. Their outputs are retained as failed numerical attempts, not scores. Repair 1 uses BF16 training and explicit FP32 validation, with strict nonfinite state diagnostics. This also changes numerical precision relative to the original MAE controls; attributing differences solely to the mathematical loss would be unjustified. The mathematical full-sample objective, unbiased minibatch scaling, official-score parity, target transforms and checkpoint reload were checked before launch.

No learned meta-stacker is introduced. The existing 'stacking' is the author's flat averaging plus the separately reported native affine placement procedure.

## ADMETlab branch

The queue contains 32,421 canonical isomeric SMILES: 5,655 official train/test structures first, followed by 26,766 additional public structures. All returned endpoint identities, including CYP endpoints, are retained. These are model-generated descriptors/pseudolabels, not additional experimental ground truth. Feature alignment is explicit; imputation and scaling are fitted on each inner training fold only. ADMETlab's historical training membership is unknown and remains a limitation even after our own outer exclusion.

Initial single-molecule API attempts returned HTTP 429, followed by a successful same-IP/same-payload request after a 45-minute cooldown. The documented web batch route then returned three complete rows with 120 actual endpoint columns, including explicit raw SMILES. Its predictions differ from the API feature=true mode, so the acquisition and feature experiment use web_default consistently and never mix the API probe vectors. The three empty legacy API columns are not fabricated. Full acquisition is being prepared on a separate low-cost instance; there is no ADMETlab scientific score yet. The eight-GPU training instance was recovered and destroyed after all 120 new model fits completed.

## Decision

Report every completed recipe on both holdouts and all four CYPs. Do not tune blend weights or affine placement on the outer holdouts and present that as a fresh held-out result. Retain adverse cases. The existing rank-27 submission is a separate full-data artifact and is unchanged by these holdout experiments. Any new submission requires a concrete selected recipe, full-data fitting and the applicable submission rules.

## Acquisition outcome at 16:28 UTC

The first 100-molecule web-default batch on the inexpensive instance was rejected with HTTP 429, without Retry-After or a specific explanation. The client stopped without retry or IP switching. Three earlier contract probes succeeded, but there is no complete queue feature matrix and no trained feature-arm result. Both cheap instances were recovered/destroyed and confirmed absent. The feature experiment remains prepared at commit 4ab5b103dc5961bce6c1a93b78b428708b9fc1a2. Input-only batches are available in admetlab-ready-batches.zip. This is an external acquisition blocker, not a negative score for ADMETlab features.
