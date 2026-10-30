"""Publish immutable deadline receipts and source-bound current-state facts."""
from pathlib import Path
import argparse,datetime,gzip,hashlib,json,shutil

NAMES=['wire-candidate-metal-r01','pin-retention-consumers-r01','pin-retention-consumers-r02','upper-whole-net-search-r01','upper-whole-net-search-r02','upper-whole-net-search-r03','upper-local-component-search-r01','upper-cut-corner-r01','upper-cut-corner-r02','upper-cut-corner-r03','original-ram-mapping-r01','current-electrical-r01','current-electrical-r02','conservative-low-views-r01','conservative-native-check-r01','llsys-wire-pin-retention-r01','llsys13093-views-r01','native-patch-audit-r03-llaccel13093']

def publish(aux,out):
    names=NAMES+['current-common-deadline-r01','llsys-residual87-preflight-r01',
      'current-common-resume-r01','parent1011-firsthop-r02','llsys-residual87-preflight-r02',
      'common-def-import-r01','all13507-first-hop-r01','firsthop75-r01',
      'drive-sizing-llsys-r04','drive-sizing-vector-r04','common-parent-PG-local-r01','fair-boundary-source-inventory-r01']
    aux,out=Path(aux),Path(out);dest=out/'data/deadline_receipts';dest.mkdir(exist_ok=True)
    for name in names:
        source=aux/'gate_terminal_updates'/name;q=json.loads((source/'capture.json').read_text())
        assert q['source_completed_utc']
        for r in q['records']:
            data=(source/(r['name']+'.gz')).read_bytes();assert hashlib.sha256(data).hexdigest()==r['stored_sha256'] and hashlib.sha256(gzip.decompress(data)).hexdigest()==r['sha256']
        target=dest/name
        if target.exists():
            for p in source.rglob('*'):
                if p.is_file():assert (target/p.relative_to(source)).read_bytes()==p.read_bytes()
        else:shutil.copytree(source,target)
    def raw(name):return json.loads(gzip.decompress((dest/name/'execution.json.gz').read_bytes()))
    ll=raw('llsys-wire-pin-retention-r01');views=raw('llsys13093-views-r01');audit=raw('native-patch-audit-r03-llaccel13093');electrical=raw('current-electrical-r02');coarse=raw('conservative-native-check-r01');ram=raw('original-ram-mapping-r01')
    odbsha=ll['files']['routed.odb']['sha256'];assert odbsha=='c4947012b2396735c69f395446dede19472fbc9ba1329eb4b68407dd66c5c1ad'
    assert views['source_geometry_sha256']==odbsha and views['matching_all_signal_model_pins']==13507 and views['SPEF_replay_matches_source']
    assert next(v for p,v in audit['source_SHA'].items() if p.endswith('/routed.odb'))==odbsha and audit['native_counts']['native_decoder_RECT']==0
    assert electrical['cases']['llaccel_aux']['ODB_SHA256']==odbsha and not electrical.get('actual_failure')
    for label,folder in [('upper_local_failure_r02','local-upper-components-r02'),('upper_local_components_r03','local-upper-components-r03'),('upper_reserved_escape_r04','local-upper-components-r04'),('upper_minimal_bypass_r01','local-upper-native-bypass-r01'),('upper_simultaneous_flow_r01','local-upper-flow-r01'),('upper_simultaneous_flow_r02','local-upper-flow-r02')]:
        source=aux/folder/'execution.json';target=dest/(label+'.json');data=source.read_bytes()
        if target.exists():assert target.read_bytes()==data
        else:target.write_bytes(data)
    observation=max(aux.glob('native_phase_observation_*.json'),key=lambda p:p.name);obs=json.loads(observation.read_text());target=dest/observation.name
    if target.exists():assert target.read_bytes()==observation.read_bytes()
    else:shutil.copyfile(observation,target)
    common=raw('current-common-deadline-r01')
    common_log=gzip.decompress((dest/'current-common-deadline-r01/lower_route.log.gz').read_bytes()).decode()
    assert 'No access point for u_llaccel_aux/bit_1011' in common_log
    assert common['native_final_stage_status']['lower_global_route']=='EXECUTED' and common['native_final_stage_status']['lower_detailed_route']=='FAIL'
    mapping=aux/'inventory/pin_logical_mapping.json';mp=json.loads(mapping.read_text());assert mp['llaccel_aux']['bit_3005']['semantic_bus']=='bank_we' and mp['llaccel_aux']['bit_3005']['semantic_bit']==67
    facts={'schema':1,'scope':'CURRENT_DEADLINE_STAGE_FACTS_NOT_FULL_GOAL_QUALIFICATION','as_of_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'full_qualification':False,
      'current_LL':{'source':'llsys_wire_pin_retention/r01','ODB_SHA256':odbsha,'source_ODB':'/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/llsys_wire_pin_retention/r01/routed.odb','setup_ns':ll['setup_ns'],'min_slack_ns_includes_removal':ll['hold_ns'],'native_DRC_count':ll['fresh_DRC_count'],'whole_signal_geometry':ll['whole_signal_geometry'],'old10261_plus_new2832_access_edits':13093,'not_moved_from_original_A_count':True,'pin_contract':ll['complete_pin_contract'],'actual_metal_union_unchanged':ll['actual_metal_union_unchanged_from_source_wire_via_plus_original_BPins'],'all_existing_WIRE_VIA_plus_exact2827_old_pin_squares':ll['all_original_WIRE_VIA_exact_plus_only_2827_requested_old_pin_WIRE_squares'],'RECT_audit_native0':True,'matching13507_views_complete':True,'parent_AP':'NOT_VALIDATED','full_rules_GDS_RTL':'NOT_QUALIFIED','evidence':'data/deadline_receipts/llsys-wire-pin-retention-r01/execution.json.gz','coordinates':'data/deadline_receipts/llsys-wire-pin-retention-r01/all_13507_actual_pin_correspondence.csv.gz','views':'data/deadline_receipts/llsys13093-views-r01/execution.json.gz'},
      'electrical_cases':electrical['cases'],'electrical_evidence':'data/deadline_receipts/current-electrical-r02/execution.json.gz','LL_worst_function_mapping':{'instance':'output10580','pin':'Z','native_net':'bit_3005','master':'BUF_X1','semantic_interface':'bank_we[67]','function_zh':'把写入许可送往设计外部的存储接口；外部SRAM并未虚构为六块内部已实现硬件','source_mapping_SHA256':hashlib.sha256(mapping.read_bytes()).hexdigest()},
      'conservative_parent_native_readback':{'all_24767_and_PG':coarse['all_24767_signal_pins_and_PG_preserved'],'source_epoch':'Previous f0b2 LL plus other5 current sources; c494 source has separate new view and must be checked at parent import','evidence':'data/deadline_receipts/conservative-native-check-r01/execution.json.gz'},
      'original_RAM_mapping':{'source_RTL_SHA256':next(iter(ram['source_SHA'].values())),'actual_cells':ram['actual_mapped_statistics']['modules']['\\fakeram45_1r1w_64x64']['num_cells'],'actual_area_um2':ram['mapped_standard_cell_master_area_um2'],'original_abstract_area_um2':ram['original_abstract_area_um2'],'cannot_fit_this_mapping_in_original_outline':ram['drop_in_original_footprint_impossible_by_cell_area_alone'],'GDS_or_macro_replacement':'NOT_EXECUTED','evidence':'data/deadline_receipts/original-ram-mapping-r01/execution.json.gz'},
      'latest_native_phase_observation':obs,'observation_evidence':'data/deadline_receipts/'+observation.name,'upper_actual_two_Shorts_fixed':False,'geometric_solver_limits':'Bounded seven-net model infeasible; twelve measured-blocker-net model reached180s without feasible incumbent. Neither is a global physical impossibility proof; no native repair is claimed.','original_objective_complete':False}
    facts['common_base_actual_failure']={'completed_utc':common['completed_utc'],'job':'93460','stage':'lower_detailed_route','object':'u_llaccel_aux/bit_1011','semantic_interface':'dram_rsp_rdata[329]','function_zh':'把外部DRAM返回数据送入llaccel控制搬运块','native_error':'DRT-0073 No access point','layer':'metal5','local_xy_um':[340.015,1062.390],'current_c494_pin_unchanged':True,'PG_and_global_route':'EXECUTED','freeze_RC_STA_function':'NOT_EXECUTED','evidence':'data/deadline_receipts/current-common-deadline-r01/execution.json.gz','native_log':'data/deadline_receipts/current-common-deadline-r01/lower_route.log.gz'}
    imported=raw('common-def-import-r01');cause=raw('parent1011-firsthop-r02');risk=raw('all13507-first-hop-r01');sized=raw('drive-sizing-llsys-r04');pg=raw('common-parent-PG-local-r01')
    assert imported['native_returncodes']['fresh_import']==0 and all(imported['original_parent_preserved'].values()) and imported['all256_native_FIXED_status_preserved']
    assert sized['native_stages']['real_route_RC_STA.stages.tsv']['detailed_route']=='FAIL'
    facts['latest_engineering_trials']={
      'common_checkpoint_import':{'source':'common_checkpoint_def_import/r01','actual_native_import_and_PG':'EXECUTED','all_original_graph_PG_ports_poses_and256FIXED_preserved':True,'lower_route_freeze_RC_STA_functions':'NOT_EXECUTED_FOR_THIS_IMPORTED_CURRENT_SOURCE','evidence':'data/deadline_receipts/common-def-import-r01/execution.json.gz'},
      'macro_swap_crash':{'source':'common_current_resume/r01','native_returncode':-11,'phase':'current_master_swaps','root_cause':'Not proven; only macro swap API stage located. Fresh DEF import succeeds; do not repeat the crash path.','evidence':'data/deadline_receipts/current-common-resume-r01/execution.json.gz'},
      'bit1011_actual_first_hop':{'foreign_net':'net257248','layer':'metal6','actual_box_DBU':[679890,1830640,680170,2205000],'original_M5_center_DBU':[680030,2124780],'screened_target_center_DBU':[679470,2124780],'target_not_qualified_route':True,'evidence':'data/deadline_receipts/parent1011-firsthop-r02/execution.json.gz'},
      'all13507_first_hop_risks':{'status_counts':risk['status_counts'],'scope':'Actual first-hop geometry risk only; not8570 native DRC failures and not entire stack proof','evidence':'data/deadline_receipts/all13507-first-hop-r01/execution.json.gz'},
      'actual75_port_trial':{'stage':'native detailed route','failure':'DRT-1231 PIN/bit_3598 lacks access point; that pin was NOT among selected75. Original all-port AP gap persists.','new_source_not_promoted':True,'evidence':'data/deadline_receipts/firsthop75-r01/execution.json.gz'},
      'actual_LL_sizing':{'actual_sized_and_legalized':7438,'all_reported_drivers':7784,'no_stronger_compatible_family':346,'stage':'incremental GRT executed; native DRT failed at unchanged bit_3598 AP; no new RC/STA result','cost_is_separate_not_pure_XY':True,'evidence':'data/deadline_receipts/drive-sizing-llsys-r04/execution.json.gz'},
      'VECTOR_range_script_failure':{'actual_sized_and_legalized':75,'failure':'Wrong M2-M8 script range rejected original M9 guide _086937_; this is a trial script error, not a proof against original M2-M10','correction':'Original source fresh.tcl SHA-bound M2-M10 restored; closed75-size placement reused in93556, terminal result pending','evidence':'data/deadline_receipts/drive-sizing-vector-r04/execution.json.gz'},
      'actual_parent_PG_local':{'rows':pg['actual_parent_pg_local_rows'],'native_R0_transform':pg['actual_R0_transform'],'evidence':'data/deadline_receipts/common-parent-PG-local-r01/execution.json.gz'},
      'new_all_port_real_stubs':{'r01_job':'93557','r02_job':'93560','r03_job':json.loads((aux/'deadline_all_access_stubs_r03_submission.json').read_text())['job'],'scope':'Real native stub/XY edit under all13507 contract; single-terminal declarations must be proven and retained. Current qualification pending; do not promote by submission.'}}
    baseline=raw('fair-boundary-source-inventory-r01')
    assert baseline['all_sources_unchanged'] and all(all(baseline['cases'][case]['exact_resource_constraint_fingerprint_matches'].values()) for case in ['act','mxu','llaccel_aux'])
    facts['fair_boundary_source_checks']={'exact_cells_connections_poses_PG_die_SDC_matches':['act','mxu','llaccel_aux'],'same_resource_leaf_reuse_only_not_system_PPA':True,'remaining_not_yet_exact_byte_proven':['gemm','vector','opentpu_aux'],'evidence':'data/deadline_receipts/fair-boundary-source-inventory-r01/execution.json.gz'}
    facts['historical_native_phase_observation']=facts.pop('latest_native_phase_observation')
    (out/'data/deadline_engineering_receipts.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print('DEADLINE_STAGE_FACTS_PUBLISHED',len(names),'closed receipt groups; current LL',odbsha,'native0/STA failed; goal incomplete')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--aux',required=True);p.add_argument('--out',required=True);a=p.parse_args();publish(a.aux,a.out)
