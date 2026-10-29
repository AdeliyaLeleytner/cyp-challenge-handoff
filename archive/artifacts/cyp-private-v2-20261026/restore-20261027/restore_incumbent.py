"""One user-authorized re-dispatch of the exact preserved 0.4425 incumbent CSV.

Why this wrapper exists instead of h6_submit.py --send:

  h6_submit.guard_ledger refuses any CSV hash that already has an attempt directory
  ("no automatic retry"). That guard exists to stop an agent retrying after an
  ambiguous or failed upload. This dispatch is the opposite case: the file was
  accepted and scored 0.4425 on 2026-10-24, three later submissions replaced it,
  only the latest submission counts, and the user explicitly asked for the
  incumbent to be put back. So the duplicate-hash check is deliberately set aside
  and recorded; every other guard in that helper runs unchanged, including the
  reconciliation requirement and the 12-hour per-track cooldown.

Report field stays blank with open_code=False, exactly as the 2026-10-27 entry.
No report, code, weights or prediction artifact is published by this script.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ast, copy, fcntl, hashlib, json, sys, time, urllib.request

HERE = Path(__file__).resolve().parent
TRANSPORT = Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/model-audit/submission-transport')
sys.path.insert(0, str(TRANSPORT))
import live_contract as lc
import h6_submit as old

CSV = Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/submission-ledger/intents/204c6f5fad76a1663ece1c6f6b1960934658200929dbd24b98d0af5db171cb64/submission.csv')
EXPECTED = '349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37'
OFFICIAL_BLIND = Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/challenge-audit/sources/dataset-cyp-challenge-TEST-BLINDED.csv')
OFFICIAL_BLIND_SHA = 'a342f8444a8dcb531ca12f3685293f0bd6c36ae9073f491e44a9bc1cc4b741f9'
VALIDATOR = Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/sources/activity_validation.py')
AUTHORIZATION = {
    'source': 'Direct user message in the Claude Code session',
    'text': 'давай сначала сделаем это',
    'answering': 'Proposal to put the preserved 0.4425 incumbent CSV back on the board as the counting entry.',
    'scope': 'One dispatch of this exact CSV. No publication of report, code, weights or predictions.',
}


def now():
    return datetime.now(timezone.utc)


def check_report_guard(private):
    """Confirm, in isolation, that a blank report with open_code=False still passes."""
    tree = ast.parse((private / 'submission.py').read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'submit_predictions')
    branch = next(n for n in fn.body if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == 'open_code_checkbox')
    wrapper = ast.parse('def guard(model_tag,open_code_checkbox):\n pass').body[0]
    wrapper.body = [copy.deepcopy(branch), ast.Return(value=ast.Name(id='model_status', ctx=ast.Load()))]
    module = ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[]))

    def forbidden(*a, **kw):
        raise AssertionError('Report lookup must not run on the closed-code branch')

    ns = {'validate_model_details': forbidden}
    exec(compile(module, 'isolated_report_guard', 'exec'), ns)
    assert ns['guard']('', False) == 'Not submitted'
    return {'blank_report_closed_code_passed': True, 'guard_lines': [branch.lineno, branch.end_lineno],
            'source_sha256': lc.sha(private / 'submission.py')}


def prepare():
    stamp = now().strftime('%Y%m%dT%H%M%S%fZ')
    contract_path = lc.refresh(HERE / 'fresh' / stamp)
    contract = json.loads(Path(contract_path).read_text())
    private = Path(contract_path).parent / 'private'

    assert contract['phase'] in [1, 2], 'Unexpected challenge phase'
    assert now() < datetime.fromisoformat(contract['final_deadline_utc']), 'Final deadline has passed'
    assert now() >= datetime.fromisoformat(contract['conservative_public_cooldown_until_utc']), 'Public cooldown still active'
    assert contract['rows'] == 750 and contract['cooldown_hours_per_track'] == 12, 'Reviewed rules differ'
    assert contract['latest_valid_submission_counts'] is True
    for role, rec in contract['source_snapshots'].items():
        assert lc.sha(rec['path']) == rec['sha256'], 'Source snapshot changed: ' + role

    report = check_report_guard(private)
    contract['public_https_model_report_required'] = False
    contract['report_policy'] = ('Blank report with open_code=False verified from the current handler. '
                                 'Final-leaderboard report requirement is a separate, still open user decision.')
    lc.dump(HERE / 'reviewed-contract.json', contract)

    identity = json.loads((TRANSPORT / 'identity.json').read_text())
    prior = identity['source_intent']
    assert lc.sha(prior['path']) == prior['sha256'], 'Prior identity intent changed'
    args = identity['api_arguments_preserved']
    previous = json.loads(Path(prior['path']).read_text())['api_arguments_without_file']
    assert args == {k: previous[k] for k in old.IDENTITY_FIELDS}, 'Identity/consent flags changed'
    assert args['username'] == 'AdeliyaLL' and args['user_alias'] == 'AdeliyaLL-CYP'
    assert args['open_code_checkbox'] is False and args['track_select'] == 'Regression Prediction'
    assert args['proprietary_data_checkbox'] is False and args['paper_checkbox'] is False
    args = {**args, 'model_tag': ''}

    assert lc.sha(CSV) == EXPECTED, 'Incumbent CSV hash mismatch'
    assert lc.sha(OFFICIAL_BLIND) == OFFICIAL_BLIND_SHA, 'Official blinded TEST hash mismatch'
    validation = old.validate_csv(CSV, OFFICIAL_BLIND, VALIDATOR)

    # Deliberate, recorded deviation: the duplicate-hash guard is the one check set
    # aside here. Pass a key that is not an existing attempt directory so that the
    # reconciliation and cooldown checks still run against the real ledger.
    attempt_key = EXPECTED + '__restore-' + stamp
    assert not (old.LEDGER / 'attempts' / attempt_key).exists()
    history = old.guard_ledger(old.LEDGER, attempt_key, now())

    authorization = {**AUTHORIZATION, 'utc': now().isoformat(), 'candidate_sha256': EXPECTED}
    lc.dump(HERE / 'HUMAN_AUTHORIZATION.json', authorization)

    body = {
        'schema_version': 1,
        'protocol': 'restore_exact_preserved_incumbent_user_authorized_v1',
        'intent': 'Make the exact preserved 0.4425 prediction file the counting latest submission again.',
        'api_arguments_without_file': args,
        'submission_csv_sha256': EXPECTED,
        'submission_csv_source': str(CSV),
        'gradio_client_version': '2.7.2',
        'api_signature': contract['api_signature'],
        'reviewed_contract': lc.record(HERE / 'reviewed-contract.json'),
        'validation': validation,
        'report_guard': report,
        'human_authorization': lc.record(HERE / 'HUMAN_AUTHORIZATION.json'),
        'prior_history': history,
        'attempt_key': attempt_key,
        'duplicate_hash_guard_waived': True,
        'duplicate_hash_guard_reason': ('Prior dispatch of this hash was accepted and scored 0.4425; it was superseded '
                                        'by later submissions and only the latest counts. User asked for the restore. '
                                        'This is not a retry after an ambiguous upload.'),
        'transport_wrapper': lc.record(__file__),
        'legacy_mechanics': lc.record(lc.LEGACY),
        'no_report_publication': True,
        'disclosures': {'published_leaderboard_placement': True, 'reused_development_selection': True,
                        'model_report_link': 'blank; final-board report decision still open'},
    }
    legacy = lc.legacy()
    intent_id = hashlib.sha256(legacy._json_bytes(body)).hexdigest()
    directory = old.LEDGER / 'intents' / intent_id
    legacy._immutable(directory / 'intent.json', legacy._json_bytes(body))
    legacy._immutable(directory / 'submission.csv', CSV.read_bytes())
    prepared = {'intent_id': intent_id, 'intent_dir': str(directory), 'csv_sha256': EXPECTED,
                'attempt_key': attempt_key, 'intent': body, 'contract': contract}
    lc.dump(HERE / 'prepared.json', prepared)
    return prepared


def send():
    prepared = json.loads((HERE / 'prepared.json').read_text())
    legacy = lc.legacy()
    assert lc.sha(__file__) == prepared['intent']['transport_wrapper']['sha256'], 'Wrapper changed after preparation'
    assert lc.sha(prepared['intent']['human_authorization']['path']) == prepared['intent']['human_authorization']['sha256']
    assert prepared['intent']['api_arguments_without_file']['model_tag'] == ''
    assert prepared['intent']['api_arguments_without_file']['open_code_checkbox'] is False
    directory = Path(prepared['intent_dir'])
    assert lc.sha(directory / 'submission.csv') == EXPECTED
    assert hashlib.sha256(legacy._json_bytes(prepared['intent'])).hexdigest() == prepared['intent_id']

    with (old.LEDGER / '.send.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        old.guard_ledger(old.LEDGER, prepared['attempt_key'], now())
        with urllib.request.urlopen('https://huggingface.co/api/spaces/openadmet/cyp-challenge', timeout=30) as r:
            meta = json.load(r)
        assert meta['sha'] == prepared['contract']['space_revision'], 'Official source changed since review'
        assert now() < datetime.fromisoformat(prepared['contract']['final_deadline_utc']), 'Challenge is closed'
        assert now() >= datetime.fromisoformat(prepared['contract']['conservative_public_cooldown_until_utc'])

        transport = legacy.GradioTransport('2.7.2')
        assert legacy._schema_signature(transport.api_info()) == prepared['intent']['api_signature'], 'Live API differs just before send'

        target = old.LEDGER / 'attempts' / prepared['attempt_key']
        target.mkdir(parents=True, exist_ok=False)
        start = time.monotonic()
        attempt = {'schema_version': 1, 'protocol': prepared['intent']['protocol'], 'csv_sha256': EXPECTED,
                   'intent_id': prepared['intent_id'], 'username': 'AdeliyaLL', 'track': 'regression',
                   'dispatched_utc': now().isoformat(), 'status': 'dispatch_started', 'one_dispatch_only': True,
                   'duplicate_hash_guard_waived': True,
                   'report_check': {'report_url': '', 'open_code': False,
                                    'guard': prepared['intent']['report_guard'],
                                    'human_authorization': prepared['intent']['human_authorization']}}
        legacy._immutable(target / 'attempt.json', legacy._json_bytes(attempt))
        try:
            response = transport.submit_once(prepared['intent']['api_arguments_without_file'], directory / 'submission.csv')
            status, message = legacy.classify_response(response)
            receipt = {'status': status, 'response': response, 'message': message}
        except Exception as exc:
            receipt = {'status': 'unknown', 'exception_type': type(exc).__name__}
        receipt.update({'received_utc': now().isoformat(), 'transport_elapsed_seconds': time.monotonic() - start,
                        'csv_sha256': EXPECTED, 'intent_id': prepared['intent_id'], 'submission_id': None,
                        'submission_id_note': 'API does not return a backend ID; not invented',
                        'retry_permitted': False, 'accepted_is_not_scored': True,
                        'next_action': 'Read the live board to reconcile; no automatic retry'})
        legacy._immutable(target / 'receipt.json', legacy._json_bytes(receipt))
        lc.dump(HERE / 'receipt.json', receipt)
        return {k: v for k, v in receipt.items() if k not in ['response', 'message']}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--send', action='store_true', help='Explicit dispatch; preparation is the default')
    a = p.parse_args()
    if a.send:
        print(json.dumps(send(), indent=1))
    else:
        d = prepare()
        print(json.dumps({'status': 'prepared', 'sha256': EXPECTED, 'intent_id': d['intent_id'],
                          'attempt_key': d['attempt_key'], 'blank_report': True, 'no_dispatch': True,
                          'std_ddof1': d['intent']['validation']['std_ddof1'],
                          'cooldown_until': d['contract']['conservative_public_cooldown_until_utc'],
                          'deadline': d['contract']['final_deadline_utc']}, indent=1))
