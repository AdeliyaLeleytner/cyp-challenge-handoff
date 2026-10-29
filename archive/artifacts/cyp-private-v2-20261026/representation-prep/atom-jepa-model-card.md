---
license: cc-by-4.0
tags:
  - chemistry
  - materials-science
  - molecules
  - crystals
  - self-supervised-learning
  - jepa
  - equivariant
  - graph-neural-network
  - pytorch
---

# Atom-JEPA

Pretrained encoders from **Atom-JEPA: Joint-Embedding Predictive Architecture for 3D Atomistic Systems**.

[Paper](https://arxiv.org/abs/2610.08400) · [Code](https://github.com/khelverskovp/atom-jepa) · [PyPI](https://pypi.org/project/atom-jepa/)

Atom-JEPA is a self-supervised pretraining method for 3D atomistic systems. Each
structure is split into complementary context and target subgraphs by sampling a
k-hop neighborhood around an anchor atom. An equivariant graph neural network
encodes the context, and a predictor uses it to predict the representations of the
target at two scales: individual atoms and the mean-pooled substructure. The targets
are encoded from the full structure by an exponential-moving-average copy of the
encoder. This repository holds the pretrained **context encoders**, which can be
fine-tuned for property prediction or used as frozen feature extractors.

## Models

| folder | domain | pretraining data |
|---|---|---|
| [`molecules/`](molecules) | molecules | Uni-Mol molecular pretraining set, 19M molecules |
| [`crystals/`](crystals) | inorganic crystals | Alexandria PBE 3D, 1.7M crystals |

The two encoders share the same architecture:

| | |
|---|---|
| backbone | EquiformerV3, 8 transformer blocks |
| width | 256 channels, irreps up to L<sub>max</sub> = 2 (m<sub>max</sub> = 2) |
| graph | radius graph, 6 Å cutoff (periodic for crystals) |
| parameters | 39.0M |
| input | atomic numbers (Z < 128) and 3D Cartesian coordinates, plus the lattice for crystals |
| output | per-atom equivariant features; the structure embedding is the 256-dim mean of the per-atom invariant (l = 0) features |

Each folder contains:
- `model.safetensors`: the context-encoder weights;
- `config.json`: the architecture (`eqv3_cfg`).

## Usage

Install the [`atom-jepa`](https://pypi.org/project/atom-jepa/) package (after
[PyTorch](https://pytorch.org/get-started/locally/)). It downloads the weights from this
repository on first use:

```bash
pip install "atom-jepa[rdkit]"    # [rdkit] adds SMILES input, [all] also pymatgen input
                                  # [cu12] / [cu13] add the cuEquivariance GPU kernels
```

```python
from atom_jepa import AtomJEPA

model = AtomJEPA.from_pretrained("molecules")             # or "crystals"
model.embed(["CCO", "c1ccncc1"])                          # [2, 256]
model.embed("CCO", layers="all", degrees="all")           # [8, 9, 256]  all blocks, irreps l=0..2
model.embed("CCO", degrees="all", invariant=True)         # [3, 256]     rotation-invariant l=0..2
```

On a CUDA GPU the encoder runs in bf16 with the cuEquivariance kernels when installed
(`precision="fp32"` for exact fp32 features, `compile=True` for larger jobs); otherwise in
plain fp32 PyTorch. `embed` also takes `ase.Atoms`, pymatgen structures and
`(atomic_numbers, positions[, cell])`; `per_atom=True` returns per-atom features.
`AtomJEPA` is a `torch.nn.Module`, so the encoder can be fine-tuned with your own head and
training loop. See the
[package documentation](https://github.com/khelverskovp/atom-jepa#python-package) for details.

The benchmark fine-tuning scripts from the paper are in the
[GitHub repository](https://github.com/khelverskovp/atom-jepa) and take the same names:

```bash
python -m finetuning.qm9.finetune finetune.ckpt_path=molecules finetune.target=homo
python -m finetuning.matbench.finetune matbench.ckpt_path=crystals
```

To load the weights without the package, read `model.safetensors` with
`safetensors.torch.load_file`; the architecture is given by `config.json["eqv3_cfg"]`
(`atom_jepa.models.jepa_equiformer.EquiformerV3Config`).

## Intended use and limitations

- The encoders need 3D structures. For molecules given as SMILES, generate a
  conformer first (the paper uses RDKit ETKDGv3 + MMFF94). Embeddings depend on the
  conformer.
- These are pretrained representations, not property predictors. Downstream use
  needs a readout head, fine-tuning or a probe.

## Citation

```bibtex
@misc{petersen2026atomjepajointembeddingpredictivearchitecture,
      title={Atom-JEPA: Joint-Embedding Predictive Architecture for 3D Atomistic Systems},
      author={Kasper Helverskov Petersen and Rasmus Hannibal Tirsgaard and François R J Cornet and Mikkel Jordahn and Mikkel N. Schmidt},
      year={2026},
      eprint={2610.08400},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2610.08400},
}
```
