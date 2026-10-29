# Private previous-work audit: the incumbent, deployment drift and validation mismatch

The best observed submission remains the exact **349165… incumbent at displayed MA-ST-RAE0.4425**. The H6 submission91fa… scored0.4616, with all five public metrics worse. This comparison changed the native expert, the feature mixture and its placement coefficients together. Corrected native95897… was not separately scored. Therefore the observed regression does **not** identify how much came from native refitting versus added features. We must preserve the actual incumbent weights, not replace them with a rerun bearing the same recipe name.

A second consequential finding is that neither reused outer cohort closely reproduces the test's dense analogue-series regime. The529 cohort is a potency-guided analogue holdout, not an outer scaffold split; the source author had already retired this validation construction. Own750 matches selected marginal structural properties but is mostly isolated molecules internally and strongly overrepresents a CYP3A4-only coverage stratum. These are concrete reasons to reconsider the validation estimand before another architecture sweep.

All work below is local/private: frozen artifacts were read, retention copies and diagnostics were written, and existing predictions were rescored. No model was fitted, no hidden test labels were accessed, no instance was rented, and no external publication/message/submission was made.

## 1. Exact artifact identities and retention

| Role | Exact placed CSV SHA-256 | Training/source lineage |
|---|---|---|
| Observed incumbent | `349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37` | Original20 native models, run654431aa, training sourced4c1a31; serving-precision correction38fe110, without retraining |
| Corrected/refitted native | `95897f449e10899abc24c4c9c432a72b29e9a890b3208112e97cd9aa3006eaa8` | Run91132654, sourceed1ab38;10 new union/isoform fits and10 exact mtaux8/single reuses |
| Submitted H6 | `91fa8bf0870f68071b04183166b1507c20001d04f3ae3fb5f4d055618fff98c7` | Final runadf173dc, source7a62af90; corrected native plus four official-label LightGBM heads |

The private audit folder retains all six raw/placed CSVs, the40 original/corrected native checkpoints and associated component OOF/query/metadata files, four H6 heads and reload receipts, source archives, original prepared data and runtime lock. The original native full-official OOF aggregate was reconstructed from its preserved component OOF matrices without fitting; corrected-native and H6 selected OOF files were copied exactly. Source/input/output hashes are in [lineage_manifest.json](model-audit/lineage_manifest.json), [incumbent_preservation.json](model-audit/incumbent_preservation.json) and [additional_preservation_manifest.json](model-audit/additional_preservation_manifest.json). Large ADMET input banks remain at their hash-bound original private locations; this is not a claim that every dependency has been duplicated into one archive.

The original native pools contain31,670/4,905/23,264/1,493 rows for union18/mtaux8/2d6isoform6/2d6single. The corrected full fit retained those complete pools, validation memberships and hyperparameters, but removed32 train-side entries across inner folds for13 audited tautomer groups. Those32 entries represent22 distinct IDs;16 entries, from11 IDs, carry official primary labels. They are not exclusively auxiliary-label removals. Ten checkpoints changed and ten were byte-identical.

The original and corrected native experts retain their qualified legacy public-source association policy; the later28-record source quarantine was not applied to either. This is different from the policy required for a fresh curated full-pool feature experiment.

H6 is **not fine-tuned CheMeleon**. It uses a frozen600-dimensional ADME representation from the Jeremy recipe plus120 predicted ADMETlab descriptors, with shallow LightGBM heads. The chosen final tree setting is15leaves/depth4. Feature coefficients in `(1-w)*native + w*feature` are0.5567/0.3996/0.2623/0.4060 for1A2/2C9/2D6/3A4. The heads train on1,412/1,285/1,493/2,335 observed official target values. External ADMET rows from the complete32,421 collection were **not used to supervise these heads**; a full-pool graph/ADMET fusion experiment was prepared but not run.

## 2. How much predictions changed, without interpreting that as error

Mean absolute change over the same750 blinded molecules, in pIC50 units:

| CYP | Original→refitted raw | Original→refitted placed | Refitted→H6 raw | Refitted→H6 placed | Original→H6 placed |
|---|---:|---:|---:|---:|---:|
|1A2|0.0742|0.1174|0.1669|0.2155|0.2421|
|2C9|0.0571|0.0701|0.1109|0.1148|0.1326|
|2D6|0.0382|0.0897|0.0314|0.0647|0.1077|
|3A4|0.0658|0.0706|0.1324|0.1333|0.1300|

