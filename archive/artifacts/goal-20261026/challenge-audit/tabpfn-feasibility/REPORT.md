# TabPFN + ADMET feasibility addendum

**Recommendation: yes, retain one bounded TabPFN arm as an alternative to the expensive fusion route.** The absent package in the current working venv is a setup issue, not evidence of infeasibility. The required TabPFN weights already exist locally and were hash-verified without loading the model. No fit, inference, installation, rental, gated-weight download or license acceptance was performed in this audit.

## Reusable assets and exact previous recipe

- Jeremy source: `jeremycheminf/openadmet_scripts`, commit `d3a5549e0c98167435cbf8f5115c68a9a184ed7a`; scripts `04_run_tabpfn.py`, `03_embed_frozen_encoders.py`, and `src/cyp_submission/tabular_cv.py`.
- Our reciprocal adaptation: source `992b5bb`. `worker.py:tabfit` fits median imputation, standardization and PCA200 **inside each training fold**, then one `TabPFNRegressor(n_estimators=8, device="cuda", random_state=42)` per CYP. The original vendor script performed PCA beforeCV; do not restore that leakage-prone preprocessing.
- Measured historical runtime: Python3.11.13, TabPFN9.2.0, PyTorch2.8.0+cu128, NumPy2.2.6, sklearn1.7.2. The archived Linux venv is dependency/source evidence, not a portable Mac environment. Its package metadata requires Python≥3.10 and torch≥2.5; compatibility with another satisfying version still needs a bounded runtime check when execution is authorized.
- Cached TabPFN checkpoint: `/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/remote/assets/weights/tabpfn-v3.5-20260909.safetensors`, **876,027,932 bytes**, SHA256 `ece4d67eadfea42eb0e610df5189bea60cb7f31073d81e9c7a019b76eacf0be3`. HF revision `06bf2ba35c80a92a3b9abb436b99cf49e7a0365e`.
- The existing `night/tabular.py:_tfm` accepts a hash-pinned `model_asset`, verifies the file and passes its explicit `model_path` to TabPFN; this path was actually used by successful prior jobs. Reuse that pattern rather than invoking an unpinned automatic download.
- Jeremy ADME encoder is also cached: `/Users/adeliyaleleytner/.local/share/cyp-inhibition/reciprocal-comparison-20261023/full/vendor/checkpoints/chemprop_medium.pt`, SHA256 `b8137a0d202669baa9747f21eac4ef78b000afe68a3f100d25c849c41ad8a3d5`,7,711,460bytes. Its cached official-training embedding matrix is4905×600 float32 at `full/prepared/adme_pretrain.npy`, SHA256 `e0216aeaad3f8b9a34ea124b0eb90bd36ae671ae79b1d30268feccf5f8731378`. Verify the associated `prepared/challenge.csv` ID order before joining. No matching750-row blinded-test ADME matrix was established here; frozen extraction may still be needed.

The quoted **0.6569/0.6484** scores are own750 and **pooled Jeremy five-outer-fold OOF**, respectively—not reconstructed-briford529. The supervised ADME encoder's original47-task training membership remains unknown. This limits scientific independence claims even after current fold purges. The original self-supervised CheMeleon checkpoint is a different encoder.

## Access and licensing

Current HF metadata reports `gated=False`, and the exact876MB checkpoint is already present, so no new gated download is needed. The model card still contains historic gating-form text; that is distinct from the current API gate flag. [Model repository](https://huggingface.co/Prior-Labs/tabpfn_3_5).

TabPFN code is Apache2.0, but **v3.5 weights are under a separate noncommercial/nonproduction license**. Its definition expressly includes qualifying data-science competitions and research, with restrictions on commercial/production use and outputs. It is not an unrestricted Apache-licensed model. The license is saved locally for review; no new acceptance step was taken. Jeremy's repository metadata declares no license, so do not assume its bundled encoders/code are generally redistributable merely because they are public. [Official code/license distinction](https://github.com/PriorLabs/TabPFN#license), [pinned weight license](https://huggingface.co/Prior-Labs/tabpfn_3_5/blob/06bf2ba35c80a92a3b9abb436b99cf49e7a0365e/LICENSE).

## Measured cost anchor

The overnight PCA1024 self-supervised-CheMeleon + TabPFNv3.5 arm has **ten completed fold jobs** across own750/reconstructed-briford529. Each job fit/predicted all four targets with eight estimators. Total recorded worker time is **1,813.48seconds =0.504GPU-attached worker-hours**; individual jobs took129–244seconds. This includes preprocessing/startup/I/O, not a measured GPU-utilization integral. The historical hosts were4×RTX3090; each job used one CUDA device.

That is a cost proxy, not the measured runtime of ADMET120 or Jeremy-PCA200. A conservative bounded comparison can provision approximately0.5GPU-hour for one outer-cohort portfolio pass and reserve additional final-fit/setup time. A paired representation control plus augmented arm and finalOOF/refit should budget roughly1.5–2GPU-attached hours pending a representative timing check. Historical3090 pricing implied about$0.22–0.27/GPU-hour, but allocation tails/startup/storage increase billed cost and **a fresh quote is required**. Do not extrapolate the older expensive8×5090 rental's whole-run bill to this one component, and do not consume the full account balance. [Timing/asset receipt](feasibility.json).

## Bounded addition I would choose

For the smallest useful addition, use **TabPFNv3.5 on the same120 ADMET features as A1/A2**, fixed eight estimators and seed42, on the exact newly approved fold/tautomer exclusions. This isolates learner family, avoids another uncertain supervised molecular encoder, and needs no new encoder inference. Keep the120 features explicit; use only fit-side preprocessing and do not let blind/outer rows fit a PCA or scaler. Fit one endpoint at a time using observed experimental primary labels;32,421 acquired feature rows do not become32,421 labeled pIC50 examples.

If the parent instead chooses to exploit the previous strongest representation, substitute **one paired hypothesis**: ADME-PCA200 versus ADME-PCA200+ADMET120 (320features), with the same TabPFN checkpoint/OOF protocol. Keep ADMET columns outside the embedding PCA so they cannot disappear merely through the dimensionality bottleneck. Refit the matched control on current folds; do not reuse its historical0.657 score as the new control. Do not run both alternatives plus a broad TabPFN sweep by default.

One such family comparison merits prioritization over G2's60 outer/final GNN fits if the current≤$5 tranche can cover it after the corrected native reference. Preserve inner-only selection, all five metrics, per-CYP static-blend controls, teacher/encoder provenance and the reconstructed-holdout caveat. There is no evidence yet that TabPFN+ADMET will improve the final model; this is a justified candidate, not a promised winner.
