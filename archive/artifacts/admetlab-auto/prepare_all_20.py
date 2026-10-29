"""Prepare the full20-row queue and import the verified pilot without resubmission."""
from pathlib import Path
import json, shutil
from collect import Collector,ROOT,sha,save

def prepare():
    collector=Collector(ROOT/'data/molecules.csv',ROOT/'output-all-20',20)
    source=ROOT/'output-pilot-20/batches/001'
    seeded=False
    try:
        if not collector.completed(0) and (source/'result.csv').exists():
            state=json.loads((source/'state.json').read_text())
            meta=json.loads((source/'download.json').read_text())
            digest=sha(source/'result.csv')
            if state['phase']!='complete' or digest!=state['csv_sha256'] or digest!=meta['sha256']:
                raise ValueError('Пробный результат не подтверждён или изменился.')
            pilot=json.loads((source.parents[1]/'plan.json').read_text())
            if pilot['batches'][0]!=[r['request_id'] for r in collector.batches[0]]:
                raise ValueError('Молекулы первого пакета не совпадают с пробным запуском.')
            rows,audit=collector.validate(0,source/'result.csv')
            if len(rows)!=20:raise ValueError('В пробном результате должно быть20 молекул.')
            target=collector.folder(0)
            if (target/'result.csv').exists() and sha(target/'result.csv')!=digest:
                raise ValueError('В полном запуске уже есть другой результат первого пакета.')
            for name in ('result.csv','download.json'):
                temporary=target/(name+'.tmp');shutil.copy2(source/name,temporary);temporary.replace(target/name)
            collector.adopt_download(0)
            save(target/'seed-provenance.json',{'source':str(source),'csv_sha256':digest,'rows':20,'new_requests_sent':0})
            seeded=True
            collector.merge()
        print(json.dumps({'seeded_from_pilot':seeded,**collector.status()},ensure_ascii=False,indent=2))
    finally:collector.close()
if __name__=='__main__':prepare()
