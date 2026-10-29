import time,subprocess,json
from pathlib import Path
p=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023'); end=1792818000.0
(p/'rental-guard.json').write_text(json.dumps({'instance':57424368,'status':'armed','deadline':end}))
while time.time()<end:
 if (p/'rental-complete').exists():break
 time.sleep(30)
else:
 r=subprocess.run(['/Users/adeliyaleleytner/.local/bin/vastai','stop','instance','57424368','--raw'],capture_output=True,text=True)
 (p/'rental-guard.json').write_text(json.dumps({'instance':57424368,'status':'stop_requested','returncode':r.returncode}))
