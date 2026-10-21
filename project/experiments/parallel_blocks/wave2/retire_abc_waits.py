"""Retire only the specifically diagnosed wave2-01 and wave2-04 stalled steps.

No elapsed-time policy, no generalized cancellation, no main-line job access.
"""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

assert sys.argv[1:] == ['--execute'], 'This narrowly scoped operation requires --execute'
base = Path(__file__).resolve().parent.parent / 'results'
destination = base / 'parallel-blocks-wave2-stall-retirement.json'
assert not destination.exists()
probe = json.loads((base / 'parallel-blocks-wave2-05-latest.json').read_text())
assert probe['tasks']['abc-probe-short']['validation']['passed']
assert probe['tasks']['abc-probe-short']['exit_code'].strip() == '0'
host = ['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172']
jobs = {89480: 'parallel-blocks-wave2-01', 89481: 'parallel-blocks-wave2-01', 89491: 'parallel-blocks-wave2-04'}
record = dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    reason='Completed ABC output exists, persistent ABC processes wait at select; minimal long-TMPDIR reproduction and successful tool-default TMPDIR check. Not an elapsed-time deadline.',
    successful_short_probe_job=89493, short_probe_validation=probe['tasks']['abc-probe-short']['validation'],
    abc_wait_snapshot_sha256=hashlib.sha256((base/'parallel-blocks-wave2-abc-wait.json').read_bytes()).hexdigest(),
    targets=['89480.0','89480.1','89480.2','89481.0','89481.1','89481.2','89481.3','89491.1'],
    scheduler_before={}, cancellation_exit_code=None,
    source='https://github.com/YosysHQ/yosys/issues/5495',
    scope='Retain original failed/stalled evidence; do not change frozen runners or any main-line job')
for job, attempt in jobs.items():
    line = subprocess.check_output(host+['scontrol -o show job '+str(job)], text=True)
    assert 'UserId=yuzelu(' in line and 'JobName=lyz-wave2-' in line
    assert '/issue-7/'+attempt+'/runner/wave2/stream.sh' in line
    record['scheduler_before'][str(job)] = line.strip()
destination.write_text(json.dumps(record,indent=2)+'\n')
result = subprocess.run(host+['scancel '+ ' '.join(record['targets'])], text=True, capture_output=True)
record['cancellation_exit_code'] = result.returncode
record['cancellation_stdout'] = result.stdout
record['cancellation_stderr'] = result.stderr
destination.write_text(json.dumps(record,indent=2)+'\n')
result.check_returncode()
print('Retirement recorded:', ', '.join(record['targets']))
