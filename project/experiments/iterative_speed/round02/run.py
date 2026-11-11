"""R2 actual SystemC sweep: paired against R1 and bound to new RTL receipts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import traceback

import audit
from generate_round2 import generate

HERE=Path(__file__).resolve().parent
RUN15_SHA='31213ac812866f463c8bd6e32a97d41e74e570b5310b6689f15e1e8fc6727cbc'
RUN16_SHA='78c57febe43f2a114a8a21ca9b5992b465d7b7589f05c83eb68e5f97923d4ef7'
RUN17_SHA='bc27f6b66c63b7356a4ead76e800c539efb1499322f91c45114e6df79595d076'
WORK=[('decode512','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('decode512','queued_pipe_w16','adaptive'),
      ('decode2048','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('prefill2','queued_pipe_w8','adaptive_prefix_pair_combine')]


def plan():
    return [dict(workload=w,profile=p,variant=v,dual_ports=d,iteration2_enabled=e,
                 R1_enabled=True,contexts=8,P_KiB=16,switch_cycles=1,reuse_A=True,P_port_quarters=4,policy_KiB=0)
            for e in (False,True) for w,p,v in WORK for d in (False,True)]


def lookup(prior,work,profile,variant,dual,r1=False):
    matches=[c for c in prior['cases'] if c['workload']==work and c['profile']==profile and c['variant']==variant and
             c['contexts']==8 and c['P_KiB']==16 and c['dual_ports']==bool(dual) and c['P_port_quarters']==4 and
             c['policy_KiB']==0 and c['switch_cycles']==1 and c['reuse_A'] and (not r1 or c['nexp_enabled'])]
    if len(matches)!=1:raise ValueError('missing unique previous-round reference')
    return matches[0]['result']


def execute(command,log,cwd,expected=0,env=None):
    process=subprocess.run(list(map(str,command)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    if process.returncode!=expected:
        raise RuntimeError(str(command)+' exit '+str(process.returncode)+'\n'+process.stdout.decode(errors='replace')[-2400:])
    return process.stdout.decode()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);args=parser.parse_args()
    root=args.root.resolve();repo=root/'source';inputs=root/'inputs';out=root/'results'
    cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
    if not os.environ.get('SLURM_JOB_ID') or not 1<=cpus<=4:raise ValueError('actual Slurm allocation of1..4 CPUs required')
    manifest=json.loads((root/'inputs.json').read_text(encoding='utf-8'))
    if not re.fullmatch('[0-9a-f]{40}',manifest.get('source_commit','')):raise ValueError('source commit absent')
    for field,base in (('code_sha256',repo),('input_sha256',root)):
        if not manifest.get(field):raise ValueError('empty deployment lock '+field)
        for name,digest in manifest[field].items():
            if audit.sha(base/name)!=digest:raise ValueError('deployment SHA mismatch '+name)
    for name,digest in [('run15-result.json',RUN15_SHA),('r1-calibration-result.json',RUN16_SHA),('run17-result.json',RUN17_SHA)]:
        if audit.sha(root/name)!=digest:raise ValueError('prior receipt SHA mismatch '+name)
    prior15=json.loads((root/'run15-result.json').read_text());prior17=json.loads((root/'run17-result.json').read_text())
    if prior15.get('passed') is not True or prior15.get('all21_historical_fields_exact') is not True:raise ValueError('run15 incomplete')
    if prior17.get('passed') is not True or prior17.get('baseline_phase_passed') is not True or len(prior17['cases'])!=16:raise ValueError('R1 prior incomplete')
    r1_calibration=root/'r1-calibration-result.json';calibration=root/'calibration-result.json'
    r1_profile=audit.legacy(str(repo)).read_calibration(r1_calibration);r2_profile=audit.read_calibration(calibration)
    if r1_profile['result_sha256']==r2_profile['result_sha256']:raise ValueError('R2 cannot reuse old profile identity')
    if json.loads((HERE/'plan.json').read_text())!=plan():raise ValueError('R2 frozen plan drift')
    for name,digest in prior17['input_sha256'].items():
        if audit.sha(inputs/name)!=digest:raise ValueError('old input drift '+name)
    out.mkdir(exist_ok=False);generated=out/'generated'
    report=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=audit.sha(root/'inputs.json'),
        scope=audit.SCOPE,prior_run15_sha256=RUN15_SHA,prior_run17_sha256=RUN17_SHA,
        input_sha256=prior17['input_sha256'],R1_calibration=r1_profile,R2_calibration=r2_profile,
        versions=dict(python=platform.python_version(),SystemC='3.0.2'),cases=[],baseline_phase_passed=False,
        primary_target=prior17['primary_target'],unchanged_hardware=prior17['unchanged_hardware'],layers=prior17['layers'])
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    try:
        report['versions']['gcc']=execute(['g++','--version'],out/'gcc-version.log',out).splitlines()[0]
        generation=generate(repo,generated,r1_calibration,calibration)
        if generation['round1_generated_sha256']!=prior17['generation']['generated_sha256']:raise ValueError('frozen R1 generated sources differ from run17')
        report['generation']=generation;report['round1_generated_exact']=True
        (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219');flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
        def build(folder,binary,log):
            execute(['g++',*flags,folder/'model.cpp','-I'+str(folder),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
                     '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',binary],log,out)
        build(generated,out/'model',out/'build.log')
        frozen=repo/'project/experiments/p_dma_study/upstream'
        execute(['g++',*flags,frozen/'kernel_probe.cpp','-o',out/'kernel_probe'],out/'kernel-build.log',out)
        env=dict(os.environ,BLOCK_STUDY_MODEL=str(out/'model'));env.pop('U_FUSION_EVENTS',None);env.pop('U_FUSION_TRACE_SHA256',None)
        for script in ('check_kernels.py','validate.py','smoke.py'):
            execute([sys.executable,'-B',frozen/script],out/(script+'.log'),out,env=env)

        def case(item):
            work,prof,variant,dual,enabled=item;trace=inputs/(work+'.trace')
            name='{}-{}-{}-r2{}'.format(work,prof,'idealdual' if dual else 'shared',int(enabled))
            command=[out/'model',trace,prof,variant,8,1,1,16,int(dual),4,0,1,int(enabled)]
            text=execute(command,out/(name+'.log'),out)
            rows=[json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
            if len(rows)!=1 or 'MODEL_FAILURE' in text or 'SystemC 3.0.2' not in text:raise ValueError('invalid R2 case '+name)
            row=rows[0];baseline=lookup(prior17,work,prof,variant,dual,True);old=lookup(prior15,work,prof,variant,dual)
            audit_args=(baseline,old,trace,r1_profile,r2_profile,enabled,repo)
            checked=audit.check(row,*audit_args);negatives=audit.reject_checks(row,*audit_args)
            record=dict(workload=work,profile=prof,variant=variant,contexts=8,P_KiB=16,dual_ports=bool(dual),
                switch_cycles=1,reuse_A=True,P_port_quarters=4,policy_KiB=0,R1_enabled=True,iteration2_enabled=bool(enabled),
                result=row,audit=checked,negative_checks=negatives,command=list(map(str,command)),
                speedup_vs_same_layer_R1=baseline['seconds']/row['seconds'],log_sha256=audit.sha(out/(name+'.log')))
            (out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
            print('ROUND2_CASE '+name+' tokens_s='+str(row['tokens_per_second']),flush=True);return record
        for enabled in (False,True):
            jobs=[(w,p,v,d,enabled) for w,p,v in WORK for d in (False,True)]
            with ThreadPoolExecutor(max_workers=cpus) as pool:
                for record in pool.map(case,jobs):report['cases'].append(record);save()
            if not enabled:report['baseline_phase_passed']=True;save()

        invalid=[]
        for value in ('2','1junk','-1'):
            label='invalid-flag-'+str(len(invalid))
            text=execute([out/'model',inputs/'decode512.trace','queued_pipe_w8','adaptive_prefix_pair_combine',8,1,1,16,0,4,0,1,value],
                         out/(label+'.log'),out,expected=2)
            if 'RESULT ' in text or 'invalid iteration2 NExp flag' not in text:raise ValueError('invalid R2 flag accepted')
            invalid.append(value)
        text=execute([out/'model',inputs/'decode512.trace','queued_pipe_w8','adaptive_prefix_pair_combine',8,1,1,16,0,4,0,0,1],
                     out/'R1-disabled.log',out,expected=2)
        if 'RESULT ' in text or 'requires R1 enabled' not in text:raise ValueError('R2 accepted disabled R1')
        no_profile=out/'no-new-profile';generate(repo,no_profile,r1_calibration)
        build(no_profile,out/'no-new-profile-model',out/'no-new-profile-build.log')
        text=execute([out/'no-new-profile-model',inputs/'decode512.trace','queued_pipe_w8','adaptive_prefix_pair_combine',8,1,1,16,0,4,0,1,1],
                     out/'missing-new-profile.log',out,expected=2)
        if 'RESULT ' in text or 'passed stateless calibrated profile' not in text:raise ValueError('missing R2 profile accepted')
        report['invalid_CLI_rejected']=invalid;report['R1_disabled_rejected']=True;report['missing_new_profile_rejected']=True
        raw=json.loads(calibration.read_text());profile_negatives=[]
        for label,mutate in [
            ('fee_minus_one',lambda x:x['profile']['rows'][7].__setitem__('charge_cycles',x['profile']['rows'][7]['charge_cycles']-1)),
            ('free_S16_n8',lambda x:x['profile']['rows'][7].__setitem__('subcounts',[8])),
            ('old_mode_identity',lambda x:x['profile']['rows'][0].__setitem__('mode','legacy_s32_low16_zeroextend')),
            ('unpassed_calibration',lambda x:x.__setitem__('passed',False)),
            ('unbound_measurement_log',lambda x:x['measurements']['compute_s32'][0].__setitem__('log_sha256','0'*64)),
            ('old_command_measurement',lambda x:x['measurements']['compute_s32'][0].__setitem__('direct_mode',0)),
            ('stateless_gate_absent',lambda x:x['gates'].__setitem__('stateless_context_preservation',False)),
            ('old_batch_regression_absent',lambda x:x['gates'].__setitem__('old_batch_compatibility',False)),
        ]:
            bad=deepcopy(raw);mutate(bad);target=out/('negative-profile-'+label+'.json');target.write_text(json.dumps(bad),encoding='utf-8')
            try:audit.read_calibration(target)
            except (ValueError,KeyError):profile_negatives.append(label)
            else:raise ValueError('invalid R2 profile accepted '+label)
        report['profile_negative_rejections']=profile_negatives
        def main_case(dual):
            return next(c for c in report['cases'] if c['workload']=='decode512' and c['profile']=='queued_pipe_w8' and c['dual_ports']==dual and c['iteration2_enabled'])
        main=main_case(True);shared=main_case(False)
        report['target_status']=dict(legacy_conditional_target_reached=main['result']['seconds']<=.2,
            ideal_target_tokens_per_second=main['result']['tokens_per_second'],shared_projection_tokens_per_second=shared['result']['tokens_per_second'],
            actual_four_1RW_hardware_5_tokens_s_claimed=False)
        report['passed']=True
    except Exception as error:
        report['error']=repr(error);report['traceback']=traceback.format_exc();raise
    finally:save()
    print('ROUND2_STATELESS_NEXP_PASS16',flush=True)


if __name__=='__main__':main()
