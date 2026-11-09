"""Read-only verification of the completed, curated old-metric replay."""
import base64
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sha = lambda data: hashlib.sha256(data).hexdigest()
index = json.loads((HERE / 'index.json').read_bytes())
raw = {}
for item in index['artifacts']:
    encoded = (HERE / item['path']).read_bytes()
    assert sha(encoded) == item['stored_sha256'] and len(encoded) == item['stored_bytes'], item['path']
    data = gzip.decompress(base64.b64decode(encoded)) if item['encoding'] == 'gzip+base64' else encoded
    assert sha(data) == item['raw_sha256'] and len(data) == item['raw_bytes'], item['path']
    raw[item['run'], item['source_path']] = data
assert len(index['runs']) == 1
run, meta = next(iter(index['runs'].items()))
manifest = json.loads(raw[run, 'inputs.json'])
report = json.loads(raw[run, 'results/result.json'])
assert meta['whole_run_passed'] and meta['job']['state'] == 'COMPLETED' and meta['job']['exit_code'] == '0:0'
assert report['passed'] and report['source_commit'] == manifest['source_commit'] == meta['source_commit']
assert report['manifest_sha256'] == sha(raw[run, 'inputs.json'])
assert report['all21_historical_fields_exact'] and report['run12_generated_exact']
assert report['completed_independent_audit']['passed'] and report['completed_independent_audit']['cases'] == 21
assert len(report['cases']) == 21 and len(report['independent_negative_rejections']) == 7
assert report['source_drift_rejected'] and report['prior_drift_rejected'] and len(report['invalid_CLI_rejected']) == 2
checked = 0
for line in raw[run, 'output-files.sha256'].decode().splitlines():
    digest, path = line.split('  ', 1)
    if (run, path) in raw:
        assert sha(raw[run, path]) == digest, path
        checked += 1
for path, digest in manifest['code_sha256'].items():
    assert sha((REPO / path).read_bytes()) == digest, path
input_raw = {}
for item in index['input_artifacts']:
    encoded = (HERE / item['path']).read_bytes()
    assert sha(encoded) == item['stored_sha256'] and len(encoded) == item['stored_bytes']
    data = gzip.decompress(base64.b64decode(encoded)) if item['encoding'] == 'gzip+base64' else encoded
    assert sha(data) == item['raw_sha256'] == manifest['input_sha256'][item['source_path']]
    assert len(data) == item['raw_bytes'] and item['source_path'] not in input_raw
    input_raw[item['source_path']] = data
assert set(input_raw) == set(manifest['input_sha256'])
prior_reports = {name: json.loads(input_raw[name + '-result.json']) for name in ('run01', 'run04', 'run05', 'run12')}
for name, prior in prior_reports.items():
    assert sha(input_raw[name + '-result.json']) == report['prior_sha256'][name]
    assert prior['source_commit'] == json.loads(input_raw[name + '-inputs.json'])['source_commit']
audit_spec = importlib.util.spec_from_file_location('legacy_independent_audit',
    REPO / 'project/experiments/legacy_metric_eval/verify_completed.py')
audit_module = importlib.util.module_from_spec(audit_spec)
audit_spec.loader.exec_module(audit_module)
assert audit_module.verify_completed(report, prior_reports)['passed']
for case in report['cases']:
    log_name = Path(case['command'][0]).parent / (
        case['workload'] + '-' + case['profile'] + '-' + case['role'] + '-' + str(case['P_KiB']) + '.log')
    # Command paths are POSIX server paths; use only their final component locally.
    name = str(log_name).replace('\\', '/').rsplit('/', 1)[1]
    assert sha(raw[run, 'results/' + name]) == case['log_sha256'], name
    assert case['audit']['passed'] and case['U_reference']['passed']
analysis = json.loads((HERE / 'analysis.json').read_bytes())
spec = importlib.util.spec_from_file_location('legacy_analysis', HERE / 'analyse.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
expected = module.analyze(report, analysis['source'])
expected['analysis_script_sha256'] = sha((HERE / 'analyse.py').read_bytes())
assert analysis == expected
assert analysis['source']['decoded_json_sha256'] == sha(raw[run, 'results/result.json'])
assert analysis['generated_sha256'] == report['generated_sha256']
assert (HERE / 'analysis.md').read_text(encoding='utf-8') == module.markdown(analysis)
summary = json.loads((HERE / 'summary.json').read_bytes())
assert summary['result_sha256'] == sha(raw[run, 'results/result.json'])
assert summary['analysis_sha256'] == sha((HERE / 'analysis.json').read_bytes())
assert summary['source_commit'] == report['source_commit']
print(json.dumps(dict(passed=True, cases=21, artifacts=len(index['artifacts']),
    selected_output_SHA_checks=checked, current_source_SHA_checks=len(manifest['code_sha256']),
    archived_input_SHA_checks=len(input_raw), historical_replay_reaudited_locally=True)))
