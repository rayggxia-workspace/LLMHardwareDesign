"""Slurm-only SystemC projection with finite-M RTL/control provenance."""
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
from generate_round3 import generate

HERE=Path(__file__).resolve().parent
RUN19_SHA='b16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098'
RUN16_SHA='78c57febe43f2a114a8a21ca9b5992b465d7b7589f05c83eb68e5f97923d4ef7'
RUN18_SHA='fb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78'
WORK=[('decode512','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('decode512','queued_pipe_w16','adaptive'),
      ('decode2048','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('prefill2','queued_pipe_w8','adaptive_prefix_pair_combine')]

def plan():
    return [dict(workload=w,profile=p,variant=v,dual_ports=d,iteration3_buffers=b,R1_enabled=True,R2_enabled=True,
                 contexts=8,P_KiB=16,switch_cycles=1,reuse_A=True,P_port_quarters=4,policy_KiB=0)
            for b in (0,1,2) for w,p,v in WORK for d in (False,True)]

def lookup(prior,w,p,v,d):
    matches=[c for c in prior['cases'] if (c['workload'],c['profile'],c['variant'],c['dual_ports'])==(w,p,v,d) and c['iteration2_enabled']]
    audit.require(len(matches)==1,'unique R2 active baseline missing');return matches[0]['result']

def execute(command,log,cwd,expected=0,env=None):
    command=list(map(str,command));process=subprocess.run(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    if process.returncode!=expected:raise RuntimeError(str(command)+' exit '+str(process.returncode)+'\n'+process.stdout.decode(errors='replace')[-2400:])
    return process.stdout.decode()

def result(text):
    rows=[json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
    audit.require(len(rows)==1 and 'MODEL_FAILURE' not in text and 'SystemC 3.0.2' in text,'invalid actual SystemC result')
    return rows[0]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);args=parser.parse_args()
    root=args.root.resolve();repo=root/'source';inputs=root/'inputs';out=root/'results';cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
    audit.require(bool(os.environ.get('SLURM_JOB_ID')) and 1<=cpus<=4,'actual Slurm1..4CPU allocation required')
    manifest=json.loads((root/'inputs.json').read_bytes())
    audit.require(re.fullmatch('[0-9a-f]{40}',manifest.get('source_commit','')) is not None,'source commit absent')
    for field,base in (('code_sha256',repo),('input_sha256',root)):
        audit.require(bool(manifest.get(field)),'empty deployment lock '+field)
        for name,digest in manifest[field].items():audit.require(audit.sha(base/name)==digest,'deployment drift '+name)
    for name,digest in [('run19-result.json',RUN19_SHA),('r1-calibration-result.json',RUN16_SHA),('r2-calibration-result.json',RUN18_SHA)]:
        audit.require(audit.sha(root/name)==digest,'frozen prerequisite changed '+name)
    prior=json.loads((root/'run19-result.json').read_bytes());audit.require(prior.get('passed') is True and prior.get('baseline_phase_passed') is True and len(prior['cases'])==16,'R2 prior incomplete')
    for name,digest in prior['input_sha256'].items():audit.require(audit.sha(inputs/name)==digest,'old trace/profile changed '+name)
    audit.require(json.loads((HERE/'plan.json').read_bytes())==plan(),'R3 plan drift')
    r1=root/'r1-calibration-result.json';r2=root/'r2-calibration-result.json';calibration=root/'calibration-result.json';profile=audit.read_calibration(calibration)
    out.mkdir(exist_ok=False)
    report=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=audit.sha(root/'inputs.json'),scope=audit.SCOPE,
        prior_run19_sha256=RUN19_SHA,input_sha256=prior['input_sha256'],R3_calibration=profile,baseline_phase_passed=False,
        versions=dict(python=platform.python_version(),SystemC='3.0.2'),cases=[],primary_target=prior['primary_target'],
        unchanged_hardware=prior['unchanged_hardware'],layers=prior['layers'],full_P_DMA_integration=False,physical_qualified=False)
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    try:
        report['versions']['gcc']=execute(['g++','--version'],out/'gcc-version.log',out).splitlines()[0]
        generated=out/'generated';generation=generate(repo,generated,r1,r2,calibration)
        audit.require(generation['round2_generated_sha256']==prior['generation']['generated_sha256'],'R2 generated sources differ from actual run19')
        report['generation']=generation;report['round2_generated_exact']=True
        (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219');flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
        def build(folder,binary,log):
            execute(['g++',*flags,folder/'model.cpp','-I'+str(folder),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),'-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',binary],log,out)
        build(generated,out/'model',out/'build.log')
        frozen=repo/'project/experiments/p_dma_study/upstream'
        execute(['g++',*flags,frozen/'kernel_probe.cpp','-o',out/'kernel_probe'],out/'kernel-build.log',out)
        env=dict(os.environ,BLOCK_STUDY_MODEL=str(out/'model'));env.pop('U_FUSION_EVENTS',None);env.pop('U_FUSION_TRACE_SHA256',None)
        for script in ('check_kernels.py','validate.py','smoke.py'):execute([sys.executable,'-B',frozen/script],out/(script+'.log'),out,env=env)
        def command(trace,p,v,d,b):return [out/'model',trace,p,v,8,1,1,16,int(d),4,0,1,1,b]
        # Small real SystemC tests exercise both resident and context/prefix
        # address maps before fulltrace; no measured fulltensor math is claimed.
        edges=[]
        for k,n,abits,p,v in [(2048,16,32,'queued_pipe_w8','adaptive_prefix_pair_combine'),
                              (11008,128,32,'queued_pipe_w8','adaptive_prefix_pair_combine'),
                              (2049,17,32,'queued_pipe_w8','adaptive_prefix_pair_combine'),
                              (2048,16,16,'queued_pipe_w8','adaptive_prefix_pair_combine'),
                              (2048,16,32,'queued_pipe_w16','adaptive')]:
            label='edge-K{}-N{}-A{}-{}'.format(k,n,abits,p);trace=out/(label+'.trace')
            trace.write_text('3 1 1\n0 {} {} 1\n1 {} 16 1\n2 {} 32 0\n2 Dot {} 1 {} {} 1 16 0 2 0 1\n'.format(k,abits,k*n,n,n,n,k),encoding='utf8')
            for dual in (False,True):
                baseline=result(execute(command(trace,p,v,dual,0),out/(label+'-'+str(int(dual))+'-0.log'),out))
                baseline.pop('iteration3_study')
                for b in (1,2):
                    log=out/(label+'-'+str(int(dual))+'-'+str(b)+'.log');row=result(execute(command(trace,p,v,dual,b),log,out))
                    checked=audit.check(row,baseline,trace,profile,b)
                    edges.append(dict(trace=trace.name,trace_sha256=audit.sha(trace),dual_ports=dual,buffers=b,audit=checked,log_sha256=audit.sha(log),result=row))
        report['smalltrace_cases']=edges;save()
        def case(item):
            w,p,v,d,b=item;trace=inputs/(w+'.trace');name='{}-{}-{}-buf{}'.format(w,p,'idealdual' if d else 'shared',b)
            cmd=command(trace,p,v,d,b);log=out/(name+'.log');row=result(execute(cmd,log,out));baseline=lookup(prior,w,p,v,d)
            checked=audit.check(row,baseline,trace,profile,b);negatives=audit.reject_checks(row,baseline,trace,profile,b)
            record=dict(workload=w,profile=p,variant=v,contexts=8,P_KiB=16,dual_ports=d,switch_cycles=1,reuse_A=True,
                P_port_quarters=4,policy_KiB=0,R1_enabled=True,R2_enabled=True,iteration3_buffers=b,result=row,audit=checked,
                negative_checks=negatives,command=list(map(str,cmd)),speedup_vs_same_layer_R2=baseline['seconds']/row['seconds'],log_sha256=audit.sha(log))
            (out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
            print('ROUND3_CASE '+name+' tokens_s='+str(row['tokens_per_second']),flush=True);return record
        for b in (0,1,2):
            jobs=[(w,p,v,d,b) for w,p,v in WORK for d in (False,True)]
            with ThreadPoolExecutor(max_workers=cpus) as pool:
                for record in pool.map(case,jobs):report['cases'].append(record);save()
            if b==0:report['baseline_phase_passed']=True;save()
        invalid=[]
        for value in ('3','2junk','-1'):
            text=execute(command(inputs/'decode512.trace','queued_pipe_w8','adaptive_prefix_pair_combine',False,value),out/('invalid-'+str(len(invalid))+'.log'),out,expected=2)
            audit.require('invalid iteration3 buffer count' in text and 'RESULT ' not in text,'invalid finite buffer count accepted');invalid.append(value)
        report['invalid_CLI_rejected']=invalid
        missing=out/'no-finite-profile';generate(repo,missing,r1,r2);build(missing,out/'no-finite-model',out/'no-finite-build.log')
        cmd=command(inputs/'decode512.trace','queued_pipe_w8','adaptive_prefix_pair_combine',False,1);cmd[0]=out/'no-finite-model'
        text=execute(cmd,out/'no-finite-profile.log',out,expected=2)
        audit.require('requires passed finite service profile' in text and 'RESULT ' not in text,'missing finite calibration accepted');report['missing_profile_rejected']=True
        raw=json.loads(calibration.read_bytes());rejected=[]
        for label,mutate in [('unpassed',lambda x:x.__setitem__('passed',False)),
             ('source_identity',lambda x:x['control_source_sha256'].__setitem__('finite_control.hpp','0'*64)),
             ('free_ACK',lambda x:x['profile']['ack_delays'].__setitem__('nominal_read_accept_to_consumed_ack_cycles',[0])),
             ('unmatched_control',lambda x:x['runs'][0]['control'].__setitem__('matched',False)),
             ('unbound_measurement',lambda x:x['profile']['rows'][0].__setitem__('log_sha256','0'*64)),
             ('unbounded_buffers',lambda x:x['profile'].__setitem__('buffer_choices',[1,2,8]))]:
            bad=deepcopy(raw);mutate(bad);path=out/('bad-profile-'+label+'.json');path.write_text(json.dumps(bad),encoding='utf8')
            try:audit.read_calibration(path)
            except (ValueError,KeyError):rejected.append(label)
            else:raise ValueError('bad finite profile accepted '+label)
        report['profile_negative_rejections']=rejected
        best={}
        for dual in (False,True):
            choices=[c for c in report['cases'] if c['workload']=='decode512' and c['profile']=='queued_pipe_w8' and c['dual_ports']==dual]
            winner=max(choices,key=lambda c:c['result']['tokens_per_second']);best['idealdual' if dual else 'shared']=dict(buffers=winner['iteration3_buffers'],tokens_per_second=winner['result']['tokens_per_second'])
        report['best_measured_configuration_including_R2_baseline']=best
        report['target_status']=dict(legacy_conditional_target_reached=best['idealdual']['tokens_per_second']>=5,
            ideal_target_tokens_per_second=best['idealdual']['tokens_per_second'],shared_projection_tokens_per_second=best['shared']['tokens_per_second'],actual_four_1RW_hardware_5_tokens_s_claimed=False)
        report['passed']=True
    except Exception as error:report['error']=repr(error);report['traceback']=traceback.format_exc();raise
    finally:save()
    print('ROUND3_FINITE_M_SYSTEMC_PASS24',flush=True)

if __name__=='__main__':main()
