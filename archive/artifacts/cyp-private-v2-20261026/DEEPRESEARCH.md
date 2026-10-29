# Evidence synthesis, first private round

This is a living research record, not a public report. External claims below are author-reported unless explicitly marked as our reproduction. No hidden outcomes are used.

## Challenge measurement and selection

The [official protocol](https://openadmet.ghost.io/announcing-openadmets-cyp-inhibition-blind-challenge/) distinguishes +NADPH primary screening from −NADPH direct preincubation.3A4 uses DBOMF,1A2/2C9 EOMCC, and2D6 dextromethorphan parent-depletion MS. Test construction expands25 potent parents in each of1A2/2C9/3A4 into10 catalog analogs and then assays all750 across4CYPs. This makes source/condition and series structure material; it does not justify converting screening log-fold-change to direct IC50. Existing tables show49.5049505µM recorded single concentration, signed Emax, and sparse direct labels. Exact current dilution/Emax normalization remains unresolved.

## Verified prior-work boundaries

Private diagnostics in PREVIOUS_WORK_MODEL.md establish that one identical-data native fold changed predictions on rerun, and10/20 checkpoints changed overall. Keep the deployed349165 artifact fixed. Blind within-query NN median.656 differs from.416/.424 for existing holdouts; only41official compounds have all4direct labels. The reconstructed529 is an active-guided analogue split that its author retired. Do not treat old local gains or these reused diagnostics as a fresh confirmation set.

## Source-backed method candidates

[Scigantic factorial](https://github.com/Scigantic/open-admet-challenge-cyp/blob/e70a2920d611684c9aaff07400d951e2e79dd5f6/training/chemeleon_arms/INTERVAL_2X2_RESULT.md) reports a loss×sample-weighting interaction at fixed2048width: interval/uniform.6895 versus MAE/uniform.7170; interval/inverse-variance.7422 versus MAE/inverse-variance.7187. Its claimed component gain is not our reproduction or the current live score. Actual code carries target-bound columns at zero loss weight, and the weighting proxy comes from reported intervals. A new four-cell trial needs a common checkpoint metric, per-target bound masks, fold-local weight scaling, matched initialization/data/precision, and no dummy-bound denominator dilution.

[Doctawho measurement model](https://github.com/doctawho42/CYPChallenge/blob/bf018b8311c5e7804674384aa5cc16b6c93db94b/docs/method_report.md) reports successful and negative measurement/representation arms. Source inspection finds its screen link uses the same direct-potency latent despite the NADPH mismatch; fixed E/H nuisance parameters were fitted using all paired cells. Treat this as an empirical comparator requiring fold-local repair, not a physical truth. Its dead-zone majorise–minimise objective and free auxiliary head remain testable separately.

[Scigantic incumbent correction](https://github.com/Scigantic/open-admet-challenge-cyp/blob/e70a2920d611684c9aaff07400d951e2e79dd5f6/scripts/build_r25.py) and [Jackson hinge blending](https://github.com/JacksonBurns/cyp-challenge/blob/9cfa8fb412bd05ede7fe3d2f59c86744d480ba2e/src/hinge_blend.py) motivate preserving a fixed incumbent while evaluating component deltas. Readout signs, squared-vs-L1 hinge and exact released/live revision distinctions matter. No signed-coefficient search or leaderboard probes are authorized in the first replay.

## Biological/public-data evidence

The exact cached CHEMBL10/1A2 cell is reproduced by mixing two AC50 records and one IC50 record; its cross-assay SD is not automatically repeat uncertainty. Direct human target queries also contain homolog and predicted-assay examples. The new public-data pilot therefore retains activity type, relation, unit, assay, probe/preparation, organism and document instead of silently calling every pChEMBL value pIC50. Censored IC50 relations are distinct from Bayesian credible intervals and from missing labels.

Root literature discovery is recorded under literature/. The [erlotinib study](https://doi.org/10.1038/aps.2010.218) is a concrete substrate-dependence example; full-text reading is in progress. [CYP2C9 structure/ML](https://doi.org/10.1371/journal.pcbi.1009820) uses classification and selected descriptors/protein conformations; its effect sizes are not direct-pIC50/ST-RAE evidence. The [censored-regression preprint](https://www.alphaxiv.org/pdf/2409.04313) uses private assay data, so it offers a method, not an open training set. Its explicit censoring assumption is not interchangeable with the challenge's posterior credible bands. Journal/PubMed retrievals that returned abstracts only are not labeled full reads.
