"""Configuration constants for the CYP Challenge HuggingFace Space."""

import os

# -------------------------------- Global Params ---------------------------------------

# This is updated manually to allow control over what is visible on the HF Space.
# Possible phases:
# 0: Pre-challenge
# 1: Phase 1 (only live leaderboard)
# 2: Phase 2 (live leaderboard + static interim leaderboard)
# 3: Challenge closed, final leaderboard not yet released
# 4: Challenge closed, final leaderboard released
CURRENT_PHASE = 2
HOURS_BETWEEN_SUBMISSIONS = 12
# Minimum standard deviation for regression predictions to be considered valid.
# Constant columns (with or without slight noise added) can be used to game the
# leaderboard metric.
MIN_PREDICTION_STD = 0.01

# Leaderboard and S3 configuration.
# Regression, classification, and structure are three fully independent backend
# tracks (each with its own submissions/scores/leaderboard S3 prefix, Lambda,
# per-track macro-average, etc.). Must mirror backend.config.TrackPaths.track.
REGRESSION_TRACK = "regression"
CLASSIFICATION_TRACK = "classification"
STRUCTURE_TRACK = "structure"

# {track} is one of REGRESSION_TRACK / CLASSIFICATION_TRACK / STRUCTURE_TRACK.
# {endpoint_slug} is MACRO_ENDPOINT_LABEL ("MA") for a track's master (macro-ranked)
# leaderboard (only present once a track has more than one endpoint), a
# REGRESSION_ENDPOINTS/CLASSIFICATION_ENDPOINTS entry (e.g.
# "CYP3A4_pIC50_direct_inhibition") for that endpoint's own leaderboard, or
# STRUCTURE_ENDPOINTS[0] ("structure") for the structure track's one leaderboard —
# see leaderboards.format_leaderboard_uri.
# {version} is "latest" or an ISO timestamp.
# Every leaderboard file (all tracks, all stages) follows this one convention — must
# mirror backend.aws_leaderboards._leaderboard_file_path.
LEADERBOARD_URI_FORMAT = (
    "leaderboard/{leaderboard_type}/{track}/{endpoint_slug}_leaderboard_{version}.csv"
)
S3_BUCKET: str = os.environ.get("S3_BUCKET", "")
AWS_DEFAULT_REGION: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
CHALLENGE_ANNOUCEMENT_LINK = (
    "https://openadmet.ghost.io/announcing-openadmets-cyp-inhibition-blind-challenge"
)
DATASET_DOWNLOAD_LINK = (
    "https://huggingface.co/datasets/openadmet/cyp-challenge-train-test"
    if CURRENT_PHASE >= 1
    else False
)
TUTORIAL_LINK = "https://github.com/OpenADMET/CYP-Challenge-Tutorial"

# Activity bootstrap-results.parquet files hold one row per (Sample, Endpoint) pair,
# including this synthetic pseudo-endpoint holding the multi-endpoint macro-averaged
# scores for that bootstrap sample. Must mirror backend.config.MACRO_ENDPOINT_LABEL.
MACRO_ENDPOINT_LABEL = "MA"

# -------------------------------- Activity Track Params -------------------------------

# Dataset sizes and required columns
ACTIVITY_DATASET_SIZE = 750
IDENTIFIER_COLUMNS = ["SMILES", "Molecule_Name"]

# Drives one leaderboard tab per activity endpoint. Must mirror
# backend.config.ACTIVITY_ENDPOINTS.
REGRESSION_NAME = "Direct Inhibition Prediction (Regression)"
REGRESSION_ENDPOINTS = [
    "CYP1A2_pIC50_direct_inhibition",
    "CYP2C9_pIC50_direct_inhibition",
    "CYP2D6_pIC50_direct_inhibition",
    "CYP3A4_pIC50_direct_inhibition",
]
CLASSIFICATION_NAME = "TDI Prediction (Classification)"
CLASSIFICATION_ENDPOINTS = [
    "CYP2D6_is_TDI",
    "CYP3A4_is_TDI",
]

