"""Actual source-derived one-net detailed routing ECO, not a LEF/plot edit."""
from pathlib import Path
import datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check
from compare_native_route_representations import routing_box_hashes

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'system_patch_route/r02/opentpu_aux-C';rp=source/'execution.json';prior=json.loads(rp.read_text())
    assert prior.get('completed_utc') and prior['fresh_DRC_count']==2 and prior['whole_signal_geometry']['pass']
    assert prior['native_returncodes']=={'implementation':0,'fresh_DRC':0} and prior['all_closed_sources_unchanged'] and prior['container_libraries_unchanged']
    assert all(prior['all_cells_poses_original_connections_pins_PG_die_unchanged'].values())
    odb=source/'routed.odb';geometry=source/'whole_access.tsv.gz';drc=source/'independent.drc'
    for p in [odb,geometry,drc]:assert sha(p)==prior['files'][p.name]['sha256']
    assert drc.read_text().count('net:_215139_')==2 and re.findall(r'violation type: ([^\n]+)',drc.read_text())==['Metal Spacing','NS Metal']
    trial=ROOT/'trials/access-r03/opentpu_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc'])
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    out=ROOT/'system_stacked_via_route'/revision/'opentpu_aux-C';out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,odb,geometry,drc,trial,sdc]}
    rec={'scope':'ACTUAL_ONE_NET_NATIVE_DETAILED_ROUTE_ENCODER_ECO_NOT_PIN_CHANGE_OR_FULL_QUALIFICATION',
      'source_SHA':inputs,'source_native_DRC_count':2,'target_net':'_215139_',
      'source_setup_ns':prior['setup_ns'],'source_hold_ns':prior['hold_ns'],
      'all_original_pin_layers_XY_sizes_cells_PG_constraints_requested_unchanged':True,
      'original_allowed_layers':'signal M2-M8; clock M4-M8; original M1 terminal via access retained',
      'via_policy':'Reuse actual original via1/via2 definitions and original terminal shapes; stack at original driver via Y only if both M1 landings fit actual terminals',
      'detailed_router_engine_rerun':False,'global_route_reexecuted':False,
      'implementation_method':'Native OpenDB detailed wire encoder, then independent original native DRC, whole connectivity, PG, RCX and original SDC STA',
      'original_failures_retained':True,'full_qualification':False,'native_returncodes':{},
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for p in old['libs']:
        if Path(p).is_file():common+=['--bind',p+':'+p+':ro']
    try:
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        rec['actual_typical_Liberty_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',lib]).decode().split()[0]
        assert rec['actual_typical_Liberty_SHA256']==prior['container_library_SHA256'][lib]
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        contracts=(DRIVER/'output_chain_placement.tcl').read_text().split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
        lines=[helper,contracts]+['read_liberty '+tcl(p) for p in old['libs']]
        lines+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),
          'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set_routing_layers -signal metal2-metal8 -clock metal4-metal8',
          'fingerprint '+tcl(out/'before'),'connection_contract '+tcl(out/'before.connections.tsv'),
          'set original_obs [obs_snapshot]',
          'if {![stage native_one_net_detailed_routing {source '+tcl(DRIVER/'stack_system_target_vias.tcl')+';write_db '+tcl(out/'routed_PENDING_CONTRACTS.odb')+'}]} {catch {write_db '+tcl(out/'failed_edit.odb')+'};close $stages;exit 1}',
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
        p=out/'route.tcl';p.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_returncodes']['detailed_edit_and_analysis']=execute(common,p,out/'native.log',env,threads=4);save()
        if (out/'routed.odb').exists():
            p=out/'fresh.tcl';p.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,p,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():
            rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
            count=prior['whole_signal_geometry']['checked_nets'];a,_=routing_box_hashes(geometry,count);b,_=routing_box_hashes(out/'whole_access.tsv.gz',count);assert set(a)==set(b)
            changed=[n for n in a if a[n]!=b[n]];rec['actual_changed_multiterminal_net_wire_via_box_multisets']=changed
            rec['all_other_exported_multiterminal_route_box_multisets_identical']=changed==['_215139_']
            rec['route_representation_scope']='All '+str(count)+' exported multi-terminal nets; duplicates retained; not geometric union, one-terminal unused-net proof or RC equivalence.'
            assert rec['all_other_exported_multiterminal_route_box_multisets_identical']
        rec['original_cells_poses_signal_connections_pins_PG_die_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','connections','pins','pdn','die']}
        if (out/'actual_detail_edit.json').exists():rec['actual_detail_edit']=json.loads((out/'actual_detail_edit.json').read_text())
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
    passed=('actual_failure' not in rec and rec['native_returncodes'].get('detailed_edit_and_analysis')==0 and rec.get('fresh_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and all(rec.get('original_cells_poses_signal_connections_pins_PG_die_unchanged',{}).values()) and rec.get('all_other_exported_multiterminal_route_box_multisets_identical') and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0 and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0 and rec['all_closed_sources_unchanged'] and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['VDD','VSS','rcx','sta','whole_signal_geometry']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
