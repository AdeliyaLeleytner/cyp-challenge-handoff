# OpenADMET CYP interim entry: physicochemical linear baseline

**Track:** Direct Inhibition Prediction (Regression)  
**Recipe date:** September 20, 2026  
**Scope:** public adaptation of the original locally reviewed method report;
challenge upload remains pending. No new scientific evaluation is reported here.

## Summary

This entry predicts direct-inhibition $\mathrm{pIC}_{50}$ for CYP1A2, CYP2C9,
CYP2D6 and CYP3A4 using four independent ordinary least-squares models. Each model
uses the same 14 RDKit physicochemical descriptors, with standardization fitted
only to that enzyme's labeled training compounds. This is a transparent baseline,
not a claim of improved or established blind-test performance.

## Data and scope

Only the public [OpenADMET challenge direct-inhibition dataset](https://huggingface.co/datasets/openadmet/cyp-challenge-train-test/tree/3ac9c5dbb83eec5780ec7fa511908698cfe1396d)
supplies labels. The training table contains 4,905 compounds with a sparse
enzyme-label matrix:

| Endpoint | Observed training labels |
|---|---:|
| CYP1A2 | 1,412 |
| CYP2C9 | 1,285 |
| CYP2D6 | 1,493 |
| CYP3A4 | 2,335 |

All 750 blinded test compounds receive predictions. Original molecule identifiers,
SMILES strings and row order are preserved. No experimental test labels or
leaderboard feedback were used in the frozen baseline recipe.

No proprietary training data, external bioactivity labels, pretrained weights,
TDI labels, maximal-effect measurements or single-concentration screening
measurements enter these fits. Other project investigations do not change the
baseline's input scope.

## Molecular processing and descriptors

RDKit parses each input structure. For disconnected structures, the implemented
rule selects the fragment with the **greatest number of heavy atoms**, sanitizes
it and emits canonical SMILES. It does **not** explicitly neutralize charges or
guarantee an organic fragment, despite the historical implementation's imprecise
docstring. Original input SMILES remain in the output; canonical SMILES are used
only for feature calculation. Invalid structures block generation rather than
being silently dropped.

The fixed descriptor order is:

1. Calculated lipophilicity (`MolLogP`)
2. Molecular weight (`MolWt`)
3. Molar refractivity (`MolMR`)
4. Topological polar surface area (`TPSA`)
5. Hydrogen-bond donor count (`NumHBD`)
6. Hydrogen-bond acceptor count (`NumHBA`)
7. Rotatable-bond count (`NumRotatableBonds`)
8. Total ring count (`NumRings`)
9. Aromatic ring count (`NumAromaticRings`)
10. Aliphatic ring count (`NumAliphaticRings`)
11. Heteroatom count (`NumHeteroatoms`)
12. Fraction of $sp^3$ carbon (`FractionCSP3`)
13. Heavy-atom count (`NumHeavyAtoms`)
14. Formal charge (`FormalCharge`)

All raw descriptors must be finite **before** the frozen wrapper calls
`numpy.nan_to_num`. Finite raw values must match the wrapper's output exactly.
There is no feature imputation, no dropped test row and no fabricated fallback
prediction. Canonical duplicates are retained by the recipe, not deduplicated
after inspection.

## Fitting and prediction

The original registry entry `T1_simple_desc_linear` is a `StandardScaler()`
followed by default `LinearRegression()`. For each enzyme, the original
`endpoint_frame` excludes rows missing that endpoint's observed point estimate.
All remaining labels must be finite real numbers, and the observed counts must
match the table above. A new independent registry instance is fitted on all
those rows. The scaler sees only that endpoint's training rows.

Fits are unweighted. Confidence bounds are carried by the historical data loader
but are **not** passed to the estimator. No target imputation or relabeling is
performed. For descriptor vector $x$,

$$
\hat y = \left(\frac{x-\mu}{s}\right)^{\mathsf T}\beta+b,
$$

where $\mu$ and $s$ are training-only centering/scaling parameters and
$\beta,b$ are fitted coefficients and intercept.

This is one full-data model per endpoint, **not** an average of cross-validation
models. The original recipe was fixed in writing before its blinded-compound
predictions were generated. There is no cross-validation during refitting,
hyperparameter optimization, feature selection, stochastic training, interval
weighting, model switching, ensembling, clipping, offset correction or added
noise. Default ordinary least squares is not replaced by a different optimizer.

Outputs are $\mathrm{pIC}_{50}$ point predictions, not concentrations,
probabilities, confidence intervals or TDI classifications. CSV output uses 17
significant digits, with `SMILES` first and `Molecule_Name` second, followed by the
four endpoints in the order shown above. This differs from the upstream test
table's identifier-column order; it does not change the row-level mapping.

## Historical checks versus public reproduction

**SUPPORTABLE WITH CAVEATS** is the existing PatAgent verdict for the original
package's submission-format and provenance readiness. The
[separate review](cyp_challenge/results/submission/interim_regression_linear_v1_review/patagent_review.json)
binds that verdict to the exact CSV, not to predictive accuracy or this new public
entry point. The reviewed CSV SHA-256 is:

```text
645f6840d50dcdf4f3b1eb17f409621e81ecca7efe17c6755fc49652a0bc7b73
```

The original review records checks for 750 rows and the six required columns;
unique complete identifiers; original identifier/SMILES mapping and row order;
finite predictions; and the per-endpoint nonconstant/sample-standard-deviation
gate. The minimum sample standard deviation is $0.01$, using one degree of
freedom. These are structural checks, not accuracy measurements.

It also records original parameter reconstruction and a separate-process fresh
refit, together with execution of the unmodified official validator pinned to
commit `858ae63ce79934113bccdb7fc65467de5f7b1935`. Its
[Apache-2.0 source](https://github.com/OpenADMET/CYP-Challenge-Tutorial/blob/858ae63ce79934113bccdb7fc65467de5f7b1935/validation/activity_validation.py)
was supplemented by stricter mapping, dtype and variance checks.

The public [reproduction entry point](tools/reproduce_baseline.py) is a new
portable wrapper around the **byte-exact original** data, feature and model
modules. It checks literal source/data SHA-256 pins, exact library versions, the
14-feature order, four label counts and default registry parameters. It uses
one numerical-library thread, not a GPU. It does not load pickle or download
weights. A new public-run receipt is required before claiming this entry point
has reproduced the reviewed file; the historical receipt is not a substitute.

The reference environment is CPython 3.13.14, NumPy 2.4.3, pandas 2.2.3,
SciPy 1.17.1, scikit-learn 1.8.0, RDKit 2025.09.6 (distribution version
2025.9.6) and threadpoolctl 3.6.0. Absolute and relative comparison tolerances
are fixed at $10^{-10}$. Numerical agreement and exact CSV byte identity are
recorded separately. A Python patch deviation is warned about unless strict
patch checking is requested; dependency deviations fail by default.

The original Windows-specific builder also sealed installed binaries, original
protocol bytes and machine-specific provenance. Those historical seals are not
distribution requirements for the new wrapper. Public redactions produce
**derived bytes**: their original and published hashes and redaction counts must
be distinguished in the exporter's manifest. The public runner does not claim to
verify a redacted protocol against the original protocol's checksum.

## Limitations and review scope

The following caveats belong to the existing review, not to a new result:

- All four original descriptor designs had rank 13 of 14. Individual coefficients
  are not uniquely interpretable. Do not add regularization or drop a descriptor
  after inspecting test outputs.
- Some test compounds have identical predictions. This is allowed by the format
  rules and does not, by itself, establish identical descriptor vectors.
- The original review noted compression of the predicted range, particularly for
  CYP2D6. That is a prediction-distribution diagnostic, not observed test error.
- The reference was selected after exploratory modeling. No unbiased prospective
  performance estimate or reliable within-series structure–activity relationship
  claim is made.
- Cross-platform numerical equivalence is not guaranteed beyond the recorded
  environment and fixed reproduction tolerance.

The wider program's grouped repeated cross-validation is distinct from these
full-data refits; this report does not newly certify that evaluation protocol.
Format compliance and numerical reproducibility do not establish blind-test
accuracy or leaderboard competitiveness. This method makes no TDI, docking,
structural-prediction or mechanistic claim. Exploratory follow-up is deferred
until after the interim deadline and must not silently alter this recipe.
