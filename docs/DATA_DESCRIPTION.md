# Data Description

This document describes the data used by the selected Direct Inhibition regression model. The broader research archive contains additional experiments; collecting a dataset does not imply that it contributes to the submitted predictor.

## 1. Official task data

| Data | Role |
|---|---|
| 4,905 official training molecules | Primary direct-inhibition supervision, with endpoint-specific missingness |
| 750 blinded query molecules | Prediction inputs; experimental target labels are unavailable to the modeling pipeline |
| Official single-concentration +NADPH screening measurements | Separate auxiliary tasks and targets for screen-response teachers |
| Official direct-inhibition confidence limits | Interval-aware losses and evaluation where the corresponding model recipe uses them |

The numbers of observed official direct-inhibition targets are **1,412 for CYP1A2, 1,285 for CYP2C9, 1,493 for CYP2D6 and 2,335 for CYP3A4**. These are endpoint measurement counts, not disjoint molecule counts. Missing values are not converted into zero activity or assumed non-inhibition.

The primary unit is **pIC50 = -log10(IC50 in mol/L)**. Thus an IC50 supplied in nM is converted as `9 - log10(IC50_nM)`, and an IC50 in micromolar units as `6 - log10(IC50_uM)`. Already logarithmic values must not be transformed again. Reported inequality relations and intervals need to retain their meaning after conversion; taking the negative logarithm reverses the ordering of concentration bounds.

Single-concentration log2 fold change, percentage inhibition, maximal screening response, IC50, Ki and binding Kd are not interchangeable observations. The submitted model uses assay-specific auxiliary heads or predicted screening features instead of declaring all such endpoints to be direct-inhibition pIC50.

## 2. Public external supervision

The graph-model training pipeline includes public **ChEMBL CYP measurements** and **PubChem/Veith CYP screening data**, including the AID1851 assay collection. These supply five isoform-specific auxiliary channels per source in the 18-task task set. The separate 8-task task set uses the official primary and screening endpoints.

External rows preserve source identity and assay/endpoint distinctions in preparation records. Potency values, screening responses and missingness remain distinct. External auxiliary losses are weighted separately from official primary losses. In the optimized 18-task component used for CYP2C9, the external task weight is 0.3.

The broader audited structure pool comprised 32,421 unique requested structures: 4,905 official training, 750 blinded query, 35 additional official-source structures, 24,701 ChEMBL 37 structures and 2,030 PubChem/Veith structures under that audit's identity convention. This is a **feature-collection inventory**, not the supervised training size of every model. Final components use their own prepared source snapshots, eligibility filters and missing-label masks; historical source snapshots are not all interchangeable with this inventory.

Source IDs and raw SMILES are retained alongside derived structural identifiers. Counts of source records, assays, aliases, standardized graphs and supervised targets can differ. Duplicate records and stereochemical variants must not be silently treated as independent evidence of the same endpoint. A source-provenance audit also removed known fragment-only/problematic source entities from the optimized CYP2C9 external-data training pool.

No private proprietary experimental dataset is declared as direct supervision for this model. Pretrained representations are an additional source of learned information; their complete pretraining membership was not independently audited, so a universal absence of pretraining overlap is not claimed.

## 3. Molecular identity and preparation

The submitted file retains the official molecule IDs and raw SMILES. Model-specific transformations are applied to derived representations rather than replacing these export identifiers.

Graph and descriptor models parse molecular structures with RDKit. Some single-target branches use largest-fragment selection and charge neutralization. Other branches deduplicate using the connectivity block of InChIKey, which does not distinguish stereoisomers. Therefore, preserving raw stereochemical SMILES does not mean that every historical component distinguishes all stereoisomers. This is a limitation of the mixed pipeline, not a uniform stereochemistry-preservation guarantee.

The three-dimensional molecular branch generated valid conformers for all 5,655 official training and query structures. Saved coordinates support molecular representation learning; they are not experimentally determined bound poses, docking results or measurements of CYP affinity. Invalid two-dimensional or zero-coordinate substitutes were not counted as valid conformers in the coverage check.

Some historical components used full-pool preprocessing before cross-validation, including target/descriptor scaling. Their OOF metrics must be interpreted with that limitation. The newer screen-informed SVR pipeline fits scaling and PCA within each training context. A clean downstream fitting procedure does not retroactively correct an upstream preprocessing issue.

## 4. Representations versus measured labels

The selected model combines several types of input:

- Molecular graphs and computed molecular descriptors for graph-regression components.
- Three-dimensional conformers and Uni-Mol2 representations for one CYP2D6 base component.
- A frozen 600-dimensional learned ADME embedding for screening teachers.
- A 2,048-dimensional ADME-adapted CheMeleon embedding for the CYP2D6 student.
- Four cross-fitted predicted screening responses as additional student features.

Neither a pretrained embedding coordinate nor a predicted screen response is an experimental measurement for a query molecule. The teacher predictions provide learned assay-related information while retaining the distinction between screening response and potency.

ADMETlab property vectors were collected in the broader project: 32,419 complete numerical vectors and 32,418 feature-eligible rows after identity checks, with all 5,655 official molecules covered. These **120-property service predictions are not the ADME600 embedding**. They are not a separately added property block in the selected model described here.

Likewise, affinity scoring and expanded external-data experiments explored elsewhere in the project do not imply that docking, Nesso affinity scores, BindingDB additions or every collected external endpoint are present in this submission. They are not additional components of the frozen assembly in the model report.

## 5. Fitting, selection and query access

Official training labels support model development and the frozen final fits. Later development procedures used an explicitly restricted development pool and separate confirmation handling; historical components did not all follow the same protocol. The final screen-informed production stage uses permitted official labels with fixed fold exclusions after its recipe has been chosen, rather than searching hyperparameters on its production OOF outputs.

Query molecule structures are used to produce predictions. Query prediction means and standard deviations are also used by the explicitly transductive serving transformation. No row-level experimental query labels enter these fits. Historical calibration constants and final endpoint selection are informed by leaderboard feedback, so this is not a purely training-only model-selection history.

Development hit-expansion views and scaffold splits probe different generalization conditions. The official query construction uses chemically related expansions around selected hits; it is not a random sample of the training population. CYP2D6 was not a driver of the hit expansion. This makes a local scaffold score and a leaderboard score different estimands, even when they use the same numerical metric.

## 6. Availability

The methodological update does not redistribute datasets or trained checkpoints. Existing data sources, software and pretrained representations retain their respective access and license terms. Exact prepared-data manifests, feature hashes, folds and fitted transformations are retained privately for provenance checks. This narrative report is not a standalone retraining package.
