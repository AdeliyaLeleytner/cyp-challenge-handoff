# Public data preparation child

Launch entrypoint from the future committed ORX child, with the actual staged asset root:

```sh
python -u -m night.public_prepare --asset-root /workspace/cyp-night/assets
```

The CLI requires `cohorts.json`, `official-train.csv`, and `official-test.csv` in that root. It verifies that every normalized official train/test parent is in `excluded_parent_keys`, then excludes these parents from external public data only. Optional existing `reference/public_data/{chembl_all_isoforms,pubchem_all_isoforms}.csv` tables are read only for structural overlap and net-new counts. Original R0 assets and reference/neural code remain untouched.

Default sources are the four version-1 Tox21 CYP assays and BindingDB native articles release 202610, including optional assay joins. Loader options can be supplied through `--config path.json`; `--sources tox21_cyp` or `--sources bindingdb_native_articles` allows an explicitly source-specific child. No silent fallback is performed. Missing optional parquet engine leaves CSV authoritative; `--no-parquet` skips that extra artifact.

Outputs under `assets/new_public/`:

- `measurements.csv` and, when an engine is installed, `measurements.parquet`: tidy measurements and provenance.
- `auxiliary_wide.csv`: equality-only QC-filtered IC50/AC50, separate source/target/endpoint heads, median within normalized isomeric identity.
- `manifest.json`: code/source/input/output hashes, source versions, loader source counts, exclusion evidence and head definitions.
- `overlap.json`: overlap with the existing reference corpus and between new sources; these are structural overlaps, not evidence of independent assays.
- `data_quality.json`: `running`, `pass`, or `fail`; CLI exits 2 on failure. Pass requires exclusion completeness, no leaked official parents, valid normalized structures, finite uncensored regression labels for eligible points, and at least one eligible IC50/AC50 row per requested source. It does not claim predictive benefit or identical assay domain.

Integration should be an explicit D0/D1 config branch, leaving all R0 components unchanged. At `neural.run_trial`'s current `build_component_data` boundary, append the new heads to the returned training table with `build_public_auxiliary_dataset`; use the current component's lower-case primary names and retain `primary_mapping`. Add the returned head names to `target_columns`, recompute task weights using fitting rows only, and record assembly/source manifests in model metadata. The official-only validation table must have these new auxiliary columns set to NaN. Query predictions and exported primary column mappings stay unchanged. A consumer must require `data_quality.passed` and verify the measurement file's SHA256 against `manifest.json` before ingestion. This is integration guidance, not an edit to the reference or neural adapters.

Minimal live schema smoke on 2026-10-24: AID1671196 version1, SID144205501/CID17931; filtered POST returned exactly one SID, CID property POST resolved SMILES, and parser returned three AC50 replicates plus a separate binary outcome. Fit metadata explicitly states molar logarithmic units; one replicate passed inhibitor QC. Only the description, the first 4096 bytes of concise CSV, one full SID row and one CID property record were accessed locally. No archive or full assay table was downloaded. Evidence: `public-data-live-schema.json`, `public-data-live-smoke.json` and their tiny cache.

Synthetic preparation smoke passed quality/exclusion gates and the full artifact-writing path using an injected fixture loader. No network, model training, launch, branch switch or commit was performed by this helper.
