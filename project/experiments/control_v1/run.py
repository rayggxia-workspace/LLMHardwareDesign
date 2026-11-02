"""Source-bound control RTL tests and mapping. Must run inside Slurm allocation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
COMPILER='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
MODELS={'c':('control_c','test_c.cpp'),'endpoint':('control_endpoint_queue','test_endpoint.cpp'),
        'planner':('control_dma_planner','test_planner.cpp'),'axil':('control_axil_bridge','test_axil.cpp')}
MODELS['traces']=('control_c','test_traces.cpp')
MODELS['status']=('control_status','test_status.cpp')
MODELS['reset']=('control_reset_distribution','test_reset.cpp')
MODELS['d']=('control_d','test_d.cpp')
MODELS['ds']=('control_d_s_pair','test_d.cpp')
MODELS['system']=('control_system','test_system.cpp')
MODELS['route']=('control_route','test_route.cpp')
MODELS['s_arbiter']=('control_s_arbiter','test_s_arbiter.cpp')
for _role in ('e','g','n'):MODELS['pair_'+_role]=('control_pair_'+_role,'test_vector.cpp')
for _role in ('m','n','e','g','s','t'):MODELS['adapter_'+_role]=('control_adapter_'+_role,'test_adapter_'+_role+'.cpp')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=MODELS,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--physical',action='store_true')
    p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID'),'EDA only in Slurm'
    affinity=sorted(os.sched_getaffinity(0));assert len(affinity)<=16
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    top,cpp=MODELS[a.model];rtl=ROOT/'project/rtl/control_v1'/(top+'.sv');cpp=Path(__file__).parent/cpp
    sources=[rtl]
    if a.model=='d':sources.extend(rtl.parent/(name+'.sv') for name in ('control_dma_planner','control_dma_read','control_dma_write'))
    if a.model=='ds':
        sources=[ROOT/'project/experiments/control_v1/control_d_s_pair.sv']
        sources.extend(ROOT/'project/rtl/control_v1'/(name+'.sv') for name in ('control_d','control_dma_planner','control_dma_read','control_dma_write'))
        sources.extend(ROOT/'project/rtl/block_feed_v1'/(name+'.sv') for name in ('block_feed_s_macro','block_feed_s16k','block_feed_loader'))
    includes=[];extra_inputs=[];sim_sources=[];cflags='-std=c++17 -O1'+(' -DREAL_S' if a.model=='ds' else '')
    if a.model in ('reset','system'):
        sim_sources.append(ROOT/'project/experiments/control_v1/BUF_X16.v');extra_inputs.extend(sim_sources)
    if a.model=='system':
        sources=list(sorted((ROOT/'project/rtl/control_v1').glob('*.sv')))
        sources.extend(ROOT/'project/rtl/block_feed_v1'/(name+'.sv') for name in ('block_feed_s_macro','block_feed_s16k','block_feed_loader'))
        sources.extend(ROOT/'project/rtl/block_v2'/(name+'.sv') for name in ('block_v2_m','block_v2_n','block_v2_n_group','block_v2_e','block_v2_g'))
        sources.append(ROOT/'project/rtl/block_v1/transaction6k.sv')
        extra_inputs.extend(ROOT/'project/rtl/block_v2'/name for name in ('block_v2_g_tables.svh','block_v2_n_exp.svh'))
        includes=['-I'+str(ROOT/'project/rtl/block_v2'),str(ROOT/'project/experiments/control_v1/native_t_lint.vlt')]
        extra_inputs.append(ROOT/'project/experiments/control_v1/native_t_lint.vlt')
    if a.model in ('adapter_n','adapter_e','adapter_g'):
        sources.append(ROOT/'project/rtl/control_v1/control_vector_adapter.sv')
        extra_inputs.append(ROOT/'project/experiments/control_v1/adapter_vector_bench.hpp')
    if a.model.startswith('pair_'):
        role=a.model[-1];sources=[ROOT/'project/experiments/control_v1'/('control_pair_'+role+'.sv')]
        sources.extend(ROOT/'project/rtl/control_v1'/(name+'.sv') for name in ('control_adapter_'+role,'control_vector_adapter'))
        sources.extend(ROOT/'project/rtl/block_feed_v1'/(name+'.sv') for name in ('block_feed_s_macro','block_feed_s16k','block_feed_loader'))
        sources.append(ROOT/'project/rtl/block_v2'/('block_v2_'+role+'.sv'))
        if role=='n':sources.append(ROOT/'project/rtl/block_v2/block_v2_n_group.sv')
        if role in ('g','n'):extra_inputs.append(ROOT/'project/rtl/block_v2'/('block_v2_g_tables.svh' if role=='g' else 'block_v2_n_exp.svh'))
        includes=['-I'+str(ROOT/'project/rtl/block_v2')];cflags+=' -DROLE='+str({'e':3,'g':4,'n':2}[role])
    receipt=dict(passed=False,top=top,source_sha256={str(f.relative_to(ROOT)):sha(f) for f in [*sources,*extra_inputs,cpp,Path(__file__)]},
                 affinity=affinity,job=os.environ['SLURM_JOB_ID'],commands=[],runs=[],qualified_hard_macro=False)
    def run(command,log,cwd=None):
        command=list(map(str,command));start=time.time()
        with (a.out/log).open('w') as f:q=subprocess.run(command,cwd=cwd or a.out,stdout=f,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=command,log=log,sha256=sha(a.out/log),returncode=q.returncode,seconds=time.time()-start))
        assert q.returncode==0,(log,q.returncode)
    try:
        receipt['verilator_version']=subprocess.check_output([COMPILER,'--version'],text=True).strip()
        run([COMPILER,'--lint-only','-Wall','--top-module',top,*includes,*sources,*sim_sources],'lint.log')
        run([COMPILER,'--cc','--exe','--build','-j','8','--top-module',top,'--Mdir',a.out/'obj',
             '--x-initial','unique','--x-assign','unique','-CFLAGS',cflags,*includes,*sources,*sim_sources,cpp],'build.log')
        for mode,seed in [(1,162),(2,162),(2,163)]:
            log=f'run-{mode}-{seed}.json';run([a.out/'obj'/('V'+top),f'+verilator+rand+reset+{mode}',f'+verilator+seed+{seed}'],log)
            result=json.loads((a.out/log).read_text());assert result['passed'];receipt['runs'].append(result)
        receipt['rtl_passed']=True
        if a.verify_only:
            receipt['passed']=True
            return
        lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
        mapping=a.out/'mapping'/top;mapping.mkdir(parents=True)
        script=f'read_liberty -lib {lib}\nread_verilog -sv '+ ' '.join(map(str,sources))+f'\nhierarchy -check -top {top}\nflatten -noscopeinfo\nproc\nopt\n'
        script+=f'synth -top {top} -noabc\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nclean\ncheck -assert\n'
        script+='flatten -noscopeinfo\nclean\ncheck -assert\n'
        script+='hilomap -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z\nclean\ncheck -assert\n'
        script+=f'stat -liberty {lib}\nwrite_verilog -noattr mapped.v\nwrite_json mapped.json\n'
        (mapping/'map.ys').write_text(script);run(['yosys','-s',mapping/'map.ys'],'map.log',mapping)
        module=json.loads((mapping/'mapped.json').read_text())['modules'][top];cells={}
        for c in module['cells'].values():
            assert not c['type'].startswith('$');cells[c['type']]=cells.get(c['type'],0)+1
        if a.model=='reset':
            assert sum(count for name,count in cells.items() if name.startswith('DFF'))==1,cells
            assert cells.get('BUF_X16',0)>=25,('Reset branches merged or lost',cells)
        mapped=dict(passed=True,mapped=True,top=top,source_sha256={str(f.relative_to(ROOT)):sha(f) for f in sources},liberty_sha256=sha(lib),
            cell_counts=cells,ports={k:dict(direction=v['direction'],bits=len(v['bits'])) for k,v in module['ports'].items()},
            reused_artifacts=dict(artifacts={str(mapping/n):sha(mapping/n) for n in ['mapped.v','mapped.json']}))
        (mapping/'receipt.json').write_text(json.dumps(mapped,indent=2)+'\n');receipt['mapped']=mapped
        if a.physical:
            # Call the existing generic implementation body, not its old
            # fixed-top CLI. Accepted macro sources and scripts stay unchanged.
            sys.path.insert(0,str(ROOT/'project/experiments/block_v2'))
            import physical
            out=a.out/'pnr';out.mkdir()
            args=SimpleNamespace(out=out,top=top,mapping=a.out/'mapping',input_receivers=True,
                remove_abc_buffers=False,placement_mode='timing',fanout_mode='original',
                r_compact_floorplan=False,r_strong_clock=False,refine_partition_placement=False,
                placement_hold_margin=None,hold_repair_margin=0.015 if a.model=='d' else 0.005 if a.model in ('adapter_e','route','s_arbiter','status') else 0.0)
            def physical_run(command,log):run(command,'pnr/'+log,out)
            physical.implement(args,physical_run)
            receipt['native_pipeline_completed']=True
        receipt['passed']=True
    finally:
        receipt['outputs']={str(f.relative_to(a.out)):sha(f) for f in a.out.glob('*.log')}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
