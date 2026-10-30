"""Route the physically installed CEC-proven VECTOR slice, with fresh RC/STA.

Original routed DB and guides are loaded before incremental graph edits.
Only affected nets are requested, but final DRC/connectivity/STA are whole
block. A failed native route is saved for local diagnosis rather than retried
blindly. Original cell/pin/PDN/clock constraints remain independently checked.
"""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_vector_resume import COST_PROC
from verify_mapped_eco import export_graph,load
from run_current_driver_sizing import read_cells
from check_access import check
DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'vector_verified_slice_install/r02';rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and not q.get('actual_failure') and q['all_closed_sources_unchanged']
    assert q['relative_actual_graph_matches_closed_CEC_plus_identity_buffers'] and all(q['all_original_interfaces_PG_die_unchanged'].values())
    names=['actual_install_plan.json','replay_install.tcl','verified_new_cell_poses.tcl','placed.cells.tsv','placed.pins.tsv','placed.pdn.tsv','placed.die.tsv','installed.tsv.gz']
    files=[source/n for n in names]
    for p in files:assert sha(p)==q['files'][p.name]['sha256']
    original=ROOT/'vector_resume/r01';oq=json.loads((original/'execution.json').read_text());odb=original/'routed.odb';guide=original/'route.guide'
    assert sha(odb)=='243c1025646eb8b41b00e8257b78484b458d4eff250fa0b09ce32bc3fe7682d9'
    for p in [odb,guide]:assert sha(p)==oq['files'][p.name]['sha256']
    tp=ROOT/'trials/access-r03/vector-C/execution.json';trial=json.loads(tp.read_text());sdc=Path(trial['source_sdc'])
    assert sha(sdc)==trial['input_sha256'][str(sdc)]
    reservations=[Path(p) for p in trial['input_sha256'] if p.endswith('/access_reservations.tcl')];assert len(reservations)==1
    reservation=reservations[0];assert sha(reservation)==trial['input_sha256'][str(reservation)]
    files += [rp,original/'execution.json',odb,guide,tp,sdc,reservation]
    inputs={str(p):sha(p) for p in files}
    out=ROOT/'vector_verified_slice_route'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_CEC_VERIFIED_COMBINATIONAL_ECO_INCIDENT_ROUTE_WITH_FULL_BLOCK_POSTCHECKS_NOT_PURE_XY',
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'source_SHA':inputs,'native_returncodes':{},'full_qualification':False,'original_SDC_clock_external_loads':'UNCHANGED',
      'allowed_layers':'signal M2-M10; clock M4-M10 unchanged','source_setup_ns':oq['setup_ns'],'source_hold_ns':oq['hold_ns'],
      'separate_mapping_cost':q['separate_mapping_cost'],'pipeline_protocol_cache_state_changes':0,
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for p in trial['libs']:
        if Path(p).is_file():common+=['--bind',p+':'+p+':ro']
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    def native(label,body,threads=8):
        script=out/(label+'.tcl');script.write_text(helper.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')+'\n'+body+'\n')
        code=execute(common,script,out/(label+'.log'),'PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=threads)
        rec['native_returncodes'][label]=code;save();assert code==0,label
    try:
        plan=json.loads((source/'actual_install_plan.json').read_text());assert len(plan['new_cells'])==q['new_total_cells']
        lines=['read_liberty '+tcl(p) for p in trial['libs']]+['read_db '+tcl(odb),'read_sdc '+tcl(sdc),COST_PROC,
          'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set original_obs [lsort [$b getObstructions]];set temporary_obs {};set access_reservations {};source '+tcl(reservation),
          'foreach r $access_reservations {lassign $r ly a c d e;set z {};foreach v [list $a $c $d $e] {lappend z [expr {round($v*$u)}]};lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$z]}',
          'set_routing_layers -signal metal2-metal10 -clock metal4-metal10','read_guides '+tcl(guide),
          'if {![stage begin_incremental {global_route -start_incremental}]} {close $stages;exit 1}',
          'if {![stage actual_verified_graph_pose_replay {source '+tcl(source/'replay_install.tcl')+';source '+tcl(source/'verified_new_cell_poses.tcl')+';foreach r $mapped_replay {lassign $r name master x y status orient;set i [$b findInst $name];if {$i eq "NULL" || [[$i getMaster] getName] ne $master || $orient eq ""} {error "Native mapped pose/master mismatch"};$i setOrient $orient;$i setLocation $x $y;$i setPlacementStatus $status};filler_placement -prefix HPY_VEC_MAP_FILL_ $filler_masters;global_connect;check_placement -verbose}]} {catch {write_db '+tcl(out/'failed_replay.odb')+'};close $stages;exit 1}',
          'if {![stage incremental_global_route {global_route -end_incremental -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}',
          'set requested {'+' '.join(tcl(n) for n in plan['all_touched_signal_nets'])+'};set actual {};set f [open '+tcl(out/'requested_and_retired_nets.tsv')+' w];foreach nn $requested {if {[$b findNet $nn] eq "NULL"} {puts $f [list RETIRED_CONE_INTERIOR $nn]} else {lappend actual $nn;puts $f [list ACTUAL_ROUTE_REQUEST $nn]}};close $f;set_nets_to_route $actual',
          'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1}]} {catch {write_db '+tcl(out/'failed_route.odb')+'};close $stages;exit 1}',
          'foreach ob $temporary_obs {odb::dbObstruction_destroy $ob};if {[lsort [$b getObstructions]] ne $original_obs} {error "Original OBS changed"}',
          'fingerprint '+tcl(out/'after'),'cell_cost '+tcl(out/'after.cell_cost.tsv'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+';report_checks -path_delay max -group_path_count 12 -fields {capacitance slew fanout} -format full_clock_expanded -digits 6 > '+tcl(out/'max12_paths.txt')+'}','close $stages']
        native('actual_route_RC_STA','\n'.join(lines))
        native('fresh_DRC','read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\nclose $stages',threads=1)
        rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['native_returncodes']['fresh_routed_graph']=export_graph(common,out/'routed.odb',out,'routed');save();assert rec['native_returncodes']['fresh_routed_graph']==0
        assert load(out/'routed.tsv.gz')==load(source/'installed.tsv.gz')
        refcells,refterms=read_cells(source/'placed.cells.tsv');cells,terms=read_cells(out/'after.cells.tsv')
        nonfill={n for n in load(source/'installed.tsv.gz')[0]};assert all(cells[n]==refcells[n] for n in nonfill)
        rec['all_verified_functional_cells_and_graph_unchanged_through_route']=True
        rec['all_interface_pin_geometry_PG_die_preserved']={k:sha(source/('placed.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']};assert all(rec['all_interface_pin_geometry_PG_die_preserved'].values())
        for kind in ['setup','hold']:rec[kind+'_ns']=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',(out/(kind+'.txt')).read_text())[1])
        rec['literal_VIOLATED_markers_not_full_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['native_stages']={p.name:{r['stage']:r['status'] for r in csv.DictReader(p.open(),delimiter='\t')} for p in out.glob('*.stages.tsv')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    stages=rec['native_stages'].get('actual_route_RC_STA.stages.tsv',{})
    return int(bool(rec.get('actual_failure')) or not rec['all_closed_sources_unchanged'] or rec.get('fresh_DRC_count')!=0 or not rec.get('whole_signal_geometry',{}).get('pass') or rec.get('setup_ns',-1)<0 or rec.get('hold_ns',-1)<0 or rec.get('literal_VIOLATED_markers_not_full_failure_count',1)>0 or not all(stages.get(k)=='EXECUTED' for k in ['detailed_route','VDD','VSS','whole_signal_geometry','rcx','sta']))


if __name__=='__main__':sys.exit(run(sys.argv[1]))
