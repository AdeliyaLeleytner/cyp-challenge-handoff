# CYP Challenge

Our entry to the OpenADMET CYP Inhibition Blind Challenge: predicting inhibition of
CYP1A2, CYP2C9, CYP2D6 and CYP3A4 from molecular structure. Submission closes
3 November 2026.

The primary artefact is the document [`docs/CYP — модель и данные.pdf`](docs/) (in
Russian, and staying that way — it is the team's working document). Thirty-five pages: the
biochemistry of the task, what is in the data and what we measured from it, the model
with a justification for each part, the verification protocol, and a list of what has
already been tried and does not work. Everything else in this repository is the code
those numbers came from.

**[`METHOD.md`](METHOD.md)** is the method write-up in English: the loss derived from the
competition's own metric, the conjunction the classification label folds into, what we made of the
released data, the apparatus that tells an effect from a noise floor, a catalogue of what we tried
and closed, and a falsifiable prediction for the interim reveal. Roughly twenty minutes.

**[`docs/method_report.md`](docs/method_report.md)** is the short version written for the
organisers: what ships, the closed form we derived for the challenge's own metric, the uncertainty
apparatus, what we refused and why, and the limitations stated plainly. Roughly ten minutes, and
**the place to start if you are judging rather than reproducing.**

(This file said "and linked from the leaderboard" until 21 September. It was not: the board's Model
Report field has pointed at `METHOD.md` in every committed snapshot, so a judge following our row
has been handed the twenty-minute reproduction document instead of the ten-minute one written for
them. The field is set per submission and is corrected on the next upload.)

## Getting started

```bash
uv sync                             # environment, exact versions from uv.lock
git submodule update --init         # organisers' repo, holds the official metric
bash data/fetch.sh                  # challenge data (~7 MB, not stored in git)
uv run python src/feats.py          # features: fingerprint, descriptors, mechanistic block
uv run python src/score.py          # scores the ablation: six feature sets, macro ST-RAE 0.7729 / 0.7673
```

If you do not have [uv](https://docs.astral.sh/uv/) yet:
`curl -LsSf https://astral.sh/uv/install.sh | sh`. It fetches the pinned Python 3.12
itself, so nothing else needs installing. `make help` lists the pipeline targets.

Working on this with others? Read [CONTRIBUTING.md](CONTRIBUTING.md) first — it covers
who regenerates the expensive artefacts and how not to invalidate each other's numbers.

**Never used git or GitHub?** Start with [ONBOARDING.md](ONBOARDING.md) instead — it is
written in Russian, assumes nothing, and covers the traps specific to this repository.

## Layout

| Directory | Contents |
|---|---|
| `docs/` | the document and its sources (`tex/`, built with XeLaTeX), archive of earlier versions |
| `src/` | the pipeline: features, baselines, ablations, TDI, decision layer |
| `eda/` | data exploration and the figures for the document |
| `verify/` | 112 verification scripts, see `verify/README.md` |
| `results/` | run logs and saved out-of-fold predictions |
| `data/` | challenge data, not stored in git, see `data/README.md` |
| `tests/` | the golden-value guard on the cross-validation split |

Two modules at the root are shared by everything: `cyppaths.py` (paths, and locating the
organisers' repository) and `cypsplit.py` (the cross-validation split).

## Pipeline

Each step depends on the one before it:

1. `src/feats.py` — builds `data/feats.npz`: Morgan counts at r=2 (2048), 217 RDKit
   descriptors, 30 mechanistic features. The mechanistic block uses `src/pka.py`, a rule
   for estimating the pKa of the most basic centre.
2. `src/base.py` — baseline on fingerprint plus descriptors, five-fold cross-validation
   over Butina clusters at threshold 0.35.
3. `src/ablate.py` — six feature sets on the same folds, saves out-of-fold predictions to
   `results/preds/oof.json`.
4. `src/score.py` — metrics and a paired bootstrap over the saved predictions.
5. `src/range.py`, `src/rangectl.py` — testing the range-restriction explanation for CYP2D6.
6. `src/mech2.py`–`src/mech4.py` — three ways to bring in the primary screen, all three negative.
7. `src/tdibase.py`, `src/tdiprob.py` — baselines for the classification track.
8. `src/decision.py`, `src/decision2.py` — the decision layer for ST-RAE and its oracle ceiling.

Row 5 of the ablation grid — the joint likelihood — has its own chain, because its
predictions live in their own files and take about half an hour per arm to make:

9. `src/trunk.py` — shared trunk, two heads, `lambda_scr` as the switch on the screening
   loss term. `--mode twohead` gives the screen a free head; `--mode calibrated` routes it
   through the fixed instrument calibration instead, with no new parameters. One output
   file per mode, `results/preds/trunk_{mode}.json`; `--noise` adds an eta suffix. Both are
   committed, so everything below runs in minutes.
10. `src/trunkscore.py` — the lambda response with a paired bootstrap against lambda = 0.
11. `src/trunkdose.py` — the dose curve in lambda: whether the control is exact, what the
    damage is made of per enzyme, and how the arms compare with the boosting under a tilted
    label marginal.
12. `src/trunknoise.py` — the dose curve in *noise*. Degrades the screening channel in
    known steps so the four-enzyme ordering becomes four separate curves; needs the
    `--noise` runs of `src/trunk.py` first.

Two more that stand outside the grid:

13. `src/submit.py` — builds both submission files and refuses to write anything the
    organisers' validators reject.
14. `src/reweight.py` — scores under a test-like label marginal, since the test's own
    geometry cannot be reproduced by any re-split of the training data.

## Key numbers

Five-fold cross-validation over Butina clusters, threshold 0.35, seed 0.

| | 1A2 | 2C9 | 2D6 | 3A4 | Macro |
|---|---|---|---|---|---|
| ST-RAE, fingerprint and descriptors | 0.880 | 0.702 | 0.993 | 0.518 | 0.773 |
| ST-RAE, plus mechanistic block | 0.879 | 0.691 | 0.980 | 0.519 | 0.767 |
| Spearman, plus mechanistic block | 0.496 | 0.597 | 0.403 | 0.765 | 0.565 |
| sd of ST-RAE across four split seeds | 0.0109 | 0.0078 | 0.0052 | 0.0057 | 0.0019 |

One on the ST-RAE scale is what you get by predicting a single number for every compound.
CYP2D6 sits almost exactly there, and section three of the document is about why.

## How we work

All of this comes from measurement rather than from first principles; the reasoning is in
the document.

- **Only rank survives.** An affine pair — a shrink and a shift, fitted to the metric per
  fold — is applied before anything is written out, and being monotone it can undo any
  intervention that only changed scale or location. Five measured gains vanished or
  reversed when this was first checked, and a sixth later. Report the rank and the
  post-pair score; a gain on raw ST-RAE is not evidence of anything.
- Compare variants only on the same split and only with a paired bootstrap over
  compounds. A difference without an interval is not a result.
- One split is not enough: changing the seed moves macro ST-RAE by 0.016, which is more
  than the typical effect being measured. Any decision about what to submit is taken over
  at least four seeds — and **no result is written up from a run that has not printed its
  aggregate table**. Three conclusions have been withdrawn for breaking that rule.
- Our cross-validation is about 0.13 harder than the real test set, by median similarity
  to the nearest training compound. Quote a size-matched pair: a held-out row's similarity
  is a maximum over four fifths of the training set and a test row's over all of it, and a
  maximum over a larger reference set is larger for free. Local numbers are a lower bound,
  but they also select for a different skill than the leaderboard pays for — every saved
  ablation has been re-scored under weights matching the test's regime, and six of seven
  keep their ordering.
- **Check the log before evaluating an idea, not after.** `verify/README.md` runs past item 300
  and several proposals have been re-derived from scratch that were already built, run and
  measured in it.
- Negative results are recorded and stay in the repository. They are now the majority of
  that file and some of the most useful content here.
- The environment is pinned for a reason: scikit-learn 1.3.2 through 1.8.0 reproduce
  `results/preds/oof.json` bit for bit, 1.9.0 does not. See the comment in `pyproject.toml`.
