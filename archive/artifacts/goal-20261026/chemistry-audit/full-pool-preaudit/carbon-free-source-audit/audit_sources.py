#!/usr/bin/env python3
"""Read-only, bounded trace of seven carbon-free requests to saved source records."""
from pathlib import Path
import datetime, hashlib, json
import pandas as pd
from rdkit import Chem, rdBase

OUT=Path(__file__).resolve().parent
BASE=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/fullfit-strae-prep/stage/original_full')
entries=json.loads((OUT.parent/'no-carbon-molecules.json').read_text())
smiles={e['SMILES'] for e in entries}
pub=pd.read_csv(BASE/'raw/pubchem_all_isoforms.csv')
ch=pd.read_csv(BASE/'raw/chembl_all_isoforms.csv')
pub=pub[pub.smiles.isin(smiles)].copy();ch=ch[ch.chembl_id.eq('CHEMBL69710')].copy()
pub.to_csv(OUT/'saved-pubchem-matched-rows.csv',index=False)
ch.to_csv(OUT/'saved-chembl-matched-rows.csv',index=False)
primary=json.loads(json.loads((OUT/'primary-0.json').read_text())['value']['content'][0]['text'])
pc={r['CID']:r for r in primary['records']}
chembl=json.loads(json.loads((OUT/'primary-1.json').read_text())['value']['content'][0]['text'])['compounds'][0]
def canonical(s):
 m=Chem.MolFromSmiles(s)
 return Chem.MolToSmiles(m,isomericSmiles=True) if m else None
records=[]
for e in entries:
 for (sid,cid,orig),g in pub[pub.smiles.eq(e['SMILES'])].groupby(['sid','cid','orig_smiles']):
  ref=pc[int(cid)]
  records.append(dict(request_id=e['request_id'],request_smiles=e['SMILES'],source='PubChem/Veith',sid=int(sid),cid=int(cid),original_smiles=orig,primary_smiles=ref['SMILES'],primary_name=ref.get('IUPACName'),primary_synonyms=ref.get('synonyms'),source_rows=len(g),original_matches_primary=canonical(orig)==canonical(ref['SMILES']),request_matches_original=canonical(e['SMILES'])==canonical(orig),request_fragments=len(Chem.GetMolFrags(Chem.MolFromSmiles(e['SMILES']))),original_fragments=len(Chem.GetMolFrags(Chem.MolFromSmiles(orig))),max_response_by_isoform=dict(zip(g.isoform,g.max_response)),activity_outcomes=dict(zip(g.isoform,g.activity_outcome)),primary_url=f'https://pubchem.ncbi.nlm.nih.gov/compound/{cid}'))
 for r in ch[ch.smiles.eq(e['SMILES'])].to_dict('records'):
  records.append(dict(request_id=e['request_id'],request_smiles=e['SMILES'],source='ChEMBL',chembl_id=r['chembl_id'],original_smiles=r['orig_smiles'],primary_smiles=chembl['smiles'],primary_name=chembl['pref_name'],original_matches_primary=canonical(r['orig_smiles'])==canonical(chembl['smiles']),request_matches_original=canonical(e['SMILES'])==canonical(r['orig_smiles']),saved_inchi_key=r['inchi_key'],primary_inchi_key=chembl['inchi_key'],source_rows=1,n_measurements=int(r['n_measurements']),cyp3a4_pic50=r['cyp3a4_pic50'],primary_url='https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL69710/'))
(OUT/'source-identity-comparisons.json').write_text(json.dumps(records,indent=2)+'\n')
native=[]
for name in ['union18','2d6isoform6']:
 d=pd.read_csv(BASE/f'prepared/{name}.csv');sub=d[d.smiles.isin(smiles)].copy();sub.insert(0,'component',name);native.append(sub)
pd.concat(native).to_csv(OUT/'native-training-rows.csv',index=False)
ammonia=pub[pub.smiles.eq('N')].groupby('isoform').max_response.mean().to_dict()
summary=dict(audited_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),n_requests=7,n_distinct_pubchem_cids=pub.cid.nunique(),n_source_records=len(records),n_pubchem_assay_rows=len(pub),n_chembl_aggregated_rows=len(ch),all_saved_originals_match_live_primary=all(r['original_matches_primary'] for r in records),intact_requests=sorted({r['request_smiles'] for r in records if r['request_matches_original']}),fragmented_requests=sorted({r['request_smiles'] for r in records if not r['request_matches_original']}),ammonia_pooled_max_response=ammonia,rdkit=rdBase.rdkitVersion,interpretation='Saved orig_smiles are source structure evidence; id-map originals are already cleaned pool representations. No data or labels were modified. Matching primary database records does not verify the physical assayed specimen or coordination geometry.')
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
inputs=[BASE/'raw/pubchem_all_isoforms.csv',BASE/'raw/chembl_all_isoforms.csv',BASE/'prepared/union18.csv',BASE/'prepared/2d6isoform6.csv',OUT.parent/'no-carbon-molecules.json']
(OUT/'input-sha256.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},indent=2)+'\n')
print(json.dumps(summary,indent=2))
