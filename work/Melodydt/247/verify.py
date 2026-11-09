"""Verify delivered receipts and latest tested source identities, not rerun RTL."""
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
index=json.loads((HERE/'index.json').read_text())
for name,value in index['files_sha256'].items():assert sha(HERE/name)==value,name
latest={}
for name,run in sorted(index['runs'].items()):
    assert run['state']=='COMPLETED' and run['exit_code']=='0:0'
    metadata=json.loads((HERE/name/'inputs.json').read_text())
    assert metadata['source_commit']==run['source_commit']
    latest.update(metadata['code_sha256'])
    sources={n:h for h,n in (line.split('  ',1) for line in (HERE/name/'source-files.sha256').read_text().splitlines())}
    assert sources==metadata['code_sha256']
    data={n:h for h,n in (line.split('  ',1) for line in (HERE/name/'input-files.sha256').read_text().splitlines())}
    assert data==metadata['input_sha256']
checked=0
for name,value in latest.items():
    if Path(name).suffix in ('.py','.sv','.svh','.cpp','.hpp','.inc','.sh','.json'):
        assert sha(REPO/name)==value,name
        checked+=1
s1=json.loads((HERE/'run01/summary.json').read_text())
s2=json.loads((HERE/'run02/summary.json').read_text())
s3=json.loads((HERE/'run03/summary.json').read_text())
assert len(s1)==35 and len(s3)==21 and s2['passed']
assert s2['edge']['total_model_invocations']==32 and all(s2['edge']['coverage'].values())
assert all(c['baseline_cycles']==c['candidate_cycles']==288 for c in s2['P_cycle_comparisons'])
for run,summary in [('run01',s1),('run03',s3)]:
    for file in (HERE/run/'results').glob('*.json'):
        raw=json.loads(file.read_text())
        if 'result' not in raw or 'workload' not in raw:continue
        found=next(r for r in summary if r['workload']==raw['workload'] and r['profile']==raw['profile'] and
                   r['variant']==raw['variant'] and r['contexts']==raw['contexts'] and
                   r['switch_cycles']==raw['switch_cycles'] and
                   (r.get('reuse_A')==raw.get('reuse_A') if run=='run01' else r['contract']==raw['contract']))
        assert found['tokens_s']==raw['result']['tokens_per_second']
        assert found['bus_bytes']==raw['result']['read_bus_bytes']+raw['result']['write_bus_bytes']
print(json.dumps(dict(passed=True,curated_files=len(index['files_sha256']),latest_functional_SHA_files=checked,
                     full_trace_executions=len(s1)+len(s3),edge_invocations=32,
                     recovered_output_SHA=sum(r['recovered_output_SHA_checked'] for r in index['runs'].values()),
                     scope='receipt and current-source consistency; no new simulation or physical qualification')))
