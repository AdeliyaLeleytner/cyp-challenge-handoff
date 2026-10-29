# /// script
# requires-python = ">=3.11"
# dependencies = ["rdkit==2026.9.1", "numpy==2.5.4", "pandas==3.1.0", "scipy", "matplotlib", "scikit-learn"]
# ///
"""Local structural audit only; no model training or hidden test labels.
Run: uv run --no-project analyze.py
"""
from pathlib import Path
import csv, json, hashlib, sys, platform, warnings
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
import scipy, matplotlib, sklearn
from scipy.stats import wasserstein_distance
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from rdkit import Chem, DataStructs, rdBase
from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors, rdFingerprintGenerator, Draw
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.ML.Cluster import Butina
import matplotlib.pyplot as plt
from orx_figstyle import use_style, PALETTE, save

OUT = Path(__file__).resolve().parent
SRC = OUT.parent / 'cyp-review' / 'sources'
FIG = OUT / 'figures'; FIG.mkdir(exist_ok=True)
CYP = ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']
TARGET = {c: c+'_pIC50_direct_inhibition' for c in CYP}

def log(s): print(s, flush=True)
def read(name): return pd.read_csv(SRC/name)
def qstats(a):
    a=np.asarray(a,dtype=float)
    return {'n':len(a),'min':float(a.min()),'q10':float(np.quantile(a,.1)),
            'q25':float(np.quantile(a,.25)),'median':float(np.median(a)),
            'q75':float(np.quantile(a,.75)),'q90':float(np.quantile(a,.9)),
            'max':float(a.max()),'mean':float(a.mean())}
def simstats(a):
    out=qstats(a)
    out.update({f'n_ge_{t}':int(np.sum(np.asarray(a)>=t)) for t in [.4,.5,.6,.7,.8,.9,1.]})
    return out
