"""Verify immutable policy-only source and server receipts; no simulation."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[4]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
index=json.loads((HERE/'index.json').read_text());assert index['state']=='COMPLETED' and index['exit_code']=='0:0'
for n,h in index['files_sha256'].items():assert sha(HERE/n)==h,n
meta=json.loads((HERE/'inputs.json').read_text());assert meta['source_commit']==index['source_commit']
for file,key in [('source-files.sha256','code_sha256'),('input-files.sha256','input_sha256')]:
    assert {n:h for h,n in (line.split('  ',1) for line in (HERE/file).read_text().splitlines())}==meta[key]
functional=0
for n,h in meta['code_sha256'].items():
    if Path(n).suffix in ('.py','.json','.cpp','.hpp','.inc','.sh','.sv','.svh'):
        assert sha(REPO/n)==h,n;functional+=1
s=json.loads((HERE/'summary.json').read_text())
assert s['passed'] and s['default_phase_passed'] and s['default_full_result_replays']==12
assert s['source_commit']==index['source_commit'] and s['source_and_prior_SHA_negative']
assert s['prior_run04']['result_sha256']==json.loads((HERE.parent/'index.json').read_text())['full_result_sha256']
assert len(s['cases'])==index['full_trace_executions'] and len(s['invalid_CLI_rejected'])==index['invalid_CLI_count']
assert all(c['audit_passed'] and c['U_reference']['passed'] and c['policy_audit']['passed'] for c in s['cases'])
assert all(len(c['negative_checks'])==6 for c in s['cases'])
def key(c):return tuple(c[k] for k in ('workload','profile','route','P_port_quarters','policy_KiB'))
rows={key(c):c for c in s['cases']};selected=0
for path in (HERE/'results').glob('*.json'):
    c=json.loads(path.read_text())
    if 'result' not in c:continue
    raw=c['result'];r=rows[key(c)]
    assert r['tokens_s']==raw['tokens_per_second'] and r['bus_bytes']==raw['read_bus_bytes']+raw['write_bus_bytes']
    assert r['policy_study']==raw['policy_study'] and r['P_ports']==raw['hardware_study']['P_ports'];selected+=1
print(json.dumps(dict(passed=True,curated_files=len(index['files_sha256']),functional_source_SHA=functional,
    full_trace_executions=len(rows),default_replays=12,invalid_CLI=index['invalid_CLI_count'],selected_raw_cases=selected,
    recovered_output_SHA=index['recovered_output_SHA_checked'],scope='source/receipt verification; no new simulation')))
