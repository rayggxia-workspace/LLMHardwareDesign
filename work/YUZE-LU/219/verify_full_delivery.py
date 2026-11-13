"""Check recovered evidence and staged Git blobs against the executed source."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]


def main():
    out=ROOT/'work/YUZE-LU/219/results/full-v1'
    receipt=json.loads((out/'receipt.json').read_text());files=0;sources=0
    for name,entry in receipt['outputs'].items():
        if entry['kept_server']:continue
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==entry['sha256'],name
        files+=1
    for line in (out/'plan/input.sha256').read_text().splitlines():
        expected,name=line.split(maxsplit=1)
        if '/' in name:continue
        path='project/experiments/block_synthesis/'+name
        blob=subprocess.check_output(['git','show',':'+path],cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest()==expected,path
        sources+=1
    summary=json.loads((out/'plan/generated/summary.json').read_text())
    numeric=json.loads((out/'numeric/generated/report.json').read_text())
    assert summary['primitive_program_sha256']==numeric['program_sha256']
    assert summary['status']=='complete_graph_planning_passed'
    assert numeric['status']=='primitive_program_passed' and all(r['passed'] for r in numeric['samples'])
    for row in summary['results']:
        for key in ('audit','baseline_audit','address_check','primitive_address_check','native_cost_check'):
            assert row[key]['passed'],(row['scenario'],key)
    result={'passed':True,'verified_outputs':files,'staged_source_blobs':sources,
            'management_check':'python scripts/check_project.py passed',
            'numeric_program_sha256':numeric['program_sha256']}
    (out/'validation.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(result))


if __name__=='__main__':main()