For1A2,30% of original→H6 placed predictions move by more than log10(2), corresponding to a greater-than-twofold change in predicted IC50. The maximum change is1.1816pIC50. Original versus H6 prediction Spearman correlations are0.9705/0.9881/0.9673/0.9897. These are model-to-model comparisons, **not** correlations with experimental truth. Even a large drift can improve or worsen predictions; the unscored95897 stage prevents causal attribution of the public score change.

An existing same-input rerun is especially informative. Union18 fold0 has identical CSV bytes, train/validation indices, hyperparameters, recorded package versions and worker-function AST in the old and new runs. Nevertheless its checkpoint changed, best epoch moved36→35, and its unaveraged blinded-query MAD is0.244–0.315pIC50 across targets. Both worker logs identifyRTX3090; the source uses16-mixed precision and does not request deterministic execution. This demonstrates drift without changing that fold's data. It does not establish a particular nondeterminism cause or whether that drift harms hidden performance. A suspected initialization/sampler bug was not established and should not be claimed. See [unchanged_fold0_rerun_evidence.json](model-audit/unchanged_fold0_rerun_evidence.json) and [native_refit_conditions.csv](model-audit/native_refit_conditions.csv).

Placement is an active transformation, not a label on the same predictions. H6 reduces raw query SD relative to corrected native from0.7447→0.5918 on1A2,0.7195→0.6149 on2C9,0.3531→0.3213 on2D6, and0.9574→0.8592 on3A4. The corresponding placement scales increase from1.622→2.112,1.366→1.626,2.549→2.801 and1.163→1.312. The maps restore published population assumptions while amplifying a different residual shape. The1A2 estimated blind Pearson rises from0.7780 to0.8047 because the OOF-derived estimate changes; this is not a measured hidden-test correlation.

The exact path decomposition in [placement_path_decomposition.csv](model-audit/placement_path_decomposition.csv) holds the original map fixed while changing raw predictions, then changes the map. Its signed changes add exactly. Absolute magnitudes need not add because the two effects can cancel; they must not be presented as percentages of causal error. Positive affine placement preserves ranks except the few floor ties (two original/refitted and three H6 points for1A2). A calibration-only account is therefore insufficient to explain the broader public rank-metric deterioration; the underlying refit/blend also changes ranks, but its separate contributions remain unidentified.

Full drift quantiles, maxima, potency-band crossings, component differences and molecule IDs are retained in [unlabeled_prediction_drift.csv](model-audit/unlabeled_prediction_drift.csv), [native_component_drift.csv](model-audit/native_component_drift.csv), [prediction_and_placement_statistics.csv](model-audit/prediction_and_placement_statistics.csv) and [per_molecule_prediction_drift.csv](model-audit/per_molecule_prediction_drift.csv).

## 3. The actual validation populations

**Own750:** the constructor makes a parent-identity-grouped split, then optimizes6,000 swaps toward public-test nearest-neighbor distributions, descriptor quantiles and scaffold coverage, subject to at least150 observed labels per CYP. It uses label availability and structures, but not activity values. It is not a scaffold-disjoint outer holdout. The initial CheMeleon experiment additionally reserved350 validation molecules; later native/feature comparisons used the remaining4,155 as their outer-training pool. Its exact-Murcko coverage matches the test at24.5% by design; that does not establish comparable analogue-series density or assay composition. [Constructor](</Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/chemeleon-baseline-20261023/make_split.py>)

**Reconstructed briford529:** replaying the cached published algorithm on its exact reference data reproduces all529 IDs. It retains184 distinct top-potency seed compounds in training, formed from the top50 per each of four CYP targets, and holds out up to10 nearby existing training compounds per hit above sparse-count Tanimoto0.4. This differs from the organizer's stated75seeds from25hits in1A2/2C9/3A4 only and750 newly purchased catalogue analogues assayed against all four CYPs. Numeric activity values influence the reconstructed split through seed selection. Its author explicitly retired this analogue holdout and warned that auxiliary-model gains on it were not confirmed on the board. Our old cohort metadata's generic scaffold wording must not be mistaken for the outer-split definition. [Exact replay](model-audit/briford529_protocol_replay.json); [cached author warning](/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/reference_audit/sources/8c72c7559471febaf0962fd551b4eaab8db3a136/ml_pipelines/OpenADMET/cyp/storage/README.md:10).

