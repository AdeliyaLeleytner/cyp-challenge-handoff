"""Reproducible read-only source comparison. No training and no activity pooling across sources."""
from pathlib import Path
import json, hashlib, re, pickle, sys, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger, DataStructs
from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors, rdFingerprintGenerator
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold
RDLogger.DisableLog('rdApp.*')
ROOT=Path(__file__).resolve().parent
CAM=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023')
A=CAM/'remote/assets'; B=A/'reference/public_data'
USER=Path('/Users/adeliyaleleytner/Downloads/Telegram Desktop/chembl_CYP_final_ChEMBL_37.csv')
OLD=Path('/Users/adeliyaleleytner/.local/share/cyp-inhibition/reciprocal-comparison-20261023/full/prepared/aux.csv')
TARGETS=['CYP1A2','CYP2C9','CYP2D6','CYP3A4','CYP2C19']
PROPS=['MW','cLogP','TPSA','HBD','HBA','RotB','AromaticRings','FractionCSP3','HeavyAtoms','NitrogenAtoms']
manifest=[]; datasets={}; rawframes={}
def read(path):
    raw=path.read_bytes();df=pd.read_csv(path)
    manifest.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(df),'columns':list(df)})
    return df
def write(name,df):df.to_csv(ROOT/'tables'/name,index=False)
def save(name,obj):(ROOT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def normalize(smiles):
    try:
        m=Chem.MolFromSmiles(smiles)
        if m is None:return {'smiles':smiles,'valid':False}
        original_key=Chem.MolToInchiKey(m)
        m=rdMolStandardize.Uncharger().uncharge(rdMolStandardize.FragmentParent(m))
        # Fragment selection may leave RingInfo uninitialized for acyclic fragments.
        Chem.SanitizeMol(m)
        iso=Chem.MolToSmiles(m,canonical=True,isomericSmiles=True)
        iso_key=Chem.MolToInchiKey(m)
        Chem.RemoveStereochemistry(m)
        parent=Chem.MolToSmiles(m,canonical=True,isomericSmiles=False)
        sc=Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(m),isomericSmiles=False)
        return dict(smiles=smiles,valid=True,iso=iso,parent=parent,original_key=original_key,iso_key=iso_key,scaffold=sc,
          MW=Descriptors.MolWt(m),cLogP=Descriptors.MolLogP(m),TPSA=rdMolDescriptors.CalcTPSA(m),HBD=Lipinski.NumHDonors(m),HBA=Lipinski.NumHAcceptors(m),RotB=Lipinski.NumRotatableBonds(m),AromaticRings=rdMolDescriptors.CalcNumAromaticRings(m),FractionCSP3=rdMolDescriptors.CalcFractionCSP3(m),HeavyAtoms=m.GetNumHeavyAtoms(),NitrogenAtoms=sum(x.GetAtomicNum()==7 for x in m.GetAtoms()),CarbonAtoms=sum(x.GetAtomicNum()==6 for x in m.GetAtoms()))
    except Exception as e:return {'smiles':smiles,'valid':False,'error':type(e).__name__}
def attach(df,smiles='SMILES'):
    x=df.rename(columns={smiles:'smiles'}).copy()
    return x.merge(CACHE,on='smiles',how='left',validate='many_to_one')
def wide(frame,smiles,cols,endpoint):
    rows=[]
    for col,gene in cols.items():
        x=frame[[smiles,col]].rename(columns={smiles:'smiles',col:'value'}).dropna(subset=['value'])
        x['gene']=gene;x['endpoint']=endpoint;x['relation']='point';rows.append(x)
    return pd.concat(rows,ignore_index=True) if rows else pd.DataFrame(columns=['smiles','value','gene','endpoint','relation'])
def add(name,structures,labels,source_rows,meaning,used):
    s=attach(structures.drop_duplicates(),'smiles'); l=attach(labels,'smiles') if len(labels) else labels.copy()
    datasets[name]={'structures':s,'labels':l,'source_rows':source_rows,'meaning':meaning,'used':used}
