# Intermediate ADMET output audit: frozen18,460 outcomes

Snapshot manifest time2026-10-26 02:57:34.748491 UTC. **This is not the final audit and not complete acquisition:**18,460 exact requested outcomes are present,13,961 of32,421 requests remain at this snapshot. Of the observed outcomes,18,459 contain120 finite numeric endpoints; one is an explicit whole-row service rejection. One of the numeric rows has an unresolved returned-structure problem, leaving18,458 rows without that feature-identity exception. Source-supervision exclusions are a separate policy layer.

The snapshot contains all4,905 official training structures and750 official blinded-test structures. Both exceptions below are external-only. Neither requires stopping acquisition of the remaining molecules or resubmitting these exact requests.

## Integrity and chemical checks

- Stable manifest/raw/features hashes were verified before freezing. There are18,460 unique request IDs and raw SMILES, no extra IDs, no duplicates, and exact raw/feature order agreement.
- The independent audit checked raw-to-numeric conversion and categorical status flags for every row, including the chemically unresolved row: **zero errors**. There are120 base endpoints plus120 sparse `Invalid Molecule` status-indicator columns. These are not240 biological endpoints. Blank status indicators mean that category was absent; do not automatically feed these sparse status columns into a numeric feature matrix.
- All missing base numeric values are the120 explicitly rejected `Cl` endpoints. No other numeric missingness or nonfinite base value was found.
- All64 documented classification-probability bounds passed. Regression and computed/rule columns were not indiscriminately constrained to0..1.
- For18,458 rows with numeric values and sanitizable service structures, reported MW equals exact monoisotopic mass rounded2dp, and formal charge matches RDKit. No alert atom-index errors occurred. The unresolved Sb row's four alert matches also satisfy index bounds against its17-atom unsanitized returned representation; that positional check does not validate its chemistry.
-18,446 request/service pairs have the same isomeric graph,10 differ by protonation/charge,3 by sulfoxide representation, and1 fails service-structure sanitization. All13 stated protonation/normalization changes pass a separate strict stereo-preserving comparison; they are listed with official IDs. There are36 literal SMILES differences overall, including the unsanitizable row. The legacy summary counts35 because its molecular-details table skips the parse failure; both raw strings for the exception are explicitly preserved separately.
- No exact isomeric duplicate groups arise in requests or parsed service structures. Six groups become identical only after stripping stereo; those distinct requests remain separate. No feature-profile merging was performed.

## Terminal service rejection

`CHEMBL69710`, request `Cl`, ID `68bd1bd95ba465c01242172601c742e27c193936ade6718ca7f8c8b4764c40d4`:

- Raw response says `Invalid Molecule` for all120 endpoints; service SMILES is also `Cl`.
- All120 base numeric values are blank, and all120 corresponding category flags equal1.0. The cache preserves this outcome correctly.
- It has only `union18` and `2d6isoform6` aliases, no official train/test alias, and belongs to the approved28-request original-source quarantine.
- Treat it as a terminal service rejection, not a failed network request or a successful numeric prediction. No imputation, graph repair or retry is recommended.

Exact raw and feature evidence is in `service-rejections.json`, `rejected-raw-evidence.csv` and `rejected-features-evidence.csv`.

## Numeric output with unresolved service graph

`VEITH-BFYUTTCUVJJEFR`, request ID `3488cefb9a5eaad40d36431e5760123e7ee1738496efb2ac00a5204f00afeed1`:

Request:
`NS(=O)(=O)CC1C=C[CH]([Sb-]([Cl])([Cl])([Cl])([Cl])[Cl])C=C1`

Returned service structure:
`NS(=O)(=O)CC1C=CC([SbH](Cl)(Cl)(Cl)(Cl)Cl)C=C1`

The requested graph parses. Sb has degree6, no explicit H, charge−1 and explicit valence6. The service representation changes Sb to neutral `[SbH]`: degree6 plus one explicit H gives valence7. RDKit2026.09.1 raises `SANITIZE_PROPERTIES`: “Explicit valence for atom # 9 Sb, 7, is greater than permitted.” Both representations have17 heavy atoms. Request exact mass is467.79185223991; an unsanitized diagnostic calculation on the returned representation is468.799128692, matching reported468.8. Reported formal charge0 matches the altered returned representation, not request charge−1. Thus numeric self-consistency does not establish requested-graph identity. The request has no specified stereo atoms/bonds; the service graph cannot be certified by sanitized stereochemical comparison.

The server returned all120 finite values, so this is **not** an explicit `Invalid Molecule` rejection. Preserve it as `numeric_returned_unresolved_service_structure`, with no automatic repair or retry. The separate parent-approved feature exclusion is in `feature-eligibility-exclusions.csv` and `.json`; it is not retroactively inserted into the original-source28 quarantine. Both aliases are external-only. Raw/feature hashes, sanitization evidence, charge/mass details and source-shard copies are recorded.

For fresh full-pool matched control/candidate fits, the union of source28 plus this feature exception is29 unique requests. Exactly29 rows are affected in each of `union18` and `2d6isoform6` for own750, briford529 and the fullfit10 companion; `mtaux8` and `2d6single` remain unaffected. The additional Sb original row indices are own30363/22191, briford30584/22277, full31117/22711 (union/isoform). `matched-fresh-pool-exclusion-impact.json` records those effects. No folds/data were changed. Official-only feature inputs are unaffected by these two exceptions.

## Policy and implementation boundaries

`DISPOSITION-snapshot.json` freezes the parent's source-supervision policy, including official-only, historical-native and fresh-full-pool distinctions. The feature-identity audit does not reinterpret a fragment prediction as a prediction for its original metal complex. The earlier source28 policy and this new service-graph exception serve different purposes.

The old lower-level audit stopped when it tried to parse the explicit rejection as a numeric MW. Its failure log is retained. A snapshot-local copy, `audit_intermediate.py`, adds only status-aware numeric/MW handling; `adaptation.json` records both code hashes. Independent `audit_outcomes.py` verifies status flags and numeric values even on the unsanitizable graph. **The collector, full wrapper and full audit contract were not changed.** The proposed minimal final-contract adaptation is in `FINAL_CONTRACT_PROPOSAL.md`.

Snapshot hashes:

- Raw: `4fd8efae4ce80882a006bc544b6e295d1cbe925e843737fad51ddad0e848a496`
- Features: `60efd8495091137b39e7a10a0553d58d9913a8f257fbed259e7f11732e12c9db`
- Disposition: `f5c223e6bb33aae059bfd32e02baacdd71d91c418c8abd2af095b6462fd23c60`

`exception-source-shards.json` identifies the exact contributing shard, its manifest SHA256 and row index for both exceptions; copies are retained. `outcomes-summary.json` gives the status-aware counts; `summary.json` is the adapted legacy audit and still calls all240 encoded columns numeric features, so use the independent120-base/120-status distinction for downstream gating. All raw evidence remains preserved.