# Controls whether the "Classification Prediction" option is shown on the Submit
# tab — same plain-bool, manually-controlled pattern as STRUCTURE_TRACK_LIVE below.
CLASSIFICATION_ACTIVE = True

# Regression and classification are independent submission tracks (see
# render_submission_tab / Submission.track) — REQUIRED_REGRESSION_COLUMNS and
# REQUIRED_CLASSIFICATION_COLUMNS drive each upload's own validation.
# ACTIVITY_ENDPOINTS/ACTIVITY_DATASET_SIZE remain as the combined view of the shared
# underlying compound set — used by head_to_head.py's cross-track comparison, and as
# the shared row-count both tracks validate against (same compounds, different
# columns) — not as a submission-upload concept.
ACTIVITY_ENDPOINTS = REGRESSION_ENDPOINTS + CLASSIFICATION_ENDPOINTS
REQUIRED_REGRESSION_COLUMNS = IDENTIFIER_COLUMNS + REGRESSION_ENDPOINTS
REQUIRED_CLASSIFICATION_COLUMNS = IDENTIFIER_COLUMNS + CLASSIFICATION_ENDPOINTS

# Metric names as they appear (unprefixed, once narrowed to a single endpoint) in a
# leaderboard's columns, and how each should be labelled in the UI, in display order
# (primary/sort metric RAE first). Must mirror backend.config.ACTIVITY_METRICS.
ACTIVITY_METRIC_DISPLAY_NAMES = {
    "ST-RAE": "ST-RAE",
    "MAE": "MAE",
    "R2": "R²",
    "Spearman_R": "Spearman's ρ",
    "Kendall_Tau": "Kendall's τ",
}

# Same idea, for the classification (TDI) track's leaderboard columns. MCC is the
# primary/sort metric, listed first. Must mirror backend.config.CLASSIFICATION_METRICS.
CLASSIFICATION_METRIC_DISPLAY_NAMES = {
    "MCC": "MCC",
    "Accuracy": "Accuracy",
    "Precision": "Precision",
    "Recall": "Recall",
    "F1": "F1 Score",
}

# -------------------------------- Stucture Track Params -------------------------------

# The structure track will be started halfway through the challenge, so we can control
# when it is visible on the HF Space.
STRUCTURE_TRACK_LIVE = True
STRUCTURE_DATASET_SIZE = 20

# Structure track's single leaderboard slug. Must mirror
# backend.config.STRUCTURE_ENDPOINTS.
STRUCTURE_NAME = "Structure Prediction (Pose)"
STRUCTURE_ENDPOINTS = ["structure"]

# ------------------------------- Useful functions -------------------------------------


def _submission_schema_row(column: str, dtype: str, description: str) -> str:
    return f"| `{column}` | {dtype} | {description} |"


def _endpoint_schema_row(endpoint: str, kind: str) -> str:
    """Build a submission schema table row for one regression/classification endpoint."""
    isoform = endpoint.split("_", 1)[0]
    if kind == "regression":
        return _submission_schema_row(
            endpoint, "float", f"Predicted direct-inhibition pIC50 for {isoform}"
        )
    return _submission_schema_row(
        endpoint,
        "bool",
        f"Predicted time-dependent inhibition call for {isoform} "
        "(`True`/`False` or `1`/`0`)",
    )


# Single source of truth for each track's submission file column schema — shown on
# both the Submit tab (submission.py) and in the FAQ, generated from
# REGRESSION_ENDPOINTS / CLASSIFICATION_ENDPOINTS so the two can't drift out of sync
# with each other or with the actual validation logic (which checks
# REQUIRED_REGRESSION_COLUMNS/REQUIRED_CLASSIFICATION_COLUMNS).
def _schema_table_md(rows: list[str]) -> str:
    return "\n".join(
        [
            "| Column Name | Type | Description |",
            "| :--- | :--- | :--- |",
            _submission_schema_row(
                "SMILES", "string", "SMILES string for the compound"
            ),
            _submission_schema_row(
                "Molecule_Name", "string", "Unique compound identifier"
            ),
            *rows,
        ]
    )


