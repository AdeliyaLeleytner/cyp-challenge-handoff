# TDI submission preflight — 24 October 2026

Read-only inspection only. No file uploaded, no submit call, no remote state mutation. User condition remains: submit an independently evaluated improved candidate, not merely any successfully trained file.

## Current official contract

- Live Space revision **`7f3873d820029457d722da25dac088a0d64c9fcf`**, unchanged from the direct-inhibition reproduction review. Sources pinned from that revision, not unversioned main. Live `/gradio_api/info` and `/config` saved alongside source snapshots.
- Tutorial revision **`832ae6d6447b07c2c71059de34d07f1130388247`**. Pinned official `validation/tdi_validation.py` SHA256 **`e343dc779076b9df302621b66bb1b5ca1a1a19b26e16614d674f4a174d4193ad`**.
- `CURRENT_PHASE=2`, `CLASSIFICATION_ACTIVE=True`, classification choice present in live API. Deadline **3 November 2026,23:59UTC = 4 November,02:59 Moscow**. Recheck phase/source/API/deadline immediately before eventual dispatch; current handler primarily gates UI by phase and does not itself prove calendar eligibility.
- Backend tracks are independent. Classification cooldown looks up `submissions/classification/<safe_username>/...`, regression uses a separate prefix. **One TDI submission per12hours**; the direct-inhibition submission does not start that clock. Same username/alias is correct and keeps the same team. One account perteam; latest valid entry counts.
- File: CSV or Parquet,750rows, identifiers `SMILES`,`Molecule_Name`, predictions `CYP2D6_is_TDI`,`CYP3A4_is_TDI`. Predictions must be binary, not probabilities, no missing values, **both classes present for each endpoint**. No regression standard-deviation check belongs here. Preserve exact official ID→SMILES mapping and row order; stronger local exact-four-column/unique-ID checks are appropriate.
- Tutorial validator checks binary encodings, missing/duplicate IDs and expected IDs, but **does not enforce both predicted classes** or exact ID→SMILES pairing. Add those current-Space/mapping checks separately. Numeric0/1 or pandas Boolean CSV True/False meet current server parser; do not rely on arbitrary normalized strings accepted by the more permissive tutorial.
- `/submit_predictions` has exactly13arguments in this order: `username, user_alias, anon_checkbox, participant_name, discord_username, email, affiliation, model_tag, paper_checkbox, proprietary_data_checkbox, open_code_checkbox, track_select, file_input`. File is `gradio_client.handle_file(path)` as13thargument. Correct backend selector **`Classification Prediction`**, not the UI leaderboard title `TDI Prediction (Classification)`.
- Caller identity/disclosures: usernameAdeliyaLL,aliasAdeliyaLL-CYP,anonymousTrue,optionalidentityfieldsblank,paperFalse,proprietaryFalse,openCodeFalse. Source template is `../sources/submission-preflight/intended-arguments-template.json`. Actual method tag must identify the final trained recipe; placeholder is not a sendable value.
- A reachable HTTPS method report is required by deadline for final eligibility. With OpenCodeFalse, current server accepts a nonempty description without validating aURL, so a live submission is possible before public report release. This is NOT permission to claim code alreadypublic, and a description alone does not fulfill final report requirement. Prepare report independently; don't pretend borrowed public source URL represents our trained improved method.
- Acceptance text: `Submission received from ... for the Classification Prediction track. Your predictions are being processed ... within 2 hours.` It is acceptance/pending, not scoring. The endpoint does not return a submissionID. Exact delay is unknown until observed.

Source pointers: `submission.py`400-447signature;547-585classificationvalidation/cooldown;290-340pertracklookup;647-650receipt;165-170finalreport; `config.py`14-15phase/cooldown,74-97schema,319-327deadline,349-356independenttracks/teamrule.

## Exact safe reuse of previous transport

Existing audited file: `/Users/adeliyaleleytner/autoresearch-runs/cyp-briford-reproduction-20261024/package/dispatch_runtime/night/submit_candidate.py`. SHA256 `936bf402652bc2975a30a9d05430ff662b63a585500a3d96df3c11235f3b8dd7`.

