"""Slurm-only fixed-S context sweep; all controls use the frozen Issue245 graph."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from generate import generate, HERE, BASE
import study_audit


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(cmd, log, cwd, env=None):
    process = subprocess.run(list(map(str, cmd)), cwd=cwd, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    if process.returncode:
        raise RuntimeError(str(cmd)+' '+process.stdout.decode(errors='replace')[-3000:])
    return process.stdout.decode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out, inputs = args.out.resolve(), args.inputs.resolve()
    out.mkdir(parents=True, exist_ok=False)
    lock = json.loads((HERE/'source.json').read_text())
    for name, value in lock['input_sha256'].items():
        assert digest(inputs/name) == value, name
    (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
    (out/'generated').mkdir()
    generate(out)
    prefix = Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror']
    execute(['g++', *flags, out/'model.cpp', '-I'+str(out), '-I'+str(prefix/'include'),
             '-L'+str(prefix/'lib'), '-Wl,-rpath,'+str(prefix/'lib'), '-lsystemc', '-o', out/'model'],
            out/'build.log', out)
    execute(['g++', *flags, BASE/'upstream/kernel_probe.cpp', '-o', out/'kernel_probe'],
            out/'kernel-build.log', out)
    env = dict(os.environ, BLOCK_STUDY_MODEL=str(out/'model'))
    for script in ['check_kernels.py', 'validate.py', 'smoke.py']:
        execute([sys.executable, '-B', BASE/'upstream'/script], out/(script+'.log'), out, env)
    execute([sys.executable, '-B', BASE/'oracle.py'], out/'legacy-oracle.log', out)
    oracle = execute([sys.executable, '-B', HERE/'context_oracle.py', '--output', out/'context-oracle.json'],
                     out/'context-oracle.log', out)
    prior = json.loads((inputs/'prior-results.json').read_text())

    def case(item):
        workload, profile, variant, contexts, switch, reuse = item
        name = f'{workload}-{profile}-{variant}-c{contexts}-s{switch}-a{reuse}'
        text = execute([out/'model', inputs/(workload+'.trace'), profile, variant, contexts, switch, reuse],
                       out/(name+'.log'), out)
        assert 'MODEL_FAILURE' not in text and 'SystemC 3.0.2' in text
        results = [json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
        assert len(results) == 1
        result = results[0]
        baseline = next(c['result'] for c in prior['cases'] if c['binary']=='model' and
                        c['workload']==workload and c['profile']==profile and c['variant']==variant)
        audit = study_audit.check(result, inputs/(workload+'.trace'), baseline, contexts, switch, reuse)
        rejected = study_audit.reject_checks(result, inputs/(workload+'.trace'), baseline, contexts, switch, reuse)
        record = dict(workload=workload, profile=profile, variant=variant, contexts=contexts,
                      switch_cycles=switch, reuse_A=bool(reuse), result=result, audit=audit,
                      baseline_seconds=baseline['seconds'], negative_checks=rejected,
                      log_sha256=digest(out/(name+'.log')))
        (out/(name+'.json')).write_bytes((json.dumps(record, indent=2)+'\n').encode())
        print(json.dumps(dict(case=name, tokens_s=result['tokens_per_second'],
                              speedup=baseline['seconds']/result['seconds'],
                              bus_bytes=result['read_bus_bytes']+result['write_bus_bytes'])), flush=True)
        return record

    best = 'adaptive_prefix_pair_combine'
    cases = [('decode512', 'queued_pipe_w8', v, c, 1, 1)
             for v in ('observe', best) for c in (1, 2, 4, 8, 16)]
    cases += [('decode512', 'queued_pipe_w16', v, c, 1, 1)
              for v in ('observe', 'adaptive') for c in (1, 2, 4, 8)]
    cases += [('decode512', 'queued_pipe_w8', best, 8, s, 1) for s in (0, 3, 8)]
    cases += [('decode512', 'queued_pipe_w8', v, 8, 1, 0) for v in ('observe', best)]
    cases += [(w, 'queued_pipe_w8', v, c, 1, 1)
              for w in ('decode128', 'decode2048', 'prefill2') for v in ('observe', best) for c in (1, 8)]
    workers = min(4, int(os.environ['SLURM_CPUS_PER_TASK']))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(case, cases))
    report = dict(passed=True, issue=247,
                  source_commit=json.loads((out.parent/'inputs.json').read_text())['source_commit'],
                  scope='conditional architecture model; no tensor/RTL/physical/DDR qualification',
                  fixed_S_bytes=16384, fixed_P_count=2, fixed_bandwidth_B_s=17100000000,
                  cases=records, complete_legacy_baseline_exact=True,
                  context_oracle_log_sha256=digest(out/'context-oracle.log'),
                  versions=dict(python=platform.python_version(), SystemC='3.0.2',
                                gcc=subprocess.check_output(['g++', '--version'], text=True).splitlines()[0]),
                  input_sha256=lock['input_sha256'],
                  generated_sha256={p.name:digest(p) for p in out.iterdir() if p.suffix in ('.cpp', '.hpp', '.inc')},
                  source_sha256={p.name:digest(p) for p in HERE.iterdir() if p.suffix in ('.py', '.json', '.sh', '.hpp', '.inc')})
    assert oracle.strip(), 'missing oracle receipt'
    (out/'result.json').write_bytes((json.dumps(report, indent=2)+'\n').encode())
    print('AREA_CONTEXT_PASS '+str(len(records)), flush=True)


if __name__ == '__main__':
    main()
