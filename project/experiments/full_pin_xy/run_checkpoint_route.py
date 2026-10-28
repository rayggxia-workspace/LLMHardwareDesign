"""Route the successfully isolated SYSTEM placement; keep original OBS and rules."""
from pathlib import Path
import datetime,json,os,re,sys
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent
OBS_PROC='''proc obs_contract {ob} {set bb [$ob getBBox];return [list [$ob getId] [[$bb getTechLayer] getName] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]}'''


def run(revision):
    legal=ROOT/'checkpoint_legalization/r02';lp=legal/'execution.json';j=json.loads(lp.read_text())
    assert j.get('completed_utc') and j['native_returncode']==0 and j['source_unchanged'] and all(j['geometry_invariants'].values())
    placed=legal/'placed_NOT_ROUTED.odb';assert sha(placed)==j['files'][placed.name]['sha256']
    eco=ROOT/'leaf_eco/r08/opentpu_aux-C';ep=eco/'execution.json';e=json.loads(ep.read_text())
    source=ROOT/'finalized'/e['source_physical_revision']/'opentpu_aux-C';original=source/'clean.odb'
    p=json.loads((source/'execution.json').read_text());trial=Path(p['legacy_RC_STA_receipt']);old=json.loads(trial.read_text())
    assert sha(original)==p['clean_odb_sha256']
    sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
    reservation=[Path(k) for k in old['input_sha256'] if k.endswith('/access_reservations.tcl')];assert len(reservation)==1
    reservation=reservation[0];assert sha(reservation)==old['input_sha256'][str(reservation)]
    out=ROOT/'checkpoint_route'/revision;out.mkdir(parents=True,exist_ok=False)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for path in old['libs']:
        if Path(path).is_file():common+=['--bind',path+':'+path+':ro']
    inp={str(q):sha(q) for q in [lp,placed,ep,original,sdc,reservation,trial]}
    rec={'scope':'COSTED_SYSTEM_ECO_FULL_REROUTE_FROM_ISOLATED_PLACEMENT_NOT_QUALIFIED',
      'source_inputs_SHA':inp,'original_SDC':str(sdc),'original_routing_layers':'signal M2-M8; clock M4-M8',
      'full_qualification':False,'source_cell_repair':'r08; resizer not rerun',
      'source_placement':str(placed),'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    # Original IDs AND geometry are exported by an independent native read.
    audit=out/'original_OBS.tcl';audit.write_text(OBS_PROC+'\nread_db '+tcl(original)+'\nset original_obs {};foreach ob [[ord::get_db_block] getObstructions] {lappend original_obs [obs_contract $ob]};set f [open '+tcl(out/'original_OBS_contract.tcl')+' w];puts $f [list set original_obs $original_obs];close $f\n')
    rec['original_OBS_export_returncode']=execute(common,audit,out/'original_OBS.log',threads=1)
    assert rec['original_OBS_export_returncode']==0
    helpers=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    lines=[helpers,OBS_PROC]+['read_liberty '+tcl(path) for path in old['libs']]
    lines+=['read_db '+tcl(placed),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
      'fingerprint '+tcl(out/'before'),'set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];source '+tcl(out/'original_OBS_contract.tcl'),
      'set original_by_id [dict create];foreach row $original_obs {dict set original_by_id [lindex $row 0] $row};set original_seen {};set temporary_obs {};set actual_new_boxes {}',
      'foreach ob [$b getObstructions] {set row [obs_contract $ob];set id [$ob getId];if {[dict exists $original_by_id $id]} {if {$row ne [dict get $original_by_id $id]} {error "Original OBS geometry changed"};lappend original_seen $id} else {lappend temporary_obs $ob;lappend actual_new_boxes [lrange $row 1 end]}}',
      'if {[lsort $original_seen] ne [lsort [dict keys $original_by_id]]} {error "Missing original OBS"}',
      'set access_reservations {};source '+tcl(reservation)+';set expected_new_boxes {};foreach row $access_reservations {lassign $row ly x0 y0 x1 y1;set bb {};foreach v [list $x0 $y0 $x1 $y1] {lappend bb [expr {round($v*$u)}]};lappend expected_new_boxes [list $ly {*}$bb]};if {[lsort $actual_new_boxes] ne [lsort $expected_new_boxes]} {error "Checkpoint additional OBS differs from exact source access reservations"}',
      'set f [open '+tcl(out/'temporary_OBS_lineage.txt')+' w];puts $f [list original [llength $original_obs] temporary [llength $temporary_obs] exact_geometry_multiset_match 1];close $f',
      'set_routing_layers -signal metal2-metal8 -clock metal4-metal8',
      'if {![stage rip_signal_clock_routes {foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}}}]} {close $stages;exit 1}',
      'if {![stage global_route {global_route -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {close $stages;exit 1}',
      'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1}]} {close $stages;exit 1}',
      'if {![stage remove_only_source_temporary_OBS {foreach ob $temporary_obs {odb::dbObstruction_destroy $ob};set after_obs {};foreach ob [$b getObstructions] {lappend after_obs [obs_contract $ob]};if {[lsort $after_obs] ne [lsort $original_obs]} {error "Original OBS changed after cleanup"};write_db '+tcl(out/'routed.odb')+'}]} {close $stages;exit 1}',
      'fingerprint '+tcl(out/'after'),'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),
      'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
      'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
      'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}',
      'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
      'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}',
      'close $stages']
    script=out/'route.tcl';script.write_text('\n'.join(lines)+'\n')
    rec['native_returncode']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'))
    if (out/'routed.odb').exists():
        fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['fresh_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
        if rec['fresh_DRC_returncode']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
    if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
    rec['geometry_invariants']={k:((out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv'))) for k in ['cells','pins','pdn','die']}
    rec['source_unchanged']=all(sha(Path(p))==v for p,v in inp.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('CHECKPOINT_ROUTE',rec['native_returncode'],'NOT_FULLY_QUALIFIED',flush=True)
    return rec['native_returncode']


if __name__=='__main__':sys.exit(run(sys.argv[1]))
