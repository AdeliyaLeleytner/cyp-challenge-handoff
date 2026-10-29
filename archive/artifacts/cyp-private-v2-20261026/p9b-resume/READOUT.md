# Complete 5,655-molecule Atom-JEPA bank

All 4,905 official training molecules and 750 blinded molecules now have finite, 256-dimensional frozen features in the exact official order, with original SMILES retained. The final bank is `results/embeddings.npy`, SHA256 `3ce3d1b947f09849dc44548232c54ba9be417eb6fa3c3f8dc2bb0c599d2f2c69`.

The representation is Atom-JEPA 0.3.0 block 8 **after** final normalization, degree 0, averaged over atoms. It uses CPU fp32, the pinned 156 MB weights, ETKDGv3 seed 42, explicit hydrogens, and MMFF94 with at most 500 iterations. No normalization or fragment removal was applied. No activity labels entered the encoder.

The original run `f870d574-9ed7-4b77-b0c6-e42ec35509dd` (source `8ab23c4`) completed all 5,655 attempts in 5,235 seconds, within its 90-minute limit. It yielded 5,654 vectors and one explicit legacy-CIP validation failure, OCNT-2315767. Its artifacts and failure ledger remain unchanged.

Independent chemistry review found no stereochemical inversion: specified atom orientations and the graph remained unchanged, and modern CIP labels were consistently R/R. However, the legacy label of atom 13 changed from S to R after MMFF. See `../p9b/independent-stereo-review/INDEPENDENT_REVIEW.json`. The repaired validator clears stale CIP properties and computes modern labels consistently on the original reference graph and a copy containing the saved coordinates. It also checks atom-neighbor orientation, bond stereochemistry, and enhanced stereo groups. Preflight tests reject deliberately inverted coordinates and changed atom identity.

The approved repair run `57881623-7ebf-4816-b9c5-89e0805c0a9c` (node `06b2e55c`, source `0b7a2d3`) finished in 18.43 seconds. It revalidated all 5,654 saved coordinate records **before** reusing their vectors, kept those vectors bit-for-bit unchanged, and computed only the missing embedding.

The failed row had no saved full-precision coordinates because its check failed before writing them. It was regenerated with the identical fixed protocol and seed. Two deterministic repetitions produced identical float32 coordinates and the original MMFF energy. Rounded diagnostic SDF coordinates were **not** used. This provenance is explicit; we do not claim that an unpersisted original coordinate file existed.

The final independent assembly audit verified all 5,655 coordinate rows, 1,116 specified atom-stereochemistry checks, 28 explicit bond-stereochemistry checks, and 211 rows with enhanced stereo groups, with no flags. Exact IDs, SMILES, order, complete unique outcomes, and bitwise reuse of old vectors all passed. The 32 original smoke-test sentinels still match exactly. See `COORDINATE_AUDIT.json`, `results/COMPLETE.json`, `results/REUSE_AUDIT.json`, and `VALIDATOR_PREFLIGHT.json`.

These are generated single conformers, not experimental bound poses. MMFF nonconvergence is retained and flagged under the declared 500-iteration protocol; no alternative conformer or seed search was used. Compound-level overlap with the encoder's pretraining data is unknown, so downstream fold purging does not prove pretraining independence. The completed bank enables a controlled readout comparison; it does not establish predictive improvement or top-10 potential.

No paid compute, GPU, public upload, or submission was used. The separate paired TabICL profile and full comparison are tracked under `../p9-tabicl/`. They use primary labels only and fit PCA96 and scalers on actual training rows.
