"""Route all 770 real adapter branches, then assemble exact existing FIXED wires.

Native partial-FIXED routing skipped remaining branches in closed trials. This
compiler instead preserves routed wire opcodes with dbWire.append, and checks
the resulting 514-net physical graph independently. Still adapter-only, not a
frozen six-block base, valid accelerator timing model or two full systems.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter,defaultdict
import csv,datetime,gzip,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_preconnected_upper import groups,audit_geometry
from check_access import check,check_rows

DRIVER=Path(__file__).resolve().parent


def table(path):
    with gzip.open(path,'rt') as f:return list(csv.DictReader(f,delimiter='\t'))


def material_and_indispensability(out,plan,physical):
    branch=table(out/'branch_access.tsv.gz');final=table(out/'whole_access.tsv.gz')
    bypin={h['helper_pin']:g['net'] for g in physical for h in g['endpoints']}
    old_to_new=defaultdict(set);edge_members=defaultdict(set)
    for r in branch:
        if r['kind']=='BTERM':
            pin=r['link'][2:];assert pin in bypin
            old_to_new[r['net']].add(bypin[pin]);edge_members[r['net']].add(pin)
    assert len(old_to_new)==770 and all(len(s)==1 for s in old_to_new.values())
    expected_edges={frozenset(h['helper_pin'] for h in e['endpoints']) for e in plan['physical_edges']}
    assert {frozenset(s) for s in edge_members.values()}==expected_edges and len(expected_edges)==770
    key=lambda r:(r['kind'],r['layer'])+tuple(int(r[k]) for k in ['x0','y0','x1','y1'])
    wanted=Counter((next(iter(old_to_new[r['net']])),)+key(r) for r in branch if r['kind'] in ['WIRE','VIA'])
    final_material=Counter((r['net'],)+key(r) for r in final if r['kind'] in ['WIRE','VIA'])
    bynet=defaultdict(list)
    for r in final:bynet[r['net']].append(r)
    cut=[]
    for g in physical:
        w=g['fixed_conductor']
        if not w:continue
        rect=[round(w[k+'_um']*2000) for k in ['x0','y0','x1','y1']]
        wirekey=('WIRE','metal10')+tuple(rect)
        wanted[(g['net'],)+wirekey]+=1
        found=[r for r in bynet[g['net']] if key(r)==wirekey];assert len(found)==1
        # This is an analysis-only cut of one actual exported rectangle. The
        # implementation, real lower checkpoint and final native DB stay intact.
        remaining=[dict(r) for r in bynet[g['net']] if r is not found[0]]
        q=check_rows(remaining,False)['nets'][g['net']]
        real=[h for h in g['endpoints'] if not h['component'].startswith('SHARED:')]
        assert len(real)==2
        pair={'B:'+h['helper_pin'] for h in real}
        connected=any(pair<=set(ts) for ts in q['terminal_groups'])
        assert not connected and q['terminal_components']==2
        cut.append({'resource':w['resource'],'native_net':g['net'],
                    'original_edge_ids':';'.join(map(str,g['edge_ids'])),
                    'actual_fixed_rectangle_removed_in_analysis_only':True,
                    'real_source_to_sink_connected_without_fixed_rectangle':connected,
                    'terminal_components_without_fixed_rectangle':q['terminal_components']})
    assert wanted==final_material,'Opcode composition changed actual branch or fixed metal/via rectangles'
    assert len(cut)==256
    with (out/'all256_actual_fixed_bridge_cut_checks.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(cut[0]));w.writeheader();w.writerows(cut)
    return {'all_770_actual_branch_pairs_preserved':True,
            'all_actual_branch_WIRE_VIA_multisets_preserved_under_net_rebinding':True,
            'exactly_256_original_actual_FIXED_M10_rectangles_added_to_helper_context':True,
            'all_256_fixed_bridges_indispensable_for_real_source_sink_geometry':True,
            'scope':'Actual native rectangles/via links and analysis-only bridge cuts; not GDS LVS, full base freeze, RTL or STA'}


def one(mode,root):
    out=root/mode;out.mkdir(exist_ok=False)
    rec={'scope':'ALL770_ROUTED_BRANCHES_EXACT_NATIVE_FIXED_COMPOSITION_NOT_COMPLETE_SYSTEM',
         'mode':mode,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'scheduler_job':os.environ['SLURM_JOB_ID'],'native_returncodes':{},
         'base_frozen':False,'base_qualified':False,'full_qualification':False,
         'RC_STA_electrical':'NOT_EXECUTED_ADAPTER_HELPER_NOT_ACCELERATOR_TIMING_MODEL',
         'helper_passive_port_directions':'Routing helper labels are not additional functional drivers; actual driver/sink graph is source-bound by original compiled plan',
         'leaf_selection':'Original R02 unqualified source; not upgraded to newer leaf views',
         'source_SHA':{}}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        old=ROOT/'upper_adaptation_trial/r02';planfile=old/(mode+'_actual_hook_plan.json')
        plan=json.loads(planfile.read_text());source=old/mode/'placed_adapter_NOT_SYSTEM.odb'
        prior=json.loads((old/mode/'execution.json').read_text())
        assert sha(source)==prior['files'][source.name]['sha256'] and sha(planfile)==prior['source_plan_SHA256']
        base=Path(plan['source_lower_checkpoint']);assert sha(base)==plan['source_lower_checkpoint_SHA256']
        api=ROOT/'native_wire_append_api/r02/execution.json';proof=json.loads(api.read_text())
        assert proof['native_returncode']==0 and proof['actual_rectangle_multisets_and_native_FIXED_ROUTED_path_flags_preserved'] and proof['source_unchanged']
        wf=ROOT/'common_integration/r01/C/actual_shared_conductors.json';wires=json.loads(wf.read_text())
        fixed_audit=ROOT/'shared_conductor_audit/r02/execution.json';fa=json.loads(fixed_audit.read_text())
        assert fa['all_256_native_FIXEDS_and_original_net_bindings_verified']
        assert all(sha(Path(p))==s for p,s in fa['source_SHA'].items())
        physical=groups(plan,wires);rc=ROOT/'upper_layer_probe/r01/model/research12.setRC.tcl'
        rec['source_SHA']={str(p):sha(p) for p in [source,planfile,old/mode/'execution.json',base,api,wf,fixed_audit,rc]}
        rec['source_lower_checkpoint_SHA256']=sha(base)
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        rec['actual_edges']=770;rec['actual_hooks']=1540;rec['actual_shared_fixed_resources']=256
        (out/'physical_quotient_plan.json').write_text(json.dumps(physical,indent=2)+'\n');save()
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        obs='proc save_obs {file} {set f [open $file w];foreach ob [[ord::get_db_block] getObstructions] {set r [$ob getBBox];puts $f [list [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]};close $f}'
        lines=[helper.replace('$out/stages.tsv','$out/branch_route_stages.tsv'),
          'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
          'read_db '+tcl(source),'source '+tcl(rc),obs,
          'set b [ord::get_db_block];if {[llength [$b getNets]]!=770 || [llength [$b getBTerms]]!=1540 || [llength [$b getInsts]]} {error "Original full helper count mismatch"}',
          'foreach n [$b getNets] {if {[$n getWire] ne "NULL"} {error "Unexpected original helper wire"}}',
          'fingerprint '+tcl(out/'before_route'),'save_obs '+tcl(out/'before.OBS.tsv'),
          'set_routing_layers -signal metal11-metal12 -clock metal11-metal12',
          'if {![stage global_route_CuGR_all770 {global_route -use_cugr -verbose -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}',
          'if {![stage require_all770_native_guides {set f [open '+tcl(out/'native_guide_inventory.tsv')+' w];puts $f "net\\tguide_count";set count 0;foreach n [$b getNets] {set gs [$n getGuides];if {![llength $gs]} {error "Missing branch guide"};incr count;puts $f "[$n getName]\\t[llength $gs]"};close $f;if {$count!=770} {error "Incomplete original edges"}}]} {close $stages;exit 1}',
          'if {![stage detailed_route_all770 {detailed_route -output_drc '+tcl(out/'branch_route.drc')+' -verbose 1;write_db '+tcl(out/'routed_770_BRANCHES_NOT_SYSTEM.odb')+'}]} {close $stages;exit 1}',
          'fingerprint '+tcl(out/'after_branch_route'),'save_obs '+tcl(out/'after_branch.OBS.tsv'),
          'source '+tcl(DRIVER/'export_access.tcl'),'close $stages']
        script=out/'route_branches.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'branch_access.tsv.gz')
        rec['native_returncodes']['all770_branch_route']=execute(common,script,out/'branch_native.log',env,threads=4);save()
        if rec['native_returncodes']['all770_branch_route']!=0:raise RuntimeError('Full branch routing failed; no composition or full-system claim')
        rec['all_770_branch_geometry']=check(out/'branch_access.tsv.gz',True)
        assert rec['all_770_branch_geometry']['pass'] and rec['all_770_branch_geometry']['checked_nets']==770 and rec['all_770_branch_geometry']['checked_terminals']==1540
        assert all(sha(out/('before_route.'+k+'.tsv'))==sha(out/('after_branch_route.'+k+'.tsv')) for k in ['pins','cells','pdn','die'])
        assert sha(out/'before.OBS.tsv')==sha(out/'after_branch.OBS.tsv')
        lines=[helper.replace('$out/stages.tsv','$out/composition_stages.tsv'),'read_db '+tcl(out/'routed_770_BRANCHES_NOT_SYSTEM.odb'),obs,
          'set b [ord::get_db_block];set m10 [[ord::get_db_tech] findLayer metal10];if {[$m10 getWidth]!=1600} {error "Actual FIXED width differs"}']
        body=[]
        for g in physical:
            body+=['if {[$b findNet '+tcl(g['net'])+'] ne "NULL"} {error "Canonical net name collision"}',
                   'set n [odb::dbNet_create $b '+tcl(g['net'])+'];set olds {}']
            for h in g['endpoints']:
                body+=['set bt [$b findBTerm '+tcl(h['helper_pin'])+'];set old [$bt getNet];if {[llength [$old getBTerms]]>2 || [llength [$old getITerms]] || [$old getWire] eq "NULL"} {error "Unexpected routed old branch"};lappend olds $old;$bt disconnect;$bt connect $n']
            body+=['set nw [odb::dbWire_create $n];foreach old [lsort -unique $olds] {if {[llength [$old getBTerms]] || [llength [$old getITerms]]} {error "Original branch terms not fully rebound"};$nw append [$old getWire];if {[llength [$old getBTerms]]} {error "Append changed original ownership"};odb::dbNet_destroy $old}']
            if any(plan['physical_edges'][i]['clock'] for i in g['edge_ids']):body+=['$n setSigType CLOCK']
            w=g['fixed_conductor']
            if w:
                a=[round(x*2000) for x in w['actual_A_xy_um']];z=[round(x*2000) for x in w['actual_B_xy_um']]
                body+=['set tmp [odb::dbNet_create $b HPY_FIXED_STAGING];set tw [odb::dbWire_create $tmp];set enc [odb::dbWireEncoder];$enc begin $tw;$enc newPath $m10 FIXED;$enc addPoint '+str(a[0])+' '+str(a[1])+';$enc addPoint '+str(z[0])+' '+str(z[1])+';$enc end;$nw append $tw;odb::dbNet_destroy $tmp']
        body+=['if {[llength [$b getNets]]!=514 || [llength [$b getBTerms]]!=1540 || [llength [$b getInsts]]} {error "Final actual graph counts wrong"}']
        lines+=['if {![stage exact_native_opcode_composition {'+'\n'.join(body)+'}]} {catch {write_db '+tcl(out/'failed_composition.odb')+'};close $stages;exit 1}',
          'fingerprint '+tcl(out/'after_composition'),'save_obs '+tcl(out/'after_composition.OBS.tsv'),
          'write_db '+tcl(out/'routed_adapter_NOT_SYSTEM.odb'),'write_def '+tcl(out/'routed_adapter.def'),
          'source '+tcl(DRIVER/'export_access.tcl'),'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),'close $stages']
        script=out/'compose_actual_wires.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_returncodes']['exact_native_composition']=execute(common,script,out/'composition_native.log',env,threads=4);save()
        if rec['native_returncodes']['exact_native_composition']!=0:raise RuntimeError('Native wire composition failed; output retained unqualified')
        rec['all_514_composed_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['exact_hook_and_lower_material_contract']=audit_geometry(out/'whole_access.tsv.gz',physical)
        rec['actual_material_and_fixed_bridge_cut_checks']=material_and_indispensability(out,plan,physical)
        assert sha(out/'before.OBS.tsv')==sha(out/'after_composition.OBS.tsv')
        assert all(sha(out/('before_route.'+k+'.tsv'))==sha(out/('after_composition.'+k+'.tsv')) for k in ['cells','pdn','die'])
        text=(out/'routed_adapter.def').read_text();assert len(re.findall(r'\+\s+FIXED\s+metal10\b',text))==256
        rec['all_256_native_FIXED_paths_preserved']=True
        script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed_adapter_NOT_SYSTEM.odb')+'\nset_routing_layers -signal metal11-metal12 -clock metal11-metal12\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'independent.log',threads=1)
        if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        rec['native_binary_unchanged']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]==rec['actual_OpenROAD_binary_SHA256']
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in rec['source_SHA'].items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return rec


def run(revision):
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    out=ROOT/'upper_branch_composition'/revision;out.mkdir(parents=True,exist_ok=False)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda mode:one(mode,out),['opentpu','llaccel']))
    summary={'scope':'TWO_ALL770_ADAPTER_COMPOSITIONS_NOT_TWO_COMPLETE_SYSTEMS','full_qualification':False,
      'modes':[{k:r.get(k) for k in ['mode','native_returncodes','fresh_DRC_count','actual_failure']} for r in results]}
    (out/'trial_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return 0 if all('actual_failure' not in r and r.get('fresh_DRC_count')==0 and r.get('all_514_composed_geometry',{}).get('pass') and r.get('all_256_native_FIXED_paths_preserved') and r.get('actual_material_and_fixed_bridge_cut_checks',{}).get('all_256_fixed_bridges_indispensable_for_real_source_sink_geometry') and r.get('native_binary_unchanged') and r['all_closed_sources_unchanged'] for r in results) else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