The two outer cohorts overlap143 molecules. Each one's training pool contains many of the other one's held-out molecules, and both have repeatedly influenced development choices. Their independently fitted OOF weights do not make later model-family selection across the two cohorts an independent confirmation. The audited13 strict identity groups do not cross the official outer or inner folds in these two cohorts; this rules out that specific official-only leakage claim, not every possible identity or teacher-pretraining overlap.

Measured geometry using the original audit convention (Cleanup/FragmentParent, Morgan radius2/2048bits, no chirality):

| Query population | Actual official reference n | Median query→training NN | Median within-query NN | Fraction with another query neighbor≥0.7 |
|---|---:|---:|---:|---:|
| Blinded750 |4,905|0.587|0.656|34.8%|
| Own750 |4,155|0.544|0.416|7.6%|
| Briford529 |4,375|0.478|0.424|10.6%|

The last two columns show the central mismatch that marginal training-coverage matching missed. At the0.7 Butina proxy threshold,66.5% of blinded molecules are singleton clusters, versus93.1% of own750 and89.6% of briford529. These are structural proxies, not the unreleased organizer parent-series identities. Downsampling the blinded set to529 molecules still gives within-query NN medians0.636–0.653 over30fixed draws, so the difference is not explained by query count alone. Under the actual briford selector's raw sparse-count representation, the same direction holds: within-query medians0.667/0.449/0.480 for blind/own/briford.

Endpoint-specific primary-label support is weaker than all-structure coverage. Blind nearest-neighbor medians against observed primary-label pools are0.517/0.518/0.471/0.538. Own's corresponding scored subsets are0.508/0.500/0.468/0.541; briford's are0.416/0.433/0.405/0.478. Native encoder exposure to all31,670 structures raises blinded all-structure median only to0.590; it is not equivalent to having primary labels on those neighbors. Equal-reference-pool controls and per-query tables are preserved, rather than treating the different reference sizes as identical. [Geometry tables](model-audit/actual_reference_geometry.csv); [series proxies](model-audit/query_series_proxies.csv); [count-fingerprint sensitivity](model-audit/sparse_count_geometry_sensitivity.csv).

## 4. Assay and missing-label regime

The released direct-training table has6,525 observed cells out of19,620 possible cells. Of4,905 molecules,3,596 have only one direct label and only41 have all four. The official announcement describes the training DRC matrix as sparse and the purchased-analogue test as dense;2D6 was not a seed-selection target. Its readout also differs from the fluorescence assays: the announcement identifies dextromethorphan depletion on Echo-MS. The single-concentration screening condition includes+NADPH preincubation, whereas the direct target uses the−NADPH preincubation arm; these are not interchangeable experimental labels. The source HTML and its provenance are retained by the assay-audit peer in `biochem_sources/official-challenge-announcement*`.

The4,376 unique IDs in the released single-concentration table are not a4,376-subset of the direct table:4,375 overlap, one is single-only (`OCNT-2328658`), and530 direct IDs lack a released single record. Every one of those530 has a CYP3A4 direct value and no direct values for the other three CYPs. They are an endpoint-specific coverage stratum, not generic random missingness and not the briford529 holdout. Missing released rows do not prove an assay was never performed.

| Population | No released single record | CYP3A4 direct-label coverage | CYP3A4 observed mean |
|---|---:|---:|---:|
| Full direct train |530/4,905 (10.8%)|2,335/4,905|4.096|
| Own750 |232/750 (30.9%)|515/750|4.191|
| Briford529 |99/529 (18.7%)|270/529|4.573|

The530 stratum's3A4 mean is4.311. Own750's label counts are150/151/150/515; briford's are161/139/175/270. Thus a macro-average gives equal target weight while evaluating substantially different compound subpopulations per target. Matching SMILES geometry alone cannot reconstruct missing target outcomes or the dense query panel. These missing values must not be recoded as negatives.