def main():
    global CACHE
    t=time.time()
    u=read(USER); train=read(A/'official-train.csv'); test=read(A/'official-test.csv')
    ch=read(B/'chembl_all_isoforms.csv'); ve=read(B/'pubchem_all_isoforms.csv'); single=read(B/'single_concentration.csv');tdi=read(B/'tdi.csv');emax=read(B/'emax.csv')
    newer=read(A/'new_public/auxiliary_wide.csv');pat=read(A/'new_public_patents/auxiliary_wide.csv');old=read(OLD)
    allsmiles=set(u.std_smiles)|set(train.SMILES)|set(test.SMILES)|set(ch.smiles)|set(ve.smiles)|set(single.smiles)|set(tdi.smiles)|set(emax.smiles)|set(newer.SMILES)|set(pat.SMILES)|set(old.SMILES)
    cachepath=ROOT/'structure_cache_v2.pkl'; cache=pickle.loads(cachepath.read_bytes()) if cachepath.exists() else {}
    missing=sorted(allsmiles-set(cache));print('normalize',len(missing),'of',len(allsmiles),flush=True)
    if missing:
        with ProcessPoolExecutor(max_workers=4) as pool:
            for i,v in enumerate(pool.map(normalize,missing,chunksize=100)):
                cache[v['smiles']]=v
                if (i+1)%5000==0:print('normalized',i+1,flush=True)
        cachepath.write_bytes(pickle.dumps(cache))
    CACHE=pd.DataFrame([cache[s] for s in sorted(allsmiles)])
    write('invalid_structures.csv',CACHE[~CACHE.valid])
    # Preserve task and relation literally: user has no schema documentation.
    ul=u.rename(columns={'std_smiles':'smiles','y':'value','task':'endpoint','y_type':'relation'})
    add('User_ChEMBL37',ul[['smiles']],ul,len(u),'User y; hts/ic50 and point/upper_bound preserved; units/aggregation unverified','not trained')
    add('Official_TRAIN',train[['SMILES']].rename(columns={'SMILES':'smiles'}),wide(train,'SMILES',{g+'_pIC50_direct_inhibition':g for g in TARGETS[:4]},'pIC50_direct'),len(train),'Challenge direct pIC50 with confidence intervals','all experiments')
    add('Official_TEST',test[['SMILES']].rename(columns={'SMILES':'smiles'}),pd.DataFrame(),len(test),'Structures only; no experimental labels','prediction only')
    sl=single[['smiles','enzyme','log2fc_estimate']].rename(columns={'enzyme':'gene','log2fc_estimate':'value'});sl['endpoint']='log2FC';sl['relation']='point'
    add('Official_single',single[['smiles']],sl,len(single),'Single concentration log2 fold change, not potency','auxiliary heads')
    add('Official_TDI',tdi[['smiles']],wide(tdi,'smiles',{g.lower()+'_pic50_tdi_condition':g for g in TARGETS[:4]},'pIC50_TDI_condition'),len(tdi),'Potency under TDI condition; not a TDI binary call','selected auxiliary heads')
    ee=pd.concat([wide(emax,'smiles',{g.lower()+'_emax_vs_pos_ctrl_'+kind:g for g in TARGETS[:4]},'Emax_'+kind) for kind in ['direct_inhibition','tdi_condition']])
    add('Official_Emax',emax[['smiles']],ee,len(emax),'Max effect relative to positive control, not potency','selected auxiliary heads')
    cl=wide(ch,'smiles',{g.lower()+'_pic50':g for g in TARGETS},'ChEMBL_potency')
    add('Briford_ChEMBL_raw',ch[['smiles']],cl,len(ch),'Author public ChEMBL snapshot, aggregated potency','source of final model')
    vl=ve[['smiles','isoform','max_response']].rename(columns={'isoform':'gene','max_response':'value'}).dropna(subset=['value']);vl['gene']=vl.gene.str.upper();vl['endpoint']='qHTS_max_response';vl['relation']='point'
    add('Briford_Veith_raw',ve[['smiles']],vl,len(ve),'Raw qHTS maximum response; includes inactive observations','source of final model')
    excl=set(datasets['Official_TRAIN']['structures'].parent.dropna())|set(datasets['Official_TEST']['structures'].parent.dropna())
    cc=attach(ch,'smiles');cc=cc[cc.valid & ~cc.parent.isin(excl)].drop_duplicates('parent')
    add('Ours_ChEMBL_used',cc[['smiles']],wide(cc,'smiles',{g.lower()+'_pic50':g for g in TARGETS},'ChEMBL_potency'),len(cc),'Parent-filtered/deduplicated briford ChEMBL','final union18 and 2D6 auxiliary')
    vp=ve.pivot_table(index='smiles',columns='isoform',values='max_response').clip(-150,50).reset_index()
    vv=attach(vp,'smiles');vv=vv[vv.valid & ~vv.parent.isin(excl)].drop_duplicates('parent')
    add('Ours_Veith_used',vv[['smiles']],wide(vv,'smiles',{g.lower():g for g in TARGETS},'qHTS_max_response'),len(vv),'Mean by original SMILES and CYP; clipped [-150,50], parent-filtered','final union18 and 2D6 auxiliary')
    for tag,needle,ep in [('Ours_Tox21_used','tox21','pAC50'),('Ours_BindingDB_articles','native_articles','pIC50')]:
        cols={c:re.search(r'CYP(?:1A2|2C9|2D6|3A4)',c).group() for c in newer if c.startswith('aux_') and needle in c}
        nd=newer[newer[list(cols)].notna().any(axis=1)].copy()
        # Recorded training filter drops one normalized SMILES that cannot reparse.
        nd=nd[nd.SMILES.map(lambda s:cache[s]['valid'])]
        add(tag,nd[['SMILES']].rename(columns={'SMILES':'smiles'}),wide(nd,'SMILES',cols,ep),len(nd),'Equality-only eligible values; source/target/endpoint median','CheMeleon augmentation experiments only')
    cols={c:re.search(r'CYP(?:1A2|2C9|2D6|3A4)',c).group() for c in pat if c.startswith('aux_')}
    add('Ours_BindingDB_patents',pat[['SMILES']].rename(columns={'SMILES':'smiles'}),wide(pat,'SMILES',cols,'pIC50'),len(pat),'Equality-only patent IC50 median, October2026 snapshot','CheMeleon augmentation experiments only')
    for tag,prefix,ending,ep in [('Earlier_Jeremy_ChEMBL','chembl_','_ChEMBL_PIC50','ChEMBL_potency'),('Earlier_Jeremy_PubChem','pubchem_','_PubChem_qHTS','pAC50')]:
        od=old[old.Molecule_Name.str.startswith(prefix)].copy();cols={c:c.split('_')[0] for c in od if c.endswith(ending)}
        add(tag,od[['SMILES']].rename(columns={'SMILES':'smiles'}),wide(od,'SMILES',cols,ep),len(od),'Earlier prepared external subset; same-source overlap not independent data','previous Jeremy comparison')
    parentsets={n:set(d['structures'].parent.dropna()) for n,d in datasets.items()}
    isosets={n:set(d['structures'].iso.dropna()) for n,d in datasets.items()}
    scaffsets={n:set(d['structures'].scaffold.dropna())-{''} for n,d in datasets.items()}
    usednames=[n for n in datasets if n.startswith(('Ours_','Earlier_'))]
    external=set.union(*(parentsets[n] for n in usednames));allours=external|set.union(*(parentsets[n] for n in ['Official_TRAIN','Official_TDI','Official_Emax','Official_single']))
    finalexternal=parentsets['Ours_ChEMBL_used']|parentsets['Ours_Veith_used']
    memberships=datasets['User_ChEMBL37']['structures'].copy()
    for n,ss in parentsets.items():memberships['in_'+n]=memberships.parent.isin(ss)
    memberships['new_vs_all_existing']=~memberships.parent.isin(allours)
    memberships['eligible_new_excluding_test']=memberships.new_vs_all_existing & ~memberships.parent.isin(parentsets['Official_TEST']) & memberships.valid
    write('user_structure_membership.csv',memberships)
    novel=set(memberships.loc[memberships.eligible_new_excluding_test,'parent'])
    summary=[];activity=[];chemstats=[]
    for name,d in datasets.items():
        s=d['structures'];l=d['labels'];valid=s[s.valid];unique=valid.drop_duplicates('parent')
        row={'dataset':name,'source_rows':d['source_rows'],'label_values':len(l),'raw_smiles':len(s),'valid_raw_smiles':len(valid),'stereo_structures':len(isosets[name]),'parents':len(parentsets[name]),'scaffolds_nonempty':len(scaffsets[name]),'acyclic_parent_fraction':float(unique.scaffold.eq('').mean()),'carbon_free_parents':int(unique.CarbonAtoms.eq(0).sum()),'user_parent_overlap':len(parentsets[name]&parentsets['User_ChEMBL37']),'train_parent_overlap':len(parentsets[name]&parentsets['Official_TRAIN']),'test_parent_overlap':len(parentsets[name]&parentsets['Official_TEST']),'meaning':d['meaning'],'used':d['used']}
        for prop in PROPS:row[prop+'_median']=float(unique[prop].median())
        summary.append(row)
        for prop in PROPS:
            z=unique[prop].dropna();chemstats.append({'dataset':name,'property':prop,'n':len(z),'mean':z.mean(),'sd':z.std(),'q05':z.quantile(.05),'q25':z.quantile(.25),'median':z.median(),'q75':z.quantile(.75),'q95':z.quantile(.95)})
        if len(l):
            for (gene,ep,rel),z in l.groupby(['gene','endpoint','relation'],dropna=False):
                x=z.value.astype(float);activity.append({'dataset':name,'gene':gene,'endpoint':ep,'relation':rel,'rows':len(z),'parents':z.parent.nunique(),'min':x.min(),'q05':x.quantile(.05),'q25':x.quantile(.25),'median':x.median(),'q75':x.quantile(.75),'q95':x.quantile(.95),'max':x.max(),'mean':x.mean(),'sd':x.std()})
    write('dataset_comparison.csv',pd.DataFrame(summary));write('activity_statistics.csv',pd.DataFrame(activity));write('chemical_statistics.csv',pd.DataFrame(chemstats))
    overlaps=[]
    for a in datasets:
        for b in datasets:
            x,y=parentsets[a],parentsets[b];i=len(x&y)
            overlaps.append({'dataset_a':a,'dataset_b':b,'parent_intersection':i,'fraction_a':i/len(x),'jaccard':i/len(x|y),'stereo_intersection':len(isosets[a]&isosets[b]),'scaffold_intersection':len(scaffsets[a]&scaffsets[b])})
    write('pairwise_overlap.csv',pd.DataFrame(overlaps))
    # Literal user QC, without inferring flag definitions or censoring units.
    um=datasets['User_ChEMBL37']['labels'];write('user_target_task_relation.csv',pd.DataFrame(activity).query("dataset=='User_ChEMBL37'"))
    flags=[]
    for flag in ['stereo_undefined','has_stereo_sibling','any_preinc','implausible']:
        for (g,task),z in um.groupby(['gene','endpoint']):flags.append({'flag':flag,'gene':g,'task':task,'rows':len(z),'flagged_rows':int(z[flag].sum()),'fraction':float(z[flag].mean())})
    write('user_flags.csv',pd.DataFrame(flags));write('user_flagged_implausible.csv',um[um.implausible])
    qcs={'input_rows':len(u),'unique_supplied_inchikey':u.inchikey.nunique(),'unique_supplied_inchikey14':u.inchikey14.nunique(),'exact_duplicate_rows':int(u.duplicated().sum()),'duplicate_gene_inchikey_task':int(u.duplicated(['gene','inchikey','task']).sum()),'supplied_inchikey14_mismatch':int((u.inchikey.str[:14]!=u.inchikey14).sum()),'computed_original_inchikey_mismatch':int((um.inchikey!=um.original_key).sum()),'missing_spread':int(u.spread.isna().sum()),'point_with_zero_n_point':int(((u.y_type=='point')&(u.n_point==0)).sum()),'bound_with_points':int(((u.y_type=='upper_bound')&(u.n_point>0)).sum()),'spread_point_quantiles':u.loc[u.y_type=='point','spread'].quantile([0,.5,.9,.95,.99,1]).to_dict(),'preinc_is_not_verified_tdi':True,'y_scale_unverified':True,'unit_conversion_applied_to_user':False}
    save('quality.json',qcs)
    # Pair molecule/target values at two identity levels; no point treatment of bounds.
    pairs=[];pair_stats=[]
    for identity in ['iso','parent']:
        for comparator in ['Ours_ChEMBL_used','Briford_ChEMBL_raw','Earlier_Jeremy_ChEMBL','Official_TRAIN','Ours_Tox21_used']:
            cl=datasets[comparator]['labels'].query("gene in @TARGETS").groupby([identity,'gene']).value.median()
            for task in ['hts','ic50']:
                us=um[(um.endpoint==task)&(um.relation=='point')].groupby([identity,'gene']).value.median()
                joined=pd.concat([us.rename('user_y'),cl.rename('other_value')],axis=1,join='inner').dropna().reset_index();joined['delta']=joined.user_y-joined.other_value
                joined['identity']=identity;joined['comparator']=comparator;joined['user_task']=task;pairs.append(joined)
                for gene,z in joined.groupby('gene'):
                    pair_stats.append({'identity':identity,'comparator':comparator,'user_task':task,'gene':gene,'n_pairs':len(z),'median_delta':z.delta.median(),'median_abs_delta':z.delta.abs().median(),'within_0_1_fraction':z.delta.abs().le(.1).mean(),'abs_delta_gt_1_fraction':z.delta.abs().gt(1).mean(),'pearson':z.user_y.corr(z.other_value) if len(z)>2 else np.nan,'spearman':z.user_y.corr(z.other_value,method='spearman') if len(z)>2 else np.nan,'interpretation':'Numerical comparison only; user y units and aggregation unconfirmed'})
    pairs=pd.concat(pairs,ignore_index=True);write('paired_activity_values.csv',pairs);write('paired_activity_statistics.csv',pd.DataFrame(pair_stats))
    write('paired_largest_disagreements.csv',pairs.sort_values('delta',key=lambda x:x.abs(),ascending=False).head(250))
    # Same user molecule in multiple CYPs: co-measured panels, not clinical selectivity.
    corrs=[]
    for task in ['hts','ic50']:
        panel=um[(um.endpoint==task)&(um.relation=='point')].pivot_table(index='iso',columns='gene',values='value',aggfunc='median')
        for a in TARGETS[:4]:
            for b in TARGETS[:4]:
                z=panel[[a,b]].dropna() if a!=b else panel[[a]].dropna()
                corrs.append({'task':task,'target_a':a,'target_b':b,'n_shared':len(z),'spearman':1.0 if a==b else z.iloc[:,0].corr(z.iloc[:,1],method='spearman')})
    write('user_cross_target_correlations.csv',pd.DataFrame(corrs))
    # Structure geometry uses exact exhaustive reference pools for each TEST query.
    allparents=sorted(set.union(*parentsets.values()));pos={s:i for i,s in enumerate(allparents)}
    gen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048,includeChirality=False)
    fps=[gen.GetFingerprint(Chem.MolFromSmiles(s)) for s in allparents]
    refs={n:ss for n,ss in parentsets.items() if n not in ['Official_TEST','Official_single','Official_TDI','Official_Emax']}
    refs['Existing_all_labelled']=allours;refs['User_novel_excluding_TEST']=novel;refs['Existing_plus_user_novel']=allours|novel
    idx={n:np.array([pos[s] for s in sorted(ss)],dtype=int) for n,ss in refs.items()}
    testnorm=attach(test[['Molecule_Name','SMILES']],'SMILES');nn=[]
    print('similarity TEST queries',len(testnorm),'reference parents',len(allparents),flush=True)
    for qi,row in testnorm.iterrows():
        sims=np.array(DataStructs.BulkTanimotoSimilarity(fps[pos[row.parent]],fps))
        for name,ix in idx.items():
            k=ix[np.argmax(sims[ix])] if len(ix) else None
            nn.append({'Molecule_Name':row.Molecule_Name,'reference':name,'max_tanimoto':float(sims[k]) if k is not None else np.nan,'nearest_parent':allparents[k] if k is not None else None})
        if (qi+1)%150==0:print('similarity query',qi+1,flush=True)
    nn=pd.DataFrame(nn);write('test_nearest_neighbors.csv',nn)
    nns=[]
    for name,z in nn.groupby('reference'):
        a=z.max_tanimoto;nns.append({'reference':name,'reference_parents':len(refs[name]),'test_rows':len(z),'median':a.median(),'q10':a.quantile(.1),'q90':a.quantile(.9),'mean':a.mean(),'exact_matches':int(a.eq(1).sum()),'ge_0_5':int(a.ge(.5).sum()),'ge_0_7':int(a.ge(.7).sum()),'ge_0_9':int(a.ge(.9).sum())})
    write('test_similarity_summary.csv',pd.DataFrame(nns))
    gain=nn.pivot(index='Molecule_Name',columns='reference',values='max_tanimoto');gain['gain']=gain.Existing_plus_user_novel-gain.Existing_all_labelled
    write('test_coverage_increment.csv',gain[['Existing_all_labelled','User_novel_excluding_TEST','Existing_plus_user_novel','gain']].reset_index())
    uf=um.merge(memberships[['smiles','new_vs_all_existing','eligible_new_excluding_test']],on='smiles',validate='many_to_one')
    uf.to_csv(ROOT/'tables/user_rows_annotated.csv.gz',index=False,compression='gzip')
    long=pd.concat([d['labels'].assign(dataset=n) for n,d in datasets.items() if len(d['labels'])],ignore_index=True)
    # This long table preserves source and endpoint; it is not a pooled training target.
    long[['dataset','smiles','iso','parent','gene','endpoint','relation','value']].to_csv(ROOT/'tables/all_sources_long.csv.gz',index=False,compression='gzip')
    CACHE.to_csv(ROOT/'tables/structure_descriptors.csv.gz',index=False,compression='gzip')
    save('source_manifest.json',manifest)
    save('summary.json',{'datasets':len(datasets),'unique_raw_smiles':len(CACHE),'invalid_raw_smiles':int((~CACHE.valid).sum()),'user_rows':len(u),'user_parents':len(parentsets['User_ChEMBL37']),'existing_external_parents':len(external),'existing_all_labelled_parents':len(allours),'final_external_parents':len(finalexternal),'user_overlap_all_existing':len(parentsets['User_ChEMBL37']&allours),'user_novel_vs_all_existing':len(parentsets['User_ChEMBL37']-allours),'user_novel_excluding_TEST':len(novel),'user_overlap_TEST':len(parentsets['User_ChEMBL37']&parentsets['Official_TEST']),'user_overlap_TRAIN':len(parentsets['User_ChEMBL37']&parentsets['Official_TRAIN']),'test_queries_with_any_similarity_gain':int(gain.gain.gt(1e-12).sum()),'test_mean_similarity_gain':float(gain.gain.mean()),'runtime_seconds':time.time()-t,'normalization':'RDKit FragmentParent, Uncharger; stereo retained for iso and removed for parent. No tautomer canonicalization. Descriptors on neutral nonstereo parent. Empty scaffolds excluded from shared-scaffold counts.','similarity':'Morgan radius2,2048bits,no chirality; exhaustive max over each reference pool; all750TEST queries. Reference pool size affects max similarity.','user_metadata':'No preparation script/schema exists per user. y,spread,upper_bound direction and any_preinc semantics remain source labels, not verified experimental definitions.','lachrymator':'Write-up and figures only; no molecule table or code in pinned repository tree. Exact overlaps and empirical statistics unavailable.'})
    print('COMPLETE',json.dumps(json.loads((ROOT/'summary.json').read_text())),flush=True)
if __name__=='__main__':main()
