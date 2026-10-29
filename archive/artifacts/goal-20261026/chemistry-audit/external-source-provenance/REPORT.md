# External original-source provenance audit

**Propose quarantining28 exact prepared request rows from future matched supervised fits.** The five previously verified carbon-free residuals are included. Four additional metal-parent/source cases remain explicitly ambiguous, not included. This is a proposal: no data, folds, models, collection records or resource state were changed.

The original raw source records were audited here, not merely the already-cleaned ID map. Source fingerprints and exact proposed row IDs, SMILES, request hashes, source identifiers, target values and fold memberships are preserved in this directory. The completed strict-tautomer reference remains historical evidence under its actual source curation; this audit does not retrospectively certify it for original-assay identity.

## Scope and verification

The saved public source inputs contain85,535 PubChem assay rows, representing17,107 SID records, and25,841 ChEMBL aggregate records:42,948 source records in all. Every original and cleaned SMILES parsed. The native producer was replayed: ChEMBL first-connectivity-key selection, PubChem mean pivot by cleaned SMILES, fixed[-150,50] response clipping, sorted-first connectivity-key selection, then joins into the actual saved `union18` pool. Of the source records,41,656 contribute to at least one prepared destination. **208,315 source-target comparisons reproduced saved values with zero mismatches**, including missing values. A source can join more than one prepared destination; counts are not assumed one-to-one.

The source pool for the affected2d6 member is a subset of these rows apart from two official challenge IDs, neither involved here. Membership and selected target counts were independently read from every actual cohort/member CSV and JSON, not inferred from the union count.

## Observed transformations

Counts below describe contributing source records; several can lead to one prepared molecule.

| Source-to-cleaned transformation | Records |
|---|---:|
| Exact isomeric graph preserved |36,420|
| Original fragment retained after ordinary functional normalization/uncharging: parent candidates |1,427|
| Whole entity normalized/uncharged |59|
| Same atom connectivity, with bond-order, charge or stereo rearrangement |3,604|
| Original fragment connectivity retained, with such rearrangement |104|
| Transition-metal context lost |38|
| Tin context lost |1|
| Nonmetal carbon-free residual from lithium chloride |2|
| Explicit stereo-only representation change |1|

The last stereo-only row is PubChem SID4254252, prepared `VEITH-ZJZYQKKDHFXIAM`: its saved original has a specified chiral center and the cleaned request leaves it unspecified. This is an ambiguity flag, not a new automatic quarantine. The connectivity diagnostic deliberately ignores bond order, aromaticity, charge and stereo while retaining atom identities/isotopes and adjacency. It does **not** establish stereochemical or tautomer equivalence and is never used for merging or training. No capped tautomer enumeration was used to declare equivalence.

Across all42,948 records there are233 metal-loss records;223 contribute to the prepared pool. Among the active records,38 lose transition metals and1 loses Sn. The rest mostly remove Na/K/Ca/Li; ordinary organic-drug counterion removal is not itself an error. No nonmetal single-fragment original loses heavy atoms. Two concerning metal-loss source records were discarded by the original producer's first-key selection and do not contribute labels: SID4253650/CID6713829 (Cu/aspartate) and SID4254069/CID16684735 (bonded Sn/nucleoside). They are documented, not unnecessarily quarantined from nonexistent training rows.

## Many-to-one source records

There are1,649 prepared destinations with more than one distinct original isomeric graph. This does not mean1,649 wrong entities: salts, protonation, tautomers, source conventions and stereochemical variants all contribute. The classifications are147 common retained-parent/counterion-normalization candidates;874 other original transformations leading to one cleaned graph;620 different cleaned graphs joined by the original connectivity-key recipe;6 proposed-quarantine groups; and2 ambiguous metal/source groups. The620 groups remain a broader stereochemistry/protonation/tautomer source-join caveat, not silently merged or declared erroneous here.

Within PubChem's actual mean pivot,65 cleaned structures aggregate different original CIDs. Four are in the28-row proposal: the nicotine request combines four original graphs/CIDs, EDTA combines three metal records, isonicotinic acid combines two Pt records, and ammonia combines the Pt and Ru records. All65 are listed in `pubchem-pivot-original-collapses.csv`; the others are not automatically treated as misattributions.

