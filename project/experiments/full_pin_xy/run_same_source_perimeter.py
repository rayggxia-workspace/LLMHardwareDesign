"""Actual optimized perimeter baseline from CURRENT C cells/poses/PG/SDC.

Reuse old optimized boundary XY, not its mismatched ECO resources. No cell
placement/sizing/CTS/resource edit. All original pins/constants remain. This is
a leaf comparison stage; it cannot stand for a common-base system comparison.
"""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_common_integration import source_view,actual_boundary_pins
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_llsys_actual_tips import pin_contract
from check_access import check
from lef_view_contract import verify
DRIVER=Path(__file__).resolve().parent
CASES={'gemm':(3753,10,'antenna_incremental_eco/r01/gemm-C','diode_views/r01/gemm-C'),
       'vector':(2246,10,'vector_resume/r01','vector_current_views/r01/vector-C'),
       'opentpu_aux':(2229,8,'system_stacked_via_route/r01/opentpu_aux-C','system_stacked_via_views/r01/opentpu_aux-C')}
def run(case,revision):
    assert case in CASES;count,top,relative,view_relative=CASES[case];source=ROOT/relative;rp=source/'execution.json';s=json.loads(rp.read_text());odb=source/'routed.odb'
    assert s.get('completed_utc') and s['fresh_DRC_count']==0 and s['whole_signal_geometry']['pass'] and sha(odb)==s['files'][odb.name]['sha256']
    view=ROOT/view_relative;vp=view/'execution.json';v=json.loads(vp.read_text());assert v.get('completed_utc') and v['source_geometry_sha256']==sha(odb) and v['native_export_returncode']==v['fresh_model_read_returncode']==0 and v['matching_all_signal_model_pins']==count
    inventory=ROOT/'fair_boundary_source_inventory/r01/execution.json';i=json.loads(inventory.read_text());assert i.get('completed_utc') and i['all_sources_unchanged']
    assert all(i['cases'][case]['exact_resource_constraint_fingerprint_matches'][k] for k in ['pdn.tsv','die.tsv','sdc'])
    aopt=source_view(case,'Aopt','original');wanted=actual_boundary_pins(aopt['directory']/'abstract.lef',case,'Aopt')
    pinfile=view/'pins.tsv';assert sha(pinfile)==v['files'][pinfile.name]['sha256']
    current={r['pin']:r for r in csv.DictReader(pinfile.open(),delimiter='\t') if r['use'] not in ['POWER','GROUND']};assert len(current)==count
    normalized={n.replace('\\',''):n for n in current};assert len(normalized)==count
    targets={};desired=[]
    for r in wanted:
        name=normalized[r['pin']];c=current[name];box=[round(r[k]*2000) for k in ['x0_um','y0_um','x1_um','y1_um']]
        assert c['layer']==r['layer'] and c['direction']==r['direction'] and box[2]-box[0]==box[3]-box[1]==280
        oldbox=[int(c[k]) for k in ['x0','y0','x1','y1']]
        desired.append(dict(r,native_pin=name,source_C_box_DBU=oldbox,target_Aopt_box_DBU=box))
        if box!=oldbox:targets[name]=(c['layer'],box)
    assert len(desired)==count and targets
    trial=ROOT/'trials/access-r03'/(case+'-C')/'execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
    boundary_trial=ROOT/'trials/full-controls-r04'/(case+'-Aopt')/'execution.json';b=json.loads(boundary_trial.read_text());reservations=[Path(p) for p in b['input_sha256'] if p.endswith('/access_reservations.tcl')]
    for p in reservations:assert sha(p)==b['input_sha256'][str(p)]
    routing='set_routing_layers -signal metal2-metal'+str(top)+' -clock metal4-metal'+str(top)
    witnesses=[source/name for name in s['files'] if name.endswith('.tcl') and s['files'][name]['bytes']<1024*1024 and routing in (source/name).read_text()]
    assert witnesses,'Original allowed routing range has no SHA-bound native witness'
    for p in witnesses:assert sha(p)==s['files'][p.name]['sha256']
    inputs={str(p):sha(p) for p in [rp,odb,vp,pinfile,inventory,aopt['receipt'],aopt['directory']/'abstract.lef',trial,sdc,boundary_trial]+reservations+witnesses}
    out=ROOT/'same_source_perimeter'/revision/case;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_CURRENT_C_RESOURCE_OPTIMIZED_PERIMETER_LEAF_BASELINE_NOT_FULL_SYSTEM',
      'case':case,'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,
      'original_signal_pins':count,'requested_XY_changes':len(targets),'original_allowed_layers':routing,
      'new_cells_sizes_placement_CTS_or_architecture_changes':0,'original_clock_loads_and_all_signal_semantics':'UNCHANGED',
      'optimized_perimeter_XY_source':str(aopt['directory']),'resource_epoch':'Current C source; old Aopt mismatched resources are not used',
      'missing_full_rules_GDS_RTL_and_system_proof':'UNCHANGED_NOT_QUALIFIED','native_returncodes':{}}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    (out/'all_original_and_optimized_perimeter_pin_targets.json').write_text(json.dumps(desired,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    for prefix in ['/public/home/yuzelu/project-circuit','/public/home/yuzelu/PingyangHuang/issue-55']:common+=['--bind',prefix+':'+prefix+':ro']
    for lib in old['libs']:
        if Path(lib).is_file():common+=['--bind',lib+':'+lib+':ro']
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    try:
        lines=[helper]+['read_liberty '+tcl(lib) for lib in old['libs']]+['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set original_obs [lsort [$b getObstructions]];set temporary_obs {}','fingerprint '+tcl(out/'before'),
          'if {![stage current_resource_optimized_perimeter_pin_edits {']
        for name,(layer,box) in targets.items():
            x,y=(box[0]+box[2])/4000.,(box[1]+box[3])/4000.
            lines.append('place_pin -pin_name '+tcl(name)+' -layer '+layer+' -location {'+str(x)+' '+str(y)+'} -pin_size {.14 .14}')
        lines+=['}]} {close $stages;exit 1}','fingerprint '+tcl(out/'moved')]
        for p in reservations:lines+=['set access_reservations {};source '+tcl(p),'foreach r $access_reservations {lassign $r ly a c d e;set z {};foreach v [list $a $c $d $e] {lappend z [expr {round($v*$u)}]};lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$z]}']
        lines+=[routing,
          'if {![stage rip_only_signal_and_clock_routes {foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}}}]} {close $stages;exit 1}',
          'if {![stage actual_global_route {global_route -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}',
          'if {![stage actual_detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1}]} {catch {write_db '+tcl(out/'failed_route.odb')+'};close $stages;exit 1}',
          'foreach ob $temporary_obs {odb::dbObstruction_destroy $ob};if {[lsort [$b getObstructions]] ne $original_obs} {error "Original OBS changed"}',
          'fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),
          'write_abstract_lef '+tcl(out/'abstract.lef'),'write_abstract_lef -bloat_factor 0 '+tcl(out/'detailed.lef'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}','stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'source '+tcl(DRIVER/'export_access.tcl'),'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}',
          'stage extracted_research_timing_model {write_timing_model '+tcl(out/'timing.lib')+'}','close $stages']
        script=out/'route.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_returncodes']['actual_Aopt_same_resources']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=8);save()
        if (out/'routed.odb').exists():
            rec['complete_pin_contract']=pin_contract(out,targets,count)
            rec['exact_C_resource_cells_connections_poses_PG_and_die_preserved']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']};assert all(rec['exact_C_resource_cells_connections_poses_PG_and_die_preserved'].values())
            rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True);rec['OBS_view_contract']=verify(out/'abstract.lef',out/'detailed.lef')
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed.odb')+'\n'+routing+'\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'fresh.log',threads=4)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
            for kind in ['setup','hold']:rec[kind+'_ns']=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',(out/(kind+'.txt')).read_text())[1])
            rec['literal_VIOLATED_markers_not_full_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    if (out/'stages.tsv').exists():rec['native_stages']={r['stage']:r['status'] for r in csv.DictReader((out/'stages.tsv').open(),delimiter='\t')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or rec.get('fresh_DRC_count')!=0 or not all(rec.get('native_stages',{}).get(k)=='EXECUTED' for k in ['actual_global_route','actual_detailed_route','VDD','VSS','rcx','sta']) or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(*sys.argv[1:]))
