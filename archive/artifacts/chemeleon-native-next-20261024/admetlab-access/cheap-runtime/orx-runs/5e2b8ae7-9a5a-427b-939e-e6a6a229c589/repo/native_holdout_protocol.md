# Native briford frozen outer validation

Two independent retrainings using frozen own750 and briford529 IDs. Each uses4 native member architectures and5 native scaffold folds with seed42 and original early stopping. Each member's held query is predicted by mean of five models; no outer labels used for fitting, scaling, stopping or selection.

Remove held IDs and stored extra parent-purge IDs, all matching normalized parent keys and native InChI connectivity keys across full merged source pools. Remove entire rows/all endpoints. Preserve remaining native row order, native public joining and domain-specific heads. Recompute native primary inverse-count weights and each member's folds after exclusion.

Two predeclared output vectors: raw native flat ensemble and unchanged author public-test placement. Published placement is evaluated exactly as used by the latest full-data reproduction; report its dependence on public TEST statistics. It is not optimized for either local holdout. No tuning after observing scores. ST-RAE uses official interval scorer and per-evaluated-target mean denominator. Cohorts have143 shared molecules, so their results are not independent replications.

Code audit addressed child-process cleanup and filtered-data manifest provenance. Author saved original checkpoints/historical environment remain unavailable; this tests the exact source-recipe implementation already used, not claims of bitwise historical replication.
