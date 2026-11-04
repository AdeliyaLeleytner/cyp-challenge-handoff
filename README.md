# OpenADMET CYP — Model Methodology

Methodology and data documentation for the **Direct Inhibition / Regression Prediction** submission by **Adeliya Leleytner**.

The model predicts direct-inhibition pIC50 for **CYP1A2, CYP2C9, CYP2D6 and CYP3A4** from molecular structures. It combines endpoint-specific molecular graph ensembles with a three-dimensional molecular model and a screen-informed support-vector regression component for CYP2D6.

## Read the report

- [Model methodology](docs/MODEL_REPORT.md): model families, training, cross-fitting, endpoint-specific assembly, output calibration and validation limitations.
- [Data description](docs/DATA_DESCRIPTION.md): official training data, public auxiliary measurements, representations, units and molecular preparation.

The report identifies the submitted prediction artifact by its SHA256 and describes its frozen serving procedure. The owner confirmed that this artifact was resubmitted before the deadline. This documentation update does not submit or modify predictions and does not establish a final leaderboard result.

**Documentation updated: 4 November 2026.** This repository contains only the model report and data description. Code, checkpoints, prediction tables and datasets are not included.

This repository is private. Reviewers need explicitly granted repository access. Repository access does not grant redistribution rights to third-party data or pretrained models.
