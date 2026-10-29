# OpenADMET CYP — Research Handoff

Private research repository for continuing the CYP Challenge. This snapshot was assembled on **29 October 2026** and brings together Direct Inhibition, TDI, ADMETlab collection, reproductions of public solutions, data audits, and private experiments P1–P11.

## Abstract

This project studies structure-based prediction of direct inhibition of CYP1A2, CYP2C9, CYP2D6, and CYP3A4. The primary task is pIC50 regression using 4,905 official training molecules and 750 blinded query molecules. The main reproduced baseline is a briford-style Chemprop ensemble with four task sets (18/8/6/1), five folds, and the published output-distribution placement procedure. Its exact preserved submission achieved **MA-ST-RAE 0.4424575** on the evaluated portion of the hidden test set and remains the project's best preserved submission.

ADMETlab outcomes were collected and chemically audited for 32,421 unique requested structures: 32,419 complete numerical vectors, 32,418 feature-eligible rows, and complete coverage of all 5,655 official molecules. These predicted properties are not experimental CYP labels. Experiments tested LightGBM readouts of ADME/ADMET features, direct concatenation of 120 properties into Chemprop, alternative losses, a two-descriptor unit correction, additional representations, and nested ensembles. H6 improved some local ST-RAE estimates but worsened the leaderboard score to 0.4616; a variant anchored to the original native ensemble scored 0.4679. The original 0.4425 submission was restored on 27 October. The local gains therefore did not establish an improvement on the leaderboard.

The main unresolved question is how validation and output calibration correspond to the challenge distribution. The two development cohorts, own750 and reconstructed-briford529, overlap by 143 molecules, have been reused during development, and do not reproduce the dense analogue-series structure of the blinded query set. P11 provides a provisional protocol for evaluating future candidates, not a validated leaderboard forecast. A separate TDI branch reproduces Jeremy and Hauser recipes and tests extensions; no candidate improved both development holdouts, so no TDI submission was made.

**Working package:** code, data, and results across the research directions, with the original native ensemble, final H6 heads, and selected TDI baseline models. Intermediate and rejected binary checkpoints were omitted at the owner's request. Quick access: [data](data/README.md), [models](models/README.md), and [results](results/README.md).

## Start here

1. [HANDOFF.md](docs/HANDOFF.md) — current state, findings, and next steps.
2. [EXPERIMENTS.md](docs/EXPERIMENTS.md) — experiment map and decisions.
3. [DATA.md](docs/DATA.md) — datasets, features, chemical corrections, and validation scope.
4. [REPRODUCING.md](docs/REPRODUCING.md) — restoration and execution on another machine.
5. [SUBMISSIONS.md](docs/SUBMISSIONS.md) — exact files and submission history.
6. [ARCHIVE_INDEX.md](docs/ARCHIVE_INDEX.md) — research directory guide.
7. [PACKAGE.md](docs/PACKAGE.md) — package contents and manifests.

## Quick verification without training

```bash
gh repo clone AdeliyaLeleytner/cyp-challenge-handoff
cd cyp-challenge-handoff
python3 tools/verify_handoff.py
```

Restore the included models, arrays, and large tables with the commands below. The download is approximately 2.94 GB; allow 12 GB of free disk space.

```bash
python3 tools/restore_assets.py --download
python3 tools/verify_handoff.py --all
```

Access to the private repository and release requires an authorized GitHub account. The restoration tool uses `gh`, checks SHA256 hashes, and restores the original archive paths. It performs no training or submissions. Use `--list` to inspect the required downloads or `--prefix archive/artifacts/cyp-private-v2-20261026/p11/` to select a research directory. Identical files are stored once by hash; restoration uses hard links where possible and copies otherwise.

The `archive/` directory preserves historical working directories and source records under their original names. Use `docs/` for the current handoff workflow: historical plans may be outdated and may contain machine-specific absolute paths. The tools do not automatically execute archived submission, collection, or compute-rental scripts. The original public gist was deleted at the owner's request; historical references to it do not imply that it is available or should be restored.

Keep these materials private. Third-party code, datasets, and checkpoints retain their original ownership and license terms; no blanket open-source license is assigned to the archive. The recipient must be granted repository access before continuing the work.
