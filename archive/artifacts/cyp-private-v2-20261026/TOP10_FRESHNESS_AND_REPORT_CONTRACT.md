# Top10 freshness and report contract — read-only audit

**No new usable top10 method/weights were found in the two linked reports. The current LIVE handler does not require a public report when the open-code flag is false. The final-report requirement remains stated in the official UI.** These are separate facts; this audit authorizes neither a submission nor publication.

## Top10 public materials

The supplied LIVE Direct Inhibition snapshot at2026-10-26T16:52:43UTC has a top10cutoffMA-ST-RAE0.4183. Eight entries say “Not submitted”; the only report links areRubyy(rank4,0.3922) andrasayan-labs(rank8,0.4122).

| Linked entry | Fresh read | Usable additions versus SOURCE_INVENTORY |
|---|---|---|
| [Rubyy HF card](https://huggingface.co/basedonAI/openadmet-cyp-inhibition-rubyy/blob/main/README.md) | Public revision`e105d251cb04058e87588976253c4f934fdf377d`, unchanged. Repository has onlyREADME.md and.gitattributes. Card remains a generic CYP-prediction placeholder. | No methods, training recipe, model weights or inference implementation. |
| [rasayan-cyp](https://github.com/whis9/rasayan-cyp) | Public metadata size0; last pushed2026-09-19T15:21:18Z. Git-tree API returns409 explicitly stating the repository is empty. | No code/method/weight artifact. A newer leaderboard score does not imply public implementation was added. |

Across all35report-bearing entries in the supplied snapshot, no other participant report URL was added, removed or changed versus the2026-10-26T11:08:57SOURCE_INVENTORY census. Our own prior deleted report appears only as stale leaderboard metadata; the inventory intentionally stored its URL asnull. That apparent difference is a privacy redaction, not a new report. It was not fetched or republished. Other public reports were not broadly re-audited because no link changed and this task was bounded to the two top10leads.

## Actual current submission validation

Fresh official Space revision:`059ab0d96a539616ba7d0f805a2e7d1808703192`, CURRENT_PHASE2. Evidence is the public [submission handler](https://huggingface.co/spaces/openadmet/cyp-challenge/blob/059ab0d96a539616ba7d0f805a2e7d1808703192/submission.py), not an inference from missing leaderboard links.

- `submission.py:489–499`: report validation runs only when `open_code_checkbox` is true. If false, an empty `model_tag` is stored as “Not submitted”; the handler continues to track/file validation.
- When open-code is true, `validate_model_details` rejects an empty link or an invalid/unreachable URL. [utils.py:471–482](https://huggingface.co/spaces/openadmet/cyp-challenge/blob/059ab0d96a539616ba7d0f805a2e7d1808703192/utils.py) requires thehttps prefix and performs a reachability check.
- The subsequent `Submission` metadata receives that report status and is persisted through the normal path. There is no additional unconditional nonempty-report check in the inspected handler.
- Current Gradio API metadata still requires the **model_tag argument to be supplied**: it has no default. That is not a requirement for a nonempty URL. A future authorized client must pass an empty string rather than simply omit the parameter when using the no-report path. The open-code argument defaults tofalse.
- The leaderboard formatter explicitly renders missing/empty report values as “Not submitted.” A visible link is metadata, not evidence that a substantive report or open implementation was reviewed.

The exact report-validation AST branch and its original URL helper were also isolated and exercised **locally**, with a stub URL checker: blank+open-codefalse→“Not submitted”; blank+true→error; reachablehttps+true→accepted link; unreachable orhttp+true→error. This did not import or call the full submission module, contact the submission endpoint, read/upload a prediction file, access storage or make network calls. See`report-guard-evidence.json` and`verify_report_guard.py` in the evidence folder. This verifies the public handler logic; it is not a live submission test or a guarantee that every otherwise invalid file will be accepted.

## LIVE versus FINAL eligibility

The current form text at`submission.py:166–170` states that a method report is required before the deadline to appear on the final leaderboard, and immediately required when declaring open-source code. The`Submission.model_report_link` field defaults toempty and its documentation likewise describes a before-deadline requirement. The FAQ says code openness is not mandatory for ordinary leaderboard ranking; that does not waive a separate method-report requirement.

Current deadline text isNovember3,2026at23:59UTC. The public Space renders final/interim tables from static results; the inspected repository does **not** expose the final selection/eligibility-generation pipeline. Consequently:

| Question | Supported conclusion |
|---|---|
| Does the current LIVE handler universally require a publichttpsreport? | **No.** Report validation is conditional onopen-code=true. |
| Can blankreport+open-code=false pass the report-specific validation? | **Yes**, by explicit code path; other submission checks still apply. |
| Is a report required for final inclusion according to the official interface? | **Yes**, before the deadline. |
| Has automatic FINAL backend enforcement been verified? | **No**; final eligibility production is not exposed in this Space source. |
| Does this permit bypassing a stated final rule? | **No**. Optional LIVE metadata and final eligibility are distinct. |
| Does this audit authorize posting our methods or dispatching predictions? | **No**. User privacy instructions and current no-dispatch scope remain. |

A later LIVE attempt, if separately authorized, need not publish a report merely because our earlier helper demanded one. A final-method disclosure decision would still require reconciling the stated rules with the user’s privacy instruction. Open-code=false must accurately reflect the submitted method’s status; no fabricated report or misleading disclosure is suggested.

## Correction to our earlier helper assumption

Our local`submission-transport/live_contract.py:46` hardcoded`public_https_model_report_required=True` without reflecting the conditional backend branch. That is an overstrict local assumption, **not the current unconditional LIVE requirement**. `h6_submit.py` subsequently enforces a public-report receipt from that local policy. Historical files/receipts were not edited here.

A future separately authorized transport update should distinguish: required API argument; optional empty report for closed-code LIVE entries; required reachablehttpsreport when declaring open code; stated final-report eligibility; unverified final enforcement; and separate publication authorization. It should preserve existing identity/consent flags and never infer permission to publish. This report is evidence for such an update, not a patch or dispatch.

## Evidence and scope

Evidence folder:`leaderboard-target/freshness-20261026/` contains fresh Space/model/repository metadata, source files, API info, full Rubyy card, empty-repository response, URL/time/status/SHA256fetch ledger, report-link comparison, isolated guard checks and evidence manifest. The supplied16:52snapshot is preserved and bound rather than silently replaced with a later score snapshot. No scientific literature search, model run, report upload, organizer message or leaderboard submission occurred.
