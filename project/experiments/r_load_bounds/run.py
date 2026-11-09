"""Run the R LOAD contract against real RTL; negative control uses old main RTL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=('raw256', 'raw1024', 'service256', 'negative'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--old-rtl', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    negative = args.case == 'negative'
    if negative and not args.old_rtl:
        parser.error('--old-rtl is required for the negative control')
    rtl = ROOT / 'project/rtl/r_local_state/r_stream_local.sv'
    if negative:
        rtl = args.old_rtl.resolve()
    top = 'tb_service_bounds' if args.case == 'service256' else 'tb_load_bounds'
    sources = [HERE / (top + '.sv'), rtl, ROOT / 'project/rtl/r_local_state/r_state_store.sv']
    if args.case == 'service256':
        sources.append(ROOT / 'project/rtl/block_cfj_v1/ucf_r256_service.sv')
    verilator = '/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator'
    command = [verilator, '--binary', '--timing', '--assert', '-Wno-fatal',
               '--x-initial', 'unique', '--x-assign', 'unique', '-j',
               os.environ.get('SLURM_CPUS_PER_TASK', '4'), '--top-module', top,
               '--Mdir', str(out / 'obj')]
    if top == 'tb_load_bounds':
        command.append('-GWORDS=' + ('1024' if args.case == 'raw1024' else '256'))
    command += list(map(str, sources))
    report = dict(passed=False, case=args.case, negative_control=negative,
                  source_sha256={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else 'old-main/r_stream_local.sv': digest(p) for p in sources},
                  runner_sha256=digest(Path(__file__)), runs=[],
                  verilator_version=subprocess.check_output([verilator, '--version'], text=True).strip(),
                  compile_command=command, cpu_affinity=sorted(os.sched_getaffinity(0)))
    try:
        with (out / 'compile.log').open('w') as stream:
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
        for mode, seed in [(1, 143), (2, 143), (2, 144)]:
            log = out / f'run-{mode}-{seed}.log'
            with log.open('w') as stream:
                result = subprocess.run([str(out / 'obj' / ('V' + top)),
                    f'+verilator+rand+reset+{mode}', f'+verilator+seed+{seed}'],
                    stdout=stream, stderr=subprocess.STDOUT)
            text = log.read_text()
            if negative:
                assert result.returncode != 0 and 'invalid LOAD accepted WORDS=256 t=0 i=64' in text, text[-2000:]
            else:
                assert result.returncode == 0 and 'PASS ' in text, text[-2000:]
            report['runs'].append(dict(mode=mode, seed=seed, exit_code=result.returncode,
                                       log_sha256=digest(log),
                                       outcome='expected old-source defect' if negative else 'passed'))
        report['passed'] = True
    finally:
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
