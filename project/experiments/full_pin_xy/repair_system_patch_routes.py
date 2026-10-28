"""Continue the actual routed SYSTEM with native clean-patches, no cell ECO.

The two source M2 violations remain in history. This is a routing algorithm
variant, not removal of a DRC check, pin migration or a timing relaxation.
"""
from pathlib import Path
import datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'output_chain_resume/r02/opentpu_aux-C'
    receipt=source/'execution.json';prior=json.loads(receipt.read_text())
    assert prior.get('completed_utc') and prior['fresh_DRC_count']==2 and prior['whole_signal_geometry']['pass']
    assert prior['native_returncodes']['route']==0 and prior['all_sources_unchanged']
    assert all(prior['pin_PG_die_unchanged'].values())
    odb=source/'routed.odb';assert sha(odb)==prior['files'][odb.name]['sha256']
    drc=source/'independent.drc';assert sha(drc)==prior['files'][drc.name]['sha256']
    assert re.findall(r'violation type: ([^\n]+)',drc.read_text())==['Metal Spacing','NS Metal']
    assert drc.read_text().count('net:_215139_')==2
    original=ROOT/'trials/access-r03/opentpu_aux-C/execution.json';old=json.loads(original.read_text())
    sdc=Path(old['source_sdc']);assert sha(sdc)==old['input_sha256'][str(sdc)]
    reservations=[Path(p) for p in prior['source_SHA'] if p.endswith('/access_reservations.tcl')]
    assert len(reservations)==1 and sha(reservations[0])==prior['source_SHA'][str(reservations[0])]
    out=ROOT/'system_patch_route'/revision/'opentpu_aux-C';out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [receipt,odb,drc,original,sdc,reservations[0]]}
    inputs.update({p:sha(Path(p)) for p in old['libs']})
    rec={'scope':'ACTUAL_SYSTEM_NATIVE_CLEAN_PATCHES_ROUTE_VARIANT_NOT_CELLS_OR_PIN_ECO_OR_QUALIFICATION',
      'source_SHA':inputs,'source_native_DRC_count':2,'source_setup_ns':prior['setup_ns'],'source_hold_ns':prior['hold_ns'],
      'original_SDC_and_allowed_layers_unchanged':True,'original_failures_retained':True,
      'new_cells_sizing_pin_XY_changes_requested':0,'detailed_route_options':['-clean_patches'],
      'global_route_reexecuted':False,'full_qualification':False,'native_returncodes':{},
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
    try:
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        contracts=(DRIVER/'output_chain_placement.tcl').read_text().split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
        commands=[helper,contracts]+['read_liberty '+tcl(p) for p in old['libs']]
        commands+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),
          'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'fingerprint '+tcl(out/'before'),'connection_contract '+tcl(out/'before.connections.tsv'),
          'set original_obs [obs_snapshot];set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]',
          'set access_reservations {};source '+tcl(reservations[0]),
          'set temporary_obs {};foreach row $access_reservations {lassign $row ly x0 y0 x1 y1;set coords {};foreach v [list $x0 $y0 $x1 $y1] {lappend coords [expr {round($v*$u)}]};lappend temporary_obs [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$coords]}',
          'set_routing_layers -signal metal2-metal8 -clock metal4-metal8',
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
        script=out/'route.tcl';script.write_text('\n'.join(commands)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_returncodes']['implementation']=execute(common,script,out/'native.log',env,threads=4);save()
        if (out/'routed.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['all_cells_poses_original_connections_pins_PG_die_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','connections','pins','pdn','die']}
        for kind in ['setup','hold']:
            p=out/(kind+'.txt')
            if p.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:max|min)\s+([-\d.]+)',p.read_text())[1])
        if (out/'checks.txt').exists():rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
        if (out/'stages.tsv').exists():
            import csv
            with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    passed=('actual_failure' not in rec and rec['native_returncodes'].get('implementation')==0 and rec.get('fresh_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and all(rec.get('all_cells_poses_original_connections_pins_PG_die_unchanged',{}).values()) and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0 and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0 and rec['all_closed_sources_unchanged'] and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['VDD','VSS','rcx','sta','whole_signal_geometry']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
