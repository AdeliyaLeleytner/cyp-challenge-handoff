from pathlib import Path
import json
import pandas as pd
import numpy as np
P=Path(__file__).resolve().parent;T=P/'tables'
u=pd.read_csv(T/'user_rows_annotated.csv.gz');long=pd.read_csv(T/'all_sources_long.csv.gz');desc=pd.read_csv(T/'structure_descriptors.csv.gz');s=json.loads((P/'summary.json').read_text())
def write(n,d):d.to_csv(T/n,index=False)
novel=[]
for (task,rel),z in u.groupby(['endpoint','relation']):
 a=z[z.eligible_new_excluding_test];novel.append({'task':task,'relation':rel,'all_rows':len(z),'all_parents':z.parent.nunique(),'novel_rows_excluding_TEST':len(a),'novel_parents_excluding_TEST':a.parent.nunique(),'already_known_parent_rows':int((~z.new_vs_all_existing).sum())})
write('novelty_by_label_type.csv',pd.DataFrame(novel))
known_names=[n for n in long.dataset.unique() if n.startswith(('Ours_','Earlier_'))]+['Official_TRAIN','Official_single','Official_TDI','Official_Emax']
existing_smiles=set(long.loc[long.dataset.isin(known_names),'smiles']);existing_desc=desc[desc.smiles.isin(existing_smiles)]
ud=desc[desc.smiles.isin(u.smiles.unique())];test_path=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/remote/assets/official-test.csv');td=desc[desc.smiles.isin(pd.read_csv(test_path).SMILES)]
identity=[]
for key in ['iso','parent','iso_key']:
 a=set(ud[key].dropna());b=set(existing_desc[key].dropna());tt=set(td[key].dropna());identity.append({'identity':key,'user_unique':len(a),'archive_with_numeric_labels_unique':len(b),'overlap':len(a&b),'novel_excluding_TEST':len(a-b-tt),'TEST_overlap':len(a&tt),'note':'Archive here includes structures with at least one numeric label in the comparison table; differs slightly from all source-table rows.'})
a=set(ud.iso_key.str[:14]);b=set(existing_desc.iso_key.dropna().str[:14]);tt=set(td.iso_key.str[:14]);identity.append({'identity':'normalized_InChIKey14','user_unique':len(a),'archive_with_numeric_labels_unique':len(b),'overlap':len(a&b),'novel_excluding_TEST':len(a-b-tt),'TEST_overlap':len(a&tt),'note':'InChI normalization can merge some tautomer forms that non-tautomer-canonical parent SMILES keep separate.'})
write('identity_sensitivity.csv',pd.DataFrame(identity))
coverage=[]
existing_potency=long[long.dataset.isin(['Ours_ChEMBL_used','Earlier_Jeremy_ChEMBL','Official_TRAIN','Ours_BindingDB_articles','Ours_BindingDB_patents'])]
ch=long[long.dataset=='Ours_ChEMBL_used'];pair_ch=set(zip(ch.iso,ch.gene));pair_any=set(zip(existing_potency.iso,existing_potency.gene))
u['known_iso_target_in_our_ChEMBL']=[(i,g) in pair_ch for i,g in zip(u.iso,u.gene)]
u['known_iso_target_in_potency_sources']=[(i,g) in pair_any for i,g in zip(u.iso,u.gene)]
for (gene,task,rel),z in u.groupby(['gene','endpoint','relation']):coverage.append({'gene':gene,'task':task,'relation':rel,'rows':len(z),'existing_ChEMBL_pair_rows':int(z.known_iso_target_in_our_ChEMBL.sum()),'new_pair_vs_ChEMBL_rows':int((~z.known_iso_target_in_our_ChEMBL).sum()),'new_pair_vs_potency_sources_rows':int((~z.known_iso_target_in_potency_sources).sum()),'new_structure_rows':int(z.eligible_new_excluding_test.sum())})
write('user_label_novelty.csv',pd.DataFrame(coverage))
write('user_novel_structures.csv',u[u.eligible_new_excluding_test][['smiles','iso','parent','gene','endpoint','relation','value','n_point','n_bound','n_assay','spread','any_preinc','implausible']])
sp=u[u.eligible_new_excluding_test].drop_duplicates('parent');sc_existing=set(existing_desc.scaffold.dropna())-{''};sc_user=set(sp.scaffold.dropna())-{''}
s['novel_user_scaffolds_vs_numeric_archive']=len(sc_user-sc_existing)
s['user_numeric_structure_fraction_existing']=s['user_overlap_all_existing']/s['user_parents']
s['upper_bound_rows']=int(u.relation.eq('upper_bound').sum());s['upper_bound_fraction']=float(u.relation.eq('upper_bound').mean())
s['novelty_by_label_type']=novel
for task in ['hts','ic50']:
 pairs=pd.read_csv(T/'paired_activity_values.csv',low_memory=False);z=pairs[(pairs.identity=='iso')&(pairs.comparator=='Ours_ChEMBL_used')&(pairs.user_task==task)]
 s['matched_'+task]={'pairs':len(z),'median_absolute_numeric_difference':float(z.delta.abs().median()),'within_0_1_fraction':float(z.delta.abs().le(.1).mean()),'beyond_1_fraction':float(z.delta.abs().gt(1).mean())}
