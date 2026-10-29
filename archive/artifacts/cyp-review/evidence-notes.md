# Direct Inhibition Track: evidence and starting plan

Checked 2026-10-22. This is a targeted literature review and public-data audit, not a trained model or a demonstrated winning entry.

## Challenge facts

- Deadline: 2026-11-03 23:59 UTC, equivalent to 2026-11-04 02:59 Europe/Moscow.
- Task: predict four direct-inhibition pIC50 values for each of 750 test compounds; 3,000 finite predictions, with the official identifiers.
- Primary metric: macro-average of ST-RAE across CYP1A2, CYP2C9, CYP2D6, CYP3A4, lower is better.
- Secondary metrics: MAE, R2, Spearman rho, Kendall tau; 1,000 bootstrap resamples.
- External data and pretrained models allowed. Proprietary data must be disclosed. One account per collaborating team; submissions at most once per 12 hours; latest valid submission counts.
- Rules: [official Space configuration](https://huggingface.co/spaces/openadmet/cyp-challenge/blob/main/config.py).
- Dataset: [official release](https://huggingface.co/datasets/openadmet/cyp-challenge-train-test).

Observed CSV counts:

| Target | Nonmissing direct pIC50 | pIC50 below 4 | Median interval width |
|---|---:|---:|---:|
| CYP1A2 | 1,412 | 232 | 0.328330 |
| CYP2C9 | 1,285 | 259 | 0.525758 |
| CYP2D6 | 1,493 | 129 | 0.271608 |
| CYP3A4 | 2,335 | 944 | 0.379150 |

Main CSV has 4,905 rows, 6,525 observed target cells. Missing labels are unknown, not inactive.

Auxiliary audit: TDI file has 6,145 rows; its direct pIC50 columns add zero measured molecule-target pairs relative to the main file and have zero numerical conflicts at tolerance 1e-6. Emax CSV has 6,145 rows (README says 6,146). Single-concentration CSV has 17,504 rows. None of these auxiliary files overlap blinded test Molecule_Name identifiers. This is an ID comparison, not a standardized-structure overlap audit.

## Exact primary score

For observed molecule i in endpoint e, let [L_i,U_i] be the experimental credible interval and p_i the prediction:

`d(p_i, [L_i,U_i]) = max(L_i - p_i, 0) + max(p_i - U_i, 0)`

`ST-RAE_e = sum_i d(p_i,[L_i,U_i]) / sum_i d(mean(y_e),[L_i,U_i])`

`MA-ST-RAE = mean_e ST-RAE_e` over the four CYP endpoints.

The denominator is also interval-aware. The reference mean is computed from the evaluated ground-truth set, not the training set. For a nonzero denominator, 0 means all predictions are within their intervals; 1 means equal interval error to the constant reference mean; values greater than 1 are worse. The exact competition aggregation additionally averages bootstrap score distributions, so a single full-set plug-in value is not identical to the leaderboard bootstrap mean.

No special clipping at pIC50=4 occurs in the selected ST-RAE function. Both interval bounds are used for every scored example. The tutorial includes other RAE functions, but the config selects `rae_soft_threshold_absolute_error`. Do not silently substitute conventional RAE, inverse-variance weights, or clipping at 4.

Verified directly from [official scoring functions](https://github.com/OpenADMET/CYP-Challenge-Tutorial/blob/main/evaluation/custom_scoring_functions.py), [selected metrics](https://github.com/OpenADMET/CYP-Challenge-Tutorial/blob/main/evaluation/config.py), and [evaluation/aggregation](https://github.com/OpenADMET/CYP-Challenge-Tutorial/blob/main/evaluation/evaluate_predictions.py). Local copies are under `sources/`.

Executed the two relevant official functions extracted by Python AST, with their numerical implementation unchanged. Toy y=[4,6], intervals [3.8,4.2] and [5.8,6.2]: predictions y score 0; predictions [5,5] score 1; predictions [4.4,6.4] score 0.25. Evaluated-set mean predictor scores 1 on each actual training endpoint. These are scoring checks, not model validation results.

## Test design and assay meaning

The [organizers' announcement](https://openadmet.ghost.io/announcing-openadmets-cyp-inhibition-blind-challenge/) describes selecting 25 potent seeds for each of CYP1A2, CYP2C9 and CYP3A4, then purchasing 10 similar molecules per seed. CYP2D6 was not used to select seeds. All four targets are measured in the test. Train labels are sparse and hit-selected.

The primary screen used TDI conditions. Its log2 fold change must not be treated as direct-inhibition pIC50. Three CYP readouts are fluorogenic; CYP2D6 uses dextromethorphan turnover measured by mass spectrometry. Cross-assay transfer requires keeping conditions and endpoints distinct. In-vitro inhibition is not a direct estimate of clinical harm.

## Literature reading record

1. **Burns et al., CheMeleon, arXiv:2506.15792v2 (2026-02-09).** [Full paper](https://arxiv.org/html/2506.15792v2), [code](https://github.com/JacksonBurns/CheMeleon). Main text, results tables 1-2, discussion and methods inspected; supplement not exhaustively inspected. Descriptor-pretrained D-MPNN, then fine-tuning. Reported wins including statistical ties: 21/28 Polaris and 29/30 MoleculeACE tasks. These are task win counts, not percentages of correctly predicted molecules. Activity cliffs remain harder than ordinary examples. Earlier v1 reported different baseline comparisons; v2 supersedes those numbers in this review. Figure 1 extracted from PDF page 4, inspected visually, saved as `figures/chemeleon-workflow.png`.
2. **Revisiting ADMET prediction reliability under real-world challenges in the foundation model era (2026).** [Full paper, DOI 10.1186/s13321-026-01217-2](https://link.springer.com/article/10.1186/s13321-026-01217-2). Main methods, results and discussion inspected; supplementary evidence not exhaustively inspected. Supports comparing KPGT, descriptor-based boosting, TabPFNv2 and complementary ensembles. MoleculeACE mean R2: KPGT 0.678; XGBoost/MorganCount 0.668; TabPFNv2/RDKit 0.649. Different endpoints/splits/metrics from the challenge; this is candidate-selection evidence, not a CYP competition ranking.
3. **Woo et al. (2026), Enhancing CYP3A4 Inhibition Prediction Using a Hybrid GNN–ML Model with Data Augmentation.** [Full paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12944684/), DOI [10.3390/ph19020258](https://doi.org/10.3390/ph19020258). Main methods/results and conclusion inspected; supplements not exhaustively inspected. 23,713 compounds; target percent inhibition around 10 micromolar, not pIC50. Internal ML-ensemble RMSE 19.1031, hybrid 19.0784; external n=100. Useful evidence for complementary representations, but the small internal gain and heterogeneous assay data do not establish transferable superiority.

Other leads: [GRASP preprint](https://www.biorxiv.org/content/10.64898/2026.09.28.755019v1.full) full text was inaccessible (403); no claim-level reliance. [Model-scaling preprint](https://arxiv.org/html/2604.26498v1) inspected but not used to establish universal rankings because of heterogeneous training budgets. [Public entrant report](https://huggingface.co/Nomad-link-id/openadmet-cyp-methods) is self-reported OOF evidence, with ordinary RAE named and blend selection on the same OOF predictions; not verified leaderboard evidence.

Search limitation: PubMed discovery returned results but metadata retrieval required a missing contact email; OpenAlex required a missing API key. Continued through original publisher/arXiv sources. No claim of an exhaustive systematic review.

## Proposed bounded next phase

This is Codex's recommendation for testing, not a measured result:

1. Standardize molecular identity with provenance; keep the original submission identifiers, stereochemistry and measured intervals. Inspect test-to-train nearest-neighbor similarities and selection effects.
2. Construct repeated analogue-expansion-like validation: keep a selected training seed and hide different measured analogues; choose seeds from fold-training labels only. Match test similarity distributions using structures only. Add a cluster/scaffold holdout as a complementary stress test. Do not select held-out compounds using their unknown activity. All supervised auxiliary data for held-out molecules must stay out of the training fold.
3. Compare nearest-neighbor/Tanimoto regression, RF or LightGBM on Morgan count fingerprints plus physicochemical descriptors, multitask Chemprop and fine-tuned CheMeleon. Use fixed common splits and macro ST-RAE for selection. Compare per-target models when joint training harms an endpoint.
4. Compare ordinary robust regression losses with interval-distance training losses; pick using held-out ST-RAE and secondary metrics. Intervals are experimental targets, not available inference inputs. Avoid arbitrary inverse-uncertainty weighting.
5. Test the value of auxiliary single-concentration, Emax and TDI targets independently. These can teach a shared representation or generate cross-fitted predictions. Never supply measured auxiliary values to validation/test when unavailable at real inference time; do not double-count direct labels duplicated in TDI data.
6. Blend only models with demonstrated complementary errors, with simple per-endpoint weights and a separate check on weight selection. Consider curated external CYP assays or KPGT/TabPFN only if the first comparison identifies a useful gap. External IC50/Ki, TDI, percent inhibition, substrate turnover and binary labels need separate semantics.
7. Freeze and validate the final 750-row submission by Nov 2, retain Nov 3 for verification and authorized upload. Training resources and budget are not specified yet.

## Source versions

- HF Space: `170259e18470549b034e437b671aff6bab598e3b`.
- HF dataset: `146282d2ce1532f1803679a834a9bec9dac1e482`.
- Tutorial: `832ae6d6447b07c2c71059de34d07f1130388247`.
- Local source hashes: `source-sha256.json`; descriptive statistics: `data-audit.json`.

## Independent advisory consultation and Codex decision

Wrapper exited 0 with a substantive structured response. Consultation ID `20261022T122047Z-4ea96806`; requested model `claude-fable-5`, actual primary model `claude-opus-5`, automatic fallback used. This is Opus advice; the version is recorded exactly as returned, without inferring Opus 5.5.

Useful recommendations retained: align evaluation with the interval metric; inspect chemistry similarities before choosing validation; compare descriptor models and multitask/pretrained graph models; test auxiliary targets; preserve a validated fallback submission.

Codex independently checked the scoring code, counted all observed labels, and read the official assay/test construction and selected primary literature. Material corrections:

- Advisor suggested holding out the seed together with its analogues as the primary design-mimicking split. Codex instead retains the known seed while holding out query analogues for the primary imitation of this challenge. Entire-series holdout remains a separate stress test. Seed identities and nearest measured neighbors still need structural verification.
- The claim that training is inactive-dominated is unsupported: only 1,564 of 6,525 observed direct-inhibition cells (23.97%) have pIC50 < 4, and every endpoint is below 50%. This does not establish test prevalence either. No blanket downward recalibration is recommended.
- A prediction below the interval's lower edge is penalized too. The advisor's statement that any prediction below an inactive example's upper edge is unpenalized is incorrect for the implemented two-sided interval metric.
- Numerical score/noise targets imported from another OpenADMET challenge are not transferred here. No claim of a 0.03 significance cutoff or a known attainable score.
- Pure interval loss and a mixed interval/L1 loss are candidates to compare, not guaranteed improvements; the proposed fixed mixture weight is not evidence-backed for this data.
- The latest CheMeleon v2 reports 21/28 Polaris wins, superseding the v1 22/28 number in the original advisory brief. Final recommendations use v2 evidence.
- Budget and external submission decisions are not needed to complete the requested explanation. No training, account changes, messaging or competition submission was performed.

Decision: proceed with the bounded model-comparison plan above when implementation is requested, with analogue-aware validation and official MA-ST-RAE as the selection criterion. No universal SOTA or likely victory is asserted.
