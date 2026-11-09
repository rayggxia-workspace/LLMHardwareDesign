"""P-only SRAM capacity sweep with independent traffic and baseline checks."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from generate import generate,HERE,BASE
from reject import rejections

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def execute(cmd,log,cwd,env=None):
    p=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(p.stdout)
    if p.returncode:raise RuntimeError(str(cmd)+' '+p.stdout.decode(errors='replace')[-2400:])
    return p.stdout.decode()

def main():
    a=argparse.ArgumentParser();a.add_argument('--inputs',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    args=a.parse_args();out=args.out.resolve();inputs=args.inputs.resolve();out.mkdir(exist_ok=False,parents=True)
    lock=json.loads((HERE/'source.json').read_text())
    for name,value in lock['input_sha256'].items():assert digest(inputs/name)==value,name
    (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
    (out/'generated').mkdir()
    generate(out)
    spec=importlib.util.spec_from_file_location('capacity_audit',out/'capacity_audit.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
    execute(['g++',*flags,out/'model.cpp','-I'+str(out),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'model'],out/'build.log',out)
    execute(['g++',*flags,BASE/'upstream/kernel_probe.cpp','-o',out/'kernel_probe'],out/'kernel-build.log',out)
    env=dict(os.environ,BLOCK_STUDY_MODEL=str(out/'model'))
    for script in ['check_kernels.py','validate.py','smoke.py']:
        execute([sys.executable,'-B',BASE/'upstream'/script],out/(script+'.log'),out,env)
    execute([sys.executable,'-B',BASE/'oracle.py'],out/'oracle.log',out)
    prior=json.loads((inputs/'prior-results.json').read_text())
    def case(item):
        workload,profile,variant,kib,lat=item;name=f'{workload}-{profile}-{variant}-s{kib}-p{lat}'
        output=execute([out/'model',inputs/(workload+'.trace'),profile,variant,kib,lat],out/(name+'.log'),out)
        assert 'MODEL_FAILURE' not in output
        rows=[json.loads(s[7:]) for s in output.splitlines() if s.startswith('RESULT ')];assert len(rows)==1
        r=rows[0];assert r['detail']['P_capacity_bytes']==kib*1024 and r['detail']['P_service_cycles']==lat
        assert 'SystemC 3.0.2' in output
        checked=audit.check(r,inputs/(workload+'.trace'),kib*1024)
        bad=deepcopy(r);bad['P_scratch_peak_bytes']=kib*1024+1
        try:audit.check(bad,inputs/(workload+'.trace'),kib*1024)
        except AssertionError:pass
        else:raise ValueError('capacity overflow accepted')
        if workload=='decode512' and kib>=64:
            sh=next(s for s in r['detail']['matrix_shapes'] if s['key']=='1x2048x11008b1l0')
            assert sh['flows']['A']['logical_read']==11008*4*2*36
        if kib==16 and lat==1:
            old=next(c['result'] for c in prior['cases'] if c['binary']=='model' and c['workload']==workload and c['profile']==profile and c['variant']==variant)
            observed=deepcopy(r);del observed['detail']['P_capacity_bytes'];del observed['detail']['P_service_cycles']
            assert observed==old,'16KiB full result regression'
        record=dict(workload=workload,profile=profile,variant=variant,P_KiB=kib,P_service_cycles=lat,result=r,audit=checked,log_sha256=digest(out/(name+'.log')))
        (out/(name+'.json')).write_bytes((json.dumps(record,indent=2)+'\n').encode())
        print(json.dumps(dict(case=name,tokens_s=r['tokens_per_second'],bus_bytes=r['read_bus_bytes']+r['write_bus_bytes'],commands=r['M_commands'])),flush=True)
        return record
    cases=[('decode512','queued_pipe_w8',v,k,1) for v in ['observe','adaptive_prefix_pair_combine'] for k in [16,32,43,48,64,128]]
    cases += [('decode512','queued_pipe_w16',v,k,1) for v in ['observe','adaptive'] for k in [16,48,64]]
    cases += [('decode512','queued_pipe_w8',v,64,2) for v in ['observe','adaptive_prefix_pair_combine']]
    cases += [(w,'queued_pipe_w8',v,k,1) for w in ['decode2048','prefill2'] for v in ['observe','adaptive_prefix_pair_combine'] for k in [16,64]]
    workers=min(4,int(os.environ['SLURM_CPUS_PER_TASK']))
    with ThreadPoolExecutor(max_workers=workers) as pool:records=list(pool.map(case,cases))
    first=next(r['result'] for r in records if r['P_KiB']==16 and r['variant']=='observe')
    negative=rejections(first,inputs/'decode512.trace')
    report=dict(passed=True,source_commit=json.loads((out.parent/'inputs.json').read_text())['source_commit'],
        scope='P-only capacity and P-port occupancy conditional SystemC study; no physical or tensor quality qualification',
        versions=dict(python=platform.python_version(),gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],SystemC='3.0.2'),
        fixed_U_bytes=16384,fixed_M_count=2,fixed_bandwidth=17100000000,cases=records,negative_checks=negative,
        baseline_16KiB_complete_result_exact=True,input_sha256=lock['input_sha256'],
        generated_sha256={n:digest(out/n) for n in ['model.cpp','matrix.inc','detail.hpp','capacity_audit.py']},
        source_sha256={p.name:digest(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.sh')})
    (out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print('SRAM_CAPACITY_PASS '+str(len(records)),flush=True)
if __name__=='__main__':main()
