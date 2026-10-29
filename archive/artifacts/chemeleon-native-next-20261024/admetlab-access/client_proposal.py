"""Minimal transport proposal; no network happens on import.

Route/payload comes from maintained ToxMCP secondary source, not a successful
live official-schema probe. Root must verify schema/service before bulk use.
Preserve full JSON response; it may contain task id rather than final rows.
"""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = 'https://admetlab3.scbdd.com'

def post_json(path, payload, timeout=30):
    request=Request(BASE+path, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'}, method='POST')
    with urlopen(request, timeout=timeout) as response:
        raw=response.read()
        if response.status != 200:
            raise RuntimeError(f'HTTP {response.status}')
    return json.loads(raw)

def predict_one(smiles, feature=True):
    if not isinstance(smiles,str) or not smiles.strip():
        raise ValueError('One nonempty string SMILES is required')
    return post_json('/api/single/admet', {'SMILES':smiles, 'feature':bool(feature)})

def fetch_csv(task_id, timeout=30):
    request=Request(BASE+'/api/admetCSV', data=json.dumps({'taskId':task_id}).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urlopen(request,timeout=timeout) as response:
        return dict(response.headers),response.read()
