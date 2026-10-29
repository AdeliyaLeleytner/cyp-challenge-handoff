# P8c independent staged-data and condition-routing audit

**PASS for the inspected stage and source hashes.** No scientific model fits, optimizer steps, data acquisition or paid resources were used by this auditor. Stage/code ownership remains with the training agent.

## Data, maps and folds

The31,641 row IDs, exact model SMILES, request IDs and order are unchanged from the repaired P7 table. The18 existing target columns and all8 primary interval carrier columns are numerically identical. All29 exclusions and allfive repaired train/stop/test index lists are unchanged; therefore the previous whole-row source/equivalence purges apply to all22 tasks, including the new active tasks.

The four added active columns match the original TDI table exactly under the declared ID join:1413/1285/1495/2378 finite cells for1A2/2C9/2D6/3A4, total6571. No new row, inferred value or normalization is introduced. B/C/D consume the same cells; A masks all four active labels. The earlier source/model isomeric-graph audit and preserved exact source identity support this join.

Frozen selected-map file SHA256 is `be16dd34c6776312e73707acd0c0e0dff1823c32267b20f76af8263f3c6aa9d8`; selector membership SHA256 is `c35da59a6d34041e74c57dea996d7395e3022669bb102d2fc121162a834aab64`. Both are byte-identical to P8b. Every one of20 maps is selected by its own outer fold and CYP, and every map’s exact molecule/request training IDs reproduce that fold’s post-purge paired active/screen rows. No nuisance refitting occurs in the graph runner.

Stage certificate: STAGE_CERTIFICATE.json. Manifest SHA256 `6f5ae8f88db9bad8bd71c8eba2ebf00d09675ecb44992ab195bfc45fd6b61c47`.

## Routing and loss arithmetic

The inspected ConditionLoss correctly performs:

- A/B: unchanged free screen outputs.
- C: unscale standardized predicted active head18+j to raw pIC50, apply its frozen map, then standardize the resulting raw log2FC with the screen target’s training scaler exactly once.
- D: the same sequence using direct headj and the identical active-trained map.

Screen output positions are7/5/6/4 for1A2/2C9/2D6/3A4. Each is replaced in its existing loss slot; there is no additional duplicate screen penalty. The unused free-screen predictions do not create a bypass in C/D. All map tensors are fixed buffers with no trainable parameters.

The denominator is batch size×22, independent of missing or masked label count. Masking A’s active labels does not rescale primary coefficients. All8 interval carriers are excluded from loss. Row weights remain uniform. Chemprop’s inspected training_step creates the finite mask and replaces NaN targets with0 before invoking the criterion, so missing values are not treated as observations.

Forward/autograd arithmetic checks covered all5folds×4arms and all four single-screen masks, using nontrivial target scales. Only the intended free-screen/active/direct input received a screen-loss gradient. Direct gradient coefficients stayed identical when active labels were masked; carrier gradients were zero. The loss matched an independent single-screen calculation with denominatorB×22. Independent NumPy evaluation of the saved maps agreed with the float32 implementation within maximum absolute discrepancy2.86e-6 at the tested values. Raw auxiliary export agreed with the effective standardized output after one inverse scaling. These were arithmetic tests, not model fitting.

Routing certificate: ROUTING_CERTIFICATE.json; inspected core SHA256 `9cb73df09ecf26caf1459b290cdcd05c3f745622c1087428d542134cd276604c`.

## Runner inspection

The runner uses one shared22-target table and repaired folds for every arm. Target scalers fit post-purge training rows only. A’s unused active heads have identity scales and masked values; all existing18 scales are fitted identically. B/C/D use all22 training target scales. Per-fold map selection explicitly matches outer-fold ID and CYP and rechecks exact paired-training membership digests.

The graph has30 outputs:22 real heads plus8 primary interval carriers. Stopping uses direct predictions only, correctly unscaled, with bounds22:26 and26:30. The empirical screen route is not used for checkpoint selection. Export preserves direct/active raw predictions and replaces only the relevant auxiliary screen outputs. Auxiliary heldout errors/extrapolation are recorded as diagnostics, not checkpoint criteria. Shared initialized parameter and BatchNorm buffer hashes are checked across the four arms in the orchestrator.

The current config is a three-epoch fold0 smoke; it is implementation/runtime evidence only. Any full authorized run must retain these scientific paths and hashes or expose its explicit code diff. This audit does not replace the training owner’s smoke, checkpoint recovery or spending controls, and adds no new protocol factor or approval requirement.

## Scope limits

This confirms implementation of the declared empirical contrast, not a kinetic interpretation or predictive gain. The frozen map was selected using paired measured active-potency observations; application to predicted potency/unpaired screen compounds can shift its input distribution. A/B versus C/D intentionally differ in effective screen-function flexibility. C/D is the matched routing contrast. Unknown assay normalization/efficacy and teacher-free molecular model uncertainty remain scientific limitations.

All files remain private. The audit scripts read stages and produce only this audit folder’s certificates; they do not modify training source or data.