def write_json(name, obj):
    (OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

train=read('cyp-challenge-TRAIN_inhibition.csv'); test=read('cyp-challenge-TEST-BLINDED.csv')
tdi=read('cyp-challenge-TRAIN_TDI.csv'); emax=read('cyp-challenge-TRAIN_Emax.csv')
single=read('cyp-challenge-single-concentration-TRAIN.csv')
all_source=pd.concat([train[['Molecule_Name','SMILES']],test,tdi[['Molecule_Name','SMILES']],
                      emax[['Molecule_Name','SMILES']],single[['Molecule_Name','SMILES']]])
conflicts=all_source.groupby('Molecule_Name').SMILES.nunique()
assert conflicts.max()==1, 'Inconsistent structure for identifier'
all_source=all_source.drop_duplicates('Molecule_Name').reset_index(drop=True)
log(f'Loaded train={len(train)}, test={len(test)}, unique source IDs={len(all_source)}')

uncharger=rdMolStandardize.Uncharger()
cache={}; mols={}; invalid=[]
for n,row in all_source.iterrows():
    name, smi=row.Molecule_Name,row.SMILES
    m=Chem.MolFromSmiles(smi)
    if m is None: invalid.append(name); continue
    raw_iso=Chem.MolToSmiles(m,isomericSmiles=True)
    clean=rdMolStandardize.Cleanup(m)
    p=rdMolStandardize.FragmentParent(clean,skipStandardize=True)
    neutral=uncharger.uncharge(Chem.Mol(p))
    sc=MurckoScaffold.GetScaffoldForMol(p)
    scs=Chem.MolToSmiles(sc,isomericSmiles=False)
    generic=Chem.MolToSmiles(MurckoScaffold.MakeScaffoldGeneric(sc),isomericSmiles=False) if scs else ''
    rec={'Molecule_Name':name,'SMILES':smi,'canonical_isomeric':raw_iso,
         'parent_isomeric':Chem.MolToSmiles(p,isomericSmiles=True),
         'parent_no_stereo':Chem.MolToSmiles(p,isomericSmiles=False),
         'neutral_parent_isomeric':Chem.MolToSmiles(neutral,isomericSmiles=True),
         'n_fragments':len(Chem.GetMolFrags(m)),'parent_atoms':p.GetNumHeavyAtoms(),
         'parent_changed':raw_iso!=Chem.MolToSmiles(p,isomericSmiles=True),
         'murcko':scs,'generic_murcko':generic,
         'MW':Descriptors.MolWt(p),'cLogP':Descriptors.MolLogP(p),'TPSA':Descriptors.TPSA(p),
         'HBD':Lipinski.NumHDonors(p),'HBA':Lipinski.NumHAcceptors(p),
         'rotatable_bonds':Lipinski.NumRotatableBonds(p),
         'rings':rdMolDescriptors.CalcNumRings(p),
         'aromatic_rings':rdMolDescriptors.CalcNumAromaticRings(p),
         'fraction_CSP3':rdMolDescriptors.CalcFractionCSP3(p),
         'formal_charge':Chem.GetFormalCharge(p),
         'defined_stereocentres':sum(v!='?' for _,v in Chem.FindMolChiralCenters(p,includeUnassigned=True)),
         'undefined_stereocentres':sum(v=='?' for _,v in Chem.FindMolChiralCenters(p,includeUnassigned=True))}
    cache[name]=rec; mols[name]=p
    if n and n%1500==0:log(f'Standardized {n} molecules')
assert not invalid, f'Invalid structures {invalid}'
meta=pd.DataFrame(cache.values()).set_index('Molecule_Name')
tr=meta.loc[train.Molecule_Name].reset_index(); te=meta.loc[test.Molecule_Name].reset_index()
meta.to_csv(OUT/'all_molecule_structures.csv')

identity={}
for key in ['canonical_isomeric','parent_isomeric','parent_no_stereo','neutral_parent_isomeric']:
    shared=set(tr[key])&set(te[key]); extras=meta.loc[~meta.index.isin(train.Molecule_Name)&~meta.index.isin(test.Molecule_Name)]
    identity[key]={'train_unique':int(tr[key].nunique()),'test_unique':int(te[key].nunique()),
                   'train_duplicate_rows':int(tr[key].duplicated().sum()),
                   'test_duplicate_rows':int(te[key].duplicated().sum()),
                   'test_matching_train':int(te[key].isin(shared).sum()),
                   'test_matching_auxiliary_only':int(te[key].isin(set(extras[key])).sum())}
overlap_rows=[]
for key in identity:
    z=te[['Molecule_Name',key]].merge(tr[['Molecule_Name',key]],on=key,suffixes=('_test','_train'))
    for _,r in z.iterrows():overlap_rows.append({'identity_rule':key,'test_id':r.Molecule_Name_test,'train_id':r.Molecule_Name_train})
pd.DataFrame(overlap_rows,columns=['identity_rule','test_id','train_id']).to_csv(OUT/'cross_set_identity_matches.csv',index=False)

scaffold_summary={};scaffold_rows=[]
for key in ['murcko','generic_murcko']:
    tc=Counter(x for x in tr[key] if x);qc=Counter(x for x in te[key] if x)
    seen=te[key].ne('')&te[key].isin(tc)
    scaffold_summary[key]={'train_nonempty_unique':len(tc),'test_nonempty_unique':len(qc),
       'shared_unique':len(set(tc)&set(qc)),'train_acyclic':int(tr[key].eq('').sum()),
       'test_acyclic':int(te[key].eq('').sum()),'test_molecules_seen':int(seen.sum()),
       'test_molecules_unseen_nonempty':int((te[key].ne('')&~seen).sum()),
       'train_singleton_scaffolds':sum(v==1 for v in tc.values()),
       'test_singleton_scaffolds':sum(v==1 for v in qc.values()),
       'test_largest_group':max(qc.values(),default=0)}
    for c in CYP:
        known=set(tr.loc[train[TARGET[c]].notna(),key])-{''}
        scaffold_summary[key][c+'_test_seen']=int((te[key].ne('')&te[key].isin(known)).sum())
    for rank,s in enumerate(sorted(set(tc)|set(qc),key=lambda x:(-qc[x],-tc[x],x)),1):
        row={'kind':key,'scaffold_id':('S' if key=='murcko' else 'G')+f'{rank:04d}',
             'scaffold_smiles':s,'train_count':tc[s],'test_count':qc[s]}
        for c in CYP:row[c+'_train_measured']=int(((tr[key]==s)&train[TARGET[c]].notna()).sum())
        scaffold_rows.append(row)
scaffolds=pd.DataFrame(scaffold_rows);scaffolds.to_csv(OUT/'scaffold_inventory.csv',index=False)
log('Identity and scaffold counts computed')

fpgen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048,includeChirality=False)
fp={k:fpgen.GetFingerprint(m) for k,m in mols.items()}
trfp=[fp[k] for k in train.Molecule_Name];tefp=[fp[k] for k in test.Molecule_Name]
sim=np.asarray([DataStructs.BulkTanimotoSimilarity(f,trfp) for f in tefp],dtype=np.float32)
train_sim=np.asarray([DataStructs.BulkTanimotoSimilarity(f,trfp) for f in trfp],dtype=np.float32)
test_sim=np.asarray([DataStructs.BulkTanimotoSimilarity(f,tefp) for f in tefp],dtype=np.float32)
assert np.allclose(np.diag(train_sim),1) and np.allclose(train_sim,train_sim.T)
assert np.all((sim>=0)&(sim<=1))
np.savez_compressed(OUT/'similarity_matrices.npz',test_train=sim,train_train=train_sim,test_test=test_sim)
summary={'counts':{'train':len(train),'test':len(test),'source_unique_ids':len(meta),'invalid_smiles':len(invalid)},
         'identity':identity,'scaffolds':scaffold_summary,'similarity':{},'fingerprint_sensitivity':{}}
