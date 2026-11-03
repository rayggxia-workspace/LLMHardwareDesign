"""Verify received raw artifacts, tested Git inputs and retained baseline bytes."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sha = lambda b: hashlib.sha256(b).hexdigest()
index = json.loads((HERE / 'evidence/remote-index.json').read_text())
count = 0
for task in index:
    for entry in task['files']:
        if not entry['download']:
            continue
        p = HERE / 'evidence' / ('job-' + task['job_id']) / entry['path']
        data = p.read_bytes()
        assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], str(p)
        count += 1
final = json.loads((HERE / 'evidence/job-96410/result-r01/results.json').read_text())
assert final['pass_all'] and final['source_unchanged']
assert final['structural_inventory'] == dict(private_stores=9, arbiters=9, feeders=3, banks=36, payload_bits=1179648)
assert len(final['runs']) == 9
assert {(r['init'], r['seed']) for r in final['runs']} == {(m, s) for m in (0, 1, 2) for s in (177, 1001, 9001)}
assert all(r['pass'] and r['requests'] - r['responses'] == 2 for r in final['runs'])
assert sum(r['checks'] for r in final['runs']) == final['checks'] == 12676350
source = final['source']
for name, expected in source['files'].items():
    tested = subprocess.check_output(['git', 'show', source['commit'] + ':' + name], cwd=ROOT)
    current = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
    assert sha(tested) == expected and current == tested, name
    if name.startswith('project/rtl/block_feed_v1/'):
        baseline = subprocess.check_output(['git', 'show', source['baseline'] + ':' + name], cwd=ROOT)
        assert tested == baseline, name
print(f'PASS: {count} raw remote files; 8 tested/current Git inputs; unchanged legacy storage/loader; '
      '9/9 runs; 12,676,350 checks. No physical qualification implied.')
