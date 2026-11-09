"""Verify source-bound run04 evidence; this does not rerun the simulation."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
index = json.loads((HERE / 'index.json').read_text())
for name, value in index['files_sha256'].items(): assert sha(HERE / name) == value, name
assert index['state'] == 'COMPLETED' and index['exit_code'] == '0:0'
metadata = json.loads((HERE / 'inputs.json').read_text())
assert metadata['source_commit'] == index['source_commit']
for filename, key in [('source-files.sha256', 'code_sha256'), ('input-files.sha256', 'input_sha256')]:
    actual = {name: value for value, name in (line.split('  ', 1) for line in (HERE / filename).read_text().splitlines())}
    assert actual == metadata[key], filename
functional = 0
for name, value in metadata['code_sha256'].items():
    if Path(name).suffix in ('.py','.cpp','.hpp','.inc','.json','.sh','.sv','.svh'):
        assert sha(REPO / name) == value, name
        functional += 1
summary = json.loads((HERE / 'summary.json').read_text())
assert summary['passed'] and summary['regression_phase_passed']
assert summary['source_commit'] == index['source_commit']
assert summary['generator_lock_negative'] and summary['prerequisite_lock_negative']
assert summary['source_lock_negative']['passed']
assert len(summary['cases']) == index['full_trace_executions'] + index['small_trace_executions']
assert all(c['audit_passed'] and c['U_reference']['passed'] for c in summary['cases'])
assert all(c['all_real_metrics_exact'] for c in summary['resident_context_overlap'])
assert len(summary['port_cost_grid']) == 12
assert len(summary['invalid_CLI_rejected']) == index['invalid_CLI_count']
def key(c):
    return tuple(c[n] for n in ('workload','profile','variant','contexts','switch_cycles','reuse_A','P_KiB','dual_ports','P_port_quarters'))
rows = {key(c): c for c in summary['cases']}
selected = 0
for path in (HERE / 'results').glob('*.json'):
    raw = json.loads(path.read_text())
    if 'result' not in raw: continue
    s = rows[key(raw)]; r = raw['result']
    assert s['tokens_s'] == r['tokens_per_second'] and s['seconds'] == r['seconds']
    assert s['bus_bytes'] == r['read_bus_bytes'] + r['write_bus_bytes']
    assert s['M_commands'] == r['M_commands'] and s['context_study'] == r['context_study']
    selected += 1
print(json.dumps(dict(passed=True, curated_files=len(index['files_sha256']), functional_source_SHA= functional,
    full_trace_executions=index['full_trace_executions'], small_trace_executions=index['small_trace_executions'],
    invalid_CLI=index['invalid_CLI_count'], selected_raw_cases=selected,
    recovered_output_SHA=index['recovered_output_SHA_checked'], scope='source and receipt consistency; no new simulation or physical qualification')))