SUBMISSION_SCHEMA_TABLE_REGRESSION_MD = _schema_table_md(
    [_endpoint_schema_row(e, "regression") for e in REGRESSION_ENDPOINTS]
)
SUBMISSION_SCHEMA_TABLE_CLASSIFICATION_MD = _schema_table_md(
    [_endpoint_schema_row(e, "classification") for e in CLASSIFICATION_ENDPOINTS]
)


def _example_row(identifiers: tuple[str, str], values: list) -> str:
    return ",".join([*identifiers, *[str(v) for v in values]])


def _csv_example_md(endpoint_columns: list[str], example_rows: list[list]) -> str:
    header = ",".join(IDENTIFIER_COLUMNS + endpoint_columns)
    rows = "\n".join(
        _example_row(identifiers, values) for identifiers, values in example_rows
    )
    return f"""```
{header}
{rows}
...
```"""


SUBMISSION_CSV_EXAMPLE_REGRESSION_MD = _csv_example_md(
    REGRESSION_ENDPOINTS,
    [
        (("CCO", "OADMET-00000"), [6.23, 5.94, 6.78, 5.41]),
        (("c1ccccc1", "OADMET-00001"), [5.87, 6.10, 5.55, 6.02]),
    ],
)
SUBMISSION_CSV_EXAMPLE_CLASSIFICATION_MD = _csv_example_md(
    CLASSIFICATION_ENDPOINTS,
    [
        (("CCO", "OADMET-00000"), [False, True]),
        (("c1ccccc1", "OADMET-00001"), [True, False]),
    ],
)

# ------------------------------- Challenge Page Content -------------------------------

# Challenge page content
PAGE_TITLE = "OpenADMET CYP Blind Challenge"

HEADER_MARKDOWN = """## OpenADMET Blind Challenge: Predicting CYP Inhibition 🧬
The next OpenADMET blind challenge focuses on predicting **Cytochrome P450 (CYP) inhibition**. CYP enzymes are the primary drivers of xenobiotic metabolism, and unexpected CYP inhibition can derail drug discovery programs through unpredictable drug-drug interactions. The goal of this challenge is to develop predictive models that can accurately forecast CYP inhibition, thereby aiding in the design of safer and more effective drugs.

This heme-containing superfamily is responsible for the biotransformation of the vast majority of marketed small-molecule drugs and contains dozens of human isoforms with overlapping and complementary substrate scopes. This flexibility is exactly what makes them so central to xenobiotic metabolism and makes their collective behavior difficult to predict. 

Go to the **Leaderboard** to see current standings. To participate, head to the **Submit** tab to upload your predictions.

**Challenge Timeline**: 
* Submissions open August 17th. 
* Intermediate submission deadline is September 24th.
* An intermediate leaderboard will be released September 25th.
* Submissions will close on November 3rd.
"""

HOW_TO_PARTICIPATE_MD = f"""## ✅ How to Participate

1. **Register:** Create an account with Hugging Face.
2. **Get the Data:** Access the training data (including primary screening data and ~1,500 DRCs per isoform) on the Hugging Face Dataset page.
3. **Walk through the Tutorial:** Check out the baseline notebooks and validation scripts in the [challenge tutorial repository]({TUTORIAL_LINK}).
4. **Disclosures:** Indicate whether your submission contributes open-source code and disclose any use of **proprietary training data**.
5. **Join the Community:** Get support, ask questions, and collaborate in the `#cyp-challenge` channel on our [Discord](https://discord.com/channels/1412827471488745545/1480419832787763412).
6. **Submit:** Upload your predictions via the **Submit** tab.

---"""

