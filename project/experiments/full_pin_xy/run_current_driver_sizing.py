"""Actual current-source electrical repair, with original interfaces/SDC.

All reported cap/slew drivers are inventoried. Only same-Liberty-function/state
drive variants are allowed; geometry legalization is isolated from STA. Costs
and unrepairable families remain explicit, never a pure-XY benefit claim.
"""
from pathlib import Path
from collections import defaultdict
import csv,datetime,hashlib,json,math,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_vector_resume import COST_PROC
from cell_semantics import groups,contract
from check_access import check
DRIVER=Path(__file__).resolve().parent
SOURCES={'llaccel_aux':'llsys_wire_pin_retention/r01','vector':'vector_resume/r01','opentpu_aux':'system_stacked_via_route/r01/opentpu_aux-C'}
TRIALS={'llaccel_aux':'llsys-pg-r03','vector':'access-r03','opentpu_aux':'access-r03'}

def read_cells(path):
    cells={};terms={}
    for line in path.open():
        p=line.split()
        if len(p)==3:terms[(p[0],p[1])]=p[2]
        elif len(p)>=5:cells[p[0]]=(p[1],tuple(p[2:]))
    return cells,terms

def run(case,revision):
    assert case in SOURCES
    source=ROOT/SOURCES[case];rp=source/'execution.json';q=json.loads(rp.read_text())
    assert q.get('completed_utc') and q['fresh_DRC_count']==0 and q['whole_signal_geometry']['pass']
    odb=source/'routed.odb';report=source/'checks.txt'
    for p in [odb,report]:assert sha(p)==q['files'][p.name]['sha256']
    ep=ROOT/'current_electrical_classification/r02/execution.json';e=json.loads(ep.read_text())
    assert e.get('completed_utc') and not e.get('actual_failure') and e['cases'][case]['ODB_SHA256']==sha(odb)
    trial=ROOT/'trials'/TRIALS[case]/(case+'-C')/'execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc'])
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    out=ROOT/'current_driver_sizing'/revision/case;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,odb,report,ep,trial,sdc]}
    rec={'scope':'ACTUAL_CURRENT_ALL_REPORTED_ELECTRICAL_DRIVER_INVENTORY_AND_COMPATIBLE_SIZING_NOT_PURE_XY',
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'source_SHA':inputs,'full_qualification':False,'source_setup_ns':q.get('setup_ns'),'source_min_ns':q.get('hold_ns'),
      'interface_function_bits_constants_pin_XY_layer_size_connections_targets_and_allowed_layers':'MUST_REMAIN_UNCHANGED',
      'original_clock_and_external_load_constraints':'UNCHANGED','additional_buffers_requested':0,'functional_architecture_change':False,
      'native_returncodes':{},'RC_STA_full_rules_function':'NOT_YET_EXECUTED','costs':'SEPARATE_DRIVE_SIZE_AND_MOVEMENT_NOT_PIN_XY_SAVING'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save();common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for lib in old['libs']:
        if Path(lib).is_file():common+=['--bind',lib+':'+lib+':ro']
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    def native(label,body,threads=8):
        script=out/(label+'.tcl');script.write_text(helper.replace('$out/stages.tsv','$out/'+label+'.stages.tsv')+'\n'+body+'\n')
        rc=execute(common,script,out/(label+'.log'),'PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=threads)
        rec['native_returncodes'][label]=rc;save()
        if rc:raise RuntimeError(label+' failed '+str(rc))
    try:
        libpath='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        text=subprocess.check_output(common+[IMAGE,'cat',libpath]).decode();rec['actual_Liberty_SHA256']=hashlib.sha256(text.encode()).hexdigest()
        assert rec['actual_Liberty_SHA256']=='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
        models=dict(groups(text,'cell'));families=defaultdict(list);caps={};logic={}
        for name,body in models.items():
            m=re.fullmatch(r'(.+)_X(\d+)',name)
            if not m:continue
            families[m[1]].append((int(m[2]),name))
            for pin,b in groups(body,'pin'):
                z=re.search(r'\bmax_capacitance\s*:\s*([\d.eE+-]+)',b)
                if z:caps[name,pin]=float(z[1])
            logic[name]=contract('cell ('+name+') {'+body+'}',name)
        native('original_native_inventory','read_db '+tcl(odb)+'\nfingerprint '+tcl(out/'before')+'\n'+COST_PROC+'\ncell_cost '+tcl(out/'before.cell_cost.tsv')+'\nclose $stages',threads=1)
        before,terms=read_cells(out/'before.cells.tsv')
        nonfill={r['instance'] for r in csv.DictReader((out/'before.cell_cost.tsv').open(),delimiter='\t') if r['type']!='CORE_SPACER'}
        terms={k:v for k,v in terms.items() if k[0] in nonfill};viol=defaultdict(dict);section=None
        for line in report.read_text().splitlines():
            if line.strip() in ['max slew','max capacitance','max fanout']:section=line.strip()
            if section not in ['max slew','max capacitance'] or '(VIOLATED)' not in line:continue
            p=line.split();assert len(p)>=5
            inst,pin=p[0].rsplit('/',1);assert inst in before and (inst,pin) in terms
            viol[inst][section]={'pin':pin,'limit':float(p[1]),'actual':float(p[2]),'native_line':line}
        selected={};inventory=[]
        for inst,checks in sorted(viol.items()):
            master=before[inst][0];m=re.fullmatch(r'(.+)_X(\d+)',master);target=None;candidates=[]
            if m:
                for strength,name in sorted(families[m[1]]):
                    if strength<=int(m[2]) or logic[name]!=logic[master]:continue
                    capok=all(caps.get((name,r['pin']),0)>=r['actual']*1.1 for kind,r in checks.items() if kind=='max capacitance')
                    slewok=all(strength>=int(m[2])*r['actual']/r['limit']*1.1 for kind,r in checks.items() if kind=='max slew')
                    candidates.append((strength,name,capok and slewok))
                fits=[n for strength,n,ok in candidates if ok]
                target=fits[0] if fits else candidates[-1][1] if candidates else None
            row={'instance':inst,'original_master':master,'actual_failures':checks,'new_master':target,
                 'status':'PROVEN_SAME_LOGIC_STATE_DRIVE_VARIANT_REQUIRES_REAL_ROUTE_CHECKS' if target else 'NO_STRONGER_IDENTICAL_LOGIC_STATE_FAMILY_NOT_FIXED',
                 'linear_slew_strength_estimate_is_selection_hint_not_STA_result':True}
            inventory.append(row)
            if target:selected[inst]=(master,target)
        assert selected;rec['all_actual_reported_driver_count']=len(viol);rec['requested_real_size_changes']=len(selected);rec['unrepaired_no_stronger_compatible_family']=len(viol)-len(selected)
        (out/'all_actual_violating_drivers_and_size_contracts.json').write_text(json.dumps(inventory,indent=2)+'\n');save()
        select='set selected [dict create]\n'+''.join('dict set selected '+tcl(n)+' '+tcl(new)+'\n' for n,(oldmaster,new) in selected.items())
        placement=select+'\nread_db '+tcl(odb)+r'''
set b [ord::get_db_block];set statuses [dict create];set filler_masters {}
foreach i [$b getInsts] {set name [$i getName];if {[[$i getMaster] getType] eq "CORE_SPACER"} {lappend filler_masters [[$i getMaster] getName];continue};dict set statuses $name [$i getPlacementStatus]}
set filler_masters [lsort -unique $filler_masters];remove_fillers
foreach i [$b getInsts] {set name [$i getName];if {[dict exists $selected $name]} {set m [[ord::get_db] findMaster [dict get $selected $name]];if {$m eq "NULL" || ![$i swapMaster $m]} {error "Size swap failed"};$i setPlacementStatus PLACED} else {$i setPlacementStatus LOCKED}}
if {![stage isolated_legalization {detailed_placement -use_diamond_legalizer;check_placement -verbose}]} {close $stages;exit 1}
dict for {name status} $statuses {[$b findInst $name] setPlacementStatus $status}
set f [open @@POSES@@ w];puts $f [list set filler_masters $filler_masters];dict for {name master} $selected {set i [$b findInst $name];lassign [$i getLocation] x y;puts $f [list lappend size_replay [list $name $master $x $y [$i getPlacementStatus]]]};close $f
fingerprint @@PLACED@@
write_db @@CHECKPOINT@@
close $stages
'''
        for a,b in [('@@POSES@@',tcl(out/'actual_size_poses.tcl')),('@@PLACED@@',tcl(out/'placed')),('@@CHECKPOINT@@',tcl(out/'placed_NOT_ROUTED.odb'))]:placement=placement.replace(a,b)
        native('isolated_geometry_size_and_legalization',placement)
        after,at=read_cells(out/'placed.cells.tsv');assert terms=={k:v for k,v in at.items() if k[0] in nonfill}
        assert all(n in after and (after[n][0]==selected[n][1] if n in selected else after[n]==before[n]) for n in nonfill)
        rec['isolated_all_signal_connections_and_nonselected_functional_poses_preserved']=True;save()
        guides=[source/'route.guide',ROOT/'trials'/TRIALS[case]/(case+'-C')/'route.guide']
        guide=next(p for p in guides if p.exists());inputs[str(guide)]=sha(guide)
        reservations=[Path(p) for p in old['input_sha256'] if p.endswith('/access_reservations.tcl')]
        for p in reservations:assert sha(p)==old['input_sha256'][str(p)];inputs[str(p)]=sha(p)
        lines=['read_liberty '+tcl(p) for p in old['libs']]+['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',COST_PROC,
          'set b [ord::get_db_block];set temporary_obs {};set original_obs [lsort [$b getObstructions]];set u [$b getDbUnitsPerMicron]']
        for p in reservations:lines+=['set access_reservations {};source '+tcl(p),'foreach r $access_reservations {lassign $r ly a c d e;set z {};foreach v [list $a $c $d $e] {lappend z [expr {round($v*$u)}]};lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$z]}']
        lines+=['set_routing_layers -signal metal2-metal8 -clock metal4-metal8','read_guides '+tcl(guide),
          'if {![stage begin_incremental {global_route -start_incremental}]} {close $stages;exit 1}',
          'remove_fillers;set size_replay {};source '+tcl(out/'actual_size_poses.tcl'),
          'if {![stage exact_verified_size_pose_replay {foreach r $size_replay {lassign $r name master x y status;set i [$b findInst $name];if {![$i swapMaster [[ord::get_db] findMaster $master]]} {error "Replay swap failed"};$i setLocation $x $y;$i setPlacementStatus $status};if {[llength $filler_masters]} {filler_placement -prefix PINXY_CURRENT_SIZE_FILL_ $filler_masters};global_connect;check_placement -verbose}]} {close $stages;exit 1}',
          'if {![stage incremental_global_route {global_route -end_incremental -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {close $stages;exit 1}',
          'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1}]} {close $stages;exit 1}',
          'foreach ob $temporary_obs {odb::dbObstruction_destroy $ob};if {[lsort [$b getObstructions]] ne $original_obs} {error "Original OBS changed"}',
          'fingerprint '+tcl(out/'after'),'cell_cost '+tcl(out/'after.cell_cost.tsv'),'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'source '+tcl(DRIVER/'export_access.tcl'),
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']
        native('real_route_RC_STA','\n'.join(lines))
        native('fresh_DRC','read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\nclose $stages',threads=1)
        rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M));rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        cells,ct=read_cells(out/'after.cells.tsv');assert {k:v for k,v in ct.items() if k[0] in nonfill}==terms
        assert all(cells[n][0]==selected[n][1] if n in selected else cells[n]==before[n] for n in nonfill)
        rec['exact_original_graph_with_only_proven_size_and_pose_changes']=True
        rec['pin_PG_die_preserved']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']};assert all(rec['pin_PG_die_preserved'].values())
        cost=lambda name:{r['instance']:r for r in csv.DictReader((out/(name+'.cell_cost.tsv')).open(),delimiter='\t') if r['type']!='CORE_SPACER'}
        a,b=cost('before'),cost('after');assert set(a)==set(b)
        rec['separate_ECO_cost']={'added_functional_cells':0,'sized_cells':len(selected),'moved_cells':sum((a[n]['x_dbu'],a[n]['y_dbu'])!=(b[n]['x_dbu'],b[n]['y_dbu']) for n in a),'master_bbox_area_delta_um2':sum(float(b[n]['area_um2'])-float(a[n]['area_um2']) for n in a),'block_outline_unchanged':True}
        for kind in ['setup','hold']:rec[kind+'_ns']=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',(out/(kind+'.txt')).read_text())[1])
        rec['literal_VIOLATED_markers_not_full_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['native_stages']={p.name:{r['stage']:r['status'] for r in csv.DictReader(p.open(),delimiter='\t')} for p in out.glob('*.stages.tsv')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or rec.get('fresh_DRC_count')!=0 or rec.get('setup_ns',-1)<0 or rec.get('hold_ns',-1)<0 or rec.get('literal_VIOLATED_markers_not_full_failure_count',1)>0 or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(*sys.argv[1:]))
