"""Allocated runner: immutable sources, fresh outputs, matched XY-only trials.

Completion of a Tcl command is not a physical pass. Keep stages and raw reports.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,os,json,hashlib,datetime,sys,re,traceback
from run_exports import ROOT,CFG,IMAGE,BIN,sha
DRIVER=Path(__file__).resolve().parent

def config_values(path,seen=None):
    seen=set() if seen is None else seen
    path=Path(path);assert path.exists(),path
    if str(path) in seen:return {}
    seen.add(str(path));values={}
    for line in path.read_text().splitlines():
        line=line.strip()
        if line.startswith('include '):
            values.update(config_values(line.split(None,1)[1],seen))
        m=re.match(r'(?:export\s+)?(\w+)\s*[:?+]?=\s*(.*)',line)
        if m:values[m[1]]=m[2]
    return values

def one(case,plan,revision):
    out=ROOT/'trials'/revision/(case+'-'+plan);out.mkdir(parents=True,exist_ok=False)
    spec=CFG['physical_blocks'][case];src=Path(spec['odb']);before=src.stat();observed=sha(src)
    assert observed==spec['expected_sha256']
    # Source config is at the design run root, six levels above .../base/*.odb.
    source_config=src.parents[5]/('vec-config.mk' if case=='vector' else 'config.mk')
    values=config_values(source_config)
    std='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
    libs=[std]+values.get('ADDITIONAL_LIBS','').split()
    libtcl=out/'libs.tcl';libtcl.write_text(''.join('read_liberty {'+p+'}\n' for p in libs))
    sdc=src.parent/('5_1_grt.sdc' if case.endswith('_aux') else '6_final.sdc')
    assert sdc.exists(),sdc
    inputs=ROOT/'inputs'/os.environ.get('PINXY_INPUT_SET','trial-inputs-r03')
    if plan=='A_replay' and not (inputs/(case+'-'+plan+'.tcl')).exists():
        raise RuntimeError('A_replay needs explicitly frozen A coordinates')
    selected_count=sum(line.startswith('lappend relocations ') for line in (inputs/(case+'-'+plan+'.tcl')).read_text().splitlines())
    receipt={'case':case,'plan':plan,'selected_pin_count':selected_count,'stage_scope':'{} selected pins; all remaining pins stay original; pure XY, no buffering/resizing'.format(selected_count),
       'source_odb':str(src),'source_sha256':observed,'source_config':str(source_config),'source_sdc':str(sdc),'libs':libs,
       'input_sha256':{str(p):sha(p) for p in [src,sdc,source_config,inputs/(case+'-'+plan+'.tcl'),DRIVER/'physical_trial.tcl']+list(map(Path,libs[1:]))},
       'scheduler_job':os.environ['SLURM_JOB_ID'],'allocated_cpus':os.environ['SLURM_CPUS_PER_TASK'],'openroad_threads':4,
       'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
       'parent_handoff_target_layer':'UNKNOWN; this experiment cannot qualify parent access'}
    env='PINXY_OUTPUT={},PINXY_ODB={},PINXY_SDC={},PINXY_LIBS_TCL={},PINXY_RELOCATIONS={},PINXY_PLAN={},PINXY_TOP_LAYER={},PINXY_DRIVER={},PINXY_ACCESS_OUT={},OMP_NUM_THREADS=4'.format(
        out,src,sdc,libtcl,inputs/(case+'-'+plan+'.tcl'),plan,8 if case.endswith('_aux') else 10,DRIVER,out/'access.tsv')
    cmd=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
         '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
         '--home',str(ROOT/'home'),'--pwd',str(out),'--env',env,IMAGE,BIN,'-threads','4','-no_init','-exit',str(DRIVER/'physical_trial.tcl')]
    receipt['command']=cmd
    (out/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n')
    with (out/'openroad.log').open('x') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    receipt['returncode']=result.returncode;receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if (out/'access.tsv').exists():
        from check_access import check
        access=check(out/'access.tsv');(out/'access.json').write_text(json.dumps(access,indent=2)+'\n')
        receipt['selected_access_pass']=access['pass']
    assert observed==sha(src) and before.st_mtime_ns==src.stat().st_mtime_ns,'SOURCE CHANGED'
    receipt['source_unchanged']=True
    receipt['fingerprint_checks']={}
    for suffix in ['cells','pdn','die']:
        p=out/('before.'+suffix+'.tsv');q=out/('after.'+suffix+'.tsv')
        receipt['fingerprint_checks'][suffix]={'before_sha256':sha(p) if p.exists() else None,'after_sha256':sha(q) if q.exists() else None,
            'exact_equal':p.exists() and q.exists() and sha(p)==sha(q)}
    receipt['outputs']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    receipt['status']='STAGES_EXECUTED_NOT_QUALIFIED' if result.returncode==0 else 'ACTUAL_TRIAL_FAILED'
    (out/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('TRIAL_RETURN',case,plan,result.returncode,flush=True)
    return result.returncode==0

def safe(args):
    out=ROOT/'trials'/args[2]/(args[0]+'-'+args[1])
    if out.exists():
        print('REFUSE_EXISTING_TRIAL_DIRECTORY_UNCHANGED',out,flush=True);return False
    try:return one(*args)
    except Exception:
        traceback.print_exc();print('DRIVER_FAILED',args,flush=True)
        out=ROOT/'trials'/args[2]/(args[0]+'-'+args[1]);out.mkdir(parents=True,exist_ok=True)
        with (out/'driver_failure.json').open('x') as f:f.write(json.dumps({'args':args,'traceback':traceback.format_exc(),'status':'DRIVER_FAILED_NOT_PHYSICAL_RESULT'},indent=2)+'\n')
        return False

if __name__=='__main__':
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    gate=json.loads((ROOT/'inputs'/os.environ.get('PINXY_INPUT_SET','trial-inputs-r03')/'coverage_gate.json').read_text());assert gate['status']=='PASS_ALL_BLOCK_CANDIDATE_COVERAGE_ONLY'
    case,revision=sys.argv[1:3]
    with (ROOT/'logs'/('platform-'+case+'-'+revision+'.log')).open('x') as f:
        subprocess.run(['singularity','exec','--cleanenv','--home',str(ROOT/'home'),IMAGE,'sh','-c',
            'command -v klayout; grep -E "MIN_ROUTING_LAYER|MAX_ROUTING_LAYER|MIN_CLK_ROUTING|MAX_CLK_ROUTING" /OpenROAD-flow-scripts/flow/platforms/nangate45/config.mk; cat /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl; ls /OpenROAD-flow-scripts/flow/platforms/nangate45/drc; sha256sum /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules /OpenROAD-flow-scripts/flow/platforms/nangate45/config.mk /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'],stdout=f,stderr=subprocess.STDOUT,check=True)
    # Positional plan list avoids Slurm --export treating embedded commas as
    # separate variable assignments. Existing environment-based inputs remain valid.
    plans=(sys.argv[3] if len(sys.argv)>3 else os.environ.get('PINXY_PLANS','A,A_replay,Aopt,B,C')).split(',')
    assert set(plans)<=set(['A','A_replay','Aopt','B','C'])
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(safe,[(case,p,revision) for p in plans]))
    (ROOT/'trials'/revision/(case+'-batch.json')).write_text(json.dumps({'case':case,'plans':plans,'process_return_success':results,'qualification':'CHECK_INDEPENDENT_STAGE_RESULTS'},indent=2)+'\n')
    sys.exit(0 if all(results) else 1)
