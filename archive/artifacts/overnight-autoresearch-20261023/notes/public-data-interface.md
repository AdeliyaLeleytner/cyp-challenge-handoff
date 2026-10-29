# public_data.py interface

Remote runtime (no network at import):

```python
from night.public_data import load_public_data, wide_auxiliary_table, normalize_parent_key

tidy, manifest = load_public_data(
    asset_root,
    sources=["tox21_cyp", "bindingdb_native_articles"],
    excluded_parent_keys=official_parent_keys,
    known_parent_keys=existing_external_parent_keys,  # optional; None -> no claimed net-new count
    config={"targets": ["CYP1A2", "CYP2C9", "CYP2D6", "CYP3A4"],
            "tox21_version": 1, "bindingdb_release": "202610",
            "bindingdb_join_assays": True},
)
wide, target_columns, head_manifest = wide_auxiliary_table(tidy)
```

Default wide grouping is source+assay_id+target+endpoint; only equality p-activity rows passing source QC, IC50/AC50, are used. Native BindingDB contains many assays; source-level IC50 pooling is an explicit root-owned adaptation via group_by=("source","target","endpoint"), not the default. Source/assay metadata remain in the tidy table. Ki/Kd/EC50 are retained separately in tidy data and require explicit endpoints selection; never rename them IC50. Binary outcome rows have task_kind=binary and p_activity missing, so the point-regression helper cannot accidentally ingest them.

Tox21 domains:1671199(CYP1A2),1671198(2C9),1671196(2D6),1671201(3A4), pinned description version1. FullCSV is fetched in bounded2000SID batches. Structures use batchedCID property queries, preserving isomericSMILES when returned. Fit_LogAC50 converts only when metadata declares molar units; otherwise potencyµM may be used, or unverifiedlog units remain unconverted. Inactive/inconclusive fitted values are preserved but excluded from the default point head. Replicate fields and outcomes are retained.

BindingDB native articles202610: monthly ZIP checked against its officialMD5 plus recordedSHA256. No ZIP extraction to paths; streamingTSV handles variable protein-chain tails as documented by BindingDB. Exact humanCYP accession, singlechain, nativeBindingDB-source filters are applied. Endpointinequalities are preserved and reversed underp-transform. Optionalmapping+assaydescriptionZIPs join reactionSetIDs to assayIDs; unresolvedjoins remain explicitly annotated.

Identity helper normalize_and_exclude(df, excluded_parent_keys, smiles_col="SMILES") returns filteredDataFrame+audit, preserving roworder and resettingindex. It adds parent_key (fragmentparent,uncharged,stereo-removed) and canonical_smiles (samebutstereo-preserved). No tautomer canonicalization. OriginalSMILES retained. Bothhelpers returnNone for invalid structures rather than dropping them silently; dropcounts are recorded by the tablehelper.

Cache: asset_root/public_data/cache/<source>/<version>/ with per-response.http.json signatures/hashes and process-safe locks. Publicallowlist only, noauthorizationheaders orprivatestorage. Timeouts/retries/pacing are bounded. Derived table and manifest: asset_root/public_data/derived/<request/exclusion signature>/. Manifest recordsrawcounts, endpointcounts, invalid/excluded/dedupcounts, actualeligiblepoints, structuralnet-newcounts (ifknownsetgiven), sourceversions and sourcefilehashes.

Generic D0/D1 training assembly:

```python
from night.public_data import build_public_auxiliary_dataset
combined, auxiliary_heads, assembly_metadata = build_public_auxiliary_dataset(
    train_df, tidy,
    excluded_parent_keys=all_official_train_and_test_parent_keys,
    primary_columns=primary_target_columns,
    group_by=("source", "target", "endpoint"),
)
all_target_columns = primary_target_columns + auxiliary_heads
```

The exclusion set filters only external public rows. Official training IDs, order, original SMILES and primary labels remain unchanged even when their parents are in that set. This supports the campaign's identical external corpus across evaluation folds and final training. Normalized isomeric identity joins auxiliary labels to any matching official rows when a narrower exclusion policy is deliberately supplied. Unmatched public molecules are appended, with primary labels missing. No binary outcome is cast to potency; only finite equality IC50/AC50 passing source QC enters this helper by default. The assembly helper defaults to source+target+endpoint pooling to keep D0/D1 head counts manageable; the lower-level wide helper retains its assay-specific default. Metadata reports head definitions, source versions and assay IDs, label counts, attachment counts, public-only rows and exclusion counts/hash. Original tidy provenance remains the authoritative measurement record.

Validation: notes/public-data-smoke.py passed seven synthetic groups using the existing local scientific venv, including primary-label preservation, all-official-parent exclusion affecting only public rows, optional exact-isomer attachment and an empty external corpus. No live HTTP or model training occurred. Actual download-format validation remains a remote runtime check; absent/unexpected schemas raise PublicDataError instead of silently using different assays or unfiltered data.
