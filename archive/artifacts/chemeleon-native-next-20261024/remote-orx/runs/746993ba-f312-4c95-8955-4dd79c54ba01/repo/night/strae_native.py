"""Frozen two-encoder, two-cohort exact-ST-RAE experiment queue; no holdout fitting."""
from pathlib import Path
import json, os, shutil, signal, subprocess, sys, time
from . import briford_native as native
from .chemeleon_native import CHECKPOINT_SHA, ENCODER
from .briford_holdouts import score
from .strae_objective import MODE
from . import gpu_slots


def _copy_unchanged(source, target):
    if target.exists():
        if native.sha(source) != native.sha(target):
            raise ValueError(f'Refusing to overwrite changed prepared data: {target}')
    else:
        shutil.copy2(source, target)


def _save_unchanged(path, value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f'Refusing to overwrite changed prepared specification: {path}')
    else:
        native.save(path, value)


def prepare(config):
    assets = Path(config['assets']); destination = Path(config['output_dir'])
    initializations = config['initializations']
    if not initializations or len(set(initializations)) != len(initializations) or not set(initializations) <= {'scratch', 'chemeleon'}:
        raise ValueError('initializations must contain scratch and/or chemeleon without duplicates')
    if 'chemeleon' in initializations:
        assert native.sha(assets/'weights/chemeleon_mp.pt') == CHECKPOINT_SHA
    configurations = []
    for initialization in initializations:
        for cohort in ['own750', 'briford529']:
            source = assets/'frozen_holdouts'/cohort
            root = destination/f'{initialization}_exact_strae'/cohort
            prep = root/'prepared'; prep.mkdir(parents=True, exist_ok=True)
            for filename in ['truth.csv', 'query.csv', 'exclusion-audit.json']:
                _copy_unchanged(source/filename, root/filename)
            manifest = json.loads((source/'prepared/manifest.json').read_text())
            assert manifest['source_sha256'] == native.sources()
            models = {}
            for member in native.MODELS:
                spec = json.loads((source/'prepared'/f'{member}.json').read_text())
                assert native.sha(source/'prepared'/f'{member}.csv') == spec['data_sha256']
                assert manifest['outer_exclusion_audit'][member]['remaining_held_id_parent_or_connectivity_overlap'] == 0
                _copy_unchanged(source/'prepared'/f'{member}.csv', prep/f'{member}.csv')
                # Only explicit model/loss changes; the original JSON fold indices stay untouched.
                hp = spec['hyperparameters']; hp['criterion_mode'] = MODE
                if initialization == 'chemeleon':
                    hp.update(from_foundation=str(assets/'weights/chemeleon_mp.pt'), hidden_dim=2048, depth=6)
                    spec['foundation'] = {'checkpoint_sha256': CHECKPOINT_SHA, 'effective_encoder': ENCODER,
                                          'fixed_ffn_dropout': hp['dropout']}
                else:
                    if hp.get('from_foundation'):
                        raise ValueError('Frozen control unexpectedly contains foundation initialization')
                spec['loss_design'] = {'mode': MODE, 'normalizers': 'inner-fit only',
                    'auxiliary_rule': 'native_aux_weight/sum_native_primary_weights times per-auxiliary-head observed-label mean',
                    'checkpoint_monitor': 'val_primary_strae', 'smooth_or_center_penalty': False}
                _save_unchanged(prep/f'{member}.json', spec)
                models[member] = {k:v for k,v in spec.items() if k != 'folds'}
            _save_unchanged(prep/'manifest.json', {**manifest, 'models': models, 'criterion_mode': MODE,
                'initialization': initialization, 'frozen_control_manifest_sha256': native.sha(source/'prepared/manifest.json')})
            cfg = {'initialization': initialization, 'cohort': cohort, 'phase': 'train',
                'prepared_dir': str(prep), 'output_dir': str(root/'results'),
                'official_test': str(root/'query.csv'), 'validator_path': str(assets/'activity_validation.py'),
                'known_limits': ['Exact ST-RAE on fit sample; actual hidden TEST denominators are unknown.',
                                 'Auxiliary per-head means preserve nominal author head budgets, not native label-frequency weighting.',
                                 'Primary-only validation metric changes checkpoint selection.',
                                 'Published placement targets real TEST distribution; both raw and placed scores are reported.']}
            _save_unchanged(root/'config.json', cfg); configurations.append(cfg)
    return configurations


