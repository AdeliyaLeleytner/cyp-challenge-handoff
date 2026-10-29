# CYP direct-inhibition CheMeleon baseline

One bounded four-target fine-tuning run on official direct-inhibition measurements only. No auxiliary labels, external activity data, model sweep or public submission.

The split is frozen before training: 3,805 fitting molecules,350 independent validation molecules for checkpoint selection,750 final holdout molecules. Holdout selection uses molecular structure and label availability, never activity values or leaderboard results. It approximates the public test's geometry but does not reconstruct its unknown label distribution. Missing targets are masked.

CheMeleon message passing weights: Zenodo15460715, SHA256 `c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651`. Strict loading and feature dimensions checked. Encoder fully trainable. Four-task default RegressionFFN, mean aggregation, no batch normalization, masked MSE on train-only standardized targets. Full runtime pins are in requirements.lock.txt.

Checkpoint selected by inner-validation loss. Outer holdout is predicted once afterward. Report official two-sided interval ST-RAE, secondary metrics,1000 bootstrap resamples and constant train-mean reference. No claim that the local score predicts the leaderboard score; intervals do not include split-selection or training-seed uncertainty.

Fixed command: `bash run.sh`. Run through orx with task-local store `/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store`, local backend and MPS on this Mac. The explicit interpreter in run.sh is the pinned local environment, outside the Documents file-provider directory.

The preflight executes a single forward/backward compatibility check without optimizer steps; it is not a trained checkpoint. `outputs/` contains logs, checkpoints, predictions and final results when a run finishes.
