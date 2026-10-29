"""Validate reported gate scope and numbers against immutable native receipts."""
from pathlib import Path
import gzip,hashlib,json,re


def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())


def check(out):
    data=out/'data';matrix=data/'qualification_matrix.json'
    if not matrix.exists():return
    j=read(matrix);rows={r['case']:r for r in j['blocks']}
    assert len(rows)==6 and sum(r['original_signal_pins'] for r in rows.values())==24767
    assert all(r['full_qualification'] is False and r['mapped_design_formal_equivalence']=='NOT_EXECUTED' for r in rows.values())
    assert not j['common_base_qualified_or_frozen'] and not j['two_complete_M11_M12_modes_implemented']
    native_files=0
    for index in (data/'gate_milestones').glob('gate-*/snapshot.json'):
        meta=read(index);assert not meta['full_qualification']
        for r in meta['records']:
            if r['storage']!='LOSSLESS_SNAPSHOT':continue
            p=index.parent/r['relative'];stored=p.read_bytes();raw=gzip.decompress(stored)
            assert hashlib.sha256(stored).hexdigest()==r['stored_sha256']
            assert hashlib.sha256(raw).hexdigest()==r['sha256'] and len(raw)==r['bytes']
            native_files+=1
    latest=out/j['source_snapshot'];assert latest.exists();folder=latest.parent
    for case in ['gemm','mxu']:
        failed=folder/'streamout/costed-r01'/(case+'-C_ECO');old=read(failed/'execution.json.gz')
        assert old['merge_returncode']==1 and old.get('DRC_returncode') is None
        assert 'Duplicate MACRO name:' in gzip.decompress((failed/'merge.log.gz').read_bytes()).decode()
        fixed=folder/'streamout/costed-r02'/(case+'-C_ECO');cfg=read(fixed/'reader_configuration.json.gz');inputs=read(fixed/'input.json.gz')
        assert cfg['read_lef_with_def_before'] is True and cfg['read_lef_with_def_after'] is False
        assert cfg['explicit_LEFs_roundtrip_exact'] and cfg['explicit_LEFs']==inputs['lefs']
        merge=read(fixed/'merge.json.gz');assert merge['allow_empty']=='DISABLED' and merge['no_missing_macro_waiver']
        gds_source=rows[case].get('historical_source_before_M6_escape',rows[case])
        assert gds_source['strict_GDS_merge_errors']==merge['merge_errors']
        if case=='gemm':assert merge['merge_errors']==0
        else:assert merge['merge_errors']==4 and gds_source['complete_rules'].startswith('FAILED_STRICT_GDS')
        version='r03' if case=='gemm' else 'r04'
        paths=sorted((data/'continuation/resume').glob('resume-*/leaf_eco/'+version+'/'+case+'-C/execution.json.gz'));assert paths
        physical=read(paths[-1]);assert rows[case]['native_DRC_count']==physical['fresh_DRC_count']==0
        for kind in ['setup','hold']:
            text=gzip.decompress((paths[-1].parent/(kind+'.txt.gz')).read_bytes()).decode()
            historical=rows[case].get('historical_source_before_M6_escape',rows[case].get('historical_matched_costed_source_before_diode',rows[case]))
            value=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',text)[1]);assert historical[kind+'_ns']==value
        if (fixed/'execution.json.gz').exists():
            end=read(fixed/'execution.json.gz')
            assert gds_source.get('historical_costed_GDS_findings_before_diode',gds_source['available_deck_findings'])==end.get('available_deck_findings')
            assert not end['full_qualification']
    ll=rows['llaccel_aux'];oldll=ll.get('historical_source_before_actual_via_tips',ll)
    assert oldll['native_DRC_count']==4 and oldll['newer_attempt']['three_pin_job'].endswith('FAILED_DRT_1231')
    if ll.get('historical_source_before_actual_via_tips'):
        q=next(q for q in j['LLSYSTEM_actual_three_pin_via_tip_attempts'] if q['revision']=='r02')
        assert q['completed_utc'] and q['native_returncodes']=={'actual_edit_and_analysis':0,'fresh_DRC':0}
        assert ll['completed_source']=='actual_via_tips/r02' and ll['native_DRC_count']==q['fresh_DRC_count']==0
        assert q['whole_signal_geometry']['pass'] and q['whole_signal_geometry']['checked_nets']==725253 and q['whole_signal_geometry']['checked_terminals']==2325528 and q['whole_signal_geometry']['checked_shapes']==28517815
        assert q['complete_pin_contract']['all_signal_pins']==13507 and q['complete_pin_contract']['only_changed_XY_pins']==['bit_1382013','bit_1389626','bit_6907']
        assert q['complete_pin_contract']['all_functions_directions_networks_layers_sizes_and_PG_preserved']
        assert q['all_other_725250_multiterminal_route_box_multisets_identical'] and q['exactly_eight_actual_WIRE_rectangles_removed_no_added_wire_or_via_material'] and q['all_actual_target_via_rectangle_multisets_preserved']
        assert all(q['all_cells_signal_connections_PG_die_unchanged'].values()) and q['all_closed_sources_unchanged'] and q['container_library_unchanged']
        assert ll['setup_ns']==q['setup_ns']==-3.909029 and ll['hold_ns']==q['hold_ns']==-0.587515 and ll['violation_marker_rows']==q['literal_VIOLATED_markers_not_complete_failure_count']==8876
        expected_model='SOURCE_BOUND_ACTUAL_RCX_REPLAY_VERIFIED_MINIMUM_PERIOD_MISSING' if j.get('LLSYSTEM_current_actual_tip_views',{}).get('completed_utc') else 'NOT_EXPORTED'
        assert ll['current_source_research_model']==expected_model and 'NOT_VALIDATED' in ll['parent_access'] and not ll['full_qualification']
    system=folder/'checkpoint_route/r01/execution.json.gz'
    if system.exists() and read(system).get('completed_utc'):
        q=read(system);assert not q['full_qualification'] and q['native_returncode']==0 and q['fresh_DRC_count']==0
        assert q['source_unchanged'] and all(q['geometry_invariants'].values()) and q['whole_signal_geometry']['pass']
        historical=rows['opentpu_aux'].get('historical_source_before_existing_buffer_relocation',rows['opentpu_aux'])
        assert historical['completed_source']=='costed_ECO/isolated-route-r01'
        for kind in ['setup','hold']:
            t=gzip.decompress((system.parent/(kind+'.txt.gz')).read_bytes()).decode()
            value=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',t)[1]);assert historical[kind+'_ns']==value<0
        assert historical['violation_marker_rows']==gzip.decompress((system.parent/'checks.txt.gz').read_bytes()).decode().count('(VIOLATED)')
    parents={r['version']:r for r in j.get('selected_parent_fixture_terminal_receipts',[])}
    for case,plan,errors,nets in [('gemm','Aopt',0,3753),('mxu','Aopt',5,2172),('mxu','C',2,2172)]:
        relative='escape_fixtures/'+('gemm-r01' if case=='gemm' else 'mxu-r01')+'/'+case+'-'+plan
        if relative not in parents:continue
        r=parents[relative];assert r['native_DRC']==errors and r['signal_geometry'] is True and r['both_PG_native_log_connected'] is True
        assert r['signal_nets_checked']==nets and r['parent_M10_accesses']==256
        drc=folder/relative/'independent.drc.gz';text=gzip.decompress(drc.read_bytes()).decode()
        assert len(re.findall(r'^violation type:',text,re.M))==errors
    for r in j.get('optimized_boundary_same_ECO_controls',[]):
        p=out/r['evidence'];q=read(p)
        assert r['native_DRC']==q['fresh_DRC_count']==0 and r['whole_signal_geometry'] is True
        assert all(r['geometry_invariants'].values()) and r['source_unchanged'] and not r['full_qualification']
        assert len(r['targeted_master_changes'])=={'gemm':3,'mxu':1}[r['case']]
        for kind in ['setup','hold']:
            t=gzip.decompress((p.parent/(kind+'.txt.gz')).read_bytes()).decode()
            assert r[kind+'_ns']==float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',t)[1])>0
    audit=j.get('antenna_checker_disagreement')
    if audit:
        q=read(out/audit['evidence']);assert q['native_returncode']==0 and q['source_unchanged'] and 'ANTENNA_X1' in q['actual_diode_liberty_cells']
        text=gzip.decompress(((out/audit['evidence']).parent/'native.log.gz').read_bytes()).decode()
        assert 'Found 0 net violations' in text and 'Found 0 pin violations' in text
        historical=rows['gemm'].get('historical_costed_GDS_findings_before_diode',rows['gemm']['available_deck_findings'])
        assert audit['GDS_deck_findings_not_repaired']==historical==1460
    for r in j.get('whole_mapped_relative_digital_contracts',[]):
        q=read(out/r['evidence']);assert q['relative_mapped_digital_contract_pass'] and q['all_sources_unchanged']
        assert q['same_all_top_ports_directions_and_networks'] and q['same_nonfiller_instance_set']
        assert q['same_all_signal_clock_reset_constant_terminals_and_networks'] and q['changed_masters_exact_Liberty_logic_state_contract']
        assert q['native_export_codes']==[0,0] and q['RTL_equivalence']=='NOT_EXECUTED' and not q['full_qualification']
        assert len(q['changed_masters'])=={'gemm':3,'mxu':1}[r['case']]
        assert rows[r['case']]['whole_mapped_relative_digital_contract'] is True
    if j.get('native_antenna_coverage_audit'):
        q=j['native_antenna_coverage_audit'];assert q['source_unchanged'] and q['native_returncode']==0
        assert len(q['layer_rules'])==10 and all(r['has_default_antenna_rule']==r['has_oxide2_rule']=='0' for r in q['layer_rules'])
        assert q['source_macro_LEF_has_gate_area'] is False
    if j.get('new_SYSTEM_costed_view'):
        q=j['new_SYSTEM_costed_view'];assert q['native_export_returncode']==0 and q['matching_all_signal_model_pins']==2229
        assert q['all_original_signal_and_PG_pins_and_size_exactly_preserved'] and q['SPEF_replay_matches_source']
        cost=q['separate_cell_ECO_cost'];assert cost['same_original_macro_resources_and_placement']
        assert cost['added_functional_instances_excluding_fillers']==5829 and cost['changed_master_original_instances']==980
        assert cost['moved_original_instances']==1168 and not q['full_qualification']
    for r in j.get('new_actual_integration_views',[]):
        q=read(out/r['evidence']);assert r['native_export_returncode']==0 and not r['full_qualification']
        if 'llaccel_aux' in r['version']:
            assert r['signal_bits']==13507 and r['source_native_DRC']==4
            assert r['status']=='UNQUALIFIED_FAILED_DRC_SOURCE_EXTRACTED_MODEL_EXPORTED'
            assert q['explicit_unqualified_failed_DRC_source_export'] and q['exact_all_signal_pin_direction_match']
    probes=j.get('fixed_signal_wire_native_API_probes',[])
    if probes:
        assert [(r['revision'],r['native_returncode']) for r in probes]==[('r01',1),('r02',0)]
        assert probes[-1]['DEF_fixed_M10_wire'] is True
        source=(out/probes[-1]['evidence']).parent/'fixed.def.gz'
        assert '+ FIXED metal10' in gzip.decompress(source.read_bytes()).decode()
        assert not j['actual_common_integration_trial']['qualified'] and not j['actual_common_integration_trial']['frozen']
    for r in j.get('same_ECO_actual_leaf_DRT_metrics',[]):
        raw=gzip.decompress((out/r['evidence']).read_bytes());text=raw.decode()
        assert hashlib.sha256(raw).hexdigest()==r['source_native_log_uncompressed_SHA256']
        assert float(re.findall(r'Total wire length = ([\d.]+) um\.',text)[-1])==r['DRT_reported_wire_length_um']
        assert int(re.findall(r'Total number of vias = (\d+)\.',text)[-1])==r['DRT_reported_vias']
        assert set(r['DRT_reported_per_layer_wire_length_um'])=={'metal'+str(i) for i in range(1,11)}
        assert r['not_geometric_endpoint_L1'] and r['not_extracted_RC_or_system_gain']
    if j.get('VECTOR_filler_order_control',{}).get('receipt'):
        q=j['VECTOR_filler_order_control']['receipt'];assert q['native_returncode']==0 and q['all_sources_unchanged']
        assert q['fillers_removed_before_estimation'] and not q['full_qualification']
        assert j['VECTOR_isolated_estimator_trial']['receipt']['native_returncode']==1
    if j.get('actual_six_resource_placement'):
        assert j['actual_six_resource_placement']['actual_instances']==44 and not j['actual_six_resource_placement']['full_qualification']
    if j.get('VECTOR_checkpoint_resume_submission'):
        r=j['VECTOR_checkpoint_resume_submission'];s=read(out/r['evidence'])
        p=(out/r['evidence']).parent/'vector_resume_r01.execution.json.gz';raw=gzip.decompress(p.read_bytes());q=json.loads(raw)
        assert hashlib.sha256(raw).hexdigest()==s['initial_execution_uncompressed_SHA256']
        assert q['scheduler_job']==s['job']==r['job']=='92872' and q['driver_commit']==s['head']==r['source_driver_commit']
        assert q['repair_design_repeated'] is False and q['full_qualification'] is False
        assert q['original_SDC_clocks_loads_and_allowed_layers_preserved'] and not r['full_qualification']
    if j.get('SYSTEM_directed_buffer_relation'):
        r=j['SYSTEM_directed_buffer_relation'];q=read(out/r['evidence']);s=q['summary']
        assert q['relative_mapped_digital_contract_pass'] and q['all_sources_unchanged'] and q['native_export_codes']==[0,0]
        assert s['added_identity_buffers']==5829 and s['resized_original_instances']==980 and s['original_signal_terminals']==1539803
        assert s['original_nonfiller_instances']==438852 and s['actual_nonfiller_instances']==444681 and s['null_terminals_checked_individually']==9723
        assert s['directed_original_driver_reachability'] and s['added_buffer_graph_acyclic']
        assert q['RTL_formal_equivalence']=='NOT_EXECUTED' and not q['full_qualification']
        assert rows['opentpu_aux']['whole_mapped_relative_digital_contract'] is True
    if j.get('actual_GDS_antenna_correlations'):
        q=j['actual_GDS_antenna_correlations'];s=q['correlation_summary']
        assert q['native_returncode']==0 and q['all_sources_unchanged'] and not q['full_qualification']
        assert s['marker_count']==1460 and s['mapping_status_counts']=={'UNIQUE_EXACT_POLYGON_CONDUCTOR_CORRELATION':1460} and s['unique_correlated_net_count']==636
        assert s['bbox_only_assignment_used'] is False and not s['original1460_findings_repaired'] and not s['functional_or_LVS_proof']
        assert s['diode_inventory']['actual_standard_GDS_cell_nonempty'] and s['diode_inventory']['diode_recognition_area_um2']>0
        assert s['diode_inventory']['diode_contact_overlap_area_um2']>0
    if j.get('MXU_M6_bounded_ownership'):
        q=j['MXU_M6_bounded_ownership'];assert q['old_and_costed_leaf_all_exported_M6_rectangles_and_net_labels_equal']
        assert q['original_parent_native_DRC_count_retained']==2 and q['gap_is_not_a_rule_pass'] and not q['full_qualification']
    if j.get('VECTOR_physical_resume_latest',{}).get('terminal_receipt'):
        q=read(out/j['VECTOR_physical_resume_latest']['evidence']);r=rows['vector']
        assert q['fresh_DRC_count']==0 and q['whole_signal_geometry']['pass'] and q['whole_signal_geometry']['checked_nets']==375675
        assert q['setup_ns']==r['setup_ns']==-4.14022 and q['hold_ns']==r['hold_ns']==0.037989
        assert r['violation_marker_rows']==83 and r['completed_source']=='costed_VECTOR_resume/r01'
        assert all(q['source_pin_PG_die_unchanged'].values()) and q['all_sources_unchanged'] and not r['full_qualification']
        assert q['separate_cell_ECO_cost']['added_functional_instances_excluding_fillers']==180
    for q in j.get('latest_actual_extracted_path_audits',[]):
        assert q['native_returncode']==0 and q['all_sources_unchanged'] and all(q['source_worst_slacks_exactly_replayed'].values())
        assert not q['full_qualification']
    if j.get('actual_critical_path_diagnosis'):
        q=j['actual_critical_path_diagnosis'];assert not q['full_qualification'] and q['original_clock_constraints_unchanged']
        for r in q['paths']:
            p=folder/'actual_path_audit/r01'/r['case']/'setup_paths.json.gz';raw=gzip.decompress(p.read_bytes())
            assert hashlib.sha256(raw).hexdigest()==r['actual_setup_path_JSON_uncompressed_SHA256']
            assert abs(r['cell_arc_increment_ns']+r['net_arc_increment_ns']-r['endpoint_arrival_ns']+r['launch_Q_arrival_ns'])<1e-9
    if j.get('GEMM_real_diode_ECO'):
        q=j['GEMM_real_diode_ECO'];assert not q['full_qualification']
        r=q['receipt'];assert r['original_antenna_findings']==1460 and r['actual_correlated_native_nets']==636
        assert r['original_antenna_rules_unchanged'] and r['no_fake_gate_or_diffusion_area']
        lib=r.get('actual_diode_Liberty_contract')
        if lib:assert lib['capacitive_load_unit']==['1','ff'] and lib['actual_input_capacitance']>0 and lib['single_input_only_no_output_function_or_state']
        if r.get('completed_utc'):
            assert r['fresh_DRC_count']==0 and r['whole_signal_geometry']['checked_nets']==268637 and r['whole_signal_geometry']['pass']
            assert r['original_functional_instances_pose_and_terminal_contract_unchanged'] and all(r['unchanged_geometry'].values())
            assert q['setup_ns']==0.770727 and q['hold_ns']==0.0395 and q['literal_VIOLATED_markers_not_complete_failure_count']==2
            assert {x['pin'] for x in q['max_capacitance_failures']}=={'_328822_/ZN','_332783_/ZN'}
            assert all(x['slack_ff']<0 and x['cap_ff']>x['limit_ff'] for x in q['max_capacitance_failures'])
            assert abs(r['separate_diode_cost']['master_bbox_area_um2']-169.176)<1e-6
    if j.get('GEMM_passive_load_digital_relation'):
        q=j['GEMM_passive_load_digital_relation'];s=q['summary']
        assert q['relative_mapped_digital_contract_pass'] and q['all_stable_geometry_and_source_files_unchanged']
        assert q['native_export_codes']==[0,0] and q['electrical_target_export_returncode']==0
        assert s['original_nonfiller_instances']==226775 and s['original_signal_terminals']==826710 and s['top_ports']==3753
        assert s['added_real_diode_cells']==s['added_non_driving_input_loads']==636
        assert s['actual_input_capacitance']>0 and s['original_all_signal_terminal_and_port_graph_exactly_equal']
        assert q['RTL_formal_equivalence']=='NOT_EXECUTED' and not q['full_qualification']
    if j.get('GEMM_real_diode_GDS_available_deck'):
        q=j['GEMM_real_diode_GDS_available_deck'];assert q['merge_returncode']==q['DRC_returncode']==0
        assert q['available_deck_findings']==sum(q['available_deck_findings_by_category'].values())==37
        assert all('ANTENNA' in k for k in q['available_deck_findings_by_category']) and not q['full_qualification']
        old=j['GEMM_real_diode_ECO']['receipt'];assert q['source_DEF_SHA']==old['files']['routed.def']['sha256']
        assert q['source_receipt_and_DEF_unchanged'] and j['GEMM_real_diode_ECO']['original1460_repair_not_yet_verified']
    if j.get('GEMM_post_diode_size_ECO',{}).get('completed_utc'):
        q=j['GEMM_post_diode_size_ECO'];assert q['native_returncodes']['implementation']==q['native_returncodes']['fresh_DRC']==q['native_returncodes']['relative_graph_export']==0
        assert q['fresh_DRC_count']==0 and q['whole_signal_geometry']['pass'] and all(q['pin_PG_die_unchanged'].values())
        assert q['setup_ns']==0.770752 and q['hold_ns']==0.039624 and q['literal_VIOLATED_markers_not_complete_failure_count']==0
        assert q['all_original_signal_terminal_and_port_graph_equal_with_exact_two_proven_sizes'] and q['retained_real_diode_count']==636
        assert q['all_sources_unchanged'] and not q['full_qualification']
        cost=q['separate_two_size_ECO_cost'];assert cost['changed_masters']==2 and cost['moved_existing_instances']==1 and cost['added_functional_instances']==0 and abs(cost['standard_cell_master_bbox_area_delta_um2']-1.33)<1e-6
        r=rows['gemm'].get('historical_636diode_two_size_source',rows['gemm'])
        assert r['completed_source']=='costed_real_diode_and_sizes/r01'
        assert r['setup_ns']==q['setup_ns'] and r['hold_ns']==q['hold_ns']
    if j.get('GEMM_post_diode_size_GDS_available_deck',{}).get('completed_utc'):
        q=j['GEMM_post_diode_size_GDS_available_deck'];assert q['merge_returncode']==q['DRC_returncode']==0
        assert q['available_deck_findings']==37 and q['source_DEF_SHA']==j['GEMM_post_diode_size_ECO']['files']['routed.def']['sha256']
        r=rows['gemm'].get('historical_636diode_two_size_source',rows['gemm'])
        assert r['available_deck_findings']==37 and not q['full_qualification']
    if j.get('GEMM_remaining_antenna_native_correlations'):
        q=j['GEMM_remaining_antenna_native_correlations'];a=q['correlation_summary']
        assert q['native_returncode']==0 and q['all_sources_unchanged'] and not q['full_qualification']
        assert a['marker_count']==37 and a['mapping_status_counts']=={'UNIQUE_EXACT_POLYGON_CONDUCTOR_CORRELATION':37}
        assert a['unique_correlated_net_count']==22 and len(a['mapped_nets_without_existing_real_diode'])==22 and a['mapped_nets_already_with_real_diode']==[]
    if j.get('GEMM_additional22_diode_actual_attempt'):
        q=j['GEMM_additional22_diode_actual_attempt'];assert not q['full_qualification']
        assert q['previous_real_diodes']==636 and q['requested_additional_real_diodes']==22
        assert q['no_full_signal_clock_wire_rip_requested'] and q['DRT_not_claimed_22_net_only']
        if q.get('native_returncodes',{}).get('implementation')==0:
            p=(out/q['evidence']).parent;stages=gzip.decompress((p/'stages.tsv.gz').read_bytes()).decode()
            for stage in ['actual_diode_insert','diode_legalization','global_route','detailed_route','preserve_original_views','VDD','VSS','whole_signal_geometry','rcx','sta']:
                assert stage+'\tEXECUTED\t' in stages
            partial=q['closed_native_implementation_STA_reports_not_fresh_DRC_or_final_graph']
            for kind in ['setup','hold']:
                text=gzip.decompress((p/(kind+'.txt.gz')).read_bytes()).decode()
                assert partial[kind+'_ns']==float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',text)[1])
        if q.get('completed_utc'):
            assert q['fresh_DRC_count']==0 and q['whole_signal_geometry']['pass'] and q['whole_signal_geometry']['checked_terminals']==806643
            assert q['actual_total_real_diodes']==658 and q['all_original_instances_and_signal_graph_preserved_with_only_22_real_diode_loads']
            assert q['all_prior_functional_and_636_diode_poses_and_terminals_unchanged'] and all(q['pin_PG_die_unchanged'].values())
            assert q['setup_ns']==rows['gemm']['setup_ns']==0.770702 and q['hold_ns']==rows['gemm']['hold_ns']==0.039533
            assert q['literal_VIOLATED_markers_not_complete_failure_count']==0 and q['separate_additional_diode_cost']['master_bbox_area_um2']==5.852
            assert rows['gemm']['completed_source']=='658_real_diodes/r01'
            if not j.get('GEMM_actual658_diode_strict_GDS_available_deck',{}).get('completed_utc'):assert rows['gemm']['available_deck_findings'] is None
            assert j.get('actual_22_diode_access_figure') and (out/'assets/gemm_real_diode_access.png').exists() and (out/'assets/gemm_real_diode_access.svg').exists()
    if j.get('actual_22_diode_access_figure'):
        q=j['actual_22_diode_access_figure'];assert q['old_GDS_findings']==37 and q['new_actual_diodes']==22 and q['unchanged_original_signal_pins']==3753
        assert abs(q['new_master_bbox_area_um2']-5.852)<1e-6 and not q['full_qualification']
    if j.get('upper_all770_actual_hook_preparation_r02'):
        q=j['upper_all770_actual_hook_preparation_r02'];assert q['actual_hook_boxes']==1541 and q['per_mode_edges']==770
        assert q['native_via10_M10_landing_size_dbu']==[1600,1600] and not q['full_qualification']
        assert set(q['native_clock_net_aliases'])=={'opentpu:2:external_clock','llaccel:2:external_clock'}
    if j.get('upper_all770_actual_terminal_r02'):
        q=j['upper_all770_actual_terminal_r02'];assert q['same_real_partial_lower_input_for_both_modes'] and q['all_preparation_sources_unchanged']
        assert not q['full_qualification'] and not q['qualified_common_base'] and not q['two_complete_M11_M12_systems']
        for mode in ['opentpu','llaccel']:
            r=next(r for r in q['modes'] if r['mode']==mode);assert r['native_route_returncode']==1
            assert r['independent_DRC_count'] is None and r['actual_770_native_edge_terminal_bijection'] is None
            p=(out/q['evidence']).parent/mode
            assert 'GRT-0116' in gzip.decompress((p/'global_route.error.txt.gz').read_bytes()).decode()
            actual=read(p/'execution.json.gz');assert actual['native_route_returncode']==1 and actual['completed_utc']
            assert 'routed_adapter_NOT_SYSTEM.odb' not in actual['files']
            stages=gzip.decompress((p/'stages.tsv.gz').read_bytes()).decode()
            assert 'global_route\tFAIL\tGRT-0116' in stages and 'detailed_route\tEXECUTED' not in stages
    if j.get('VECTOR_exact_Liberty_table_grid_diagnosis'):
        q=j['VECTOR_exact_Liberty_table_grid_diagnosis'];assert not q['full_qualification'] and not q['is_zero_wire_lower_bound'] and not q['is_timing_repair_or_proof_infeasible']
        assert q['actual_cell_arc_count']==141 and abs(q['actual_extracted_cell_arrival_increment_sum_ns']-6.7401)<1e-6
        assert q['actual_Liberty_SHA256']=='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
        assert q['masters_on_path_with_no_exact_function_family_size_alternative']==['FA_X1','HA_X1','OAI33_X1']
    if j.get('native_GRT_capability_r02'):
        q=j['native_GRT_capability_r02'];p=(out/q['evidence']).parent
        assert q['native_returncode']==0 and q['no_active_process_attach_signal_or_input_mutation'] and not q['full_qualification']
        body=gzip.decompress((p/'global_route.body.tcl.gz').read_bytes()).decode();log=gzip.decompress((p/'native.log.gz').read_bytes()).decode()
        assert 'if { [info exists keys(-guide_file)] } {' in body and 'info eif' not in body
        assert 'BODY_COMPLETE global_route 1' in log and '0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53' in log
    if j.get('actual_whole_net_routing_box_comparison'):
        q=j['actual_whole_net_routing_box_comparison'];assert q['all_closed_source_geometry_and_receipts_unchanged'] and not q['full_qualification']
        a,b=q['comparisons'];assert a['actual_nets']==b['actual_nets']==268637
        assert a['counts']=={'identical':268622,'different_representation':15}
        assert b['counts']=={'identical':268560,'different_representation':77}
        assert b['by_target_group']['new_22_diode_net:different_representation']==22
        assert b['by_target_group']['previous_636_diode_net:different_representation']==2
        assert b['by_target_group']['other_original_net:different_representation']==53
    if j.get('GEMM_actual658_diode_physical_and_extracted_views',{}).get('completed_utc'):
        q=j['GEMM_actual658_diode_physical_and_extracted_views'];assert not q['full_qualification'] and 'actual_failure' not in q
        assert q['native_export_returncode']==q['fresh_model_read_returncode']==0 and q['matching_all_signal_model_pins']==3753
        assert q['SPEF_replay_matches_source'] and q['all_original_signal_and_PG_pins_and_size_exactly_preserved']
        assert q['all_sources_and_pre_RCX_geometry_unchanged'] and q['minimum_period_present'] is False
        source=j['GEMM_additional22_diode_actual_attempt']
        assert q['source_receipt_SHA256']==hashlib.sha256(gzip.decompress((out/source['evidence']).read_bytes())).hexdigest()
        assert q['source_geometry_sha256']==source['files']['routed.odb']['sha256'] and q['source_SPEF_sha256']==source['files']['extracted.spef']['sha256']
        assert '92997实际研究视图已导出' in (out/'report.html').read_text(encoding='utf-8')
    if j.get('GEMM_actual658_diode_strict_GDS_available_deck',{}).get('completed_utc'):
        q=j['GEMM_actual658_diode_strict_GDS_available_deck'];source=j['GEMM_additional22_diode_actual_attempt']
        assert q['source_kind']=='incremental' and q['source_receipt_and_DEF_unchanged'] and not q['full_qualification']
        assert q['source_DEF_SHA']==source['files']['routed.def']['sha256'] and q['source_native_DRC_count']==0
        assert q['source_receipt_SHA']==hashlib.sha256(gzip.decompress((out/source['evidence']).read_bytes())).hexdigest()
        assert q['strict_allow_empty']=='DISABLED' and not q['missing_SRAM_geometry_fabricated']
        assert q['merge_returncode']==q['DRC_returncode']==0
        assert q['available_deck_findings']==sum(q['available_deck_findings_by_category'].values())==rows['gemm']['available_deck_findings']==0
        import xml.etree.ElementTree as ET
        actual_rdb=(out/q['evidence']).parent/'diagnostic.lyrdb.gz'
        assert len(ET.fromstring(gzip.decompress(actual_rdb.read_bytes())).findall('.//item'))==0
    if j.get('upper_fullframe_two_edge_tool_diagnosis',{}).get('completed_utc'):
        q=j['upper_fullframe_two_edge_tool_diagnosis'];assert not q['full_qualification'] and q['subset_edges']==2 and q['original_mode_edges']==770
        assert q['fresh_DRC_count']==0 and q['only_two_selected_edge_geometry']['checked_nets']==2 and q['only_two_selected_edge_geometry']['pass']
        assert q['actual_four_selected_M10_hook_rectangles_unchanged'] and q['entire_original_overlay_M10_PG_OBS_constraint_set_preserved']
        assert q['all_closed_source_geometry_files_unchanged']
        p=(out/q['evidence']).parent
        import csv,io
        guides=list(csv.DictReader(io.StringIO(gzip.decompress((p/'failed_checkpoint_guides.tsv.gz').read_bytes()).decode()),delimiter='\t'))
        assert len(guides)==770 and all(int(g['DB_guide_count_or_minus1_unsupported'])>0 for g in guides)
        text=gzip.decompress((p/'recovered_from_failed.guide.gz').read_bytes()).decode()
        ids=re.findall(r'^(?:src|dst)\[(\d+)\]\s*\n\(',text,re.M);assert len(ids)==len(set(ids))==770 and set(map(int,ids))==set(range(770))
    if j.get('all770_native_guide_detail_continuation_r01'):
        q=j['all770_native_guide_detail_continuation_r01']
        assert not q['full_qualification'] and not q['qualified_common_base'] and not q['two_complete_M11_M12_systems']
        assert q['same_partial_base_input_for_both_modes'] and q['original_GRT_failed_in_both_modes'] and not q['global_route_reexecuted']
        modes=j['all770_native_guide_detail_mode_receipts_r01'];assert len(modes)==2
        for m in modes:
            assert m['completed_utc'] and m['native_returncodes']['detailed_continuation']==1
            assert m['all_original770_nets_had_native_DB_guides'] and m['all_closed_sources_unchanged']
            assert m['original_GRT_state']=='FAILED_GRT_0116_RETAINED_NOT_WAIVED'
            assert m['native_stage_status']['detailed_route']=='FAIL' and not m['allow_congestion_or_infinite_capacity_used']
            assert 'independent_DRC_count' not in m and 'all_edge_signal_clock_geometry' not in m
            p=(out/m['evidence']).parent
            assert 'DRT-0352' in gzip.decompress((p/'detailed_route.error.txt.gz').read_bytes()).decode()
        assert modes[0]['source_lower_checkpoint_SHA256']==modes[1]['source_lower_checkpoint_SHA256']==q['source_lower_checkpoint_SHA256']
    if j.get('SYSTEM_current_relocated_source_path_audit',{}).get('completed_utc'):
        q=j['SYSTEM_current_relocated_source_path_audit'];assert q['native_returncode']==0 and q['source_kind']=='system_existing_buffers_r02'
        assert q['all_sources_unchanged'] and all(q['source_worst_slacks_exactly_replayed'].values()) and not q['full_qualification']
        source=j['SYSTEM_existing_buffer_relocation_r02'];assert q['source_SHA'][q['actual_source_directory']+'/routed.odb']==source['files']['routed.odb']['sha256']
        assert q['source_SHA'][q['actual_source_directory']+'/extracted.spef']==source['files']['extracted.spef']['sha256']
        r=j['SYSTEM_actual_M2_and_current_path_diagnosis'];assert not r['full_qualification'] and not r['plot_contains_other_nets_PDN_or_all_OBS']
        assert r['source_native_DRC_count']==2 and len(r['actual_native_markers'])==2 and all(m['layer']=='metal2' for m in r['actual_native_markers'])
        assert {p['source_text_slack_ns'] for p in r['paths']}=={-0.056303,-0.119814}
        import csv,io
        p=(out/q['evidence']).parent
        native_compressed=gzip.decompress((p/'fresh_DRC_target_net.tsv.gz.gz').read_bytes())
        assert hashlib.sha256(native_compressed).hexdigest()==q['files']['fresh_DRC_target_net.tsv.gz']['sha256']
        native=list(csv.DictReader(io.StringIO(gzip.decompress(native_compressed).decode()),delimiter='\t'))
        with (data/'system_actual_M2_net_rectangles.csv').open(encoding='utf-8') as f:exported=list(csv.DictReader(f))
        assert exported==native and len(native)==r['actual_rectangle_rows'] and {x['net'] for x in native}=={'_215139_'}
    if j.get('SYSTEM_clean_patch_r01_preparation_failure'):
        q=j['SYSTEM_clean_patch_r01_preparation_failure'];assert q['state']=='FAILED_BEFORE_NATIVE_ROUTING' and not q['full_qualification']
        text=gzip.decompress((out/q['evidence']).read_bytes()).decode();assert 'FileNotFoundError' in text and '/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib' in text
    if j.get('MXU_escape_r01_preparation_failure'):
        q=j['MXU_escape_r01_preparation_failure'];assert q['state']=='FAILED_BEFORE_NATIVE_ROUTING' and not q['full_qualification']
        text=gzip.decompress((out/q['evidence']).read_bytes()).decode();assert "KeyError: 'setup_ns'" in text
    if j.get('SYSTEM_native_clean_patches_r02_attempt'):
        q=j['SYSTEM_native_clean_patches_r02_attempt'];assert not q['full_qualification'] and q['source_native_DRC_count']==2
        assert q['original_SDC_and_allowed_layers_unchanged'] and q['new_cells_sizing_pin_XY_changes_requested']==0 and not q['global_route_reexecuted']
    if j.get('MXU_actual_M6_escape_r02_attempt'):
        q=j['MXU_actual_M6_escape_r02_attempt'];assert not q['full_qualification'] and q['source_native_DRC_count']==0
        assert q['profile']=='mxu_M6_escape' and q['new_cells_sizing_pin_XY_changes_requested']==0
        assert q['original_SDC_and_allowed_layers_unchanged']
        if 'temporary_keepout_gap_and_thickness_um' in q:assert q['temporary_keepout_gap_and_thickness_um']==.14
        p=(out/q['evidence']).parent
        assert 'set gap 280;set thick 280' in gzip.decompress((p/'route.tcl.gz').read_bytes()).decode()
        if q.get('completed_utc'):
            assert q['native_returncodes']=={'implementation':0,'fresh_DRC':0} and q['fresh_DRC_count']==0
            assert q['whole_signal_geometry']['pass'] and q['whole_signal_geometry']['checked_nets']==191438
            assert q['whole_signal_geometry']['checked_terminals']==597343 and all(q['all_cells_poses_original_connections_pins_PG_die_unchanged'].values())
            assert q['all_closed_sources_unchanged'] and q['container_libraries_unchanged'] and q['all_original_pins_and_size_in_actual_new_LEF_identical']
            assert q['setup_ns']==rows['mxu']['setup_ns']==.246690 and q['hold_ns']==rows['mxu']['hold_ns']==.038538
            assert q['literal_VIOLATED_markers_not_complete_failure_count']==0 and rows['mxu']['completed_source']=='M6_escape_route/r02'
            assert rows['mxu']['current_source_research_model'] in ['NOT_EXPORTED','SOURCE_BOUND_ACTUAL_RCX_REPLAY_VERIFIED_MINIMUM_PERIOD_MISSING'] and rows['mxu']['strict_GDS_merge_errors'] is None
            assert rows['mxu']['historical_source_before_M6_escape']['strict_GDS_merge_errors']==4
            for k in ['cells','connections','pins','pdn','die']:assert q['files']['before.'+k+'.tsv']['sha256']==q['files']['after.'+k+'.tsv']['sha256']
    if j.get('GEMM_actual658_parent_r01_preparation_failure'):
        q=j['GEMM_actual658_parent_r01_preparation_failure'];assert q['status']=='FAILED_NOT_PHYSICAL_QUALIFICATION' and 'AssertionError' in q['traceback']
    if j.get('GEMM_actual658_parent_r02_attempt',{}).get('completed_utc'):
        q=j['GEMM_actual658_parent_r02_attempt'];assert not q['full_qualification'] and q['source_view_kind']=='real_diode658'
        assert q['native_route_returncode']==1 and q['source_unchanged'] and q['all_closed_source_views_unchanged']
        assert q['all_signal_pins']==3753 and q['actual_parent_M10_landing_ports']==256 and not q['GRT_overflow_allowed_for_guide_only']
        assert q['source_clean_ODB_SHA']==j['GEMM_actual658_diode_physical_and_extracted_views']['source_geometry_sha256']
        assert q['reused_prior_parent_repair_as_proposal']['prior_proposal_rejected_by_current_source_screening']
        assert 'independent_DRC_count' not in q and 'whole_signal_geometry' not in q
        assert 'GRT-0116' in gzip.decompress((out/q['evidence']).parent.joinpath('route.log.gz').read_bytes()).decode()
    if j.get('VECTOR_actual_gate_clone_probe_r01',{}).get('completed_utc'):
        q=j['VECTOR_actual_gate_clone_probe_r01'];assert not q['full_qualification'] and q['native_returncodes']['clone_heuristic_probe']==-11
        assert q['all_closed_sources_unchanged'] and q['final_legalization_route_RC_STA']=='NOT_EXECUTED' and q['new_clone_full_digital_relation']=='NOT_EXECUTED'
        assert 'gate_repaired_NOT_LEGALIZED_OR_ROUTED.odb' not in q['files'] and 'after.pins.tsv' not in q['files']
        assert 'Signal 11 received' in gzip.decompress((out/q['evidence']).parent.joinpath('native.log.gz').read_bytes()).decode()
    if j.get('MXU_actual_M6_escape_physical_RC_views',{}).get('completed_utc'):
        q=j['MXU_actual_M6_escape_physical_RC_views'];source=j['MXU_actual_M6_escape_r02_attempt']
        assert q['native_export_returncode']==q['fresh_model_read_returncode']==0 and q['matching_all_signal_model_pins']==2172
        assert q['all_original_signal_and_PG_pins_and_size_exactly_preserved'] and q['all_sources_and_pre_RCX_geometry_unchanged'] and q['SPEF_replay_matches_source']
        assert not q['minimum_period_present'] and not q['full_qualification']
        assert q['source_geometry_sha256']==source['files']['routed.odb']['sha256'] and q['source_SPEF_sha256']==source['files']['extracted.spef']['sha256']
        assert q['source_receipt_SHA256']==hashlib.sha256(gzip.decompress((out/source['evidence']).read_bytes())).hexdigest()
        r=j['MXU_actual_M6_escape_context'];assert not r['full_qualification'] and r['new_parent_validation']=='NOT_EXECUTED'
        assert abs(r['before_OBS_intersection_pin_union_area_um2']-.0098)<1e-9 and abs(r['after_OBS_intersection_pin_union_area_um2']-.0098)<1e-9
    if j.get('SYSTEM_native_clean_patches_r02_attempt',{}).get('completed_utc'):
        q=j['SYSTEM_native_clean_patches_r02_attempt'];source_row=rows['opentpu_aux'].get('historical_source_before_stacked_via',rows['opentpu_aux'])
        assert q['fresh_DRC_count']==source_row['native_DRC_count']==2 and q['whole_signal_geometry']['pass']
        assert q['setup_ns']==source_row['setup_ns']==-.056396 and q['hold_ns']==source_row['hold_ns']==-.119919
        assert q['all_closed_sources_unchanged'] and all(q['all_cells_poses_original_connections_pins_PG_die_unchanged'].values())
    if j.get('SYSTEM_existing_buffer_relocation_r02',{}).get('completed_utc'):
        q=j['SYSTEM_existing_buffer_relocation_r02'];assert not q['full_qualification'] and q['native_returncodes']['route']==0
        system_source_row=rows['opentpu_aux'].get('historical_source_before_stacked_via',rows['opentpu_aux'])
        source_row=system_source_row.get('historical_source_before_clean_patches',system_source_row)
        assert q['fresh_DRC_count']==source_row['native_DRC_count']==2 and q['whole_signal_geometry']['pass']
        assert q['setup_ns']==source_row['setup_ns']==-0.056303 and q['hold_ns']==source_row['hold_ns']==-0.119814
        assert q['literal_VIOLATED_markers_not_complete_failure_count']==1233 and q['all_sources_unchanged']
        assert all(q['pin_PG_die_unchanged'].values()) and not q['legalization_recomputed'] and not q['selection_or_moves_recomputed']
        for kind in ['connections','nonselected']:assert q['files']['before.'+kind+'.tsv']['sha256']==q['files']['after.'+kind+'.tsv']['sha256']
    if j.get('VECTOR_original_GRT_context_probe_r02',{}).get('completed_utc'):
        q=j['VECTOR_original_GRT_context_probe_r02'];assert not q['full_qualification'] and q['native_returncodes']['clone_heuristic_probe']==1
        assert q['all_closed_sources_unchanged'] and q['final_legalization_route_RC_STA']=='NOT_EXECUTED'
        assert 'gate_repaired_NOT_LEGALIZED_OR_ROUTED.odb' not in q['files'] and 'after.pins.tsv' not in q['files']
        text=gzip.decompress((out/q['evidence']).parent.joinpath('native.log.gz').read_bytes()).decode()
        assert 'RSZ-0074' in text and 'STAGE_EXECUTED initialize_original_GRT_context' in text
    for key in ['SYSTEM_actual_stacked_via_r01','MXU_actual_view_parent_recheck_r01']:
        q=j.get(key,{})
        if not q.get('completed_utc'):continue
        assert not q['full_qualification'] and q['all_closed_sources_unchanged']
        if 'fresh_DRC_count' in q:
            text=gzip.decompress((out/q['evidence']).parent.joinpath('independent.drc.gz').read_bytes()).decode()
            assert q['fresh_DRC_count']==len(re.findall(r'^violation type:',text,re.M))
        if key=='MXU_actual_view_parent_recheck_r01':
            assert q['all_original_leaf_signal_pins']==2172 and q['actual_new_leaf_ODB_SHA256']==j['MXU_actual_M6_escape_physical_RC_views']['source_geometry_sha256']
            assert q['parent_RC_STA']=='NOT_EXECUTED_ACCESS_RECHECK_ONLY'
            assert all(q['all_original_parent_BTerm_PG_die_geometry_unchanged'].values())
            if not q['all_original_macro_pin_rectangles_net_directions_layers_in_parent_exactly_unchanged']:
                from collections import Counter
                import csv,io
                clock_folder=(out/q['evidence']).parent
                def parse_terms(name):return list(csv.DictReader(io.StringIO(gzip.decompress((clock_folder/name).read_bytes()).decode()),delimiter='\t'))
                a=parse_terms('before.child_terms.tsv.gz');b=parse_terms('after.child_terms.tsv.gz')
                key=lambda r:tuple(sorted(r.items()))
                ca=Counter(map(key,a));cb=Counter(map(key,b));minus=list((ca-cb).elements());plus=list((cb-ca).elements())
                assert len(a)==len(b)==2245 and len(minus)==len(plus)==1
                before,after=dict(minus[0]),dict(plus[0]);assert before['pin']==after['pin']=='clk'
                assert before['use']=='CLOCK' and after['use']=='SIGNAL'
                assert {k:v for k,v in before.items() if k!='use'}=={k:v for k,v in after.items() if k!='use'}
                failure=j['MXU_current_actual_view_clock_USE_regression']
                assert failure['status']=='FAILED_CLOCK_USE_CONTRACT' and failure['original']==before and failure['after_actual_view_swap']==after
                assert failure['original_native_receipt_false_preserved'] and not failure['full_qualification']
                assert rows['mxu']['parent_access'].endswith('_CLOCK_USE_CONTRACT_FAILED') and not rows['mxu']['full_qualification']
            assert q['whole_parent_signal_geometry']['pass'] and q['whole_parent_signal_geometry']['checked_nets']==2172
        elif q.get('whole_signal_geometry'):
            assert q['whole_signal_geometry']['pass'] and q['whole_signal_geometry']['checked_nets']==466332
            assert all(q['original_cells_poses_signal_connections_pins_PG_die_unchanged'].values())
            assert q['actual_changed_multiterminal_net_wire_via_box_multisets']==['_215139_']
    if j.get('ALL24767_actual_parent_track_geometry'):
        q=j['ALL24767_actual_parent_track_geometry'];assert q['all_closed_sources_unchanged'] and not q['full_qualification']
        assert sum(v['signal_pins'] for v in q['per_block_track_geometry'].values())==24767
        assert {k:v['preferred_axis_center_not_aligned'] for k,v in q['per_block_track_geometry'].items()}=={'act':0,'mxu':0,'opentpu_aux':0,'gemm':0,'vector':0,'llaccel_aux':13184}
        assert q['actual_complete_selected_net_row_counts']['bit_1025']==535
        figure=j['LL_SYSTEM_actual_via_tip_figure'];assert not figure['full_qualification']
        assert figure['actual_rows_before_after']==[862,854] and figure['removed_WIRE_rectangles']==8 and figure['all_actual_vias_preserved']
        assert figure['source_native_DRC_before_after']==[4,0] and figure['setup_hold_ns']==[-3.909029,-.587515]
    if j.get('MXU_native_clock_Liberty_binding_probe'):
        q=j['MXU_native_clock_Liberty_binding_probe'];assert q['native_probe_returncode']==0 and q['all_closed_sources_unchanged'] and not q['full_qualification']
        assert q['actual_native_stage_rows'][1:]==['after_LEF\tSIGNAL\tNULL\tNULL','after_Liberty\tCLOCK\tNULL\tNULL','after_link_design\tCLOCK\tCLOCK\tSIGNAL','after_original_create_clock\tCLOCK\tCLOCK\tSIGNAL']
    q=j.get('MXU_clock_bound_parent_recheck_r02',{})
    if q.get('completed_utc'):
        assert q['native_returncodes']['actual_view_swap_and_access_export']==-11 and q['all_closed_sources_unchanged']
        assert 'fresh_DRC_count' not in q and not q['full_qualification']
    q=j.get('LLSYSTEM_current_actual_tip_views',{})
    if q.get('completed_utc'):
        import csv,io
        from collections import Counter
        assert q['native_export_returncode']==q['fresh_model_read_returncode']==0 and q['matching_all_signal_model_pins']==13507
        assert q['all_sources_and_pre_RCX_geometry_unchanged'] and q['SPEF_replay_matches_source'] and q['all_13507_current_pins_and_PG_match_actual_after_edit']
        assert not q['full_qualification'] and q['minimum_period_present'] is False
        current_source=read(folder/'llsys_actual_via_tips/r02/execution.json.gz')
        assert q['source_geometry_sha256']==current_source['files']['routed.odb']['sha256']
        assert q['source_SPEF_sha256']==current_source['files']['extracted.spef']['sha256']
        view_folder=(out/q['evidence']).parent
        new_pins=gzip.decompress((view_folder/'pins.tsv.gz').read_bytes()).decode().splitlines()[1:]
        source_pins=gzip.decompress((folder/'llsys_actual_via_tips/r02/after.pins.tsv.gz').read_bytes()).decode().splitlines()
        assert Counter(tuple(s.split()) for s in new_pins)==Counter(tuple(s.split()) for s in source_pins)
        for k in ['setup','hold']:
            assert gzip.decompress((view_folder/(k+'.txt.gz')).read_bytes())==gzip.decompress((folder/('llsys_actual_via_tips/r02/'+k+'.txt.gz')).read_bytes())
        assert rows['llaccel_aux']['current_source_research_model']=='SOURCE_BOUND_ACTUAL_RCX_REPLAY_VERIFIED_MINIMUM_PERIOD_MISSING'
    for q in j.get('source_bound_extended_STA_r01',[]):
        assert not q['full_qualification']
        if not q.get('completed_utc'):continue
        assert q['native_returncode']==0 and q['all_sources_unchanged'] and all(q['source_worst_slacks_exactly_replayed'].values())
        assert q['original_constraints_and_SPEF_unchanged']
        assert 'extended_checks_all_not_only_violators.txt' in q['files']
    if j.get('planned_default_via10_pair_geometric_screen'):
        q=j['planned_default_via10_pair_geometric_screen'];assert not q['full_qualification'] and q['cut_spacing_um_explicit_assumption']==.88
        table=out/'data/upper_planned_via10_pair_screen_r01/planned_via10_nearest.csv'
        assert hashlib.sha256(table.read_bytes()).hexdigest()==q['table_sha256']
        for mode in q['modes']:
            assert mode['planned_hook_count']==1540 and mode['all_pairs_tested']==1540*1539//2
            assert not mode['conflicts'] and abs(mode['minimum_cut_rectangle_gap_um']-2.4)<1e-9
            p=(out/j['source_snapshot']).parent/'upper_adaptation_trial/r02'/(mode['mode']+'_actual_hook_plan.json.gz')
            assert hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()==mode['source_plan_raw_sha256']
    if j.get('SYSTEM_actual_stacked_via_physical_RC_views',{}).get('completed_utc'):
        q=j['SYSTEM_actual_stacked_via_physical_RC_views'];source=j['SYSTEM_actual_stacked_via_r01']
        assert not q['full_qualification'] and q['native_export_returncode']==q['fresh_model_read_returncode']==q['before_target_actual_export_returncode']==0
        assert q['matching_all_signal_model_pins']==2229 and q['all_original_signal_and_PG_pins_and_size_exactly_preserved']
        assert q['SPEF_replay_matches_source'] and q['all_sources_and_pre_RCX_geometry_unchanged'] and not q['minimum_period_present']
        assert q['source_geometry_sha256']==source['files']['routed.odb']['sha256'] and q['source_SPEF_sha256']==source['files']['extracted.spef']['sha256']
        assert q['source_receipt_SHA256']==hashlib.sha256(gzip.decompress((out/source['evidence']).read_bytes())).hexdigest()
        assert q['current_exact_source_extended_STA']['native_command_executed']
        assert q['current_exact_source_extended_STA']['actual_report_SHA256']==q['files']['current_source_extended_checks_all.txt']['sha256']
        assert rows['opentpu_aux']['current_source_research_model']=='SOURCE_BOUND_ACTUAL_RCX_REPLAY_VERIFIED_MINIMUM_PERIOD_MISSING'
        f=j['SYSTEM_actual_stacked_via_figure'];assert not f['full_qualification'] and f['source_native_DRC_before_after']==[2,0]
        assert f['after_ODB_SHA256']==q['source_geometry_sha256'] and f['before_ODB_SHA256']==q['before_actual_geometry_sha256']
    if j.get('VECTOR_probe_strict_directed_buffer_relation_r01',{}).get('completed_utc'):
        q=j['VECTOR_probe_strict_directed_buffer_relation_r01'];assert not q['full_qualification'] and not q['relative_mapped_digital_contract_pass']
        assert q['all_closed_sources_unchanged'] and 'An original logical net split after buffer elimination' in q['actual_failure']
        assert rows['vector']['completed_source']=='costed_VECTOR_resume/r01'
    if j.get('LLSYSTEM_actual_four_marker_diagnosis_r01',{}).get('completed_utc'):
        q=j['LLSYSTEM_actual_four_marker_diagnosis_r01'];assert not q['full_qualification'] and q['all_closed_sources_unchanged'] and q['native_local_PG_OBS_export_returncode']==0
        assert q['source_native_DRC_count']==4 and q['source_all_multiterminal_nets']==725253 and q['all_target_rows']==862 and q['local_signal_clock_rows']==831
        assert q['all_three_net_connectivity_replay']['pass'] and q['all_three_net_connectivity_replay']['checked_nets']==3
    if j.get('VECTOR_actual_five_input_partition_restore_r01',{}).get('completed_utc'):
        q=j['VECTOR_actual_five_input_partition_restore_r01'];assert not q['full_qualification'] and q['relative_mapped_digital_contract_pass']
        assert q['pre_native_simulated_strict_relation_pass'] and not q['strict_verifier_changed'] and q['old_strict_failure_retained']
        assert q['native_returncodes']=={'restore_original_five_inputs':0,'restored_full_graph':0}
        assert q['actual_changed_signal_terminals_exactly_five_inputs'] and len(q['exact_five_input_restores'])==5
        assert q['all_cell_instances_masters_poses_areas_unchanged'] and all(q['all_original_pins_PG_die_unchanged'].values())
        assert q['all_closed_sources_unchanged'] and q['new_cells_or_sizing_in_this_restore']==0 and q['legality_route_RC_STA']=='NOT_EXECUTED'
        assert q['summary']['original_signal_terminals']==1076467 and q['summary']['top_ports']==2246 and q['summary']['added_identity_buffers']==49
        assert q['summary']['resized_original_instances']==365 and q['summary']['original_net_partition_equal_after_buffer_elimination']
        assert q['summary']['directed_original_driver_reachability'] and q['summary']['added_buffer_graph_acyclic']
    for q in j.get('latest_actual_parent_landing_repairs',[]):
        if not q.get('completed_utc'):continue
        assert q['native_route_returncode']==q['fresh_DRC_returncode']==0 and q['whole_signal_geometry']['pass']
        assert q['fresh_DRC_count']==(0 if q['case']=='gemm' else 1)
        assert q['exactly_one_parent_M10_pin_XY_changed_all_other_rectangles_unchanged'] and q['all_PG_geometry_byteexact_unchanged'] and q['both_power_grids_pass']
        assert q['source_unchanged'] and not q['full_qualification']
    if j.get('actual_fixed256_native_attribute_audit'):
        q=j['actual_fixed256_native_attribute_audit'];assert q['native_export_returncode']==0 and not q['native_export_executed_this_run']
        assert q['all_256_native_FIXEDS_and_original_net_bindings_verified'] and q['all_closed_source_files_unchanged'] and q['native_shared_conductor_count']==256
        assert q['actual_shared_centerline_length_um']==8192 and not q['qualified'] and not q['frozen']
        old=read(folder/'shared_conductor_audit/r01/execution.json.gz');assert old['native_export_returncode']==0 and old['all_256_native_FIXEDS_and_original_net_bindings_verified'] is False
        fixed=read(folder/'shared_conductor_audit/r02/native_fixedness.json.gz');assert len(fixed)==256 and len({x['pad'] for x in fixed})==256
        assert all(x['native_DEF_path_status']=='FIXED' and x['native_layer']=='metal10' and '+ FIXED metal10' in x['native_DEF_net_statement'] for x in fixed)
        p=j['actual_shared_conductor_geometry'];assert p['native_fixed_conductors']==256 and p['native_shared_port_boxes']==512 and not p['full_qualification']
    if j.get('SYSTEM_output_chain_placement'):
        q=j['SYSTEM_output_chain_placement'];r=q['receipt']
        assert not q['full_qualification'] and r['native_returncodes']['implementation']==-11
        assert r['new_functional_cells']==r['master_sizing_changes']==r['functional_net_splits']==0
        assert r['output_port_selection_summary']=={'all_output_ports_considered':1244,'private_output_chains_selected':772}
        assert r['selected_existing_buffers']==1262 and r['all_sources_unchanged']
        assert 'Signal 11 received' in gzip.decompress((out/q['evidence']).parent.joinpath('native.log.gz').read_bytes()).decode()
    if j.get('SYSTEM_output_chain_resume'):
        q=j['SYSTEM_output_chain_resume'];r=q['receipt'];assert not q['full_qualification'] and not r['selection_or_moves_recomputed']
        assert r['native_returncodes']['legalization']==0 and r['isolated_geometry_contracts_pass']
        if r.get('completed_utc'):
            assert r['native_returncodes']['route']==1 and r['route_stage_status']['preserve_contracts']=='FAIL'
            assert 'fresh_DRC_count' not in r and 'setup_ns' not in r
            assert 'Empty command name' in gzip.decompress((out/q['evidence']).parent.joinpath('preserve_contracts.error.txt.gz').read_bytes()).decode()
        meta=read(latest);indexed={x['source']:x for x in meta['records']}
        base='/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027/'
        for kind in ['connections','nonselected']:
            p=base+'output_chain_resume/r01/opentpu_aux-C/placed.'+kind+'.tsv'
            ref=base+'output_chain_placement/r01/opentpu_aux-C/before.'+kind+'.tsv'
            assert indexed[p]['closed_native_stage']=='isolated_legalization' and indexed[p]['sha256']==r['source_SHA'][ref]
    print('PASS_GATE_MATRIX_NATIVE_EVIDENCE',len(rows),'blocks;',native_files,'raw files; duplicate-LEF failure and real strict-merge outcomes preserved; NOT full qualification')
