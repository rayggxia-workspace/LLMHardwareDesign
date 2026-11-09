"""Build frozen baseline/fork, prove observation invariance, then run ablations."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from audit import check
from instrument import generate,HERE


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(command,log,cwd,env=None):
    p=subprocess.run(list(map(str,command)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(p.stdout)
    if p.returncode:raise RuntimeError(str(command)+' exit '+str(p.returncode)+' '+p.stdout.decode(errors='replace')[-2400:])
    return p.stdout.decode()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    a.out=a.out.resolve();a.inputs=a.inputs.resolve()
    if not 1<=a.workers<=int(os.environ.get('SLURM_CPUS_PER_TASK','4')):raise ValueError('worker allocation')
    generated=a.out/'generated';generated.mkdir()
    source=json.loads((HERE/'source.json').read_text())
    for name,value in source['extra_inputs_sha256'].items():
        if digest(a.inputs/name)!=value:raise ValueError('auxiliary input SHA drift '+name)
    for name,info in source['traces'].items():
        if digest(a.inputs/name)!=info['lf_sha256']:raise ValueError('trace SHA drift '+name)
        (generated/name).write_bytes((a.inputs/name).read_bytes())
    (a.out/'m-profile.log').write_bytes((a.inputs/'m-profile.log').read_bytes())
    model=a.out/'instrumented.cpp';model.write_bytes(generate().encode())
    prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
    versions={'python':platform.python_version(),'gcc':subprocess.check_output(['g++','--version'],text=True).splitlines()[0]}
    for src,dst in ((HERE/'upstream/model.cpp',a.out/'baseline'),(model,a.out/'model')):
        execute(['g++',*flags,src,'-I'+str(HERE),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
                 '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',dst],a.out/(dst.name+'-build.log'),a.out)
    execute(['g++',*flags,HERE/'upstream/kernel_probe.cpp','-o',a.out/'kernel_probe'],a.out/'kernel-build.log',a.out)
    env=dict(os.environ,BLOCK_STUDY_MODEL=str(a.out/'model'))
    for script in ('check_kernels.py','validate.py','smoke.py'):
        execute([sys.executable,'-B',HERE/'upstream'/script],a.out/(script+'.log'),a.out,env)
    execute([sys.executable,'-B',HERE/'oracle.py'],a.out/'oracle.log',a.out)

    def case(item):
        workload,profile,variant,binary=item
        name='-'.join(item);log=a.out/(name+'.log')
        command=[a.out/binary,generated/(workload+'.trace'),profile]
        if binary=='model':command.append(variant)
        output=execute(command,log,a.out)
        if 'MODEL_FAILURE' in output:raise RuntimeError(output[-2400:])
        rows=[json.loads(s[7:]) for s in output.splitlines() if s.startswith('RESULT ')]
        if len(rows)!=1:raise RuntimeError('missing/duplicate RESULT')
        row=rows[0];audit=check(row,generated/(workload+'.trace')) if binary=='model' else None
        banner=next((s.strip() for s in output.splitlines() if 'SystemC ' in s),'待核实')
        if 'SystemC 3.0.2' not in banner:raise ValueError('unexpected SystemC version '+banner)
        record=dict(workload=workload,profile=profile,variant=variant,binary=binary,result=row,audit=audit,
                    systemc_banner=banner,log_sha256=digest(log))
        (a.out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(dict(case=name,token_s=row['tokens_per_second'],bus_bytes=row['read_bus_bytes']+row['write_bus_bytes'])),flush=True)
        return record

    first=[('decode512',p,'observe',b) for p in ('queued_pipe_w8','queued_pipe_w16') for b in ('baseline','model')]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:records=list(pool.map(case,first))
    expected=json.loads((a.inputs/'baseline-results.json').read_text())
    for profile in ('queued_pipe_w8','queued_pipe_w16'):
        old=next(r['result'] for r in records if r['profile']==profile and r['binary']=='baseline')
        observed=next(r['result'] for r in records if r['profile']==profile and r['binary']=='model')
        original=next(r for r in expected if r['workload']=='decode512' and r['profile']==profile)
        if {k:v for k,v in observed.items() if k!='detail'}!=old:raise ValueError('instrumentation changes original timing/statistics')
        for key,value in old.items():
            if original[key]!=value:raise ValueError('Linux/upstream baseline mismatch '+key)
    variants=['prefix','prefix_slow','pair','combine','pair_combine','prefix_pair_combine',
              'queue_off','buffer1','credits8','k64','k128','prefix_k64','prefix_k128']
    cases=[('decode512','queued_pipe_w8',v,'model') for v in variants]
    cases += [('decode512','queued_pipe_w16',v,'model') for v in ('prefix','pair_combine','prefix_pair_combine')]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:records+=list(pool.map(case,cases))
    best=min((r for r in records if r['binary']=='model' and r['profile']=='queued_pipe_w8'),key=lambda r:r['result']['seconds'])['variant']
    supplement=[(w,'queued_pipe_w8',v,'model') for w in ('decode128','decode2048','prefill2') for v in sorted({'observe',best})]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:records+=list(pool.map(case,supplement))
    # Same-K cache addition must preserve arithmetic commands and static/dynamic B.
    for profile in ('queued_pipe_w8','queued_pipe_w16'):
        old=next(r for r in records if r['workload']=='decode512' and r['binary']=='model' and r['profile']==profile and r['variant']=='observe')
        new=next(r for r in records if r['workload']=='decode512' and r['profile']==profile and r['variant']=='prefix')
        for key in ('M_commands','M_tiles','M_work_ticks','vector_work_ticks'):
            if new['result'][key]!=old['result'][key]:raise ValueError('cache changes arithmetic work '+key)
        saved=sum(p['prefix_A_saved_bytes'] for p in new['result']['detail']['P'])
        if old['audit']['flow_totals']['A']['logical_read']-new['audit']['flow_totals']['A']['logical_read']!=saved:
            raise ValueError('retained A savings not conserved')
    report=dict(passed=True,versions=versions,workers=a.workers,baseline_and_observation_exact=True,
                upstream_baseline_exact=True,best_context512_variant=best,cases=records,
                source_commit=json.loads((a.out.parent/'inputs.json').read_text())['source_commit'],
                generated_source_sha256=digest(model),input_sha256={p.name:digest(p) for p in a.inputs.iterdir() if p.is_file()},
                source_sha256={str(p.relative_to(HERE)):digest(p) for p in HERE.rglob('*')
                               if p.is_file() and p.suffix in ('.py','.cpp','.hpp','.inc','.json','.sh')},
                scope='conditional SystemC architecture study; no production RTL/numeric-KV/physical/energy qualification')
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('P_DMA_STUDY_PASS '+str(len(records)),flush=True)


if __name__=='__main__':main()