ABOUT_MD = f"""
# 💊 OpenADMET CYP Inhibition Blind Challenge

## Background: Why CYP Inhibition Matters

Following our successful PXR Challenge, we are excited to launch our next blind challenge: **Predicting Cytochrome P450 (CYP) Inhibition**. Where PXR *induction* accelerates metabolism by upregulating metabolizing enzymes, CYP *inhibition* does the opposite, jamming the body’s primary mechanism for xenobiotic elimination. Both can derail drug discovery programs through the same general mechanism: unpredictable drug exposure.

When a candidate compound inhibits a CYP isoform, it slows the clearance of co-administered drugs cleared by that enzyme, driving plasma concentrations upward into toxic territory. Consequences include:

* **Drug–Drug Interactions (DDIs):** Reduced clearance pushes exposure above the therapeutic window, representing the most common CYP-mediated clinical liability.
* **Narrow Therapeutic Index Risk:** Dangerously amplifies exposure for co-medications with little margin between efficacy and toxicity.
* **Time-Dependent Inhibition (TDI):** Mechanism-based ("suicide") inhibitors generate reactive metabolites or complexes during catalytic turnover that irreversibly disable the enzyme, causing DDIs that persist long after the parent compound has cleared.

Evaluating CYP inhibition is a core pillar of the ADMET cascade and a strict regulatory requirement for the FDA and EMA. Predicting inhibition across a panel *in silico* allows teams to design out interaction liabilities early and aligns with the FDA’s New Approach Methodologies (NAMs) initiative to reduce preclinical animal testing.

Like PXR, CYPs present a modeling challenge that goes beyond a single number. Their active sites are large, malleable, and heme-centered, accommodating chemically diverse substrates in multiple binding orientations. High-quality, consistently generated inhibition data across a unified isoform panel remains rare, a gap this challenge directly addresses.

---

## The Activity Dataset

At Octant, OpenADMET generated a high-throughput, 12-point dose-response curve (DRC) dataset across four major human CYP isoforms driving small-molecule drug metabolism: **CYP3A4, CYP2C9, CYP2D6, and CYP1A2**.

The dataset was built using a two-tier screening strategy followed by hit expansion:

* **Primary Screen:** Single-concentration screening across Enamine DDS10 (diversity set) and FDAA (FDA-approved compounds) libraries. 
* **Dose-Response Training Set:** Top hits were promoted to 12-point DRCs (~1,500 DRCs per CYP) and fit using a Bayesian curve-fitting pipeline.
* **Analog Expansion Test Set:** Hit expansion was performed on the top 25 hits from CYP1A2, CYP2C9, and CYP3A4 by purchasing the top 10 chemisimilars (ECFP4 Tanimoto similarity) per hit compound from the Enamine US catalog.
* **Dense Test Matrix:** The resulting **750-compound test set** was fully assayed in 12-point DRC mode against **all four CYPs** (including CYP2D6), yielding a dense test matrix with detailed SAR and activity cliffs.

---

## Developing the Assay

We developed high-throughput biochemical assays compatible with Octant’s Navigator platform in 1536-well plate format:

* **Fluorescence Panel (CYP3A4, CYP2C9, CYP1A2):** Adapted from ThermoFisher Vivid fluorogenic kits. Recombinant enzymes metabolize masked probes to produce fluorescent readouts.
* **Echo-MS Mass Spectrometry Panel (CYP2D6):** Because fluorogenic 2D6 probes exhibited poor signal-to-noise ratios, we developed a label-free mass spectrometry assay. 
* **Default TDI Protocol:** Direct and time-dependent inhibition were measured simultaneously using an IC50-shift design. Every compound is pre-incubated with recombinant CYP in the absence and presence of cofactor before probe substrate addition. A leftward shift signals mechanism-based time-dependent inhibition.

---

## 🧪 The Challenge Tracks

This challenge is split into three related tracks.

### 1. Direct Inhibition Track (Regression)
Predict the direct-inhibition (pIC50) for all 4 isoforms (**CYP3A4, CYP2C9, CYP2D6, CYP1A2**) across the 750-compound test set (4 continuous regression targets per compound).

* **Soft-Threshold Scoring:** Low-activity compounds (pIC50 < 4) fall below the lowest tested assay dose and carry higher experimental noise. To avoid penalizing models unfairly, we introduce **Soft-Threshold Relative Absolute Error (ST-RAE)**. Error is measured as the distance between the predicted value and the credible interval bound of the fitted dose-response curve; predictions falling anywhere inside the credible interval incur zero error.
* **Primary Evaluation Metric:** **Macro-Averaged Soft-Threshold RAE (MA-ST-RAE)** across all four endpoints. Secondary metrics (MAE, R², Spearman ρ, Kendall's τ) are also reported with 1,000-sample bootstrap confidence intervals.

### 2. Time-Dependent Inhibition Track (Classification)
Classify whether a compound exhibits significant time-dependent inhibition (boolean True/False label). This mirrors real-world drug discovery workflows where positive calls trigger follow-up kinetic studies.

* **Target Isoforms:** Evaluated on **CYP3A4 and CYP2D6** only (where TDI phenomena are clinically prominent).
* **Primary Evaluation Metric:** **Matthews Correlation Coefficient (MCC)**, ideal for imbalanced, threshold-based classification labels.
* **Label Definition:** Positive means the TDI-arm IC50 shift exceeds 2-fold relative to direct inhibition, including inferred positives among low-activity compounds where a shift can't be measured directly. See the FAQ for the full labeling rules.

### 3. Structure Prediction Track
Predict the 3D structure of a **CYP3A4** protein-ligand complex given only the ligand SMILES. Our team at UCSF resolved 20 novel Cryo-EM structures of CYP3A4 complexed with a selection of assayed ligands (15 from the training set, 2 from the test set, and 3 additional compounds) — significantly expanding the chemical space beyond existing X-ray PDB structures. CYP3A4's remarkably flexible, heme-centered binding pocket, combined with the fact that similar ligands can adopt drastically distinct binding poses, makes it a notoriously hard target for computational structure prediction.

* **Submission:** A single `.zip` archive containing all 20 predicted complexes. Co-folding models, docking software, public PDB structures, or proprietary data are all fair game — feel free to draw inspiration from workflows that succeeded in our previous [PXR challenge](https://huggingface.co/spaces/openadmet/pxr-challenge).
* **Primary Evaluation Metric:** **Local Distance Difference Test for Protein-Ligand Interactions (LDDT-PLI)**, scored automatically against the blinded ground truth via the OpenStructure pipeline. Secondary metrics include Binding-Site Superposed, Symmetry-Corrected Pose RMSD (BiSyRMSD).
* **Physical Plausibility Checks:** New for this challenge, every submitted structure is also run through [PoseBusters](https://pubs.rsc.org/sc/article/15/9/3130/827511/PoseBusters-AI-based-docking-methods-fail-to) chemical/geometric sanity checks — accuracy metrics like LDDT-PLI or BiSyRMSD don't tell the whole story, and producing physically realistic poses matters too. A structure that fails basic OpenStructure checks receives an LDDT-PLI score of 0 and a 20 Å BiSyRMSD penalty; a structure that fails PoseBusters receives an LDDT-PLI score of 0.


---

## 🏆 Innovation in ML Award

In addition to leaderboard rankings, the OpenADMET team will present an award for the **Most Innovative Machine Learning Approach(es)**. This award rewards exploration over mere exploitation. We will evaluate architectural novelty, creative data usage, novel uncertainty quantification strategies, and simple yet effective ideas—regardless of final leaderboard rank!

---

{HOW_TO_PARTICIPATE_MD if CURRENT_PHASE in [1, 2] else ""}

## 📅 Timeline

*All submission deadlines are 23:59 UTC.*

| Date | Action |
|:--- |:--- |
| **July 29, 2026** | Challenge announced |
| **August 17, 2026** | Training/Test sets released; submissions open 🚀 |
| **September 24, 2026 (23:59 UTC)** | Deadline for intermediate leaderboard submissions |
| **September 25, 2026** | Intermediate leaderboard released (one-time full test set reveal) |
| **November 3, 2026 (23:59 UTC)** | Submissions close 🏁 |
| **From November 4, 2026** | Final leaderboard released, webinars, blog posts, and wrap-up |

---

## Acknowledgements
We would like to acknowledge the hard work of all the experimentalists at Octant and UCSF for making this challenge possible.

We would also like to thank our funders for their support of OpenADMET, in particular ARPAH, Radial (part of the Astera Institute - https://ror.org/00ydx1s47), Schrodinger Inc, and the Gates Foundation.  We would also like to thank our partners Enamine, HuggingFace, OpenEye, CDD Vault, Discovery Life Sciences and the beamline staff at NSLS-II for their support. 

This work is supported by the Advanced Research Projects Agency for Health (ARPA-H) under AVOID-OME, and Award Number 1AY1AX000035. The contents are those of the authors. They may not reflect the policies of the Department of Health and Human Services or the U.S. government. The content is solely the responsibility of the authors and does not necessarily represent the official views of the Advanced Research Projects Agency for Health.
"""