summary['standardization']={'train_changed':int(tr.parent_changed.sum()),'test_changed':int(te.parent_changed.sum()),
                           'train_multifragment':int((tr.n_fragments>1).sum()),'test_multifragment':int((te.n_fragments>1).sum())}
nearest_rows=[]
coverage=pd.DataFrame({'Molecule_Name':test.Molecule_Name,'SMILES':test.SMILES,'murcko':te.murcko,
                      'scaffold_seen_in_train':te.murcko.ne('')&te.murcko.isin(set(tr.murcko))})
for pool in ['all']+CYP:
    idx=np.arange(len(train)) if pool=='all' else np.flatnonzero(train[TARGET[pool]].notna())
    sub=sim[:,idx]; order=np.argsort(-sub,axis=1,kind='stable')[:,:5];top=np.take_along_axis(sub,order,axis=1)
    coverage[pool+'_max_similarity']=top[:,0];coverage[pool+'_mean_top5']=top.mean(axis=1)
    coverage[pool+'_nearest_id']=train.Molecule_Name.iloc[idx[order[:,0]]].to_numpy()
    for th in [.4,.5,.6,.7,.8]:coverage[pool+f'_neighbors_ge_{th}']=(sub>=th).sum(axis=1)
    summary['similarity'][pool]=simstats(top[:,0]);summary['similarity'][pool]['reference_size']=len(idx)
    for i in range(len(test)):
        for rank in range(5):
            j=idx[order[i,rank]]
            row={'test_id':test.Molecule_Name.iloc[i],'pool':pool,'rank':rank+1,
                 'train_id':train.Molecule_Name.iloc[j],'tanimoto':float(sub[i,order[i,rank]]),
                 'same_murcko':bool(te.murcko.iloc[i] and te.murcko.iloc[i]==tr.murcko.iloc[j]),
                 'test_SMILES':test.SMILES.iloc[i],'train_SMILES':train.SMILES.iloc[j]}
            for c in CYP:row[TARGET[c]]=train[TARGET[c]].iloc[j]
            nearest_rows.append(row)
coverage.to_csv(OUT/'test_coverage.csv',index=False)
pd.DataFrame(nearest_rows).to_csv(OUT/'test_nearest_neighbors.csv',index=False)
np.fill_diagonal(train_sim,-1);loo=train_sim.max(axis=1);np.fill_diagonal(train_sim,1)
np.fill_diagonal(test_sim,-1);test_loo=test_sim.max(axis=1);np.fill_diagonal(test_sim,1)
summary['similarity']['train_leave_self_out']=simstats(loo)
summary['similarity']['test_leave_self_out']=simstats(test_loo)

