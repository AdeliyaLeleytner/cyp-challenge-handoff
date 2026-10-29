# Literature reading ledger — private,26October2026

Retrieval used one no-date-cutoff, default-relevance PubMed/OpenAlex loop (difficulty7), followed by one focused recovery of the censored-regression preprint. This is a decision-oriented review, not an exhaustive systematic review. The initial ranked candidates are saved in selected-discovery-ids.json; that file's earlier followup_rounds_used=0 is superseded here by1. No scientific source retrieval was delegated.

## Read status and consequence

| Work | Coverage actually obtained/read | Consequence for experiments |
|---|---|---|
| Stresser etal.,2000, PMID11095581 | PubMed abstract only; full-text flag did not return a full paper | Substrate dependence is a candidate explanation; reported multi-probe IC50 variation is not a universal correction factor. DBF is not automatically identical to the challenge's DBOMF. |
| Dong etal., erlotinib, DOI10.1038/aps.2010.218, PMID21372830 | PubMed abstract and partial official PMC body through methods; full-text MCP returned an empty body. Subsequent PMC access blocked. | Probe-specific reversible effects and active-preincubation TDI can coexist. Do not impose a universal shift sign or equate the +NADPH screen to the direct assay. No clinical inference. |
| Gong etal.,2024, DOI10.1002/jat.4601, PMID38544296 | PubMed abstract only | XGBoost/CatBoost classification results are a reason to retain tabular controls, not evidence of quantitative pIC50/ST-RAE superiority. Split, preprocessing and exact data details unverified. |
| Goldwaser etal.,2022, CYP2C9 structure/ML article, DOI10.1371/journal.pcbi.1009820, PMID35081108 | Official PLOS main body and PMC full-text main body, including experimental methods; supplementary files/visuals not yet read | Classification combines AC50/IC50-positive and single-concentration-negative definitions; docking adds only slight reported improvement over descriptors. Prospective supersome and cellular contexts differ. This does not justify expensive docking as the first lever or treating paper accuracy as challenge performance. |
| Enhancing Uncertainty Quantification in Drug Discovery with Censored Regression Labels, arXiv2409.04313; journal DOI10.1016/j.ailsci.2025.100128 | Full preprint available; intro,data,core losses,evaluation,results,case-study,conclusions and model-selection text read. Formula-heavy evidential section and graphical appendices not fully inspected. Journal full text unavailable; do not substitute preprint as journal read. | True threshold censoring can supply additional information. Its private AZ data are not an open training set; its one-sided squared/Tobit objectives differ from L1 distance to Bayesian credible bands. Calibration does not establish that predicted variance is experimental replicate error. |

Author names and identifiers above were checked against saved PubMed metadata.

## Evidence chain and alternatives

The challenge estimand is fitted potency under one particular probe/preincubation/readout. A structure-only ligand-level median cannot represent all assay contexts simultaneously. However, context-aware models can overfit sparse metadata; the first comparison therefore holds compound membership and record weighting fixed. The null alternative is that chemistry coverage plus robust pooling explains any benefit.

The censoring preprint includes 12,875 CYP3A4,12,876 CYP2C9 LC-MS and14,062 CYP2C9 fluorescence measurements, with61%,63% and58% censoring respectively (private datasets; Table1). Its comparisons train on different available label sets and optimize MSE/NLL, not the official challenge score. It is method support for P4's later censoring factor, not evidence to censor low official point estimates.

According to PubMed/PMC's CYP2C9 article, the prospective supersome assay uses diclofenac5µM,6min preincubation before NADPH and15min reaction, whereas the cell assay uses luciferin-H and4h incubation. These are explicit examples of context, not transferable settings for the challenge. [Paper](https://doi.org/10.1371/journal.pcbi.1009820).

The erlotinib study's contrasting substrate effects are a concrete reason to avoid universal Ki-to-IC50 or direct-to-TDI conversions. Its retrieved body remains incomplete. [Paper](https://doi.org/10.1038/aps.2010.218).

The censored-regression paper reports that predicted aleatoric variance did not track duplicate-measurement variability in its case study, despite reasonable calibration. This warns against interpreting a model variance or cross-assay standard deviation as laboratory repeat uncertainty. [Preprint](https://www.alphaxiv.org/pdf/2409.04313).

## Still uncertain

Exact challenge Emax normalization, curve parameterization/priors, probe loading/Km and missingness causes are not established. Biology motivates discriminating comparisons; it does not identify the cause of the worse live submission. No author score, significance convention or discovery rank becomes this campaign's success threshold.

