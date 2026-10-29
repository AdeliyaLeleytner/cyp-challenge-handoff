# Independent Claude consultation
Round: 1
## User request
«блять ну посчитай, в чем проблема то» following «а какой балл получился на нашем holdout и holdout briford у этого воспроизведения?» Earlier: «сделай точь-в-точь воспроизведение bridford»; Vast.ai rental authorized for fast execution.
## Authoritative context and constraints
2026-10-24. Project root is this repository. Authorized retraining and local scoring; existing submission dispatch must not be duplicated or disrupted. No architecture search. Follow immutable ORX experiment snapshots. User AGENTS requires independent advisory. No secrets in inputs.
## Current state
Native-source 20-model (4 members x5 folds seed42) full-data submission trained successfully. Native member sizes 31670/4905/23264/1493. This includes all old own750 and briford529 holdouts. Thus no independent scores for that latest reproduction. Old adapted ensemble scores .60238/.62678 are not native reproduction results.
## Evidence and source map
- night/briford_native.py: native preparation, workers, fold means, endpoint averaging, author placement functions.
- vendor/briford_native/cyp_recalibrate.py: OOF_TO_BLIND, BLIND_MOMENTS, STRAE_MOMENTS and place/recalibrate.
- vendor/briford_native/cyp_union_features.py and cyp_aux_features.py: native joins and data preparation.
- night/evaluation.py and official_scoring_functions.py: official ST-RAE and alignment checks.
- /Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/remote/assets/cohorts.json and official-train.csv: frozen outer cohorts and truth intervals.
- /Users/adeliyaleleytner/autoresearch-runs/cyp-briford-reproduction-20261024/prepared: full training pools/specs.
## Work already performed
Verified full-pool inclusion, read native functions and official scorer; no new training yet. Previous run took 28 minutes on four3090 GPUs; current offers include eight3090 at ~$1.38/hour. Prior source/data snapshots and weights recovered; no new dataset acquisition needed.
## Questions for independent assessment
1. What evaluation protocol faithfully measures the requested reproduction on these two frozen cohorts, including handling public/auxiliary overlaps, fivefold ensembles and the native placement?
2. What are the critical checks and reporting distinctions before these results are interpreted alongside prior adapted scores?
## Known missing or inaccessible information
Author historical original checkpoint/environment are unavailable; this is same available-source reproduction as prior turn. New holdout scores unknown. Fixed placement constants were derived by author from public leaderboard, not these local holdout labels.
## Codex position
withheld for independent first-round assessment.
## Confidentiality check
No credentials, private keys, .env contents or unnecessary personal information.
