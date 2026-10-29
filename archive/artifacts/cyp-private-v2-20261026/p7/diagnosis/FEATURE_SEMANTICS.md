# P7 ADMET feature semantics and chemical diagnosis

The120 inputs contain useful CYP association **and** a concrete descriptor-scale defect. Neither observation alone explains P7’s worse held-out predictions. The strongest verified chemical issue is the service’s enormous reported molecular-volume values for85 retained B/Si/As/Se/Sb/Hg compounds, which collapse ordinary volume variation under the actual training StandardScaler. Separately, CYP classifier probabilities are not direct-inhibition pIC50, and considerable probability mass lies near0 or1. The paired-analogue analysis tests whether their quantitative signal survives locally; it must not be replaced by an assumption that saturation caused the failure.

No new prediction-service request, literature retrieval, model fit, rental, chemical standardization or dataset edit was performed. These are read-only feature/association diagnostics on the exact P7 inputs. Model-audit owns P7’s six reported performance measures and paired uncertainty; challenge-audit owns checkpoint interventions. This report does not substitute feature correlations for those performance results.

## What the120 columns actually are

The exact taxonomy, original display names and provider explanations are in feature-taxonomy.csv. It separates:

| Group | Count | Interpretation |
|---|---:|---|
| Structure-derived descriptors and fixed scores |19|14basic physical/topological descriptors plus QED, synthetic accessibility, Fsp3, MCE-18 and NP-likeness. Fragment scores may encode corpus-derived priors; they are not measured bioassay labels. |
| Structural alerts and filter rules |16|Eight medicinal-chemistry filters/alerts plus eight toxicity-rule endpoints. List-valued atom matches were converted to match counts by the frozen parser; counts retain less information than the actual matched pattern/positions. |
| Named CYP inhibitor/substrate predictions |13|Seven inhibitor and six substrate classifier outputs, including auxiliary isoforms. They are not quantitative potency measurements. |
| Other modeled ADMET properties |71|A mixture of probabilities and quantitative predictions, including seven learned physicochemical properties, ADME, toxicity and assay-interference/synthesis predictions. |
| Underspecified CSV-only score |1|Other_assay_interference, numerical0–1 output, but the saved detailed explanation is empty. Its probability/class semantics are not certified from range alone. |

Across the84 defined model outputs,66 are documented classification probabilities and18 are quantitative regression predictions. These numbers differ from the earlier conservative audit’s64 probability checks because this semantic inventory also recognizes explicit probability explanations in the returned schema. It does not modify the audited feature cache or its contract.

**logP, logD7.4, logS, acidic/basic pKa, melting point and boiling point are modeled outputs here**, not automatically independent RDKit descriptors. MW, atom/ring/bond counts, TPSA and formal charge are structure-derived. Lipinski/Pfizer/GSK/GoldenTriangle are fixed rule definitions, but the saved docs do not establish which internal logP/logD estimate supplies every rule; do not claim exact algebraic identity to the separately returned learned property.

The official API distinguishes numeric values from0/−1/1 decision flags. P7 uses the numeric values, not the service’s pass/warning/danger decisions. A classifier value0.99 is not99% experimental inhibition and cannot be converted to pIC50 without a separately justified observation model.

Documentation caveats are retained: the CYP substrate **display names and dataset table identify substrate classifiers**, but their live explanation strings incorrectly repeat “inhibitor.” Consequently those columns must not be reinterpreted as more inhibitor probabilities; their calibration/positive-class labeling requires provider-level clarity. The boiling-point explanation also accidentally says “melting point,” while the display/model table identifies boiling point. Other_assay_interference has1001distinct values0…1 but no adequate detailed definition in the saved response; numerical format is not semantic proof.

## Endpoint mismatch with the challenge

The experimental target is a fitted direct-condition pIC50 from recombinant CYP assays: −NADPH preincubation; DBOMF for3A4, EOMCC for1A2/2C9, and dextromethorphan parent-depletion MS for2D6. Primary screen measurements instead use +NADPH preincubation. A substrate classifier predicts a different question from inhibitor potency; being a substrate and an inhibitor are not mutually exclusive mechanisms.

