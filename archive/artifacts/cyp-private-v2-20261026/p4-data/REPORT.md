# P4/D1 bounded raw-record pilot — private, no fits

The acquisition produced a useful curation panel, **not a defensible general cross-probe benchmark**. It preserves780 unique activity records:773 IC50 records plus the7-row CHEMBL10/CYP1A2 mixed-estimand control. The selected metadata pools were exhausted below the3000-record cap. Only2 compound-targets retain exact, unflagged measurements across different probes, so this panel cannot establish a general substrate-context advantage. No further acquisition or model fitting was performed.

## Acquisition and scope

Initial round:96 main records/92 compound IDs,72 already present by ChEMBL ID. Root authorized expanding the same saved metadata pools after low yield. Round2 retained all available assays in the up-to100 human/confidence9 metadata pools for midazolam, dextromethorphan and bufuralol, excluding earlier queried assay IDs. Selection depended on assay metadata, not numerical activity. All returned values, missing rows, inequalities and flags remain in raw JSON. First-round files remain unchanged. ChEMBL status reports ChEMBL37, release2026-05-01. The API responded successfully; capped pages of up to250 records were sufficient. This is a metadata-selected sample, not representative prevalence across ChEMBL.

| Retrieval context | IC50 records | Proposed exact records |
|---|---:|---:|
| CYP3A4 DBOMF |21|9|
| CYP3A4 midazolam |367|271|
| CYP3A4 paired midazolam/testosterone document |2|2|
| CYP2D6 dextromethorphan |235|102|
| CYP2D6 bufuralol |148|68|

The780 records cover158 assays and122 documents; their assay and document metadata are complete in the inventory. Source registry counts are761 literature(src1),2 PubChem(src7),2 DrugMatrix(src15),15 BindingDB patents(src37). The curated source canonical SMILES is retained exactly. It is not proof that we recovered the physical salt/formulation used in the assay. No local neutralization, fragment removal, stereo erasure or tautomer merging occurred.

## What the records say

Main IC50 relations:459 `=`,261 `>`,29 `<`,1 `>=`,23 missing. Units are nM for750 and absent for23. Missing-value comments say22 “Not Determined” and1 “corresponding IC50 reported as Active”; these are not numerical IC50s or invented bounds. A reported concentration inequality is preserved and reversed correctly only in the explicitly derived negative-log concentration column. No AC50/Ki conversion or potency-range imputation occurred.

The conservative exact-comparison proposal contains452 records/442 isomeric-graph–target combinations, after separating controls, inequality/missing records, source QC flags, potential duplicates and one unavailable structure. Ten source flags are “Outside typical range”; these remain observed records and are **not declared invalid**, merely separated from this first exact-value contrast. The single unavailable structure is activity15445939/CHEMBL6067487 (`canonical_smiles=null`), not a failed chemistry repair.

Preparation/probe/time/concentration mentions are extracted as descriptive flags only. Exact assay descriptions and parameters remain available. “At XµM” is not assigned automatically to probe versus inhibitor; absent NADPH language does not prove no preincubation. Recombinant, microsomal and other systems remain separate observed contexts. No missing concentration, free fraction, NADPH timing or Emax definition is invented.

Only two exact compound-target examples span probe mentions:

- CHEMBL332643/CYP3A4: testosterone2500nM, midazolam1′-OH1100nM, midazolam4-OH1000nM. Same cited document; microsomal/recombinant preparation not established by these descriptions. The midazolam metabolites must not be collapsed silently.
- CHEMBL1484/CYP2D6: dextromethorphan1590nM and bufuralol1780nM, described as human liver microsomes. Different assay records/context details remain; this is not repeat-measurement uncertainty.

These are retained positive controls for context bookkeeping, not evidence of a universal directional shift. The initial6 retrieval-context overlaps shrink to2 exact probe-context examples after respecting relation/QC/context semantics.

## Overlap and what is genuinely new

