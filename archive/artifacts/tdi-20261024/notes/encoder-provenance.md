# Frozen encoder provenance audit — 2026-10-24

Read-only audit of existing public checkpoints and public repository metadata. No training or large data download. Scope: distinguish verifiable exclusions in our current fitting from unverified original pretraining corpus membership.

## Conclusion

Our outer-holdout exclusions can be verified for all labels fitted in this campaign. **The original pretraining-corpus membership of the two supplied Jeremy ADME checkpoints cannot be independently certified from the published kit.** We found no affirmative evidence that these checkpoints were trained on the official challenge's TDI labels, but absence of a corpus manifest means that we cannot establish that they were not. State this limitation when calling validation leak-safe: strict in our downstream fitting, unknown at inherited external encoder-pretraining stage.

The public README explicitly reports ChEMBL/TDC/Polaris plus a public Novartis-surrogate CYP panel. This is an author statement, not a data-membership audit. “Surrogate” must remain in the description; it does not establish access to proprietary Novartis measurements.

## Verified checkpoints inspected locally

Weights directory: `/Users/adeliyaleleytner/autoresearch-runs/cyp-tdi-20261024/stage/weights`.

| File | Bytes | SHA256 | Verified architecture |
|---|---:|---|---|
| chemprop_medium.pt | 7,711,460 | b8137a0d202669baa9747f21eac4ef78b000afe68a3f100d25c849c41ad8a3d5 | BondMessagePassing, hidden600, depth4, NormAggregation(norm100), RegressionFFN47tasks |
| chemprop_chemeleon.pt | 51,847,844 | b2b3ce2d5a40c46c4dbae1e553ce63d3c0e6a15abe800fde18b8b8814e2f7cc6 | BondMessagePassing, hidden2048, depth6, MeanAggregation, RegressionFFN47tasks |
| chemeleon_foundation.pt | 34,859,448 | c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651 | Encoder-only BondMessagePassing, hidden2048, depth6; our extraction uses MeanAggregation |

The two ADME files contain only top-level `hyper_parameters`, `state_dict`, `output_columns`. **output_columns is None in both.** There are no exported molecule IDs, SMILES, source row lists, source dataset hashes, explicit target names, training dates, training epochs or exclusion declarations. The47head count is identifiable from the actual predictor metadata, but the47 endpoint identities are not. A regression head does not prove that classification labels were never represented numerically during pretraining.

Both ADME encoders have batch_norm=False. The medium encoder uses norm pooling rather than mean pooling; our retained vendor fingerprint operation preserves this distinction. These are different pretrained models, not two seeds of the same architecture.

## Public source findings

Pinned public source tree:
https://github.com/jeremycheminf/openadmet_scripts/tree/d3a5549e0c98167435cbf8f5115c68a9a184ed7a/CYP_Challenge

Pinned README:
https://github.com/jeremycheminf/openadmet_scripts/blob/d3a5549e0c98167435cbf8f5115c68a9a184ed7a/CYP_Challenge/README.md

Relevant local text: `sources/jeremy-README.md`, lines64–76,112–115, and references lines154–188.

The README states:
- medium is an ADME/CYP pretrained D-MPNN;
- the CheMeleon-derived model was initialized from the foundation model and then trained on the same corpus;
- checkpoints come from a sibling `adme_pretrain` project;
- corpus sources are public ChEMBL/TDC/Polaris and a public Novartis-surrogate CYP panel described in an OpenADMET community talk;
- TDI kit freezes the medium encoder and trains a TabICL classifier on official TDI labels.

The pinned full repository tree was inspected (`sources/jeremy-tree.json`; tree SHA d3a5549e0c98167435cbf8f5115c68a9a184ed7a). It publishes model files, extraction/finetuning code and a CYP ChEMBL CSV, but **no adme_pretrain directory, corpus manifest or47-target dictionary**. A current read-only listing of the author's public repositories did not expose a separately named adme_pretrain repository. This establishes only that the needed audit artifacts were not found in the inspected public sources; the project could exist elsewhere or privately.

Read-only GitHub commit-history queries for both checkpoint paths return their addition at commit cb09f313353e, dated2026-09-02T18:51:28Z, with the challenge-kit addition. This is the public file-addition date, **not the actual model-training date**. It cannot prove training preceded release of the competition labels.

Pinned extraction code:
https://github.com/jeremycheminf/openadmet_scripts/blob/d3a5549e0c98167435cbf8f5115c68a9a184ed7a/CYP_Challenge/src/cyp_submission/chemprop_transfer.py

Our vendored file SHA256: 4daa3b30ffe8becd09e6533a331f7ac1d7f8984e7bed46de590698ecaf378c2c.

The frozen extraction function reads only supplied SMILES and checkpoint tensors, calls model.fingerprint under inference mode, and fits no parameters. Our two compatibility adaptations (explicit CPU checkpoint relocation; module-local DataLoader preserving drop_last=False under Chemprop2.2.1) do not add training labels. Their presence and hashes are recorded by embeddings.py.

## What is known about challenge-label exposure

- **Current pipeline:** the frozen embedding extractor consumes molecule structures, not official direct/TDI labels. Downstream fitting must use only the frozen development indices for the relevant outer cohort; source membership checks in data preparation cover the labels we control.
- **Prior unrelated full-data briford weights:** they did consume official challenge auxiliary labels. We correctly do not use those weights as an allegedly independent encoder in these outer-holdout comparisons.
- **Jeremy ADME inherited weights:** no explicit official-TDI training use found in published source/documentation, but insufficient provenance to certify exclusion. The same caveat applies to their official direct-inhibition auxiliary measurements and to duplicated molecules carrying external labels.
- **Generic CheMeleon:** a separate public foundation checkpoint, not the supplied ADME-further-trained checkpoint. Its use offers a comparison with a different provenance chain. This audit verified local structure/hash, not its entire original corpus membership.

## Reporting language

Recommended: “Official holdout molecules and their auxiliary labels were excluded from all fitting performed in our TDI campaign. Two comparison methods use public frozen ADME checkpoints supplied by Jeremy; the published kit does not expose their complete pretraining corpus, so upstream molecule/label overlap cannot be ruled out. A separate generic CheMeleon and structure-only baselines provide additional comparisons.”

Avoid: “all models are certified to have never seen any holdout label,” “the Novartis source contains proprietary measured labels,” or “47 targets exclude TDI” — none is established by available evidence.
