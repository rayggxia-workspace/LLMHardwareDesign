"""Fresh native P&R of issue143 independently verified macros. Completion is not qualification.

Receives immutable synthesis, never another macro's physical databases.
All processes run inside the job's own CPU affinity and output directory.
"""
import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'project/experiments/block_v1'))
sys.path.insert(0, str(ROOT/'project/experiments/block_feed_v1'))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):h.update(b)
    return h.hexdigest()


def implement(args, run):
    from structural_view import unsigned, compare
    from pins import generate
    from revision300_ports import independent
    from pin_contract import script as pin_script
    from constraints import generate as constraints
    from native_reroute import config_suffix
    out=args.out; top=args.top
    mapping_path=args.mapping/top/'receipt.json'
    mapping=json.loads(mapping_path.read_text());assert mapping['passed'] and mapping['mapped']
    for path,digest in mapping['source_sha256'].items():assert sha(ROOT/path)==digest
    artifacts=mapping['reused_artifacts']['artifacts']
    for path,digest in artifacts.items():assert sha(path)==digest
    mapped=next(Path(p).parent for p in artifacts if p.endswith('/mapped.json'))
    flow=Path('/OpenROAD-flow-scripts/flow');platform=flow/'platforms/nangate45'
    lib=platform/'lib/NangateOpenCellLibrary_typical.lib';assert sha(lib)==mapping['liberty_sha256']
    expected=json.loads((mapped/'mapped.json').read_text())
    removed=[]
    for module in expected['modules'].values():
        for name,cell in list(module.get('cells',{}).items()):
            if cell['type']=='$scopeinfo':
                assert not cell['connections']; removed.append(name);del module['cells'][name]
            else:assert not cell['type'].startswith('$'),cell['type']
    has_signed=any(v.get('signed') for m in expected['modules'].values() for k in ('ports','netnames') for v in m.get(k,{}).values())
    metadata=unsigned(expected) if has_signed else dict(removed_signed_metadata=[])
    metadata['removed_portless_scope_annotations']=removed
    (out/'unsigned.json').write_text(json.dumps(expected)+'\n')
    script='read_json '+str(out/'unsigned.json')+'\nhierarchy -check -top '+top+'\n'
    script+='write_verilog -noattr -noexpr -norename structural.v\nwrite_json structural.json\n'
    script+='design -reset\nread_liberty -lib '+str(lib)+'\nread_verilog structural.v\n'
    script+='hierarchy -check -top '+top+'\nwrite_json reparsed.json\n'
    (out/'structural.ys').write_text(script);run(['yosys','-s',out/'structural.ys'],'structural.log')
    expected=json.loads((out/'structural.json').read_text());observed=json.loads((out/'reparsed.json').read_text())
    proof=compare(expected,observed);negative=copy.deepcopy(observed)
    cell=next(iter(negative['modules'][top]['cells'].values()));values=next(v for v in cell['connections'].values() if v)
    values[0]='1' if values[0]!='1' else '0'
    rejected=False
    try:compare(expected,negative)
    except AssertionError:rejected=True
    assert rejected;proof.update(metadata=metadata,single_pin_bit_negative_rejected=True)
    (out/'structural-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    folder=ROOT/'project/experiments/block_v1'
    technology=json.loads((folder/'technology-2um-v1.json').read_text())
    native=platform/'lef/NangateOpenCellLibrary.tech.lef';assert sha(native)==technology['native_tech_sha256']
    text=lib.read_text();starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',text));areas={}
    for i,m in enumerate(starts):
        chunk=text[m.end():starts[i+1].start() if i+1<len(starts) else len(text)]
        areas[m.group(1)]=float(re.search(r'\barea\s*:\s*([\d.eE+-]+)\s*;',chunk).group(1))
    active=sum(areas[name]*count for name,count in mapping['cell_counts'].items())
    side=max(400,math.ceil((math.sqrt(active/.4)+40)/10)*10)
    if top=='control_link8':
        # A small, separately qualified eight-lane drive/isolation macro.
        # Actual placement/DRC/PG/timing remain the same final gates.
        side=max(100,math.ceil((math.sqrt((active+8*areas['BUF_X32']+10*areas['BUF_X8'])/.4)+40)/10)*10)
    if top=='block_v1_r':
        if args.r_compact_floorplan:
            side=2400
            # Capacity forecast only; real placement/routing and all gates stay.
            assert active*1.55<=.45*(side-40)**2,('R compact area headroom',active)
        else:side=max(3000,side)
    arbiter_side=getattr(args,'s_arbiter_side_um',None)
    if arbiter_side is not None:
        assert top=='control_s_arbiter_r7' and arbiter_side==3200 and getattr(args,'strong_output_drivers',False)
        assert side<=arbiter_side, ('Arbiter floorplan cannot shrink mapped capacity',side)
        side=arbiter_side
    while True:
        try:
            plan,fixture,geometry=generate(mapping['ports'],side,technology);break
        except AssertionError as error:
            if not error.args or not isinstance(error.args[0],tuple) or error.args[0][0]!='Insufficient staggered interface tracks':raise
            side+=10
    (out/'pins.json').write_text(json.dumps(plan,indent=2)+'\n');(out/'pins.tcl').write_text(pin_script(plan))
    coarse=independent(ROOT,out,fixture,run)
    budget=json.loads((folder/'physical-budget-300mhz.json').read_text())
    sdc=re.sub(r'create_clock -name core -period [^ ]+','create_clock -name core -period %.12g'%budget['clock_ns'],constraints(budget))
    (out/'input.sdc').write_text(sdc);shutil.copyfile(out/'structural.v',out/'input.v')
    input_sha=sha(out/'input.v');nickname='bv1_'+top
    config='export PLATFORM = nangate45\nexport DESIGN_NAME = '+top+'\nexport DESIGN_NICKNAME = '+nickname+'\n'
    config+='export VERILOG_FILES = '+str(out/'input.v')+'\nexport SDC_FILE = '+str(out/'input.sdc')+'\n'
    config+='export DIE_AREA = 0 0 %g %g\nexport CORE_AREA = 20 20 %g %g\n'%(side,side,side-20,side-20)
    config+='export PLACE_DENSITY = 0.45\nexport FOOTPRINT_TCL = '+str(out/'pins.tcl')+'\nexport KEEP_VARS = 1\n'
    density=getattr(args,'placement_density',None)
    if density is not None:
        assert (top.startswith('control_')or top=='block_feed_s_macro') and density in (.40,.42,.45)
        config+='export PLACE_DENSITY = '+str(density)+'\n'
    if top=='block_v2_n':
        # The first Q1.14 route has two final native M2 markers on one net.
        # Preserve it as a failure; use a fresh, less dense placement and route.
        config+='export PLACE_DENSITY = 0.42\n'
    config+='override export MIN_ROUTING_LAYER = metal1\noverride export MAX_ROUTING_LAYER = metal10\n'
    cts_args='-sink_clustering_enable -repair_clock_nets -apply_ndr none'
    if args.r_strong_clock:
        # Native CTS_ARGS replaces the default argument list; encode the cell
        # list here, not in an ignored CTS_BUF_LIST environment variable.
        assert all(name in areas for name in ('BUF_X4','BUF_X8','BUF_X16','BUF_X32'))
        cts_args+=' -buf_list {BUF_X4 BUF_X8 BUF_X16 BUF_X32}'
    if top=='block_v1_r':
        config+='export PLACE_DENSITY = '+('0.45' if args.r_compact_floorplan else '0.25')+'\nexport CTS_ARGS = '+cts_args+'\n'
    if args.remove_abc_buffers:
        assert not any(name.startswith(('BUF_','CLKBUF_')) for name in mapping['cell_counts'])
        config+='export REMOVE_ABC_BUFFERS = 1\n'
    if top=='control_adapter_s':
        shutil.copyfile(ROOT/'project/experiments/control_v1/control_hold_budget.tcl',out/'control-hold-budget.tcl')
        config+='export PRE_CTS_TCL = '+str(out/'control-hold-budget.tcl')+'\n'
    if top in ('control_adapter_r','control_s_arbiter_r7'):
        shutil.copyfile(ROOT/'project/experiments/control_v1/r256_hold_budget.tcl',out/'r256-hold-budget.tcl')
        config+='export PRE_CTS_TCL = '+str(out/'r256-hold-budget.tcl')+'\n'
    if args.placement_mode=='geometric':
        # Avoid repeated resizer calls inside GPL on the large mux-based store.
        # The subsequent placed repair_design/repair_timing and final gates stay.
        config+='export GPL_TIMING_DRIVEN = 0\nexport ENABLE_PLACE_REPAIR_TIMING = 1\n'
    if args.fanout_mode=='partition':
        assert top in ('block_feed_s_macro','block_v1_r') and args.placement_mode=='geometric'
        shutil.copyfile(ROOT/'project/experiments/block_feed_v1/partition_fanout.tcl',out/'partition-fanout.tcl')
        if args.refine_partition_placement:
            with (out/'partition-fanout.tcl').open('a') as stream:
                stream.write('\n'+(ROOT/'project/experiments/block_v2/refine_partition_placement.tcl').read_text())
        if args.placement_hold_margin is not None:
            # Only this pre-CTS process changes its optimization target. CTS
            # starts a fresh process and reloads the normal 0.02ns target.
            with (out/'partition-fanout.tcl').open('a') as stream:
                stream.write('\nset ::env(HOLD_SLACK_MARGIN) 0\n'
                    'puts "ISSUE143_R_PLACEMENT_HOLD target=0ns; CTS reloads configured margin; final checks unchanged"\n')
        config+='export PRE_RESIZE_TCL = '+str(out/'partition-fanout.tcl')+'\n'
    hook=(folder/'native_input_diodes.tcl').read_text().replace('  if {[$port getName] eq "clk"} {continue}\n','')
    if args.input_receivers:
        hook=(ROOT/'project/experiments/block_feed_v1/input_receivers.tcl').read_text()+'\n'+hook
    if getattr(args,'strong_output_drivers',False):
        assert top.startswith('control_')or top=='block_feed_s_macro','Only control leaves or the explicitly authorized S rebuild'
        hook=(ROOT/'project/experiments/block_feed_v1/input_receivers.tcl').read_text()+'\n'+(ROOT/'project/experiments/control_v1/output_drivers.tcl').read_text()+'\n'+(folder/'native_input_diodes.tcl').read_text().replace('  if {[$port getName] eq "clk"} {continue}\n','')
    if top=='block_v1_r':hook+='\nset_global_routing_layer_adjustment metal4-metal10 .20\n'
    (out/'input-diodes.tcl').write_text(hook)
    # Optimization target, not a timing exception: final native min slack must
    # remain nonnegative under the unchanged full SDC/uncertainty contract.
    hold_target='%.3f'%args.hold_repair_margin
    config+=config_suffix(40,.005,out/'input-diodes.tcl','metal10')+'\nexport HOLD_SLACK_MARGIN = '+hold_target+'\n'
    (out/'config.mk').write_text(config)
    results=out/'flow/results/nangate45'/nickname/'base';results.mkdir(parents=True)
    for suffix in ('v','sdc'):
        p=results/('1_2_yosys.'+suffix);shutil.copyfile(out/('input.'+suffix),p);p.chmod(0o444)
    command=['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),'WORK_HOME='+str(out/'flow'),'NUM_CORES=16']
    wanted=dict(MIN_ROUTING_LAYER='metal1',MAX_ROUTING_LAYER='metal10',KEEP_VARS='1',LEC_CHECK='1',SEC_CHECK='0',
                TECH_LEF=str(native),RCX_RULES=str(platform/'rcx_patterns.rules'),CAP_MARGIN='40',HOLD_SLACK_MARGIN=hold_target)
    if args.remove_abc_buffers:wanted['REMOVE_ABC_BUFFERS']='1'
    if top=='control_adapter_s':wanted['PRE_CTS_TCL']=str(out/'control-hold-budget.tcl')
    if top in ('control_adapter_r','control_s_arbiter_r7'):wanted['PRE_CTS_TCL']=str(out/'r256-hold-budget.tcl')
    if density is not None:wanted['PLACE_DENSITY']=str(density)
    if top=='block_v2_n':wanted['PLACE_DENSITY']='0.42'
    if top=='block_v1_r':wanted.update(PLACE_DENSITY='0.45' if args.r_compact_floorplan else '0.25',CTS_ARGS=cts_args)
    if args.placement_mode=='geometric':
        wanted.update(GPL_TIMING_DRIVEN='0',ENABLE_PLACE_REPAIR_TIMING='1')
    if args.fanout_mode=='partition':wanted['PRE_RESIZE_TCL']=str(out/'partition-fanout.tcl')
    actual={}
    for key,value in wanted.items():
        log='variable-'+key+'.log';run(command+['print-'+key],log)
        actual[key]=re.search(r'(?m)^'+key+r': (.+)$',(out/log).read_text()).group(1).strip()
        assert actual[key]==value,(key,actual[key],value)
    result=dict(schema='issue143-native-flow/1',passed=False,top=top,implementation_count=1,
                mapping_receipt_sha256=sha(mapping_path),rtl_sha256=mapping['source_sha256'],mapped_artifacts=artifacts,
                mapped_area_um2=active,die_um=[side,side],config_sha256=sha(out/'config.mk'),pins_sha256=sha(out/'pins.json'),
                budget=budget,actual_variables=actual,planned_complete_escape=geometry,planned_independent_gds=coarse,
                stages=[],final_files={},qualified_hard_macro=False,inherited_physical_stages=[])
    if args.input_receivers:result['repair']='Fixed BUF_X8 data input receivers in native macro; all limits unchanged'
    result['remove_abc_buffers']=args.remove_abc_buffers
    result['strong_output_drivers']=getattr(args,'strong_output_drivers',False)
    if arbiter_side is not None:result['fresh_s_arbiter_side_um']=arbiter_side
    if top=='control_adapter_s':result['hold_buffer_budget_percent']=100
    if top in ('control_adapter_r','control_s_arbiter_r7'):
        result['hold_buffer_budget_percent']=100
        result['hold_buffer_budget_hook_sha256']=sha(out/'r256-hold-budget.tcl')
    result['placement_mode']=args.placement_mode
    if density is not None:result['placement_density']=density
    result['r_compact_floorplan']=args.r_compact_floorplan
    result['r_strong_clock']=args.r_strong_clock
    result['fanout_mode']=args.fanout_mode
    result['refine_partition_placement']=args.refine_partition_placement
    result['placement_hold_margin_ns']=args.placement_hold_margin if args.placement_hold_margin is not None else args.hold_repair_margin
    result['hold_repair_margin_ns']=args.hold_repair_margin
    def save():(out/'native-flow.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    for number,stage in enumerate(('do-1_synth','do-floorplan','do-place','do-cts','do-route','do-finish')):
        run(command+[stage],'%02d-%s.log'%(number,stage));result['stages'].append(stage)
        if stage=='do-route' and getattr(args,'control_escape_repair',[]):
            sys.path.insert(0,str(ROOT/'project/experiments/control_v1'))
            from prefreeze_escape import repair
            result['control_prefreeze_escape']=repair(ROOT,out,results,top,args.control_escape_repair,run)
        assert sha(out/'input.v')==input_sha;save()
    for suffix in ('v','sdc','def','odb','spef'):
        p=results/('6_final.'+suffix);assert p.is_file()
        result['final_files'][p.name]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
    if getattr(args,'strong_output_drivers',False):
        sys.path.insert(0,str(ROOT/'project/experiments/control_v1'))
        from strong_driver_audit import audit
        result['strong_output_driver_proof']=audit(results/'6_final.odb',out,
            sum(row['bits']for row in mapping['ports'].values()if row['direction']=='output'))
    result['passed']=True;result['pipeline_completed']=True;save()


def main():
    p=argparse.ArgumentParser();p.add_argument('--top',choices=['block_v2_e','block_v2_g','block_v2_n','block_v2_m','block_v1_r'],required=True)
    p.add_argument('--mapping',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--remove-abc-buffers',action='store_true')
    p.add_argument('--input-receivers',action='store_true')
    p.add_argument('--placement-mode',choices=['timing','geometric'],default='timing')
    p.add_argument('--fanout-mode',choices=['original','partition'],default='original')
    p.add_argument('--refine-partition-placement',action='store_true')
    p.add_argument('--placement-hold-margin',type=float,choices=[0.0])
    p.add_argument('--r-compact-floorplan',action='store_true')
    p.add_argument('--r-strong-clock',action='store_true')
    p.add_argument('--hold-repair-margin',type=float,choices=[0.0,0.02],default=0.02)
    args=p.parse_args()
    if args.r_compact_floorplan:assert args.top=='block_v1_r'
    if args.r_strong_clock:assert args.top=='block_v1_r'
    if args.refine_partition_placement:
        assert args.top=='block_v1_r' and args.placement_mode=='geometric' and args.fanout_mode=='partition'
    if args.placement_hold_margin is not None:
        assert args.top=='block_v1_r' and args.placement_mode=='geometric' and args.fanout_mode=='partition'
    args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,top=args.top,start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                 affinity=sorted(__import__('os').sched_getaffinity(0)),commands=[],inputs={})
    for folder in ('project/experiments/block_v2','project/experiments/block_feed_v1','project/experiments/block_v1','project/rtl/block_v2'):
        for f in (ROOT/folder).rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts:receipt['inputs'][str(f.relative_to(ROOT))]=sha(f)
    def run(command,log):
        command=list(map(str,command));start=time.time()
        with (args.out/log).open('w') as stream:
            q=subprocess.run(command,cwd=args.out,stdout=stream,stderr=subprocess.STDOUT)
        receipt['commands'].append(dict(command=command,log=log,sha256=sha(args.out/log),returncode=q.returncode,seconds=time.time()-start))
        assert q.returncode==0,(log,q.returncode)
    try:implement(args,run);receipt['passed']=True
    finally:
        receipt['outputs']={str(f.relative_to(args.out)):sha(f) for f in args.out.rglob('*') if f.is_file()}
        receipt['end_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        (args.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