# Descriptive bounds across the flags; no semantic validity filter inferred.
q=[]
for flag in ['n_point','n_bound','n_assay','spread']:
 for (task,rel),z in u.groupby(['endpoint','relation']):
  a=z[flag].dropna();q.append({'column':flag,'task':task,'relation':rel,'nonmissing':len(a),'zero':int(a.eq(0).sum()),'one':int(a.eq(1).sum()),'median':a.median(),'q95':a.quantile(.95),'max':a.max()})
write('user_support_statistics.csv',pd.DataFrame(q))
write('largest_user_spread.csv',u[u.relation=='point'].sort_values('spread',ascending=False).head(100))
write('source_descriptor_extremes.csv',desc[desc.valid].nlargest(100,'MW')[['smiles','parent','MW','cLogP','TPSA','CarbonAtoms']])
bio=[
 ['pIC50','-log10(IC50 in mol/L)','Concentration producing half-maximal inhibition under a specified assay','Depends on substrate, enzyme system and incubation; not interchangeable with Ki','Official TRAIN / ChEMBL'],
 ['pAC50','-log10(AC50 in mol/L)','Concentration giving half of the fitted assay response','Not automatically identical to IC50 or Kd','Tox21 / earlier PubChem'],
 ['log2FC','log2 ratio of assay signal','Effect at a fixed tested concentration','Not a concentration or pIC50; interpretation needs assay sign convention','Official single-concentration'],
 ['max_response','Signed normalized assay response','qHTS response at the top concentration','Activity amplitude rather than potency; source includes inactive curves','Veith'],
 ['Emax','Response relative to positive control','Fitted maximal effect','Do not convert blindly to percent inhibition or pIC50','Official Emax'],
 ['TDI condition pIC50','pIC50 under a preincubation condition','Potency measured under TDI assay conditions','One preincubation flag does not itself establish time-dependent inactivation','Official TDI'],
 ['User y','Undocumented; numerical agreement with existing log potency','Preserved exactly as supplied','No verified units, aggregation rule, original assay IDs or protocol','User CSV'],
 ['User upper_bound','Upper bound label in supplied y coordinates','A limit rather than an exact value','If y is pIC50, y<5 would mean IC50>10 micromolar; direction/conversion requires confirmation','User CSV'],
 ['any_preinc','Boolean flag; generation rule unavailable','Possible indicator of preincubation in source metadata','Not a measured TDI class, kinact or KI','User CSV'],
 ['spread','Numeric summary; generation rule unavailable','Provided measure of within-group dispersion','Do not equate with SD, credible interval or assay error without definition','User CSV']]
write('biological_meaning.csv',pd.DataFrame(bio,columns=['quantity','units','biological_meaning','limitation','source']))
methods=[
 ['User ChEMBL37','60882 aggregated rows;28822 exact structures;27815 normalized parents','hts/ic50;point/upper_bound;4CYPs','No preparation script or original assay IDs','Not used in any model yet','Not known'],
 ['Our final submitted model','Official4905 plus26825 external parents for union18;specialists use subsets','Separate official,ChEMBL andVeith auxiliary heads','Archived input files, hashes, fold fits and source code','5scaffold folds x2seeds;4D-MPNN families','No retrieved catalogue-neighbour training tier'],
 ['briford archived raw files','25841ChEMBL rows;85535Veith assay rows;actual measured in this audit','5CYP potency and5CYP max_response plus official arms','Public tables available; actual historic model/OOF not available','Our reconstruction differs in standardization, partitions and calibration','Compare actual tables directly'],
 ['briford current write-up','Author reports24918ChEMBL skeletons,16546Veith compounds,31670union compounds','Separate heads;fourD-MPNN family ensemble','Author-reported counts; may differ from archived snapshots and identity policy','Published method includes calibration for train/test population shift','Author explanation, not an independently replayed experiment'],
 ['lachrymator pinned write-up','Author reports88683retrieved neighbours;4999admitted;labelled corpus size unspecified','Public bioactivity pretraining plus calculated properties;source tables unspecified','README+6figures+license only;no dataset, code or exact folds','Representation-diverse ensemble;Butina cluster-disjoint folds;nonnegative stacking','4999neighbours have calculated properties and no assay endpoints']]
write('pipeline_comparison.csv',pd.DataFrame(methods,columns=['pipeline','data_size_and_basis','labels','available_evidence','model_and_split','neighbour_or_scope_note']))
(P/'summary.json').write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'new_label_rows':coverage,'novelty':novel,'new_scaffolds':s['novel_user_scaffolds_vs_numeric_archive']},ensure_ascii=False))
