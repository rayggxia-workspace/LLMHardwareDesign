"""Reuse the actual six-resource checkpoint with a distinct native CuGR search.

Leave the long original FastRoute job intact. No new placement, PDN, hook,
topology, budget, leaf model or physical rule; still an unqualified lower trial.
"""
from pathlib import Path
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_escape_fixture import execute
from run_parent_trial import tcl
from run_common_integration import SHARED_SNAPSHOT,verify_graph
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision,source_kind='fixed_partial'):
    assert source_kind in ['fixed_partial','closed_CuGR_global_r01']
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    source=ROOT/'common_integration/r01/C';odb=source/'fixed_prewires_NOT_FROZEN.odb'
    audit=ROOT/'shared_conductor_audit/r02/execution.json';proof=json.loads(audit.read_text())
    assert proof['all_256_native_FIXEDS_and_original_net_bindings_verified']
    assert all(sha(Path(p))==s for p,s in proof['source_SHA'].items())
    assert sha(odb)==proof['source_SHA'][str(odb)]
    shared=json.loads((source/'actual_shared_conductors.json').read_text());assert len(shared)==256
    original=source/'lower_route.tcl'
    libs=[line for line in original.read_text().splitlines() if line.startswith('read_liberty ')]
    assert len(libs)==7
    inputs={str(p):sha(p) for p in [odb,audit,original,source/'actual_shared_conductors.json',source/'before.shared.tsv']+list(source.glob('p126_*.lib'))}
    partial_odb=odb
    if source_kind=='closed_CuGR_global_r01':
        closed=ROOT/'common_lower_resume/r01';previous=json.loads((closed/'execution.json').read_text())
        assert previous.get('completed_utc') and previous['all_closed_sources_unchanged']
        assert previous['native_stage_status']['lower_global_route_CuGR']=='EXECUTED'
        assert previous['native_stage_status']['lower_detailed_route']=='FAIL'
        assert 'DRT-0302' in (closed/'native.log').read_text()
        odb=closed/'global.odb';guide=closed/'route.guide'
        for p in [odb,guide]:assert sha(p)==previous['files'][p.name]['sha256']
        inputs.update({str(p):sha(p) for p in [odb,guide,closed/'execution.json',closed/'native.log']})
    out=ROOT/'common_lower_resume'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_SIX_RESOURCE_PRIVATE_LOWER_ROUTE_CUGR_NOT_FROZEN_BASE',
         'source_SHA':inputs,'source_partial_lower_SHA256':sha(partial_odb),
         'actual_routing_checkpoint_SHA256':sha(odb),'source_kind':source_kind,
         'global_route_reexecuted':source_kind=='fixed_partial',
         'construction_shared_BPin_container_fix':source_kind=='closed_CuGR_global_r01',
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'native_global_search_engine':'CuGR; original FastRoute92855 left running unchanged',
         'allowed_layers':'Same original parent: signal M2-M10; clock M4-M10',
         'same_resources_placement_PDN_hooks_256_fixed_conductors_and_preconnect_topology':True,
         'leaf_sources':'Original R02 unqualified selection; not upgraded to latest 658/M6/SYSTEM views',
         'frozen':False,'qualified':False,'full_qualification':False,
         'RC_STA_electrical':'NOT_EXECUTED_ROUTING_ONLY','two_complete_functions':'NOT_IMPLEMENTED'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        helper=(DRIVER/'parent_trial.tcl').read_text().split('if {![stage load {',1)[0]
        lines=[helper,SHARED_SNAPSHOT,'set common_shared_pads {'+' '.join(w['construction_pad'] for w in shared)+'}']+libs
        lines+=['read_db '+tcl(odb)]
        if source_kind=='closed_CuGR_global_r01':
            lines+=['parent_contract '+tcl(out/'before_BPin_container_fix'),
              'if {![stage shared_construction_BPin_containers {set b [ord::get_db_block];set count 0;foreach pad $common_shared_pads {set bt [$b findBTerm $pad];if {$bt eq "NULL"} {error "Missing original construction pad"};set bps [$bt getBPins];if {[llength $bps]!=2} {error "Not the exact original two-BPin case"};set keep [lindex $bps 0];set drop [lindex $bps 1];if {[llength [$keep getBoxes]]!=1 || [llength [$drop getBoxes]]!=1} {error "Unexpected original boxes"};set box [lindex [$drop getBoxes] 0];odb::dbBox_create $keep [$box getTechLayer] [$box xMin] [$box yMin] [$box xMax] [$box yMax];odb::dbBPin_destroy $drop;if {[llength [$bt getBPins]]!=1 || [llength [$keep getBoxes]]!=2} {error "BPin regrouping failed"};incr count};if {$count!=256} {error "Incomplete shared pad coverage"}}]} {close $stages;exit 1}']
        lines+=['common_shared_snapshot '+tcl(out/'before.shared.tsv'),
          'parent_contract '+tcl(out/'before_route'),
          'set_routing_layers -signal metal2-metal10 -clock metal4-metal10']
        if source_kind=='fixed_partial':
            lines+=['if {![stage lower_global_route_CuGR {global_route -use_cugr -verbose -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}',
                    'write_db '+tcl(out/'global.odb')]
        else:
            lines+=['if {![stage read_closed_original_CuGR_guides {read_guides '+tcl(guide)+'}]} {close $stages;exit 1}',
                    'write_db '+tcl(out/'regrouped_BPin_NOT_FROZEN.odb'),
                    'write_def '+tcl(out/'regrouped_BPin.def')]
        lines+=[
          'if {![stage lower_detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1;write_db '+tcl(out/'routed_NOT_FROZEN.odb')+';write_def '+tcl(out/'routed.def')+'}]} {close $stages;exit 1}',
          'common_shared_snapshot '+tcl(out/'after.shared.tsv'),'parent_contract '+tcl(out/'after_route'),
          'source '+tcl(DRIVER/'export_access.tcl'),
          'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),
          'stage final_VDD {check_power_grid -net VDD -error_file '+tcl(out/'final_VDD.rpt')+'}',
          'stage final_VSS {check_power_grid -net VSS -error_file '+tcl(out/'final_VSS.rpt')+'}','close $stages']
        script=out/'lower_route.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_PARENT_OUT='+str(out)+',PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_route_returncode']=execute(common,script,out/'native.log',env,threads=8);save()
        if (out/'before_BPin_container_fix.pins.tsv').exists() and (out/'before_route.pins.tsv').exists():
            rec['all_flat_pin_geometry_PG_instances_unchanged_by_BPin_regrouping']={k:sha(out/('before_BPin_container_fix.'+k+'.tsv'))==sha(out/('before_route.'+k+'.tsv')) for k in ['pins','pdn','instances']}
            assert all(rec['all_flat_pin_geometry_PG_instances_unchanged_by_BPin_regrouping'].values())
        if (out/'after.shared.tsv').exists():
            assert sha(source/'before.shared.tsv')==sha(out/'before.shared.tsv')==sha(out/'after.shared.tsv')
            rec['all_256_original_shared_material_boxes_and_native_net_bindings_unchanged']=True
            rec['parent_invariants']={k:sha(out/('before_route.'+k+'.tsv'))==sha(out/('after_route.'+k+'.tsv')) for k in ['pins','pdn','instances']}
            assert all(rec['parent_invariants'].values())
        if (out/'routed_NOT_FROZEN.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed_NOT_FROZEN.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['fresh_DRC_returncode']=execute(common,script,out/'independent.log',threads=4)
            if rec['fresh_DRC_returncode']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
            # Exact native FIXED status is independent from the box snapshot.
            text=(out/'routed.def').read_text();assert len(re.findall(r'\+\s+FIXED\s+metal10\b',text))==256
            rec['all_256_native_FIXED_status_paths_retained']=True
        if (out/'whole_access.tsv.gz').exists():
            rec['all_multiterminal_geometry']=check(out/'whole_access.tsv.gz',True)
            assert set(rec['all_multiterminal_geometry']['checked_layers'])<={*['metal'+str(i) for i in range(1,11)],*['via'+str(i) for i in range(1,10)]}
            rec['no_material_above_M10_or_via9_in_lower_export']=True
        if (out/'after_route.endpoints.tsv').exists():
            verify_graph(ROOT/'inputs/common-topology-r02',out/'after_route.endpoints.tsv',out/'all_original_endpoint_graph_check.json')
            rec['complete_original_endpoint_graph_check_executed']=True
        if (out/'stages.tsv').exists():
            with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
        rec['actual_native_binary_unchanged']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]==rec['actual_OpenROAD_binary_SHA256']
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    passed=('actual_failure' not in rec and rec.get('native_route_returncode')==0 and rec.get('fresh_DRC_count')==0 and rec.get('all_multiterminal_geometry',{}).get('pass') and rec.get('all_256_native_FIXED_status_paths_retained') and rec.get('complete_original_endpoint_graph_check_executed') and rec['all_closed_sources_unchanged'] and all(rec.get('parent_invariants',{}).values()) and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['final_VDD','final_VSS']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
