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
MODELS['link8']=('control_link8','test_link8.cpp')
MODELS['d']=('control_d','test_d.cpp')
MODELS['ds']=('control_d_s_pair','test_d.cpp')
MODELS['system']=('control_system','test_system.cpp')
MODELS['route']=('control_route','test_route.cpp')
MODELS['s_arbiter']=('control_s_arbiter','test_s_arbiter.cpp')
MODELS['native_s']=('block_feed_s_macro',None)
MODELS['native_s_rtl']=('block_feed_s_macro','test_native_s.cpp')
MODELS['native_s_cts']=('block_feed_s_macro',None)
MODELS['native_s_reset_diagnostic']=('block_feed_s_macro',None)
MODELS['native_s_reset_repair']=('block_feed_s_macro',None)
MODELS['native_s_reset_probe']=('block_feed_s_macro',None)
MODELS['native_s_escape_repair']=('block_feed_s_macro',None)
for _role in ('e','g','n'):MODELS['pair_'+_role]=('control_pair_'+_role,'test_vector.cpp')
for _role in ('m','n','e','g','s','t'):MODELS['adapter_'+_role]=('control_adapter_'+_role,'test_adapter_'+_role+'.cpp')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=MODELS,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--physical',action='store_true')
    p.add_argument('--verify-only',action='store_true')
    p.add_argument('--s-native-delivery',type=Path,
                   help='User-authorized S-only rebuild: reuse the exact qualified logical mapping and add drive inside S; all physical/final gates must be rerun')
    p.add_argument('--s-cts-folder',type=Path,help='Read-only diagnosis of the new S CTS checkpoint; no qualification')
    p.add_argument('--s-grt-folder',type=Path,help='Read-only completed new S post-GRT reset branch measurements; no qualification')
    p.add_argument('--s-native-source',type=Path,help='Completed new S source for explicitly bound GRT reuse; no acceptance inherited')
    p.add_argument('--s-reset-evidence',type=Path,help='Passed read-only reset branch measurements')
    p.add_argument('--s-reset-buffers',type=int,choices=[48,64,96,128],help='Real BUF_X1 per measured fast reset branch; all final gates rerun')
    p.add_argument('--s-escape-drc',type=Path,help='Exact retained S1181 complete-native M10 spacing failure')
    p.add_argument('--s-escape-checkpoint',type=Path,help='Exact failed1340 preparation with successful zero complete-native DRC; no qualification inherited')
    p.add_argument('--s-hold-margin',type=float,choices=[0.0,0.005,0.015,0.02],default=0.0)
    p.add_argument('--placement-density',type=float,choices=[0.40,0.42,0.45])
    p.add_argument('--strong-output-drivers',action='store_true',
                   help='Add explicit native BUF_X32 output stages before final routing; fresh gates required')
    p.add_argument('--repair-s-arbiter-escape',action='store_true')
    p.add_argument('--repair-s-arbiter-write-escape',action='store_true',
                   help='Repair only the observed din[633] M10 escape before fresh final extraction and all gates')
    p.add_argument('--repair-s-arbiter-data-escape',choices=['din[632]','din[633]'],
                   help='Explicit observed M10 data escape; fresh final extraction and all gates remain mandatory')
    p.add_argument('--repair-s-arbiter-strong-escapes',action='store_true',
                   help='Only retained strong-output candidate violations: din629/din633/dout117')
    a=p.parse_args()
    if a.model=='native_s_escape_repair':
        assert a.s_native_source and a.s_escape_drc and a.physical and not a.verify_only
        assert not any([a.s_reset_evidence,a.s_reset_buffers,a.s_grt_folder,a.s_cts_folder,a.s_native_delivery])
        from s_escape_repair import implement
        implement(a);return
    assert not a.s_escape_drc and not a.s_escape_checkpoint
    if a.model in ('native_s_reset_repair','native_s_reset_probe'):
        assert a.s_native_source and a.s_reset_evidence and a.s_reset_buffers and a.physical and not a.verify_only
        assert not a.s_grt_folder and not a.s_cts_folder and not a.s_native_delivery
        if a.model=='native_s_reset_probe':
            from s_reset_probe import inspect
            inspect(a)
        else:
            from s_reset_repair import implement
            implement(a)
        return
    assert not a.s_native_source and not a.s_reset_evidence and not a.s_reset_buffers
    if a.model=='native_s_reset_diagnostic':
        assert a.s_grt_folder and a.verify_only and not a.physical and not a.s_native_delivery and not a.s_cts_folder
        from s_reset_branch import inspect
        inspect(a);return
    assert not a.s_grt_folder
    if a.model=='native_s_cts':
        assert a.s_cts_folder and a.verify_only and not a.physical and not a.s_native_delivery
        from native_s_output import inspect_cts
        inspect_cts(a);return
    assert not a.s_cts_folder
    if a.model=='native_s':
        assert a.s_native_delivery and a.physical and a.strong_output_drivers and not a.verify_only
        from native_s_output import implement
        implement(a);return
    assert not a.s_native_delivery
    assert sum(map(bool,[a.repair_s_arbiter_escape,a.repair_s_arbiter_write_escape,a.repair_s_arbiter_data_escape,a.repair_s_arbiter_strong_escapes]))<=1
    assert not a.repair_s_arbiter_strong_escapes or(a.model=='s_arbiter'and a.strong_output_drivers)
    assert not (a.repair_s_arbiter_escape or a.repair_s_arbiter_write_escape or a.repair_s_arbiter_data_escape) or a.model=='s_arbiter'
    assert os.environ.get('SLURM_JOB_ID'),'EDA only in Slurm'
    affinity=sorted(os.sched_getaffinity(0));assert len(affinity)<=16
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    top,cpp=MODELS[a.model];rtl=ROOT/'project/rtl/control_v1'/(top+'.sv');cpp=Path(__file__).parent/cpp
    sources=[rtl]
    if a.model=='native_s_rtl':
        assert a.verify_only and not a.physical
        sources=[ROOT/'project/rtl/block_feed_v1'/(name+'.sv') for name in ('block_feed_s_macro','block_feed_s16k','block_feed_loader')]
    if a.model=='d':sources.extend(rtl.parent/(name+'.sv') for name in ('control_dma_planner','control_dma_read','control_dma_write'))
    if a.model=='ds':
        sources=[ROOT/'project/experiments/control_v1/control_d_s_pair.sv']
        sources.extend(ROOT/'project/rtl/control_v1'/(name+'.sv') for name in ('control_d','control_dma_planner','control_dma_read','control_dma_write'))
        sources.extend(ROOT/'project/rtl/block_feed_v1'/(name+'.sv') for name in ('block_feed_s_macro','block_feed_s16k','block_feed_loader'))
    includes=[];extra_inputs=[];sim_sources=[];cflags='-std=c++17 -O1'+(' -DREAL_S' if a.model=='ds' else '')
    if a.strong_output_drivers:extra_inputs.append(ROOT/'project/experiments/control_v1/output_drivers.tcl')
    if a.model in ('reset','system'):
        sim_sources.append(ROOT/'project/experiments/control_v1/BUF_X16.v');extra_inputs.extend(sim_sources)
    if a.model=='adapter_s':extra_inputs.append(ROOT/'project/experiments/control_v1/control_hold_budget.tcl')
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
                remove_abc_buffers=False,placement_mode='timing',fanout_mode='original',placement_density=a.placement_density,
                control_escape_repair=['din[629]','din[633]','dout[117]'] if a.repair_s_arbiter_strong_escapes else ['dout[117]'] if a.repair_s_arbiter_escape else ['din[633]'] if a.repair_s_arbiter_write_escape else [a.repair_s_arbiter_data_escape] if a.repair_s_arbiter_data_escape else [],
                r_compact_floorplan=False,r_strong_clock=False,refine_partition_placement=False,
                strong_output_drivers=a.strong_output_drivers,
                placement_hold_margin=None,hold_repair_margin=0.015 if a.model in ('d','reset','adapter_s') else 0.005 if a.model in ('adapter_e','route','s_arbiter','status') else 0.0)
            def physical_run(command,log):run(command,'pnr/'+log,out)
            physical.implement(args,physical_run)
            receipt['native_pipeline_completed']=True
        receipt['passed']=True
    finally:
        receipt['outputs']={str(f.relative_to(a.out)):sha(f) for f in a.out.glob('*.log')}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
