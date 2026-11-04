"""Independent arithmetic, coverage, source identity and raw-evidence audit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
DEFAULT = ROOT / 'work/huangpingyang04-lgtm/181/evidence/release'


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(directory, *, mutation=None):
    index = json.loads((directory / 'reception-index.json').read_text())
    result = json.loads((directory / 'result/results.json').read_text())
    profiles = json.loads((directory / 'result/profiles.json').read_text())
    binding = json.loads((directory / 'source/source_binding.json').read_text())
    receipt = json.loads((directory / 'submission.json').read_text())
    for path, row in index['files'].items():
        p = directory / path
        require(p.is_file() and p.stat().st_size == row['bytes'] and digest(p) == row['sha256'],
                f'Raw evidence SHA/size mismatch: {path}')
    require(binding == result['source'] == receipt['source'], 'Source binding differs across evidence')
    for path, expected in binding['files'].items():
        blob = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{binding["git_commit"]}:{path}'])
        require(hashlib.sha256(blob).hexdigest() == expected, f'Source not bound to commit: {path}')
        if path.startswith('project/rtl/block_'):
            baseline = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{binding["base_commit"]}:{path}'])
            require(blob == baseline, f'Frozen base RTL modified: {path}')
    require(result['pass_all'] and result['source_unchanged'], 'Incomplete/changed-source execution')
    require(result['job_id'] == receipt['job_id'] == index['job_id'], 'Job identity mismatch')
    scheduler = (directory / 'scheduler.txt').read_text()
    require(f'{result["job_id"]}|COMPLETED|0:0|' in scheduler and 'TimeLimit=UNLIMITED' in scheduler,
            'Slurm did not complete successfully with UNLIMITED time')
    require(result['executable_sha256'] == index['remote_large_files']['result/obj/Vhbm_s_pool']['sha256'],
            'Executed binary source index mismatch')
    require(len(result['runs']) == len(profiles) == 35, 'Positive profile omission')
    require({p['name'] for p in profiles} == {p['name'] for p in result['runs']}, 'Profile names differ')
    if mutation == 'throughput':
        result['runs'][0]['load']['gbps'] *= 2
    elif mutation == 'credit':
        result['runs'][0]['load']['per_s_max_credit'][0] = 999
    elif mutation == 'coverage':
        result['runs'][0]['matrix_results'] -= 1
    checks = 0
    matrices = 0
    for row, profile in zip(result['runs'], profiles):
        log = directory / 'result' / row['log']
        raw = json.loads(log.read_text().splitlines()[-1])
        # Verify all recorded raw fields, but keep metric re-derivation separate.
        require(row['pass'] and digest(log) == row['log_sha256'], 'Run/log identity mismatch')
        require(row['name'] == profile['name'], 'Profile order mismatch')
        n = row['active_s']
        require(row['matrices'] == n and row['matrix_results'] == n * 64, 'Missing numeric coverage')
        for phase in ('load', 'writeback', 'store'):
            data = row[phase]
            words = 32 if phase == 'writeback' else row['bulk'] + 48 + (32 if phase == 'store' else 0)
            expected_bytes = n * words * 16
            require(data['bytes'] == expected_bytes and data['issued'] == data['retired'] == n * words,
                    f'Lost/duplicated transfer: {row["name"]}/{phase}')
            require(data['per_s_bytes'] == [words * 16] * n, 'Destination byte accounting mismatch')
            require(len(data['per_s_max_credit']) == n and
                    all(0 < v <= row['credits'] for v in data['per_s_max_credit']), 'Credit exceeded')
            require(data['max_queue'] <= row['queue'], 'Channel queue exceeded')
            require(max(data['per_s_max_arbitration_gap']) <= n - 1, 'Round-robin opportunity bound exceeded')
            exact = expected_bytes * 3 / data['ticks']
            require(abs(data['gbps'] - exact) <= 0.00006 * max(1, exact), 'Throughput arithmetic mismatch')
            if phase != 'writeback':
                # One 128bit word/core-cycle/group and finite user-side HBM bus.
                group_bound = row['groups'] * 4.8
                bus_bound = row['channels'] * row['channel_width'] / 8 * 3 / row['mem_period_ticks']
                require(data['gbps'] <= min(group_bound, bus_bound) * 1.02, 'Exceeds link/bus capacity')
                if not row['coordinated_reset']:
                    require(sum(data['channel_beats']) == n * words, 'Channel beat accounting mismatch')
            require(raw[phase]['ticks'] == data['ticks'], 'Raw timing differs')
        if row['stall_core_cycles']:
            require(row['load']['other_completions_during_s0_hold'] > 0, 'No isolated-destination progress')
        checks += row['checks']
        matrices += row['matrices']
    require(checks == result['checks'] and matrices == result['matrices'] == 230, 'Suite totals differ')
    require({(p['init'], p['seed']) for p in result['runs'] if p['name'].startswith('init-')} ==
            {(m, s) for m in (0, 1, 2) for s in (181, 9001)}, 'Initial-state/seed coverage missing')
    require(len(result['negatives']) == 5, 'Negative coverage missing')
    for row in result['negatives']:
        log = directory / 'result' / row['log']
        require(row['exit_code'] != 0 and row['expected'] in log.read_text() and digest(log) == row['log_sha256'],
                'Negative control incorrectly accepted')
    return dict(pass_all=True, job_id=result['job_id'], positive_runs=35, negative_runs=5,
                matrices=matrices, matrix_results=matrices * 64, runtime_checks=checks,
                raw_files=len(index['files']), source_commit=binding['git_commit'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, default=DEFAULT)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    report = audit(args.evidence)
    rejected = []
    for mutation in ('throughput', 'credit', 'coverage'):
        try:
            audit(args.evidence, mutation=mutation)
        except AssertionError:
            rejected.append(mutation)
        else:
            raise AssertionError(f'Independent checker accepted mutated {mutation}')
    report['checker_negative_controls'] = rejected
    if args.out:
        args.out.write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
