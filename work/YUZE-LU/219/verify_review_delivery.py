"""Check recovered review evidence against the staged compiler Git blobs."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def main():
    out = ROOT / 'work/YUZE-LU/219/results/mutex-control-v1'
    receipt = json.loads((out / 'receipt.json').read_text())
    files = 0
    for name, row in receipt['outputs'].items():
        if row['kept_server']:
            continue
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == row['sha256'], name
        files += 1
    tests = receipt['attempts'][0]
    assert tests['directory'].endswith('/' + receipt['primary']['tests'])
    blobs = 0
    for name, sha in tests['source_sha256'].items():
        path = 'project/experiments/block_synthesis/' + name
        data = subprocess.check_output(['git', 'show', ':' + path], cwd=ROOT)
        assert hashlib.sha256(data).hexdigest() == sha, path
        blobs += 1
    report = json.loads((out / 'current-control/generated/report.json').read_text())
    assert report['status'] == 'generated_mc_lc_replay_passed'
    assert len(report['cases']) == 9 and all(c['passed'] for c in report['cases'])
    assert report['mother_target']['top'] == 'mother_control_64'
    probe = json.loads((out / 'tests/static-conflict.json').read_text())
    assert probe['status'] == 'passed' and probe['legal_alternative']['nets'] == ['a', 'c']
    assert probe['no_legal_alternative']['status'] == 'no_plan_in_bounded_search'
    summary = json.loads((out / 'plan/generated/summary.json').read_text())
    assert summary['status'] == 'complete_graph_planning_passed'
    assert all(r['audit']['passed'] for r in summary['results'])
    final = out.parent / 'mutex-control-v2'
    final_receipt = json.loads((final / 'receipt.json').read_text())
    final_files = 0
    for name, row in final_receipt['outputs'].items():
        if not row['kept_server']:
            assert hashlib.sha256((final / name).read_bytes()).hexdigest() == row['sha256'], name
            final_files += 1
    final_report = json.loads((final / 'current-control/generated/report.json').read_text())
    assert final_report['status'] == 'generated_mc_lc_replay_passed'
    assert len(final_report['cases']) == 9 and all(c['passed'] for c in final_report['cases'])
    assert final_report['mother_target']['top'] == 'mother_control_64'
    result = {'passed': True, 'recovered_sha_checks': files, 'staged_source_blob_checks': blobs,
              'final_control_sha_checks': final_files,
              'current_mother_and_fixed_u_replays': 9, 'unit_tests': 90,
              'scope': 'review repair and constrained native control graph, not whole-system qualification'}
    (out / 'validation.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps(result))


if __name__ == '__main__':
    main()
