# Seven carbon-free entries: source identity audit

Audited 2026-10-26. Scope is exactly the seven preflagged request structures; no collection, training or data edits were performed.

**Two entries retain their saved original structure. Five are fragments of source salts/metal complexes, and one of those pools measurements from two different source compounds.** This is a source-to-model representation problem, established by the saved `orig_smiles` and verified primary compound records. It is not an inference from lack of carbon, instability, unusual elements or failed parsing.

All eight PubChem CIDs and CHEMBL69710 were retrieved through primary database tools. Every saved `orig_smiles` matches the corresponding live primary SMILES as an isomeric graph. The precise physical material, coordination geometry and whether a specimen was used as a deliberate control cannot be certified from these records alone. Both intact entries have five saved Veith measurements marked Inactive; that does not establish a designated negative-control role.

| Request / pool ID | Saved source identity | Finding |
|---|---|---|
| `NO`, VEITH-AVXURJPOCDRRFD | SID11111291, [CID787 hydroxylamine](https://pubchem.ncbi.nlm.nih.gov/compound/787) | Intact. Original and requested SMILES are `NO`. |
| `O=P(O)(O)OP(=O)(O)O`, VEITH-XPPKVPWEQAFLFU | SID4253134, [CID1023 pyrophosphoric acid](https://pubchem.ncbi.nlm.nih.gov/compound/1023) | Intact isomeric graph; only SMILES traversal differs. |
| `O=S(O)O`, VEITH-LSNNMFCWUKXFEE | SID4253982, [CID426356](https://pubchem.ncbi.nlm.nih.gov/compound/426356), NSC-187613; original `[NH2-].[NH2-].[NH2-].[NH2-].OS(=O)O.OS(=O)O.[Co]` | One sulfurous-acid fragment retained from the multicomponent cobalt record. Activity is not independently an assay of sulfurous acid. Primary record itself is a disconnected representation; coordination fidelity remains uncertain. |
| `NNNNN`, VEITH-ZKVJJVAZTBDPNW | SID11114293, [CID6604952](https://pubchem.ncbi.nlm.nih.gov/compound/6604952), NCGC00025374-01 / Tocris-1439; original `N.N.N.N.NNNNN.NNNNN.O.O.Cl.Cl.Cl.Cl.Cl.Cl.[Ru].[Ru].[Ru]` | N5 chain retained from a much larger multicomponent Ru record. No evidence of a separately tested pentazane. The N–N chains are already present in the primary record; this audit does not certify that record's coordination representation. |
| `Cl`, CHEMBL69710 | [ChEMBL69710 CHLOROLITHIUM](https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL69710/) and SID11111379 / [CID433294 lithium chloride](https://pubchem.ncbi.nlm.nih.gov/compound/433294); original `[Cl-].[Li+]` | Li removed and chloride protonated to the HCl SMILES. ChEMBL has CYP3A4 pIC50=4.5 from three saved measurements; Veith contributes five max-response endpoints. These belong to lithium chloride, not an independently tested hydrochloric-acid molecule. Saved ChEMBL `inchi_key` is also the cleaned HCl key, while live ChEMBL key is KWGKDLIKAYFUFQ-UHFFFAOYSA-M. |
| `N#[O+]`, VEITH-KEJOCWOXCDWNID | SID11112083 / [CID6604165 sodium nitroprusside](https://pubchem.ncbi.nlm.nih.gov/compound/6604165); original `[C-]#N.[C-]#N.[C-]#N.[C-]#N.[C-]#N.N#[O+].[Na+].[Na+].[Fe+2]` | Nitrosyl fragment retained, losing Fe, Na and five carbon-containing cyanide fragments. This source was not carbon-free. It is not an assay of the isolated request fragment. |
| `N`, VEITH-QGZKDVFQNNGYKY | SID11111627 / [CID5460033](https://pubchem.ncbi.nlm.nih.gov/compound/5460033), original `N.N.Cl[Pt]Cl`; **and** SID11111739 / [CID6603984](https://pubchem.ncbi.nlm.nih.gov/compound/6603984), original `N.N.N.N.N.N.N.N.N.N.N.N.N.N.O.O.[Ru].[Ru].[Ru]` | Both different metal-complex records collapse to ammonia. The producer pivots by cleaned SMILES with mean aggregation, so all five endpoint values average the two sources. These are not ammonia assay measurements. |

The intact structures are chemically plausible inorganic/reactive screening entries. Their prediction applicability should remain a separate question. The five fragments pass SMILES parsing and exact request hashing; those checks cannot repair the source/assay mismatch.

## Concrete target consequence

All seven rows appear in both `union18` and `2d6isoform6` prepared pools (14 component rows). The six VEITH-prefixed rows carry public max-response values. CHEMBL69710 also carries ChEMBL CYP3A4 pIC50=4.5. Actual selected heads remain controlled by each member's existing specification.

For `N`, the saved Pt and Ru CYP2D6 responses are −39.42 and −22.83, yielding the stored **−31.125**. The analogous pooled values are CYP1A2 −43.0, CYP2C19 −77.49, CYP2C9 −60.275, CYP3A4 −42.1895. For `NNNNN`, the stored CYP2D6 response **−93.85** comes from the entire CID6604952 record. Adding ADMETlab predictions for ammonia or an N5 chain would make the feature representation internally consistent with the cleaned request, but would not make these experimental targets belong to that request molecule.

This problem predates ADMETlab acquisition. Earlier source-alias audit checked the id-map's already-cleaned `SMILES` against `request_smiles`; it did not claim that raw public-assay `orig_smiles` were unchanged. Here the earlier boundary is now explicitly traced. The scope is seven flagged requests, not an estimate of the rate of such errors across all 26,766 external-only requests.

## Practical recommendation, not an applied change

Preserve the frozen native reference and all collection records. Record these five requests as `upstream_fragment_assay_identity_mismatch`; record the ammonia row additionally as a conflation of two source identities. Keep the two intact rows as an applicability slice, without declaring them invalid or controls. A later curation branch should review these five target rows independently of feature efficacy; compare any corrected control and feature model on the same curated membership. Do not silently substitute full complexes into the existing feature rows, merge the original complexes, infer coordination geometry, or reuse fragment predictions as full-complex predictions. No such branch or retraining was performed here.

## Reproducibility

- `saved-pubchem-matched-rows.csv`: all40 underlying saved assay rows, retaining SID/CID/isoform/outcome/curve fields.
- `saved-chembl-matched-rows.csv`: the one aggregated ChEMBL record, including three-measurement count and original SMILES.
- `source-identity-comparisons.json`: nine source identities and primary graph comparisons.
- `native-training-rows.csv`: the14 saved prepared component rows.
- `primary-0.json`, `primary-1.json`: exact database tool responses, including aliases and structures.
- `input-sha256.json`: source-file fingerprints; `audit_sources.py` reruns local comparisons against the saved primary responses.

Run using `/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python audit_sources.py`. Primary records were checked on2026-10-26; all9 saved originals matched. No ADMETlab requests or paid compute were used.
