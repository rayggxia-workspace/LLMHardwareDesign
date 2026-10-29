"""Route the exact adapter graph with its existing FIXED M10 edges present.

This is an unqualified routing-context experiment, not a new topology, frozen
base, complete accelerator, STA model or proof of a pin-XY benefit.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, Counter
import csv, datetime, gzip, json, os, re, sys, traceback
from run_exports import ROOT, sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER = Path(__file__).resolve().parent


def groups(plan, conductors):
    edges = plan['physical_edges']
    assert len(edges) == 770
    shared = defaultdict(list)
    for edge in edges:
        for h in edge['endpoints']:
            if h['component'].startswith('SHARED:'):
                shared[h['component']].append((edge, h))
    assert len(shared) == 256
    used = set(); result = []
    for wire in conductors:
        pair = shared[wire['component']]
        assert len(pair) == 2 and {h['shared_end'] for e, h in pair} == {'A', 'B'}
        assert len({h['net'] for e, h in pair}) == 1
        ids = sorted(e['edge_id'] for e, h in pair)
        assert not used.intersection(ids); used.update(ids)
        endpoints = [h for e, _ in pair for h in e['endpoints']]
        assert len({h['helper_pin'] for h in endpoints}) == 4
        for e, h in pair:
            xy = wire['actual_'+h['shared_end']+'_xy_um']
            box = [round((xy[0]-.4)*2000), round((xy[1]-.4)*2000),
                   round((xy[0]+.4)*2000), round((xy[1]+.4)*2000)]
            assert box == h['base_pin_box_dbu']
        result.append({'net': pair[0][1]['net'], 'edge_ids': ids,
                       'endpoints': endpoints, 'fixed_conductor': wire})
    for edge in edges:
        if edge['edge_id'] not in used:
            result.append({'net': 'adapter_edge_'+str(edge['edge_id']),
                           'edge_ids': [edge['edge_id']], 'endpoints': edge['endpoints'],
                           'fixed_conductor': None})
    assert len(result) == 514
    assert sorted(i for g in result for i in g['edge_ids']) == list(range(770))
    assert Counter(len(g['endpoints']) for g in result) == {4: 256, 2: 258}
    assert len({h['helper_pin'] for g in result for h in g['endpoints']}) == 1540
    assert len({g['net'] for g in result}) == 514
    return result


def covered(rect, boxes):
    """Exact integer rectangle-union coverage, not bbox-only containment."""
    x0,y0,x1,y1 = rect
    clipped = [(max(x0,a),max(y0,b),min(x1,c),min(y1,d)) for a,b,c,d in boxes]
    clipped = [q for q in clipped if q[0]<q[2] and q[1]<q[3]]
    xs = sorted({x0,x1} | {q[i] for q in clipped for i in (0,2)})
    for a,b in zip(xs,xs[1:]):
        ys = sorted((q[1],q[3]) for q in clipped if q[0]<=a and q[2]>=b)
        end = y0
        for c,d in ys:
            if c>end: return False
            end=max(end,d)
        if end<y1: return False
    return True


def audit_geometry(path, physical):
    with gzip.open(path,'rt') as f: rows=list(csv.DictReader(f,delimiter='\t'))
    bynet=defaultdict(list)
    for r in rows: bynet[r['net']].append(r)
    assert set(bynet)=={g['net'] for g in physical}
    seen=set(); fixed_count=0
    for g in physical:
        expected={h['helper_pin']:h['base_pin_box_dbu'] for h in g['endpoints']}
        terms={}; m10=[]; allowed=list(expected.values())
        wire=g['fixed_conductor']
        rect=None
        if wire:
            rect=[round(wire[k+'_um']*2000) for k in ['x0','y0','x1','y1']]
            allowed.append(rect)
        for r in bynet[g['net']]:
            box=[int(r[k]) for k in ['x0','y0','x1','y1']]
            assert r['kind']!='UNROUTED'
            if r['kind']=='BTERM':
                name=r['link'][2:]; assert name not in terms
                assert name in expected and box==expected[name] and r['layer']=='metal10'
                terms[name]=box;seen.add(name)
            if r['layer']=='metal10':
                assert covered(box,allowed),('M10 material outside original fixed wires/hooks',g['net'],r)
                m10.append(box)
            else: assert r['layer'] in ['metal11','metal12','via10','via11'],r
        assert terms==expected
        if rect:
            assert covered(rect,m10),('Original FIXED M10 material lost',g['net'])
            fixed_count+=1
    assert len(seen)==1540 and fixed_count==256
    return {'all_770_original_edges_accounted_for':True,'actual_native_nets':514,
            'exact_original_hook_boxes':1540,'original_fixed_M10_unions_covered':256,
            'all_M10_contained_in_original_hook_or_fixed_conductor_material':True,
            'no_added_M1_M9_or_cut1_cut9':True,
            'scope':'Exact integer union/material containment; not normalized full-base freeze, GDS LVS or RC/STA'}


def fixed_commands(g):
    w=g['fixed_conductor'];assert w
    a=[round(q*2000) for q in w['actual_A_xy_um']];z=[round(q*2000) for q in w['actual_B_xy_um']]
    return ['set n [$b findNet '+tcl(g['net'])+'];if {[$n getWire] ne "NULL"} {error "Unexpected wire before actual FIXED restoration"}',
            'set w [odb::dbWire_create $n];set enc [odb::dbWireEncoder];$enc begin $w;$enc newPath $m10 FIXED;$enc addPoint '+str(a[0])+' '+str(a[1])+';$enc addPoint '+str(z[0])+' '+str(z[1])+';$enc end']


def one(mode,root,conductors,proof,profile):
    old=ROOT/'upper_adaptation_trial/r02'
    planfile=old/(mode+'_actual_hook_plan.json');plan=json.loads(planfile.read_text())
    source=old/mode/'placed_adapter_NOT_SYSTEM.odb'
    prior=json.loads((old/mode/'execution.json').read_text())
    assert sha(source)==prior['files'][source.name]['sha256']
    assert sha(planfile)==prior['source_plan_SHA256']
    assert sha(Path(plan['source_lower_checkpoint']))==plan['source_lower_checkpoint_SHA256']
    assert proof['all_256_native_FIXEDS_and_original_net_bindings_verified']
    assert all(sha(Path(p))==s for p,s in proof['source_SHA'].items())
    assert proof['source_SHA'][plan['source_lower_checkpoint']]==plan['source_lower_checkpoint_SHA256']
    physical=groups(plan,conductors)
    out=root/mode;out.mkdir(exist_ok=False)
    rc=ROOT/'upper_layer_probe/r01/model/research12.setRC.tcl'
    inputs={str(p):sha(p) for p in [source,planfile,old/mode/'execution.json',rc,
        ROOT/'common_integration/r01/C/actual_shared_conductors.json',
        ROOT/'shared_conductor_audit/r02/execution.json']}
    rec={'scope':'ALL_EDGES_WITH_ACTUAL_FIXED_M10_CONNECTIVITY_UNQUALIFIED_ROUTING_CONTEXT',
         'mode':mode,'source_SHA':inputs,'source_lower_checkpoint_SHA256':plan['source_lower_checkpoint_SHA256'],
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,
         'base_frozen':False,'complete_system':False,'RC_STA_electrical':'NOT_EXECUTED',
         'original_edges':770,'physical_quotient_nets':514,'same_actual_hook_boxes':1540,
         'same_actual_fixed_M10_conductors':256,'architecture_or_topology_change':False}
    rec['guide_search_profile']=profile
    detach=profile.startswith('detach_for_')
    rec['temporary_guide_only_wire_detachment']=detach
    rec['native_global_search_engine']='CuGR' if 'cugr' in profile else 'FastRoute'
    rec['guide_model_scope']='Only helper in-memory guide search may omit the already verified fixed fragments; original lower source immutable, exact native FIXED fragments restored before DRT and every terminal/material/DRC check remains required.'
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    (out/'physical_quotient_plan.json').write_text(json.dumps(physical,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
            '--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        lines=[helper,'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
               'read_db '+tcl(source),'source '+tcl(rc),
               'set b [ord::get_db_block];set m10 [[ord::get_db_tech] findLayer metal10]',
               'proc save_obs {file} {set f [open $file w];foreach ob [[ord::get_db_block] getObstructions] {set r [$ob getBBox];puts $f [list [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]};close $f}',
               'save_obs '+tcl(out/'before.OBS.tsv')]
        for g in physical:
            lines+=['if {[$b findNet '+tcl(g['net'])+'] ne "NULL"} {error "Quotient name collision"}',
                    'set n [odb::dbNet_create $b '+tcl(g['net'])+'];set olds {}']
            for h in g['endpoints']:
                lines+=['set bt [$b findBTerm '+tcl(h['helper_pin'])+'];lappend olds [$bt getNet];$bt disconnect;$bt connect $n']
            lines+=['foreach old [lsort -unique $olds] {if {[llength [$old getBTerms]]!=0 || [llength [$old getITerms]]!=0 || [$old getWire] ne "NULL"} {error "Unexpected residual old adapter net"};odb::dbNet_destroy $old}']
            if any(plan['physical_edges'][i]['clock'] for i in g['edge_ids']): lines+=['$n setSigType CLOCK']
            w=g['fixed_conductor']
            if w:
                lines+=fixed_commands(g)
        lines+=['if {[llength [$b getNets]]!=514 || [llength [$b getBTerms]]!=1540 || [llength [$b getInsts]]!=0} {error "Quotient native object count mismatch"}',
          'write_db '+tcl(out/'preconnected_adapter_NOT_SYSTEM.odb'),
          'write_def '+tcl(out/'preconnected_adapter.def'),
          'fingerprint '+tcl(out/'before'),
          'set_routing_layers -signal metal11-metal12 -clock metal11-metal12']
        if detach:
            lines+=['if {![stage guide_only_detach_fixed_fragments {set removed 0;foreach n [$b getNets] {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w;incr removed}};if {$removed!=256} {error "Unexpected detached fragment count"}}]} {close $stages;exit 1}']
        engine=' -use_cugr -verbose' if 'cugr' in profile else ''
        lines+=['set global_ok [stage global_route {global_route'+engine+' -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]']
        if detach:
            restore=[cmd for g in physical if g['fixed_conductor'] for cmd in fixed_commands(g)]
            lines+=['if {![stage restore_exact_FIXED_before_DRT {'+'\n'.join(restore)+'\nwrite_db '+tcl(out/'restored_FIXED_before_DRT.odb')+';write_def '+tcl(out/'restored_FIXED_before_DRT.def')+'}]} {close $stages;exit 1}',
                    'if {$global_ok} {if {![stage require_all514_native_guides {set f [open '+tcl(out/'native_guide_inventory.tsv')+' w];puts $f "net\\tguide_count";set count 0;foreach n [$b getNets] {set gs [$n getGuides];if {![llength $gs]} {error "Missing actual guide on quotient net"};puts $f "[$n getName]\\t[llength $gs]";incr count};close $f;if {$count!=514} {error "Missing quotient net"}}]} {close $stages;exit 1}}']
        lines+=['if {!$global_ok} {catch {write_db '+tcl(out/'failed_global.odb')+'};catch {write_def '+tcl(out/'failed_global.def')+'};close $stages;exit 1}',
          'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1;write_db '+tcl(out/'routed_adapter_NOT_SYSTEM.odb')+';write_def '+tcl(out/'routed_adapter.def')+'}]} {close $stages;exit 1}',
          'fingerprint '+tcl(out/'after'),'save_obs '+tcl(out/'after.OBS.tsv'),
          'source '+tcl(DRIVER/'export_access.tcl'),'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),'close $stages']
        script=out/'route.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_route_returncode']=execute(common,script,out/'native.log',env,threads=4)
        if (out/'preconnected_adapter.def').exists():
            text=(out/'preconnected_adapter.def').read_text()
            assert len(re.findall(r'\+\s+FIXED\s+metal10\b',text))==256
            rec['actual_native_quotient_and_256_FIXED_context_created']=True
        if (out/'routed_adapter_NOT_SYSTEM.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed_adapter_NOT_SYSTEM.odb')+'\nset_routing_layers -signal metal11-metal12 -clock metal11-metal12\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['independent_DRC_returncode']=execute(common,script,out/'independent.log',threads=1)
            if rec['independent_DRC_returncode']==0:
                rec['independent_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():
            rec['actual_all_net_geometry']=check(out/'whole_access.tsv.gz',True)
            rec['actual_geometry_contract']=audit_geometry(out/'whole_access.tsv.gz',physical)
            assert all(sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','die','OBS'])
            rec['all_original_hook_shapes_die_and_OBS_unchanged']=True
        # The actual DEF FIXED attributes are checked independently of rectangle
        # coverage; a router changing path status is a retained failure.
        deffile=out/'routed_adapter.def'
        if deffile.exists():
            text=deffile.read_text(); statements=re.findall(r'^\s*-\s+(\S+)\s+(.*?);',text,re.M|re.S)
            native={n:s for n,s in statements if n in {g['net'] for g in physical if g['fixed_conductor']}}
            assert len(native)==256
            assert all(re.search(r'\+\s+FIXED\s+metal10\b',s) for s in native.values())
            rec['all256_native_FIXED_attributes_retained']=True
    except Exception: rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return rec


def run(revision,profile='fixed_context'):
    assert profile in ['fixed_context','detach_for_guides_restore_before_DRT','detach_for_cugr_guides_restore_before_DRT']
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    out=ROOT/'upper_preconnected'/revision;out.mkdir(parents=True,exist_ok=False)
    wires=json.loads((ROOT/'common_integration/r01/C/actual_shared_conductors.json').read_text())
    proof=json.loads((ROOT/'shared_conductor_audit/r02/execution.json').read_text())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda mode:one(mode,out,wires,proof,profile),['opentpu','llaccel']))
    assert len({r['source_lower_checkpoint_SHA256'] for r in results})==1
    summary={'scope':'UNQUALIFIED_FULL_ADAPTER_PRECONNECTED_CONTEXT_NOT_TWO_SYSTEMS',
             'same_lower_input_SHA256':results[0]['source_lower_checkpoint_SHA256'],
             'full_qualification':False,'modes':[{k:r.get(k) for k in ['mode','native_route_returncode','independent_DRC_count','all256_native_FIXED_attributes_retained','actual_failure']} for r in results]}
    (out/'trial_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return 0 if all(r.get('native_route_returncode')==0 and r.get('independent_DRC_count')==0 and r.get('actual_all_net_geometry',{}).get('pass') and r.get('all256_native_FIXED_attributes_retained') and r['all_closed_sources_unchanged'] for r in results) else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
