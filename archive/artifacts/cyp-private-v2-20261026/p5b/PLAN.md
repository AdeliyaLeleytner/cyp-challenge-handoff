# P5b — incumbent-anchored H6 coefficient refit

Hypothesis: the existing positive fixed-coefficient P5 signal may persist or improve when the frozen H6 feature-only expert is blended with the ORIGINAL native expert using coefficients learned against that same original expert's matching outer-training OOF. The H6 deployment changed native refits and placement together; its worse public result does not isolate this fixed-expert combination.

Pin the original native outer-training OOF and original query vectors already independently reconstructed in P9 nesting. Pin the existing selected H6 ADME720-LightGBM feature-only outer-training OOF and query banks, including selection/data-audit provenance. Do not change H6 parameters, features, heads or predictions. Exact training/query ID sets, SMILES and observed-label masks must match each frozen cohort. If a matching bank is absent, stop and report; never substitute global OOF.

For each CYP, fit a single convex feature coefficient w in[0,1] using only outer-training OOF pIC50 labels and intervals. Use the existing exact weighted-endpoint-median objective/tie convention (smallest minimizer), equivalent to minimizing soft-interval ST-RAE for that target. No intercept, coefficient grid, negative weights, model refit, new feature value, or calibration fit. Persist coefficients before scoring outer-query values.

Controls are the unchanged original native and the exact fixed-coefficient P5 original+H6 mixture. Verify both against their preserved vectors. Evaluate new coefficients on the same full-context frozen H6 query predictions, all five official metrics. Raw is primary. Apply the already-frozen original serving operator only as a separate diagnostic, with its established local-population mismatch; never recompute its parameters for a candidate.

Use the original P5 paired-bootstrap convention: 1,000 draws, seed20261026, non-isomeric Bemis–Murcko scaffold groups, with acyclic molecules grouped by connectivity InChIKey. The same query draws serve all arms and lanes. Intervals hold fitted coefficients fixed. Reused overlapping holdouts, native source/purge limitations, differing native component folds, and historical H6 development selection remain explicit; this is not independent fresh validation.

One committed local CPU run capped at10minutes, no paid resources, no new base fits. Preserve the exact0.4425 incumbent. No publication or submission. Private candidate preparation is conditional on the resulting evidence; no blind score is inferred from this experiment.