The saved ADMETlab dataset table describes binary positive/negative CYP training sets, e.g. inhibitor totals12614/12089/13073/12339 for1A2/2C9/2D6/3A4, and much smaller substrate totals366/811/877/979. These are documented provider datasets, not counts of independent assay-matched examples added to our training. The available documentation does not establish per-record probe, substrate concentration, enzyme preparation, preincubation/NADPH timing, inhibitor threshold or source structure membership matching this challenge. Do not assume one universal10µM threshold or that a substrate score measures active-preincubation metabolism quantitatively.

The teacher’s molecule-level training membership and exact deployed checkpoint are not recovered here. Possible overlap with public chemistry/assay pools is unresolved. Therefore positive teacher–challenge association may reflect transferable chemistry, source overlap or both; it is not an independently validated out-of-domain prediction. The feature source is the preserved web-default cache, not new API inference. No replicate measurements or experimental uncertainty were obtained by labeling.

## Mechanical integrity and actual training preprocessing

All31,641×120 numeric inputs are finite, and no feature is constant within any of the five post-purge training folds. Imputation is therefore inactive; missingness cannot explain this P7 comparison. Stage row identity, source strings, audit exclusions and all3,796,920 feature values were already independently verified. There is no evidence here of a shuffled SMILES→feature join.

P7 fits mean/standard deviation on each fold’s full union training rows and feeds the resulting standardized columns directly to the neural prediction layers. Formal charge is99.10–99.28% at its modal value, yet rare charged cases reach|z|≈28. A sparse chemically meaningful feature can therefore be highly leveraged after standardization without being erroneous.

Several outputs are physically unconstrained regression estimates: PPB ranges−17.57…105.90%, with14negative and32above100 values; Fu reaches162.13%, with34above100. Those are out-of-domain model predictions, not valid physical fractions. Preserve them as evidence; this diagnostic does not silently clip, impute or delete them. VDss reaches1226.84L/kg for official OCNT-2328970, a long-chain quaternary ammonium structure, with|z|≈132.65. Extreme predictions are plausible sources of numerical leverage, but their impact on gradients/predictions remains a testable hypothesis.

## Concrete volume-scale defect

Eighty-five retained structures have reported Vol>10000, all with one or more of B, Si, As, Se, Sb or Hg. These are legitimate element/structure applicability cases, **not85invalid molecules**. Examples on the same documented van-der-Waals-volume scale:

- CHEMBL113478:MW315.90, Vol57,461,988.6874.
- VEITH-FBFPLFGAIISYPJ:MW440.18, Vol88,943,751.3042.

The values exist in the original returned CSV, match exact request IDs and are preserved in the numeric matrix. Dense follows the documented MW/Vol ratio, around5×10⁻⁶ for these examples. This is not a merge/parser artifact. The element-associated magnitudes are incompatible with interpreting these numbers as ordinary molecular size on the same scale as the bulk of small molecules. A subsequent source/numerical control reproduced the mechanism: the public Scopy calculator mixes decimal Å-scale radii with integer picometre-scale radii, e.g. C1.70 versus Se190/B192, then cubes them. The unrounded equation matches all85service volumes to maximum relative discrepancy3.27×10⁻¹⁵ and200ordinary controls to8.09×10⁻¹⁶. The exact deployed server revision is not established. See [source and numerical proof](volume-source/UNIT_BUG_EVIDENCE.md); no corrected feature values were applied.

Training-fold Vol medians are357–362; means inflate to71,186–118,358 and standard deviations to1.67–2.11million. Under the **actual P7 scaler**, the central98% raw range(about142–819, depending on fold) spans only0.000318–0.000394standardized units. Ordinary molecular volume information is effectively compressed, while rare element cases dominate this coordinate’s scale. The highest standardized Vol magnitude is53.14. This is a concrete feature-quality mechanism that finite-value and SMILES-identity checks alone cannot detect.

