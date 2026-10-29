# Host2 recovery certificate

Snapshot: 2026-10-24T00:08:58.803117+00:00 to 2026-10-24T00:09:01.039198+00:00.

All 1,204 scoped files (484,696,125 bytes) match local copies by SHA256. Zero missing files, size/hash mismatches, unstable files, symlinks or remote file-list changes.

| Scope | Files | Bytes |
|---|---:|---:|
| assets | 11 | 62691661 |
| results | 919 | 378634004 |
| orx_runs | 268 | 21878331 |
| orx_source | 3 | 21483520 |
| root_files | 3 | 8609 |

The result audit covers 4 campaign directories and 60 neural checkpoints, including final seed142 and the earlier campaign runs. The ORX recovery includes3 original source TAR snapshots and3 run directories with source repos, launch scripts, logs and exit codes, under campaign/remote2-orx. Assets/results and environment lockfiles are under campaign/remote2.

No external HuggingFace/model cache or other unique model weights were discovered. Known non-campaign cache is matplotlib28KB and an empty motd marker. Provider bootstrap onstart.sh and ports.log are outside model/data scope.

This is a byte-preservation audit, not a model/environment restore test. Python environment binaries/system packages were excluded; the requirements lockfile is recovered. No instance stop/destruction was performed; root owns cleanup.

Detailed hashes: remote-manifest.json and local-*-hashes.json. Machine-readable result: recovery-certificate.json.