The [previous seven-entry report](../full-pool-preaudit/carbon-free-source-audit/REPORT.md) establishes the five carbon-free mismatches directly against live primary records. Additional focused primary lookups confirmed the two distinct [Mn/EDTA](https://pubchem.ncbi.nlm.nih.gov/compound/407541) and [Cu/EDTA](https://pubchem.ncbi.nlm.nih.gov/compound/407542) source records, loss of Co/cyanide from [CID6604202](https://pubchem.ncbi.nlm.nih.gov/compound/6604202), explicitly bonded Sn in [CID16684901](https://pubchem.ncbi.nlm.nih.gov/compound/16684901), and the two-ligand Zn entity in [CID4019772](https://pubchem.ncbi.nlm.nih.gov/compound/4019772). Saved responses are included. The audit does not reconstruct coordination bonds or certify the physical assay specimen.

## Quarantine versus ambiguity

The28 proposed rows have loss of a defining metal/complex/entity context, explicit bonded-metal deletion, aggregation of different metal-containing entities into a ligand, or one of the five verified inorganic residuals. The evidence is a changed source-to-request entity, not lack of carbon or unusual elements. Each exact source relationship and reason is in `metal-source-adjudications.csv`; `proposed-quarantine.csv` is the machine-readable28-row proposal.

Four cases remain separate:

- **CHEMBL1382627**, silver sulfadiazine: Ag is removed, but [ChEMBL explicitly designates CHEMBL439 as active/parent](https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL1382627/). This supports a deliberate parent convention; whether it is appropriate for the assay needs adjudication.
- **CHEMBL1411246**, Zn dithiocarbamate: metal-complex concerns exist, but [ChEMBL designates a nonmetal active/parent CHEMBL1615644](https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL1411246/).
- **CHEMBL1555810**, Zn salt of an organic cephalosporin: [ChEMBL designates active/parent CHEMBL1626208](https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL1555810/). Standard drug-salt normalization is plausible.
- **CHEMBL359744**, anthracycline receiving a PubChem record with disconnected neutral W: loss is certain but the W source representation/assay role is unresolved. A dot does not justify inventing coordination.

These four are not automatically counted as confirmed wrong targets. Likewise, the intact hydroxylamine and pyrophosphoric-acid rows are retained as applicability cases, not declared invalid. The86 unusual-element request molecules from the full-pool preaudit remain an applicability slice; this audit does not reject them merely because of their elements.

## Effect if the28-row proposal is approved

The same28 external rows occur in both affected members of every cohort. None is an official challenge row; none contributes a direct challenge pIC50, log2fc, TDI or Emax target. Each cohort loses144 selected external target cells from `union18` (135 Veith values and9 ChEMBL values), and29 from `2d6isoform6` (27 Veith and2 ChEMBL). Some source labels on a quarantined row may be individually legitimate; this is conservative whole-row quarantine of a mixed-provenance representation, not a claim that every target cell is wrong. A more selective target-mask intervention would be a different explicitly versioned proposal.

| Cohort | Member | Before | Proposed rows | After if approved |
|---|---|---:|---:|---:|
| own750 |union18|30,916|28|30,888|
| own750 |2d6isoform6|22,744|28|22,716|
| briford529 |union18|31,137|28|31,109|
| briford529 |2d6isoform6|22,830|28|22,802|
| fullfit10 companion |union18|31,670|28|31,642|
| fullfit10 companion |2d6isoform6|23,264|28|23,236|

`mtaux8` and `2d6single` lose zero rows in all three cohorts. Thus the proposal touches56 component rows per cohort,168 across these three data views, representing28 unique request molecules. There are no new outer-holdout exclusions or changes to the original outer truth sets. `quarantine-exact-rows.csv` provides original row indices and every selected value; `quarantine-fold-impact.csv` gives exact train/validation indices for each existing fold.

If approved, create new children from the preserved nodes. Apply the same source-curation treatment to control and feature models; preserve surviving original validation membership and strict-tautomer train-side exclusions. Reindex deleted rows, preserve hyperparameters and primary-task weights, and reseal input/spec hashes. The affected neural members would require20 outer-cohort fits and10 full-fit-companion fits under the existing five-fold recipes. Unchanged-member reuse requires the existing provenance/hash checks. This audit authorizes or launches none of those fits. The earlier strict-tautomer scores cannot stand in for a newly curated matched control.

## Artifacts and limits

- `all-source-transformations.csv`, `classified-source-transformations.csv`, `refined-source-transformations.csv`: complete raw original→cleaned→prepared mapping with source identifiers and observed transformations.
- `metal-loss-source-records.csv`, `carbon-free-source-records.csv`: all affected originals, including producer-discarded records.
- `collapsed-original-entities.csv`, `classified-collapses.csv`, `pubchem-pivot-original-collapses.csv`: exact many-to-one evidence.
- `proposed-quarantine.csv`, `ambiguous-parent-source-review.csv`, `metal-source-adjudications.csv`: proposed decisions and retained uncertainty.
- `quarantine-pool-impact.csv`, `quarantine-exact-rows.csv`, `quarantine-fold-impact.csv`: exact consequences on saved cohorts.
- `source-value-replay-mismatches.csv`: empty because replay matches; `summary.json`, `refined-summary.json` contain counts.
- `input-sha256.json`, `pool-input-sha256.json`, `artifacts-sha256.json`: immutable input and output fingerprints.

Reproduce with the project Python: `audit_sources.py`, then `adjudicate_and_count.py`, then `refine_transformations.py`. These scripts write only this artifact directory and never fit models or change source data. Live primary responses are cached; reproducing the audit does not issue network requests.

Passing the separate final ADMET output audit will certify request/output alignment and numeric integrity, not repair upstream source curation or validate prediction accuracy. The source audit quantifies observed transformation patterns; it is not a full manual review of all external assays or all620 connectivity-key joins.
