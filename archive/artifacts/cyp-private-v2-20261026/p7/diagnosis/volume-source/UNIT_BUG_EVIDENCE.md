# Molecular-volume unit mechanism: source and numeric controls

The reported volume anomaly is reproducible from a mixed-unit radius table in the public authors’ Scopy calculator. At pinned revision`ed2651583ee25c0a7f9767e3ed54452f81b3de79`, [CalculateMolVolume](https://github.com/kotori-y/Scopy/blob/ed2651583ee25c0a7f9767e3ed54452f81b3de79/scopy/ScoDruglikeness/molproperty.py#L842) documents an Å³ result and sums4πr³/3 over hydrogen-completed atoms, minus5.92per bond. The table mixes H1.20/C1.70 with B192, Si210, As185, Se190, Sb206 and Hg155. Those latter magnitudes correspond to picometre-style radii rather than Å-scale values, inflating the affected atom volume contributions by10⁶.

Using that exact radius table and equation on the **returned service structures**, before the public function’s final two-decimal rounding, reproduces:

| Frozen numerical control | n | Maximum relative discrepancy |
|---|---:|---:|
| All85retained anomalous-volume molecules |85|3.27×10⁻¹⁵|
| Ordinary controls selected by request-ID order, without activity use |200|8.09×10⁻¹⁶|

Absolute discrepancies are at most1.19×10⁻⁷ for the huge volumes and4.55×10⁻¹³ for ordinary volumes. The public source rounds to two decimals, whereas the service retains unrounded values; applying public rounding differs by at most0.005. This is numerical evidence for the same underlying calculation, not just a resemblance between two large examples.

The exact deployed ADMETlab server revision remains unavailable, so we do not claim the current public Scopy checkout is its entire runtime. The numeric mechanism of the85volume defects is nevertheless reproduced with ordinary controls. Molecules and stereochemistry remain unchanged. No corrected feature matrix, replacement radii, hand-repaired values or row exclusions were produced. This finding concerns the numeric descriptor, not chemical invalidity of B/Si/As/Se/Sb/Hg molecules.

Evidence: source-ledger.json pins retrieved code URLs/hashes; NUMERICAL_PROOF.json contains table and control statistics; formula-comparison.csv preserves every request/service string and discrepancy; verify_formula.py is the independent formula reproduction. No predicted ADMET service call or model fit was made.
