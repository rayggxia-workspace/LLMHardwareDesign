"""Route every compiled upper-adaptation edge over actual common M10 hooks.

An explicitly UNQUALIFIED adapter-only integration trial. The lower checkpoint
is real and immutable but its private routes/leaf qualifications are not closed.
No complete-system, qualified-freeze, full RC/STA or manufacturing claim.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter,defaultdict
import csv,datetime,gzip,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def table(path):
    with path.open() as f:return list(csv.DictReader(f,delimiter='\t'))


def prepare(out):
    base=ROOT/'common_integration/r01/C';odb=base/'fixed_prewires_NOT_FROZEN.odb'
    audited=ROOT/'shared_conductor_audit/r02/execution.json';proof=json.loads(audited.read_text())
    assert proof['all_256_native_FIXEDS_and_original_net_bindings_verified'] and proof['all_closed_source_files_unchanged']
    assert sha(odb)==proof['source_SHA'][str(odb)]
    contract=ROOT/'inputs/common-topology-r02';pads=json.loads((contract/'access_pads.json').read_text())
    components=json.loads((contract/'components.json').read_text());wires=json.loads((contract/'component_wire_names.json').read_text())
    topology=json.loads((contract/'topology_proof.json').read_text());assert topology['all_original_signal_pins']==24767 and not topology['frozen']
    boxes=table(base/'before_route.pins.tsv');bypin=defaultdict(list)
    for q in boxes:bypin[q['pin']].append(q)
    hooks={};allboxes=[];aliases={}
    for component,pad in pads.items():
        rows=sorted(bypin[pad],key=lambda q:(int(q['y0']),int(q['x0'])))
        shared=component.startswith('SHARED:');assert len(rows)==(2 if shared else 1)
        for index,q in enumerate(rows):
            assert q['layer']=='metal10'
            if q['net']!=wires[component]:
                # Verilog clock input aliases become canonical native net names.
                # Accept only the two exact, sole-TOP_IO clock components.
                ts=components[component];design=component.split(':')[0]
                assert component==design+':2:external_clock' and design in ['opentpu','llaccel']
                assert len(ts)==1 and ts[0]['kind']=='TOP_IO' and ts[0]['pin']=='clk' and ts[0]['direction']=='input'
                assert q['net']==design+'__clk'
                aliases[component]={'compiled_wire':wires[component],'actual_native_clock_alias':q['net']}
            box=[int(q[k]) for k in ['x0','y0','x1','y1']];assert box[2]-box[0]==box[3]-box[1]==1600
            hook=dict(component=component,pad=pad,net=q['net'],base_pin_box_dbu=box,shared_end=('A' if index==0 else 'B') if shared else None)
            hooks[component,hook['shared_end']]=hook;allboxes.append(tuple(box))
    assert len(hooks)==len(set(allboxes))==1541
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';model=json.loads((tech.parent/'model.json').read_text())
    assert model['original_M1_M10_and_via1_via9_layer_blocks_identical'] and sha(tech)==model['files'][tech.name]['sha256']
    rc=tech.parent/'research12.setRC.tcl';assert sha(rc)==model['files'][rc.name]['sha256']
    inputs={str(p):sha(p) for p in [odb,audited,tech,rc,tech.parent/'model.json',base/'before_route.pins.tsv',base/'actual_M10_obstacles.tsv']+list(p for p in contract.iterdir() if p.is_file())}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    script=out/'base_boundary.tcl';script.write_text('\n'.join(['read_db '+tcl(odb),
      'set b [ord::get_db_block];set tech [ord::get_db_tech];set f [open '+tcl(out/'base_boundary.tsv')+' w]',
      'set d [$b getDieArea];puts $f [join [list DIE [$d xMin] [$d yMin] [$d xMax] [$d yMax] [$b getDbUnitsPerMicron]] "\\t"]',
      'set found 0;foreach via [$tech getVias] {if {[$via getName] eq "via10_0"} {incr found;foreach box [$via getBoxes] {puts $f [join [list VIA10 [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]] "\\t"]}}};if {$found!=1} {error "Actual boundary via10_0 missing/ambiguous"};close $f'])+'\n')
    assert execute(common,script,out/'base_boundary.log',threads=1)==0
    frame=None;via=[]
    for line in (out/'base_boundary.tsv').read_text().splitlines():
        row=line.split('\t')
        if row[0]=='DIE':frame=list(map(int,row[1:5]));assert int(row[5])==2000
        else:via.append({'layer':row[1],'box_dbu':list(map(int,row[2:]))})
    lower=[q for q in via if q['layer']=='metal10'];assert len(lower)==1 and lower[0]['box_dbu']==[-800,-800,800,800]
    plans={}
    for mode in ['opentpu','llaccel']:
        source_edges=json.loads((contract/(mode+'_adaptation_edges.json')).read_text());assert len(source_edges)==770
        used=Counter();physical=[]
        for i,edge in enumerate(source_edges):
            reverse=('INACTIVE physically driven constant clock'==edge['connection'])
            source_side='b' if reverse else 'a';sink_side='a' if reverse else 'b'
            for side,is_source in [(source_side,True),(sink_side,False)]:
                comp=edge['component_'+side]
                if comp.startswith('SHARED:'):continue
                def driver(t):return (t['kind']=='TOP_IO' and t['direction']=='input') or (t['kind']!='TOP_IO' and t['direction']=='output')
                assert any(driver(t)==is_source for t in components[comp]),(mode,comp,'Actual compiled source/sink role differs')
            points=[]
            for side in ['a','b']:
                comp=edge['component_'+side];end=('B' if side=='a' else 'A') if comp.startswith('SHARED:') else None
                h=hooks[comp,end];used[comp,end]+=1;box=h['base_pin_box_dbu'];cx=(box[0]+box[2])//2;cy=(box[1]+box[3])//2
                translated=[cx-800,cy-800,cx+800,cy+800];assert translated==box
                points.append(dict(h,helper_pin=('src' if side==source_side else 'dst')+'['+str(i)+']',proposed_via10_M10_landing_dbu=translated))
            physical.append(dict(edge_id=i,connection=edge['connection'],clock='clock' in edge['connection'].lower(),endpoints=points))
        assert len(used)==1540 and set(used.values())=={1}
        unused=set(hooks)-set(used);assert len(unused)==1
        component,end=next(iter(unused));inactive='llaccel' if mode=='opentpu' else 'opentpu'
        assert component.startswith(inactive+':') and component.endswith(':external_clock') and end is None
        assert len(components[component])==1 and components[component][0]['kind']=='TOP_IO'
        shared={c for c,end in used if c.startswith('SHARED:')};assert len(shared)==256
        assert all(used[c,'A']==used[c,'B']==1 for c in shared)
        plan={'scope':'ALL_770_ADAPTER_EDGES_OVER_ACTUAL_HOOKS_NOT_COMPLETE_SYSTEM',
          'mode':mode,'edge_count':770,'used_actual_hook_boxes':1540,'unused_inactive_external_clock_component':component,
          'all256_shared_resources_use_distinct_A_B_endpoints':True,'source_lower_checkpoint':str(odb),
          'source_lower_checkpoint_SHA256':inputs[str(odb)],'base_qualified':False,'base_frozen':False,
          'lower_M10_default_via10_footprint_coverage':'ALL_1540_PLANNED_LANDINGS_EXACTLY_EXISTING_BASE_PINS; actual routed landings must still be checked',
          'research_technology_SHA256':inputs[str(tech)],'frame_dbu':frame,'native_via10_template_boxes':via,
          'physical_edges':physical,'full_qualification':False}
        (out/(mode+'_actual_hook_plan.json')).write_text(json.dumps(plan,indent=2)+'\n');plans[mode]=plan
    rec={'scope':'REAL_PARTIAL_BASE_AND_ALL_ADAPTER_HOOK_PREPARATION_NOT_FROZEN_SYSTEM',
      'source_SHA':inputs,'actual_hook_boxes':1541,'same_real_lower_checkpoint_for_both_modes':True,
      'native_via10_M10_landing_size_dbu':[1600,1600],'per_mode_edges':770,'native_clock_net_aliases':aliases,'full_qualification':False}
    (out/'preparation.json').write_text(json.dumps(rec,indent=2)+'\n')
    return plans,rec,tech


def one(mode,plan,root,tech):
    out=root/mode;out.mkdir(parents=True,exist_ok=False)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    rec={'scope':'ACTUAL_ALL_770_UPPER_ADAPTER_EDGE_TRIAL_NOT_TWO_COMPLETE_SYSTEMS',
      'mode':mode,'source_lower_checkpoint_SHA256':plan['source_lower_checkpoint_SHA256'],
      'source_plan_SHA256':sha(root/(mode+'_actual_hook_plan.json')),'base_qualified':False,'base_frozen':False,
      'complete_system_function_and_full_original_pin_physical_connectivity':'NOT_VERIFIED_LOWER_BASE_ROUTE_AND_LEAF_GATES_INCOMPLETE',
      'RC_STA_electrical':'NOT_EXECUTED_ROUTING_ONLY_NO_ZERO_CAP_STUB_OR_TIMING_PASS_CLAIM',
      'technology':'RESEARCH_EXTRAPOLATION_NOT_MANUFACTURING_QUALIFIED','full_qualification':False,
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID']}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    try:
        # Helper port driver/load roles follow the compiled real graph (including
        # reversed inactive-clock edge order). This is not accelerator RTL/STA.
        (out/'routing_helper.v').write_text('module upper_adapter_trial(input [769:0] src, output [769:0] dst); assign dst=src; endmodule\n')
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        frame=' '.join(str(q/2000.) for q in plan['frame_dbu'])
        lines=[helper,'read_lef '+tcl(tech),
          'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
          'read_verilog '+tcl(out/'routing_helper.v'),'link_design upper_adapter_trial',
          'initialize_floorplan -die_area {'+frame+'} -core_area {'+frame+'} -site FreePDK45_38x28_10R_NP_162NW_34O','make_tracks',
          'source '+tcl(tech.parent/'research12.setRC.tcl'),
          'set b [ord::get_db_block];if {[llength [$b getInsts]]!=0} {error "Adapter helper must add no FEOL instances"};set m10 [[ord::get_db_tech] findLayer metal10]']
        for edge in plan['physical_edges']:
            for h in edge['endpoints']:
                box=h['base_pin_box_dbu'];name=h['helper_pin']
                lines.append('set bt [$b findBTerm '+tcl(name)+'];if {$bt eq "NULL"} {error "Missing actual edge terminal"};set bp [odb::dbBPin_create $bt];$bp setPlacementStatus FIRM;odb::dbBox_create $bp $m10 '+' '.join(map(str,box)))
                if edge['clock']:lines.append('$bt setSigType CLOCK;[$bt getNet] setSigType CLOCK')
        # Real base PG/OBS constraints at M10 are supplied as such, never as
        # fabricated free space. Real shared signal material is not foreign OBS.
        for q in table(ROOT/'common_integration/r01/C/actual_M10_obstacles.tsv'):
            lines.append('odb::dbObstruction_create $b $m10 '+' '.join(str(int(q[k])) for k in ['x0','y0','x1','y1']))
        lines+=['write_db '+tcl(out/'placed_adapter_NOT_SYSTEM.odb'),
          'set_routing_layers -signal metal11-metal12 -clock metal11-metal12',
          'if {![stage global_route {global_route -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}',
          'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1;write_db '+tcl(out/'routed_adapter_NOT_SYSTEM.odb')+';write_def '+tcl(out/'routed_adapter.def')+'}]} {close $stages;exit 1}',
          'source '+tcl(DRIVER/'export_access.tcl'),'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),'close $stages']
        script=out/'route.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_route_returncode']=execute(common,script,out/'native.log',env,threads=4)
        if (out/'routed_adapter_NOT_SYSTEM.odb').exists():
            fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed_adapter_NOT_SYSTEM.odb')+'\nset_routing_layers -signal metal11-metal12 -clock metal11-metal12\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['independent_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
            if rec['independent_DRC_returncode']==0:rec['independent_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():
            rec['all_edge_signal_clock_geometry']=check(out/'whole_access.tsv.gz',True)
            expected={h['helper_pin']:h for e in plan['physical_edges'] for h in e['endpoints']};native_terms={};net_edges=defaultdict(set);m10=0;vias=defaultdict(set);forbidden=[]
            with gzip.open(out/'whole_access.tsv.gz','rt') as f:
                records=list(csv.DictReader(f,delimiter='\t'))
            for q in records:
                if q['kind']=='BTERM':
                    pin=q['link'][2:];assert pin not in native_terms and pin in expected
                    assert [int(q[k]) for k in ['x0','y0','x1','y1']]==expected[pin]['base_pin_box_dbu'] and q['layer']=='metal10'
                    native_terms[pin]=q;net_edges[q['net']].add(int(re.search(r'\[(\d+)\]',pin).group(1)))
            assert set(native_terms)==set(expected) and len(net_edges)==770 and all(len(s)==1 for s in net_edges.values())
            for q in records:
                edge=next(iter(net_edges[q['net']]));boxes=[h['base_pin_box_dbu'] for h in plan['physical_edges'][edge]['endpoints']]
                b=[int(q[k]) for k in ['x0','y0','x1','y1']]
                if q['layer']=='metal10':
                    assert any(a[0]<=b[0] and a[1]<=b[1] and a[2]>=b[2] and a[3]>=b[3] for a in boxes),('New M10 footprint outside real frozen-hook material',q)
                    m10+=1
                elif q['layer'] not in ['metal11','metal12','via10','via11']:forbidden.append(q)
                if q['kind']=='VIA' and q['layer'] in ['via10','via11']:vias[q['layer']].add((q['net'],q['link']))
            assert not forbidden,'Unexpected added M1-M9/cut1-cut9 or unsupported geometry'
            rec['actual_770_native_edge_terminal_bijection']=True
            rec['all_actual_overlay_M10_material_contained_in_existing_base_hook_rectangles']=True
            rec['new_material_below_M10_or_original_cut1_cut9_count']=0
            rec['observed_M10_geometry_rows_with_duplicates']=m10
            rec['actual_via_definition_instances']={k:len(v) for k,v in vias.items()}
            rec['same_lower_material_proof_scope']='Immutable real partial base input plus exact containment of every overlay M10 box; not a qualified frozen base or completed full-system composition/LVS.'
    except Exception:
        rec['actual_failure']=traceback.format_exc()
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return rec


def run(revision):
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    out=ROOT/'upper_adaptation_trial'/revision;out.mkdir(parents=True,exist_ok=False)
    try:
        plans,prep,tech=prepare(out)
    except Exception:
        failure={'scope':'ALL_EDGE_UPPER_PREPARATION_FAILED_NO_COMPLETE_SYSTEM_OR_ROUTE_CLAIM',
          'actual_failure':traceback.format_exc(),'full_qualification':False,'scheduler_job':os.environ['SLURM_JOB_ID'],
          'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip()}
        (out/'preparation_failure.json').write_text(json.dumps(failure,indent=2)+'\n');return 1
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda mode:one(mode,plans[mode],out,tech),['opentpu','llaccel']))
    assert results[0]['source_lower_checkpoint_SHA256']==results[1]['source_lower_checkpoint_SHA256']
    rec={'scope':'TWO_ALL_EDGE_ADAPTER_ONLY_TRIALS_NOT_TWO_COMPLETE_FUNCTIONAL_SYSTEMS',
      'same_real_partial_lower_input_for_both_modes':True,'source_lower_checkpoint_SHA256':results[0]['source_lower_checkpoint_SHA256'],
      'all_preparation_sources_unchanged':all(sha(Path(k))==v for k,v in prep['source_SHA'].items()),
      'modes':[{k:r.get(k) for k in ['mode','native_route_returncode','independent_DRC_count','actual_770_native_edge_terminal_bijection','all_actual_overlay_M10_material_contained_in_existing_base_hook_rectangles','actual_failure']} for r in results],
      'full_qualification':False,'qualified_common_base':False,'two_complete_M11_M12_systems':False}
    (out/'trial_summary.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec['all_preparation_sources_unchanged'] and all(r.get('native_route_returncode')==0 and r.get('independent_DRC_count')==0 and r.get('actual_770_native_edge_terminal_bijection') and r.get('all_actual_overlay_M10_material_contained_in_existing_base_hook_rectangles') and r.get('all_edge_signal_clock_geometry',{}).get('pass') for r in results) else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
