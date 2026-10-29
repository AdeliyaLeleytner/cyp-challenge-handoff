# Frozen ADME600 blind bank with full reference reproduction

Inference only, on the existing instance57759747 and unchanged1.10USD phase cap/deadline05:31:54UTC. Preserve the answered TabPFN runtime in its original venv; create a separate encoder venv from the same pinned Torch2.8/cu128 image and install the historical Chemprop2.2.1/Lightning2.5.5/RDKit2026.9.1/NumPy2.2.6 stack.

Reproduce all4905 reference fingerprints before any blind inference. Use exact original official SMILES/order, frozen checkpointb8137a, eval mode, batch256, shuffleFalse/drop_lastFalse, dataset cache, collate_batch, model.fingerprint under torch.inference_mode. No real target values enter the encoder. Original producer and direct local imports have no explicit precision override; record and check normal FP32/highest matmul precision, CUDA TF32off, no autocast. Do not run unrelated legacy downloads or model training.

The parent fixed atol=1e-5 and rtol=1e-5 before this run. Every one of4905×600 values must pass against the cached matrixe0216a. On failure save diagnostics and stop: no blind bank, no tolerance increase, no approximate replacement. On success generate750×600 finite float32 embeddings and exact original-ID/SMILES/request-ID rows; check the encoder state did not change. Save current/runtime/protocol hashes, full reproduced matrix and canary statistics. The scoped receipt becomes consumable after verified recovery annotates its recorded ORX commit; this annotation is linked to the unchanged raw remote receipt hash.

This produces a frozen feature asset, not a model selection, final refit or submission. Full32,421-outcome auditing and final policy gates remain separate.
