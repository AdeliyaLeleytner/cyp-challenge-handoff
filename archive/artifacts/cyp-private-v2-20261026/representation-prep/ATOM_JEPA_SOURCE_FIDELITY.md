# Bounded notebook-16 fidelity check

The cached adlvdl notebook16 feeds **one 256-dimensional last-block slice before final normalization** to TabICL under the pinned Atom-JEPA0.3.0 API. It does **not** concatenate all eight layers, and it does **not** use the post-final-normalization `layers="last"` route tested in P9.

Exact cached code references (repository snapshot `5ab3d7c9792e09da3fd10a18971a6696bdd62ecb`):

- `sources/adlvdl/encoders.py:58–65` loads `AtomJEPA.from_pretrained("molecules")`, calls `model.embed(..., layers="all")`, and saves the concatenated sample batches. This cache has shape n×8×256; the concatenation is over samples, not over the eight feature layers.
- `sources/adlvdl/notebooks/16_encoders.py:149–152` selects `_jepa[_idx, -1, :]`. Only the last of the eight cached blocks, width256, enters that notebook's features. The comment calling this “the package default” is misleading for the inspected0.3.0 API.
- `atom-jepa-0.3.0-source/atom_jepa/api.py:198–205` collects requested integer block outputs with hooks and separately obtains the normalized encoder output. Lines236–237 explicitly distinguish integer blocks/`"all"` (before final norm) from `"last"` (after final norm).
- `sources/adlvdl/notebooks/16_encoders.py:211–215,231–240` constructs splits per endpoint and passes that endpoint's `_tr` feature rows and `y_true` directly to `predict_subprocess`.
- `sources/adlvdl/src/cyp/tabular_models.py:137,142` sets128 PCA features and2 estimators. Lines492–512 cast input tofloat32 and fit `PCA(n_components=min(128,n_rows,n_features), random_state=42)` on the supplied endpoint training rows. There is no separate StandardScaler in this path. `svd_solver` and whitening use sklearn defaults (auto andFalse), rather than P9's explicitly fullSVD.

P9 deliberately tested a controlled alternative: post-normalization last256, StandardScaler followed by PCA96, with the scaler/PCA trained on all eligible official training rows in each fold before target-specific labeled contexts are selected. The published notebook instead uses pre-normalization last256, PCA128 without an external scaler, fitted on each endpoint's supplied training rows. The representation, scaling, dimensionality, and PCA fitting population therefore differ materially.

The source wrapper also uses a mutable model alias and package defaults; its exact historical weight/package resolution is not recovered by this code inspection. Current P9 pins are stronger provenance, but they do not make the pipelines equivalent.

Consequently, P9's negative result applies to its post-normalization/PCA96 route. It is not evidence that the published notebook16 recipe was reproduced and failed. That precise pre-normalization/PCA128 route remains an untested next lever. No extra encoder inference, layer sweep, model fit, or large fetch was performed for this check.
