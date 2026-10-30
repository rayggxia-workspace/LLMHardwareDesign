"""Issue143 exact-final qualification; physical source receipt and all gates mandatory."""
import argparse
import concurrent.futures
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
sys.path.insert(0,str(ROOT/'project/experiments/block_feed_v1'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from io_slots import file_sha as sha

LIB=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')


def source(folder):
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['passed']
    f=folder/'final-source.json';assert sha(f)==receipt['outputs'][f.name]
    flow=json.loads(f.read_text());assert flow['passed'] and flow['pipeline_completed']
    for path,digest in flow['rtl_sha256'].items():assert sha(ROOT/path)==digest
    results=folder/'flow/results/nangate45'/('bv1_'+flow['top'])/'base'
    for path,row in flow['final_files'].items():
        assert sha(results/path)==row['sha256']==receipt['outputs'][str((results/path).relative_to(folder))]
    for path,key in [('config.mk','config_sha256'),('pins.json','pins_sha256')]:
        assert sha(folder/path)==flow[key]==receipt['outputs'][path]
    for path in ['pins.tcl','input.sdc']:
        assert sha(folder/path)==receipt['outputs'][path]
    for name in ['1_synth_lec.v','bv1-input-diodes.tsv']:
        assert sha(results/name)==receipt['outputs'][str((results/name).relative_to(folder))]
    if flow.get('repair'):
        f=results/'feed-input-receivers.tsv';assert sha(f)==receipt['outputs'][str(f.relative_to(folder))]
    if flow.get('fanout_mode')=='partition':
        for f in (folder/'partition-fanout.tcl',results/'feed-partition-fanout.tsv'):
            assert sha(f)==receipt['outputs'][str(f.relative_to(folder))]
    return folder,receipt,flow,results


def seal(raw,out):
    from constraint_readback import audit
    from constraints import generate
    receipt=json.loads((raw/'receipt.json').read_text());assert receipt['passed']
    f=raw/'native-flow.json';assert sha(f)==receipt['outputs'][f.name]
    flow=json.loads(f.read_text());assert flow['passed'] and flow['pipeline_completed']
    assert flow['stages']==['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish']
    if flow.get('inherited_physical_stages'):
        # A deliberately failed route can still supply its earlier completed
        # CTS, but never transfer any route/final success or acceptance.
        original=Path(flow['source_native_folder'])
        producer=json.loads((original/'receipt.json').read_text())
        binding={}
        for i,stage in enumerate(flow['inherited_physical_stages']):
            name='%02d-%s.log'%(i,stage)
            assert sha(original/name)==flow['source_cts_stage_log_sha256'][name]==producer['outputs'][name]
            commands=[c for c in producer['commands'] if c['log']==name]
            assert len(commands)==1 and commands[0]['returncode']==0
            binding[name]=producer['outputs'][name]
        for name,row in flow['source_cts_files'].items():
            assert sha(row['path'])==row['sha256']==producer['outputs'][str(Path(row['path']).relative_to(original))]
        flow['completed_cts_provenance']=dict(producer_receipt_sha256=sha(original/'receipt.json'),
            producer_passed=producer['passed'],successful_stage_logs=binding,
            scope='Only explicit successful first-four-stage checkpoints; failed original route is not accepted')
    if flow.get('source_grt_checkpoint'):
        checkpoint=flow['source_grt_checkpoint'];prior=Path(checkpoint['folder'])
        r=json.loads((prior/'receipt.json').read_text());assert sha(prior/'receipt.json')==checkpoint['receipt_sha256']
        for name,row in checkpoint['files'].items():
            p=Path(row['path']);assert sha(p)==row['sha256']==r['outputs'][str(p.relative_to(prior))]
        name=checkpoint.get('journal_name','source-cts-journal.json')
        assert name in ('source-cts-journal.json','native-flow.json')
        journal=prior/name
        expected=checkpoint.get('journal_sha256',flow['source_native_journal_sha256'])
        assert sha(journal)==expected==r['outputs'][journal.name]
        if name=='native-flow.json':
            producer=json.loads(journal.read_text())
            assert producer['top']==flow['top'] and producer['rtl_sha256']==flow['rtl_sha256']
    if flow.get('postroute_repair'):
        proof=raw/'route-repair-proof.json'
        assert sha(proof)==flow['postroute_repair']['proof_sha256']==receipt['outputs'][proof.name]
        repaired=json.loads(proof.read_text())
        assert repaired['passed'] and repaired['native_whole_drc_zero']
        assert repaired['identical_non_target_geometry'] and repaired['identical_target_terminal_connections']
        assert sha(Path(repaired['source'])/'receipt.json')==repaired['source_receipt_sha256']
        for row in repaired['source_files'].values():assert sha(row['path'])==row['sha256']
        shutil.copyfile(proof,out/proof.name)
    relative='flow/results/nangate45/bv1_'+flow['top']+'/base'
    before=raw/relative;after=out/relative;after.mkdir(parents=True)
    config_files=['config.mk','pins.json','pins.tcl','input.sdc']
    if flow.get('fanout_mode')=='partition':config_files.append('partition-fanout.tcl')
    for name in config_files:
        assert sha(raw/name)==receipt['outputs'][name];shutil.copyfile(raw/name,out/name)
    budget=flow['budget'];approved=re.sub(r'create_clock -name core -period [^ ]+',
        'create_clock -name core -period %.12g'%budget['clock_ns'],generate(budget))
    assert (out/'input.sdc').read_text()==approved
    original=(before/'6_final.sdc').read_text()
    flow['original_flow_boundary']=audit(original,json.loads((out/'pins.json').read_text())['pins'],dict(budget,clock_ns=3.3333))
    bound={}
    names=['6_final.v','6_final.sdc','6_final.odb','6_final.def','6_final.spef','1_synth_lec.v','bv1-input-diodes.tsv']
    if flow.get('repair'):names.append('feed-input-receivers.tsv')
    if flow.get('fanout_mode')=='partition':names.append('feed-partition-fanout.tsv')
    for name in names:
        p=before/name;assert sha(p)==receipt['outputs'][str(p.relative_to(raw))]
        if name in flow['final_files']:assert sha(p)==flow['final_files'][name]['sha256']
        bound[name]=sha(p);shutil.copyfile(p,after/name)
    (out/'original-flow-final.sdc').write_text(original);(after/'6_final.sdc').write_text(approved)
    flow['final_files']={n:dict(path=str(after/n),sha256=sha(after/n),bytes=(after/n).stat().st_size) for n in flow['final_files']}
    flow.update(raw_source=str(raw),raw_receipt_sha256=sha(raw/'receipt.json'),raw_bound_files=bound,
        final_sdc_policy='Freeze exact approved clock before new independent gates; preserve original stricter3.3333ns flow SDC; all other final files byte identical',
        qualified_hard_macro=False)
    (out/'final-source.json').write_text(json.dumps(flow,indent=2)+'\n')
    assert all(sha(before/n)==h for n,h in bound.items())


def final_function(folder,out,run,pair=None,reuse=None):
    from native_signal_view import export
    assert pair is None and reuse is None
    source_dir,receipt,flow,results=source(folder);top=flow['top']
    assert top in ('block_v2_e','block_v2_g','block_v2_n','block_v2_m')
    netlist,proof=export(ROOT,out,run,source_dir,receipt,results,top,LIB)
    (out/'cells.ys').write_text('read_liberty -ignore_miss_func -ignore_miss_dir '+str(LIB)+'\nwrite_verilog -noattr cells.v\n')
    run(['yosys','-s',out/'cells.ys'],'cells.log')
    bench=ROOT/'project/experiments/block_v2'/('test_'+top[-1]+'.cpp')
    compiler='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
    # Cell-model warnings are logged; the source RTL has its separate strict lint.
    run([compiler,'--cc','--exe','--build','-j','16','-Wno-fatal','--top-module',top,
         '-Mdir',out/'obj','--output-split','12000','--output-split-cfuncs','150',
         '--x-initial','unique','--x-assign','unique','-CFLAGS','-std=c++17 -O1',
         netlist,out/'cells.v',bench],'build.log')
    runs={}
    for name,initial,seed in [('all-ones',1,143),('random-143',2,143),('random-144',2,144)]:
        log=name+'.log';run([out/'obj'/('V'+top),'+verilator+rand+reset+'+str(initial),'+verilator+seed+'+str(seed)],log)
        result=json.loads((out/log).read_text());assert result['passed']
        runs[name]=dict(initial=initial,seed=seed,result=result,log_sha256=sha(out/log))
    assert all(v['result']==runs['all-ones']['result']for v in runs.values())
    report=dict(passed=True,top=top,test_top=top,source_receipt_sha256=sha(folder/'receipt.json'),
        full_final_netlist=proof,bench_sha256=sha(bench),compiled_bench_sha256=sha(bench),library_sha256=sha(LIB),
        cell_models_sha256=sha(out/'cells.v'),initial_runs=runs,qualified_hard_macro=False,
        compiler_organization=dict(build_jobs=16,simulation_threads=1,concurrent_initial_states=1))
    (out/'final-function.json').write_text(json.dumps(report,indent=2)+'\n')


def final_formal(folder,out,run,function_folder):
    from native_logic_projection import export
    from native_formal import inspect
    from native_formal import fixture as lec_fixture
    from native_projection_control import verify as projection
    folder,receipt,flow,results=source(folder);top=flow['top']
    control=out/'controls';control.mkdir()
    (control/'lec').mkdir();lec_fixture(ROOT,control/'lec',run)
    for polarity in (0,1):
        p=control/str(polarity);p.mkdir()
        projection(ROOT,p,1,lambda cmd,log:run(cmd,'control-'+str(polarity)+'-'+log),polarity)
    # The fully exported immutable view is the computation dependency, whereas
    # a successful function receipt is still an unconditional acceptance gate.
    # Start expensive LEC while the same view is compiled/simulated, then join
    # both receipts below. Nothing can be accepted from an incomplete function.
    view_file=function_folder/'physical-functional-proof.json'
    view=json.loads(view_file.read_text());view_sha=sha(view_file)
    assert view['passed']
    assert view['input_sha256'][str(results/'6_final.odb')]==flow['final_files']['6_final.odb']['sha256']
    assert view['input_sha256'][str(results/'6_final.v')]==flow['final_files']['6_final.v']['sha256']
    actual=Path(view['full_view']);assert actual==function_folder/'physical-functional.v'
    actual_sha=sha(actual);assert actual_sha==view['full_view_sha256']
    before,bproof=export(ROOT,out,run,results/'1_synth_lec.v',LIB,top,'before',constant_functions=True)
    after,aproof=export(ROOT,out,run,actual,LIB,top,'after',constant_functions=True)
    assert bproof['removed_count']==0 and aproof['removed_count']>0
    config='format: verilog\ninput_paths:\n  - '+str(before)+'\n  - '+str(after)+'\nliberty_files:\n - '+str(LIB)+'\nlog_file: '+str(out/'kepler.log')+'\n'
    (out/'kepler.yml').write_text(config)
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    run([binary,'--config',out/'kepler.yml'],'formal.log')
    received=inspect((out/'kepler.log').read_text())
    fr=json.loads((function_folder/'receipt.json').read_text());assert fr['passed']
    f=function_folder/'final-function.json';assert sha(f)==fr['outputs'][f.name]
    fn=json.loads(f.read_text());assert fn['passed'] and fn['source_receipt_sha256']==sha(folder/'receipt.json')
    assert fn['full_final_netlist']==view and sha(view_file)==view_sha==fr['outputs'][view_file.name]
    assert sha(actual)==actual_sha==fn['full_final_netlist']['full_view_sha256']==fr['outputs'][str(actual.relative_to(function_folder))]
    result=dict(passed=received['passed'],top=top,strict_native_lec=received,before=bproof,after=aproof,
                source_receipt_sha256=sha(folder/'receipt.json'),function_receipt_sha256=sha(function_folder/'receipt.json'),
                log_sha256=sha(out/'kepler.log'),binary_sha256=sha(binary),qualified_hard_macro=False)
    (out/'formal.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']


def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['controls','seal','physical','drc','drc-compute','drc-join','function','formal','formal-join','deliver','geometry','escape'])
    p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--peer',type=Path);p.add_argument('--function',type=Path)
    p.add_argument('--gates',type=Path)
    p.add_argument('--computation',type=Path)
    p.add_argument('--reuse-build',type=Path)
    p.add_argument('--geometry',type=Path);p.add_argument('--native-source',type=Path)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,operation=a.operation,source=str(a.source),commands=[],inputs={})
    for d in ['project/experiments/block_v2','project/experiments/block_feed_v1','project/experiments/block_v1','project/rtl/block_v2']:
        for f in (ROOT/d).rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts:receipt['inputs'][str(f.relative_to(ROOT))]=sha(f)
    def run(cmd,log):
        cmd=list(map(str,cmd));start=time.time()
        with (a.out/log).open('w') as stream:q=subprocess.run(cmd,cwd=a.out,stdout=stream,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=cmd,log=log,sha256=sha(a.out/log),returncode=q.returncode,seconds=time.time()-start))
        assert q.returncode==0,(log,q.returncode)
    try:
        if a.operation=='controls':
            from receive import fresh_controls
            report=fresh_controls(ROOT,a.out,run)
            (a.out/'controls.json').write_text(json.dumps(dict(passed=True,boundary=report),indent=2)+'\n')
        elif a.operation=='seal':seal(a.source,a.out)
        elif a.operation in ('physical','drc'):
            import receive
            selected=lambda target,kind:source(a.source)
            getattr(receive,a.operation)(ROOT,a.out,16,run,'m' if source(a.source)[2]['top']=='block_feed_m' else 's',selected=selected)
        elif a.operation in ('drc-compute','drc-join'):
            from drc_computation import compute,join
            if a.operation=='drc-compute':compute(ROOT,a.source,a.out,run)
            else:join(ROOT,a.source,a.out,run,a.computation)
        elif a.operation=='function':final_function(a.source,a.out,run,a.peer,a.reuse_build)
        elif a.operation=='formal-join':
            from formal_join import join
            join(ROOT,a.source,a.out,run,a.function,a.computation)
        elif a.operation=='deliver':
            from deliver import deliver
            deliver(a.source,a.out,run,a.gates)
        elif a.operation=='geometry':
            from deliver import geometry
            geometry(a.source,a.out,run)
        elif a.operation=='escape':
            from escape import implement
            from deliver import accepted
            implement(ROOT,a.out,16,run,accepted(a.source)['macro'].lower(),a.source,a.geometry,a.native_source)
        else:final_formal(a.source,a.out,run,a.function)
        receipt['passed']=True
    finally:
        receipt['outputs']={str(f.relative_to(a.out)):sha(f) for f in a.out.rglob('*') if f.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
