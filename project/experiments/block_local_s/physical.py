"""Source-bound local-S P&R, independent gates and 300MHz reception."""
import argparse
import collections
import concurrent.futures
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
        input_receivers=True,remove_abc_buffers=True,placement_mode='geometric',fanout_mode='partition',
        refine_partition_placement=False,placement_hold_margin=0.0,r_compact_floorplan=False,
        r_strong_clock=False,hold_repair_margin=.005,prepare_only=True)
    module.implement(options,run)
    flow=json.loads((out/'native-flow.json').read_text())
    assert flow['stages']==[] and not flow['passed'] and flow['prepared_only']


def resume(a,out,run):
    """Copy a verified completed placement; never inherit failed CTS outputs."""
    prior=a.physical.resolve();flow=json.loads((prior/'native-flow.json').read_text())
    assert flow['top']=='local_s_'+a.variant and flow['stages']==STAGES[:3]
    assert not flow['passed'] and not flow.get('inherited_physical_stages')
    for name,digest in flow['rtl_sha256'].items():assert sha(ROOT/name)==digest
    snapshot=out/'placement-source';snapshot.mkdir()
    journal=prior/'native-flow.json';journal_sha=sha(journal)
    shutil.copyfile(journal,snapshot/journal.name)
    commands=[];logs={};jobs=[]
    for i,item in enumerate(flow['stage_receipts']):
        assert item['stage']==STAGES[i]
        log=Path(item['log']);receipt=log.parent/'run.json'
        bound=json.loads(receipt.read_text())
        assert bound['passed'] and bound['source_unchanged'] and bound['job']==item['job']
        assert sha(log)==item['sha256']==bound['outputs'][log.name]
        actual=[c for c in bound['commands'] if c['log']==log.name]
        assert len(actual)==1 and actual[0]['exit']==0
        name='%02d-%s.log'%(i,item['stage'])
        assert sha(prior/name)==sha(log)
        shutil.copyfile(log,snapshot/name);shutil.copyfile(log,out/name)
        saved=snapshot/('stage-%d-run.json'%i);shutil.copyfile(receipt,saved)
        commands.append(dict(log=name,returncode=actual[0]['exit'],original_argv=actual[0]['argv'],
                             original_stage_receipt=str(receipt),original_stage_receipt_sha256=sha(receipt)))
        logs[name]=sha(log);jobs.append(bound['job'])
    assert len(commands)==3
    config_files=['config.mk','pins.json','pins.tcl','input.sdc','input.v','input-diodes.tcl','partition-fanout.tcl']
    for name in config_files:
        shutil.copyfile(prior/name,snapshot/name);shutil.copyfile(prior/name,out/name)
    assert sha(prior/'config.mk')==flow['config_sha256'] and sha(prior/'pins.json')==flow['pins_sha256']
    relative='flow/results/nangate45/bv1_'+flow['top']+'/base'
    source=prior/relative;target=out/relative;target.mkdir(parents=True)
    frozen=snapshot/relative;frozen.mkdir(parents=True)
    copied={}
    for path in source.iterdir():
        if path.is_file() and path.name.startswith(('1_','2_','3_')):
            digest=sha(path);shutil.copyfile(path,target/path.name);shutil.copyfile(path,frozen/path.name)
            assert sha(target/path.name)==sha(frozen/path.name)==digest
            copied[path.name]=dict(path=str(frozen/path.name),sha256=digest)
    assert {'3_place.odb','3_place.sdc','1_synth_lec.v'}<=set(copied)
    assert sha(journal)==journal_sha
    outputs={str(p.relative_to(snapshot)):sha(p) for p in snapshot.rglob('*') if p.is_file()}
    dump(snapshot/'receipt.json',dict(passed=False,commands=commands,outputs=outputs,
        source=str(prior),source_journal_sha256=journal_sha,completed_stage_jobs=jobs,
        scope='Adapter over three actual successful stage receipts; original physical run failed CTS. No CTS/route/final qualification.'))
    config=(out/'config.mk').read_text().replace(str(prior),str(out))
    assert config.count('export HOLD_SLACK_MARGIN = 0.020')==1
    config=config.replace('export HOLD_SLACK_MARGIN = 0.020','export HOLD_SLACK_MARGIN = 0.005')
    (out/'config.mk').write_text(config)
    flow.update(passed=False,pipeline_completed=False,prepared_only=False,final_files={},
        inherited_physical_stages=STAGES[:3],source_native_folder=str(snapshot),
        source_cts_stage_log_sha256=logs,source_cts_files=copied,
        config_sha256=sha(out/'config.mk'),hold_repair_margin_ns=.005,
        resume_scope='Only completed synthesis/floorplan/placement reused; fresh CTS, route, finish and all final gates',
        placement_checkpoint_receipt_sha256=sha(snapshot/'receipt.json'))
    flow['actual_variables']['HOLD_SLACK_MARGIN']='0.005'
    flow['actual_variables']['PRE_RESIZE_TCL']=str(out/'partition-fanout.tcl')
    command=['make','-C',FLOW,'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    import re
    for key in ('HOLD_SLACK_MARGIN','LEC_CHECK','SEC_CHECK','PRE_RESIZE_TCL'):
        name='variable-'+key+'.log';run(command+['print-'+key],name)
        actual=re.search(r'(?m)^'+key+r': (.+)$',(out/name).read_text()).group(1).strip()
        assert actual==flow['actual_variables'][key]
    dump(out/'native-flow.json',flow)


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
    f=out/'final-source.json';flow=json.loads(f.read_text())
    if flow.get('placement_checkpoint_receipt_sha256'):
        assert sha(Path(flow['source_native_folder'])/'receipt.json')==flow['placement_checkpoint_receipt_sha256']
        flow['completed_cts_provenance']['scope']='Only three explicitly successful placed stages inherited; failed source CTS not accepted'
        dump(f,flow)
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


def function(a,out,run):
    from qualify import source
    from native_signal_view import export
    folder,r,flow,results=source(a.sealed);top=flow['top']
    netlist,view=export(ROOT,out,run,folder,r,results,top,LIB)
    (out/'cells.ys').write_text('read_liberty -ignore_miss_func -ignore_miss_dir '+str(LIB)+'\nwrite_verilog -noattr '+str(out/'cells.v')+'\n')
    run(['yosys','-s',out/'cells.ys'],'cells.log')
    clients,feeder=VARIANTS[a.variant]
    compiler='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
    bench=ROOT/'project/experiments/block_local_s/test_physical.cpp'
    run([compiler,'--cc','--exe','--build','-j','16','-Wno-fatal','--assert',
         '--top-module',top,'--prefix','Vlocal_s_physical','--Mdir',out/'obj',
         '--output-split','12000','--output-split-cfuncs','150','--output-groups','0','--threads','4',
         '--x-initial','unique','--x-assign','unique','-CFLAGS',f'-std=c++17 -O1 -DCLIENT_COUNT={clients} -DWITH_FEEDER={int(feeder)}',
         netlist,out/'cells.v',bench],'build.log')
    exe=out/'obj/Vlocal_s_physical'
    def one(mode):
        name=f'init-{mode}.log'
        run([exe,f'+verilator+rand+reset+{mode}',f'+verilator+seed+{177+mode}'],name)
        rows=[]
        for line in (out/name).read_text().splitlines():
            try:v=json.loads(line)
            except ValueError:continue
            if isinstance(v,dict):rows.append(v)
        assert len(rows)==1 and rows[0]['passed'] and rows[0]['checks']>0
        return dict(mode=mode,seed=177+mode,result=rows[0],log=name,sha256=sha(out/name))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:runs=list(pool.map(one,(0,1,2)))
    assert all(row['result']==runs[0]['result'] for row in runs)
    dump(out/'final-function.json',dict(passed=True,top=top,variant=a.variant,source_receipt_sha256=sha(folder/'receipt.json'),
        full_final_netlist=view,bench_sha256=sha(bench),cell_models_sha256=sha(out/'cells.v'),
        executable_sha256=sha(exe),initial_runs=runs,checks=sum(row['result']['checks'] for row in runs),
        scope='Actual final ODB full signal netlist, retained protection cells, three actual initial states; STA covers delays separately'))


def formal(a,out,run):
    from qualify import source
    from native_logic_projection import export
    from native_formal import fixture,inspect
    from native_projection_control import verify
    folder,r,flow,results=source(a.sealed);top=flow['top']
    functional=a.gates/'function'
    fr=json.loads((functional/'run.json').read_text());assert fr['passed']
    fn=json.loads((functional/'final-function.json').read_text())
    assert fn['passed'] and fn['source_receipt_sha256']==sha(folder/'receipt.json')
    assert sha(functional/'final-function.json')==fr['outputs']['final-function.json']
    actual=Path(fn['full_final_netlist']['full_view'])
    assert sha(actual)==fn['full_final_netlist']['full_view_sha256']
    controls=out/'controls';controls.mkdir()
    (controls/'lec').mkdir();fixture(ROOT,controls/'lec',run)
    for polarity in (0,1):
        target=controls/str(polarity);target.mkdir()
        verify(ROOT,target,1,lambda cmd,log:run(cmd,f'projection-{polarity}-'+log),polarity)
    before,bp=export(ROOT,out,run,results/'1_synth_lec.v',LIB,top,'before',constant_functions=True)
    after,ap=export(ROOT,out,run,actual,LIB,top,'after',constant_functions=True)
    config='format: verilog\ninput_paths:\n  - '+str(before)+'\n  - '+str(after)+'\nliberty_files:\n - '+str(LIB)+'\nlog_file: '+str(out/'kepler.log')+'\n'
    (out/'kepler.yml').write_text(config)
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    run([binary,'--config',out/'kepler.yml'],'formal.log')
    proof=inspect((out/'kepler.log').read_text())
    dump(out/'formal.json',dict(passed=proof['passed'],top=top,strict_native_lec=proof,
        source_receipt_sha256=sha(folder/'receipt.json'),function_receipt_sha256=sha(functional/'run.json'),
        before=bp,after=ap,binary_sha256=sha(binary),log_sha256=sha(out/'kepler.log')))
    assert proof['passed']


def deliver(a,out,run):
    from qualify import source
    folder,r,flow,results=source(a.sealed)
    names={'physical':'five-macro-physical.json','drc':'five-macro-drc.json','function':'final-function.json','formal':'formal.json'}
    proofs={};receipts={}
    for mode,name in names.items():
        parent=a.gates/mode;receipt=json.loads((parent/'run.json').read_text())
        assert receipt['passed'] and receipt['source_unchanged']
        assert sha(parent/name)==receipt['outputs'][name]
        proof=json.loads((parent/name).read_text())
        assert proof['passed'] and proof['source_receipt_sha256']==sha(folder/'receipt.json')
        proofs[mode]=proof
        receipts[mode]=dict(path=str(parent/'run.json'),sha256=sha(parent/'run.json'),report_path=str(parent/name),report_sha256=sha(parent/name))
    assert all(proofs['physical']['checks'].values())
    assert proofs['drc']['full_deck']['total_items']==0 and not proofs['drc']['native_report'].strip()
    assert all(proofs['formal']['strict_native_lec']['checks'].values())
    assert proofs['formal']['function_receipt_sha256']==receipts['function']['sha256']
    gds=Path(proofs['drc']['gds']['path']);assert sha(gds)==proofs['drc']['gds']['sha256']
    files={}
    for src in [results/('6_final.'+ext) for ext in ('v','sdc','def','odb','spef')]+[gds]:
        dst=out/src.name;shutil.copyfile(src,dst);assert sha(dst)==sha(src)
        files[dst.name]=dict(path=str(dst),bytes=dst.stat().st_size,sha256=sha(dst))
    render='import pya\nv=pya.LayoutView()\nv.load_layout('+repr(str(out/'6_final.gds'))+',0)\nv.max_hier()\nv.add_missing_layers()\nv.zoom_fit()\nv.save_image('+repr(str(out/'layout.png'))+',1600,1600)\n'
    (out/'render.py').write_text(render)
    run(['env','QT_QPA_PLATFORM=offscreen','klayout','-z','-r',out/'render.py'],'render.log')
    assert (out/'layout.png').stat().st_size>1000
    dump(out/'delivery.json',dict(passed=True,native_leaf_accepted=True,variant=a.variant,top=flow['top'],
        source_receipt_sha256=sha(folder/'receipt.json'),gate_receipts=receipts,final_files=files,
        die_um=flow['die_um'],active_area_um2=proofs['physical']['active_area_um2'],
        timing=proofs['physical']['timing']['timed_endpoints'],
        image=dict(path=str(out/'layout.png'),sha256=sha(out/'layout.png')),
        scope='Actual native M1-M10 TT300MHz leaf acceptance; not hierarchical Liberty, M11/M12 system or foundry signoff'))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['map','prepare','resume','stage','seal','physical','drc','function','formal','deliver'],required=True)
    p.add_argument('--variant',choices=list(VARIANTS),required=True)
    for name in ('out','mapping','physical','sealed','gates'):p.add_argument('--'+name,type=Path,required=name=='out')
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
        {'map':mapping,'prepare':prepare,'resume':resume,'stage':stage,'seal':seal,'physical':physical,'drc':drc,'function':function,'formal':formal,'deliver':deliver}[a.mode](a,a.out,run)
        receipt['passed']=True
    except Exception as e:
        receipt['error']=repr(e);raise
    finally:
        receipt['end']=time.time();receipt['source_unchanged']=all(sha(ROOT/n)==h for n,h in manifest['files'].items())
        receipt['outputs']={p.name:sha(p) for p in a.out.iterdir() if p.is_file() and p.name!='run.json'}
        dump(a.out/'run.json',receipt)


if __name__=='__main__':main()
