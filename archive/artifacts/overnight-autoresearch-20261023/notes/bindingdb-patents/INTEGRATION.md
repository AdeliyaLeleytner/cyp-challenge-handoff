# Optional BindingDB patents — isolated future child

Implemented only `night/bindingdb_patents.py`; existing `night/public_data.py`, model adapters and frozen R0/D0/D1 outputs were not edited.

Future committed CPU child entrypoint:

```sh
python -u -m night.bindingdb_patents --asset-root /workspace/cyp-night/assets --release 202610
```

The actual asset-root must contain `cohorts.json`, `official-train.csv`, and `official-test.csv`. Every official normalized parent must be present in the exclusion list. Output is fixed to **assets/new_public_patents/**, preserving the original `assets/new_public/` eight-head corpus. Raw files share the immutable paced hash-checked `assets/public_data/cache/` cache; optional assay maps can therefore be reused.

Primary source verified 2026-10-24: [BindingDB download listing](https://www.bindingdb.org/rwd/bind/chemsearch/marvin/Download.jsp) identifies a separate patent TSV archive for release202610, displayed size163.65MB. Anonymous HEAD on [archive URL](https://www.bindingdb.org/rwd/bind/downloads/BindingDB_Patents_202610_tsv.zip) returned200 and171600536bytes. The [official MD5](https://www.bindingdb.org/rwd/bind/downloads/BindingDB_Patents_202610_tsv.md5) is `ad9ceb37d98d1e7935bf4ffbc14e8ee9`. Listing HTML, HEAD headers and checksum text are saved here. No archive was downloaded locally.

Parser behavior:

- Reuses the existing exact human CYP SwissProt-accession, single-chain and organism filters, numeric parsing and inequality reversal.
- Disables the *article-specific* curation-source check because this is a dedicated patent archive; every retained record must instead have explicit `Patent Number` provenance. Rows without it are counted and excluded. No fallback to ChEMBL or full BindingDB.
- Gives rows source=`bindingdb_patents`, document_id=`PATENT:<number>`, retaining article DOI, entry DOI, PMID, curation source, assay/reaction IDs and all original provenance in JSON.
- Keeps IC50, Ki, Kd and EC50 separately; default training view uses only finite equality IC50. Censored values remain available in tidy data but are not exact labels.
- Excludes all official train/test parent structures; deduplicates exact source measurement keys and records counts. Structural overlap with the initial new-public corpus and existing reference CSVs is reported separately.

Outputs match the preparation convention: `measurements.csv`, optional `measurements.parquet`, `auxiliary_wide.csv`, `manifest.json`, `overlap.json`, `data_quality.json`. Data-quality pass requires usable patent IC50 heads, no official-parent overlap, valid structures and patent provenance, and finite uncensored eligible labels. A pass does not establish model benefit or equivalent assay conditions. CLI exits2 on failure.

For a new experimental config, read the separate patent manifest, require quality pass, and verify the measurements hash. Either concatenate its tidy rows with the initial tidy corpus before `build_public_auxiliary_dataset`, or train a separate patent-only auxiliary arm. Keep the source in the head grouping, so patent IC50 heads do not overwrite article/Tox21 heads. Recompute task weights using fitting rows only. Validation-only new heads stay NaN. Do not overwrite original D0/D1 data or silently pool patent/ChEMBL replicates. Patent-family duplication and repeated publication of the same series are possible; the manifest reports structural overlap, not assay independence.

Synthetic smoke passed target/source/provenance filtering, patent numbers, inequality/endpoint separation, all-official-parent exclusion and unchanged initial output-folder checks. `--help` also passes. Source SHA256: `7231938ba352eeaf497b40dfdfdad4536341f16e5add62c8d3af0d81cb85398d`. The module is untracked; no commit, branch switch, model fitting, launch or large download was performed.

## Why native articles yielded only102 usable IC50 values

The supplied remote `notes/new-public-manifest.json` accounts for the reduction:

| Stage | Count |
|---|---:|
| Rows in native-articles-only archive | 93712 |
| Selected exact human CYP target rows | 159 |
| Parsed endpoint measurements | 158 |
| Official-parent records excluded | 1 |
| Retained measurements | 157 |
| IC50 / Ki / Kd retained | 120 / 30 / 7 |
| Equality points across all endpoints | 129 |
| Eligible IC50 used by the initial auxiliary heads | 102 |

No measurements were lost to invalid numeric cells, invalid structures, imported-source filtering, multichain filtering, or declared nonhuman organisms. The main reduction precedes label filtering:93553 archive rows have unsupported target accessions. Thus the small result is consistent with selecting four CYPs from the small native-article subset, which omits both ChEMBL-imported and patent records. It is not evidence that all BindingDB has only102 CYP values.

Target coverage beyond exact accessions has not yet been independently enumerated. `audit_native_target_coverage.py` is a read-only optional remote audit of the already cached native ZIP: it reports CYP-like target names whose accessions fail the existing exact filter. Run this small CPU scan if resolving accession variants matters; its output does not automatically authorize broadening the target filter.
