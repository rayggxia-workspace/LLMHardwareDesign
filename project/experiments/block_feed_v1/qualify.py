"""Seal a completed candidate, then freshly qualify exact immutable final files."""
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
    return folder,receipt,flow,results


def seal(raw,out):
    from constraint_readback import audit
    from constraints import generate
    receipt=json.loads((raw/'receipt.json').read_text());assert receipt['passed']
    f=raw/'native-flow.json';assert sha(f)==receipt['outputs'][f.name]
    flow=json.loads(f.read_text());assert flow['passed'] and flow['pipeline_completed']
    assert flow['stages']==['do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish']
    relative='flow/results/nangate45/bv1_'+flow['top']+'/base'
    before=raw/relative;after=out/relative;after.mkdir(parents=True)
    for name in ['config.mk','pins.json','pins.tcl','input.sdc']:
        assert sha(raw/name)==receipt['outputs'][name];shutil.copyfile(raw/name,out/name)
    budget=flow['budget'];approved=re.sub(r'create_clock -name core -period [^ ]+',
        'create_clock -name core -period %.12g'%budget['clock_ns'],generate(budget))
    assert (out/'input.sdc').read_text()==approved
    original=(before/'6_final.sdc').read_text()
    flow['original_flow_boundary']=audit(original,json.loads((out/'pins.json').read_text())['pins'],dict(budget,clock_ns=3.3333))
    bound={}
    for name in ['6_final.v','6_final.sdc','6_final.odb','6_final.def','6_final.spef','1_synth_lec.v','bv1-input-diodes.tsv']:
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


def final_function(folder,out,run,pair=None):
    from native_signal_view import export
    source_dir,receipt,flow,results=source(folder);top=flow['top']
    netlist,proof=export(ROOT,out,run,source_dir,receipt,results,top,LIB)
    (out/'cells.ys').write_text('read_liberty -ignore_miss_func -ignore_miss_dir '+str(LIB)+'\nwrite_verilog -noattr cells.v\n')
    run(['yosys','-s',out/'cells.ys'],'cells.log')
    paths=[netlist,out/'cells.v'];extra=None
    if pair is not None:
        assert top=='block_feed_s_macro'
        peer,pr,pf,presults=source(pair)
        assert pf['top']=='block_feed_m'
        extra=out/'peer';extra.mkdir()
        def peer_run(cmd,log):run(cmd,'peer-'+log)
        # Export functions use explicit absolute output paths.
        mnet,mproof=export(ROOT,extra,peer_run,peer,pr,presults,'block_feed_m',LIB)
        paths += [mnet,ROOT/'project/rtl/block_feed_v1/block_feed_pair.sv',ROOT/'project/rtl/block_v1/transaction6k.sv']
        top='block_feed_pair';bench=ROOT/'project/experiments/block_feed_v1/test_pair.cpp'
    else:bench=ROOT/'project/experiments/block_feed_v1/test_m.cpp'
    compiler='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
    run([compiler,'--cc','--exe','--build','-j','16','-Wno-fatal','--top-module',top,'--prefix','V'+top,
         '-Mdir',out/'obj','--output-split','12000','--output-split-cfuncs','150','--threads','4',
         '--x-initial','unique','--x-assign','unique','-CFLAGS','-std=c++17 -O1',*paths,bench],'build.log')
    def one(case):
        name,initial,seed=case;log=name+'.log'
        run([out/'obj'/('V'+top),'+verilator+rand+reset+'+str(initial),'+verilator+seed+'+str(seed)],log)
        rows=[]
        for line in (out/log).read_text().splitlines():
            try:v=json.loads(line)
            except ValueError:continue
            if isinstance(v,dict):rows.append(v)
        assert len(rows)==1 and rows[0]['passed']
        return name,dict(initial=initial,seed=seed,result=rows[0],log_sha256=sha(out/log))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        runs=dict(pool.map(one,[('all-ones',1,130),('random-130',2,130),('random-131',2,131)]))
    assert all(v['result']==runs['all-ones']['result'] for v in runs.values())
    result=dict(passed=True,top=flow['top'],test_top=top,source_receipt_sha256=sha(folder/'receipt.json'),
                full_final_netlist=proof,bench_sha256=sha(bench),library_sha256=sha(LIB),
                cell_models_sha256=sha(out/'cells.v'),initial_runs=runs,qualified_hard_macro=False)
    if extra is not None:result.update(peer_source_receipt_sha256=sha(pair/'receipt.json'),peer_full_final_netlist=mproof)
    (out/'final-function.json').write_text(json.dumps(result,indent=2)+'\n')


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
    fr=json.loads((function_folder/'receipt.json').read_text());assert fr['passed']
    f=function_folder/'final-function.json';assert sha(f)==fr['outputs'][f.name]
    fn=json.loads(f.read_text());assert fn['passed'] and fn['source_receipt_sha256']==sha(folder/'receipt.json')
    actual=Path(fn['full_final_netlist']['full_view']);assert sha(actual)==fn['full_final_netlist']['full_view_sha256']
    before,bproof=export(ROOT,out,run,results/'1_synth_lec.v',LIB,top,'before',constant_functions=True)
    after,aproof=export(ROOT,out,run,actual,LIB,top,'after',constant_functions=True)
    assert bproof['removed_count']==0 and aproof['removed_count']>0
    config='format: verilog\ninput_paths:\n  - '+str(before)+'\n  - '+str(after)+'\nliberty_files:\n - '+str(LIB)+'\nlog_file: '+str(out/'kepler.log')+'\n'
    (out/'kepler.yml').write_text(config)
    binary=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal')
    run([binary,'--config',out/'kepler.yml'],'formal.log')
    received=inspect((out/'kepler.log').read_text())
    result=dict(passed=received['passed'],top=top,strict_native_lec=received,before=bproof,after=aproof,
                source_receipt_sha256=sha(folder/'receipt.json'),function_receipt_sha256=sha(function_folder/'receipt.json'),
                log_sha256=sha(out/'kepler.log'),binary_sha256=sha(binary),qualified_hard_macro=False)
    (out/'formal.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']


def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['controls','seal','physical','drc','function','formal'])
    p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--peer',type=Path);p.add_argument('--function',type=Path)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,operation=a.operation,source=str(a.source),commands=[],inputs={})
    for d in ['project/experiments/block_feed_v1','project/experiments/block_v1','project/rtl/block_feed_v1']:
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
        elif a.operation=='function':final_function(a.source,a.out,run,a.peer)
        else:final_formal(a.source,a.out,run,a.function)
        receipt['passed']=True
    finally:
        receipt['outputs']={str(f.relative_to(a.out)):sha(f) for f in a.out.rglob('*') if f.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