Evidence: large-volume-feature-cases.csv, large-volume-raw-evidence.csv and volume-scaling-diagnostic.json. No rows or values have been repaired. A scientifically justified later repair would address the descriptor implementation/applicability, not automatically purge legitimate organoboron or organosilicon chemistry.

## Redundancy: measurable, but not “all useless duplicates”

The standardized training correlation spectrum has participation-ratio effective rank24.94–25.90 out of120columns. This describes concentrated covariance; it does not prove only25features contain independent target information. At|correlation|≥0.95 there are only2Pearson pairs and3–4Spearman pairs per fold. Strong examples: Fu versus PPB(about−0.993Pearson); logD versus logP(about0.959Pearson). MW/Vol has0.954Spearman but only0.003Pearson in fold0, illustrating the distortion caused by the extreme volume values.

Many endpoints are correlated because they share molecular physicochemistry and modeling priors. They may also overlap information already in the graph encoder. Neither correlation nor deterministic graph derivability proves redundancy for a finite trained network. The failure could instead involve optimization, target/task imbalance or a harmful subset of features; those alternatives require matched interventions.

## CYP probabilities have signal and substantial boundary mass

Global associations use all available official direct labels, not repeated outer-fold counts. They are descriptive and do not select a feature/model:

| CYP | Measured direct n | Inhibitor-score Spearman | Substrate-score Spearman | Inhibitor scores≤.01 | ≥.99 | Exactly1 |
|---|---:|---:|---:|---:|---:|---:|
|1A2|1412|0.3864|0.0894|214|401|10|
|2C9|1285|0.3785|0.0903|327|190|0|
|2D6|1493|0.2729|0.1144|478|256|16|
|3A4|2335|0.4889|0.0619|538|373|14|

None of these official-label inhibitor subsets contains exact0. Native scores include extremely small positive values; exact1 is uncommon, but39–49% of labeled examples lie in≤.01 or≥.99 tails. These descriptive tail thresholds were specified for diagnosis, not optimized to predict the observed P7 outcome.

CYP scores are **not generally rounded to three decimals**: fold0 has roughly17–18.7thousand distinct values among18,950training molecules. Thus widespread exact ties from CSV rounding are not supported for these columns. The CSV-only Other_assay_interference score is coarser, with1001distinct values. Near-boundary compression is still a plausible loss of useful numeric resolution, especially for within-class potency ordering, but it must be checked on actual analogue pairs and against the trained model’s dependence.

Per-fold correlations/ranges and all66verified probability endpoints’ exact0/1 andnear-boundary fractions are saved in training-teacher-signal.csv and verified-probability-ranges.csv. The own-inhibitor relationship persists across allfive training folds; the own-substrate relationship is much weaker. Weak global substrate correlation does not imply a useless feature in a nonlinear multi-task model.

## Within-analogue teacher signal: evidence against a blanket saturation explanation

Use the120exact pairs emitted by model-audit: distinct official molecules, same held-out fold/CYP, both experimental labels, Morgan radius2/2048bits with Tanimoto≥0.7 under its existing Cleanup+FragmentParent/no-chirality **geometry convention**. This convention does not merge molecular identities or remove isotope/stereo distinctions from the preserved original strings/labels. Model-audit independently recomputed all120 similarities and verified the≥0.7 condition, including six float32 cache entries displayed just below0.7. Pairs and repeated molecules are dependent; there are no independent-pair significance claims.

| CYP | Pairs | Spearman of signed teacher/pIC50 differences | Teacher point-order agreements | Same≤.01 or≥.99 tail | Exact teacher ties |
|---|---:|---:|---:|---:|---:|
|1A2|11|0.500|10/11|2|0|
|2C9|0|not estimable|not estimable|0|0|
|2D6|12|0.762|8/12|9|0|
|3A4|97|0.127|49/97|21|6|

