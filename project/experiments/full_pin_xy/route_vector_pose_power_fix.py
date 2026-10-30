"""Route actual nets incident on the nine corrected VECTOR orientations.

The local fix restored legal placement and VSS; VDD now touches old clock
wires172/167 rather than reversed cell power pins. Reroute those measured
incident nets under original M2-M10/M4-M10, without new sizing or cells.
"""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check
from compare_native_route_representations import routing_box_hashes
DRIVER=Path(__file__).resolve().parent
def run(revision):
    fix=ROOT/'vector_pose_power_fix/r02';fp=fix/'execution.json';f=json.loads(fp.read_text())
    assert f.get('completed_utc') and f['all_source_geometry_and_closed_legal_inputs_unchanged'] and f['native_stages']['legal_pose_check']==f['native_stages']['VSS']=='EXECUTED'
    assert f['native_stages']['VDD']=='FAIL';log=(fix/'native.log').read_text();assert 'PSM-0038' not in log
    power_shorts=re.findall(r'Shorted shape on net VDD to net (\S+)',log);assert power_shorts and set(power_shorts)<=set(['clknet_leaf_167_clk','clknet_leaf_172_clk'])
    source=ROOT/'current_driver_sizing/r05/vector';sp=source/'execution.json';s=json.loads(sp.read_text());odb=source/'routed.odb';guide=source/'route.guide';geo=source/'whole_access.tsv.gz'
    assert s.get('completed_utc') and s['all_closed_sources_unchanged'] and s['fresh_DRC_count']==0 and s['whole_signal_geometry']['pass']
    for p in [odb,guide,geo,source/'after.cells.tsv']:assert sha(p)==s['files'][p.name]['sha256']
    assert f['source_SHA'][str(odb)]==sha(odb)
    rows=list(csv.DictReader((fix/'actual9_orientation_fixes.tsv').open(),delimiter='\t'));assert len(rows)==9
    wanted={r['instance'] for r in rows};affected=set()
    for line in (source/'after.cells.tsv').open():
        p=line.split()
        if len(p)==3 and p[0].strip('{}') in wanted:
            net=p[2].strip('{}')
            if net not in ['VDD','VSS','NULL']:affected.add(net)
    assert set(power_shorts)<=affected
    trial=ROOT/'trials/access-r03/vector-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
    reservations=[Path(p) for p in old['input_sha256'] if p.endswith('/access_reservations.tcl')]
    for p in reservations:assert sha(p)==old['input_sha256'][str(p)]
    inputs={str(p):sha(p) for p in [fp,fix/'native.log',fix/'actual9_orientation_fixes.tsv',fix/'after.cells.tsv',sp,odb,guide,geo,trial,sdc]+reservations}
    out=ROOT/'vector_pose_route_fix'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_NINE_VERIFIED_POSE_AND_INCIDENT_CLOCK_DATA_REROUTE_NOT_PURE_PIN_XY_OR_FULL_QUALIFICATION',
      'source_SHA':inputs,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,
      'same75_size_ECO_resources_and_master_poses_as_verified_legalization':True,'additional_functional_cells_or_sizes':0,
      'original_allowed_layers':'signal M2-M10; clock M4-M10','original_clocks_loads_protocol_and_interfaces':'UNCHANGED',
      'measured_old_clock_VDD_shorts':sorted(set(power_shorts)),'actually_selected_incident_networks':sorted(affected),'native_returncodes':{}}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    for prefix in ['/public/home/yuzelu/project-circuit','/public/home/yuzelu/PingyangHuang/issue-55']:common+=['--bind',prefix+':'+prefix+':ro']
    for lib in old['libs']:
        if Path(lib).is_file():common+=['--bind',lib+':'+lib+':ro']
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    try:
        lines=[helper]+['read_liberty '+tcl(lib) for lib in old['libs']]+['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set original_obs [lsort [$b getObstructions]];set temporary_obs {}','fingerprint '+tcl(out/'before')]
        for p in reservations:lines+=['set access_reservations {};source '+tcl(p),'foreach r $access_reservations {lassign $r ly a c d e;set z {};foreach v [list $a $c $d $e] {lappend z [expr {round($v*$u)}]};lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$z]}']
        lines+=['set_routing_layers -signal metal2-metal10 -clock metal4-metal10','read_guides '+tcl(guide),
          'if {![stage begin_incremental {global_route -start_incremental}]} {close $stages;exit 1}',
          'if {![stage restore_exact9_legal_poses {']
        for r in rows:
            lines+=['set i [$b findInst '+tcl(r['instance'])+'];if {$i eq "NULL" || [[$i getMaster] getName] ne '+tcl(r['master'])+' || [$i getOrient] ne '+tcl(r['old_orientation'])+'} {error "Measured orientation source changed"};$i setOrient '+r['new_orientation']+';$i setLocation '+r['x']+' '+r['y']]
        lines+=['check_placement -verbose}]} {close $stages;exit 1}',
          'if {![stage incremental_global_route {global_route -end_incremental -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {close $stages;exit 1}',
          'set selected_names {'+' '.join(tcl(n) for n in sorted(affected))+'};set_nets_to_route $selected_names',
          'if {![stage incident_nets_detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1}]} {catch {write_db '+tcl(out/'failed_route.odb')+'};close $stages;exit 1}',
          'foreach ob $temporary_obs {odb::dbObstruction_destroy $ob};if {[lsort [$b getObstructions]] ne $original_obs} {error "Original OBS changed"}',
          'fingerprint '+tcl(out/'after'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}','stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'source '+tcl(DRIVER/'export_access.tcl'),
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']
        script=out/'route.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_returncodes']['actual9_pose_and_incident_route']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=8);save()
        if (out/'routed.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'fresh.log',threads=4)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
            rec['all_verified_functional_and_filler_cells_masters_poses_orientations_and_graph_exact']=sha(out/'after.cells.tsv')==sha(fix/'after.cells.tsv');assert rec['all_verified_functional_and_filler_cells_masters_poses_orientations_and_graph_exact']
            rec['original_pin_PG_die_preserved']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']};assert all(rec['original_pin_PG_die_preserved'].values())
            rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
            a,_=routing_box_hashes(geo,375675);b,_=routing_box_hashes(out/'whole_access.tsv.gz',375675)
            rec['actual_changed_route_networks']=[n for n in a if a[n]!=b[n]];rec['other_than_incident_route_changes']=[n for n in rec['actual_changed_route_networks'] if n not in affected]
            for kind in ['setup','hold']:rec[kind+'_ns']=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',(out/(kind+'.txt')).read_text())[1])
            rec['literal_VIOLATED_markers_not_full_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    if (out/'stages.tsv').exists():rec['native_stages']={r['stage']:r['status'] for r in csv.DictReader((out/'stages.tsv').open(),delimiter='\t')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or rec.get('fresh_DRC_count')!=0 or not all(rec.get('native_stages',{}).get(k)=='EXECUTED' for k in ['incident_nets_detailed_route','VDD','VSS','rcx','sta']) or rec.get('setup_ns',-1)<0 or rec.get('hold_ns',-1)<0 or rec.get('literal_VIOLATED_markers_not_full_failure_count',1)>0 or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
