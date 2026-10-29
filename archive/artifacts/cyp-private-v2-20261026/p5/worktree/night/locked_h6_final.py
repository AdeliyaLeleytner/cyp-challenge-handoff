"""Dedicated final recipe entrypoint: no family/mode reselection is allowed."""
from pathlib import Path
import importlib.metadata,json,sys
from .admet_full_contract_v1 import require,ContractError
ROOT=Path(__file__).resolve().parents[1]

def check_locked_config(cfg):
    expected={'name':'lightgbm__adme720','family':'lightgbm','view':'adme_admet','grid':[{'num_leaves':7,'max_depth':3},{'num_leaves':15,'max_depth':4}]}
    require(cfg.get('portfolio')==[expected] and cfg.get('final_selection_mode')=='validated_per_target_pair','Final recipe is fixed to H6 ADME720')
    require(cfg.get('blend_modes')==['per_target'] and cfg.get('use_external_tabpfn') is False,'Final recipe cannot change blend mode or add TabPFN')
    require(cfg.get('bridge_phase')=='select' and cfg.get('model_seed')==42,'Final H6 stage/seed changed')
    require(cfg.get('submission_lane')=='native_published_placement' and cfg.get('save_final_models') is True,'Final serving/model preservation contract changed')
    expected_runtime=cfg.get('required_runtime');require(isinstance(expected_runtime,dict) and set(expected_runtime)=={'numpy','pandas','scikit-learn','lightgbm','rdkit','torch','chemprop'},'Exact H6 CPU runtime must be pinned')
    actual={k:importlib.metadata.version(k) for k in expected_runtime};require(actual==expected_runtime,'Final CPU runtime differs from H6 evaluation; do not substitute GPU environment')
    return actual

def main():
    try:check_locked_config(json.loads((ROOT/'final_feature_config.json').read_text()))
    except (ContractError,OSError) as exc:
        print(json.dumps({'event':'locked_h6_blocked','error':str(exc),'fits_started':0}));raise SystemExit(2)
    from .final_feature_run import main as execute
    execute()
if __name__=='__main__':main()