Briford3A4 is more active than full training (21.1% belowpIC504 versus40.4% in full3A4), while other target means are closer to their full-training means; a blanket enrichment claim should not replace endpoint-level measurements. Interval widths and ST-RAE denominator distributions also differ. The full per-endpoint means, CI widths and denominator summaries are in [observed_label_regimes.csv](model-audit/observed_label_regimes.csv).

A contrary case matters: this530stratum does not explain the whole H6 validation gain. For own3A4, its soft-error change is essentially zero; for briford3A4 it contributes−0.00810 to the whole-cohort macro-ST delta, while H6 also improves the other targets. The stratum is a validation-design issue, not a demonstrated sole cause. [Additive score decomposition](model-audit/H6_outer_gain_by_released_assay_coverage.csv).

## 5. Strong and negative work already tested

All numbers below are **raw development ST-RAE**, lower better; they are not leaderboard scores or independent post-selection tests.

| Existing procedure | Own750 | Briford529 | What it establishes |
|---|---:|---:|---|
| Original native reference |0.626205|0.622655|Historical outer comparator, before strict corrections |
| Corrected native reference |0.620777|0.642309|Refit/purge changed the baseline differently across cohorts |
| Fine-tuned CheMeleon MAE package |0.665451|0.629016|Worse than its original native control; architecture/pooling also changed |
| Scratch ST-RAE package |0.657212|0.690033|Negative package, not an isolated loss ablation |
| CheMeleon ST-RAE package |0.674529|0.712901|Negative package; normalization/checkpoint/precision differences matter |
| ADMET120 LightGBM+native, global |0.613328|0.598232|Strong simple local comparator; own MAE/R² slightly worse |
| Fingerprint/RDKit+ADMET LightGBM+native, global |0.616090|0.598376|No uniform advantage over teacher-only blend |
| ADMET kernel+native, global |0.629538|0.615290|Own regression; not a new champion |
| FrozenCheM+ADMET Ridge+native, global |0.628577|0.596905|Adding descriptors helps its weak standalone control, but own blend regresses |
| CYP13-only LightGBM+native, global |0.614419|0.618860|CYP endpoints alone do not explain full complementary signal |
| Non-CYP107 LightGBM+native, global |0.620694|0.596500|Non-CYP descriptors can supply complementary signal |
| TabPFN3.5 ADMET120+native, global |0.621246|0.625643|Not stronger than the simple LightGBM blend |
| TabPFN ADME600+native, global |0.614514|0.626369|Better representation helps; limited briford gain |
| TabPFN ADME720+native, global |0.615352|0.624176|Adding ADMET hurts own and helps briford slightly |
| LightGBM ADME600+native, per-CYP |0.618304|0.579821|Most of H6's large briford gain already exists without ADMET120 |
| H6 ADME720+native, per-CYP |0.615706|0.579888|Submitted development-selected recipe; own secondary metrics mixed/worse |
| H7 three-way simplex |0.617911|0.579055|Drops primary ADMET expert on own; no ST gain over simpler H6 global |

The complete retained tables include all five metrics, standalone controls and separate placement lanes: [all_prior_readout_metrics.csv](model-audit/all_prior_readout_metrics.csv). The selected H6 per-target procedure worsens own2D6 ST-RAE0.7234→0.7398. The full-data H6 blend improves its training OOF estimate, but that is a selection statistic. The deployed public comparison is worse on ST-RAE, MAE, R² and both rank correlations.

Earlier context also matters: the initial CheMeleon baseline was around0.755 on own750; the reproduced Jeremy-style ensemble was around0.629. Adding CheMeleon to that ensemble changed own0.62943→0.62715 in the expanded-ensemble arm, a small local effect rather than a large solution improvement. The500-row ADMET pilot covered only431 labeled official compounds and60/54 points in the two outer subsets; its simple blends improved point estimates but paired intervals included zero, while flexible residual corrections failed. None of these small results established a hidden-test improvement.

Do not repeat the negative packages unchanged, but do not generalize them into claims that all pretraining, all metric-aware losses or all feature fusion fail. A matched full-pool graph/ADMET fusion was not executed. The original source author also recorded bounded-loss collapse and weak fingerprint-ensemble additions; those are external-source warnings, not our own experimental results.

