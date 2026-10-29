"""TDI-only immutable deployment adapter. Default: verify/prepare, never send.

No training, credential discovery, publication or automatic retry. The reviewed
regression transport is extracted by AST with its single attempt track literal
mechanically changed; regression qualification/CSV code is never executed.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen

import numpy as np
import pandas as pd

SPACE = 'https://openadmet-cyp-challenge.hf.space'
SPACE_REVISION = '7f3873d820029457d722da25dac088a0d64c9fcf'
TUTORIAL_REVISION = '832ae6d6447b07c2c71059de34d07f1130388247'
VALIDATOR_SHA256 = 'e343dc779076b9df302621b66bb1b5ca1a1a19b26e16614d674f4a174d4193ad'
TRANSPORT_PATH = Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-briford-reproduction-20261024/package/dispatch_runtime/night/submit_candidate.py')
TRANSPORT_SHA256 = '936bf402652bc2975a30a9d05430ff662b63a585500a3d96df3c11235f3b8dd7'
OFFICIAL_TEST_MAPPING_SHA256 = '1976cf8d7719a928419e408d87fd2aa6bd0abeee3da3e7ae98169cb557efe738'
TARGETS = ('CYP2D6_is_TDI', 'CYP3A4_is_TDI')
SEEDS = (42, 142)
COHORTS = ('own750', 'briford529', 'full')
HOLDOUT_ID_SHA = {
 'own750': 'befcfc0f85f8a4920afae21a01a0ce0242d5e7e3c5d96a98aca5114d74517504',
 'briford529': 'f5b99359b0752a485b2123a87777fb09b7b3b8b8db60052e63d5468439de2a08',
}
API_NAME = '/submit_predictions'
PARAMETERS = ['username','user_alias','anon_checkbox','participant_name','discord_username','email',
              'affiliation','model_tag','paper_checkbox','proprietary_data_checkbox','open_code_checkbox',
              'track_select','file_input']
DEADLINE = datetime(2026, 11, 3, 23, 59, tzinfo=timezone.utc)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def read_json(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def immutable(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == value, f'Immutable artifact differs: {path}')
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(value)


def _transport_namespace():
    """Extract only reviewed transport helpers; never import regression main/prepare."""
    require(sha(TRANSPORT_PATH) == TRANSPORT_SHA256, 'Reviewed transport source changed')
    names = {'_now','_sha_bytes','_sha','_json_bytes','_immutable','_record',
             '_schema_signature','GradioTransport','classify_response','_guard_ledger','send_prepared'}
    tree = ast.parse(TRANSPORT_PATH.read_text())
    selected = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    require({n.name for n in selected} == names, 'Transport extraction missing reviewed helpers')
    changed = 0
    for node in selected:
        if node.name == 'send_prepared':
            for child in ast.walk(node):
                if isinstance(child, ast.Constant) and child.value == 'regression':
                    child.value = 'classification'; changed += 1
    require(changed == 1, 'Expected exactly one mechanical track literal change')
    namespace = dict(Path=Path, datetime=datetime, timezone=timezone, hashlib=hashlib,
                     json=json, os=os, re=__import__('re'), importlib=__import__('importlib'),
                     SPACE=SPACE, API_NAME=API_NAME, PARAMETERS=PARAMETERS,
                     USERNAME='AdeliyaLL', ALIAS='AdeliyaLL-CYP')
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])),
                 str(TRANSPORT_PATH) + ':transport-only-classification', 'exec'), namespace)
    native_signature = namespace['_schema_signature']
    def signature(info):
        result = native_signature(info)
        require('Classification Prediction' in result['track_choices'], 'Classification track missing from API')
        return result
    namespace['_schema_signature'] = signature
    return namespace


def check_live_contract(campaign_root):
    """Read-only current revision/API/phase/deadline checks; no file upload."""
    require(datetime.now(timezone.utc) < DEADLINE, 'Official submission deadline has passed')
    source_dir = Path(campaign_root) / 'sources/submission-preflight'
    recorded = read_json(source_dir / 'manifest.json')
    require(recorded['hf_space_commit'] == SPACE_REVISION, 'Unreviewed Space revision')
    for name in ('app.py','config.py','submission.py','live-api-info.json'):
        require(sha(source_dir / name) == recorded['source_files'][name]['sha256'], f'Pinned source changed: {name}')
    with urlopen('https://huggingface.co/api/spaces/openadmet/cyp-challenge', timeout=40) as r:
        live = json.load(r)
    require(live.get('sha') == SPACE_REVISION, 'Space source changed; review before upload')
    with urlopen(SPACE + '/gradio_api/info', timeout=40) as r:
        info = json.load(r)
    with urlopen(SPACE + '/config', timeout=40) as r:
        ui = json.load(r)
    constants = {}
    for node in ast.parse((source_dir / 'config.py').read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try: constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (TypeError, ValueError): pass
    require(constants.get('CURRENT_PHASE') in (1, 2) and constants.get('CLASSIFICATION_ACTIVE') is True,
            'TDI submissions are not in an active phase')
    require(constants.get('HOURS_BETWEEN_SUBMISSIONS') == 12, 'Cooldown rule changed')
    require(constants.get('CLASSIFICATION_ENDPOINTS') == list(TARGETS), 'TDI endpoint schema changed')
    require(constants.get('ACTIVITY_DATASET_SIZE') == 750, 'Official row count changed')
    require(any(d.get('api_name') == 'submit_predictions' for d in ui.get('dependencies', [])),
            'Live submission endpoint absent')
    signature = _transport_namespace()['_schema_signature'](info)
    old = _transport_namespace()['_schema_signature'](read_json(source_dir / 'live-api-info.json'))
    require(signature == old, 'Live API differs from reviewed contract')
    return {'space_revision': SPACE_REVISION, 'tutorial_revision': TUTORIAL_REVISION,
            'api_signature': signature, 'checked_utc': datetime.now(timezone.utc).isoformat(),
            'deadline_utc': DEADLINE.isoformat(), 'classification_cooldown_hours': 12}


class Evidence:
    def __init__(self): self.files = {}
    def add(self, path, expected=None):
        p = Path(path).resolve(); digest = sha(p)
        require(expected is None or digest == expected, f'Evidence hash mismatch: {p}')
        self.files[str(p)] = {'path': str(p), 'sha256': digest, 'bytes': p.stat().st_size}
        return p
    def json(self, path, expected=None): return read_json(self.add(path, expected))


def _resolve(path, base):
    p = Path(path).expanduser()
    return p.resolve() if p.is_absolute() else (Path(base) / p).resolve()


def _rows_hash(rows):
    return hashlib.sha256(np.asarray(rows, dtype='<i8').tobytes()).hexdigest()


def _bool_columns(frame):
    arrays = []
    for target in TARGETS:
        require(target in frame, f'Missing TDI target: {target}')
        values = frame[target]
        require(not values.isna().any(), f'Missing TDI prediction: {target}')
        # Match live pandas parser, not more-permissive arbitrary string coercion.
        require(values.isin([0, 1, True, False]).all(), f'Nonbinary prediction: {target}')
        arrays.append(values.to_numpy(dtype=bool))
    return np.column_stack(arrays)


def _score(y, pred, ids):
    y = np.asarray(y, dtype=float); pred = np.asarray(pred, dtype=bool)
    require(y.shape == pred.shape and y.ndim == 2 and y.shape[1] == 2, 'Scoring shape mismatch')
    per = {}
    for j, target in enumerate(TARGETS):
        mask = np.isfinite(y[:, j]); yy = y[mask, j]
        require(len(yy) > 0 and np.isin(yy, [0, 1]).all(), f'Invalid/missing truth for {target}')
        yy = yy.astype(bool); pp = pred[mask, j]
        tp, tn = int(np.sum(yy & pp)), int(np.sum(~yy & ~pp))
        fp, fn = int(np.sum(~yy & pp)), int(np.sum(yy & ~pp))
        den = float((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)) ** .5
        per[target] = {'defined': True, 'mcc': (tp*tn-fp*fn)/den if den else 0.,
                       'n':len(yy), 'tp':tp,'tn':tn,'fp':fp,'fn':fn}
    return {'macro_mcc': float(np.mean([v['mcc'] for v in per.values()])), 'per_target': per,
            'ids': list(ids)}


def _check_reported(actual, reported):
    require(reported.get('defined') is True, 'Reported holdout score is undefined')
    require(np.isclose(actual['macro_mcc'], reported['macro_mcc'], atol=1e-12, rtol=0), 'Reported macro MCC mismatch')
    require(reported['evaluation_input']['ids'] == actual['ids'], 'Reported score IDs misaligned')
    for target in TARGETS:
        for k in ('n', 'tp', 'tn', 'fp', 'fn', 'mcc'):
            require(np.isclose(actual['per_target'][target][k], reported['per_target'][target][k], atol=1e-12, rtol=0),
                    f'Reported {target} {k} mismatch')


def check_best_reference_gate(scores):
    """Candidate must beat every available native reference on BOTH cohorts."""
    comparisons = {}
    for cohort in COHORTS[:2]:
        require(cohort in scores, f'Missing holdout {cohort}')
        values = scores[cohort]
        for name in ('soft_candidate', 'native_reference', 'hauser_native'):
            require(name in values, f'{cohort}: missing required {name} score')
        references = {k: v['macro_mcc'] for k, v in values.items()
                      if k in ('native_reference', 'native_seed42', 'hauser_native')}
        candidate = values['soft_candidate']['macro_mcc']
        require(np.isfinite([candidate, *references.values()]).all(), 'Nonfinite gate score')
        best = max(references, key=references.get)
        delta = candidate - references[best]
        require(delta > 0, f'{cohort}: candidate MCC {candidate:.8f} does not beat best reference {best} {references[best]:.8f}')
        comparisons[cohort] = {'candidate_mcc': candidate, 'reference_mcc': references,
                               'best_reference': best, 'delta_vs_best': delta}
    return comparisons


def _apply_policy(probabilities, policy):
    require(policy['target_order'] == list(TARGETS), 'Policy target order differs')
    require(policy.get('outer_labels_used') is False, 'Policy lacks outer-label exclusion declaration')
    names = policy['models']; result = np.zeros_like(next(iter(probabilities.values())), dtype=float)
    for j, target in enumerate(TARGETS):
        w = np.array([policy['weights'][target][name] for name in names], dtype=float)
        require(np.isfinite(w).all() and np.all(w >= 0) and np.isclose(w.sum(), 1), 'Invalid ensemble weights')
        for name, weight in zip(names, w):
            a = probabilities[name]
            require(np.isfinite(a).all() and np.all((a >= 0) & (a <= 1)), 'Invalid member probabilities')
            result[:, j] += weight * a[:, j]
    thresholds = np.asarray([policy['thresholds'][t] for t in TARGETS], dtype=float)
    require(np.isfinite(thresholds).all() and policy.get('comparison') == '>=', 'Invalid threshold policy')
    return result >= thresholds


def _component(root, prep, cohort, seed, method, dev, query, evidence):
    """Verify saved fold completion, indices and feature provenance for both targets."""
    parts = []
    folds = np.load(evidence.add(prep / (f'folds_native_seed{seed}.npy' if cohort == 'full' else f'cohorts/{cohort}/folds_seed{seed}.npy')), allow_pickle=False)
    require(folds.shape == (len(dev),) and set(folds.tolist()) == set(range(5)), 'Expected five frozen folds')
    for j in range(2):
        path = root / 'results' / cohort / f'seed{seed}' / method / f'target{j}'
        job = evidence.json(path / 'job.json'); done = evidence.json(path / 'complete.json')
        identity = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()
        require(done.get('status') == 'complete' and done.get('job_sha256') == identity, 'Component not complete or job changed')
        for key, value in [('cohort',cohort),('seed',seed),('method',method),('target',j)]:
            require(job.get(key) == value, f'Job mismatch: {key}')
        require(job['input_manifest_sha256'] == sha(prep/'metadata.json'), 'Wrong data manifest in component')
        require(job['embedding_manifest_sha256'] == sha(prep/'embeddings_manifest.json'), 'Wrong embedding manifest in component')
        a = np.load(evidence.add(path/'predictions.npz', done['prediction_sha256']), allow_pickle=False)
        require(np.array_equal(a['dev_indices'], dev) and np.array_equal(a['query_indices'], query), 'Component row indices differ')
        fold_query = []; fold_hard = []; full_query = full_hard = None
        for f in range(6):
            meta = evidence.json(path/f'fit{f}.json'); arr = np.load(evidence.add(path/f'fit{f}.npz',meta['npz_sha256']),allow_pickle=False)
            require(meta['job_sha256'] == identity and meta['fit'] == f, 'Fold job provenance mismatch')
            tr = dev if f == 5 else dev[folds != f]
            va = np.array([],dtype=int) if f == 5 else dev[folds == f]
            require(meta['metadata']['train_rows_sha256'] == _rows_hash(tr), 'Fold training indices mismatch')
            require(meta['metadata']['valid_rows_sha256'] == _rows_hash(va), 'Fold validation indices mismatch')
            if f < 5:
                require(np.array_equal(a['oof'][folds == f], arr['valid_proba']), 'OOF probabilities differ from saved fit')
                require(np.array_equal(a['hard_oof'][folds == f], arr['valid_hard']), 'OOF classes differ from saved fit')
                fold_query.append(arr['query_proba']); fold_hard.append(arr['query_hard'])
            else: full_query, full_hard = arr['query_proba'], arr['query_hard']
        require(np.array_equal(a['query_full'], full_query) and np.array_equal(a['query_full_hard'], full_hard), 'Full-fit predictions differ')
        require(np.array_equal(a['query_bag'], np.mean(fold_query,axis=0)), 'Fold bagged probabilities differ')
        parts.append({k: np.asarray(a[k]) for k in ('oof','hard_oof','query_full','query_full_hard','query_bag')})
    return {k: np.column_stack([a[k] for a in parts]) for k in parts[0]}


def _gnn_component(root, prep, cohort, seed, dev, query, evidence, implementation_sha):
    """Verify a joint two-target, fivefold GNN artifact, including pilot-resumed folds."""
    path=root/'results'/cohort/f'seed{seed}'/'gnn'
    done=evidence.json(path/'complete.json')
    require(done.get('status')=='complete' and done.get('outer_labels_used_for_selection') is False,
            'Joint GNN must be complete with outer-label exclusion')
    require(done.get('query_full_is_fold_bag_alias') is True,'GNN must declare fivefold bag alias, not a sixth fit')
    signature=done['signature']
    require(signature['cohort']==cohort and signature['seed']==seed,'GNN cohort/seed signature mismatch')
    require(signature['foundation_sha256']=='c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651',
            'GNN must use pinned generic foundation, not ADME-adapted encoder')
    require(signature['implementation_sha256']==implementation_sha,'GNN implementation differs from recorded source')
    require(signature['recipe']['targets']==list(TARGETS),'GNN must have exactly the two provided targets')
    require(signature['packages']['chemprop']=='2.2.1','GNN Chemprop version differs from reviewed implementation')
    require(signature['train_csv_sha256']==sha(prep/'train.csv') and signature['test_csv_sha256']==sha(prep/'test.csv'),'GNN training/test tables differ')
    folds=np.load(evidence.add(prep/(f'folds_native_seed{seed}.npy' if cohort=='full' else f'cohorts/{cohort}/folds_seed{seed}.npy')),allow_pickle=False)
    require(folds.shape==(len(dev),) and set(folds.tolist())==set(range(5)),'GNN fivefold mapping missing')
    for name,array in [('dev_indices',dev),('query_indices',query),('folds',folds)]:
        require(signature[name+'_sha256']==hashlib.sha256(array.tobytes()).hexdigest(),'GNN index/fold signature mismatch: '+name)
    require(len(done.get('folds',[]))==5,'GNN requires all five completed folds')
    for rel,digest in done['output_sha256'].items():
        resolved=(path/rel).resolve()
        require(resolved.is_relative_to(path.resolve()),'GNN output manifest escapes artifact directory')
        evidence.add(resolved,digest)
    require(read_json(path/'recipe.json')==signature,'GNN recipe file differs from signature')
    train=pd.read_csv(prep/'train.csv');test=pd.read_csv(prep/'test.csv')
    for name,expected in [('oof',train.iloc[dev]),('query',(test if cohort=='full' else train).iloc[query])]:
        frame=pd.read_csv(path/(name+'_ids.csv'))
        require(frame[['Molecule_Name','SMILES']].astype(str).values.tolist()==expected[['Molecule_Name','SMILES']].astype(str).values.tolist(),
                'GNN '+name+' IDs/SMILES misaligned')
    a=np.load(evidence.add(path/'predictions.npz',done['prediction_sha256']),allow_pickle=False)
    require(np.array_equal(a['dev_indices'],dev) and np.array_equal(a['query_indices'],query),'GNN final index arrays differ')
    assembled=np.full((len(dev),2),np.nan,dtype=np.float32);queries=[]
    for fold in range(5):
        folder=path/f'fold{fold}';meta=evidence.json(folder/'complete.json')
        require(meta==done['folds'][fold] and meta['signature']==signature and meta['fold']==fold,'GNN fold metadata/signature differ')
        require(meta['fit_seed']==seed+fold and meta.get('best_checkpoint_loaded_for_predictions') is True,'GNN best checkpoint/fit seed provenance missing')
        require(isinstance(meta['best_epoch'],int) and 0<=meta['best_epoch']<signature['recipe']['max_epochs'] and np.isfinite(meta['best_val_loss']),
                'GNN best epoch/validation loss invalid')
        require(meta.get('identity_overlap')=={'parent_key':0,'canonical_parent':0},'GNN inner identity overlap audit missing')
        require(meta['best_checkpoint'] in meta['output_sha256'],'GNN selected checkpoint hash missing')
        for rel,digest in meta['output_sha256'].items():
            resolved=(folder/rel).resolve()
            require(resolved.is_relative_to(folder.resolve()),'GNN fold manifest escapes directory')
            evidence.add(resolved,digest)
        require((folder/meta['best_checkpoint']).suffix=='.ckpt','GNN selected checkpoint must be preserved')
        values=np.load(folder/'predictions.npz',allow_pickle=False);valid=np.flatnonzero(folds==fold)
        require(np.array_equal(values['valid_positions'],valid),'GNN local development-fold positions differ')
        require(values['valid_proba'].shape==(len(valid),2) and values['query_proba'].shape==(len(query),2),'GNN fold prediction dimensions differ')
        assembled[valid]=values['valid_proba'];queries.append(values['query_proba'])
    bag=np.mean(np.stack(queries),axis=0)
    require(np.isfinite(assembled).all() and np.isfinite(bag).all() and np.all((assembled>=0)&(assembled<=1)) and np.all((bag>=0)&(bag<=1)),'GNN incomplete/nonprobability outputs')
    require(np.array_equal(a['oof'],assembled) and np.array_equal(a['query_bag'],bag),'GNN OOF/fold mean does not reproduce final arrays')
    require(np.array_equal(a['query_full'],bag) and np.array_equal(a['query_full_hard'],bag>=.5) and np.array_equal(a['hard_oof'],assembled>=.5),
            'GNN full alias/hard predictions differ')
    require(np.array_equal(np.load(path/'oof_proba.npy',allow_pickle=False),assembled) and np.array_equal(np.load(path/'query_proba.npy',allow_pickle=False),bag),
            'GNN standalone and bundled probabilities differ')
    return {k:np.asarray(a[k]) for k in ('oof','hard_oof','query_full','query_full_hard','query_bag')}


def _check_csv(path, test_path, validator_path, evidence):
    require(sha(validator_path) == VALIDATOR_SHA256, 'Official TDI validator changed')
    evidence.add(validator_path); evidence.add(path); evidence.add(test_path)
    test = pd.read_csv(test_path,dtype={'Molecule_Name':str,'SMILES':str})
    df = pd.read_csv(path,dtype={'Molecule_Name':str,'SMILES':str})
    require(len(df)==750 and len(df.columns)==4 and set(df)=={'SMILES','Molecule_Name',*TARGETS}, 'TDI CSV must have exactly 750 rows and four columns')
    for f in (test,df):
        require(len(f)==750 and not f[['Molecule_Name','SMILES']].isna().any().any() and not f.Molecule_Name.duplicated().any(), 'Invalid official/test IDs')
    mapping = sorted(test[['Molecule_Name','SMILES']].values.tolist())
    digest=hashlib.sha256(json.dumps(mapping,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    require(digest==OFFICIAL_TEST_MAPPING_SHA256,'Not the pinned official blinded TEST mapping')
    require(df.Molecule_Name.tolist()==test.Molecule_Name.tolist() and df.SMILES.tolist()==test.SMILES.tolist(), 'CSV IDs/SMILES must match official TEST order exactly')
    pred = _bool_columns(df)
    require(all(len(np.unique(pred[:,j]))==2 for j in range(2)), 'Each TDI endpoint must have both predicted classes')
    spec=importlib.util.spec_from_file_location('_official_tdi_validator',validator_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    valid,errors=module.validate_tdi_submission(path,expected_ids=set(test.Molecule_Name))
    require(valid, f'Official TDI validator failed: {errors}')
    return {'rows':750,'columns':df.columns.tolist(),'positive_counts':pred.sum(axis=0).tolist(),
            'official_validator_passed':True,'official_test_mapping_sha256':digest},pred


def _hauser_predictions(base, prep, cohort, ids, qids, evidence):
    """Original fixed three-repeat algorithm, not artificial seed42/142 copies."""
    hdir=base/'hauser_native'/cohort;complete=evidence.json(hdir/'complete.json')
    require(complete.get('status')=='complete' and complete.get('cohort')==cohort,'Missing complete Hauser native reference')
    for rel in ('metadata.json','oof_ids.csv','oof_proba.npy','query_ids.csv','query_hard.npy','query_proba.npy','nativepolicy.json','thresholds.npy'):
        evidence.add(hdir/rel,complete['files'][rel])
    policy=read_json(hdir/'nativepolicy.json');meta=read_json(hdir/'metadata.json')
    require(policy.get('query_labels_used') is False and meta.get('query_labels_used') is False,'Hauser query-label exclusion missing')
    require(meta['prepared_manifest_sha256']==sha(prep/'metadata.json'),'Hauser data manifest differs')
    require(meta.get('partition_seeds')==[0,1,2] and meta.get('repeats')==3 and meta.get('folds_per_repeat')==5,'Hauser original3x5repeat provenance missing')
    require(pd.read_csv(hdir/'oof_ids.csv').Molecule_Name.astype(str).tolist()==ids,'Hauser OOF IDs misaligned')
    require(pd.read_csv(hdir/'query_ids.csv').Molecule_Name.astype(str).tolist()==qids,'Hauser query IDs misaligned')
    oof=np.load(hdir/'oof_proba.npy',allow_pickle=False)
    prob=np.load(hdir/'query_proba.npy',allow_pickle=False)
    hard=np.load(hdir/'query_hard.npy',allow_pickle=False)
    require(oof.shape==(len(ids),2) and prob.shape==(len(qids),2) and hard.shape==prob.shape,'Hauser prediction dimensions differ')
    require(np.isfinite(oof).all() and np.isfinite(prob).all() and np.all((oof>=0)&(oof<=1)) and np.all((prob>=0)&(prob<=1)),'Invalid Hauser probabilities')
    thresholds=np.array([policy['thresholds'][t] for t in TARGETS])
    require(np.array_equal(thresholds,np.load(hdir/'thresholds.npy',allow_pickle=False)),'Hauser threshold artifacts differ')
    require(np.array_equal(hard,prob>=thresholds),'Hauser predictions not reproduced by frozen thresholds')
    return {'oof':oof,'query_bag':prob,'native_hard':hard}


ASSAY_COLUMNS = ['cyp2d6_pic50_direct_inhibition_pred','cyp2d6_log2fc_pred',
 'cyp2d6_pic50_tdi_condition_pred','cyp2d6_emax_vs_pos_ctrl_direct_inhibition_pred',
 'cyp2d6_pic50_chembl_pred','cyp2d6_max_response_pred']
ASSAY_ALIASES = {
 'own750':['OCNT-0494161','OCNT-1911794','OCNT-1965934','OCNT-2328651','OCNT-2328781','OCNT-2328911'],
 'briford529':['OCNT-1965934','OCNT-2328651'], 'full':['OCNT-0494161','OCNT-1911794'],
}


def _mcc_one(y,p):
    y=np.asarray(y,dtype=bool);p=np.asarray(p,dtype=bool)
    tp=int(np.sum(y&p));tn=int(np.sum(~y&~p));fp=int(np.sum(~y&p));fn=int(np.sum(y&~p))
    den=float((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))**.5
    return (tp*tn-fp*fn)/den if den else 0.


def _threshold_one(y,p):
    y=np.asarray(y);p=np.asarray(p,dtype=float)
    require(y.shape==p.shape and y.size>0 and np.isin(y,[0,1]).all() and np.isfinite(p).all(),'Invalid assay threshold inputs')
    best_score=-float('inf');best=None
    for t in np.linspace(.05,.95,37):
        score=_mcc_one(y,p>=t)
        if score>best_score:best_score=score;best=float(t)
    return best,best_score


def _assay_features(local_source,design,dev_frame,query_frame,cohort,root,evidence):
    """Audit native source folds/structure purges; consume PREDICTED columns only."""
    from rdkit import Chem
    from rdkit.Chem.MolStandardize import rdMolStandardize
    paths={}
    for key in ('oof','query','prepared_csv','prepared_spec'):
        require(key in local_source,'Missing local assay source '+key)
        paths[key]=evidence.add(_resolve(local_source[key],root),design['source_hashes'][key]['sha256'])
    refs=local_source.get('provenance_refs',[])
    require(bool(refs),'Native assay source needs upstream run provenance references')
    for i,path in enumerate(refs):
        record=evidence.json(_resolve(path,root),design['source_hashes'][f'upstream_ref_{i}']['sha256'])
        state=record.get('run',record)
        require(state.get('status')=='done' and state.get('exit_code') in (None,0),'Upstream native regression run is incomplete')
    native=pd.read_csv(paths['prepared_csv'],usecols=['molecule_name','smiles'])
    spec=read_json(paths['prepared_spec'])
    require(sha(paths['prepared_csv'])==spec['data_sha256'],'Native prepared pool/spec hash differs')
    oof=pd.read_csv(paths['oof'],usecols=['molecule_name']+ASSAY_COLUMNS)
    query=pd.read_csv(paths['query'],usecols=['molecule_name']+ASSAY_COLUMNS)
    require(not oof.molecule_name.duplicated().any() and set(oof.molecule_name)==set(native.molecule_name),'Native assay OOF coverage invalid')
    require(not query.molecule_name.duplicated().any() and set(query.molecule_name)==set(query_frame.Molecule_Name),'Native assay query IDs differ')
    keys=[]
    for smi in native.smiles:
        mol=Chem.MolFromSmiles(smi);require(mol is not None,'Invalid native source structure')
        connectivity=Chem.MolToInchiKey(mol).split('-')[0]
        parent=rdMolStandardize.Uncharger().uncharge(rdMolStandardize.FragmentParent(mol));Chem.RemoveStereochemistry(parent)
        keys.append((connectivity,Chem.MolToSmiles(parent,isomericSmiles=False)))
    connected={k[0] for k in keys};parents={k[1] for k in keys}
    overlap=query_frame.loc[query_frame.parent_key.isin(connected)|query_frame.canonical_parent.isin(parents),'Molecule_Name'].tolist()
    require(set(overlap)==({'OCNT-0496981'} if cohort=='full' else set()),'Unexpected assay source/query structure overlap')
    require(design['public_query_overlap']==overlap,'Reported public query overlap differs')
    contaminated=set();validation_members=[];dev_ids=set(dev_frame.Molecule_Name)
    for fold in spec['folds']:
        tr=np.asarray(fold['train']);va=np.asarray(fold['validation'])
        require(np.issubdtype(tr.dtype,np.integer) and np.issubdtype(va.dtype,np.integer) and not np.intersect1d(tr,va).size,'Invalid native base fold indices')
        require(np.all(tr>=0) and np.all(tr<len(native)) and np.all(va>=0) and np.all(va<len(native)),'Native fold indices out of bounds')
        fit={keys[i][0] for i in tr};parent={keys[i][1] for i in tr}
        for i in va:
            name=native.molecule_name.iloc[i];validation_members.append(name)
            if name in dev_ids and (keys[i][0] in fit or keys[i][1] in parent):contaminated.add(name)
    require(sorted(validation_members)==sorted(native.molecule_name.tolist()),'Native OOF folds do not partition input pool')
    affected=dev_frame[dev_frame.Molecule_Name.isin(contaminated)]
    aliases=dev_frame.loc[dev_frame.parent_key.isin(affected.parent_key)|dev_frame.canonical_parent.isin(affected.canonical_parent),'Molecule_Name'].tolist()
    require(set(aliases)==set(ASSAY_ALIASES[cohort]) and design['excluded_alias_ids']==ASSAY_ALIASES[cohort],'Assay alias exclusion differs from frozen audit')
    return (oof.set_index('molecule_name').reindex(dev_frame.Molecule_Name)[ASSAY_COLUMNS].to_numpy(float),
            query.set_index('molecule_name').loc[query_frame.Molecule_Name,ASSAY_COLUMNS].to_numpy(float))


def _verify_assay_layout(root,campaign,prep,base,cfg,prov,ev,source_hashes):
    """E5: verify source predictions, all72 fitted models, train-only selector and gate."""
    import joblib
    require('assay_stack.py' in source_hashes and len(source_hashes['assay_stack.py'])==1,'E5 requires unique pinned assay_stack.py source')
    require('native_regression_sources' in prov,'E5 provenance needs local native_regression_sources by cohort')
    summary=ev.json(root/'summary.json');done=ev.json(root/'complete.json')
    require(done.get('status')=='complete' and done['summary_sha256']==sha(root/'summary.json'),'E5 final collection incomplete/changed')
    require(summary.get('qualified_on_both_holdouts') is True,'E5 did not qualify on both holdouts; no submission')
    require(summary['submission_sha256']==sha(root/'submission_tdi.csv'),'E5 CSV differs from completion record')
    require(summary.get('sent') is False,'E5 artifact was already marked sent')
    metadata=ev.json(prep/'metadata.json');ev.add(prep/'embeddings_manifest.json')
    for rel,digest in metadata['output_files'].items():ev.add(prep/rel,digest)
    train=pd.read_csv(prep/'train.csv');test=pd.read_csv(prep/'test.csv');labels=np.load(prep/'y_train.npy',allow_pickle=False)
    X=np.load(prep/'X_train.npy',mmap_mode='r');Xt=np.load(prep/'X_test.npy',mmap_mode='r')
    reports={};policies={};fit_count=0;full_calls=None
    for cohort in COHORTS:
        cd=prep/'cohorts'/cohort;d=root/cohort
        dev=np.load(ev.add(cd/'train_indices.npy'),allow_pickle=False)
        qi=np.load(ev.add(cd/('query_indices.npy' if cohort=='full' else 'holdout_indices.npy')),allow_pickle=False)
        df=train.iloc[dev].reset_index(drop=True);qf=(test if cohort=='full' else train).iloc[qi].reset_index(drop=True)
        ids=df.Molecule_Name.astype(str).tolist();qids=qf.Molecule_Name.astype(str).tolist()
        for key in ('Molecule_Name','parent_key','canonical_parent'):
            require(not set(df[key])&set(qf[key]),'E5 development/query identity overlap')
        if cohort!='full':require(hashlib.sha256('\n'.join(qids).encode()).hexdigest()==HOLDOUT_ID_SHA[cohort],'E5 frozen holdout IDs/order changed')
        for name,expected in [('oof',df),('query',qf)]:
            frame=pd.read_csv(ev.add(d/(name+'_ids.csv')))
            require(frame[['Molecule_Name','SMILES']].astype(str).values.tolist()==expected[['Molecule_Name','SMILES']].astype(str).values.tolist(),'E5 '+name+' ID mapping differs')
        lock=ev.json(d/'prediction-lock.json');require(lock['query_ids']==qids,'E5 prediction lock IDs differ')
        design=ev.json(d/'frozen_design.json',lock['design_sha256'])
        policy=ev.json(d/'policy.json',lock['policy_sha256']);policies[cohort]=sha(d/'policy.json')
        selected=ev.json(d/'method-selection.json',lock['method_selection_sha256'])
        require(design['implementation_sha256']==next(iter(source_hashes['assay_stack.py'])),'E5 implementation differs')
        require(design['prepared_metadata_sha256']==sha(prep/'metadata.json') and design['seeds']==list(SEEDS),'E5 input/seeds provenance differs')
        require(design['feature_columns']==ASSAY_COLUMNS+['predicted_TDI_minus_direct'],'E5 features must be predicted assays only')
        require(design['structural_columns']==ev.json(prep/'feature_columns.json'),'E5 structural feature columns differ')
        require(design['candidate_methods']==['assay_logistic','struct_assay_lgbm'],'E5 undeclared candidate methods')
        require(policy.get('outer_labels_used_for_fitting_or_threshold') is False,'E5 outer label exclusion declaration missing')
        require(selected.get('upstream_inner_cv_is_strictly_nested') is False,'E5 must disclose imperfect upstream nesting')
        native={};base_arrays={};base_policies={};bl=ev.json(base/'evaluation'/cohort/'prediction-lock.json')
        for name in ('jeremy_lgbm','tabicl_native'):
            arrays=[_component(base,prep,cohort,seed,name,dev,qi,ev) for seed in SEEDS]
            base_arrays[name]=arrays
        for reference in ('native_reference','native_seed42'):
            bp=base/'evaluation'/cohort/(reference+'_policy.json')
            native_policy=ev.json(bp,bl['policy_sha256'][reference]);base_policies[reference]=native_policy
            require(native_policy['selection_input']['ids']==ids and native_policy['models']==['jeremy_lgbm','tabicl_native'],'E5 baseline policy dev IDs/model set differ')
            values={n:(base_arrays[n][0]['query_full_hard'] if reference=='native_seed42' else np.mean([a['query_full_hard'] for a in base_arrays[n]],axis=0)) for n in native_policy['models']}
            native[reference]=_apply_policy(values,native_policy)
            path=base/'evaluation'/cohort/(reference+'_predictions.csv')
            frame=pd.read_csv(ev.add(path,bl['prediction_sha256'][reference]))
            require(frame.Molecule_Name.astype(str).tolist()==qids and np.array_equal(_bool_columns(frame),native[reference]),'E5 native reference predictions differ')
        native['hauser_native']=_hauser_predictions(base,prep,cohort,ids,qids,ev)['native_hard']
        bp=base_policies['native_seed42'];base_oof=np.zeros((len(dev),2))
        for j,target in enumerate(TARGETS):
            for name in bp['models']:base_oof[:,j]+=bp['weights'][target][name]*base_arrays[name][0]['hard_oof'][:,j]
        # Verify source-level baseline hashes while resolving remote paths by known filenames.
        for remote,digest in design['baseline_hashes'].items():
            suffix=remote.split('/evaluation/')[-1] if '/evaluation/' in remote else None
            if suffix is not None:local=base/'evaluation'/suffix
            elif '/results/' in remote:local=base/'results'/remote.split('/results/')[-1]
            else:raise ValueError('Unrecognized E5 baseline source record')
            ev.add(local,digest)
        P,Q=_assay_features(prov['native_regression_sources'][cohort],design,df,qf,cohort,root,ev)
        known=np.isfinite(labels[dev,0]);retain=known&~df.Molecule_Name.isin(ASSAY_ALIASES[cohort]).to_numpy()
        require(np.isfinite(P[known]).all() and np.isfinite(Q).all(),'Missing predicted assay features for labelled/query rows')
        require(np.array_equal(np.load(ev.add(d/'selection_mask.npy')),retain) and np.array_equal(np.load(ev.add(d/'fallback_mask.npy')),~retain),'E5 selection/fallback masks differ')
        require(policy['selection_ids']==df.Molecule_Name[retain].tolist() and policy['fallback_ids_excluded_from_selection']==df.Molecule_Name[~retain].tolist(),'E5 selection IDs include excluded/unknown labels')
        require(design['known_rows']==int(known.sum()) and design['retained_rows']==int(retain.sum()),'E5 selection row counts differ')
        assay=np.column_stack([P,P[:,2]-P[:,0]]);aq=np.column_stack([Q,Q[:,2]-Q[:,0]])
        structural=np.column_stack([X[dev],assay]);sq=np.column_stack([Xt[qi] if cohort=='full' else X[qi],aq])
        methods={}
        for method in design['candidate_methods']:
            features,query_features=(assay,aq) if method=='assay_logistic' else (structural,sq)
            all_oof=[];all_query=[];inferred_queries=[]
            for seed in SEEDS:
                sd=d/method/f'seed{seed}';fold_path=prep/(f'folds_native_seed{seed}.npy' if cohort=='full' else f'cohorts/{cohort}/folds_seed{seed}.npy')
                folds=np.load(ev.add(fold_path),allow_pickle=False);model_meta=ev.json(sd/'metadata.json')
                require(model_meta=={'folds_sha256':sha(fold_path),'seed':seed,'method':method,'full_refit_used_for_deployment':False},'E5 seed/fold/fullfit metadata differs')
                saved=np.load(ev.add(sd/'predictions.npz'),allow_pickle=False);assembled=base_oof[:,0].copy();queries=[];model_queries=[]
                for fold in range(5):
                    rows=np.flatnonzero(retain&(folds==fold));a=np.load(ev.add(sd/f'fold{fold}.npz'),allow_pickle=False)
                    require(np.array_equal(a['valid_positions'],rows),'E5 fold query positions differ')
                    model=joblib.load(ev.add(sd/f'fold{fold}.joblib'));fit_count+=1
                    positive=int(np.flatnonzero(model.classes_==1)[0]);vp=model.predict_proba(features[rows])[:,positive];qp=model.predict_proba(query_features)[:,positive]
                    require(np.allclose(vp,a['valid_proba'],rtol=1e-8,atol=1e-10) and np.allclose(qp,a['query_proba'],rtol=1e-8,atol=1e-10),'E5 saved model does not reproduce fold/query predictions')
                    assembled[rows]=a['valid_proba'];queries.append(a['query_proba']);model_queries.append(qp)
                bag=np.mean(queries,axis=0)
                require(np.array_equal(saved['oof'],assembled) and np.array_equal(saved['query_bag'],bag) and np.array_equal(saved['selection_mask'],retain),'E5 OOF/query bag not reproduced')
                model=joblib.load(ev.add(sd/'full_model.joblib'));fit_count+=1
                diagnostic=np.load(ev.add(sd/'full_query_diagnostic.npy'),allow_pickle=False)
                positive=int(np.flatnonzero(model.classes_==1)[0]);require(np.allclose(model.predict_proba(query_features)[:,positive],diagnostic,rtol=1e-8,atol=1e-10),'E5 full-fit diagnostic model mismatch')
                all_oof.append(assembled);all_query.append(bag);inferred_queries.append(np.mean(model_queries,axis=0))
            methods[method]={'oof':np.mean(all_oof,axis=0),'query':np.mean(all_query,axis=0),'reinferred':np.mean(inferred_queries,axis=0)}
        folds=np.load(prep/(f'folds_native_seed42.npy' if cohort=='full' else f'cohorts/{cohort}/folds_seed42.npy'))
        winner=None;best=-float('inf')
        for method,values in methods.items():
            crossfit=np.zeros(len(dev),dtype=bool);thresholds={}
            for fold in range(5):
                fit=retain&(folds!=fold);valid=retain&(folds==fold)
                threshold,_=_threshold_one(labels[dev[fit],0],values['oof'][fit]);thresholds[str(fold)]=threshold
                crossfit[valid]=values['oof'][valid]>=threshold
            metric=_mcc_one(labels[dev[retain],0],crossfit[retain]);diag=selected['diagnostics'][method]
            require(diag['thresholds_by_fold']==thresholds and np.isclose(diag['crossfit_threshold_mcc'],metric,rtol=0,atol=1e-12),'E5 method selector not reproduced from train-only predictions')
            require(np.array_equal(np.load(ev.add(d/method/'crossfit_classes.npy')),crossfit),'E5 crossfit classes differ')
            if metric>best:winner,best=method,metric
        require(winner==selected['selected']==policy['CYP2D6_method'],'E5 chosen method differs from training-only selection')
        require(policy['training_method_selection']==selected['diagnostics'],'E5 policy method diagnostics differ')
        threshold,metric=_threshold_one(labels[dev[retain],0],methods[winner]['oof'][retain])
        require(policy['CYP2D6']['threshold']==threshold and np.isclose(policy['CYP2D6']['mcc'],metric,rtol=0,atol=1e-12),'E5 final threshold not fitted on retained development labels')
        calls=np.column_stack([methods[winner]['query']>=threshold,native['native_seed42'][:,1]])
        require(np.array_equal(calls[:,0],methods[winner]['reinferred']>=threshold),'E5 threshold classes unstable under saved model reproduction')
        require(policy['CYP3A4_threshold']==.5 and policy['CYP3A4_source']=='native_seed42 baseline hard classes, copied unchanged','E5 CYP3A4 source policy changed')
        frame=pd.read_csv(ev.add(d/'predictions.csv',lock['predictions_sha256']))
        require(frame.Molecule_Name.astype(str).tolist()==qids and frame.SMILES.tolist()==qf.SMILES.tolist() and np.array_equal(_bool_columns(frame),calls),'E5 final calls or frozen CYP3A4 differ')
        require(np.array_equal(np.load(ev.add(d/'probabilities.npy')),np.column_stack([methods[winner]['query'],native['native_seed42'][:,1].astype(float)])),'E5 saved query probabilities differ')
        require(np.array_equal(np.load(ev.add(d/'oof_probabilities.npy')),np.column_stack([methods[winner]['oof'],base_oof[:,1]])),'E5 saved OOF probabilities differ')
        report=ev.json(d/'summary.json');require(report==summary['cohorts'][cohort],'E5 cohort/overall summaries differ')
        if cohort!='full':
            reports[cohort]={name:_score(labels[qi],p,qids) for name,p in native.items()};reports[cohort]['soft_candidate']=_score(labels[qi],calls,qids)
            _check_reported(reports[cohort]['soft_candidate'],report['holdout'])
            for name in native:_check_reported(reports[cohort][name],report['native_baselines'][name])
        else:full_calls=calls
    require(fit_count==72,'E5 requires all72 archived CPU fits')
    comparisons=check_best_reference_gate(reports)
    validation,submitted=_check_csv(root/'submission_tdi.csv',prep/'test.csv',campaign/'sources/submission-preflight/tdi_validation.py',ev)
    require(np.array_equal(submitted,full_calls),'E5 final submission differs from full-cohort policy')
    validation.update(verified_cpu_model_fits=fit_count,CYP3A4_exact_native_seed42=True,
                      assay_features_predicted_only=True,upstream_inner_cv_strictly_nested=False)
    return dict(provenance=prov,comparisons=comparisons,policy_sha256=policies,validation=validation,
                evidence=list(ev.files.values()),submission_path=str(root/'submission_tdi.csv'))


def _verify_candidate(candidate_root,campaign_root):
    root=Path(candidate_root).resolve();campaign=Path(campaign_root).resolve();ev=Evidence()
    provenance_path=root/'deployment-provenance.json'
    require(provenance_path.exists(), 'Missing deployment-provenance.json: require prepared_dir,base_results,source_files,source_runs,model_tag,gradio_client_version,selection_review')
    prov=ev.json(provenance_path)
    for key in ('prepared_dir','base_results','source_files','source_runs','model_tag','gradio_client_version','selection_review'):
        require(key in prov, f'deployment-provenance.json missing {key}')
    require(prov['selection_review'].get('outer_labels_used_for_selection') is False and prov['selection_review'].get('recipe_match_verified') is True,
            'Explicit train-only selection and full-refit recipe-match review required')
    require(isinstance(prov['model_tag'],str) and prov['model_tag'].strip() and 'REPLACE_' not in prov['model_tag'], 'Real selected TDI method tag required')
    require('TDI' in prov['model_tag'], 'Method tag must distinguish this TDI submission')
    require(bool(prov['gradio_client_version']), 'Pin gradio_client version')
    require(isinstance(prov['source_files'],list) and bool(prov['source_files']), 'Hash-pinned experiment sources required')
    source_names=set();source_hashes={}
    for record in prov['source_files']:
        path=ev.add(_resolve(record['path'],root),record['sha256']);source_names.add(path.name);source_hashes.setdefault(path.name,set()).add(record['sha256'])
    require({'runner.py','evaluation.py','learners.py','data.py','hauser_native.py'}.issubset(source_names), 'Need frozen runner/evaluation/learners/data/hauser_native source hashes')
    require(isinstance(prov['source_runs'],list) and bool(prov['source_runs']), 'Completed ORX source runs required')
    for run in prov['source_runs']:
        record=run['evidence'];state=ev.json(_resolve(record['path'],root),record['sha256']);state=state.get('run',state)
        require(state.get('status')=='done' and state.get('exit_code') in (None,0) and str(state.get('run_id',state.get('id')))==str(run['run_id']), 'Source run lacks terminal success evidence')
    prep=_resolve(prov['prepared_dir'],root);base=_resolve(prov['base_results'],root)
    if 'config_evidence' in prov:
        record=prov['config_evidence'];cfg=ev.json(_resolve(record['path'],root),record['sha256'])
    else:cfg=ev.json(root/'config.json')
    require(set(cfg['seeds'])==set(SEEDS),'Exactly paired seeds42/142 required')
    if cfg.get('phase')=='assay_stack':
        return _verify_assay_layout(root,campaign,prep,base,cfg,prov,ev,source_hashes)
    pool=_resolve(prov['pool_results'],root) if 'pool_results' in prov else None
    declared=list(dict.fromkeys(cfg.get('pool_methods',['jeremy_lgbm','tabicl_native']+cfg['methods'])))
    if cfg.get('include_hauser_candidate') is True and 'hauser_native' not in declared:declared.append('hauser_native')
    if any(n not in cfg['methods'] and n not in ('jeremy_lgbm','tabicl_native','hauser_native') for n in declared):
        require(pool is not None,'deployment-provenance.json requires local pool_results for reused complementary methods')
    if 'gnn' in declared:
        require('gnn.py' in source_hashes and len(source_hashes['gnn.py'])==1,'Need unique pinned gnn.py implementation hash')
        require('foundation_checkpoint' in prov,'deployment-provenance.json requires local foundation_checkpoint')
        ev.add(_resolve(prov['foundation_checkpoint'],root),'c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651')
    metadata=ev.json(prep/'metadata.json');ev.add(prep/'embeddings_manifest.json')
    for rel,expected in metadata['output_files'].items():ev.add(prep/rel,expected)
    train=pd.read_csv(ev.add(prep/'train.csv'));test=pd.read_csv(ev.add(prep/'test.csv'));y=np.load(ev.add(prep/'y_train.npy'),allow_pickle=False)
    summary=ev.json(root/'summary.json');done=ev.json(root/'complete.json')
    require(done.get('status')=='complete' and done['summary_sha256']==sha(root/'summary.json'),'Final collection incomplete or changed')
    require(summary.get('qualified_on_both_holdouts') is True,'Runner did not qualify candidate on both holdouts')
    require(summary.get('submission_sha256')==sha(root/'submission_tdi.csv'),'Final CSV differs from summary')
    scores={};policy_digests={};full_pred=None
    for cohort in COHORTS:
        d=root/'evaluation'/cohort;cdir=prep/'cohorts'/cohort
        dev=np.load(ev.add(cdir/'train_indices.npy'),allow_pickle=False)
        query=np.load(ev.add(cdir/('query_indices.npy' if cohort=='full' else 'holdout_indices.npy')),allow_pickle=False)
        ids=train.iloc[dev].Molecule_Name.astype(str).tolist();qids=(test if cohort=='full' else train).iloc[query].Molecule_Name.astype(str).tolist()
        require(len(set(ids))==len(ids) and len(set(qids))==len(qids) and not set(ids)&set(qids),'Duplicate/overlapping dev/query IDs')
        if cohort!='full':require(hashlib.sha256('\n'.join(qids).encode()).hexdigest()==HOLDOUT_ID_SHA[cohort],'Frozen holdout membership/order changed')
        lock=ev.json(d/'prediction-lock.json');reported=ev.json(d/'summary.json')
        require(lock.get('outer_labels_used_for_selection') is False and set(lock['seeds'])==set(SEEDS),'Selection lock missing train-only/seeds declaration')
        require(lock['query_ids']==qids and reported==summary['results'][cohort],'Evaluation ID/summary mismatch')
        models=lock['methods']; require({'jeremy_lgbm','tabicl_native'}.issubset(models),'Missing Jeremy reference members')
        require(set(models)==set(declared),'Locked candidate library differs from config')
        hauser=_hauser_predictions(base,prep,cohort,ids,qids,ev)
        loaded={};single={}
        for name in models:
            if name=='hauser_native':
                loaded[name]=hauser
                continue
            directory=root if name in cfg['methods'] else (base if name in ('jeremy_lgbm','tabicl_native') else pool)
            if name=='gnn':
                implementation_sha=next(iter(source_hashes['gnn.py']))
                arrays=[_gnn_component(directory,prep,cohort,seed,dev,query,ev,implementation_sha) for seed in SEEDS]
            else:
                arrays=[_component(directory,prep,cohort,seed,name,dev,query,ev) for seed in SEEDS]
            loaded[name]={k:np.mean([a[k] for a in arrays],axis=0) for k in arrays[0]}
            if name in ('jeremy_lgbm','tabicl_native'):
                single[name]=arrays[0] if directory==base else _component(base,prep,cohort,42,name,dev,query,ev)
        cohort_preds={}
        for name in ('soft_candidate','native_reference','native_seed42'):
            policy=ev.json(d/(name+'_policy.json'),lock['policy_sha256'][name]);policy_digests[cohort+'/'+name]=sha(d/(name+'_policy.json'))
            require(policy['selection_input']['ids']==ids,'Policy fitted on wrong development IDs')
            require(set(policy['models']).issubset(models),'Policy uses undeclared model')
            if name=='soft_candidate':
                allowed={'crossfit_pool_top3_probability_grid'}
                if cfg.get('endpointwise_selection') is True:allowed.add('endpointwise_crossfit_probability_pool')
                if cfg.get('selection_strategy')=='fixed_native_weights':allowed={'fixed_native_weights_soft_full_refit'}
                require(policy['kind'] in allowed,'Unexpected candidate selection rule: '+str(policy['kind']))
                query_mode=cfg.get('candidate_query','bag')
                require(query_mode in ('bag','full'),'Unknown candidate query mode')
                key='query_full' if query_mode=='full' else 'query_bag'
                require(all(key in loaded[n] for n in policy['models']),'Declared query mode unsupported by selected member')
                if cfg.get('selection_strategy')=='fixed_native_weights':
                    native_policy=read_json(d/'native_reference_policy.json')
                    require(policy['models']==native_policy['models'] and policy['weights']==native_policy['weights'],'E8 must preserve native ensemble weights')
                values={n:loaded[n][key] for n in policy['models']}
            else:
                require(policy['kind']=='native_jeremy_caruana' and policy['models']==['jeremy_lgbm','tabicl_native'],'Unexpected native reference recipe')
                values={n:(single[n] if name=='native_seed42' else loaded[n])['query_full_hard'] for n in policy['models']}
            pred=_apply_policy(values,policy)
            frame=pd.read_csv(ev.add(d/(name+'_predictions.csv'),lock['prediction_sha256'][name]))
            require(frame.Molecule_Name.astype(str).tolist()==qids and np.array_equal(_bool_columns(frame),pred),'Locked predictions not reproduced by policy/member arrays')
            cohort_preds[name]=pred
        hpred=hauser['native_hard']
        frame=pd.read_csv(ev.add(d/'hauser_native_predictions.csv'))
        require(frame.Molecule_Name.astype(str).tolist()==qids and np.array_equal(_bool_columns(frame),hpred),'Hauser reported predictions differ')
        cohort_preds['hauser_native']=hpred
        if cohort!='full':
            scores[cohort]={n:_score(y[query],v,qids) for n,v in cohort_preds.items()}
            for n,v in scores[cohort].items():_check_reported(v,reported['holdout'][n])
        else:full_pred=cohort_preds['soft_candidate']
    comparisons=check_best_reference_gate(scores)
    validation,submitted=_check_csv(root/'submission_tdi.csv',prep/'test.csv',campaign/'sources/submission-preflight/tdi_validation.py',ev)
    require(np.array_equal(submitted,full_pred),'Submission differs from verified full-data candidate policy')
    return dict(provenance=prov,comparisons=comparisons,policy_sha256=policy_digests,
                validation=validation,evidence=list(ev.files.values()),submission_path=str(root/'submission_tdi.csv'))


def prepare(candidate_root,campaign_root):
    """Offline model verification plus read-only live contract; creates immutable intent."""
    root=Path(candidate_root).resolve();campaign=Path(campaign_root).resolve()
    verified=_verify_candidate(root,campaign);contract=check_live_contract(campaign)
    prov=verified['provenance'];arguments=dict(username='AdeliyaLL',user_alias='AdeliyaLL-CYP',anon_checkbox=True,
        participant_name='',discord_username='',email='',affiliation='',model_tag=prov['model_tag'].strip(),
        paper_checkbox=False,proprietary_data_checkbox=False,open_code_checkbox=False,track_select='Classification Prediction')
    csvpath=Path(verified['submission_path']);digest=sha(csvpath)
    body=dict(schema_version=1,track='classification',candidate_root=str(root),campaign_root=str(campaign),
        api_signature=contract['api_signature'],api_arguments_without_file=arguments,
        gradio_client_version=prov['gradio_client_version'],csv_sha256=digest,
        qualification=verified['comparisons'],validation=verified['validation'],policy_sha256=verified['policy_sha256'],
        evidence=verified['evidence'],contract=contract,transport_source_sha256=TRANSPORT_SHA256,
        adapter_sha256=sha(__file__),method_report_required_by_deadline=True)
    intent_id=hashlib.sha256(canonical(body)).hexdigest();ledger=campaign/'submission-ledger'
    immutable(ledger/'track.json',canonical({'track':'classification','username':'AdeliyaLL'}))
    directory=ledger/'intents'/intent_id
    immutable(directory/'intent.json',canonical(body));immutable(directory/'submission.csv',csvpath.read_bytes())
    result=dict(intent_id=intent_id,intent_dir=str(directory),csv_sha256=digest,intent=body,
                ledger_dir=str(ledger),status='verified_prepared_no_upload')
    immutable(directory/'prepared.json',canonical(result))
    return result


def send(prepared,campaign_root,transport=None):
    """Explicit one-shot send only after a real prepared qualified intent exists."""
    campaign=Path(campaign_root).resolve();ledger=campaign/'submission-ledger';body=prepared['intent']
    require(Path(prepared['ledger_dir']).resolve()==ledger and Path(body['campaign_root']).resolve()==campaign,'Wrong TDI ledger/campaign')
    require(read_json(ledger/'track.json')=={'track':'classification','username':'AdeliyaLL'},'Wrong ledger track')
    require(body['track']=='classification' and body['api_arguments_without_file']['track_select']=='Classification Prediction','Only classification submission authorized')
    require(body['adapter_sha256']==sha(__file__) and body['transport_source_sha256']==TRANSPORT_SHA256,'Deployment adapter/transport changed')
    intent_path=Path(prepared['intent_dir']).resolve()
    require(intent_path==ledger/'intents'/prepared['intent_id'],'Intent outside classification ledger')
    require((intent_path/'intent.json').read_bytes()==canonical(body),'Persisted intent differs from prepared body')
    for record in body['evidence']:require(sha(record['path'])==record['sha256'],f"Prepared evidence changed: {record['path']}")
    for attempt in (ledger/'attempts').glob('*/attempt.json'):
        require(read_json(attempt).get('track')=='classification','Mixed-track ledger is forbidden')
    contract=check_live_contract(campaign)
    require(contract['api_signature']==body['api_signature'],'Live API signature changed')
    result=_transport_namespace()['send_prepared'](prepared,ledger,transport=transport)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign-root',default=str(Path(__file__).resolve().parent))
    parser.add_argument('--candidate-root');parser.add_argument('--prepared')
    parser.add_argument('--send',action='store_true',help='Explicit ONE upload after verified local improvement; never automatic')
    args=parser.parse_args()
    if args.prepared:
        result=read_json(args.prepared)
    else:
        require(args.candidate_root is not None,'Provide --candidate-root or --prepared')
        result=prepare(args.candidate_root,args.campaign_root)
    if args.send:
        receipt=send(result,args.campaign_root);print(json.dumps(receipt,indent=2));return 0 if receipt['status']=='accepted_pending' else 2
    print(json.dumps({k:v for k,v in result.items() if k!='intent'},indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
