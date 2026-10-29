# Model Report: OpenADMET CYP Inhibition Challenge (Regression Track)

Participant: KNIMEST · Written: 2026-10-14

## 1. Summary

I predict direct-inhibition pIC50 for four CYPs (1A2, 2C9, 2D6, 3A4). The main metric is MA-ST-RAE: the average over the four CYPs, where lower is better and always predicting the mean scores 1.0.

- **Final submission (A):** a two-stage TabICL model. Stage 1 predicts primary-screen log2FC; stage 2 uses those predictions to predict pIC50. In A, the log2FC values for the training rows are **in-sample** predictions. Blind MA-ST-RAE: **0.5977**.
- **Main model (T):** the same model, but the log2FC values for the training rows are **out-of-fold** predictions. I chose T in advance, based on my local validation. Blind MA-ST-RAE: **0.8111**.
- **How A was chosen:** I built A as a **diagnostic control**, not as my planned method. I picked it as the final submission **after seeing the blind results**. On my local validation, T was better than A.

## 2. Data

- I used only the training data provided by the challenge: the dose-response pIC50 values and the primary single-concentration screen (log2FC) for the same compounds.
- I used **no external data** (such as ChEMBL or PubChem) and **no in-house data**.
- No external training data was used beyond the released pretrained models (CheMeleon and TabICL).
- The primary-screen log2FC was used as **auxiliary information**. The test compounds have no screen data, so I predict log2FC from structure and use the predictions as features.
- For structure, I used embeddings from the pretrained CheMeleon model, unchanged (no fine-tuning).

## 3. Model

```
  Structure ──> CheMeleon embedding ──> PCA (256 dims)
                                           │
                     ┌─────────────────────┤
                     │                     │
     Stage 1: TabICL predicts              │
     log2FC for 4 enzymes                  │
                     │                     │
                     └──────────┬──────────┘
                                │  256 PCA features + 4 predicted log2FC
     Stage 2: TabICL predicts pIC50 (one model per CYP)
```

- **Stage 1:** I reduce the CheMeleon embedding to 256 dimensions with PCA. TabICL then predicts the screen log2FC for each of the four enzymes. It is trained on the training compounds that have screen data.
- **Stage 2:** I add the four predicted log2FC values to the 256 PCA features. TabICL then predicts pIC50, with one model per CYP, trained on that CYP's labeled compounds.
- **A vs T (the only difference):** for the training rows of stage 2, T uses out-of-fold predictions (5 folds split by scaffold), so each compound gets a prediction from a model that never saw it. A uses predictions from one stage-1 model trained on all compounds with screen data, including the compound itself. For the test compounds, and for training compounds without screen data, A and T use the same predictions, from the stage-1 model trained on all data.
- I made no submission-time adjustments, such as shifting predictions, to A or T.

## 4. Validation

- I held out 20% of the training compounds, split by scaffold, and repeated this with four different splits.
- I scored with the official ST-RAE function. I also used a weighted version, which gives more weight to training compounds that look like the test set. I used it only to compare models with each other.
- Two key results:
  - Adding predicted log2FC (T) beat the same TabICL model without it on all four splits (weighted score). On the blind set, the gain was about the same size as the weighted local estimate on my first split (−0.089 blind vs −0.092 local).
  - On my local validation, A (in-sample) was **worse** than T (out-of-fold) on all four splits. On the blind set, the order was reversed (see Limitations).
- I ran further control experiments and diagnostics. Details will be published after the challenge closes.

## 5. Results

Blind leaderboard values. Each is a single submission.

| Model | MA-ST-RAE | MA-MAE | MA-R² | MA-Spearman | MA-Kendall |
|---|---|---|---|---|---|
| v4: TabICL on PCA256, no log2FC | 0.8999 | 1.0111 | 0.0405 | 0.5965 | 0.43 |
| T: main model (out-of-fold log2FC) | 0.8111 | 0.9557 | 0.1409 | 0.6545 | 0.4812 |
| **A: final submission (in-sample log2FC)** | **0.5977** | **0.7944** | **0.4170** | **0.6698** | **0.4956** |

- My other submissions were diagnostic controls and post-hoc diagnostics, listed in `results/submissions.csv`. A "diagnostic control" was planned before I saw its result. A "post-hoc diagnostic" was designed after seeing earlier blind results. Details will be published after the challenge closes.
- The v4 MA-Kendall was recorded to two decimal places only.
- The final submission accompanying this report is model A.

## 6. Limitations

- **A was chosen after seeing the blind results.** It is a post-hoc choice, not a method chosen in advance. Its blind score should not be read as an unbiased estimate of performance.
- **Each blind value is a single point estimate.** There are no error bars. Whether the leaderboard reports a bootstrap mean or a point estimate is unconfirmed.
- **The leaderboard shown during the challenge is not the final evaluation.** The final leaderboard is released after the challenge closes (from 2026-11-04). Whether it uses the same test compounds and the same scoring as the values shown now is unconfirmed, so the final ranking may differ.
- **Local validation and the blind set disagreed.** Locally, out-of-fold (T) beat in-sample (A) on all four splits; on the blind set, A was better. So my local validation did not predict which version would do better on the blind set.

## 7. Acknowledgements and references

This work was inspired by N283T's publicly shared model report for the OpenADMET PXR Blind Challenge ([report](https://n283t.github.io/openadmet-pxr-model-report/ja/), [repository](https://github.com/N283T/openadmet-pxr-model-report)), in particular by the idea of using predicted primary-screen log2FC as auxiliary features with a tabular foundation model. I also thank OpenADMET for organizing the challenge and for the article "Are tabular foundation models all you need?" ([link](https://openadmet.ghost.io/are-tabular-foundation-models-all-you-need/)), which describes a reproducible version of this approach.

Code and analyses were developed with the assistance of Claude Code (Anthropic); all decisions and the final submission are my own.

**Related write-up.** A personal account (in Japanese) of how this work started: [note article](https://note.com/knimesupportteam/n/nef47ec12f777?hl=en).

References:

- Challenge page: https://huggingface.co/spaces/openadmet/cyp-challenge
- Dataset: https://huggingface.co/datasets/openadmet/cyp-challenge-train-test
- TabICL: https://github.com/soda-inria/tabicl (Qu, Holzmüller, Varoquaux, Le Morvan. "TabICL: A Tabular Foundation Model for In-Context Learning on Large Data", ICML 2025, arXiv:2502.05564; BSD 3-Clause as listed in the installed package metadata)
- CheMeleon: https://github.com/JacksonBurns/chemeleon ("Descriptor-based Foundation Models for Molecular Property Prediction", arXiv:2506.15792; MIT License)

## 8. Note

This is a short version, written during the challenge. It leaves out the control experiments, the further diagnostics, and my analysis of why local and blind results disagree. I plan to publish the details after the challenge closes (after 2026-11-03).