## 6. Competing explanations and discriminating next hypotheses

These are proposals for peer review, not launched experiments or claimed causes. Effect sizes are unknown; the observations above do not justify invented improvement thresholds.

**H-R — replacement of the deployed expert is a material confound.** Mechanism: refitting changes learned functions and early stopping even under the same nominal seed, then OOF-based placement changes their output maps. A candidate assessed against corrected native is not a controlled modification of the observed349165 incumbent. The existing unchanged-fold control demonstrates this concern without another paid run. A discriminating design freezes the exact incumbent predictions/checkpoints and treats native artifact identity, feature addition and map policy as separate factors. If this explanation dominates, candidate effects depend strongly on which native artifact is held fixed and rerun variability can rival small feature gains. If a feature defect dominates instead, its adverse pattern should persist conditional on either fixed base. Unlabeled drift alone cannot decide between these outcomes, and95897's hidden score remains unknown.

**H-S — sparse/extrapolative validation rewards the wrong regime.** Mechanism: both local query sets are much less internally series-dense than the real catalogue expansion, and target availability/source composition differs. Smooth pretrained embeddings may help cold/diffuse compounds while losing useful fine SAR ordering around known hits. H6's large gain on the colder briford cohort and smaller/mixed own gain is compatible with this, not proof. A discriminating study predeclares multiple parent-retained analogue and series-withheld regimes, including endpoint/source-coverage strata, before candidate scoring. Under H-S, model ranking changes systematically with interpolation/series density or label-selection regime; under H-R alone, the main contrast remains artifact identity without that structured reversal. New splits cannot make unobserved target values appear: a genuinely dense external assay panel would need its own assay-context/provenance audit and exclusion from training, rather than being treated as interchangeable with the challenge.

**H-P — the OOF-to-serving placement relation is not portable across experts.** Mechanism: the new feature blend contracts raw query dispersion, while the inherited formula uses improved OOF correlation to expand it again; the fixed OOF-to-blind multipliers were not estimated for this model family. A discriminating comparison keeps the base predictions fixed and compares predeclared incumbent-anchored versus newly OOF-derived mapping policies, using validation populations with explicit calibration semantics and no held-out-label fitting. If H-P contributes, error shifts concentrate near potency/interval bands while ranks stay unchanged; it cannot alone explain the observed broader rank-metric losses. OOF rows also come from individual held-out fold models, whereas native deployment averages five folds per component; the meta-estimation and serving variance need not coincide. That mismatch exists in the old evaluation too, so it is a potential interaction, not an automatic explanation of the final regression.

**A different modeling lever to review:** use assay-tagged measured auxiliary supervision and model the sparse-label/curve process, instead of adding another generic molecular descriptor family. Native18/8/6/1 already exploits some auxiliary measurements, so the experiment must identify a new source/context distinction or a targeted representation change rather than relabeling the same method. Keep+NADPH screening, direct inhibition, Emax, Ki/IC50/AC50 and heterogeneous probes distinct; missing cells are not negatives. Under a biological context-mismatch explanation, improvements should track compatible assay/source strata; under a generic-capacity explanation, comparable-capacity controls should improve regardless of those tags. Root's primary-literature and public-data audits should determine the concrete design before any fit.

The immediate practical consequence is to preserve the exact observed incumbent and stop treating two reused local gains as sufficient evidence for replacing it. This audit narrows the next experiments; it does not claim that the challenge is solved, that H6 features caused the entire public loss, or that no stronger model can be learned.

## Reproduction and scope

Run the private scripts in `model-audit/` with `/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python`: `prediction_lineage.py`, `preserve_incumbent_sources.py`, `complete_preservation.py`, `validation_geometry.py`, `replay_outer_protocol.py`, and `existing_result_audit.py`. They do not invoke any training, publication, notification or submission transport. The first two prediction stages are scored only where saved labeled training-cohort outcomes exist; blinded prediction diagnostics never load target values. All source artifacts remain unchanged. The supplied morphology/assay proxies should not be promoted into organizer series IDs or unseen experimental labels.
