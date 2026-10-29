"""Portable historical briford datasets. No network, private Workbench, or cohort selection.

The caller supplies a training partition and *all* official train/test parent keys.
The published recipe is reconstructed, not an assertion of identical private weights.
"""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

ISOFORMS = ['cyp3a4', 'cyp2c9', 'cyp2d6', 'cyp1a2']
DIRECT = [f'{i}_pic50_direct_inhibition' for i in ISOFORMS]
CANONICAL = [f'{i.upper()}_pIC50_direct_inhibition' for i in ['cyp1a2','cyp2c9','cyp2d6','cyp3a4']]
MAPPING = {t: t.split('_')[0].upper() + '_pIC50_direct_inhibition' for t in DIRECT}
LOG2FC = [f'{i}_log2fc' for i in ISOFORMS]
TDI = [f'{i}_pic50_tdi_condition' for i in ISOFORMS]
EMAX = [f'{i}_emax_vs_pos_ctrl_direct_inhibition' for i in ISOFORMS]
PUBLIC_ISOFORMS = ISOFORMS + ['cyp2c19']
CHEMBL = [f'{i}_pic50_chembl' for i in PUBLIC_ISOFORMS]
VEITH = [f'{i}_max_response' for i in PUBLIC_ISOFORMS]
SOURCE_REFS = {'union18':'971f6a7f24d86e59bab219347c3e14c006ae4e35',
               'framework_and_specialists':'8c72c7559471febaf0962fd551b4eaab8db3a136'}
DEFAULTS = dict(hidden_dim=700, depth=5, dropout=.1, ffn_hidden_dim=300,
                ffn_num_layers=2, batch_norm=True, aggregation='norm', loss='mae',
                max_epochs=400, patience=40, batch_size=64, warmup_epochs=2,
                init_lr=1e-4, max_lr=1e-3, final_lr=1e-4, seed=42)

@dataclass
class ComponentData:
    train_df: pd.DataFrame
    target_columns: list[str]
    task_weights: list[float]
    primary_mapping: dict[str,str]
    metadata: dict

@lru_cache(maxsize=150000)
def _parent(smiles):
    from .public_data import normalize_parent_key
    return normalize_parent_key(smiles)

def _assets(root, config):
    candidates = [Path(config['reference_data_dir'])] if config.get('reference_data_dir') else [
        Path(root)/'reference_audit/public_data', Path(root)/'reference/public_data']
    for p in candidates:
        if (p/'inhibition.csv').exists(): return p
    raise FileNotFoundError(f'Public reference CSV directory missing: {candidates}')

@lru_cache(maxsize=12)
def _read(path):
    return pd.read_csv(path)

def _standard(df):
    rename = {'molecule_name':'Molecule_Name','smiles':'SMILES'}
    for c in df:
        low = c.lower()
        if low.startswith('cyp'):
            low = low.replace('_conf_low','_ci_lower').replace('_conf_high','_ci_upper')
            rename[c] = low
    return df.rename(columns=rename).copy()

def _official_aux(base, p, kinds):
    out = base.copy()
    if 'log2fc' in kinds:
        raw = _read(str(p/'single_concentration.csv'))
        wide = raw.pivot_table(index='molecule_name', columns='enzyme', values='log2fc_estimate')
        wide.columns = [f'{c.lower()}_log2fc' for c in wide]
        wide = wide.reset_index().rename(columns={'molecule_name':'Molecule_Name'})
        out = out.drop(columns=[c for c in LOG2FC if c in out]).merge(wide[['Molecule_Name']+LOG2FC], on='Molecule_Name', how='left', validate='one_to_one')
    for kind, filename, cols in [('tdi','tdi.csv',TDI),('emax','emax.csv',EMAX)]:
        if kind in kinds:
            side = _standard(_read(str(p/filename)))[['Molecule_Name']+cols]
            out = out.drop(columns=[c for c in cols if c in out]).merge(side, on='Molecule_Name', how='left', validate='one_to_one')
    return out