# Sensitivity to hash collisions, chirality and radius; no values are cross-calibrated.
for tag,radius,bits,chiral in [('ecfp4_4096',2,4096,False),('ecfp4_2048_chiral',2,2048,True),('ecfp6_2048',3,2048,False)]:
    g=rdFingerprintGenerator.GetMorganGenerator(radius=radius,fpSize=bits,includeChirality=chiral)
    tf=[g.GetFingerprint(mols[k]) for k in train.Molecule_Name]
    qf=[g.GetFingerprint(mols[k]) for k in test.Molecule_Name]
    a=np.asarray([max(DataStructs.BulkTanimotoSimilarity(f,tf)) for f in qf])
    summary['fingerprint_sensitivity'][tag]=simstats(a)
    coverage[tag+'_max_similarity']=a
coverage.to_csv(OUT/'test_coverage.csv',index=False)
# Auxiliary-only structures may improve representation coverage but have no extra direct labels.
aux_ids=[x for x in meta.index if x not in set(test.Molecule_Name)]
auxfp=[fp[x] for x in aux_ids]
auxmax=np.array([max(DataStructs.BulkTanimotoSimilarity(f,auxfp)) for f in tefp])
summary['similarity']['all_official_training_structures']=simstats(auxmax)
summary['similarity']['all_official_training_structures']['reference_size']=len(aux_ids)
summary['similarity']['auxiliary_gain_gt_0_05']=int(np.sum(auxmax-sim.max(axis=1)>.05))
log('Pairwise similarity and endpoint coverage computed')

# Test-only clustering is descriptive, not a reconstruction of purchase parents.
cluster_rows=[];cluster_members=[]
for th in [.4,.5,.6,.7,.8]:
    cl=Butina.ClusterData(1-test_sim,len(test),1-th,isDistData=True,reordering=True)
    sizes=np.array([len(x) for x in cl])
    graph=csr_matrix(test_sim>=th)
    nc, lab=connected_components(graph,directed=False)
    cluster_rows.append({'tanimoto_threshold':th,'butina_clusters':len(cl),'singletons':int(sum(sizes==1)),
                         'largest_cluster':int(max(sizes)),'median_cluster_size':float(np.median(sizes)),
                         'clusters_size_5_to_15':int(sum((sizes>=5)&(sizes<=15))),
                         'connected_components':nc,'largest_component':int(max(Counter(lab).values()))})
    for j,group in enumerate(cl):
        for i in group:cluster_members.append({'threshold':th,'cluster':j,'size':len(group),'Molecule_Name':test.Molecule_Name.iloc[i]})
pd.DataFrame(cluster_rows).to_csv(OUT/'test_cluster_sensitivity.csv',index=False)
pd.DataFrame(cluster_members).to_csv(OUT/'test_cluster_membership.csv',index=False)
summary['test_clustering']=cluster_rows

# Compare the structural difficulty of ordinary 80/20 splits, without training.
trcl=Butina.ClusterData(1-train_sim,len(train),.4,isDistData=True,reordering=True)
butina_groups=np.empty(len(train),dtype=int)
for j,g in enumerate(trcl):butina_groups[list(g)]=j
scaf_groups=np.array([s if s else 'ACYCLIC_'+tr.parent_isomeric.iloc[i] for i,s in enumerate(tr.murcko)])
ident_groups=tr.parent_isomeric.to_numpy()
def group_holdout(groups,rng,fraction=.2):
    group_map=defaultdict(list)
    for i,g in enumerate(groups):group_map[g].append(i)
    keys=list(group_map);rng.shuffle(keys);chosen=[]
    for k in keys:
        if len(chosen)>=round(fraction*len(groups)):break
        chosen.extend(group_map[k])
    return np.array(sorted(chosen),dtype=int)
