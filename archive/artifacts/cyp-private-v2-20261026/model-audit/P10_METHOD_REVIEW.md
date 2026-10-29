# P10 material methodology review

Proceed with the proposed controlled continuation. The all18 continuation control distinguishes removing auxiliary gradients from simply training longer at low learning rate. The main comparison is primary4 versus all18 within each saved parent; the interaction across zero/repaired parents is secondary and conditional on those trained states.

The inspected P7R `night/p3_core.py:33–36` multiplies unreduced losses by sample weights, task weights and the real-task mask, but increments the denominator by all18 observed real-task cells. Keep `n_real=18`, all26 outputs, the8 bound carriers and saved target scalers. To remove auxiliary gradients, set numerator task weights4:18 to zero **after** loading the checkpoint; do not switch n_real to4 or let a checkpoint overwrite the new mask. This preserves the original primary loss scale before optimizer/clipping effects.

Verify parent epoch0 predictions, parameter/BN state, target scalers and descriptor transformations before continuation. Epoch0 must genuinely remain eligible under the same primary stopping metric; do not force a later checkpoint. Keep rows, batches/order, optimizer reset, LR policy, max epochs and patience identical across objectives. A batch with no primary observations must produce a connected zero tensor and follow the same declared step policy, not accidentally disappear or cause a backward error.

Optimizer momentum/weight decay and clipping can still change effective updates when auxiliary gradients are removed. The fixed denominator therefore does not imply identical primary parameter updates throughout training. Report selected epochs, the fraction of primary-observed cells and the actual loss mask. A null result does not establish that auxiliary data are intrinsically useless: the test is path-dependent continuation from these parents at this LR/budget, with no new label coverage.

No additional model fit or expansive audit is needed for this review. No paid resources or public action were used.

Concrete loader caution: the old P7R constructor sets warmup_epochs2, init_lr1e−4, max_lr1e−3 and final_lr1e−4. Resetting only optimizer state or its initial LR can retain an inherited Noam warmup to1e−3. Explicitly override the continuation LR/scheduler policy to the declared1e−4 and record effective LR, identically across all objectives.