def run(config):
    configurations = prepare(config); jobs = []; running = {}
    for member in ['union18', '2d6isoform6', 'mtaux8', '2d6single']:
        for fold in range(5):
            for cfg in configurations:
                directory = Path(cfg['output_dir'])/member/f'fold{fold}'
                directory.mkdir(parents=True, exist_ok=True)
                job = {'member': member, 'fold': fold, 'prepared_dir': cfg['prepared_dir'],
                       'output_dir': str(directory), 'official_test': cfg['official_test']}
                native.save(directory/'job.json', job)
                if (directory/'complete.json').exists():
                    done = json.loads((directory/'complete.json').read_text())
                    assert done['job_identity'] == native.job_identity(job), 'Completed fold recipe/data/source differs'
                    for filename, digest in done['files'].items(): assert native.sha(directory/filename) == digest
                else:
                    jobs.append(directory/'job.json')
    def cancelled(signum, frame): raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, cancelled); signal.signal(signal.SIGINT, cancelled)
    print(json.dumps({'event': 'exact_strae_experiment_start', 'criterion_mode': MODE,
                      'initializations': config['initializations'], 'pending_models': len(jobs)}), flush=True)
    try:
        while jobs or running:
            for gpu in config['gpus']:
                if gpu not in running and jobs:
                    lease = gpu_slots.acquire(gpu)
                    if lease is None: continue
                    job = jobs.pop(0); log = (job.parent/'worker.log').open('a')
                    process = subprocess.Popen([sys.executable, '-u', '-m', 'night.briford_native', '--worker', str(job)],
                        env=dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu)), stdout=log, stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lease.fileno(),))
                    running[gpu] = (process, log, job, lease)
                    print(json.dumps({'event': 'exact_strae_fold_start', 'gpu': gpu, 'job': str(job)}), flush=True)
            for gpu, (process, log, job, lease) in list(running.items()):
                code = process.poll()
                if code is None: continue
                if code: raise RuntimeError(f'Worker failed exit={code}: {job}')
                log.close(); gpu_slots.release(lease); del running[gpu]
                meta = json.loads((job.parent/'metadata.json').read_text())
                print(json.dumps({'event': 'exact_strae_fold_complete', 'gpu': gpu, 'job': str(job),
                    'best_epoch': meta['best_epoch'], 'seconds': meta['seconds'], 'remaining_models': len(jobs)+len(running)}), flush=True)
            time.sleep(2)
    finally:
        for process, log, job, lease in running.values():
            try: os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError: pass
        if running: time.sleep(3)
        for process, log, job, lease in running.values():
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait(); log.close(); gpu_slots.release(lease)
    for cfg in configurations:
        for member in native.MODELS:
            for fold in range(5):
                directory = Path(cfg['output_dir'])/member/f'fold{fold}'
                job = json.loads((directory/'job.json').read_text())
                done = json.loads((directory/'complete.json').read_text())
                assert done['job_identity'] == native.job_identity(job)
        native.collect(cfg)
    output = Path(config['output_dir']); scores = {}
    for initialization in config['initializations']:
        root = output/f'{initialization}_exact_strae'
        score({'output_dir': str(root)})
        scores[initialization] = json.loads((root/'scores.json').read_text())
    native.save(output/'scores.json', scores)
    native.save(output/'complete.json', {'status': 'complete', 'models': len(configurations)*20,
        'criterion_mode': MODE, 'initializations': config['initializations'],
        'files': {str(p.relative_to(output)):native.sha(p) for p in output.rglob('*')
                  if p.is_file() and p.suffix != '.log' and p.name != 'complete.json'}})
    print(json.dumps({'event':'exact_strae_experiment_complete', 'scores': scores}), flush=True)

if __name__ == '__main__':
    run(json.loads(Path('briford_config.json').read_text()))