**Do not invoke its `prepare`, CLI `main`, `_check_gate`, `_check_final_provenance` or `_validate_csv` for TDI.** They encode four regression targets, briford members, negative ST-RAE deltas and variance rules. Reusing those would falsely qualify or reject classification.

Use a small reviewed TDI preparation adapter plus the same transport/one-attempt machinery:

1. Copy unchanged pure helpers `_now`,`_sha_bytes`,`_sha`,`_json_bytes`,`_immutable`,`_record`, `GradioTransport`, `classify_response` and `_guard_ledger` into the TDI submission module, preserving provenance hash. `_schema_signature` keeps the same13parameter/component/default check but must explicitly require **Classification Prediction** in live track choices.
2. Adapt `send_prepared` only where it writes the attempt's hardcoded `'track':'regression'`: use validated `'track':'classification'`, derived from/checked against `body['api_arguments_without_file']['track_select']`. Otherwise preserve lock, ledger guard, immutable bytes, live-signature equality, single dispatch and no retry behavior. Calling the old function verbatim sends arguments supplied by intent but records the WRONG track; do not do that.
3. TDI preparation validates actual plan qualification: both frozen own750/briford529 cohorts, matched42/142runs, same endpoints/rows, missing-mask semantics, candidate/referenceidentity, positive macro-MCC deltas as frozen in PLAN (no regressionnegative-delta or arbitrarysignificancecriterion), train-only threshold/ensemble selection, provenance of full refit and recipe match. It records finite per-endpoint MCC/confusion/positivecounts and hashes. If nothing qualifies, no intent/send.
4. Freeze real finalCSV, officialTESTmapping, pinnedTDIvalidator, recipe, qualificationcertificate, full-fitrunprovenance, API/source hashes and installedgradio-client version into immutable `intent.json` and `submission.csv`. Prepared object retains existing keys `intent_id`,`intent_dir`,`csv_sha256`,`intent`; `intent_id=sha256(canonical_json(intent))`. `api_signature` must match live `view_api` representation exactly.
5. Use **only `/Users/adeliyaleleytner/autoresearch-runs/cyp-tdi-20261024/submission-ledger`** for TDI. Never share the old regressionledger: `_guard_ledger` scans every attempt and otherwise incorrectly blocks an independent track. Add explicit ledgertrack metadata to prevent accidental mixed use. Do not erase/ignore an existingTDIattempt.
6. Preserve local exclusive sendlock, globalCSVhash duplicate guard, accepted/ambiguous reconciliation requirement,12hcooldown, immutable attemptbeforetransport, sanitizedexceptiontype-onlyerrorlogging. Accepted/unknown are not automatically retried. A timeout cannot establish nonreceipt. Rejected response is recorded and diagnosed, not blindly resent.
7. After acceptance, check official classificationmacroCSV `/partial_5` and per-endpointCSV `/partial_6`,`/partial_7` only after verifying currentcomponentmapping. Match alias **and exactuniqueTDI model_tag and submissionminute at/after dispatch**. Save fulldownloadedCSV/hash, matchedrow and timestamp; reconcile attemptonlywithactualevidence. Report macroMCC andendpointMCC, not old regressionrank. Waiting2hoursis not evidence of a scoredresult.

## Artifacts

Source snapshots and hashes: `../sources/submission-preflight/manifest.json`; `live-api-info.json`; `live-config.json`; pinned `app.py`,`config.py`,`submission.py`,`models.py`,`utils.py`,`tdi_validation.py`. General official links:

- [Challenge UI](https://huggingface.co/spaces/openadmet/cyp-challenge)
- [Pinned Space submission handler](https://huggingface.co/spaces/openadmet/cyp-challenge/blob/7f3873d820029457d722da25dac088a0d64c9fcf/submission.py)
- [Pinned rules/config](https://huggingface.co/spaces/openadmet/cyp-challenge/blob/7f3873d820029457d722da25dac088a0d64c9fcf/config.py)
- [Pinned official TDI validator](https://github.com/OpenADMET/CYP-Challenge-Tutorial/blob/832ae6d6447b07c2c71059de34d07f1130388247/validation/tdi_validation.py)