Main records represent626 parseable exact isomeric graphs.418 match the prepared32421 queue,435 the old prepared ChEMBL structures,17 old prepared PubChem,458 original ChEMBL structures,17 original PubChem. **163 graphs are absent from both saved original external-source structure sets**. This differs from merely absent prepared graphs because source standardization can change the graph. Canonical isomeric SMILES are used only for read-only equality diagnostics, retaining original strings and all IDs.

Sixteen main graphs match official training structures; none match the750 blinded-test graphs. Before any fit, source records corresponding to each local frozen holdout must be removed from every supervised task using the campaign’s established exact/stereo-preserving alias policy, followed by the existing strict equivalence audit. Mere public assay overlap with blinded-test structures would be a disclosure/rules question, not proof of hidden-label access; none appears here. The452 proposed exact rows include419 matching prepared old ChEMBL graphs and33 not matching them; this is mostly a context/estimand recuration experiment, not hundreds of independent new exact compounds.

## Matched comparison proposal, not authorization to train

If this limited panel is used as an auxiliary recuration arm, compare the same452 proposed exact records and the same compound-target membership in both arms. Both receive `record_weight=1/n` for each exact isomeric-graph/target group, so each compound-target contributes totalweight1. Pooled arm uses molecule+target; context arm adds prespecified probe/preparation/unknown indicators while keeping model capacity controlled. Keep the official target loss, outer/inner splits, source purges, minibatch mass and total external weight identical. Do not replace the pooled arm with per-compound medians, which changes the estimand/loss. Evaluate on unchanged official holdouts, including contrary endpoint effects.

This can test practical augmentation under the sample, **not identify a causal probe effect**, because context is almost entirely confounded with compounds/documents. Censored-loss inclusion is a separate later factor using the291 explicit inequalities; it must not be combined with the context contrast. Context-specific uncertainty cannot be estimated from the two paired examples. Given the low paired coverage and new P7 priority, stop this contrast here and preserve the panel for a future justified design.

## BindingDB bounded metadata check

Official info, download and REST pages were accessible and saved with URL/hash/UTC evidence. The info page states imports from ChEMBL and selected PubChem and distinguishes staff-curated data; current page specifies CC BY3.0 for staff data and CC BY-SA3.0 for imported ChEMBL data. License/version attribution should be verified for an actual future downloaded subset. No BindingDB bulk or target affinity response was downloaded.

The official download page exposes source-separated release files and a necessary assay join: Reaction Set ID→Entry ID+Assay ID via `BindingDB_rsid_eaids.tsv`, then assay descriptions via `BindingDB_Assays.tsv`. The observed release names include202610. Target REST retrieval by UniProt with a potency cutoff does not provide an unbiased weak/negative pool, and its row limit cannot be assumed to bound server download. CYP-specific independent counts remain unmeasured. Importantly,15 records already in this panel are ChEMBL source37 **BindingDB Patent Bioactivity Data**; BindingDB is not automatically a new independent source. Deduplicate by source document/assay/compound/measurement provenance before any augmentation.

Primary metadata pages: https://www.bindingdb.org/rwd/bind/info.jsp ; https://www.bindingdb.org/rwd/bind/chemsearch/marvin/Download.jsp ; https://www.bindingdb.org/rwd/bind/BindingDBRESTfulAPI.jsp . Full raw API URLs are in the query ledgers.

## Files

- `expanded-activity-occurrences.json`: every780 original full JSON record plus retrieval provenance.
- `inventory/activity-inventory.csv`: joined record/assay/document/source inventory and explicit review flags.
- `inventory/compound-inventory.csv`, `assay-inventory.json`, `document-inventory.json`: frozen inventories.
- `inventory/proposed-exact-matched-records.csv`:452 proposed records and weights; not an approval to fit.
- `inventory/exact-cross-probe-records.csv`:5 records for2 compound-targets.
- `inventory/SUMMARY.json`: counts, overlap and input hashes.
- `FROZEN_MANIFEST.json`: file hashes; metadata/query evidence remains under raw/,round2/,metadata/.

No fits, spending, ADMET calls, public writes or submissions occurred. Original data and incumbent artifacts were not edited.
