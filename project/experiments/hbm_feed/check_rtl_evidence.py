"""Independent audit of the real RTL suite and archived original logs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
DEFAULT = ROOT / 'work/huangpingyang04-lgtm/181/evidence/rtl-release'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, msg):
    if not ok:
        raise AssertionError(msg)


def audit(path=DEFAULT, mutation=None):
    reception = json.loads((path / 'LOCAL_RECEPTION.json').read_text())
    archive = path / 'reception.tar.gz'
    require(sha(archive.read_bytes()) == reception['archive_sha256'], 'Original archive SHA mismatch')
    with tarfile.open(archive) as tar:
        index_bytes = tar.extractfile('reception-index.json').read()
        require(sha(index_bytes) == reception['index_sha256'], 'Original index SHA mismatch')
        index = json.loads(index_bytes)
        raw = {}
        for name, identity in index['files'].items():
            data = tar.extractfile(name).read()
            require(len(data) == identity['bytes'] and sha(data) == identity['sha256'], f'Archived original differs: {name}')
            local = path / name
            if local.exists():
                require(local.read_bytes() == data, f'Local evidence differs from server archive: {name}')
            raw[name] = data
    result = json.loads(raw['result/results.json'])
    source = json.loads(raw['source/source_binding.json'])
    profiles = json.loads(raw['result/profiles.json'])
    require(result['pass_all'] and result['source_unchanged'] and source == result['source'], 'Incomplete or unbound run')
    require(source['suite'] == 'rtl' and result['suite'] == 'grouped-dma-rtl', 'Architecture fixture mistaken for RTL suite')
    require('project/rtl/hbm_feed/hbm_group_dma.sv' in source['files'], 'Actual grouped RTL missing')
    for name, identity in source['files'].items():
        blob = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{source["git_commit"]}:{name}'])
        require(sha(blob) == identity, f'Source commit differs: {name}')
        if name.startswith('project/rtl/block_'):
            original = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{source["base_commit"]}:{name}'])
            require(blob == original, f'Original S/feeder/M changed: {name}')
    require(result['executable_sha256'] == index['remote_large_files']['result/obj/Vhbm_dma_system']['sha256'], 'Executable identity mismatch')
    scheduler = (path / 'scheduler.txt').read_text()
    require(f'{result["job_id"]}|COMPLETED|0:0|' in scheduler and 'TimeLimit=UNLIMITED' in scheduler, 'Bad Slurm terminal state')
    require(len(result['runs']) == len(profiles) == 38, 'RTL profile coverage missing')
    if mutation == 'credit':
        result['runs'][0]['load']['max_live'] = 99
    elif mutation == 'throughput':
        result['runs'][0]['load']['gbps'] *= 2
    elif mutation == 'matrix':
        result['runs'][0]['matrix_values'] -= 1
    total_checks = total_matrices = total_values = 0
    for row, profile in zip(result['runs'], profiles):
        require(row['name'] == profile['name'], 'Profile mismatch')
        log = raw['result/' + row['log']]
        require(row['log_sha256'] == sha(log), 'Run log identity mismatch')
        observed = json.loads(log.splitlines()[-1])
        require(row['pass'] and row['active_s'] == row['groups'] * row['per_group'], 'Active S coverage mismatch')
        n, words = row['active_s'], row['words']
        require(row['matrices'] == n and row['matrix_values'] == n * 64, 'Matrix coverage missing')
        require(row['invalid_descriptors'] == 6, 'Invalid descriptor coverage missing')
        require(row['failed_completions'] == (1 if row['error'] else 0), 'Response error did not produce hardware completion')
        require(row['protocol_recovered'] == bool(row['fault']), 'Bad/duplicate ID recovery missing')
        require(row['boundary_transfers'] == (2 if row['name'] == 'upper-boundaries' else 0), 'Upper-boundary exercise missing')
        for phase in ('load', 'store'):
            v = row[phase]
            useful = n - (phase == 'store' and row['error'] == 2)
            require(v['bytes'] == useful * words * 16 and v['completions'] == n, 'Missing bytes/completions')
            require(v['max_live'] <= row['credits'] and v['max_queue'] <= row['queue'], 'Finite resource bound exceeded')
            require(v['max_bypass'] < n, 'Eligible source round-robin fairness exceeded')
            exact = v['bytes'] * 3 / v['ticks']
            require(abs(v['gbps'] - exact) < 0.00006 * max(1, exact), 'Throughput arithmetic mismatch')
            require(v['gbps'] <= row['channels'] * 4.8 * 1.02, 'Exceeds actual RTL channel ingress bandwidth')
            if not row['error']:
                require(v['requests'] == n * words and v['s_acks'] == n * words, 'Missing actual memory/S transfers')
            require(v['ticks'] == observed[phase]['ticks'], 'Raw stage timing mismatch')
        if row['name'] == 'held-s0':
            require(row['load']['other_s_acks_during_hold'] == (n - 1) * words, 'Other destinations did not finish during S hold')
        if row['name'] == 'paused-core':
            require(row['load']['response_stalls'] > 0, 'Response CDC backpressure not exercised')
        if row['name'] == 'held-completion':
            require(row['load']['held_completion_cycles'] > 0, 'Completion retention not exercised')
        total_checks += row['checks']
        total_matrices += row['matrices']
        total_values += row['matrix_values']
    require(total_checks == result['checks'] and total_matrices == result['matrices'] == 238 and
            total_values == result['matrix_values'] == 15232, 'Suite totals differ')
    require(len(result['negatives']) == 1 and result['negatives'][0]['exit_code'] != 0, 'Payload negative control missing')
    neg = result['negatives'][0]
    require(sha(raw['result/' + neg['log']]) == neg['log_sha256'] and
            b'S write payload differs from independent external image' in raw['result/' + neg['log']], 'Payload corruption not rejected')
    require('warning:' not in raw['result/build.log'].decode(), 'C++ Werror build emitted warnings')
    require(len(result['synthesis']) == 2, 'Synthesis configurations missing')
    for item in result['synthesis']:
        log = raw['result/' + item['name'] + '.log']
        require(sha(log) == item['log_sha256'] and b'Found and reported 0 problems.' in log, 'Synthesis check-assert evidence missing')
        require(item['netlist_sha256'] == index['remote_large_files']['result/' + item['name'] + '.json']['sha256'], 'Synthesized netlist identity differs')
        require(item['cells'] == sum(item['types'].values()) and not any('LATCH' in k.upper() for k in item['types']), 'Generic cells/latches mismatch')
    return dict(pass_all=True, job_id=result['job_id'], source_commit=source['git_commit'],
                profiles=38, invalid_descriptors=38*6, matrices=238, matrix_values=15232,
                checks=total_checks, synthesized_cells={x['name']: x['cells'] for x in result['synthesis']},
                original_files=len(index['files']), original_bytes=sum(x['bytes'] for x in index['files'].values()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, default=DEFAULT)
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    result = audit(a.evidence)
    negatives = []
    for name in ('credit', 'throughput', 'matrix'):
        try:
            audit(a.evidence, mutation=name)
        except AssertionError:
            negatives.append(name)
        else:
            raise AssertionError(f'Auditor accepted altered {name}')
    result['auditor_negatives'] = negatives
    if a.out:
        a.out.write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
