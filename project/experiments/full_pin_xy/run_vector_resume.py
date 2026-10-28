"""Resume the actual 14-size/17-buffer VECTOR checkpoint, without repeating repair_design."""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_checkpoint_route import OBS_PROC
from check_access import check

DRIVER=Path(__file__).resolve().parent
COST_PROC='''proc cell_cost {file} {
 set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set f [open $file w]
 puts $f "instance\\tmaster\\ttype\\tarea_um2\\tx_dbu\\ty_dbu"
 foreach i [$b getInsts] {set m [$i getMaster];lassign [$i getLocation] x y;puts $f [join [list [$i getName] [$m getName] [$m getType] [expr {[$m getWidth]*double([$m getHeight])/($u*$u)}] $x $y] "\\t"]};close $f
}'''


def run(revision):
    out=ROOT/'vector_resume'/revision;out.mkdir(parents=True,exist_ok=False)
    start=ROOT/'estimator_diagnosis/r02';proof=json.loads((start/'execution.json').read_text())
    checkpoint=start/'cell_repaired_NOT_LEGALIZED_OR_ROUTED.odb'
    assert proof['native_returncode']==0 and proof['fillers_removed_before_estimation'] and proof['all_sources_unchanged']
    assert sha(checkpoint)==proof['files'][checkpoint.name]['sha256']
    for k in ['pins','pdn','die']:assert sha(start/('before.'+k+'.tsv'))==sha(start/('after.'+k+'.tsv'))
    source=ROOT/'finalized/access-r03/vector-C';p=json.loads((source/'execution.json').read_text())
    trial=Path(p['legacy_RC_STA_receipt']);old=json.loads(trial.read_text());sdc=Path(old['source_sdc'])
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    reservations=[Path(k) for k in old['input_sha256'] if k.endswith('/access_reservations.tcl')];assert len(reservations)==1
    reservations=reservations[0];assert sha(reservations)==old['input_sha256'][str(reservations)]
    before_cost=ROOT/'leaf_eco/r09/vector-C/before.cell_cost.tsv'
    r09=json.loads((before_cost.parent/'execution.json').read_text());assert sha(before_cost)==r09['files'][before_cost.name]['sha256']
    with before_cost.open() as f:original=list(csv.DictReader(f,delimiter='\t'))
    fillers=sorted({q['master'] for q in original if q['type']=='CORE_SPACER'});assert fillers
    inputs={str(q):sha(q) for q in [checkpoint,start/'execution.json',source/'execution.json',trial,sdc,reservations,before_cost]}
    rec={'scope':'COSTED_VECTOR_ECO_RESUME_NOT_PURE_XY_OR_FULL_QUALIFICATION',
      'source_checkpoint':str(checkpoint),'source_SHA':inputs,'repair_design_repeated':False,
      'original_SDC_clocks_loads_and_allowed_layers_preserved':True,'allowed_layers':'signal M2-M10; clock M4-M10',
      'timing_repair_estimator':'Native placement heuristic, not extracted RC; final RCX/STA mandatory',
      'full_qualification':False,'design_formal_equivalence':'NOT_EXECUTED','complete_rules':'NOT_QUALIFIED',
      'native_returncodes':{},'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for path in old['libs']:
        if Path(path).is_file():common+=['--bind',path+':'+path+':ro']
    helpers=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    liblines=['read_liberty '+tcl(path) for path in old['libs']]
    def native(label,lines):
        script=out/(label+'.tcl');h=helpers.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')
        script.write_text('\n'.join([h,COST_PROC]+lines)+'\n')
        rc=execute(common,script,out/(label+'.log'),'OMP_NUM_THREADS=4,PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'))
        rec['native_returncodes'][label]=rc;(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
        if rc:raise RuntimeError(label+' actual native failure')
    try:
        native('timing_repair',liblines+['read_db '+tcl(checkpoint),'read_sdc '+tcl(sdc),
          'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','estimate_parasitics -placement',
          'if {![stage setup_repair {repair_timing -setup -skip_pin_swap -skip_gate_cloning -skip_buffer_removal -skip_buffer_to_inverters -max_passes 20 -max_iterations 10000 -max_utilization 85 -verbose}]} {close $stages;exit 1}',
          'if {![stage hold_repair {repair_timing -hold -max_utilization 85 -verbose}]} {close $stages;exit 1}',
          'fingerprint '+tcl(out/'timing_repaired'),'cell_cost '+tcl(out/'timing_repaired.cell_cost.tsv'),
          'write_db '+tcl(out/'timing_repaired_NOT_LEGALIZED_OR_ROUTED.odb'),'close $stages'])
        native('legalization',['read_db '+tcl(out/'timing_repaired_NOT_LEGALIZED_OR_ROUTED.odb'),
          'set anchors {};foreach i [[ord::get_db_block] getInsts] {if {[[$i getMaster] getType] in {BLOCK CORE_WELLTAP}} {lappend anchors [list $i [$i getLocation] [$i getOrient] [$i getPlacementStatus]];$i setPlacementStatus FIRM}}',
          'if {![stage independent_legalization {detailed_placement -use_diamond_legalizer}]} {close $stages;exit 1}',
          'foreach row $anchors {lassign $row i xy ori status;if {[$i getLocation] ne $xy || [$i getOrient] ne $ori} {error "Original macro/welltap anchor moved"};$i setPlacementStatus $status}',
          'if {![stage placement_check {check_placement -verbose}]} {close $stages;exit 1}',
          'add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power',
          'add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground','global_connect',
          'if {![stage original_filler_master_restore {filler_placement -prefix PINXY_VECTOR_FILL_ {'+' '.join(fillers)+'};global_connect;check_placement -verbose}]} {close $stages;exit 1}',
          'fingerprint '+tcl(out/'placed'),'cell_cost '+tcl(out/'actual_final.cell_cost.tsv'),
          'write_db '+tcl(out/'placed_NOT_ROUTED.odb'),'close $stages'])
        a={q['instance']:q for q in original}
        with (out/'actual_final.cell_cost.tsv').open() as f:b={q['instance']:q for q in csv.DictReader(f,delimiter='\t')}
        names=set(a)&set(b);cost={'added_functional_instances_excluding_fillers':sum(b[n]['type']!='CORE_SPACER' for n in set(b)-set(a)),
          'removed_functional_instances_excluding_fillers':sum(a[n]['type']!='CORE_SPACER' for n in set(a)-set(b)),
          'changed_master_original_instances':sum(a[n]['master']!=b[n]['master'] for n in names),
          'moved_original_instances':sum((a[n]['x_dbu'],a[n]['y_dbu'])!=(b[n]['x_dbu'],b[n]['y_dbu']) for n in names),
          'original_CORE_SPACER_count':sum(q['type']=='CORE_SPACER' for q in a.values()),
          'restored_CORE_SPACER_count':sum(q['type']=='CORE_SPACER' for q in b.values()),
          'standard_cell_master_area_delta_um2':sum(float(q['area_um2']) for q in b.values() if q['type'] not in ['BLOCK','CORE_SPACER'])-sum(float(q['area_um2']) for q in a.values() if q['type'] not in ['BLOCK','CORE_SPACER']),
          'not_pure_pin_XY_benefit':True,'not_block_area_saving':True}
        rec['separate_cell_ECO_cost']=cost
        native('route',liblines+['read_db '+tcl(out/'placed_NOT_ROUTED.odb'),'read_sdc '+tcl(sdc),OBS_PROC,
          'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','fingerprint '+tcl(out/'before_route'),
          'set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set original_obs {};foreach ob [$b getObstructions] {lappend original_obs [obs_contract $ob]};set temporary_obs {};set access_reservations {};source '+tcl(reservations),
          'foreach row $access_reservations {lassign $row ly x0 y0 x1 y1;set c {};foreach v [list $x0 $y0 $x1 $y1] {lappend c [expr {round($v*$u)}]};lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$c]}',
          'set_routing_layers -signal metal2-metal10 -clock metal4-metal10',
          'foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}}',
          'if {![stage global_route {global_route -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}',
          'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1}]} {close $stages;exit 1}',
          'foreach ob $temporary_obs {odb::dbObstruction_destroy $ob};set actual_obs {};foreach ob [$b getObstructions] {lappend actual_obs [obs_contract $ob]};if {[lsort $actual_obs] ne [lsort $original_obs]} {error "Original OBS changed"}',
          'write_db '+tcl(out/'routed.odb'),'fingerprint '+tcl(out/'after_route'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages'])
        fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['fresh_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
        if rec['fresh_DRC_returncode']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['source_pin_PG_die_unchanged']={k:sha(start/('before.'+k+'.tsv'))==sha(out/('after_route.'+k+'.tsv')) for k in ['pins','pdn','die']}
        rec['placed_cells_pins_PG_die_unchanged_through_route']={k:sha(out/('before_route.'+k+'.tsv'))==sha(out/('after_route.'+k+'.tsv')) for k in ['cells','pins','pdn','die']}
        rec['status']='ACTUAL_COSTED_VECTOR_ROUTE_EXECUTED_READ_ALL_GATES_NOT_QUALIFIED'
    except Exception:
        rec['status']='ACTUAL_VECTOR_RESUME_FAILED_OR_INCOMPLETE';rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    stages=out/'route.stages.tsv'
    if stages.exists():
        with stages.open() as f:rec['route_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    for kind in ['setup','hold']:
        p=out/(kind+'.txt')
        if p.exists():
            match=re.search(r'worst slack (?:min|max)\s+([-\d.]+)',p.read_text())
            if match:rec[kind+'_ns']=float(match[1])
    if (out/'checks.txt').exists():rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status'],flush=True)
    passed=(rec.get('fresh_DRC_count')==0 and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0
      and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0 and rec['all_sources_unchanged']
      and rec.get('whole_signal_geometry',{}).get('pass')
      and all(rec.get('source_pin_PG_die_unchanged',{}).get(k) for k in ['pins','pdn','die'])
      and all(rec.get('placed_cells_pins_PG_die_unchanged_through_route',{}).get(k) for k in ['cells','pins','pdn','die'])
      and all(rec.get('route_stage_status',{}).get(k)=='EXECUTED' for k in ['global_route','detailed_route','VDD','VSS','whole_signal_geometry','rcx','sta']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
