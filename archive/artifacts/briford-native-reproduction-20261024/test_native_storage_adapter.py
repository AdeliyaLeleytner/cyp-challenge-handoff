"""Synthetic I/O bridge test only; no learned models and no metric claim."""
from pathlib import Path
import json,numpy as np,pandas as pd,sys
sys.path.insert(0,'/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023')
from night.briford_native import MODELS,collect,sha,save
p=Path(__file__).resolve().parent;cfg=json.loads((p/'review-code/briford_config.json').read_text());cfg['output_dir']=str(p/'synthetic_adapter_test');out=Path(cfg['output_dir']);prep=Path(cfg['prepared_dir']);q=pd.read_csv(cfg['official_test'])
for mi,(short,name) in enumerate(MODELS.items()):
 spec=json.loads((prep/f'{short}.json').read_text());df=pd.read_csv(prep/f'{short}.csv',float_precision='round_trip');targets=spec['targets'];rng=np.random.default_rng(42+mi)
 for f,fold in enumerate(spec['folds']):
  d=out/short/f'fold{f}';d.mkdir(parents=True,exist_ok=True);val=df.iloc[fold['validation']];v=val[targets].fillna(5).to_numpy()+rng.normal(0,.4,(len(val),len(targets)))
  pred=pd.DataFrame(v,columns=targets);pred.insert(0,'molecule_name',val.molecule_name.to_numpy());pred.to_csv(d/'oof.csv',index=False,float_format='%.17g')
  v=4+np.linspace(-.4,.4,len(q))[:,None]+np.arange(len(targets))[None,:]*.03+mi*.01+f*.001
  pred=pd.DataFrame(v,columns=targets);pred.insert(0,'molecule_name',q.Molecule_Name.to_numpy());pred.to_csv(d/'test.csv',index=False,float_format='%.17g')
  save(d/'complete.json',{'status':'complete','files':{s:sha(d/s) for s in ['oof.csv','test.csv']}})
collect(cfg)
print('SYNTHETIC ADAPTER TEST ONLY: native OOF retrieval, aggregation, placement and official validator passed')