def _filter_public(df, excluded, metadata, name):
    df = df.copy()
    df['parent_key'] = df.SMILES.map(_parent)
    before = len(df)
    invalid = int(df.parent_key.isna().sum())
    overlap = int(df.parent_key.isin(excluded).sum())
    df = df[df.parent_key.notna() & ~df.parent_key.isin(excluded)].copy()
    pre_dedup = len(df)
    df = df.drop_duplicates('parent_key', keep='first')
    metadata[name] = dict(raw_rows=before, invalid_parent_rows=invalid,
                          excluded_official_parent_rows=overlap,
                          duplicate_parent_rows=pre_dedup-len(df), retained_rows=len(df))
    return df

def _union_public(base, p, excluded, metadata):
    out = base.copy()
    out['parent_key'] = out.SMILES.map(_parent)
    chembl = _read(str(p/'chembl_all_isoforms.csv'))
    chembl = chembl[['chembl_id','smiles']+[f'{i}_pic50' for i in PUBLIC_ISOFORMS]].rename(
        columns={'smiles':'SMILES','chembl_id':'Molecule_Name',**{f'{i}_pic50':f'{i}_pic50_chembl' for i in PUBLIC_ISOFORMS}})
    chembl = _filter_public(chembl, excluded, metadata, 'chembl')
    veith = _read(str(p/'pubchem_all_isoforms.csv')).pivot_table(index='smiles',columns='isoform',values='max_response')
    veith.columns = [f'{c}_max_response' for c in veith]
    veith = veith[VEITH].clip(-150.,50.).reset_index().rename(columns={'smiles':'SMILES'})
    veith = _filter_public(veith, excluded, metadata, 'veith')
    veith['Molecule_Name'] = veith.parent_key.map(lambda x:'VEITH-'+hashlib.sha256(x.encode()).hexdigest()[:24])
    for raw, cols in [(chembl,CHEMBL),(veith,VEITH)]:
        out = out.merge(raw[['parent_key']+cols], on='parent_key', how='left', validate='many_to_one')
        new = raw[~raw.parent_key.isin(set(out.parent_key))]
        out = pd.concat([out,new],ignore_index=True)
    return out

