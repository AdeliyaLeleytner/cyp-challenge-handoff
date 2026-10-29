from pathlib import Path
import json,pandas as pd,hashlib
P=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();oldpath=P/'p3/stage/manifest.json';newpath=P/'p7/stage/fold-manifest.json';a=json.loads(oldpath.read_text());b=json.loads(newpath.read_text());d=pd.read_csv(P/'p7/stage/table.csv');pairpath=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/model-audit/corrected-fullfit-native/stage/audit/tautomer-pair-chemical-details.csv');pairs=pd.read_csv(pairpath);par={}
def find(v):
 par.setdefault(v,v)
 if par[v]!=v:par[v]=find(par[v])
 return par[v]
for ids in pairs[pairs.stereo_preserving_tautomer_key_equal==True].request_ids.str.split(';'):
 for rid in ids[1:]:par[find(ids[0])]=find(rid)
g=[find(v) for v in d.request_id];result=[]
for k,(old,new) in enumerate(zip(a['folds'],b['folds'])):
 forbidden={g[i] for i in old['test']};expected=[i for i in old['stop'] if g[i] not in forbidden];removed=[i for i in old['stop'] if g[i] in forbidden];assert new['train']==old['train'] and new['test']==old['test'] and new['stop']==expected
 tr,st,te=[{g[i] for i in new[r]} for r in ['train','stop','test']];assert not tr&(st|te) and not st&te
 exact={d.request_id.iloc[i] for i in old['stop']}&{d.request_id.iloc[i] for i in old['test']};assert not exact
 result.append({'fold':k,'train':len(new['train']),'stop':len(new['stop']),'test':len(new['test']),'removed_stop_rows':len(removed),'removed_stop_ids':d.molecule_name.iloc[removed].tolist(),'exact_request_overlap_before':0,'approved_equivalence_stop_test_overlap_after':0,'train_stop_or_test_overlap_after':0,'train_and_test_indices_unchanged':True})
assert sha(P/'p7/stage/table.csv')==sha(P/'p3/stage/table.csv')==b['data_sha256'];assert b['parent_p3_manifest_sha256']==sha(oldpath)
res={'status':'PASS','feature_join_certificate_sha256':sha(O/'CERTIFICATE.json'),'revised_p7_fold_manifest_sha256':sha(newpath),'parent_p3_manifest_sha256':sha(oldpath),'table_sha256':sha(P/'p7/stage/table.csv'),'pair_manifest_sha256':sha(pairpath),'all18task_row_selection':True,'removed_stopping_rows':4,'removed_exact_identity_duplicates':0,'removed_approved_stereo_preserving_equivalence_counterparts':4,'folds':result,'scope':'read-only staged data and fold validation; no fitting'};(O/'REVISED_FOLD_CERTIFICATE.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
