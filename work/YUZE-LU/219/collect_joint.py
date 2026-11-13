"""Collect immutable Issue219 attempt evidence; no hardware/model recomputation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search')
JOBS = [99775, 99777, 99781, 99782, 99784, 99785, 99800, 99801, 99809, 99810,
        99817, 99824, 99825, 99826, 99827, 99828, 99834, 99835, 99836]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    if ROOT.resolve() not in a.output.resolve().parents:
        raise ValueError('collection must remain inside the task directory')
    raw = subprocess.check_output(['sacct', '-j', ','.join(map(str, JOBS)), '-n', '-P',
        '--format=JobID,JobName,State,ExitCode,Elapsed,Timelimit,AllocCPUS,NodeList'], text=True)
    (a.output / 'slurm.psv').write_text(raw)
    jobs = [dict(zip(['id', 'name', 'state', 'exit', 'elapsed', 'limit', 'cpus', 'nodes'], r.split('|')[:8]))
            for r in raw.splitlines() if r and '.' not in r.split('|')[0]]
    test_log = ROOT / 'test-joint-final25/tests.log'
    native_log = ROOT / 'native-plan-final25/replay.log'
    model = json.loads((ROOT / 'full-qwen25-3b-v1/complete/receipt.json').read_text())
    coverage = json.loads((ROOT / 'full-audit-final25/coverage/coverage.json').read_text())
    paths = [ROOT / rel for rel in [
        'test-joint-final25/tests.log', 'test-joint-final25/input.sha256',
        'native-plan-final25/generated/plan.json', 'native-plan-final25/generated/graph.json',
        'native-plan-final25/generated/hardware.json', 'native-plan-final25/generated/audit.json',
        'native-plan-final25/generated/native-descriptors.json', 'native-plan-final25/generated/tb_pu_u_group.sv',
        'native-plan-final25/replay.log', 'native-plan-final25/source.sha256',
        'qualify-u-v1/native.log', 'qualify-u-v1/source-archive.sha256', 'qualify-u-v1/instrumented/instrumentation.json',
        'full-qwen25-3b-v1/complete/receipt.json', 'full-qwen25-3b-v1/input.sha256', 'full-qwen25-3b-v1/output.sha256',
        'full-audit-final25/coverage/imported.json', 'full-audit-final25/coverage/coverage.json', 'full-audit-final25/results.sha256',
        'cp-environment-v1/pip.log', 'cp-environment-v2/environment.log']]
    receipt = {'server_root': str(ROOT), 'jobs': jobs,
        'tests': {'count': int(re.search(r'Ran (\d+) tests', test_log.read_text()).group(1)),
                  'passed': test_log.read_text().rstrip().endswith('OK')},
        'native': {'pass_count': native_log.read_text().count('GENERATED_PLAN_PASS tasks=4 cycles=80 S_words=1024'),
                   'scope': 'U/E/16KiB-S client program, no LC fetch/DMA/top-level physical acceptance'},
        'full_model': {k: model[k] for k in ['parameter_count', 'raw_nodes', 'nodes', 'scope', 'onnx_sha256', 'validation_maxabs']},
        'compiler_coverage': coverage,
        'outputs': [{'path': str(v), 'sha256': digest(v), 'bytes': v.stat().st_size} for v in paths],
        'earlier_attempts': [
            {'attempt': 'cp-environment-v1', 'job': 99775, 'reason': 'compute-node pip DNS unavailable; replaced by offline wheels'},
            {'attempt': 'test-joint-v1', 'job': 99781, 'reason': 'spill fixture allowed an early remote copy; corrected fixture to require reuse of local S after scratch'},
            {'attempt': 'full-qwen25-3b-v1 initial submission', 'job': None,
             'reason': '64G memory request rejected by cluster memory metadata (node memory advertised as 1); submission rerun without that unusable limit'},
            {'attempt': 'test-joint-v4', 'job': 99809,
             'reason': '16-tile CP case UNKNOWN within 8 seconds; added independently checked streaming incumbent and pruned fixed alternatives'}],
        'not_achieved': ['full-model numerical lowering/mapping', 'all-five native ABI lowering',
                         'generated MC/LC images', 'native DMA replay of generated plan', 'physical routing feedback/signoff']}
    assert receipt['tests']['passed'] and receipt['tests']['count'] == 25
    assert receipt['native']['pass_count'] == 3
    assert model['parameter_count'] >= 3_000_000_000
    for number in (99777, 99782, 99785, 99836, 99834, 99835):
        j = next(j for j in jobs if j['id'] == str(number))
        assert j['state'] == 'COMPLETED' and j['exit'] == '0:0', j
        assert j['limit'] == 'UNLIMITED', j
    (a.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'tests': receipt['tests'], 'native_passes': receipt['native']['pass_count'], 'jobs': len(jobs)}))


if __name__ == '__main__':
    main()
