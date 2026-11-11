"""Verify immutable curated receipts, terminal state and current functional inputs."""
import base64
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
sha=lambda b:hashlib.sha256(b).hexdigest()
index=json.loads((HERE/'index.json').read_text())
raw={}
for item in index['artifacts']:
    path=HERE/item['path'];encoded=path.read_bytes()
    assert sha(encoded)==item['stored_sha256'] and len(encoded)==item['stored_bytes'],path
    data=gzip.decompress(base64.b64decode(encoded,validate=False)) if item['encoding']=='gzip+base64' else encoded
    assert sha(data)==item['raw_sha256'] and len(data)==item['raw_bytes'],path
    raw[(item['run'],item['source_path'])]=data
native_passed=[run for run,entry in index['runs'].items() if entry['whole_run_passed'] and json.loads(raw[(run,'inputs.json')]).get('phase')=='native']
latest_native=max(native_passed,key=lambda n:int(n[3:])) if native_passed else None
checked=0;functional=0
for run,entry in index['runs'].items():
    manifest=json.loads(raw[(run,'inputs.json')]);result=json.loads(raw[(run,'results/result.json')])
    assert manifest['source_commit']==entry['source_commit']==result['source_commit']
    assert result['passed']==entry['whole_run_passed']
    if entry['whole_run_passed']:assert entry['job']['state']=='COMPLETED' and entry['job']['exit_code']=='0:0'
    listing=raw[(run,'output-files.sha256')].decode().splitlines()
    for line in listing:
        digest,path=line.split('  ',1)
        if (run,path) in raw:
            assert sha(raw[(run,path)])==digest,(run,path);checked+=1
    for path,digest in manifest['code_sha256'].items():
        # Shared docs/runner evolution is versioned by run. Actual RTL and
        # old frozen models must remain bit-identical to their passed runs.
        if path.startswith('project/rtl/') or any('/'+folder+'/' in path for folder in ('p_dma_study','sram_capacity_study','area_speed_study','sram_port_compare')) or (
            run==latest_native and '/native_token_study/' in path and Path(path).suffix!='.md'):
            assert sha((REPO/path).read_bytes())==digest,(run,path);functional+=1
if latest_native:
    report=json.loads(raw[(latest_native,'results/result.json')])
    summary=json.loads((HERE/'summary.json').read_text())
    analysis=json.loads((HERE/'analysis.json').read_text())
    assert sha(raw[(latest_native,'results/result.json')])==summary['result_sha256']==analysis['result_sha256']
    assert sha((HERE/'analysis.json').read_bytes())==summary['analysis_sha256']
    assert report['passed'] and len(report['cases'])==9 and len(report['pairs'])==4
    assert report['native_full_model_tokens_per_second'] is None
    assert report['pairs']==summary['pairs'] and len(report['audit_negative_rejections'])==6
    assert all(not entry['native_admitted'] for entry in report['admission'])
    assert sha((REPO/'docs/experiments/pdf/issue-247-p-native-optimizations.pdf').read_bytes())==summary['PDF_sha256']
print(json.dumps(dict(passed=True,runs=list(index['runs']),artifacts=len(index['artifacts']),
                     selected_output_SHA_checks=checked,current_frozen_functional_SHA_checks=functional)))
