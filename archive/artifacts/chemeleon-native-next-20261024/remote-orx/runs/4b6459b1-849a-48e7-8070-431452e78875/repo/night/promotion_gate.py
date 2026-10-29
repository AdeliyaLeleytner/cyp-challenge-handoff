"""Artifact-only promotion certificate. Never trains, submits or publishes.

The root builds a manifest from actual completed ORX results. Every supplied
artifact is SHA-256 checked; source status evidence must contain ORX state=done.
Passing means observed improvement on two reused cohorts, not statistical proof.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

import numpy as np
import pandas as pd

from .evaluation import score, compare
from .reference import CANONICAL

COHORTS = ('own750', 'briford529')
SEEDS = ('42', '142')
REFERENCE_MEMBERS = ('union18', 'mtaux8', '2d6isoform6', '2d6single')


class GateBlocked(ValueError):
    pass


def _digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _checked_asset(record, base, label, evidence):
    if not isinstance(record, dict) or not record.get('path'):
        raise GateBlocked(f'{label}: missing artifact path/hash record')
    expected = record.get('sha256', '')
    if not isinstance(expected, str) or not re.fullmatch('[a-fA-F0-9]{64}', expected):
        raise GateBlocked(f'{label}: explicit SHA-256 required')
    path = Path(record['path']).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if not path.is_file():
        raise GateBlocked(f'{label}: artifact is not available: {path}')
    actual = _digest(path)
    if actual != expected.lower():
        raise GateBlocked(f'{label}: SHA-256 mismatch for {path}')
    evidence[label] = {'path': str(path), 'sha256': actual, 'bytes': path.stat().st_size}
    return path


def _unique_ids(values, label):
    if any(pd.isna(x) for x in values):
        raise GateBlocked(f'{label}: null IDs')
    ids = [str(x) for x in values]
    if len(ids) != len(set(ids)) or any(not x for x in ids):
        raise GateBlocked(f'{label}: duplicate or empty IDs')
    return ids


def _recipe(value, label):
    if not isinstance(value, list) or len(value) != 4 or set(value) != set(REFERENCE_MEMBERS):
        raise GateBlocked(f'{label}: reference must declare exactly the four historical recipe members')


def _raw_done(raw, run_id, label):
    # Accept a direct ORX run object or the common {run:{...}} envelope only.
    run = raw.get('run', raw)
    if not isinstance(run, dict) or run.get('status') != 'done':
        raise GateBlocked(f'{label}: raw ORX evidence must have terminal success status=done')
    actual_id = run.get('run_id', run.get('id'))
    if str(actual_id) != str(run_id):
        raise GateBlocked(f'{label}: raw ORX run ID does not match the provenance source_run')
    if run.get('exit_code') not in (None, 0):
        raise GateBlocked(f'{label}: nonzero run exit code')


def _provenance(entry, model, cohort, seed, role, base, evidence):
    label = f'{role}/{cohort}/seed{seed}'
    if entry.get('run_status') not in ('completed', 'done'):
        raise GateBlocked(f'{label}: prediction run_status is not completed/done')
    path = _checked_asset(entry.get('provenance'), base, label+'/provenance', evidence)
    provenance = json.loads(path.read_text())
    expected = {'model_name': model['name'], 'cohort': cohort, 'seed': seed,
                'prediction_sha256': entry['sha256'].lower()}
    for key, value in expected.items():
        actual = str(provenance.get(key)) if key == 'seed' else provenance.get(key)
        if actual != value:
            raise GateBlocked(f'{label}: provenance {key} mismatch')
    if provenance.get('status') not in ('completed', 'done'):
        raise GateBlocked(f'{label}: provenance is not completed/done')
    if role == 'reference':
        _recipe(provenance.get('recipe_members'), label+'/provenance')
    sources = provenance.get('source_runs')
    if not isinstance(sources, list) or not sources:
        raise GateBlocked(f'{label}: completed ORX source_runs evidence required')
    source_ids = []
    for i, source in enumerate(sources):
        source_label = label+f'/source_run{i}'
        if not source.get('run_id') or source.get('status') not in ('done', 'completed'):
            raise GateBlocked(f'{source_label}: source run ID and done/completed state required')
        status_path = _checked_asset(source.get('evidence'), base, source_label, evidence)
        _raw_done(json.loads(status_path.read_text()), source['run_id'], source_label)
        source_ids.append(str(source['run_id']))
    return {'source_run_ids': source_ids, 'provenance_sha256': evidence[label+'/provenance']['sha256']}


def _model_predictions(model, role, frozen, base, evidence):
    if not isinstance(model, dict) or not isinstance(model.get('name'), str) or not model['name']:
        raise GateBlocked(f'{role}: explicit model name required')
    if role == 'reference':
        if model['name'] != 'briford_reference':
            raise GateBlocked('Reference must be named briford_reference')
        _recipe(model.get('recipe_members'), 'reference')
    records = model.get('predictions')
    if not isinstance(records, dict) or set(records) != set(COHORTS):
        raise GateBlocked(f'{role}: predictions must contain exactly own750 and briford529')
    predictions, provenance = {}, {}
    for cohort in COHORTS:
        seeds = records[cohort]
        if not isinstance(seeds, dict) or set(map(str, seeds)) != set(SEEDS):
            raise GateBlocked(f'{role}/{cohort}: both matched seeds 42 and 142 are mandatory')
        seeds = {str(k): v for k, v in seeds.items()}
        predictions[cohort], provenance[cohort] = {}, {}
        for seed in SEEDS:
            label = f'{role}/{cohort}/seed{seed}'
            entry = seeds[seed]
            path = _checked_asset(entry, base, label+'/predictions', evidence)
            provenance[cohort][seed] = _provenance(entry, model, cohort, seed, role, base, evidence)
            pred = pd.read_csv(path, dtype={'Molecule_Name': str})
            if not {'Molecule_Name', *CANONICAL} <= set(pred):
                raise GateBlocked(f'{label}: all four canonical target columns are mandatory')
            ids = _unique_ids(pred.Molecule_Name.tolist(), label)
            if set(ids) != set(frozen[cohort]):
                raise GateBlocked(f'{label}: prediction ID set differs from the frozen outer cohort')
            pred = pred.set_index('Molecule_Name').loc[frozen[cohort], CANONICAL].reset_index()
            if not np.isfinite(pred[CANONICAL].to_numpy(float)).all():
                raise GateBlocked(f'{label}: predictions must be finite for every molecule and all four targets')
            predictions[cohort][seed] = pred
    return predictions, provenance


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(x) for x in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def evaluate_gate(manifest, *, base_dir='.', n_bootstrap=2000, bootstrap_seed=42):
    """Return pass/blocked certificate; require paired-seed AND deployed-ensemble gains.

    Input manifest: truth/cohorts {path,sha256}; candidate/reference
    {name,predictions:{cohort:{seed:{path,sha256,run_status,provenance:{path,sha256}}}}}.
    Reference additionally declares recipe_members. Each provenance JSON binds
    model_name/cohort/seed/prediction_sha256 to hashed completed ORX source runs.
    This validates saved evidence; the root is responsible for obtaining truthful
    current ORX status artifacts. No remote state query occurs in this function.
    """
    certificate = {'schema_version': 1, 'status': 'blocked', 'passed': False,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'reasons': [],
        'gate_source_sha256': _digest(Path(__file__).resolve()),
        'criterion': 'BOTH mean paired-seed macro ST-RAE delta AND macro ST-RAE delta of averaged seed42+142 prediction vectors must be strictly below zero on EACH frozen cohort.',
        'criterion_predeclaration': 'The averaged-prediction requirement was added before gate outcomes, to match the planned ten-fold-bag seed42+142 submission ensemble.',
        'required_cohorts': list(COHORTS), 'required_seeds': list(SEEDS), 'targets': list(CANONICAL),
        'bootstrap_is_reporting_only': True, 'automatic_submission': False,
        'evidence_hashes': {}, 'score_table': [], 'comparisons': {}, 'averaged_prediction_scores': {},
        'qualifications': {
            'development_seen': 'These cohorts have been inspected during development; repeated selection can overfit their readouts.',
            'seed_confirmation': 'The second seed measures initialization variability on the same cohorts, not a new independent holdout.',
            'calibration_limits': [
                'Neural inner-OOF checkpoints may be selected using the same inner validation labels.',
                'Calibration cross-fitting over existing OOF predictions is not fully nested base-model cross-validation.',
                'OOF predictions use one inner model per molecule; outer predictions average five models.',
                'Calibration and blend choices must be fitted on development labels only, never these outer labels.'],
            'provenance_limit': 'Hashes bind the supplied artifacts and saved ORX done evidence; this gate does not independently replay training or query remote ORX.',
            'statistical_limit': 'Passing establishes observed improvement under this protocol, not statistical significance or a guarantee on the blinded test.'}}
    try:
        if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
            raise GateBlocked('Manifest schema_version=1 is required')
        if n_bootstrap < 1:
            raise GateBlocked('At least one bootstrap replicate is required for reporting')
        base = Path(base_dir).resolve(); evidence = certificate['evidence_hashes']
        certificate['manifest_sha256'] = hashlib.sha256(json.dumps(manifest, sort_keys=True, allow_nan=False).encode()).hexdigest()
        cp = _checked_asset(manifest.get('cohorts'), base, 'cohorts', evidence)
        tp = _checked_asset(manifest.get('truth'), base, 'truth', evidence)
        cohort_data = json.loads(cp.read_text())['cohorts']
        frozen = {}
        for cohort, expected_n in [('own750', 750), ('briford529', 529)]:
            frozen[cohort] = _unique_ids(cohort_data[cohort]['test_ids'], cohort)
            if len(frozen[cohort]) != expected_n:
                raise GateBlocked(f'{cohort}: expected {expected_n} frozen evaluation IDs')
            if set(frozen[cohort]) & set(map(str, cohort_data[cohort]['train_ids'])):
                raise GateBlocked(f'{cohort}: frozen development/evaluation overlap')
        overlap = len(set(frozen['own750']) & set(frozen['briford529']))
        certificate['qualifications']['holdout_overlap'] = {
            'shared_molecules': overlap, 'expected_campaign_overlap': 143,
            'interpretation': 'The two evaluation cohorts overlap and are not independent replications.'}
        truth = pd.read_csv(tp, dtype={'Molecule_Name': str})
        _unique_ids(truth.Molecule_Name.tolist(), 'truth')
        truth = truth.set_index('Molecule_Name', drop=False)
        candidate, cm = _model_predictions(manifest.get('candidate'), 'candidate', frozen, base, evidence)
        reference, rm = _model_predictions(manifest.get('reference'), 'reference', frozen, base, evidence)
        certificate['candidate_name'] = manifest['candidate']['name']
        certificate['reference_name'] = manifest['reference']['name']
        certificate['reference_recipe_members'] = list(REFERENCE_MEMBERS)
        certificate['prediction_provenance'] = {'candidate': cm, 'reference': rm}
        for cohort in COHORTS:
            y = truth.loc[frozen[cohort]].reset_index(drop=True)
            for seed in SEEDS:
                cs = score(y, candidate[cohort][seed], targets=CANONICAL)
                rs = score(y, reference[cohort][seed], targets=CANONICAL)
                if not cs['defined'] or not rs['defined']:
                    raise GateBlocked(f'{cohort}/seed{seed}: undefined four-target official score')
                certificate['score_table'].append({'cohort': cohort, 'seed': int(seed),
                    'candidate_macro_ST_RAE': cs['macro_ST_RAE'], 'reference_macro_ST_RAE': rs['macro_ST_RAE'],
                    'delta': cs['macro_ST_RAE']-rs['macro_ST_RAE'], 'candidate': cs, 'reference': rs})
            result = compare(y, candidate[cohort], reference[cohort], targets=CANONICAL,
                             n_bootstrap=n_bootstrap, seed=bootstrap_seed)
            delta = result['delta_candidate_minus_reference']
            if not np.isfinite(delta):
                raise GateBlocked(f'{cohort}: nonfinite paired-seed delta')
            certificate['comparisons'][cohort] = result
            if not delta < 0.:
                certificate['reasons'].append(f'{cohort}: mean paired-seed delta {delta:.12g} is not strictly negative')
            candidate_mean = candidate[cohort][SEEDS[0]].copy()
            reference_mean = reference[cohort][SEEDS[0]].copy()
            candidate_mean[CANONICAL] = np.mean([candidate[cohort][s][CANONICAL].to_numpy(float) for s in SEEDS], axis=0)
            reference_mean[CANONICAL] = np.mean([reference[cohort][s][CANONICAL].to_numpy(float) for s in SEEDS], axis=0)
            cm_score = score(y, candidate_mean, targets=CANONICAL)
            rm_score = score(y, reference_mean, targets=CANONICAL)
            ensemble_delta = cm_score['macro_ST_RAE']-rm_score['macro_ST_RAE']
            certificate['averaged_prediction_scores'][cohort] = {
                'candidate':cm_score, 'reference':rm_score, 'delta_candidate_minus_reference':ensemble_delta,
                'aggregation':'Equal mean of seed42 and seed142 vectors, each already averaging its five inner-fold outer predictions.'}
            if not np.isfinite(ensemble_delta) or not ensemble_delta < 0.:
                certificate['reasons'].append(f'{cohort}: averaged-prediction delta {ensemble_delta:.12g} is not strictly negative')
        if not certificate['reasons']:
            certificate.update(status='pass', passed=True)
    except Exception as exc:
        certificate['reasons'].append(f'{type(exc).__name__}: {exc}')
    return _json_safe(certificate)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--n-bootstrap', type=int, default=2000)
    parser.add_argument('--bootstrap-seed', type=int, default=42)
    args = parser.parse_args(argv)
    manifest_path = Path(args.manifest).resolve()
    try:
        manifest = json.loads(manifest_path.read_text())
        certificate = evaluate_gate(manifest, base_dir=manifest_path.parent,
                                    n_bootstrap=args.n_bootstrap, bootstrap_seed=args.bootstrap_seed)
        certificate['manifest_file'] = {'path': str(manifest_path), 'sha256': _digest(manifest_path)}
    except Exception as exc:
        certificate = evaluate_gate({}, base_dir=manifest_path.parent,
                                    n_bootstrap=args.n_bootstrap, bootstrap_seed=args.bootstrap_seed)
        certificate['reasons'] = [f'{type(exc).__name__}: {exc}']
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError('Gate certificates are frozen; use a new output path')
    fd, tmp = tempfile.mkstemp(dir=output.parent, prefix=output.name+'.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(certificate, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
        # Exclusive creation also protects against a concurrent overwrite.
        os.link(tmp, output)
    finally:
        Path(tmp).unlink(missing_ok=True)
    print(json.dumps({'status':certificate['status'], 'certificate':str(output),
                      'reasons':certificate['reasons']}), flush=True)
    return 0 if certificate['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
