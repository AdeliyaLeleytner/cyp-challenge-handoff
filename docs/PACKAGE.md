# Package Contents

This repository is a portable research snapshot. Its handoff documentation is based on preserved readouts, prediction files, and receipts. Packaging did not retrain the models.

Code, small tables, reports, and manifests are stored in Git. Selected models, arrays, large CSVs, and binary artifacts are stored in the private release `handoff-2026-10-29`. `manifest/files.jsonl` defines the included files and their storage locations; `manifest/releases.json` records pack and object hashes. Identical binary objects are stored once, with their retained paths listed in the manifest.

Directory symlinks into `autoresearch-runs` were resolved into files. Historical absolute paths remain in source evidence. `tools/prepare_runtime.py` prepares a separate copy for a new machine, using `manifest/path-map.json` to map known paths.

The owner selected a working package with code, data, results, and selected model weights. Model inventories are recorded in `manifest/retained-models.json` and `manifest/omitted-models.json`; the original model files were not deleted from the owner's machine. Negative experimental results remain part of the research record. File-level packaging decisions are recorded in `manifest/exclusions.json`.

Reinstallable Python/Node environments, compiled caches, browser profiles and cookies, credentials, SSH configuration, incomplete temporary outputs, and opaque transport archives are outside the working package. It is not a disk image. Third-party source files and checkpoints retain their original licenses, including preserved LICENSE/NOTICE files. No blanket open-source license is assigned to the archive.

Repository creation and historical authorization statements do not authorize new compute spending, bulk service requests, leaderboard dispatch, or public disclosure. The recipient should use their own environment and agree further actions with the owner.