This supports poorer fine local3A4ordering than its global correlation suggests, but it does **not** show universal loss of large potency contrasts. Among11point-defined≥1log-unit3A4pairs,9have the correct inhibitor-score direction. All5pairs with separated marginal intervals by≥1log unit are correctly ordered. One of those5is in the same saturated tail. For2D6, the one interval-supported≥1log pair is also correctly ordered despite a teacher probability difference of only0.00102. Those are contrary cases to preserve, not proof of general cliff accuracy from a tiny set.

The2D6pairs often have compressed probability differences(median absolute0.00081 across12pairs), yet their signed-difference association is positive. The3A4same-tail subset has9correct/21pairs, including6ties. Saturation can reduce numeric separation or tie values, but it is not by itself a complete explanation of P7’s failure. A calibrated direct-potency model could exploit small ordered probability differences; whether this particular neural training did so is a separate checkpoint/optimization question.

“Interval-supported” here follows the supplied marginal-interval gap diagnostic, not a joint posterior probability claim. The chemistry coverage is highly uneven: no2C9pairs, very few1A2/2D6pairs. These are available same-fold analogues, not known organizer parent-series assignments. Full teacher values, inequalities, original strings and model deltas remain in teacher-close-pair-values.csv; source pair hashes and definition are in teacher-pair-receipt.json.

## Competing explanations and discriminating controls

1. **Descriptor-quality/leverage hypothesis.** Vol/Dense and extreme regression predictions distort a few coordinates and rare examples. First use frozen-checkpoint standardized-mean masking of Vol/Dense alone, preserving rows, scalers and weights. If outcomes barely move, this defect is real but insufficient to explain the trained P7 failure. A future matched refit with validated descriptor handling is a separate experiment; inference-time masking cannot undo past optimization effects.
2. **CYP-class versus quantitative-potency mismatch.** Teacher inhibitor probabilities may support broad chemical ranking but lack potency ordering within close series. Examine actual paired potency differences, teacher differences/ties and interval-supported order. Frozen masking of the13CYPcolumns versus the107non-CYPcolumns discriminates where the trained model depends on these inputs. A later logit feature representation could test probability compression, but it is not executed here and cannot restore information absent from the teacher.
3. **Broad redundant or distracting supervision.** The71other modeled endpoints and16rules may favor general drug-likeness/source-specific trends over assay-matched potency, or merely duplicate graph features. Group-level frozen interventions locate dependence; a matched retraining ablation is needed to distinguish information quality from learned reliance. No claim that “more features always overfit” follows from this single comparison.
4. **Optimization/capacity interaction.** Rare large standardized inputs and heterogeneous probabilities/regressions may change representation learning or stopping before useful features are integrated. This competes with chemical mismatch. Checkpoint/gradient/time trajectories and the shared baseline parity belong to the architecture audit; final metrics alone do not identify this cause.

Frozen intervention masks are pinned in feature-blocks.json:all120,CYP13,nonCYP107,VolDense2. Zero means **zero in the checkpoint’s standardized coordinates**, i.e. its training mean, not raw probability0. No data exclusion, new transform or recalibration is implied. Such interventions are diagnostic distribution shifts and measure dependence of the already trained predictor, not the causal effect of retraining without that block.

## Provenance and boundaries

Primary saved documentation: `admetlab-access/live-probe/feature-schema.json`(119live explanations); `webbatch-docs/description.md`, official https://admetlab3.scbdd.com/documentation/description.md ; saved official API calculation documentation at https://admetlab3.scbdd.com/apis/#/two . The return schema’s numerical values/decision distinction and model dataset table support the semantic classifications. Exact paths/hashes are bound in feature-analysis-receipt.json. No fresh predictive service call was made.

All reported distributions except the explicitly labeled global official association table are based on post-purge P7 training folds. Reused folds are dependent. Outlier/saturation/redundancy statistics are explanations to test, not a proof of why P7 failed. No feature was removed, no molecule transformed and no new candidate submitted.
