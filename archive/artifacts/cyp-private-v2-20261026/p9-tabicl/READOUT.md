# P9: the tested Atom-JEPA route did not improve the matched readout

The frozen Atom-JEPA representation is worse than the ADME600 control on all five macro metrics in the five-fold OOF comparison and both development holdouts. Neither new standalone readout beats the preserved original native ensemble. The 3D bank is complete and chemically verified; this is a measured negative result for this particular representation/readout combination, not a failed setup.

All 56 readout calls and the paired bootstrap finished in 689 seconds on the Mac, with peak RSS 2.40 GB. No paid compute, publication, or leaderboard dispatch occurred. No blend was fitted or promoted.

## Matched results

Lower ST-RAE, MAE, and RMSE are better; higher R², Spearman, and Kendall are better. These are raw predictions, with no serving calibration. Each macro value averages the four CYP metrics.

| Cohort | Representation | ST-RAE | MAE | R² | Spearman | Kendall | RMSE |
|---|---|---:|---:|---:|---:|---:|---:|
| OOF, 4,905 molecules | ADME600 | .658351 | .521213 | .421545 | .634050 | .464510 | .713234 |
| OOF, 4,905 molecules | Atom-JEPA256 | .780516 | .591503 | .280528 | .517252 | .364752 | .801789 |
| own750 | ADME600 | .684078 | .558579 | .418623 | .633603 | .461590 | .746075 |
| own750 | Atom-JEPA256 | .822539 | .636158 | .262711 | .513678 | .366118 | .844603 |
| reconstructed briford529 | ADME600 | .703871 | .504137 | .345083 | .633101 | .459676 | .686381 |
| reconstructed briford529 | Atom-JEPA256 | .773669 | .543400 | .225311 | .525038 | .368772 | .749505 |

Paired Atom-JEPA-minus-ADME macro ST-RAE differences, with conditional 95% scaffold-bootstrap intervals:

- OOF: +.122166 [.105110, .139388].
- own750: +.138462 [.085971, .194289].
- briford529: +.069799 [−.008123, .143984].

The briford ST interval includes zero; it should not be described as a uniformly decisive ST deterioration across every cohort. All five macro point estimates favor ADME, and the other four briford metric intervals also favor it. These intervals describe one fixed comparison, not variability across new training seeds or unseen evaluation regimes.

Atom-JEPA worsens ST-RAE for all four CYPs in OOF and own750. There are contrary cases in briford529: CYP2C9 improves .676818→.638567, and CYP2D6 improves .883240→.876929. The other briford targets deteriorate: CYP1A2 .656501→.780183 and CYP3A4 .598924→.798999. All per-target estimates and intervals are preserved in `full-results/aggregate-metrics.csv` and `paired-deltas.csv`; the two small improvements do not overturn the macro result.

## What was actually compared

Both branches use the same generic TabICL 2.2.0 regressor checkpoint, two estimators, seed 42, CPU fp32, and fixed preprocessing: StandardScaler followed by PCA96, with no whitening. PCA96 was fixed before readout results after checking the model's documented pretraining feature range. It superseded an earlier preparatory suggestion of 128; this is not an exact reproduction of the competitor's PCA128 pipeline.

The ADME branch uses the previously frozen, row-aligned 4,905×600 pretrained embedding cache. The Atom-JEPA branch uses the newly completed bank: block 8 **after** final normalization, degree 0, averaged over atoms, 256 features. This differs from the before-final-normalization last-layer slice in an inspected competitor cache. No competitor-fitted predictor or downloaded challenge OOF predictions were used. A subsequent bounded source check also confirms that notebook16 uses PCA128 without an external StandardScaler, fitted on each endpoint's supplied training rows. Those additional differences are documented with exact lines in `../representation-prep/ATOM_JEPA_SOURCE_FIDELITY.md`. The published recipe remains untested; this negative result must not be presented as its reproduction.

Scalers and PCA use actual training rows only. TabICL conditioning uses observed official primary pIC50 labels only; no public auxiliary assay labels enter this readout objective. Missing primary labels remain missing. The OOF comparison uses the exact repaired P7 folds, including their training-side chemical exclusions and separate stopping rows. The stopping rows are not added to the readout's training pool.