FAQ_MD = f"""
### Frequently Asked Questions

**What is the goal of the OpenADMET CYP Inhibition Challenge?**  
The goal is to predict Cytochrome P450 (CYP) inhibition across a panel of four key human isoforms (**CYP3A4, CYP2C9, CYP2D6, and CYP1A2**) for a dense test set of 750 compounds. The challenge evaluates both **Direct Inhibition** (regression) for all isoforms, and **Time-Dependent Inhibition (TDI)** (classification) only for CYP3A4 and CYP2D6.

**How does this challenge structure compare to previous challenges?**  
This challenge consists of a single continuous stage rather than two sequential unblinding phases. An interim leaderboard will reveal intermediate performance on the full test set at the halfway mark, but no ground-truth test data will be unblinded until the challenge concludes.

**Can I compete in one or both tracks?**
Yes! The **Direct Inhibition Track (Regression)** and **Time-Dependent Inhibition Track (Classification)** are independent submission tracks, each submitted as its own file (see "What file formats are required for submission?" below), and each is scored independently and ranked on its own leaderboard. You're free to submit to just one track — a strong entry in one track will still be ranked on that track's leaderboard regardless of whether you submit to the other.

**I want to participate with colleagues. Should we submit together or separately?**  
Please submit under a single Hugging Face account representing your lab or team. Multiple submissions from the same team or lab (i.e., individuals who cooperate intensively to prepare entries) are not permitted.

**Are there limits on submission frequency?**  
Yes, submissions are rate-limited to at most once every 12 hours. Only your latest valid submission will count toward the live leaderboard standings. Please run the validation script before uploading!

**When do final entries have to be submitted?**  
All final submissions must be received by **November 3, 2026, at 23:59 UTC**.

**Where do I ask technical questions?**  
For technical questions regarding dataset schema, infrastructure, or submission mechanics, use the `#cyp-challenge` [channel on the OpenADMET Discord](https://discord.gg/HJGYrHnsa).

---

#### Evaluation & Scoring

**How are predictions evaluated in the Direct Inhibition Track?**  
The primary metric is **Macro-Averaged Soft-Threshold Relative Absolute Error (MA-ST-RAE)** across all four CYP isoforms. 

Because low-activity compounds (pIC50 < 4) fall below the assay's lowest tested dose and carry higher experimental noise, we use a custom **Soft-Threshold RAE (ST-RAE)** metric. Error is measured as the distance between your prediction and the nearest credible interval bound of the fitted dose-response curve. Predictions falling anywhere inside the credible interval incur zero error penalty. Secondary metrics (MAE, R², Spearman ρ, Kendall's τ) are also reported. All metrics are bootstrapped over 1,000 resamples.

**How are predictions evaluated in the Time-Dependent Inhibition (TDI) Track?**
TDI classification is evaluated on **CYP3A4** and **CYP2D6** using the **Matthews Correlation Coefficient (MCC)** as the primary metric. Rather than predicting the TDI-arm pIC50 directly, you classify whether a compound is a time-dependent inhibitor — i.e., whether the IC50 shift after preincubation exceeds 2-fold. Predictions are requested for every compound in the test set (so the set of scored compounds carries no information back into the regression track), but only compounds whose label can be assigned with confidence contribute to the score. Secondary metrics (Accuracy, Precision, Recall, F1) are also reported.

**How exactly are TDI positive/negative labels assigned?**
Because the label reflects a *shift* between two arms (direct inhibition vs. TDI) rather than a single measured value, labeling depends on where a compound's direct-inhibition pIC50 falls relative to 4, the assay's reliable lower limit:

* **Positive** — direct-inhibition pIC50 above 4, and the shift to the TDI arm exceeds 2-fold (log10(2-fold) = 0.301).
* **Negative** — direct-inhibition pIC50 above 4, and the shift does not exceed 2-fold.
* **Inferred positive** — direct-inhibition pIC50 below 4 (too low to reliably measure a shift), but the TDI-arm pIC50 exceeds 4.301. A true direct-inhibition value of at most 4 already guarantees a >2-fold shift once the TDI-arm value clears 4.301, so these compounds — which go from no signal in direct inhibition to measurable TDI — are labeled positive. We consider these important to include rather than discard.
* **Assigned negative** — direct-inhibition pIC50 below 4 *and* TDI-arm pIC50 below 4. TDI can't be reliably determined here, but compounds this inactive in both arms are unlikely to be selected for a follow-up kinetic study in practice, so they're labeled negative by convention.

The scored **positive class = positives + inferred positives**; the scored **negative class = negatives + assigned negatives**.

**Why are low-activity compounds treated differently?**
pIC50 values below 4 are outside the reliable dynamic range of the physical assay. Standard MAE/RAE would unfairly penalize models for missing noisy point estimates in inactive regions. Soft-thresholding (regression track) and the inferred/assigned labeling scheme (TDI track) both guarantee that models are only scored against genuine chemical signal, not assay noise.

---

#### Data, Rules & Submissions

**Can I use external or proprietary data to train my models?**  
Yes! External data and pretrained models are fully permitted. However, you must disclose whether you used proprietary training data by checking the *"I used proprietary data"* box during submission. This flag will be publicly displayed on the leaderboard.

**Am I required to open-source my code?**  
Open-sourcing code is strongly encouraged (and required if you want to win kudos from the community or qualify for novel machine learning recognition), but not strictly mandatory for standard leaderboard ranking. When submitting, tick the *"Open Source Code"* checkbox and provide a link to your public repository. This will need to be a publicly accessible link at submission time, and will be displayed on the leaderboard.

**What is the "Innovation in ML Award"?**  
To encourage scientific exploration over pure leaderboard tuning, the OpenADMET team will present a discretionary award for the most innovative machine learning approach. This award considers architectural novelty, creative data usage, novel uncertainty quantification, and clever engineering, independent of your final leaderboard rank.

**Will there be a summary preprint paper?**  
No. To maximize open-science velocity and release datasets as quickly as possible, we publish detailed post-challenge writeups, deep-dive benchmarks, and analysis as **blog posts** rather than traditional preprints. Participants are actively encouraged to publish their own methods and findings independently!

---

#### Technical & Submission File Formats

**What file formats are required for submission?**

Direct Inhibition (regression) and TDI (classification) predictions are submitted as **two independent files**, one per track. Each is a `.parquet` (preferred) or `.csv` file containing exactly {ACTIVITY_DATASET_SIZE} rows (one per test set compound).

**Submission Schema Details**

*Regression track:*

{SUBMISSION_SCHEMA_TABLE_REGRESSION_MD}

*Classification track:*

{SUBMISSION_SCHEMA_TABLE_CLASSIFICATION_MD}

*Rules:*
1. Each file must contain exactly {ACTIVITY_DATASET_SIZE} rows—no more, no fewer.
2. Column names are case-sensitive and must match exactly.
3. All prediction columns in a given file are required and must be fully populated for every row: pIC50 values must be finite floats (no `NaN`, `inf`, or `-inf`) and TDI values must be valid booleans.
4. Regression and classification predictions are scored independently and ranked on separate leaderboards (see "Evaluation & Scoring" above).

**Where can I find the submission validation script?**  
Validation scripts will be released on GitHub. Always run the validation script locally before uploading to avoid failed submission attempts.

**My entry hasn't appeared on the leaderboard. What should I do?**  
First, check the `#cyp-challenge-submissions` channel on Discord for automated receipts and error logs. If your submission failed validation, re-run the local validation script against your file. If no receipt appears after 2 hours, post a message in `#cyp-challenge` for help.
"""
