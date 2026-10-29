"""Independent final assembly audit; no encoder/readout calls."""
import sys,json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
p=Path(__file__).parent;sys.path.insert(0,str(p/'worktree/night'));from p9_identity import validate
out=p/'results';rows=pd.read_csv(out/'embedding-rows.csv');expected=pd.read_csv(p.parent/'p9a/next-stage/official5655-structures.csv');bank=np.load(out/'embeddings.npy');assert bank.shape==(5655,256) and np.isfinite(bank).all();assert rows.Molecule_Name.tolist()==expected.Molecule_Name.tolist() and rows.SMILES.tolist()==expected.SMILES.tolist();ledger=[json.loads(x) for x in (out/'row-outcomes.jsonl').read_text().splitlines()];assert len(ledger)==5655 and len({x['row'] for x in ledger})==5655;ordered=sorted(ledger,key=lambda x:x['row']);assert [x['id'] for x in ordered]==rows.Molecule_Name.tolist() and [x['smiles'] for x in ordered]==rows.SMILES.tolist() and all(x['status']=='success' for x in ordered)
checked={};files={}
for f in sorted(out.glob('coordinates-*.npz')):
 co=np.load(f);files[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
 for key in co.files:
  if not key.startswith('z_'):continue
  i=int(key[2:]);assert i not in checked;checked[i]=validate(rows.SMILES.iloc[i],co[key],co[f'pos_{i}'])
assert set(checked)==set(range(5655));prior=json.load(open(p/'prior-snapshot/manifest.json'));indices=np.load(prior['files']['indices']['path']);v=np.load(prior['files']['features']['path']);assert np.array_equal(bank[indices],v)
report={'status':'complete_pass','persisted_coordinate_rows':len(checked),'expected_rows':5655,'flagged':[],'specified_atom_checks':sum(x['specified_atom_checks'] for x in checked.values()),'specified_bond_checks':sum(x['specified_bond_checks'] for x in checked.values()),'enhanced_group_rows':sum(x['enhanced_groups']>0 for x in checked.values()),'old_vectors_reused_bitwise':len(indices),'row_outcomes_exact_unique_complete':True,'exact_original_order_and_SMILES':True,'embeddings_sha256':hashlib.sha256((out/'embeddings.npy').read_bytes()).hexdigest(),'coordinate_files':files,'validator_sha256':hashlib.sha256((p/'worktree/night/p9_identity.py').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'no_model_inference':True};(p/'COORDINATE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='coordinate_files'}))
