from pathlib import Path
import os,sys,json,time,subprocess,hashlib,shutil
import torch
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs';OUT.mkdir(exist_ok=True)
protocol=json.loads((ROOT/'protocol.json').read_text());print('FROZEN_PROTOCOL',json.dumps(protocol),flush=True)
# Five fresh CheMeleon fits are tracked in a separate immutable ORX run.
core=Path(json.loads((ROOT/'core_run.json').read_text())['path'])
wait_started=time.monotonic()
while not (core/'outputs/core-complete.json').exists():
    assert time.monotonic()-wait_started<1800,'Core stage did not finish within30min; inspect its run'
    time.sleep(10)
for f in range(5):
    shutil.copytree(core/f'outputs/jeremy_{f}/chemeleon',OUT/f'jeremy_{f}/chemeleon',dirs_exist_ok=True)
print('REUSED_INDEPENDENT_CORE',str(core),flush=True)
jobs=[('ensemble',x) for x in protocol['outer_sets']]
active={};records=[];start=time.monotonic();free=list(range(torch.cuda.device_count()))
while jobs or active:
    while jobs and free:
        kind,name=jobs.pop(0);gpu=free.pop(0);logpath=OUT/f'{kind}-{name}.log';log=logpath.open('w');env=os.environ.copy();env['CUDA_VISIBLE_DEVICES']=str(gpu)
        p=subprocess.Popen([sys.executable,'-u','worker.py',kind,name],stdout=log,stderr=subprocess.STDOUT,env=env)
        active[p.pid]={'process':p,'log':log,'gpu':gpu,'kind':kind,'name':name,'started':time.time()};print('LAUNCHED',kind,name,'GPU',gpu,'PID',p.pid,flush=True)
    for pid,r in list(active.items()):
        code=r['process'].poll()
        if code is None:continue
        r['log'].close();rec={k:v for k,v in r.items() if k not in ['process','log']};rec['exit_code']=code;rec['finished']=time.time();records.append(rec);free.append(r['gpu']);del active[pid]
        (OUT/'job-ledger.json').write_text(json.dumps(records,indent=2));print('JOB_FINISHED',json.dumps(rec),flush=True)
        if code!=0:
            print('JOB_FAILURE_LOG',str(OUT/f"{r['kind']}-{r['name']}.log"),flush=True)
    if time.monotonic()-start>7200:
        for r in active.values():r['process'].terminate()
        raise TimeoutError('2h training bound reached; preserve all partial evidence')
    if active:time.sleep(5)
assert len(records)==6 and all(r['exit_code']==0 for r in records),'One or more worker jobs failed; inspect ledger and logs'
subprocess.run([sys.executable,'-u','evaluate_comparison.py'],check=True)
print('COMPARISON_COMPLETE',flush=True)
