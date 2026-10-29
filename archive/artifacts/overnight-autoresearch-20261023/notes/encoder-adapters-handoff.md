# Optional encoder extraction handoff

Implemented 2026-10-24; root owns commits, bootstrap and ORX execution. No checkpoints downloaded and no scientific model fit/extraction run locally. Eight tiny fake-encoder tests pass; the existing twelve core feature/tabular tests pass. This is interface verification, not a real GPU compatibility result.

## Entrypoint

From committed source repo, inside root's ORX entrypoint:

```sh
python -m night.encoders --molecules /workspace/cyp-night/assets/all_molecules.csv --encoder molformer --asset-root /workspace/cyp-night/assets --asset-key molformer --expected-rows 5655 --audit-path /path/to/run/molformer-extraction.json
```

Repeat with `--encoder monroe --asset-key monroe` and `--encoder chemeleon_foundation --asset-key chemeleon_foundation`. Default CLI cohort guard is 5655 unique IDs. Only Molecule_Name and SMILES are read. `--config` accepts a JSON settings file; defaults failure_policy=raise, device=cuda, seed=42. Set CUDA_VISIBLE_DEVICES in the ORX entrypoint to restrict each extraction to the selected slot. `--feature-manifest` defaults to feature_manifest.json under asset-root. Shared publication uses an advisory file lock and atomic manifest replacement; an existing asset key is never overwritten. Use a new explicit key for a changed extraction. All matrices/IDs/audits have SHA-256 hashes and preserve exact row order. No implicit weight download.

Precomputed downstream request is `features=[{"family":"precomputed","asset_key":"molformer"}]` (corresponding keys for the other encoders). Preprocessing remains train-only in tabular.py. With explicit failure_policy=nan, failed rows retain NaNs and the downstream training-only imputer handles them; failure IDs/reasons are recorded. Default raise stops publication.

## Asset manifest

Place `encoder_manifest.json` in asset-root:

```json
{"encoders": {
  "molformer": {"model_dir":"weights/molformer", "revision":"361063d0ad524ef77cf39b08469f6be770dc550f", "files_sha256":{"config.json":"ACTUAL_SHA", "model.safetensors":"0795977fe7192c4acdaf052f0e8464af57bc4bb59211271c5e61aaba2637b9c6"}},
  "monroe": {"source_dir":"sources/Monroe", "revision":"de075eabe98e4adbbedbc86ca9e877f4bfd9b629", "files_sha256":{"monroe/__init__.py":"ACTUAL_SHA"}, "model_asset":{"path":"weights/monroe/weights.pt","sha256":"df996e8e98b12a3cda5fe5acbef3e1e9a4ea31946d3736461cd07e53a5bf205a"}, "config_asset":{"path":"weights/monroe/config.json","sha256":"ACTUAL_SHA"}},
  "chemeleon_foundation": {"model_asset":{"path":"weights/chemeleon_mp.pt","sha256":"c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651"}}
}}
```

The example files_sha256 mappings are deliberately incomplete: bootstrap must enumerate and hash **all** relevant files. Monroe source_dir: every .py/.json/.csv recursively, excluding .git; the JSON/CSV molecular metadata are part of the representation. HF model_dir: every .py/.json/.txt/.model/.safetensors/.bin. Unlisted relevant files and hash mismatches raise. Files must remain under their stated bundle directory. Revision and file hashes are recorded. Bootstrap must download the actual pinned snapshot; a revision string alone is not an integrity proof.

## Public assets and dependencies

- Monroe source [pinned commit](https://github.com/blazejba/Monroe/tree/de075eabe98e4adbbedbc86ca9e877f4bfd9b629). Actual Git LFS weight [download](https://media.githubusercontent.com/media/blazejba/Monroe/de075eabe98e4adbbedbc86ca9e877f4bfd9b629/checkpoint/weights.pt), 300,057,823 bytes, SHA above. The raw.githubusercontent.com weights URL is only a small LFS pointer. [Config](https://raw.githubusercontent.com/blazejba/Monroe/de075eabe98e4adbbedbc86ca9e877f4bfd9b629/checkpoint/config.json), 1192 bytes. Encoder width720. Upstream pyproject pins no package versions, requires Python>=3.10 and torch, torch-geometric, RDKit, numpy, pandas, datamol, scipy, scikit-learn, tqdm, wandb, matplotlib, pyarrow. Do not install `[eval]`: it adds TabPFN==8.3.0, TensorFlow and benchmark packages that extraction does not require. [PyG2.7.0](https://pypi.org/project/torch-geometric/2.7.0/) is a reproducible compatible candidate for Python3.11/Torch2.8/cu128. Source grit.py uses torch_geometric.utils.scatter/softmax, not a direct torch_scatter import; minimal PyG is appropriate initially. This is documented dependency compatibility, not a tested Monroe GPU runtime.
- MoLFormer [HF snapshot](https://huggingface.co/ibm-research/MoLFormer-XL-both-10pct/tree/361063d0ad524ef77cf39b08469f6be770dc550f). Safetensors187,248,784 bytes, SHA above. Model card tested transformers==5.12.1; v4 users need a separately pinned compat-v4 snapshot, not this implicit substitution. Local-only AutoTokenizer/AutoModel with verified remote code, deterministic_eval=True, canonical non-isomeric SMILES by default, pooler_output768, 202-position limit checked before model inference. No silent truncation. Token length audit includes special tokens.
- Original CheMeleon [Zenodo weight](https://zenodo.org/records/15460715/files/chemeleon_mp.pt), SHA above also verified in existing modeling.py. The adapter enforces this exact hash, strict-loads BondMessagePassing and aggregates atom states before any predictor. Mean aggregation default; sum/norm only explicit settings. No CYP fine-tuning or prediction head. Current local API inspected under chemprop2.2.1 + torch2.8.0; root may preserve its existing pinned Chemprop version if compatible, and audit records actual version. Uses weights_only=True. No neural training.

## Explicit limitations

Monroe upstream helper silently skips failed structures and load_ckpt uses strict=False; this adapter instead maps graphs by SMILES to original IDs, records failures, and strictly loads every encoder parameter (non-encoder training-head keys are listed as ignored). Upstream ETKDGv3 uses random coordinates without randomSeed, so regeneration is not guaranteed bit-identical; the hashed extracted matrix is the reproducible artifact. All-z-zero coordinate IDs are audited; this can indicate a planar molecule or a 2D fallback, so it is not automatically classified as a conformer failure. Explicit flat_policy=raise is available. Source graph generation can consume substantially more CPU time than encoder inference. We preserve its algorithm rather than introducing an unregistered geometry variant.

Uni-Mol is still deliberately unsupported online; already-staged ID-audited Uni-Mol matrices can use the precomputed loader. No real model files or giant new dependencies were installed on the Mac.
