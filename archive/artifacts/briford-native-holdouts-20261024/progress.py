from pathlib import Path
import json,datetime
p=Path(__file__).resolve().parent
print(datetime.datetime.now(datetime.timezone.utc).isoformat())
for name in ['own750','briford529']:
 root=p/'remote/holdouts'/name
 done=list((root/'results').glob('*/fold*/complete.json'))
 jobs=list((root/'results').glob('*/fold*/job.json'))
 print(name, 'completed',len(done),'of20; prepared jobs',len(jobs))
 print({m:len(list((root/'results'/m).glob('fold*/complete.json'))) for m in ['union18','2d6isoform6','mtaux8','2d6single']})
 for f in (root/'results').glob('*/fold*/worker.log'):
  lines=f.read_text(errors='replace').splitlines()
  failures=[s for s in lines if 'Traceback' in s or 'Error:' in s]
  if failures:print(str(f),failures[-2:])
