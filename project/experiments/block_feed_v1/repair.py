"""Prefabrication input-receiver repair from this task's exact CTS checkpoint.

Only the first four completed native stages are reused. Route/finish, RCX and
all final gates must run again; no failed-route qualification is transferred.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/block_v1'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from io_slots import file_sha as sha


def repair(a,run):
    raw=a.source;out=a.out
    snapshot=(raw/'native-flow.json').read_bytes()
    journal=json.loads(snapshot);assert journal['stages'][:4]==['do-1_synth','do-floorplan','do-place','do-cts']
    top=journal['top'];assert top in ['block_feed_m','block_feed_s_macro']
    if a.from_grt:
        (out/'source-grt-journal.json').write_bytes(snapshot)
        return repair_grt(a,run,journal)
    (out/'source-cts-journal.json').write_bytes(snapshot)
    for p,digest in journal['rtl_sha256'].items():assert sha(ROOT/p)==digest
    assert sha(raw/'config.mk')==journal['config_sha256'] and sha(raw/'pins.json')==journal['pins_sha256']
    # Bind actual successful make-stage logs, not merely file existence.
    earlier={}
    for i,stage in enumerate(journal['stages'][:4]):
        log=raw/('%02d-%s.log'%(i,stage));text=log.read_text()
        assert "make: Leaving directory '/OpenROAD-flow-scripts/flow'" in text and 'Error ' not in text
        earlier[log.name]=sha(log)
        shutil.copyfile(log,out/('source-'+log.name))
    relative='flow/results/nangate45/bv1_'+top+'/base';before=raw/relative;after=out/relative;after.mkdir(parents=True)
    copied={}
    for name in ['4_cts.odb','4_cts.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc']:
        p=before/name;digest=sha(p);shutil.copyfile(p,after/name);assert sha(after/name)==digest
        copied[name]=dict(path=str(p),sha256=digest)
    for name in ['pins.json','pins.tcl','input.sdc','input.v']:
        shutil.copyfile(raw/name,out/name)
    receivers=ROOT/'project/experiments/block_feed_v1/input_receivers.tcl'
    hook=receivers.read_text()+'\n'+(raw/'input-diodes.tcl').read_text()
    (out/'input-diodes.tcl').write_text(hook)
    config=(raw/'config.mk').read_text()
    for name in ['input.v','input.sdc','pins.tcl','input-diodes.tcl']:
        assert config.count(str(raw/name))==1
        config=config.replace(str(raw/name),str(out/name))
    (out/'config.mk').write_text(config)
    result=copy.deepcopy(journal)
    result.update(passed=False,pipeline_completed=False,final_files={},source_cts_stage_log_sha256=earlier,
        source_cts_files=copied,source_native_journal_sha256=sha(out/'source-cts-journal.json'),source_native_folder=str(raw),
        inherited_physical_stages=journal['stages'][:4],fresh_physical_stages=[],stages=journal['stages'][:4],
        config_sha256=sha(out/'config.mk'),fixed_input_receiver_hook_sha256=sha(receivers),
        repair='BUF_X8 receiver at every used nonclock input, charged to fixed M1-M10; native timing/load/rule contract unchanged',qualified_hard_macro=False)
    def save():(out/'native-flow.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    wanted=dict(journal['actual_variables'],PRE_GLOBAL_ROUTE_TCL=str(out/'input-diodes.tcl'))
    for key,value in wanted.items():
        log='variable-'+key+'.log';run(cmd+['print-'+key],log)
        actual=re.search(r'(?m)^'+key+r': (.+)$',(out/log).read_text()).group(1).strip();assert actual==value
    for i,stage in enumerate(['do-route','do-finish'],4):
        run(cmd+[stage],'%02d-%s.log'%(i,stage));result['stages'].append(stage);result['fresh_physical_stages'].append(stage);save()
    for suffix in ['v','sdc','def','odb','spef']:
        p=after/('6_final.'+suffix);assert p.is_file()
        result['final_files'][p.name]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
    assert all(sha(Path(row['path']))==row['sha256'] for row in copied.values())
    result.update(passed=True,pipeline_completed=True);save()


def repair_grt(a,run,journal):
    raw=a.source;out=a.out;top=journal['top']
    receipt=json.loads((raw/'receipt.json').read_text())
    assert sha(raw/'native-flow.json')==receipt['outputs']['native-flow.json']
    for p,digest in journal['rtl_sha256'].items():assert sha(ROOT/p)==digest
    for name,key in [('config.mk','config_sha256'),('pins.json','pins_sha256')]:assert sha(raw/name)==journal[key]==receipt['outputs'][name]
    # A plain full-flow S checkpoint has no inherited CTS metadata yet. Bind
    # its actual completed first four commands/files before reusing its GRT.
    # A producer's failed route never grants any final qualification.
    provenance={}
    if not journal.get('inherited_physical_stages'):
        expected=['do-1_synth','do-floorplan','do-place','do-cts']
        assert journal['stages'][:4]==expected
        logs={}
        for i,stage in enumerate(expected):
            name='%02d-%s.log'%(i,stage)
            commands=[c for c in receipt['commands'] if c['log']==name]
            assert len(commands)==1 and commands[0]['returncode']==0
            assert sha(raw/name)==receipt['outputs'][name]==commands[0]['sha256']
            logs[name]=receipt['outputs'][name]
        cts={}
        location=raw/('flow/results/nangate45/bv1_'+top+'/base')
        for name in ['4_cts.odb','4_cts.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc']:
            f=location/name;digest=sha(f)
            assert digest==receipt['outputs'][str(f.relative_to(raw))]
            cts[name]=dict(path=str(f),sha256=digest)
        provenance=dict(inherited_physical_stages=expected,source_native_folder=str(raw),
                        source_cts_stage_log_sha256=logs,source_cts_files=cts,
                        source_native_journal_sha256=sha(raw/'native-flow.json'))
    relative='flow/results/nangate45/bv1_'+top+'/base';before=raw/relative;after=out/relative;after.mkdir(parents=True)
    copied={}
    checkpoint_files=['5_1_grt.odb','5_1_grt.sdc','route.guide','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc','bv1-input-diodes.tsv','feed-input-receivers.tsv']
    if journal.get('fanout_mode')=='partition':checkpoint_files.append('feed-partition-fanout.tsv')
    for name in checkpoint_files:
        f=before/name;digest=sha(f);assert digest==receipt['outputs'][str(f.relative_to(raw))]
        shutil.copyfile(f,after/name);copied[name]=dict(path=str(f),sha256=digest)
    config_files=['pins.json','pins.tcl','input.sdc','input.v','input-diodes.tcl']
    if journal.get('fanout_mode')=='partition':config_files.append('partition-fanout.tcl')
    for name in config_files:
        assert sha(raw/name)==receipt['outputs'][name];shutil.copyfile(raw/name,out/name)
    config=(raw/'config.mk').read_text()
    for name in config_files:config=config.replace(str(raw/name),str(out/name))
    hook=out/'electrical-closure.tcl';shutil.copyfile(ROOT/'project/experiments/block_feed_v1'/a.closure_hook,hook)
    if a.closure_hook in ('measured_m_buffer.tcl','measured_m_hold.tcl'):
        shutil.copyfile(ROOT/'project/experiments/block_feed_v1/measured_m_driver.tcl',out/'measured-driver.tcl')
    assert 'PRE_DETAIL_ROUTE_TCL' not in config
    config+='\nexport PRE_DETAIL_ROUTE_TCL = '+str(hook)+'\n';(out/'config.mk').write_text(config)
    result=copy.deepcopy(journal)
    result.update(provenance)
    result.update(passed=False,pipeline_completed=False,final_files={},stages=journal['stages'][:4],fresh_physical_stages=[],
        config_sha256=sha(out/'config.mk'),source_grt_checkpoint=dict(folder=str(raw),receipt_sha256=sha(raw/'receipt.json'),
            producer_passed=receipt['passed'],files=copied,journal_name='native-flow.json',
            journal_sha256=sha(raw/'native-flow.json')),electrical_closure_hook_sha256=sha(hook))
    wanted={k:(v.replace(str(raw)+'/',str(out)+'/') if isinstance(v,str) else v) for k,v in journal['actual_variables'].items()}
    wanted.update(PRE_GLOBAL_ROUTE_TCL=str(out/'input-diodes.tcl'),PRE_DETAIL_ROUTE_TCL=str(hook))
    result['actual_variables']=wanted
    def save():(out/'native-flow.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    for key,value in wanted.items():
        log='variable-'+key+'.log';run(cmd+['print-'+key],log)
        actual=re.search(r'(?m)^'+key+r': (.+)$',(out/log).read_text()).group(1).strip();assert actual==value
    for stage in ['do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-finish']:
        run(cmd+[stage],stage+'.log');result['fresh_physical_stages'].append(stage);save()
    result['stages']+=['do-route','do-finish']
    for suffix in ['v','sdc','def','odb','spef']:
        p=after/('6_final.'+suffix);assert p.is_file();result['final_files'][p.name]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
    assert all(sha(Path(row['path']))==row['sha256'] for row in copied.values())
    result.update(passed=True,pipeline_completed=True);save()


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--from-grt',action='store_true')
    p.add_argument('--closure-hook',choices=['electrical_closure.tcl','measured_m_buffer.tcl','measured_m_hold.tcl','measured_s_hold.tcl','inspect_s_grt.tcl'],default='electrical_closure.tcl')
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,source=str(a.source),affinity=sorted(os.sched_getaffinity(0)),commands=[],inputs={})
    for d in ['project/experiments/block_feed_v1','project/experiments/block_v1','project/rtl/block_feed_v1']:
        for f in (ROOT/d).rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts:receipt['inputs'][str(f.relative_to(ROOT))]=sha(f)
    def run(cmd,log):
        cmd=list(map(str,cmd));started=time.time()
        with (a.out/log).open('w') as stream:q=subprocess.run(cmd,cwd=a.out,stdout=stream,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=cmd,log=log,sha256=sha(a.out/log),returncode=q.returncode,seconds=time.time()-started))
        assert q.returncode==0,(log,q.returncode)
    try:repair(a,run);receipt['passed']=True
    finally:
        receipt['outputs']={str(f.relative_to(a.out)):sha(f) for f in a.out.rglob('*') if f.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
