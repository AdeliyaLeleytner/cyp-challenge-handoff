# Public-method omission audit — 2026-10-24

The user's linked repository is a relevant public method write-up and was omitted from the campaign's documented source review. The URL was already in our pre-submission leaderboard snapshot, so this was a discovery/triage omission, not a newly appeared source.

Evidence:
- `sources/presend-20261023T2345/leaderboard-live.csv`: stir_bar, rank27, MA-ST-RAE0.443539995892439, Open Code=No, exact GitHub URL.
- `DEEPRESEARCH.md`, final section: reference selection explicitly used strongest declared Open Code entry.
- `notes/presend-20261023T2345.md`: distinguished the flag from availability of public material, but that distinction did not become a complete method-report review.
- `official_results/20261024T084528Z/leaderboard.csv`: stir_bar rank29,0.443539995892439; briford rank24,0.4377997714479094. These are comparable live regression scores. They do not establish a historical best-public ranking.
- `sources/lachrymator-README-20261024.md`: current README fetched via GitHub connector. Explicitly write-up only, no training code. Historical best live rank13 and interim rank28 are different observations; interim macroST-RAE0.465 is not the current live score.

Consequences for claims:
1. Briford was the strongest declared Open Code=Yes entry in the checked board. This must not be broadened to an exhaustive survey of public methods/write-ups.
2. The user's repository should have been inspected before concluding source coverage or choosing all experimental directions. Its Open Code=No flag is not a valid exclusion from a methods review.
3. Completed configurations do not include Mitra, test-neighbour property-only augmentation, or the complete reported sequence of public-bioactivity pretraining followed by challenge fine-tuning across diverse backbones. Having tried some of the same model families does not reproduce that pipeline.
4. The current repository does not supply original training code/OOF/fold IDs sufficient for an exact reproduction. This limits direct rerunning but does not excuse omitting its method.
5. There is no controlled evidence that this omission caused the .7521205 submitted score, or that adopting its recipe would outperform the existing candidate. No new compute or submission was launched in this audit.

Correction to review process: inspect public method-report links independently of the Open Code flag; track public write-up, executable code, weights, data and split availability separately, and compare ranks only within the same board/track/date.

Independent advisor: claude-opus-5 via automatic fallback, consultation20261024T084622Z-7cb1fc13. Suggested scanning additional No-flagged URLs. Root verified rasayan-labs has a stronger live score but its linked GitHub repository is empty, so no claim of an available stronger public method is supported there. Scigantic URL returned a page title but no readable web-tool content; method availability was not established. Advice does not substitute for these source checks.
