# Paired-condition descriptive result

No model fits or new data requests. Exact existing source hashes, duplicate direct values and aligned raw SMILES were checked; the script and output hashes are in receipt.json. These are observed-data descriptions, not a causal mechanism or predictive gain.

| CYP | Complete paired points/intervals | Median active-minus-direct pIC50 | Negative point shifts | Negative non-overlapping marginal intervals | Positive non-overlapping marginal intervals |
|---|---:|---:|---:|---:|---:|
|1A2|1412|0.02370|543|0|37|
|2C9|1285|0.00736|602|15|19|
|2D6|1493|0.15432|202|7|359|
|3A4|2334|0.30743|310|6|973|

The3A4 paired count is one less than the direct-label count because complete active/direct values and marginal intervals are required. All530 direct-only/no-single compounds remain in the3A4 paired analysis; only1804 paired rows have released single-screen/plate metadata. Missing metadata was not imputed.

Small negative shifts are common for1A2/2C9, but most do not separate the two marginal intervals. Conversely,3A4 has substantial positive separation and a small number of opposite-direction cases. Marginal interval nonoverlap is not a calibrated joint credible interval for a difference; the joint posterior is unavailable. No monotonic TDI>=direct constraint is justified by these tables.

The direct-potency/shift Spearman association is−0.359 for2D6, and width/shift is0.413. Direct potency is itself subtracted when calculating shift, so neither association identifies metabolic causation. The plate-level Cohen's d correlation with shift is near zero in these observed paired subsets, but this does not exclude all plate artifacts or selection effects.

The next model contrast should separate direct and active-condition outputs and compare them with an unconstrained auxiliary-head baseline. It must keep absent blind auxiliary measurements absent, use fold-local training and not convert signed Emax or screen log2FC to direct IC50.
