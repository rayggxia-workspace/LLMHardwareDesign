"""Replay21 cases in the unchanged PR241/Issue247 S32/S96 timing system."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import traceback

HERE=Path(__file__).resolve().parent
PRIOR_SHA={
 'run01':'62c787396bd331cb2c6d8a0a4352a4ebb83456616eb141bc50c33655d84f3fc3',
 'run04':'966729e962ecde76f755a9da873f3fb7ac566e4dd454f45e7d4b6f8f76c73cce',
 'run05':'4dcb0f01357e2f71fcf9f90deeab1d1dd50101b3d928b3e9866473c91c133777',
 'run12':'e8c72c436d52969f35eb6c623b8fbedbcdbd48d35c8a4fc69f5cc2ad94ec6c41',
}
BEST='adaptive_prefix_pair_combine'
WORK=[('decode512','queued_pipe_w8',BEST),('decode512','queued_pipe_w16','adaptive'),
      ('decode2048','queued_pipe_w8',BEST),('prefill2','queued_pipe_w8',BEST)]
FIELDS=('workload','profile','variant','contexts','switch_cycles','reuse_A','P_KiB','dual_ports','P_port_quarters','policy_KiB')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plan():
    jobs=[]
    def add(work,profile,variant,ctx,kib,dual,policy,role):
        jobs.append(dict(workload=work,profile=profile,variant=variant,contexts=ctx,switch_cycles=1,
                         reuse_A=True,P_KiB=kib,dual_ports=bool(dual),P_port_quarters=4,policy_KiB=policy,role=role))
    for work,profile,variant in WORK:
        for role,ctx,dual in [('baseline',1,0),('contexts_only',8,0),('ideal_1R1W_only',1,1),('contexts_plus_ideal_1R1W',8,1)]:
            add(work,profile,variant,ctx,16,dual,0,role)
    for work in ('decode512','prefill2'):
        for kib in (48,64):add(work,'queued_pipe_w8',BEST,1,kib,1,16,'unimplemented_capacity_reference')
    add('decode512','queued_pipe_w8','observe',1,16,0,0,'original_PR241_reference')
    assert len(jobs)==21
    return jobs


def key(c):return tuple(c[f] for f in FIELDS)


def normalize(record,kind):
    if kind=='run12':
        v=record['command']
        return dict(workload=record['workload'],profile=record['profile'],variant=v[3],contexts=int(v[4]),
                    switch_cycles=int(v[5]),reuse_A=bool(int(v[6])),P_KiB=int(v[7]),dual_ports=bool(int(v[8])),
                    P_port_quarters=int(v[9]),policy_KiB=int(v[10]) if len(v)>10 else 0)
    return dict(workload=record['workload'],profile=record['profile'],variant=record['variant'],
        contexts=record['contexts'],switch_cycles=record.get('switch_cycles',1),reuse_A=record.get('reuse_A',True),
        P_KiB=record.get('P_KiB',16),dual_ports=record.get('dual_ports',kind=='run05'),
        P_port_quarters=record.get('P_port_quarters',4),policy_KiB=record.get('policy_KiB',0))


def prior_gate(path,expected):
    if sha(path)!=expected:raise ValueError('historical receipt SHA drift '+str(path))
    report=json.loads(path.read_text(encoding='utf-8'))
    if report.get('passed') is not True or not re.fullmatch('[0-9a-f]{40}',report.get('source_commit','')):
        raise ValueError('historical receipt has no passed/source evidence')
    return report


def references(priors,cfg):
    found=[]
    for kind in ('run05','run04','run01','run12'):
        report=priors[kind].get('legacy',priors[kind]) if kind=='run12' else priors[kind]
        matches=[c for c in report['cases'] if key(normalize(c,kind))==key(cfg)]
        if len(matches)>1:raise ValueError('duplicate historical key '+kind+' '+str(key(cfg)))
        if matches:found.append((kind,matches[0]['result']))
    return found


def assert_projection(actual,old,path='result'):
    """Every old field/value must remain; only new fields can be outside projection."""
    if isinstance(old,dict):
        if not isinstance(actual,dict) or not old.keys()<=actual.keys():raise ValueError('missing old fields '+path)
        for k,v in old.items():assert_projection(actual[k],v,path+'.'+k)
    elif isinstance(old,list):
        if not isinstance(actual,list) or len(actual)!=len(old):raise ValueError('old list changed '+path)
        for i,v in enumerate(old):assert_projection(actual[i],v,path+'.'+str(i))
    elif actual!=old:raise ValueError('old value changed '+path)


def compare_history(row,found):
    if not found:raise ValueError('case has no accepted historical receipt')
    checked=[]
    for kind,old in found:
        if kind=='run01':assert_projection(row,old)
        else:
            current=deepcopy(row)
            if kind=='run04':
                if set(current)-set(old)!={'policy_study'}:raise ValueError('unexpected extra run04 result fields')
                current.pop('policy_study')
            if current!=old:raise ValueError('whole RESULT historical drift '+kind)
        checked.append(dict(prior=kind,full_old_fields_equal=True,
                            mode='recursive_all_old_fields' if kind=='run01' else 'only_new_policy_metadata' if kind=='run04' else 'exact_full_result'))
    return checked


def execute(command,log,cwd,expected=0,env=None):
    run=subprocess.run([str(x) for x in command],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(run.stdout)
    if run.returncode!=expected:raise RuntimeError(str(command)+' exit '+str(run.returncode)+'\n'+run.stdout.decode(errors='replace')[-2500:])
    return run.stdout.decode()


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();repo=root/'source';inputs=root/'inputs';out=root/'results'
    cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
    if not os.environ.get('SLURM_JOB_ID') or not 1<=cpus<=4:raise ValueError('requires actual Slurm allocation, max4cores')
    manifest=json.loads((root/'inputs.json').read_text(encoding='utf-8'))
    if not re.fullmatch('[0-9a-f]{40}',manifest.get('source_commit','')):raise ValueError('real source commit required')
    for field,base in (('code_sha256',repo),('input_sha256',root)):
        if not manifest.get(field):raise ValueError('empty deployment lock '+field)
        for name,digest in manifest[field].items():
            if sha(base/name)!=digest:raise ValueError('deployment SHA drift '+name)
    sys.path.insert(0,str(repo/'project/experiments/sram_port_compare'))
    from generate_policy import generate,verify_sources,BASE
    import compare_audit
    lock=verify_sources()
    for name,digest in lock['input_sha256'].items():
        if sha(inputs/name)!=digest:raise ValueError('frozen trace/input drift '+name)
    priors={k:prior_gate(root/(k+'-result.json'),v) for k,v in PRIOR_SHA.items()}
    prior_inputs={}
    for name,old in priors.items():
        basename=name+'-inputs.json';path=root/basename
        if basename not in manifest['input_sha256']:raise ValueError('historical inputs not deployment-locked '+basename)
        previous_manifest=json.loads(path.read_text(encoding='utf-8'))
        if previous_manifest.get('source_commit')!=old['source_commit']:raise ValueError('historical result/input source mismatch '+name)
        prior_inputs[basename]=sha(path)
    jobs=plan()
    if json.loads((HERE/'plan.json').read_text(encoding='utf-8'))!=jobs:raise ValueError('checked-in21case plan drift')
    for cfg in jobs:
        if not references(priors,cfg):raise ValueError('missing historical coverage '+str(key(cfg)))
    out.mkdir(exist_ok=False);generated=out/'generated';generated.mkdir()
    report=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=sha(root/'inputs.json'),
        scope='Unchanged PR241/Issue247 S32/S96 queued/pipeline conditional evaluation,300MHz,2P/1U,17.1GB/s; no native_serial conversion',
        qualifications=dict(current_native_4x1RW_is_not_true_1R1W=True,
            conservative_no_extra_port_credit='16KiB shared calendar+ctx8 is an architecture-study reference, not a proven RTL throughput bound',
            ideal_dual='two64B/cycle directions; target reference only, not implemented four1RW-bank score',
            capacities='48/64KiB reference only; not implemented',
            contexts='old S32/S96 register-context model; native8xS64 does not acquire S96 qualification'),
        versions=dict(python=platform.python_version(),SystemC='3.0.2',gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]),
        prior_sha256=PRIOR_SHA,prior_inputs_sha256=prior_inputs,input_sha256=lock['input_sha256'],cases=[],generated_sha256={})
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    try:
        generate(generated)
        old_generated=priors['run12']['legacy']['generated_sha256']
        actual={name:sha(generated/name) for name in old_generated}
        if actual!=old_generated:raise ValueError('generated old binary source differs from actual run12')
        report['generated_sha256']=actual;report['run12_generated_exact']=True
        (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219');flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
        execute(['g++',*flags,generated/'model.cpp','-I'+str(generated),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
                 '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'model'],out/'build.log',out)
        execute(['g++',*flags,BASE/'upstream/kernel_probe.cpp','-o',out/'kernel_probe'],out/'kernel-build.log',out)
        env=dict(os.environ,BLOCK_STUDY_MODEL=str(out/'model'));env.pop('U_FUSION_EVENTS',None);env.pop('U_FUSION_TRACE_SHA256',None)
        for script in ('check_kernels.py','validate.py','smoke.py'):
            execute([sys.executable,'-B',BASE/'upstream'/script],out/(script+'.log'),out,env=env)
        def case(cfg):
            trace=inputs/(cfg['workload']+'.trace');name=cfg['workload']+'-'+cfg['profile']+'-'+cfg['role']+'-'+str(cfg['P_KiB'])
            command=[out/'model',trace,cfg['profile'],cfg['variant'],cfg['contexts'],1,1,cfg['P_KiB'],int(cfg['dual_ports']),4,cfg['policy_KiB']]
            text=execute(command,out/(name+'.log'),out)
            rows=[json.loads(s[7:]) for s in text.splitlines() if s.startswith('RESULT ')]
            if len(rows)!=1 or 'MODEL_FAILURE' in text or 'SystemC 3.0.2' not in text:raise ValueError('invalid actual case '+name)
            row=rows[0];audit=compare_audit.check(row,trace,cfg['P_KiB']*1024,cfg['dual_ports'],4,cfg['contexts'],1,True)
            policy=row['policy_study']
            if (policy['requested_policy_KiB']!=cfg['policy_KiB'] or policy['effective_policy_bytes']!=(cfg['policy_KiB'] or cfg['P_KiB'])*1024
                or policy['actual_P_capacity_bytes']!=cfg['P_KiB']*1024):raise ValueError('policy metadata drift')
            baseline=dict(cfg,contexts=1,P_KiB=16,dual_ports=False,policy_KiB=0)
            base_ref=references(priors,baseline)[0][1]
            U_check=compare_audit.check_U_reference(row,base_ref)
            found=references(priors,cfg);history=compare_history(row,found)
            record=dict(cfg,result=row,audit=audit,U_reference=U_check,reference_matches=history,
                        command=[str(x) for x in command],log_sha256=sha(out/(name+'.log')))
            (out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
            print('LEGACY_METRIC_CASE '+name+' tokens_s='+str(row['tokens_per_second']),flush=True)
            return record
        with ThreadPoolExecutor(max_workers=cpus) as pool:
            for record in pool.map(case,jobs):report['cases'].append(record);save()
        bad=deepcopy(lock);name=next(iter(bad['source_sha256']));bad['source_sha256'][name]='0'*64
        try:verify_sources(bad)
        except ValueError:report['source_drift_rejected']=True
        else:raise ValueError('source verifier accepted drift')
        try:prior_gate(root/'run12-result.json','0'*64)
        except ValueError:report['prior_drift_rejected']=True
        else:raise ValueError('prior verifier accepted drift')
        exemplar=next(c for c in report['cases'] if c['role']=='contexts_plus_ideal_1R1W' and c['profile']=='queued_pipe_w8' and c['workload']=='decode512')
        report['independent_negative_rejections']=compare_audit.reject_checks(exemplar['result'],inputs/'decode512.trace',16384,True,4,8,1,True)
        rejected=[]
        for args in ([8,1,1,16,1,4,32],[8,1,1,16,1,4,'0junk']):
            label='invalid-'+str(len(rejected));text=execute([out/'model',inputs/'decode512.trace','queued_pipe_w8',BEST,*args],out/(label+'.log'),out,expected=2)
            if 'RESULT ' in text:raise ValueError('invalid CLI produced RESULT')
            rejected.append(label)
        report['invalid_CLI_rejected']=rejected
        from verify_completed import verify_completed
        report['completed_independent_audit']=verify_completed(report,priors)
        report['all21_historical_fields_exact']=True;report['passed']=True
    except Exception as error:
        report['error']=repr(error);report['traceback']=traceback.format_exc();raise
    finally:save()
    print('LEGACY_METRIC_EVAL_PASS21',flush=True)


if __name__=='__main__':main()
