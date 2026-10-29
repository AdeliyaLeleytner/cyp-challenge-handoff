# Host1 recovery certificate

Snapshot: 2026-10-23T23:46:29.332867+00:00 to 2026-10-23T23:46:43.035601+00:00.

All 8,623 scoped files (13,365,054,026 bytes) match their local copies by SHA256. Zero missing files, size/hash mismatches, unstable files, symlinks or remote file-list changes.

| Scope | Files | Bytes |
|---|---:|---:|
| assets | 810 | 3112470048 |
| results | 5584 | 9892322449 |
| orx_runs | 2194 | 181251595 |
| orx_source | 25 | 178974720 |
| root_files | 10 | 35214 |

The recovered ORX scope includes25 original source TAR snapshots and25 run directories with source repos, launch scripts, stdout logs and exit-code files. These are under campaign/remote-orx; assets/results and environment lockfiles are under campaign/remote. All completed and incomplete campaign result directories are covered, including abandoned branches, not only the promoted candidate.

The only discovered external HuggingFace dynamic model-code cache contains MolFormer Python files whose SHA256 exactly matches already-recovered assets/weights/molformer sources. Remaining cache files are regenerable bytecode, empty package markers and matplotlib cache. No unique external model weights were found in the inspected /workspace, /tmp and /root/.cache locations. Provider bootstrap /workspace/onstart.sh and ports.log were inventoried but are not research weights/data.

This is a point-in-time byte-preservation audit, not an environment/model restore test. Python environment binaries were excluded; requirements lockfiles were recovered. No instance stop or destruction was performed. Root owns cleanup.

Detailed file hashes: remote-manifest.json and local-*-hashes.json. Machine-readable certificate: recovery-certificate.json.