split_rows=[];split_examples={}
for mode,groups in [('random_identity',ident_groups),('murcko_group',scaf_groups),('butina_0.6_group',butina_groups)]:
    for seed in range(5):
        v=group_holdout(groups,np.random.default_rng(20261023+seed));t=np.setdiff1d(np.arange(len(train)),v)
        if seed==0:split_examples[mode]=train_sim[np.ix_(v,t)].max(axis=1)
        for pool in ['all']+CYP:
            ti=t if pool=='all' else t[train[TARGET[pool]].notna().to_numpy()[t]]
            vi=v if pool=='all' else v[train[TARGET[pool]].notna().to_numpy()[v]]
            a=train_sim[np.ix_(vi,ti)].max(axis=1)
            target=coverage[pool+'_max_similarity'].to_numpy()
            known_scaffolds=set(tr.murcko.iloc[ti])-{''}
            split_rows.append({'split':mode,'seed':seed,'pool':pool,'validation_molecules':len(v),
                'validation_scored_rows':len(vi),'training_reference_rows':len(ti),
                'median_similarity':float(np.median(a)),'mean_similarity':float(np.mean(a)),
                'wasserstein_to_test':float(wasserstein_distance(a,target)),
                'fraction_ge_0.7':float(np.mean(a>=.7)),
                'fraction_exact_murcko_seen':float(np.mean([tr.murcko.iloc[i] in known_scaffolds for i in vi]))})
pd.DataFrame(split_rows).to_csv(OUT/'split_geometry_comparison.csv',index=False)
summary['split_geometry_mean']=pd.DataFrame(split_rows).groupby(['split','pool']).mean(numeric_only=True).reset_index().to_dict('records')

# Neighborhood hubs: candidates only; never label these as confirmed original seeds.
hub=[]
for j in range(len(train)):
    hits=sim[:,j]>=.5
    if hits.any():
        row={'train_id':train.Molecule_Name.iloc[j],'SMILES':train.SMILES.iloc[j],
             'test_neighbors_ge_0.5':int(hits.sum()),'test_neighbors_ge_0.6':int((sim[:,j]>=.6).sum()),
             'test_for_which_top1':int((np.argmax(sim,axis=1)==j).sum()),'max_similarity':float(sim[:,j].max())}
        for c in CYP:row[TARGET[c]]=train[TARGET[c]].iloc[j]
        hub.append(row)
pd.DataFrame(hub).sort_values(['test_neighbors_ge_0.5','test_for_which_top1'],ascending=False).to_csv(OUT/'training_neighborhood_hubs.csv',index=False)

desc_rows=[]
for c in ['MW','cLogP','TPSA','HBD','HBA','rotatable_bonds','rings','aromatic_rings','fraction_CSP3','formal_charge']:
    aa=tr[c].to_numpy();bb=te[c].to_numpy()
    row={'descriptor':c,'train_median':float(np.median(aa)),'test_median':float(np.median(bb)),
         'train_q10':float(np.quantile(aa,.1)),'train_q90':float(np.quantile(aa,.9)),
         'test_q10':float(np.quantile(bb,.1)),'test_q90':float(np.quantile(bb,.9)),
         'wasserstein_in_train_IQR':float(wasserstein_distance(aa,bb)/(np.quantile(aa,.75)-np.quantile(aa,.25))) if np.quantile(aa,.75)>np.quantile(aa,.25) else None,
         'wasserstein_raw':float(wasserstein_distance(aa,bb))}
    desc_rows.append(row)
pd.DataFrame(desc_rows).to_csv(OUT/'descriptor_comparison.csv',index=False)
summary['descriptors']=desc_rows
write_json('summary.json',summary)
manifest={'source_revision':json.loads((SRC/'hf_dataset_revision.json').read_text())['sha'],
          'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in SRC.glob('*.csv')},
          'python':platform.python_version(),'rdkit':rdBase.rdkitVersion,'numpy':np.__version__,
          'pandas':pd.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__,'sklearn':sklearn.__version__,
          'primary_fingerprint':'Morgan radius=2 fpSize=2048 includeChirality=False; Tanimoto',
          'standardization':'RDKit Cleanup then FragmentParent(skipStandardize=True); charges/stereochemistry retained. Neutral identity is additional audit only; no tautomer collapsing.',
          'scaffolds':'RDKit Murcko, chirality excluded; generic Murcko collapses atom types and bond orders; empty acyclic scaffolds excluded from shared scaffold counts.'}
write_json('manifest.json',manifest)
log('Structural split comparison computed; generating figures')

use_style()
def export(fig,name):
    save(fig,str(FIG/name));fig.savefig(FIG/(name+'.png'),dpi=190);plt.close(fig)
def ecdf(ax,a,label,color,style='-'):
    a=np.sort(a);ax.step(a,np.arange(1,len(a)+1)/len(a),where='post',label=label,color=color,ls=style)
