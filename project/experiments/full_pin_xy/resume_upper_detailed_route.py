"""Continue real DB guides after strict GRT failure, without changing its result.

No global-route rerun, -allow_congestion, infinite capacity, layer/rule relaxation
or synthetic guide. The original failed stage remains FAILED in every receipt.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from audit_full_upper_access import audit

DRIVER=Path(__file__).resolve().parent


def one(mode,revision):
    source=ROOT/'upper_adaptation_trial/r02'/mode;rp=source/'execution.json';prior=json.loads(rp.read_text())
    assert prior.get('completed_utc') and prior['native_route_returncode']==1
    assert 'GRT-0116' in (source/'global_route.error.txt').read_text()
    odb=source/'failed_global.odb';assert sha(odb)==prior['files'][odb.name]['sha256']
    planfile=source.parent/(mode+'_actual_hook_plan.json');plan=json.loads(planfile.read_text())
    assert sha(planfile)==prior['source_plan_SHA256'] and plan['edge_count']==770
    base=Path(plan['source_lower_checkpoint']);assert ROOT in base.parents and sha(base)==plan['source_lower_checkpoint_SHA256']
    assert prior['source_lower_checkpoint_SHA256']==plan['source_lower_checkpoint_SHA256']
    rc=ROOT/'upper_layer_probe/r01/model/research12.setRC.tcl'
    out=ROOT/'upper_detailed_resume'/revision/mode;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,odb,planfile,base,rc,source/'global_route.error.txt',source/'congestion.rpt']}
    rec={'scope':'ALL770_ACTUAL_GUIDE_DETAIL_CONTINUATION_NOT_TWO_COMPLETE_SYSTEMS_OR_QUALIFIED_BASE',
      'mode':mode,'source_SHA':inputs,'source_lower_checkpoint_SHA256':sha(base),
      'original_GRT_state':'FAILED_GRT_0116_RETAINED_NOT_WAIVED','global_route_reexecuted':False,
      'allow_congestion_or_infinite_capacity_used':False,'all_physical_layers_tracks_and_rules_unchanged':True,
      'base_and_leaf_views':'ORIGINAL_R02_UNQUALIFIED_INPUTS_NOT_REPLACED_BY_NEW_658_VIEWS',
      'base_frozen':False,'full_qualification':False,'RC_STA_electrical':'NOT_EXECUTED_ADAPTER_ONLY',
      'native_returncodes':{},'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        lines=[helper,'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
          'read_db '+tcl(odb),'source '+tcl(rc),'set b [ord::get_db_block];if {[llength [$b getInsts]]} {error "Unexpected FEOL instances"}',
          'set_routing_layers -signal metal11-metal12 -clock metal11-metal12',
          'fingerprint '+tcl(out/'before'),
          'proc save_obs {file} {set f [open $file w];foreach ob [[ord::get_db_block] getObstructions] {set r [$ob getBBox];puts $f [list [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]};close $f}',
          'save_obs '+tcl(out/'before.OBS.tsv'),
          'if {![stage export_existing_failed_GRT_guides {set f [open '+tcl(out/'native_guide_inventory.tsv')+' w];puts $f "net\\tguide_count";set count 0;foreach n [$b getNets] {set guides [$n getGuides];if {![llength $guides]} {error "Missing original DB guides"};incr count;puts $f "[$n getName]\\t[llength $guides]"};close $f;if {$count!=770} {error "Not all original 770 nets"};write_guides '+tcl(out/'original_FAILED_GRT.guide')+'}]} {close $stages;exit 1}',
          'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1;write_db '+tcl(out/'routed_adapter_NOT_SYSTEM.odb')+';write_def '+tcl(out/'routed_adapter.def')+'}]} {catch {write_db '+tcl(out/'failed_detail.odb')+'};close $stages;exit 1}',
          'fingerprint '+tcl(out/'after'),'save_obs '+tcl(out/'after.OBS.tsv'),
          'stage all770_native_geometry_export {source '+tcl(DRIVER/'export_access.tcl')+'}',
          'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),'close $stages']
        script=out/'resume.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_returncodes']['detailed_continuation']=execute(common,script,out/'native.log',env,threads=4);save()
        if (out/'native_guide_inventory.tsv').exists():
            with (out/'native_guide_inventory.tsv').open() as f:gs=list(csv.DictReader(f,delimiter='\t'))
            assert len(gs)==770 and all(int(g['guide_count'])>0 for g in gs)
            rec['all_original770_nets_had_native_DB_guides']=True
        if (out/'routed_adapter_NOT_SYSTEM.odb').exists():
            fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed_adapter_NOT_SYSTEM.odb')+'\nset_routing_layers -signal metal11-metal12 -clock metal11-metal12\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,fresh,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['independent_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():rec.update(audit(out,plan))
        rec['all_original_hook_shapes_and_OBS_constraints_unchanged']=all((out/('after.'+kind+'.tsv')).exists() and sha(out/('before.'+kind+'.tsv'))==sha(out/('after.'+kind+'.tsv')) for kind in ['pins','OBS','die'])
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    if (out/'stages.tsv').exists():
        with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return rec


def run(revision):
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    out=ROOT/'upper_detailed_resume'/revision;out.mkdir(parents=True,exist_ok=False)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda mode:one(mode,revision),['opentpu','llaccel']))
    assert results[0]['source_lower_checkpoint_SHA256']==results[1]['source_lower_checkpoint_SHA256']
    result={'scope':'TWO_ALL770_DETAIL_CONTINUATIONS_ORIGINAL_GLOBAL_FAILURES_RETAINED_NOT_COMPLETE_SYSTEMS',
      'same_partial_base_input_for_both_modes':True,'source_lower_checkpoint_SHA256':results[0]['source_lower_checkpoint_SHA256'],
      'original_GRT_failed_in_both_modes':True,'global_route_reexecuted':False,
      'full_qualification':False,'qualified_common_base':False,'two_complete_M11_M12_systems':False,
      'modes':[{k:r.get(k) for k in ['mode','native_returncodes','independent_DRC_count','all_edge_signal_clock_geometry','actual_770_native_edge_terminal_bijection','all_actual_overlay_M10_material_contained_in_existing_base_hook_rectangles','actual_failure']} for r in results]}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if all('actual_failure' not in r and r['native_returncodes'].get('detailed_continuation')==0 and r.get('independent_DRC_count')==0 and r.get('all_edge_signal_clock_geometry',{}).get('pass') and r.get('actual_770_native_edge_terminal_bijection') and r.get('all_actual_overlay_M10_material_contained_in_existing_base_hook_rectangles') and r.get('all_original_hook_shapes_and_OBS_constraints_unchanged') and r['all_closed_sources_unchanged'] for r in results) else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
