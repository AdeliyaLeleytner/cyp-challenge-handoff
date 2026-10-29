# Uni-Mol2 84M frozen3D control: prepared adapter and bootstrap

Prepared `night/unimol_features.py`; no real embeddings, large downloads or inference were performed locally. Root stages assets and launches the CLI through ORX in a separate environment. Existing training environments are not modified.

## Verified primary sources and interpretation

- Toolkit repository **is** [deepmodeling/unimol_tools](https://github.com/deepmodeling/unimol_tools/commit/670afbd3144b58caef1d76cc618ddfeaecab8424); commit `670afbd3144b58caef1d76cc618ddfeaecab8424` exists and is dated2026-07-16. Its setup version is0.1.6. It is not the old Uni-Mol monorepo subdirectory.
- [HF pinned checkpoint](https://huggingface.co/dptech/Uni-Mol2/blob/bf37d253c0f5ac61f468137eb00059978a104ff0/modelzoo/84M/checkpoint.pt): model revision `bf37d253c0f5ac61f468137eb00059978a104ff0`, file `modelzoo/84M/checkpoint.pt`, **336632021bytes**, SHA256 **5b9241630f1cf0b173fb06d1e76096e5daf5f91c3e51b066ba69524dafe60e35**. Independently confirmed using the HF model-revision API with `blobs=true`; no checkpoint download was needed.
- The [official model zoo](https://github.com/deepmodeling/Uni-Mol/blob/90f52c41299a1a582da0f9765e9f87aa21faa16a/unimol2/README.md) links this84M checkpoint and specifies12layers,768-dimensional embeddings and48attention heads.
- The [original paper, §3](https://arxiv.org/html/2406.14969v1#S3) describes masked-token and coordinate-denoising self-supervision on molecular structures. This supports using the published model-zoo checkpoint as a generic, frozen structural control rather than a CYP-adapted encoder. Its upstream corpus combines19M Uni-Mol molecules and ZINC20; the19M subset includes ZINC15,ChEMBL and a commercial-database source. Therefore call it a **public self-supervised checkpoint without CYP-label adaptation**, not a demonstrably all-public upstream pretraining corpus. Potential structural overlap with challenge molecules is not audited. Root should preserve this distinction in disclosures.
- The [pinned HF README](https://huggingface.co/dptech/Uni-Mol2/blob/bf37d253c0f5ac61f468137eb00059978a104ff0/README.md) is only24bytes of MIT-license metadata, so the model card alone cannot establish training provenance. The model-zoo linkage, original paper, pinned bytes and checkpoint-head checks jointly support the interpretation.

## Exact source API and adapters

The adapter loads only these unmodified pinned source files, verifying their working bytes against `git show COMMIT:path` before use:

- `unimol_tools/models/unimolv2.py`: `UniMolV2Model(output_dim=1, model_size='84m', load_pretrained=False)`, `batch_collate_fn(samples)`, and `model(**batch, return_repr=True, return_atomic_reprs=False)` produce CLS `x[:,0,:]`, dimension768.
- `models/transformersv2.py`, `config/model_config.py`, `utils/util.py`, `data/dictionary.py`, `data/conformer.py` supply the architecture, graph encodings and padding.

An isolated namespace avoids the package's training initializers and their optional dependencies. The original core modules remain unchanged. Standard Python logging replaces the package logger; download hooks raise an offline-only error. No Uni-Core, custom CUDA extension, Transformers, Hydra, OmegaConf, LMDB or Hugging Face client is required for this extraction route.

The upstream conformer path can fall back to2D/zeros and `mol2unimolv2` randomly crops when atoms exceed `max_atoms`. This adapter instead generates explicit ETKDGv3 conformers, retries once with random coordinates, uses per-ID deterministic seeds, applies a30-second embedding timeout and bounded optimization iterations, and never calls Compute2DCoords. Valid embedded coordinates may be retained if optimization reaches its iteration limit; that status is recorded rather than called convergence. Single-atom and planar molecules are not rejected merely for low coordinate rank.

Hydrogens are omitted because Uni-Mol2 uses non-H atoms. All heavy atoms and disconnected fragments remain. The default256-heavy-atom ceiling fails with a molecule-level audit; it does not crop. For successful molecules, graph conversion receives `max_atoms=actual_atom_count`, and input/output atom counts are asserted. Every5655bank row must succeed before the bank can be published. There is no missing-row, zero-vector, NaN-imputation or alternate-model fallback.

The model initializes with pretrained loading disabled, then the adapter explicitly reads only the SHA-verified public checkpoint using `torch.load(..., weights_only=False)`. This avoids Torch2.8's changed default and allows audit of load coverage. All backbone keys must match. Only the unused newly-created classification output head may be missing; only the pretraining `lm_head` may be extra. A checkpoint containing downstream classification heads or identifying a finetuning task fails. No state keys are silently discarded to make a mismatched model run.

## Isolated bootstrap, performed by root on remote compute only

Use a fresh Python3.11 environment, for example `/workspace/venvs/unimol84`. These are proposed exact bootstrap versions, not a claim that a real GPU integration has already run:

```sh
python3.11 -m venv /workspace/venvs/unimol84
/workspace/venvs/unimol84/bin/pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
/workspace/venvs/unimol84/bin/pip install numpy==2.2.6 pandas==2.2.3 scipy==1.15.3 rdkit==2026.9.1 numba==0.61.2 addict==2.4.0 tqdm==4.67.1
```

RDKit2026.9.1's `ETKDGv3().timeout` API was checked locally without generating a conformer. The source toolkit permits NumPy>=2,<2.3; the suggested NumPy/Numba versions respect that interval. The adapter requires Torch2.8.0 with CUDA12.8 and CUDA availability; it will not silently run on CPU. It records actual package versions. Root must retain `pip freeze` and the ORX environment evidence after setup.

Clone or stage the exact toolkit git checkout separately (do not pip-install its broad training dependencies). Stage the checkpoint at a local path. The only approved download URL is:

`https://huggingface.co/dptech/Uni-Mol2/resolve/bf37d253c0f5ac61f468137eb00059978a104ff0/modelzoo/84M/checkpoint.pt`

Verify the byte count and SHA above after downloading. Source git checkout must report exactly `670afbd3144b58caef1d76cc618ddfeaecab8424`; modified critical source files fail validation. The extractor performs no downloads.

## ORX command and output contract

```sh
/workspace/venvs/unimol84/bin/python -u -m night.unimol_features \
  --molecules /workspace/cyp-night/all_molecules.csv \
  --toolkit-root /workspace/cyp-night/sources/unimol_tools \
  --checkpoint /workspace/cyp-night/weights/unimol2_84m/checkpoint.pt \
  --asset-root /workspace/cyp-night \
  --asset-key unimol2_84m_foundation \
  --audit-path /workspace/cyp-night/audits/unimol2_84m.json
```

`--molecules` must have5655unique Molecule_Name rows and SMILES. Only these two columns are read; activity columns are ignored. Optional `--config` contains explicit batch/conformer settings. Defaults are batch8, four conformer threads, seed42, max256heavy atoms, one successful conformer per molecule and float32 inference. Progress events distinguish CPU conformer preparation from GPU embedding extraction.

Publication calls existing `encoders.publish_features` (contract inspected at5021ce3). It writes an ID-aligned `(5655,768)` float32 matrix, ids.csv, full audit and checksums into a content-addressed directory, then updates feature_manifest.json under the shared lock. Reusing an existing feature asset key is rejected. The bank is consumed as `{"family":"precomputed","asset_key":"unimol2_84m_foundation"}`. The audit records conformer attempts/failures, fragment and atom counts, optimization status, geometry hashes, source hashes, model hash, checkpoint key coverage, package versions and the upstream-corpus limitation.

No model quality claim follows from preparing this extractor. The remaining integration check is an ORX run against the actual pinned checkpoint and environment; a source/state mismatch must be investigated rather than bypassed.
