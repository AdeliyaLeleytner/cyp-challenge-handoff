# Independent Claude consultation

Round: 1

## User request
"самый лучший открытый результат вот https://github.com/lachrymator/openadmet-cyp-challenge-public, почему ты его пропустил?"
Prior request: research public solutions and run overnight CYP Direct Inhibition experiments, compare on own holdout and strongest public solution holdout, submit only after improvement on both. That campaign is completed and one submission was accepted. Current request asks to explain omission, not to launch new compute.

## Authoritative context and constraints
2026-10-24, Moscow timezone. Root/workspace for this scoped review is the campaign folder. Codex owns conclusions. User requires this independent advisory protocol for substantive reviews. Read-only consultation. No credentials or unrelated personal data. Do not contact others or launch training. Be brief.

## Current state
Campaign selected briford as strongest declared Open Code=Yes entry. 57 configurations were tried; own submitted score is .7521205. User points to a public method write-up that was not included in the saved review.

## Evidence and source map
- DEEPRESEARCH.md final section and PREVIOUS_WORK.md record briford as strongest declared open-code reference.
- notes/presend-20261023T2345.md lines17-26 explicitly limits ordering to Open Code=Yes and notes it does not prove absence of public material for No entries.
- sources/presend-20261023T2345/leaderboard-live.csv ALREADY contains stir_bar, rank27, ST-RAE .443539995892439, Open Code=No, and exact user-linked GitHub URL. briford rank22 score .4377997714479094.
- official_results/20261024T084528Z/leaderboard.csv is fresh live board, 258 rows; inspect corresponding current rows (previous refresh ranks stir_bar29/briford24, same scores).
- sources/lachrymator-README-20261024.md fetched now via GitHub connector. README explicitly says write-up only, not training code. Describes Butina whole-cluster folds, masked auxiliary pretraining, 4999 unlabelled test-neighbour compounds used only for calculated properties, Mitra frozen-embedding learners, nonnegative stacking and correlation pruning. It distinguishes live from interim board; historical best rank13, interim rank28 regression and rank6 TDI. Its .465 regression ST-RAE is interim, not the live .44354.
- Public GitHub metadata fetched now: repo created2026-09-13, pushed2026-09-27; this predates our overnight run. No need to infer date from current visibility alone: URL already present in our archived board is stronger evidence of discoverability.

## Work already performed
Read README, refreshed official live CSV, inspected archived board row and search report. No new model training or submissions. No controlled test of whether including this method would change our leaderboard score.

## Questions for independent assessment
1. What explanation of the omission and its consequences is warranted by these artifacts?
2. Which distinctions matter when answering the user's claim about the best open result, without minimizing the omission or claiming untested performance effects?

## Known missing or inaccessible information
No full historic public ranking archive or original stir_bar training code/OOF/split IDs. No evidence that its whole method could be exactly reproduced or that our poor score has one established cause.

## Codex position
withheld for independent first-round assessment.

## Confidentiality check
No secrets, credentials, private keys, .env contents or unnecessary personal data are included.
