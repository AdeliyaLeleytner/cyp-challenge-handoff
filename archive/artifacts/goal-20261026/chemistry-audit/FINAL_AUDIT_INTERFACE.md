# Final full-output audit interface

Use the wrapper after collection reaches32,421 exact requests. It does not submit predictions or modify the live collection. Choose a new output directory each time.

```bash
/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python \
  "/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/chemistry-audit/run_final_audit.py" \
  --root /Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500 \
  --queue /Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/admetlab-auto/data/molecules.csv \
  --map /Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/stage/admetlab-id-map.csv \
  --expected-rows 32421 \
  --out "/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/chemistry-audit/final-32421"
```

`--preflight-only` checks stable hashes and exact queue coverage without performing the full chemical audit. Exit2 means coverage/identity mismatch; the saved `coverage.json` enumerates missing and extra request IDs. It does not mean the uncollected molecules were chemically rejected. Exit3 means full coverage was reached but a mechanical output check requires review. Exit0 on the complete run means mechanical checks passed; scientific review remains necessary.

The wrapper freezes a stable manifest/raw/features snapshot, the queue and source ID map; verifies hashes and unique IDs, exact queue coverage, order and SMILES; and calls the existing `audit_chemistry.py` against that frozen copy. It retains all120 numeric features and **64 documented classification probability bounds**. The18 documented regression and38 untyped/computed/rule columns do not receive generic0..1 bounds. It checks finite values, raw-to-numeric conversion, alert atom indices, exact monoisotopic MW rounded2dp and formal charge. It saves source/request/service structure comparisons and stereo-aware duplicate groups. Standardization comparisons diagnose changes; they do not authorize replacing molecules or merging stereoisomers/tautomers.

Review `final-audit-status.json`, `summary.json`, `service-structure-differences.csv`, `chemical-duplicate-groups.json`, feature/alert error files, and the source-curation caveat. Zero exit code is not a claim of biologically correct predictions or validated original assay identity. The seven-entry source audit identified five upstream fragment/assay mismatches; see `full-pool-preaudit/carbon-free-source-audit/REPORT.md`. No source data are silently dropped.

If the service permanently rejects entries or provides partial results, complete coverage cannot be claimed by this wrapper. Keep those explicit outcomes and ask the parent workflow to adjudicate scope/missingness instead of inserting fake values. Use the lower-level `audit_chemistry.py` with a fresh `--out` for a labelled partial snapshot if that is scientifically useful; it does not enforce32,421 coverage itself.

Observed validation: live preflight at13,260 of32,421 correctly exited2 with only incomplete-coverage findings. A frozen2660-row regression smoke run is kept separately; it is not the final full-pool audit. The current full-pool queue SHA256 is `ae515913b1bedacd216e424305b57daa3dfce0cf8169352a4f41df36de477493`.
