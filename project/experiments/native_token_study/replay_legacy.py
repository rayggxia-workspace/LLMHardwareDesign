"""Re-run the frozen conditional SystemC model; never label it native RTL."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'sram_port_compare'))
from generate_policy import generate, verify_sources
import compare_audit


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(command, log, cwd):
    run = subprocess.run([str(x) for x in command], cwd=cwd,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write_bytes(run.stdout)
    if run.returncode:
        raise RuntimeError(str(command) + '\n' + run.stdout.decode(errors='replace')[-2500:])
    return run.stdout.decode()


def replay(inputs, out, prior_path):
    workers = min(4, int(os.environ.get('SLURM_CPUS_PER_TASK', '0')))
    if workers < 1:
        raise ValueError('SystemC replay requires a Slurm allocation')
    lock = verify_sources()
    for name, expected in lock['input_sha256'].items():
        if sha(inputs / name) != expected:
            raise ValueError('input drift: ' + name)
    prior = json.loads(prior_path.read_text())
    if not prior['passed'] or sha(prior_path) != '4dcb0f01357e2f71fcf9f90deeab1d1dd50101b3d928b3e9866473c91c133777':
        raise ValueError('prior successful replay SHA drift')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'm-profile.log').write_bytes((inputs / 'm-profile.log').read_bytes())
    generate(out)
    prefix = Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    execute(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', out / 'model.cpp',
             '-I' + str(out), '-I' + str(prefix / 'include'), '-L' + str(prefix / 'lib'),
             '-Wl,-rpath,' + str(prefix / 'lib'), '-lsystemc', '-o', out / 'model'],
            out / 'build.log', out)
    wanted = [c for c in prior['cases'] if c['route'] == 'B16ctx8'
              and c['policy_KiB'] == 0 and c['P_port_quarters'] == 4]
    if len(wanted) != 4:
        raise ValueError('expected four unique frozen reference workloads')

    def case(old):
        name = old['workload'] + '-' + old['profile']
        trace = inputs / (old['workload'] + '.trace')
        command = [out / 'model', trace, old['profile'], old['variant'], 8, 1, 1, 16, 1, 4]
        text = execute(command, out / (name + '.log'), out)
        rows = [json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
        if len(rows) != 1 or 'MODEL_FAILURE' in text or 'SystemC 3.0.2' not in text:
            raise ValueError('invalid SystemC receipt: ' + name)
        row = rows[0]
        if row != old['result']:
            raise ValueError('whole-result replay drift: ' + name)
        audit = compare_audit.check(row, trace, 16384, True, 4, 8, 1, True)
        record = dict(workload=old['workload'], profile=old['profile'], result=row,
                      whole_result_exact=True, audit=audit, command=[str(x) for x in command],
                      log_sha256=sha(out / (name + '.log')))
        (out / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        print('LEGACY_REPLAY ' + name + ' token/s=' + str(row['tokens_per_second']), flush=True)
        return record

    with ThreadPoolExecutor(max_workers=workers) as pool:
        cases = list(pool.map(case, wanted))
    report = dict(passed=True, scope='historical conditional S32/S96 and ideal 1R1W; not native RTL',
                  reference_sha256=sha(prior_path), cases=cases,
                  generated_sha256={p.name: sha(p) for p in out.iterdir() if p.suffix in ('.cpp', '.inc', '.hpp')})
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