The two outer predictions are genuine fits with their excluded training pools: 4,155 training molecules for own750 and 4,375 for briford529. They are not slices of global OOF. Existing normalized-parent/connectivity and audited strict-equivalence exclusions were recomputed; no additional official rows were removed. The 750 molecules in **own750 are development-training molecules, not the 750 blinded challenge molecules**. The blinded molecules have embeddings, but no blind-label evaluation or final blind prediction fit was performed here.

All 56 saved predictions, IDs, SMILES, target bounds, and per-call settings were independently checked. The five official metrics plus RMSE were independently recomputed from the original official truth; maximum discrepancy was 1.11×10⁻¹⁶. Replaying the two profile calls within the full run reproduced both CSVs byte-for-byte.

## Incumbent relevance and remaining uncertainty

The preserved original native ensemble's raw macro ST-RAE is .637771 on its rowwise OOF, .626205 on own750, and .622655 on briford529. It remains better than either new standalone readout. This is a practical historical-expert comparison, not a matched-data architecture ablation: the native ensemble uses other training data/components and its OOF components have different fold maps.

Atom-JEPA is somewhat less correlated with incumbent residuals than ADME, particularly for CYP3A4: OOF .731 versus .838, own750 .795 versus .883, and briford529 .699 versus .871. That is a possible source of complementary errors, **not evidence that adding it improves an ensemble**. Its larger marginal errors could outweigh that complementarity. No weights were fitted here, and no improvement over the incumbent has been demonstrated.

For a clean next blend test, do not fit weights on global OOF and call these outer cohorts unseen meta-validation. Current P9 provides global OOF and outer-query predictions, but does not yet provide inner OOF generated entirely inside each outer-training pool. Some outer labels influence other rows' global-OOF training contexts. A nested blend would need those additional inner predictions, or an explicitly fixed-weight diagnostic with its limited interpretation. No such new experiment is started by this report.

Both development holdouts have already been reused and overlap by 143 molecules. Their sparse assay coverage and analogue geometry differ from the blinded challenge regime. Frozen molecular pretraining overlap is also not completely known. Consequently, this comparison does not estimate a leaderboard score or settle whether a future candidate would reach the top ten.

The supported practical decision is to retain the incumbent, retain these complete banks and predictions, and not promote the tested Atom-JEPA standalone readout. The result does not rule out other representations, a different predeclared readout, or a properly evaluated ensemble, but those remain hypotheses.

## Evidence and source identities

- Full comparison: ORX node `4bfb7d37-0902-43f9-bda9-c0f3d25a0e4e`, run `9d9731a6-6fa0-41e3-afb7-1cc9cea366f1`, source `c63a2f88c8bcd7e3d3b95cccf139ef7c7dd7a42c`.
- Complete bank: `../p9b-resume/results/embeddings.npy`, SHA256 `3ce3d1b947f09849dc44548232c54ba9be417eb6fa3c3f8dc2bb0c599d2f2c69`. All 5,655 rows pass the final chemical audit. The one legacy-CIP false-positive repair and unchanged reuse of 5,654 vectors are documented in `../p9b-resume/READOUT.md`.
- Verification: `FULL_VERIFICATION.json`, `INDEPENDENT_METRICS.csv`, `PROFILE_REPLAY_PARITY.json`, and `BANK_BINDING.json`.
- Comparison artifacts: `full-results/{aggregate-metrics.csv,paired-deltas.csv,complementarity.csv,AGGREGATE.json}` and the six `{OOF,own750,briford529}-{adme600,atomjepa256}-raw.csv` files.
- Incumbent comparison: `incumbent-raw-metrics.csv`, `incumbent-complementarity.csv`, and `INCUMBENT_COMPARISON.json` with exact source hashes.
- The generic TabICL checkpoint and package pins/licenses are in `../representation-prep/tabicl/PINS.json`; the 114 MB checkpoint was downloaded and content-verified, then used offline. No model fine-tuning or large replacement Torch installation occurred.
