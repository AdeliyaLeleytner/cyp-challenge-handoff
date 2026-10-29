# OCNT-2315767: independent stereo-validator review

**The reviewed saved geometry does not show inversion. The legacy CIP comparison is a false positive for this case.** With every atom’s `_CIPCode` and `_CIPRank` cleared before modern labeling, `rdCIPLabeler.AssignCIPLabels` givesR/R at the two originally specified centres13/15 in the original graph, hydrogen-completed reference, and both saved ETKDG/MMFF geometries after assigning tags from3D. Both tags remainCCW under the same ordered neighbours. Original atom numbers, isotope/charge/map attributes, bonds, and canonical isomeric SMILES are unchanged.

Independent coordinate orientation, using the fixed four-neighbour order from the original H-completed graph:

| Centre | Neighbour order | ETKDG signed determinant | MMFF signed determinant |
|---|---|---:|---:|
|13|12,14,24,37|+8.436470Å³|+8.668888Å³|
|15|14,16,17,40|+8.394823Å³|+8.641055Å³|

Signs remain unchanged and the tetrahedra are far from degenerate. These determinants do not depend on legacy CIP rankings. The SDFs serialize coordinates to four decimals; this precision does not make their signs ambiguous. This review uses the owner-provided saved audit geometries, whose hashes are recorded; it does not claim to have regenerated the original failed run’s transient geometry.

The owner’s legacy audit showsS→R for centre13, while modern labeling isR→R and neighbour orientation is stable. This establishes a nomenclature/validator inconsistency rather than a geometric inversion here. MMFF/aromaticity-dependent legacy assignment is a plausible source of the inconsistency; the exact internal RDKit cache/representation pathway is not needed or proven by this bounded audit.

## Minimal validator repair

1. Keep the original SMILES, atom order, hydrogen convention, geometry, embedding seed, optimization result and model input unchanged. Do not accept a different stereoisomer or search another seed.
2. Make independent reference and coordinate-validation molecule copies. Prefer the same original H-completed molecular graph for both; attach the already produced coordinates to the validation copy in the verified exact atom order. This separates geometry validation from any transient MMFF aromaticity/perception state.
3. Clear `_CIPCode` and `_CIPRank` from every atom(and any bondCIP property) on both copies. Assign the validation copy’s stereo from3D with replacement of existing tags, then clear stale CIP properties again.
4. Apply **the same modern `rdCIPLabeler.AssignCIPLabels` algorithm** to both copies. Compare labels only for the originally explicitly specified centres, with the established atom mapping. Do not compare a legacy-original label against a modern/geometric label.
5. Retain independent molecular-identity, originally defined bondE/Z, enhanced-stereo-group, and coordinate/atom-number-order checks. Where using tag/orientation checks, retain the exact neighbour ordering and explicit-H convention; rawR/S labels are not interchangeable with ordered-neighbour parity.
6. Preserve failure reporting if modern assignments, defined stereochemistry or coordinate orientation disagree. This is not a blanket waiver for future stereo failures. Re-audit the persisted complete bank under the repaired validator before its later use, as already planned by the model owner.

No source or production artifacts were edited by this reviewer. No coordinates were generated, optimized, permuted or replaced; no embedding inference or paid work occurred. The code comment mentioning a possible in-memory stress control was not executed; actual checks compare the saved original geometry only. `INDEPENDENT_REVIEW.json` records source hashes, RDKit2026.09.1, fresh labels and numerical orientation evidence.
