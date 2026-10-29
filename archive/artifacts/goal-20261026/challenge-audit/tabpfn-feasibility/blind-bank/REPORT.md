# Verified frozen ADME600 blind feature bank

The750×600 float32 bank is complete and finite, with exact official test ID/SMILES ordering and canonical request IDs. No labels entered the encoder, no parameters or buffers changed, and no model was fitted.

ORX experimentd06c3395-0e1e-41d6-8f27-8b041e3ec9bb, runf9a8d969-0728-4760-b212-377f7f5480be, immutable commitc2cad8087b19282387fb9e188f24d402227fe706. Separate encoder venv: Python3.11.13, Torch2.8.0+cu128, Chemprop2.2.1, Lightning2.5.5, RDKit2026.9.1 and NumPy2.2.6. Original TabPFN venv remained unchanged. Inference body7.64s; ORX wall3m01s including setup.

Before blind inference, all4905×600 cached training values were reproduced using the original frozen checkpoint, exact SMILES/order, batch256, `shuffle=False`, `drop_last=False`, cached molecular graphs, `collate_batch`, `eval()` and `torch.inference_mode()` with `model.fingerprint`. The parent prescribed atol=rtol=1e-5 before execution. **Zero values failed.** Maximum absolute difference was5.960464477539063e-08; maximum error divided by the allowed pointwise tolerance was0.0051944259. Original producer/direct imports had no explicit global precision override; actual runtime was FP32/highest matmul precision, CUDA TF32off, no autocast. The full reproduced4905 bank is retained as evidence; it does not replace the original training cache.

`blind-bank-manifest.json` binds the matrix, row map and final receipt:

- MatrixSHA256: `43b136e8a368c91b625180b13cd2be1ed6f2b4686646a6ed757c277d3e016adc`
- RowsSHA256: `e7db7cd75456f7edf19e898fee3f7e74d470230a6b440962492d533d5179b5df`
- ReceiptSHA256: `e2ad873a2a09cd1100a0998a2c30a4905e9e1b7c2c03a894c0324fe708b24581`

All10 remote output/runtime files and the remote ORX log were recovered and hash-verified. Local checks repeated full canary comparison, finite shape, exact original ordering, request identity and required runtime equality. The final receipt annotates the verified recorded ORX commit/run ID and links the unchanged raw remote receipt hash; scientific values were not changed.

The receipt approves only frozen feature identity. Encoder pretraining membership remains unknown. Full32,421 outcome auditing, final model selection/refitting and submission gates remain separate. No checkpoint was redistributed. Shared instance57759747 was destroyed and absence verified2026-10-26 04:49:28UTC; matched posted charges across ADMET120 evaluation, H5 and this bank total$0.274, below the1.10USD phase cap.
