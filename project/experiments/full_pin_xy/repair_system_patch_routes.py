"""Continue the actual routed SYSTEM with native clean-patches, no cell ECO.

The two source M2 violations remain in history. This is a routing algorithm
variant, not removal of a DRC check, pin migration or a timing relaxation.
"""
from pathlib import Path
import datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision,profile='system_clean_patches'):
    assert profile in ['system_clean_patches','mxu_M6_escape']
    mxu=profile=='mxu_M6_escape';case='mxu' if mxu else 'opentpu_aux'
    source=ROOT/('leaf_eco/r04/mxu-C' if mxu else 'output_chain_resume/r02/opentpu_aux-C')
    receipt=source/'execution.json';prior=json.loads(receipt.read_text())
    assert prior.get('completed_utc') and prior['fresh_DRC_count']==(0 if mxu else 2) and prior['whole_signal_geometry']['pass']
    if mxu:
        assert prior['native_returncode']==0 and prior['source_unchanged'] and all(prior['geometry_invariants'].values())
    else:
        assert prior['native_returncodes']['route']==0 and prior['all_sources_unchanged']
        assert all(prior['pin_PG_die_unchanged'].values())
    odb=source/'routed.odb';assert sha(odb)==prior['files'][odb.name]['sha256']
    drc=source/'independent.drc';assert sha(drc)==prior['files'][drc.name]['sha256']
    if not mxu:
        assert re.findall(r'violation type: ([^\n]+)',drc.read_text())==['Metal Spacing','NS Metal']
        assert drc.read_text().count('net:_215139_')==2
    original=ROOT/('trials/access-r03/'+case+'-C/execution.json');old=json.loads(original.read_text())
    sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
    source_inputs=old['input_sha256'] if mxu else prior['source_SHA']
    reservations=[Path(p) for p in source_inputs if p.endswith('/access_reservations.tcl')]
    assert len(reservations)==1 and sha(reservations[0])==source_inputs[str(reservations[0])]
    out=ROOT/('pin_escape_route' if mxu else 'system_patch_route')/revision/(case+'-C');out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [receipt,odb,drc,original,sdc,reservations[0]]}
    source_slacks={}
    for kind in ['setup','hold']:
        p=source/(kind+'.txt');assert sha(p)==prior['files'][p.name]['sha256']
        inputs[str(p)]=sha(p)
        source_slacks[kind]=float(re.search(r'worst slack (?:max|min)\s+([-\d.]+)',p.read_text())[1])
    guide=source/'route.guide';expected_lef=None
    if mxu:
        assert sha(guide)==prior['files'][guide.name]['sha256'];inputs[str(guide)]=sha(guide)
        view=ROOT/'eco_views/r02/mxu-C';vp=view/'execution.json';v=json.loads(vp.read_text())
        assert v.get('completed_utc') and sha(view/'clean.odb')==sha(odb)
        expected_lef=view/'abstract.lef';assert sha(expected_lef)==v['files'][expected_lef.name]['sha256']
        inputs.update({str(p):sha(p) for p in [vp,expected_lef]})
    # Standard-cell Liberty exists inside the original ORFS image, not on host.
    inputs.update({p:sha(Path(p)) for p in old['libs'] if Path(p).is_file()})
    allowed='metal2-metal10' if mxu else 'metal2-metal8';clocks='metal4-metal10' if mxu else 'metal4-metal8'
    rec={'scope':'ACTUAL_MXU_M6_ESCAPE_RING_PHYSICAL_REROUTE_NOT_OBS_DELETION_OR_PIN_CHANGE' if mxu else 'ACTUAL_SYSTEM_NATIVE_CLEAN_PATCHES_ROUTE_VARIANT_NOT_CELLS_OR_PIN_ECO_OR_QUALIFICATION',
      'profile':profile,'source_SHA':inputs,'source_native_DRC_count':prior['fresh_DRC_count'],'source_setup_ns':source_slacks['setup'],'source_hold_ns':source_slacks['hold'],
      'original_SDC_and_allowed_layers_unchanged':True,'original_failures_retained':True,
      'new_cells_sizing_pin_XY_changes_requested':0,'detailed_route_options':[] if mxu else ['-clean_patches'],
      'global_route_reexecuted':mxu,'full_qualification':False,'native_returncodes':{},
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for path in old['libs']:
        if Path(path).is_file():common+=['--bind',path+':'+path+':ro']
    def image_library_hashes():
        return {p:subprocess.check_output(common+[IMAGE,'sha256sum',p]).decode().split()[0] for p in old['libs'] if not Path(p).is_file()}
    try:
        rec['container_library_SHA256']=image_library_hashes();save()
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        contracts=(DRIVER/'output_chain_placement.tcl').read_text().split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
        commands=[helper,contracts]+['read_liberty '+tcl(p) for p in old['libs']]
        commands+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),
          'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'fingerprint '+tcl(out/'before'),'connection_contract '+tcl(out/'before.connections.tsv'),
          'set original_obs [obs_snapshot];set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]',
          'set access_reservations {};source '+tcl(reservations[0]),
          'set temporary_obs {};foreach row $access_reservations {lassign $row ly x0 y0 x1 y1;set coords {};foreach v [list $x0 $y0 $x1 $y1] {lappend coords [expr {round($v*$u)}]};lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$coords]}',
          'set_routing_layers -signal '+allowed+' -clock '+clocks,
          'if {![stage native_clean_patches {detailed_route -clean_patches -output_drc '+tcl(out/'route.drc')+' -verbose 1}]} {catch {write_db '+tcl(out/'failed_detail.odb')+'};close $stages;exit 1}',
          'foreach ob $temporary_obs {odb::dbObstruction_destroy $ob}',
          'if {[obs_snapshot] ne $original_obs} {error "Original OBS changed"}',
          'fingerprint '+tcl(out/'after'),'connection_contract '+tcl(out/'after.connections.tsv'),
          'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),'write_verilog '+tcl(out/'mapped.v'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}',
          'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}',
          'close $stages']
        if mxu:
            index=next(i for i,line in enumerate(commands) if line.startswith('if {![stage native_clean_patches '))
            ring='''set bt [$b findBTerm {act_data[12]}];if {$bt eq "NULL"} {error "Missing original MXU pin"}
set boxes {};foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {lappend boxes $box}}
if {[llength $boxes]!=1} {error "Original MXU pin is not one rectangle"};set box [lindex $boxes 0]
if {[[$box getTechLayer] getName] ne "metal6" || [$box xMax]-[$box xMin]!=280 || [$box yMax]-[$box yMin]!=280} {error "Original M6 pin layer or size changed"}
# Temporary routing keepout only, not a claim that all spacing rules are .14um.
set gap 280;set thick 280;set a [expr {[$box xMin]-$gap}];set c [expr {[$box yMin]-$gap}];set d [expr {[$box xMax]+$gap}];set e [expr {[$box yMax]+$gap}]
set ring [list [list [expr {$a-$thick}] [expr {$c-$thick}] $a [expr {$e+$thick}]] [list $d [expr {$c-$thick}] [expr {$d+$thick}] [expr {$e+$thick}]] [list $a [expr {$c-$thick}] $d $c] [list $a $e $d [expr {$e+$thick}]]]
set f [open RING_FILE w];puts $f "layer\\tx0\\ty0\\tx1\\ty1"
foreach rect $ring {puts $f [join [list metal6 {*}$rect] "\\t"];lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer metal6] {*}$rect]};close $f
set n [$bt getNet];set wire [$n getWire];if {$wire eq "NULL"} {error "Original target wire missing"};odb::dbWire_destroy $wire
set_nets_to_route [list [$n getName]]'''.replace('RING_FILE',tcl(out/'proposed_temporary_M6_ring.tsv'))
            commands[index:index]=['read_guides '+tcl(guide),
              'if {![stage begin_incremental {global_route -start_incremental}]} {close $stages;exit 1}',
              'if {![stage reserve_M6_escape_and_rip_actual_target {'+ring+'}]} {close $stages;exit 1}',
              'if {![stage incremental_global_route {global_route -end_incremental -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}']
            commands=[s.replace('stage native_clean_patches {detailed_route -clean_patches','stage detailed_route {detailed_route') for s in commands]
            index=commands.index('write_db '+tcl(out/'routed.odb'))+1
            commands[index:index]=['write_abstract_lef '+tcl(out/'abstract.lef'),'write_abstract_lef -bloat_factor 0 '+tcl(out/'detailed.lef')]
            rec['hypothesis']='Physically route act_data[12] from unchanged original M6 pin through permitted existing layers, clearing its M6 vicinity; re-export actual metal OBS. Do not cut occupied OBS, claim a zero-DRC parent, or say DRT only changes one net.'
            rec['temporary_keepout_gap_and_thickness_um']=.14
        script=out/'route.tcl';script.write_text('\n'.join(commands)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_returncodes']['implementation']=execute(common,script,out/'native.log',env,threads=4);save()
        if (out/'routed.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal '+allowed+' -clock '+clocks+'\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['all_cells_poses_original_connections_pins_PG_die_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','connections','pins','pdn','die']}
        if mxu and (out/'abstract.lef').exists():
            from lef_view_contract import parse,verify
            rec['new_actual_OBS_view_contract']=verify(out/'abstract.lef',out/'detailed.lef')
            rec['all_original_pins_and_size_in_actual_new_LEF_identical']=parse(expected_lef)[:2]==parse(out/'abstract.lef')[:2]
            assert rec['all_original_pins_and_size_in_actual_new_LEF_identical']
        for kind in ['setup','hold']:
            p=out/(kind+'.txt')
            if p.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:max|min)\s+([-\d.]+)',p.read_text())[1])
        if (out/'checks.txt').exists():rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
        if (out/'stages.tsv').exists():
            import csv
            with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    rec['container_libraries_unchanged']=image_library_hashes()==rec.get('container_library_SHA256')
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    passed=('actual_failure' not in rec and rec['native_returncodes'].get('implementation')==0 and rec.get('fresh_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and all(rec.get('all_cells_poses_original_connections_pins_PG_die_unchanged',{}).values()) and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0 and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0 and rec['all_closed_sources_unchanged'] and rec['container_libraries_unchanged'] and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['VDD','VSS','rcx','sta','whole_signal_geometry']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