def build_component_data(component, train_df, asset_root, config=None, excluded_parent_keys=None):
    config = dict(config or {})
    if component not in {'direct','official_aux','union18','mtaux8','2d6isoform6','2d6single'}:
        raise ValueError(f'Unknown reference component: {component}')
    base = _standard(train_df)
    if base.Molecule_Name.duplicated().any(): raise ValueError('Duplicate input Molecule_Name')
    requested = config.get('targets', CANONICAL)
    primary = [t for t in DIRECT if MAPPING[t] in requested]
    if not primary: raise ValueError(f'No recognized requested targets: {requested}')
    if component in {'2d6isoform6','2d6single'}: primary = [DIRECT[2]]
    for t in primary:
        if t not in base: raise ValueError(f'Missing primary training column {t}')
    metadata = dict(component=component, source_commits=SOURCE_REFS,
        supplied_official_rows=len(base), primary_fraction=None,
        primary_fraction_note='Historical source has no primary_fraction sampler parameter.',
        deviations=['Fixed caller official folds with external auxiliary rows in every fit, rather than author CV over each union.',
                    'Task weights recomputed on the supplied training partition, rather than full-source counts.',
                    'Public CSVs are current pinned snapshots; historical trained model/OOF artifacts are unavailable.',
                    'External structures use normalized neutral nonstereo parents and exclude all provided official train/test parents.'])
    kinds = []
    if component in {'union18','mtaux8'}: kinds = ['log2fc']
    if component == '2d6isoform6': kinds = ['log2fc','tdi','emax']
    if component == 'official_aux': kinds = config.get('official_aux', ['log2fc','tdi','emax'])
    p = _assets(asset_root, config) if kinds or component == 'union18' else None
    if kinds: base = _official_aux(base,p,kinds)
    targets = primary.copy()
    if component in {'union18','mtaux8'}: targets += LOG2FC
    if component == 'union18': targets += CHEMBL+VEITH
    if component == 'official_aux':
        for kind, cols in [('log2fc',LOG2FC),('tdi',TDI),('emax',EMAX)]:
            if kind in kinds: targets += cols
    if component == '2d6isoform6': targets += [LOG2FC[2],TDI[2],EMAX[2],CHEMBL[2],VEITH[2]]
    public = component in {'union18','2d6isoform6'}
    if public and excluded_parent_keys is None:
        raise ValueError('Reference public auxiliary data require explicit all-official train/test excluded_parent_keys')
    excluded = set(excluded_parent_keys or [])
    if public:
        if component == '2d6isoform6' and config.get('include_official_side_rows',False):
            all_ids = set(_read(str(p/'inhibition.csv')).molecule_name)
            side = _standard(_read(str(p/'tdi.csv')))[['Molecule_Name','SMILES']+TDI]
            side = side[~side.Molecule_Name.isin(all_ids)]
            side = _official_aux(side,p,['emax'])
            side = _filter_public(side,excluded,metadata,'official_side_only')
            # Historical side-only records contain no primary/log2fc targets.
            base = pd.concat([base,side],ignore_index=True)
        metadata['include_official_side_rows'] = bool(component == '2d6isoform6' and config.get('include_official_side_rows',False))
        base = _union_public(base,p,excluded,metadata)
    for t in targets:
        if t not in base: raise ValueError(f'Required source head missing: {t}')
    base[targets] = base[targets].apply(pd.to_numeric,errors='raise')
    if np.isinf(base[targets].to_numpy(float)).any(): raise ValueError('Infinite training labels')
    before = len(base)
    base = base[base[targets].notna().any(axis=1)].reset_index(drop=True)
    if base.Molecule_Name.duplicated().any(): raise ValueError('Duplicate IDs after reference union')
    counts = base[targets].notna().sum()
    if (counts == 0).any(): raise ValueError(f'Unobserved required heads: {counts[counts == 0].index.tolist()}')
    if component in {'2d6isoform6','2d6single'}:
        weights = [1.] + [.3]*(len(targets)-1)
    elif component in {'union18','mtaux8'}:
        weights0 = (1/counts[primary].to_numpy(np.float32)).astype(np.float32)
        weights0 /= weights0.mean()
        weights = weights0.astype(float).tolist() + [float(.3*weights0.mean())]*(len(targets)-len(primary))
    else: weights = [1.]*len(primary)+[float(config.get('aux_weight',.3))]*(len(targets)-len(primary))
    if config.get('task_weights') is not None:
        weights = list(config['task_weights'])
        if len(weights) != len(targets): raise ValueError('Task weights length mismatch')
    if not np.isfinite(weights).all() or min(weights)<0: raise ValueError('Invalid task weights')
    metadata.update(train_rows=len(base), dropped_all_unknown_rows=before-len(base),
                    target_counts=counts.astype(int).to_dict(), task_weights=weights,
                    weighted_label_mass=float(np.dot(counts,weights)),target_order=targets)
    if p:
        metadata['source_files'] = {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.glob('*.csv')}
    return ComponentData(base,targets,weights,{t:MAPPING[t] for t in primary},metadata)

def prepare_validation_data(component, validation_df, asset_root, config, target_columns):
    """Join official labels by ID only; never append public or side-only validation rows."""
    out = _standard(validation_df)
    kinds = [k for k,cols in [('log2fc',LOG2FC),('tdi',TDI),('emax',EMAX)] if set(cols)&set(target_columns)]
    if kinds: out = _official_aux(out,_assets(asset_root,config),kinds)
    for t in target_columns:
        if t not in out: out[t] = np.nan
    return out
