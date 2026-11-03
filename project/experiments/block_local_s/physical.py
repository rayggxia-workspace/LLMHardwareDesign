"""Source-bound local-S P&R, independent gates and 300MHz reception."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[3]
for folder in ('block_v1','block_feed_v1'):
    sys.path.insert(0,str(ROOT/'project/experiments'/folder))
from io_slots import file_sha as sha

FLOW=Path('/OpenROAD-flow-scripts/flow')
LIB=FLOW/'platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
VARIANTS={'p4':(4,True),'n4':(4,False),'n5':(5,False)}
STAGES=['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish']


def dump(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def top_text(variant):
    n,feeder=VARIANTS[variant]
    ports=['input wire clk,reset',f'input wire [{n-1}:0] req_valid,req_write,rsp_ready',
           f'input wire [{n*10-1}:0] req_addr',f'input wire [{n*128-1}:0] req_data',
           f'output wire [{n-1}:0] req_ready,rsp_valid',f'output wire [{n*128-1}:0] rsp_data','output wire busy']
    common=['clk','reset','req_valid','req_write','rsp_ready','req_addr','req_data','req_ready','rsp_valid','rsp_data','busy']
    extra=['load_valid','load_ready','load_bank','load_rows','load_tiles','load_a_wide','load_b_wide','load_reuse_b',
           'load_a_base','load_b_base','done_valid','done_take','done_error','a_valid','a_ready','a_bank','a_row',
           'a_tile','a_wide','a_data','b_valid','b_ready','b_bank','b_tile','b_wide','b_half','b_data']
    if feeder:
        ports+=['input wire load_valid,load_bank,load_a_wide,load_b_wide,load_reuse_b',
                'input wire [3:0] load_rows','input wire [2:0] load_tiles',
                'input wire [9:0] load_a_base,load_b_base','output wire load_ready,done_valid,done_error',
                'input wire done_take,a_ready,b_ready','output wire a_valid,a_bank,a_wide,b_valid,b_bank,b_wide,b_half',
                'output wire [2:0] a_row','output wire [1:0] a_tile,b_tile',
                'output wire [127:0] a_data','output wire [511:0] b_data']
        connections=common+extra
        joined=',\n'.join('.'+p+'('+p+')' for p in connections)
    else:
        inputs={'load_valid':"1'b0",'load_bank':"1'b0",'load_rows':"4'b0",'load_tiles':"3'b0",
                'load_a_wide':"1'b0",'load_b_wide':"1'b0",'load_reuse_b':"1'b0",
                'load_a_base':"10'b0",'load_b_base':"10'b0",'done_take':"1'b0",'a_ready':"1'b0",'b_ready':"1'b0"}
        joined=',\n'.join(['.'+p+'('+p+')' for p in common]+['.'+p+'('+inputs.get(p,'')+')' for p in extra])
    return 'module local_s_'+variant+'(\n'+',\n'.join(ports)+'\n);\n'+f'block_local_s_macro #(.CLIENTS({n}),.WITH_FEEDER({int(feeder)})) impl(\n'+joined+'\n);\nendmodule\n'


def mapping(a,out,run):
    top='local_s_'+a.variant
    sources=[ROOT/'project/rtl/block_feed_v1'/n for n in ('block_feed_s16k.sv','block_feed_loader.sv')]
    sources += [ROOT/'project/rtl/block_local_s'/n for n in ('block_local_s_arbiter.sv','block_local_s_macro.sv')]
    (out/'top.sv').write_text(top_text(a.variant))
    abc=shutil.which('yosys-abc') or str(Path(shutil.which('yosys')).resolve().with_name('yosys-abc'))
    assert Path(abc).is_file(),abc
    batch=out/'abc-batch';batch.write_text('#!/bin/sh\nexec '+shlex.quote(abc)+' "$@"\n');batch.chmod(0o755)
    ys='read_liberty -lib '+str(LIB)+'\nread_verilog -sv '+' '.join(map(str,sources+[out/'top.sv']))+'\n'
    ys+='hierarchy -check -top '+top+'\nproc\nopt\nsynth -top '+top+' -flatten -noabc\n'
    ys+='dfflibmap -liberty '+str(LIB)+'\nabc -exe '+str(batch)+' -liberty '+str(LIB)+'\n'
    ys+='clean\nflatten -noscopeinfo\ndelete t:$scopeinfo\ncheck -assert\nstat -liberty '+str(LIB)+'\n'
    ys+='write_json '+str(out/'mapped.json')+'\nwrite_verilog -noattr -noexpr -norename '+str(out/'mapped.v')+'\n'
    (out/'map.ys').write_text(ys);run(['yosys','-s',out/'map.ys'],'map.log')
    data=json.loads((out/'mapped.json').read_text())['modules'][top]
    counts=collections.Counter(c['type'] for c in data['cells'].values())
    assert not any(t.startswith('$') for t in counts)
    result=dict(passed=True,mapped=True,top=top,variant=a.variant,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},generated_top_sha256=sha(out/'top.sv'),
        liberty_sha256=sha(LIB),abc=dict(path=abc,sha256=sha(abc)),cell_counts=dict(counts),
        ports={k:dict(direction=v['direction'],bits=len(v['bits'])) for k,v in data['ports'].items()},
        reused_artifacts=dict(scope='Fresh mapping; no inherited physical database',artifacts={str(out/n):sha(out/n) for n in ('mapped.json','mapped.v')}))
    dump(out/'receipt.json',result)


def prepare(a,out,run):
    import importlib.util
    name='local_s_shared_physical'
    spec=importlib.util.spec_from_file_location(name,ROOT/'project/experiments/block_v2/physical.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    options=SimpleNamespace(out=out,top='local_s_'+a.variant,mapping=a.mapping,
        input_receivers=True,remove_abc_buffers=False,placement_mode='geometric',fanout_mode='partition',
        refine_partition_placement=False,placement_hold_margin=None,r_compact_floorplan=False,
        r_strong_clock=False,hold_repair_margin=.02,prepare_only=True)
    module.implement(options,run)
    flow=json.loads((out/'native-flow.json').read_text())
    assert flow['stages']==[] and not flow['passed'] and flow['prepared_only']


def stage(a,out,run):
    work=a.physical.resolve();top='local_s_'+a.variant
    flow=json.loads((work/'native-flow.json').read_text())
    i=STAGES.index(a.stage)
    assert flow['top']==top and flow['stages']==STAGES[:i]
    before=sha(work/'input.v')
    run(['make','-C',FLOW,'DESIGN_CONFIG='+str(work/'config.mk'),'WORK_HOME='+str(work/'flow'),
         'NUM_CORES=16',a.stage],a.stage+'.log')
    assert sha(work/'input.v')==before
    shutil.copyfile(out/(a.stage+'.log'),work/('%02d-%s.log'%(i,a.stage)))
    flow['stages'].append(a.stage)
    flow.setdefault('stage_receipts',[]).append(dict(job=os.environ['SLURM_JOB_ID'],stage=a.stage,log=str(out/(a.stage+'.log')),sha256=sha(out/(a.stage+'.log'))))
    if i==5:
        results=work/'flow/results/nangate45'/('bv1_'+top)/'base'
        flow['final_files']={}
        for suffix in ('v','sdc','def','odb','spef'):
            p=results/('6_final.'+suffix);assert p.is_file()
            flow['final_files'][p.name]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
        flow.update(passed=True,pipeline_completed=True,prepared_only=False)
        inputs={str(p.relative_to(work)):sha(p) for p in work.rglob('*') if p.is_file() and p.name not in ('receipt.json','native-flow.json')}
        dump(work/'native-flow.json',flow);inputs['native-flow.json']=sha(work/'native-flow.json')
        dump(work/'receipt.json',dict(passed=True,outputs=inputs,scope='Completed all six native stages; independent gates remain'))
    else:dump(work/'native-flow.json',flow)


def seal(a,out,run):
    from qualify import seal as receive
    receive(a.physical,out)
    dump(out/'receipt.json',dict(passed=True,source=str(a.physical),
        outputs={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name not in ('receipt.json','run.json')}))


def physical(a,out,run):
    from qualify import source
    from receive import physical as receive
    receive(ROOT,out,16,run,'s',selected=lambda target,kind:source(a.sealed))


def drc(a,out,run):
    from qualify import source
    from native_drc import summarize
    folder,r,flow,results=source(a.sealed)
    before=sha(results/'6_final.odb')
    text='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nwrite_def before.def\n'
    text+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 local_s_native\nwrite_def after.def\n'
    (out/'native.tcl').write_text(text);run(['openroad','-no_init','-exit',out/'native.tcl'],'native.log')
    assert sha(out/'before.def')==sha(out/'after.def') and sha(results/'6_final.odb')==before
    native=(out/'native-whole-drc.rpt').read_text()
    assert not native.strip(),'Actual final whole-chip native DRC failed'
    nickname='bv1_'+flow['top']
    for category in ('results','reports','logs','objects'):(out/'gds-flow'/category/'nangate45'/nickname/'base').mkdir(parents=True)
    target=out/'gds-flow/results/nangate45'/nickname/'base'
    shutil.copyfile(results/'6_final.def',target/'6_final.def')
    run(['make','-C',FLOW,'DESIGN_CONFIG='+str(folder/'config.mk'),'WORK_HOME='+str(out/'gds-flow'),'NUM_CORES=16','do-gds'],'gds.log')
    deck=FLOW/'platforms/nangate45/drc/FreePDK45.lydrc';gds=target/'6_final.gds'
    run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(out/'full-deck.lyrdb'),'-r',deck],'full-deck.log')
    report=summarize(out/'full-deck.lyrdb')
    result=dict(passed=report['total_items']==0,top=flow['top'],source_receipt_sha256=sha(folder/'receipt.json'),
        native_report=native,full_deck=report,deck_sha256=sha(deck),gds=dict(path=str(gds),sha256=sha(gds),bytes=gds.stat().st_size))
    dump(out/'five-macro-drc.json',result);assert result['passed']


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['map','prepare','stage','seal','physical','drc'],required=True)
    p.add_argument('--variant',choices=list(VARIANTS),required=True)
    for name in ('out','mapping','physical','sealed'):p.add_argument('--'+name,type=Path,required=name=='out')
    p.add_argument('--stage',choices=STAGES)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    manifest=json.loads((ROOT/'source-snapshot.json').read_text())
    for name,value in manifest['files'].items():assert sha(ROOT/name)==value,name
    receipt=dict(passed=False,mode=a.mode,variant=a.variant,source_commit=manifest['source_commit'],
        source_manifest_sha256=sha(ROOT/'source-snapshot.json'),job=os.environ['SLURM_JOB_ID'],host=os.uname().nodename,
        cpu_affinity=sorted(os.sched_getaffinity(0)),start=time.time(),commands=[])
    def run(cmd,log):
        cmd=list(map(str,cmd));started=time.time()
        with (a.out/log).open('w') as f:q=subprocess.run(cmd,cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(argv=cmd,log=log,sha256=sha(a.out/log),exit=q.returncode,seconds=time.time()-started))
        dump(a.out/'run.json',receipt)
        if q.returncode:raise RuntimeError(log+' failed: '+str(q.returncode))
    try:
        {'map':mapping,'prepare':prepare,'stage':stage,'seal':seal,'physical':physical,'drc':drc}[a.mode](a,a.out,run)
        receipt['passed']=True
    except Exception as e:
        receipt['error']=repr(e);raise
    finally:
        receipt['end']=time.time();receipt['source_unchanged']=all(sha(ROOT/n)==h for n,h in manifest['files'].items())
        dump(a.out/'run.json',receipt)


if __name__=='__main__':main()