fig,axes=plt.subplots(1,2,figsize=(6.75,2.7),layout='constrained')
ecdf(axes[0],sim.max(axis=1),'Test to train',PALETTE['orange'])
ecdf(axes[0],loo,'Train to other train',PALETTE['blue'])
ecdf(axes[0],test_loo,'Test to other test',PALETTE['green'])
for c,col in zip(CYP,['blue','orange','green','purple']):ecdf(axes[1],coverage[c+'_max_similarity'],c,PALETTE[col])
for ax in axes:
    ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('Nearest-neighbor Tanimoto (ECFP4)');ax.set_ylabel('Cumulative fraction');ax.legend(loc='upper left',fontsize=6.5)
export(fig,'similarity_coverage')
fig,ax=plt.subplots(figsize=(6.75,2.6),layout='constrained')
ecdf(ax,sim.max(axis=1),'Competition test to full train',PALETTE['black'])
for (mode,a),col in zip(split_examples.items(),['blue','orange','green']):ecdf(ax,a,mode.replace('_',' '),PALETTE[col])
ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('Nearest-neighbor Tanimoto (ECFP4)');ax.set_ylabel('Cumulative fraction');ax.legend(loc='upper left',fontsize=6.5)
export(fig,'split_geometry')
fig,axes=plt.subplots(1,3,figsize=(6.75,2.5),layout='constrained')
for ax,c,label in zip(axes,['MW','cLogP','fraction_CSP3'],['Molecular weight (g/mol)','Calculated logP','Fraction sp3 carbon']):
    ecdf(ax,tr[c],'Train',PALETTE['blue']);ecdf(ax,te[c],'Test',PALETTE['orange']);ax.set_xlabel(label);ax.set_ylabel('Cumulative fraction');ax.legend()
export(fig,'descriptor_distributions')

for kind,data in [('top_test',scaffolds[scaffolds.kind=='murcko'].sort_values(['test_count','train_count'],ascending=False).head(12)),
                  ('top_train',scaffolds[scaffolds.kind=='murcko'].sort_values('train_count',ascending=False).head(12))]:
    ms=[Chem.MolFromSmiles(s) for s in data.scaffold_smiles]
    legends=[f'{r.scaffold_id} | test {r.test_count} | train {r.train_count}' for r in data.itertuples()]
    opts=Draw.MolDrawOptions();opts.legendFontSize=16
    svg=Draw.MolsToGridImage(ms,molsPerRow=4,subImgSize=(260,210),legends=legends,useSVG=True,drawOptions=opts)
    (FIG/(kind+'_scaffolds.svg')).write_text(svg)
    im=Draw.MolsToGridImage(ms,molsPerRow=4,subImgSize=(260,210),legends=legends,drawOptions=opts)
    im.save(FIG/(kind+'_scaffolds.png'))

# Show representative actual pairs, selected by coverage quantiles (not activity).
sorted_q=np.argsort(sim.max(axis=1));sel=[sorted_q[int(round(q*(len(test)-1)))] for q in [.05,.25,.5,.75,.95]]
pair_mols=[];legends=[]
for i in sel:
    j=int(sim[i].argmax());pair_mols += [mols[test.Molecule_Name.iloc[i]],mols[train.Molecule_Name.iloc[j]]]
    legends += [f'Test: {test.Molecule_Name.iloc[i]}',f'Train: {train.Molecule_Name.iloc[j]}\nTanimoto = {sim[i,j]:.3f}']
opts=Draw.MolDrawOptions();opts.legendFontSize=15
svg=Draw.MolsToGridImage(pair_mols,molsPerRow=2,subImgSize=(400,240),legends=legends,useSVG=True,drawOptions=opts)
(FIG/'example_neighbor_pairs.svg').write_text(svg)
Draw.MolsToGridImage(pair_mols,molsPerRow=2,subImgSize=(400,240),legends=legends,drawOptions=opts).save(FIG/'example_neighbor_pairs.png')
log(json.dumps({'identity':identity,'scaffolds':scaffold_summary,'similarity':summary['similarity'],'test_clustering':cluster_rows},indent=2))
log('AUDIT COMPLETE')
