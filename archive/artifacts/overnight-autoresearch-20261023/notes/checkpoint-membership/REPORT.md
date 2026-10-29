# Frozen encoder membership audit — 2026-10-24

The exact Jeremy encoders have verified weight provenance but **unresolved training-label membership**. Their public reproduction kit does not expose the sibling `adme_pretrain` training membership, and the checkpoints contain no molecule IDs or named output columns. Absence of those records is not evidence of clean holdouts.

## Exact artifacts used previously

Pinned repository: `jeremycheminf/openadmet_scripts`, commit `d3a5549e0c98167435cbf8f5115c68a9a184ed7a`.

| Feature cache | Checkpoint | SHA256 | Verified Git blob SHA1 |
|---|---|---|---|
| `prepared/adme_pretrain.npy`, 4905×600 | `chemprop_medium.pt` | `b8137a0d202669baa9747f21eac4ef78b000afe68a3f100d25c849c41ad8a3d5` | `94989630583632331f545379813c639de612abc3` |
| `prepared/chemeleon.npy`, 4905×2048 | `chemprop_chemeleon.pt` | `b2b3ce2d5a40c46c4dbae1e553ce63d3c0e6a15abe800fde18b8b8814e2f7cc6` | `385d0ebf503efc0f294a5882b7096d649541ab7c` |

Both local checkpoint hashes match `full/outputs/preparation.json`; both Git blob hashes match the pinned source-manifest and public repository tree. `prepare_remote.py:120–129` maps these exact filenames to the cache tags and performs frozen forward inference. This `chemeleon.npy` is an **ADME-adapted** 47-task encoder, not merely the original descriptor-foundation `chemeleon_mp.pt`. Safe pickle-opcode inspection, without unpickling, reports 47 tasks and `output_columns=None` in both checkpoints; the medium encoder has hidden size600/depth4 and adapted CheMeleon2048/depth6.

The pinned reproduction README lines113–115 describes a sibling training project using public ChEMBL/TDC/Polaris and a public Novartis-surrogate panel. Its script03 lines4–9 makes the same claim. The pinned public repository tree contains no `adme_pretrain` folder or X_train/y_train files. These are source-author descriptions, not a row-level membership manifest.

## Auditable public training tables — distinct scope

Public OpenADMET models:

- [CYP v1](https://huggingface.co/openadmet/cyp1a2-cyp2d6-cyp3a4-cyp2c9-chemeleon-v1/tree/ef24cf941ae21c7d7a64df378a846bd2066eceda), model SHA256 `81d15cc43a3608f1aab465b1e690d86fd41c420615094cca1439c2e52f3b4e7b`.
- [Earlier baseline](https://huggingface.co/openadmet/cyp1a2-cyp2d6-cyp3a4-cyp3c9-chemeleon-baseline/tree/12265ee807889b4a3765b308c69d00022b99c176), model SHA256 `5260ba497cfd3dbbd15ce3300580c45d33d71f427c499bda4c3bb5029df0fd55`.

The X_train/y_train CSVs were downloaded at these immutable revisions and their Git blob hashes checked. Each exposes 8068 rows/7800 normalized parents and four CYP labels. Their README and recipe declare no heldout split, train_size1.0. Therefore overlapping labeled rows are documented adaptation members **of those official OpenADMET models**.

| Audited labeled table | Official TRAIN rows (unique parents) | Our750 holdout rows | Briford529 holdout rows | Actual blinded TEST rows |
|---|---:|---:|---:|---:|
| Official OpenADMET v1 X_train/y_train | 67 (64) | 10 | 5 | 0 |
| Official OpenADMET earlier baseline X_train/y_train | 67 (64) | 10 | 5 | 0 |
| Jeremy disclosed `cyp_chembl.csv`, any of12 IC50/Ki tasks | 67 (65) | 13 | 6 | 0 |

Matching means RDKit FragmentParent → uncharge → remove stereochemistry → canonical SMILES, without tautomer canonicalization. Counts require at least one finite source label, not merely a structure. Per-endpoint counts and matching official molecule IDs are preserved in `membership.json` and `*-matched-official-rows.csv`. Actual TEST denotes the staged official 750-molecule blinded challenge file, not either local holdout.

The published Jeremy ChEMBL table is linked by README discussion to the pretraining project and has confirmed overlapping public CYP labels. However, its membership cannot establish which rows were actually consumed by the exact 47-task checkpoint training procedure. We have not found a checksum-linked training manifest or splits for those weights. Labels are external assays, not automatically identical challenge measurements.

Neither exact Jeremy weight hash equals either official CYP model hash, nor any of the15 weights listed in [OpenADMET foundation weights](https://huggingface.co/openadmet/chemprop-foundation-pretraining-weights/tree/0f8201d06c4656c3f97bc244ce2dc18ac2881be9). Hash inequality does not prove that encoder tensors share no ancestry; it means we cannot transfer the auditable membership of a similar repository to the exact Jeremy files.

## Consequence for evaluation

For exact Jeremy encoders: official-TRAIN exposure is plausible from the disclosed source corpus but unproven at checkpoint membership level; actual-TEST labeled exposure is unknown, with zero matches in the two audited public CYP tables. Report them as membership-unknown, never as demonstrably clean. External-table parent exclusion in later fitting cannot erase exposure during prior encoder adaptation. For the distinct official OpenADMET CYP models, labeled exposure to10/5 local holdout rows is verified and must be disclosed if those models are evaluated on those holdouts.

No fitting, Git changes, checkpoint loading/execution, or full model downloads were performed. All raw public metadata, source file hashes, reproducible audit script and per-molecule results are in this directory.
