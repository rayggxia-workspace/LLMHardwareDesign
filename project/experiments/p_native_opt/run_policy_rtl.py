"""Server-only finite arbiter RTL test. No SystemC timing substitution.

run_policy(repo, out, workers=4) is also callable by the integrated runner.
The original SRAM/controller are not replaced or executed by this local bench;
root's integration separately checks actual local_s_p and the P group.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
VERILATOR = Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
SEEDS = (143, 144, 7143)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_policy(repo, out, workers=4, verilator=VERILATOR):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    if not 1 <= workers <= int(os.environ.get('SLURM_CPUS_PER_TASK', '0')):
        raise ValueError('server Slurm CPU allocation required; do not run local EDA')
    out.mkdir(parents=True, exist_ok=False)
    original = repo/'project/rtl/block_local_s/block_local_s_arbiter.sv'
    candidate = repo/'project/rtl/block_local_s/popt_s_policy_arbiter.sv'
    top = HERE/'policy_top.sv'
    driver = HERE/'policy_test.cpp'
    report = {'passed': False, 'scope': 'real isolated arbitration RTL with finite memory responder; no DMA engine, SRAM throughput or token/s claim',
              'versions': {'python': platform.python_version()}, 'commands': [], 'measurements': [],
              'input_sha256': {str(p): sha(p) for p in (original, candidate, top, driver)},
              'verilator_binary_sha256': sha(verilator)}

    def execute(cmd, name, negative=False):
        cmd = list(map(str, cmd)); start = time.monotonic()
        p = subprocess.run(cmd, cwd=str(out), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = out/(name+'.log'); log.write_bytes(p.stdout)
        report['commands'].append({'command': cmd, 'exit_code': p.returncode,
            'seconds': time.monotonic()-start, 'log': log.name, 'log_sha256': sha(log)})
        content = p.stdout.decode('utf-8', errors='replace')
        if p.returncode and not negative:
            raise RuntimeError('failed '+name+'\n'+content[-4000:])
        return p.returncode, content

    def build(enable, burst, source, name):
        obj=out/('obj-'+name)
        execute([verilator, '--cc', '--exe', '--build', '--assert',
            '--x-initial', 'unique', '--x-assign', 'unique', '-j', workers,
            '--top-module', 'policy_top', '--Mdir', obj,
            '-GPOLICY_ENABLE='+str(enable), '-GMAX_CONSUMER_BURST='+str(burst),
            '-CFLAGS', '-std=c++17 -Wall -Wextra -Werror',
            top, original, source, driver], name+'-build')
        return obj/'Vpolicy_top'

    try:
        _, version=execute([verilator, '--version'], 'verilator-version')
        report['versions']['verilator']=version.strip()
        _, version=execute(['g++', '--version'], 'g++-version')
        report['versions']['g++']=version.splitlines()[0]
        binaries={}
        for enable, burst in ((0,2),(1,1),(1,2),(1,4)):
            name='enabled%d-burst%d' % (enable,burst)
            binary=build(enable,burst,candidate,name); binaries[(enable,burst)]=binary
            for seed in SEEDS:
                command=[binary,'--burst',burst,'--seed',seed,'+verilator+rand+reset+2',
                         '+verilator+seed+'+str(seed)]
                if enable: command.append('--enabled')
                _, content=execute(command,name+'-seed'+str(seed))
                lines=re.findall(r'^POLICY_PASS (.+)$',content,re.M)
                if len(lines)!=1: raise ValueError('missing policy positive receipt')
                row={k:int(v) for k,v in (item.split('=') for item in lines[0].split())}
                if row['enabled']!=enable or row['burst']!=burst or row['seed']!=seed:
                    raise ValueError('configuration receipt mismatch')
                if not enable and row['default_compared_cycles']<=0:
                    raise ValueError('default was not compared cycle by cycle')
                report['measurements'].append(row)

        code, content=execute([binaries[(1,2)], '--enabled', '--burst',2,
                              '--negative-response'], 'negative-response', True)
        if code==0 or 'POLICY_CHECK_FAILED READ_DATA_MISMATCH' not in content:
            raise ValueError('corrupt response negative was not detected')

        # A real faulty RTL build must fail the independent class ordering test.
        old='consumer_next<=selected==OWNER_BITS\'(CLIENTS-1) ? OWNER_BITS\'(0) : selected+1\'b1;'
        text=candidate.read_text(encoding='utf-8')
        if text.count(old)!=1: raise ValueError('negative mutation anchor drift')
        bad=out/'popt_s_policy_arbiter_bad.sv'
        bad.write_text(text.replace(old, "consumer_next<=0;"),encoding='utf-8')
        binary=build(1,2,bad,'negative-stuck-consumer-cursor')
        code, content=execute([binary,'--enabled','--burst',2], 'negative-starvation', True)
        if code==0 or 'POLICY_CHECK_FAILED SATURATED_CLASS_ROUND_ROBIN' not in content:
            raise ValueError('stuck consumer cursor negative was not detected')
        report['negative_controls']=['corrupt-read-response','faulty-RTL-consumer-round-robin']
        base=next(x for x in report['measurements'] if x['enabled']==0 and x['seed']==143)
        report['comparisons']=[]
        for row in report['measurements']:
            if row['enabled'] and row['seed']==143:
                report['comparisons'].append({'burst':row['burst'],
                    'steady_cycles':row['steady_cycles'], 'baseline_steady_cycles':base['steady_cycles'],
                    'baseline_consumer_mean_response_cycles':base['consumer_response_latency_sum']/base['consumer_responses'],
                    'consumer_mean_response_cycles':row['consumer_response_latency_sum']/row['consumer_responses'],
                    'external_max_admission_cycles':row['max_external_admission_wait'],
                    'external_max_skipped_grants':row['max_external_skipped_grants'],
                    'external_skipped_grant_bound':2*(row['burst']+1)-1})
        report['passed']=True
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)
        raise
    finally:
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    run_policy(args.repo,args.out,args.workers)
