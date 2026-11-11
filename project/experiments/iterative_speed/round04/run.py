"""R4 actual SystemC sweep against best R2, with measured lane4 fees only."""
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
from generate_round4 import generate

HERE=Path(__file__).resolve().parent
RUN15_SHA='31213ac812866f463c8bd6e32a97d41e74e570b5310b6689f15e1e8fc6727cbc'
RUN16_SHA='78c57febe43f2a114a8a21ca9b5992b465d7b7589f05c83eb68e5f97923d4ef7'
RUN18_SHA='fb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78'
RUN19_SHA='b16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098'
WORK=[('decode512','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('decode512','queued_pipe_w16','adaptive'),
      ('decode2048','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('prefill2','queued_pipe_w8','adaptive_prefix_pair_combine')]

def plan():
    return [dict(workload=w,profile=p,variant=v,dual_ports=d,iteration4_enabled=e,R1_enabled=True,R2_enabled=True,
                 contexts=8,P_KiB=16,switch_cycles=1,reuse_A=True,P_port_quarters=4,policy_KiB=0)
            for e in (False,True) for w,p,v in WORK for d in (False,True)]

def lookup(prior,w,p,v,d,r2=False):
    matches=[c for c in prior['cases'] if (c['workload'],c['profile'],c['variant'],c['dual_ports'])==(w,p,v,d) and
             c['contexts']==8 and c['P_KiB']==16 and c['P_port_quarters']==4 and c['policy_KiB']==0 and
             c['switch_cycles']==1 and c['reuse_A'] and (not r2 or c['iteration2_enabled'])]
    audit.require(len(matches)==1,'unique matched prior missing');return matches[0]['result']

def execute(command,log,cwd,expected=0,env=None):
    process=subprocess.run(list(map(str,command)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    if process.returncode!=expected:raise RuntimeError(str(command)+' exit '+str(process.returncode)+'\n'+process.stdout.decode(errors='replace')[-2400:])
    return process.stdout.decode()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);args=parser.parse_args()
    root=args.root.resolve();repo=root/'source';inputs=root/'inputs';out=root/'results';cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
    audit.require(bool(os.environ.get('SLURM_JOB_ID')) and 1<=cpus<=4,'actual Slurm1..4CPU allocation required')
    manifest=json.loads((root/'inputs.json').read_bytes());audit.require(re.fullmatch('[0-9a-f]{40}',manifest.get('source_commit','')) is not None,'source commit absent')
    for field,base in (('code_sha256',repo),('input_sha256',root)):
        audit.require(bool(manifest.get(field)),'empty deployment lock '+field)
        for name,digest in manifest[field].items():audit.require(audit.sha(base/name)==digest,'deployment SHA drift '+name)
    for name,digest in [('run15-result.json',RUN15_SHA),('r1-calibration-result.json',RUN16_SHA),('r2-calibration-result.json',RUN18_SHA),('run19-result.json',RUN19_SHA)]:
        audit.require(audit.sha(root/name)==digest,'frozen prerequisite changed '+name)
    prior15=json.loads((root/'run15-result.json').read_bytes());prior=json.loads((root/'run19-result.json').read_bytes())
    audit.require(prior15.get('passed') is True and prior15.get('all21_historical_fields_exact') is True,'run15 incomplete')
    audit.require(prior.get('passed') is True and prior.get('baseline_phase_passed') is True and len(prior['cases'])==16,'best R2 prior incomplete')
    for name,digest in prior['input_sha256'].items():audit.require(audit.sha(inputs/name)==digest,'old input drift '+name)
    audit.require(json.loads((HERE/'plan.json').read_bytes())==plan(),'R4 plan changed')
    r1=root/'r1-calibration-result.json';r2=root/'r2-calibration-result.json';calibration=root/'calibration-result.json'
    base=audit.frozen(str(repo));r1_profile=base.legacy(str(repo)).read_calibration(r1);r2_profile=base.read_calibration(r2)
    profile=audit.read_calibration(calibration,repo);audit.require(profile['result_sha256']!=r2_profile['result_sha256'],'new native profile reused old identity')
    out.mkdir(exist_ok=False)
    report=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=audit.sha(root/'inputs.json'),scope=audit.SCOPE,
        prior_run15_sha256=RUN15_SHA,prior_run19_sha256=RUN19_SHA,input_sha256=prior['input_sha256'],
        R1_calibration=r1_profile,R2_calibration=r2_profile,R4_calibration=profile,baseline_phase_passed=False,
        versions=dict(python=platform.python_version(),SystemC='3.0.2'),cases=[],primary_target=prior['primary_target'],
        unchanged_hardware=prior['unchanged_hardware'],layers=prior['layers'],R3_finite_service_enabled=False)
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    try:
        report['versions']['gcc']=execute(['g++','--version'],out/'gcc-version.log',out).splitlines()[0]
        generated=out/'generated';generation=generate(repo,generated,r1,r2,calibration)
        audit.require(generation['round2_generated_sha256']==prior['generation']['generated_sha256'],'R2 generated source differs from actualrun19')
        report['generation']=generation;report['round2_generated_exact']=True
        (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219');flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
        def build(folder,binary,log):
            execute(['g++',*flags,folder/'model.cpp','-I'+str(folder),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',binary],log,out)
        build(generated,out/'model',out/'build.log');frozen=repo/'project/experiments/p_dma_study/upstream'
        execute(['g++',*flags,frozen/'kernel_probe.cpp','-o',out/'kernel_probe'],out/'kernel-build.log',out)
        env=dict(os.environ,BLOCK_STUDY_MODEL=str(out/'model'));env.pop('U_FUSION_EVENTS',None);env.pop('U_FUSION_TRACE_SHA256',None)
        for script in ('check_kernels.py','validate.py','smoke.py'):execute([sys.executable,'-B',frozen/script],out/(script+'.log'),out,env=env)
        def command(trace,p,v,d,e):return [out/'model',trace,p,v,8,1,1,16,int(d),4,0,1,1,int(e)]
        def case(item):
            w,p,v,d,e=item;trace=inputs/(w+'.trace');name='{}-{}-{}-r4{}'.format(w,p,'idealdual' if d else 'shared',int(e))
            cmd=command(trace,p,v,d,e);log=out/(name+'.log');text=execute(cmd,log,out)
            rows=[json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
            audit.require(len(rows)==1 and 'MODEL_FAILURE' not in text and 'SystemC 3.0.2' in text,'invalid actual R4 model output')
            row=rows[0];baseline=lookup(prior,w,p,v,d,True);old=lookup(prior15,w,p,v,d)
            args=(baseline,old,trace,r1_profile,r2_profile,profile,e,repo);checked=audit.check(row,*args);negative=audit.reject_checks(row,*args)
            record=dict(workload=w,profile=p,variant=v,contexts=8,P_KiB=16,dual_ports=d,switch_cycles=1,reuse_A=True,
                P_port_quarters=4,policy_KiB=0,R1_enabled=True,R2_enabled=True,iteration4_enabled=e,result=row,audit=checked,
                negative_checks=negative,command=list(map(str,cmd)),speedup_vs_same_layer_R2=baseline['seconds']/row['seconds'],log_sha256=audit.sha(log))
            (out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
            print('ROUND4_CASE '+name+' tokens_s='+str(row['tokens_per_second']),flush=True);return record
        for enabled in (False,True):
            with ThreadPoolExecutor(max_workers=cpus) as pool:
                for record in pool.map(case,[(w,p,v,d,enabled) for w,p,v in WORK for d in (False,True)]):report['cases'].append(record);save()
            if not enabled:report['baseline_phase_passed']=True;save()
        invalid=[]
        for value in ('2','1junk','-1'):
            cmd=command(inputs/'decode512.trace','queued_pipe_w8','adaptive_prefix_pair_combine',False,0);cmd[-1]=value
            text=execute(cmd,out/('invalid-'+str(len(invalid))+'.log'),out,expected=2)
            audit.require('invalid iteration4 NExp flag' in text and 'RESULT ' not in text,'invalid R4 flag accepted');invalid.append(value)
        report['invalid_CLI_rejected']=invalid
        cmd=command(inputs/'decode512.trace','queued_pipe_w8','adaptive_prefix_pair_combine',False,1);cmd[-2]=0
        text=execute(cmd,out/'R2-disabled.log',out,expected=2)
        audit.require('requires R1/R2 enabled' in text and 'RESULT ' not in text,'R4 accepted disabled R2');report['R2_disabled_rejected']=True
        missing=out/'no-new-profile';generate(repo,missing,r1,r2);build(missing,out/'no-new-profile-model',out/'no-new-profile-build.log')
        cmd=command(inputs/'decode512.trace','queued_pipe_w8','adaptive_prefix_pair_combine',False,1);cmd[0]=out/'no-new-profile-model'
        text=execute(cmd,out/'missing-new-profile.log',out,expected=2)
        audit.require('passed four-lane calibrated profile' in text and 'RESULT ' not in text,'missing four-lane profile accepted');report['missing_new_profile_rejected']=True
        raw=json.loads(calibration.read_bytes());rejected=[]
        for label,mutate in [('fee_minus_one',lambda x:x['profile']['rows'][7].__setitem__('charge_cycles',x['profile']['rows'][7]['charge_cycles']-1)),
            ('old_mode_identity',lambda x:x['profile']['rows'][0].__setitem__('mode','legacy_s32_low16_zeroextend_stateless_op12')),
            ('unpassed',lambda x:x.__setitem__('passed',False)),('lane2_disguised',lambda x:x['profile'].__setitem__('direct_lanes',2)),
            ('default_gate_absent',lambda x:x['gates'].__setitem__('default_lanes2_compatibility',False)),
            ('wrong_native_source',lambda x:x['rtl_source_sha256'].__setitem__('project/rtl/block_v2/block_v2_n.sv','0'*64)),
            ('unbound_log',lambda x:x['measurements']['compute_s32'][0].__setitem__('log_sha256','0'*64)),
            ('false_CALC_histogram',lambda x:next(r for r in x['runs'] if r['label']=='compute')['lane_counts'][0].__setitem__('calc_steps',0)),
            ('false_CALC_count',lambda x:next(r for r in x['runs'] if r['label']=='compute')['lane_path'].__setitem__('checked_commands',0))]:
            bad=deepcopy(raw);mutate(bad);path=out/('bad-profile-'+label+'.json');path.write_text(json.dumps(bad),encoding='utf8')
            try:audit.read_calibration(path,repo)
            except (ValueError,KeyError):rejected.append(label)
            else:raise ValueError('R4 accepted corrupted native profile '+label)
        report['profile_negative_rejections']=rejected
        best={}
        for dual in (False,True):
            choices=[c for c in report['cases'] if c['workload']=='decode512' and c['profile']=='queued_pipe_w8' and c['dual_ports']==dual]
            winner=max(choices,key=lambda c:c['result']['tokens_per_second'])
            best['idealdual' if dual else 'shared']=dict(iteration4_enabled=winner['iteration4_enabled'],tokens_per_second=winner['result']['tokens_per_second'])
        report['best_measured_including_R2']=best
        report['target_status']=dict(legacy_conditional_target_reached=best['idealdual']['tokens_per_second']>=5,
            ideal_target_tokens_per_second=best['idealdual']['tokens_per_second'],shared_projection_tokens_per_second=best['shared']['tokens_per_second'],actual_four_1RW_hardware_5_tokens_s_claimed=False)
        report['passed']=True
    except Exception as error:report['error']=repr(error);report['traceback']=traceback.format_exc();raise
    finally:save()
    print('ROUND4_LANES4_NEXP_PASS16',flush=True)

if __name__=='__main__':main()
