# Competing hypothesis: molecule-dependent convex blending

**Question.** Can ADMETlab features tell us where to trust the native CYP model versus an ADMET-feature model, beyond a fixed average? The practical consequence would be to retain the native model on chemistry where the teacher is unreliable while taking more of the teacher-derived signal where it helps.

## Evidence motivating this construction

Our 500-molecule pilot found that simple native+ADMET blends improved point ST-RAE on both available holdout subsets, whereas more flexible residual corrections using 120 features worsened both. The subsets were only 60 and 54 molecules; paired intervals included zero, and MAE worsened on one subset. Thus there is evidence of complementary signal, not yet evidence of a reliable conditional reliability model. [Pilot evidence](../../admet500-pilot-20261025/RESULTS.md)

Briford's current public script weights predictions per molecule using confidence/error correlations measured out of fold. That provides a concrete alternative to flat averaging. Its reported OOF gains do not establish our expected gain or explain his latest live score, which is worse than the historical entry. [Pinned script](https://github.com/SuperCowPowers/workbench/blob/873bd9ed872ff89427128f68f210889ffa21ae68/ml_pipelines/OpenADMET/cyp/scripts/cyp_ensemble_submit.py)

Stir_bar reports that unconstrained positive/negative stacking coefficients transferred badly, then restricts stacking to nonnegative combiners and caps embedding dimension. This motivates a small, conservative gate rather than another unconstrained residual regressor. [Pinned write-up](https://github.com/lachrymator/openadmet-cyp-challenge-public/blob/6afb664e6fb22c516952e020273ba91442f426db/README.md)

## Executable hypothesis

Freeze the same two experts used in the strongest simple-blend control:

- `N_it`: native full-pool ensemble prediction for molecule i, CYP t.
- `A_it`: the selected ADMET120-feature expert's pIC50 prediction for that same molecule/endpoint. This is a model trained against challenge labels, not a raw ADMETlab inhibition probability converted into pIC50.

Fit the best **per-CYP static convex weights** `w0_t` on training OOF predictions. This stronger static control is necessary: comparing a per-CYP gate against only the pilot's single shared weight would confound molecule-dependent weighting with endpoint-specific calibration.

Define a compact reliability vector `z_it`: eight training-fitted PCA coordinates of the standardized ADMET120 block; absolute expert disagreement `|A_it-N_it|`; native disagreement across component-family means; and the corresponding ADMETlab `CYP*-inh` probability. Scale these covariates using training data only. Eight PCA dimensions is an initial capacity setting, not a claimed optimal value or scientific success threshold. Do not describe classification probability as calibrated uncertainty.

Use eleven shared slopes, with the per-CYP static intercepts inherited:

```
w_it    = clip(w0_t + beta · z_it, 0, 1)
pred_it = (1 - w_it) * N_it + w_it * A_it
```

Fit `beta` on training OOF predictions using the interval-aware macro ST-RAE objective, with shrinkage toward `beta=0`. Select any shrinkage setting using only inner training folds. The denominator and endpoint weighting must be identical for the static and gated comparisons. At `beta=0`, the candidate exactly recovers the per-CYP static blend. Its output cannot extrapolate beyond the two expert predictions for that molecule.

**Mechanism.** A constant weight averages over subregions in which the experts' relative errors differ. If ADMET features and disagreement predict those subregions, varying the weight should lower interval error without permitting the large cancelling coefficients or unrestricted residual shifts implicated in the earlier failures. This tests conditional expert selection; it does not yet test a new molecular representation or a new source of experimental information.

## Matched experiment in the 32,421-molecule setup

Keep base checkpoints, preprocessing, external auxiliary heads, allowed molecule pool and seed/fold assignments identical. The external compounds can train the base experts using their appropriate auxiliary labels; they do **not** become 32,421 same-assay labeled gate examples. Fit the gate only on observed official direct-inhibition labels. Exclude each outer holdout from all base training, supervised auxiliary sources, preprocessing fits, calibration and gate fitting under the existing purge rules.

For each of own750 and briford529, compare:

1. Native predictor alone, for context.
2. Best training-OOF per-CYP static convex blend, the decisive matched control.
3. The conditional convex blend above, on exactly the same expert predictions.
4. The same gate with ADMET/reliability covariates shuffled between training molecules, retaining the static intercepts and identical capacity, as a mechanism check.

Construct native disagreement from component-family means in both OOF and inference. Do not compare two OOF component predictions with twenty test-time fold members and call the resulting variance the same feature. If this feature cannot be made consistent, omit it from both the real and shuffled gate rather than silently changing its definition.

Report exact ST-RAE, MAE, R², Spearman and Kendall, per CYP and macro, with paired molecule/bootstrap uncertainty and the known overlap between outer holdouts. Report weights and relative expert errors across chemical families/similarity regions. Keep any final blind-population placement separate and identical between comparisons.

## Forecast, failure observation, and next step

My weak forecast is **lower macro ST-RAE than the strongest static blend**, with an additional absolute gain roughly **0.005–0.02** if the reliability covariates transfer. This is an uncertain planning forecast, not a pass/fail criterion; zero benefit or degradation is entirely plausible given the pilot's negative flexible corrections and the public CV-to-blind gaps.

The mechanistic claim fails in the intended setting if the gate's weights do not favor the locally less erroneous expert on held-out molecules, static blending matches or beats it on both outer holdouts, and shuffled covariates perform similarly. If the differences remain poorly resolved, call the result inconclusive rather than claiming conditional benefit. A gain confined to a global shift or one CYP is not evidence for molecule-dependent reliability; that is why the per-CYP static control is essential.

The next bounded step is to inspect training-only OOF relative errors against these covariates, then fit one gate and its matched controls after the complete feature matrix and expert OOF predictions are frozen. It needs no new base-model GPU training if those predictions already exist. No fit, submission, compute rental, or spending was performed for this proposal.
