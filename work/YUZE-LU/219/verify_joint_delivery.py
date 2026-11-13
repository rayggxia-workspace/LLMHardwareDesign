"""Bind collected receipts, exact executed sources and native replay inputs."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
out = Path(__file__).with_name('results') / 'joint-v1'
receipt = json.loads((out / 'receipt.json').read_text())
aliases = {'plan.json': 'native-plan.json', 'graph.json': 'native-graph.json', 'hardware.json': 'native-hardware.json',
           'audit.json': 'native-audit.json', 'tb_pu_u_group.sv': 'native-testbench.sv',
           'replay.log': 'native-replay.log'}
matched = []
for r in receipt['outputs']:
    remote = r['path']
    name = Path(remote).name
    if '/native-plan-final25/' in remote:
        name = aliases.get(name, name)
    elif '/complete/receipt.json' in remote:
        name = 'full-model.json'
    elif '/test-joint-final25/input.sha256' in remote:
        name = 'test-source.sha256'
    elif '/source.sha256' in remote:
        name = 'native-source.sha256'
    elif '/full-qwen25-3b-v1/input.sha256' in remote:
        name = 'full-model-input.sha256'
    elif '/full-qwen25-3b-v1/output.sha256' in remote:
        name = 'full-model-output.sha256'
    elif '/qualify-u-v1/' in remote or '/cp-environment-' in remote or name == 'results.sha256':
        continue
    target = out / name
    if not target.exists():
        continue
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    assert actual == r['sha256'], (remote, target, actual, r['sha256'])
    matched.append(name)
source_checks = []
for manifest in ('test-source.sha256', 'native-source.sha256'):
    for line in (out / manifest).read_text().splitlines():
        sha, name = line.split(maxsplit=1)
        source = ROOT / 'project/experiments/block_synthesis' / name
        assert hashlib.sha256(source.read_bytes()).hexdigest() == sha, (manifest, name)
        source_checks.append({'manifest': manifest, 'file': name, 'sha256': sha})
sys.path.insert(0, str(ROOT / 'project/experiments/block_synthesis'))
from verify import verify
native = {kind: json.loads((out / f'native-{kind}.json').read_text()) for kind in ('plan', 'graph', 'hardware')}
audit = verify(native['graph'], native['hardware'], native['plan'])
data = {'passed': True, 'matched_artifacts': matched, 'exact_executed_sources': source_checks,
        'native_plan_independent_replay': audit, 'test_count': receipt['tests']['count']}
(out / 'verification.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'matched_artifacts': len(matched), 'executed_source_matches': len(source_checks), 'native_plan': audit['passed']}))
