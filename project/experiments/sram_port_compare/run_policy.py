"""Default-policy whole-result replay, then a single-predicate intervention."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from generate_policy import generate,verify_sources,HERE,BASE
import compare_audit
import policy_audit

BEST='adaptive_prefix_pair_combine'
WORKLOADS=[('decode512','queued_pipe_w8',BEST),('decode512','queued_pipe_w16','adaptive'),
           ('decode2048','queued_pipe_w8',BEST),('prefill2','queued_pipe_w8',BEST)]
ROUTES=[('A48',48,1),('A64',64,1),('B16ctx8',16,8)]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(command,log,cwd,env=None,expected=0):
    process=subprocess.run(list(map(str,command)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    if process.returncode!=expected:
        raise RuntimeError(str(command)+' exit '+str(process.returncode)+' '+process.stdout.decode(errors='replace')[-3000:])
    return process.stdout.decode()


def prior_gate(args,lock):
    path=args.prior.resolve()
    if path.name!='run04-result.json':raise ValueError('use frozen run04-result.json basename')
    manifest=path.with_name('run04-inputs.json')
    for file in (path,manifest):
        if digest(file)!=lock['prerequisite_sha256'][file.name]:raise ValueError('run04 prerequisite SHA drift '+file.name)
    prior=json.loads(path.read_text(encoding='utf-8'));meta=json.loads(manifest.read_text(encoding='utf-8'))
    if prior.get('passed') is not True or not prior.get('regression_phase_passed') or not prior.get('source_commit'):
        raise ValueError('run04 has no actual passed full-regression receipt')
    if prior['source_commit']!=meta.get('source_commit'):raise ValueError('run04 manifest/source mismatch')
    for name,value in lock['dependency_sha256'].items():
        if name in ('generate_compare.py','run.py','compare_audit.py','source.json'):
            if prior['source_sha256'][name]!=value:raise ValueError('run04 frozen dependency mismatch '+name)
    return prior,dict(source_commit=prior['source_commit'],result_sha256=digest(path),inputs_sha256=digest(manifest))


def lookup(prior,workload,profile,variant,kib,ctx,q):
    rows=[c for c in prior['cases'] if c['workload']==workload and c['profile']==profile and c['variant']==variant
          and c['P_KiB']==kib and c['contexts']==ctx and c['P_port_quarters']==q
          and c['dual_ports'] and c['switch_cycles']==1 and c['reuse_A']]
    if len(rows)!=1:raise ValueError('missing/duplicate run04 reference '+str((workload,profile,variant,kib,ctx,q)))
    return rows[0]['result']


def plan(prior):
    jobs=[]
    for policy in (0,16):
        for workload,profile,variant in WORKLOADS:
            for route,kib,ctx in ROUTES:
                lookup(prior,workload,profile,variant,kib,ctx,4)
                jobs.append((workload,profile,variant,route,kib,ctx,4,policy))
    for route,kib,ctx in ROUTES[:2]:
        for q in (5,6,8):
            lookup(prior,'decode512','queued_pipe_w8',BEST,kib,ctx,q)
            jobs.append(('decode512','queued_pipe_w8',BEST,route,kib,ctx,q,16))
    return jobs


def main():
    parser=argparse.ArgumentParser()
    for name in ('inputs','out','prior'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();inputs=args.inputs.resolve();out=args.out.resolve()
    lock=verify_sources();prior,prior_index=prior_gate(args,lock);jobs=plan(prior)
    for name,value in lock['input_sha256'].items():
        if digest(inputs/name)!=value:raise ValueError('policy input SHA drift '+name)
    if int(os.environ.get('SLURM_CPUS_PER_TASK','0'))<1:raise ValueError('requires allocated Slurm CPUs')
    workers=min(4,int(os.environ['SLURM_CPUS_PER_TASK']))
    out.mkdir(parents=True,exist_ok=False);(out/'generated').mkdir()
    (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes());generate(out)
    for name in ('context_worker.inc','context_detail.hpp','detail.hpp'):
        assert digest(out/name)==prior['generated_sha256'][name],name+' changed outside policy predicate'
    prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
    execute(['g++',*flags,out/'model.cpp','-I'+str(out),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
             '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'model'],out/'build.log',out)
    execute(['g++',*flags,BASE/'upstream/kernel_probe.cpp','-o',out/'kernel_probe'],out/'kernel-build.log',out)
    env=dict(os.environ,BLOCK_STUDY_MODEL=str(out/'model'))
    for script in ('check_kernels.py','validate.py','smoke.py'):
        execute([sys.executable,'-B',BASE/'upstream'/script],out/(script+'.log'),out,env)
    def case(item):
        workload,profile,variant,route,kib,ctx,q,policy=item;trace=inputs/(workload+'.trace')
        name=f'{workload}-{profile}-{route}-q{q}-policy{policy}'
        command=[out/'model',trace,profile,variant,ctx,1,1,kib,1,q]
        if policy:command.append(policy)
        text=execute(command,out/(name+'.log'),out)
        if 'MODEL_FAILURE' in text or 'SystemC 3.0.2' not in text:raise ValueError('model failed '+name)
        rows=[json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')];assert len(rows)==1
        row=rows[0];old=lookup(prior,workload,profile,variant,kib,ctx,q)
        audit=compare_audit.check(row,trace,kib*1024,True,q,ctx,1,True)
        U_check=compare_audit.check_U_reference(row,old)
        checked=policy_audit.check_policy(row,old,policy)
        negatives=policy_audit.reject_checks(row,old,policy)
        record=dict(workload=workload,profile=profile,variant=variant,route=route,P_KiB=kib,contexts=ctx,
            P_port_quarters=q,policy_KiB=policy,result=row,audit=audit,U_reference=U_check,
            policy_audit=checked,negative_checks=negatives,
            speedup_vs_default_same_configuration=old['seconds']/row['seconds'],
            log_sha256=digest(out/(name+'.log')))
        (out/(name+'.json')).write_bytes((json.dumps(record,indent=2)+'\n').encode())
        print(json.dumps(dict(case=name,tokens_s=row['tokens_per_second'],
            speedup_vs_default_same_configuration=record['speedup_vs_default_same_configuration'])),flush=True)
        return record
    records=[]
    for defaults in (True,False):
        batch=[item for item in jobs if (item[-1]==0)==defaults]
        with ThreadPoolExecutor(max_workers=workers) as pool:records+=list(pool.map(case,batch))
    invalid=[]
    for label,value in (('unsupported-policy','32'),('numeric-tail','16junk')):
        text=execute([out/'model',inputs/'decode512.trace','queued_pipe_w8',BEST,1,1,1,48,1,4,value],
                     out/('reject-'+label+'.log'),out,expected=2)
        assert 'RESULT ' not in text;invalid.append(label)
    for kind in ('source_sha256','prerequisite_sha256'):
        bad=deepcopy(lock);name=next(iter(bad[kind]));value=bad[kind][name]
        bad[kind][name]=('0' if value[0]!='0' else '1')+value[1:]
        try:
            if kind=='source_sha256':verify_sources(bad)
            else:prior_gate(args,bad)
        except ValueError:pass
        else:raise ValueError('policy verifier accepted drift '+kind)
    report=dict(passed=True,issue=247,source_commit=json.loads((out.parent/'inputs.json').read_text(encoding='utf-8'))['source_commit'],
        scope='single adaptive-predicate capacity reference intervention; actual data capacity/ports/context and core clock unchanged',
        prior_run04=prior_index,default_full_result_replays=12,default_phase_passed=True,cases=records,
        invalid_CLI_rejected=invalid,source_and_prior_SHA_negative=True,
        fixed_P_count=2,fixed_U_bytes=16384,fixed_vector_lanes=4,fixed_bandwidth_B_s=17100000000,
        versions=dict(python=platform.python_version(),SystemC='3.0.2',gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]),
        input_sha256=lock['input_sha256'],source_lock=lock,
        source_sha256={name:digest(HERE/name) for name in lock['source_sha256']},
        generated_sha256={p.name:digest(p) for p in out.iterdir() if p.suffix in ('.cpp','.hpp','.inc')})
    (out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print('PREFETCH_POLICY_COMPARE_PASS '+str(len(records)),flush=True)


if __name__=='__main__':main()
