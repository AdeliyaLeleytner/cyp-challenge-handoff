# OpenADMET CYP Inhibition Blind Challenge: method report

Entry to the **Direct Inhibition (regression)** track. Public challenge data only; no proprietary data. Code: `cyp_challenge.ipynb` (Google Colab, free tier).

## Result so far
First submission (model E below): macro ST-RAE 0.757, MAE 0.9013, rank 107 of 243 at submission check [add Spearman, Kendall and R² from the leaderboard row after verifying the column order].

## Data and features
- Training: `cyp-challenge-TRAIN_inhibition.csv` (4,905 compounds, pIC50 plus credible intervals) and the single-concentration screen (4,376 compounds, all four isoforms, log2 fold-change).
- Features: Morgan count fingerprints (radius 2, 2048 bits) + 217 RDKit descriptors. Models: LightGBM, one per isoform.

## Main observation: labels are missing non-randomly
Most training compounds (3,596 of 4,905) have a dose-response pIC50 for only one isoform, while the single-concentration screen covers every compound on all four enzymes. Fold-change correlates strongly with pIC50 on labeled pairs (Spearman 0.82-0.94), but the unlabeled pairs are a mixture: mostly non-inhibitors for CYP2D6, but many clear inhibitors for CYP3A4. A blanket "unlabeled = inactive" rule would be wrong.

## Models
- **A**: LightGBM on labeled pIC50 only.
- **B**: A plus soft labels for unlabeled pairs, from an isotonic map of fold-change to pIC50 fitted inside each training fold (weight 0.5).
- **G**: LightGBM with a custom objective that charges nothing inside each compound's credible interval and a smoothed linear cost outside it (mimics the scoring rule).
- **E** = mean(A, B). **H** = mean(G, B).

## Validation and what we learned
Scoring code copied from the challenge's evaluation module (ST-RAE). 5-fold random CV, one seed, so differences below about 0.03 should be treated as noise.
- Soft labels (B) improved ranking and reduced predictions on clear inactives, but biased predictions low for real inhibitors (labeled bias -0.29) and worsened ST-RAE on labeled compounds (0.944 vs 0.760 for A).
- A two-stage inhibitor-classifier model did not work as built (labeled ST-RAE 1.36 with a low floor).
- The interval loss alone (G) was not better than A on all compounds (0.790 vs 0.760). The blend H was the best hedge (0.751).
- A pseudo-complete validation set built from the fold-change map favored soft labels, but the leaderboard score (0.757) tracked the labeled-compound score much better, so that pseudo score was too optimistic.
- **Distribution shift:** a classifier separates test from training structures with AUC 0.949, and test compounds have median nearest-neighbour similarity 0.59 to training (0.45 within training). Models do worse on the training compounds most similar to the test set.

## Limitations
Single seed and split; no external data; CYP2D6 is poorly predicted by every model (labeled ST-RAE about 1.0). [Update this section with the final submission and any later experiments.]

