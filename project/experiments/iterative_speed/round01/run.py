"""Round1: actual old-system model runs, using a completed integrated-U profile."""
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

import audit
from generate_round1 import generate

HERE=Path(__file__).resolve().parent
PRIOR_SHA='31213ac812866f463c8bd6e32a97d41e74e570b5310b6689f15e1e8fc6727cbc'
WORK=[('decode512','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('decode512','queued_pipe_w16','adaptive'),
      ('decode2048','queued_pipe_w8','adaptive_prefix_pair_combine'),
      ('prefill2','queued_pipe_w8','adaptive_prefix_pair_combine')]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plan():
    return [dict(workload=work,profile=profile,variant=variant,dual_ports=dual,nexp_enabled=enabled,
                 contexts=8,P_KiB=16,switch_cycles=1,reuse_A=True,P_port_quarters=4,policy_KiB=0)
            for enabled in (False,True) for work,profile,variant in WORK for dual in (False,True)]


def lookup(prior,work,profile,variant,dual):
    matches=[c for c in prior['cases'] if c['workload']==work and c['profile']==profile and c['variant']==variant
             and c['contexts']==8 and c['P_KiB']==16 and c['dual_ports']==bool(dual) and
             c['P_port_quarters']==4 and c['policy_KiB']==0 and c['switch_cycles']==1 and c['reuse_A']]
    if len(matches)!=1:raise ValueError('missing unique run15 reference')
    return matches[0]['result']


def execute(command,log,cwd,expected=0,env=None):
    process=subprocess.run(list(map(str,command)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log.write_bytes(process.stdout)
    if process.returncode!=expected:
        raise RuntimeError(str(command)+' exit '+str(process.returncode)+'\n'+process.stdout.decode(errors='replace')[-2400:])
    return process.stdout.decode()


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();repo=root/'source';inputs=root/'inputs';out=root/'results'
    cpus=int(os.environ.get('SLURM_CPUS_PER_TASK','0'))
    if not os.environ.get('SLURM_JOB_ID') or not 1<=cpus<=4:raise ValueError('actual Slurm allocation of1..4 CPUs required')
    manifest=json.loads((root/'inputs.json').read_text(encoding='utf-8'))
    if not re.fullmatch('[0-9a-f]{40}',manifest.get('source_commit','')):raise ValueError('source commit absent')
    for field,base in (('code_sha256',repo),('input_sha256',root)):
        if not manifest.get(field):raise ValueError('empty deployment lock '+field)
        for name,digest in manifest[field].items():
            if sha(base/name)!=digest:raise ValueError('deployment SHA mismatch '+name)
    if sha(root/'run15-result.json')!=PRIOR_SHA:raise ValueError('run15 prior SHA mismatch')
    prior=json.loads((root/'run15-result.json').read_text(encoding='utf-8'))
    if prior.get('passed') is not True or prior.get('all21_historical_fields_exact') is not True:
        raise ValueError('run15 prior did not finish historical replay')
    calibration=root/'calibration-result.json';profile=audit.read_calibration(calibration)
    if json.loads((HERE/'plan.json').read_text(encoding='utf-8'))!=plan():raise ValueError('frozen16case plan drift')
    for name,digest in prior['input_sha256'].items():
        if sha(inputs/name)!=digest:raise ValueError('run15 input drift '+name)
    out.mkdir(exist_ok=False);generated=out/'generated';generated.mkdir()
    report=dict(passed=False,source_commit=manifest['source_commit'],manifest_sha256=sha(root/'inputs.json'),
        scope='Round1 old-system NExp supplemental service replacement; unchanged300MHz/17.1GB/s/2P1U/16KiB/input; no full-LLM RTL qualification',
        prior_run15_sha256=PRIOR_SHA,input_sha256=prior['input_sha256'],calibration=profile,
        versions=dict(python=platform.python_version(),SystemC='3.0.2'),cases=[],baseline_phase_passed=False,
        primary_target=dict(workload='decode512',profile='queued_pipe_w8',contexts=8,dual_ports=True,P_KiB=16,
                            tokens_per_second=5,qualification='old-system conditional ideal-port target only; not achieved four1RW hardware speed'),
        unchanged_hardware=dict(core_clock_hz=300000000,aggregate_DDR_B_s=17100000000,P_count=2,U_count=1,P_S_bytes=16384,U_S_bytes=16384),
        layers=dict(shared='old shared-port ctx8 mechanism projection',ideal_dual='ideal64B read+64B write target; not implemented four1RW bandwidth'))
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    try:
        report['versions']['gcc']=execute(['g++','--version'],out/'gcc-version.log',out).splitlines()[0]
        generation=generate(repo,generated,calibration)
        if generation['frozen_generated_sha256']!=prior['generated_sha256']:
            raise ValueError('unchanged generator no longer produces run15 byte-identical sources')
        report['generation']=generation;report['frozen_generated_exact']=True
        (out/'m-profile.log').write_bytes((inputs/'m-profile.log').read_bytes())
        prefix=Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219');flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
        execute(['g++',*flags,generated/'model.cpp','-I'+str(generated),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
                 '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'model'],out/'build.log',out)
        frozen=repo/'project/experiments/p_dma_study/upstream'
        execute(['g++',*flags,frozen/'kernel_probe.cpp','-o',out/'kernel_probe'],out/'kernel-build.log',out)
        env=dict(os.environ,BLOCK_STUDY_MODEL=str(out/'model'));env.pop('U_FUSION_EVENTS',None);env.pop('U_FUSION_TRACE_SHA256',None)
        for script in ('check_kernels.py','validate.py','smoke.py'):
            execute([sys.executable,'-B',frozen/script],out/(script+'.log'),out,env=env)

        def case(item):
            work,prof,variant,dual,enabled=item;trace=inputs/(work+'.trace')
            name='{}-{}-{}-nexp{}'.format(work,prof,'idealdual' if dual else 'shared',int(enabled))
            command=[out/'model',trace,prof,variant,8,1,1,16,int(dual),4,0,int(enabled)]
            text=execute(command,out/(name+'.log'),out)
            rows=[json.loads(line[7:]) for line in text.splitlines() if line.startswith('RESULT ')]
            if len(rows)!=1 or 'MODEL_FAILURE' in text or 'SystemC 3.0.2' not in text:raise ValueError('invalid model case '+name)
            row=rows[0];baseline=lookup(prior,work,prof,variant,dual)
            checked=audit.check(row,baseline,trace,profile,enabled)
            negatives=audit.reject_checks(row,baseline,trace,profile,enabled)
            record=dict(workload=work,profile=prof,variant=variant,contexts=8,P_KiB=16,dual_ports=bool(dual),
                switch_cycles=1,reuse_A=True,P_port_quarters=4,policy_KiB=0,nexp_enabled=bool(enabled),
                result=row,audit=checked,negative_checks=negatives,command=list(map(str,command)),
                speedup_vs_same_layer_run15=baseline['seconds']/row['seconds'],log_sha256=sha(out/(name+'.log')))
            (out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
            print('ROUND1_CASE '+name+' tokens_s='+str(row['tokens_per_second']),flush=True)
            return record
        for enabled in (False,True):
            jobs=[(work,prof,variant,dual,enabled) for work,prof,variant in WORK for dual in (False,True)]
            with ThreadPoolExecutor(max_workers=cpus) as pool:
                for record in pool.map(case,jobs):report['cases'].append(record);save()
            if not enabled:report['baseline_phase_passed']=True;save()

        # Real CLI rejection. A second generated binary proves missing-profile
        # rejection; its default still remains the unmodified scalar service.
        invalid=[]
        for value in ('2','1junk','-1'):
            label='invalid-flag-'+str(len(invalid))
            text=execute([out/'model',inputs/'decode512.trace','queued_pipe_w8','adaptive_prefix_pair_combine',8,1,1,16,0,4,0,value],out/(label+'.log'),out,expected=2)
            if 'RESULT ' in text:raise ValueError('invalid flag produced result')
            invalid.append(value)
        no_profile=out/'no-profile';generate(repo,no_profile)
        execute(['g++',*flags,no_profile/'model.cpp','-I'+str(no_profile),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
                 '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',out/'no-profile-model'],out/'no-profile-build.log',out)
        text=execute([out/'no-profile-model',inputs/'decode512.trace','queued_pipe_w8','adaptive_prefix_pair_combine',8,1,1,16,0,4,0,1],
                     out/'missing-profile.log',out,expected=2)
        if 'RESULT ' in text or 'passed calibrated profile' not in text:raise ValueError('missing-profile refusal absent')
        report['invalid_CLI_rejected']=invalid;report['missing_profile_rejected']=True
        raw=json.loads(calibration.read_text(encoding='utf-8'));negative_profiles=[]
        for label,mutate in [
            ('fee_minus_one',lambda x:x['profile']['rows'][7].__setitem__('charge_cycles',x['profile']['rows'][7]['charge_cycles']-1)),
            ('free_S16_n8',lambda x:x['profile']['rows'][7].__setitem__('subcounts',[8])),
            ('missing_count',lambda x:x['profile']['rows'].pop()),
            ('unpassed_calibration',lambda x:x.__setitem__('passed',False)),
            ('unbound_measurement_log',lambda x:x['measurements']['compute_s32'][0].__setitem__('log_sha256','0'*64)),
            ('unpassed_lifecycle_gate',lambda x:x['gates'].__setitem__('lifecycle',False)),
        ]:
            bad=deepcopy(raw);mutate(bad);target=out/('negative-profile-'+label+'.json');target.write_text(json.dumps(bad),encoding='utf-8')
            try:audit.read_calibration(target)
            except (ValueError,KeyError):negative_profiles.append(label)
            else:raise ValueError('invalid profile accepted '+label)
        report['profile_negative_rejections']=negative_profiles
        main=next(c for c in report['cases'] if c['workload']=='decode512' and c['profile']=='queued_pipe_w8' and c['dual_ports'] and c['nexp_enabled'])
        shared=next(c for c in report['cases'] if c['workload']=='decode512' and c['profile']=='queued_pipe_w8' and not c['dual_ports'] and c['nexp_enabled'])
        report['target_status']=dict(legacy_conditional_target_reached=main['result']['seconds']<=.2,
            ideal_target_tokens_per_second=main['result']['tokens_per_second'],shared_projection_tokens_per_second=shared['result']['tokens_per_second'],
            actual_four_1RW_hardware_5_tokens_s_claimed=False)
        report['passed']=True
    except Exception as error:
        report['error']=repr(error);report['traceback']=traceback.format_exc();raise
    finally:save()
    print('ROUND1_NEXP_PASS16',flush=True)


if __name__=='__main__':main()
