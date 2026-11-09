"""Verify curated immutable receipts and the final tested functional source."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
index=json.loads((HERE/'index.json').read_text(encoding='utf-8'))
for name,value in index['files_sha256'].items():
    assert sha(HERE/name)==value,name
for name,value in index['final_functional_source_sha256'].items():
    assert sha(REPO/'project/experiments/p_dma_study'/name)==value,name
assert sum(r['full_trace_executions'] for r in index['runs'])==62
assert all(r['state']=='COMPLETED' and r['exit_code']=='0:0' for r in index['runs'])
rows=json.loads((HERE/'summary.json').read_text(encoding='utf-8'))
assert len(rows)==56
raw_checked=0
for path in HERE.glob('run*/results/decode*.json'):
    record=json.loads(path.read_text(encoding='utf-8'));x=record['result']
    row=next(r for r in rows if r['run']==path.parts[-3] and r['workload']==record['workload'] and r['profile']==record['profile'] and r['variant']==record['variant'])
    assert row['token_s']==x['tokens_per_second']
    assert row['bus_bytes']==x['read_bus_bytes']+x['write_bus_bytes']
    assert row['M_commands']==x['M_commands'] and record['audit']['passed']
    raw_checked+=1
assert raw_checked==4
negative=json.loads((HERE/'run04/results/rejections.json').read_text(encoding='utf-8'))
assert negative['passed'] and len(negative['rejected'])==7
print(json.dumps(dict(passed=True,curated_SHA_files=len(index['files_sha256']),functional_source_SHA_files=len(index['final_functional_source_sha256']),raw_case_summary_matches=raw_checked,full_trace_executions=62,scope='receipt/source consistency; no new simulation or RTL qualification')))
