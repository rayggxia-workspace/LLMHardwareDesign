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
        assert rows[case]['strict_GDS_merge_errors']==merge['merge_errors']
        if case=='gemm':assert merge['merge_errors']==0
        else:assert merge['merge_errors']==4 and rows[case]['complete_rules'].startswith('FAILED_STRICT_GDS')
        version='r03' if case=='gemm' else 'r04'
        paths=sorted((data/'continuation/resume').glob('resume-*/leaf_eco/'+version+'/'+case+'-C/execution.json.gz'));assert paths
        physical=read(paths[-1]);assert rows[case]['native_DRC_count']==physical['fresh_DRC_count']==0
        for kind in ['setup','hold']:
            text=gzip.decompress((paths[-1].parent/(kind+'.txt.gz')).read_bytes()).decode()
            historical=rows[case].get('historical_matched_costed_source_before_diode',rows[case])
            value=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',text)[1]);assert historical[kind+'_ns']==value
        if (fixed/'execution.json.gz').exists():
            end=read(fixed/'execution.json.gz')
            assert rows[case]['available_deck_findings']==end.get('available_deck_findings')
            assert not end['full_qualification']
    assert rows['llaccel_aux']['native_DRC_count']==4 and rows['llaccel_aux']['newer_attempt']['three_pin_job'].endswith('FAILED_DRT_1231')
    system=folder/'checkpoint_route/r01/execution.json.gz'
    if system.exists() and read(system).get('completed_utc'):
        q=read(system);assert not q['full_qualification'] and q['native_returncode']==0 and q['fresh_DRC_count']==0
        assert q['source_unchanged'] and all(q['geometry_invariants'].values()) and q['whole_signal_geometry']['pass']
        assert rows['opentpu_aux']['completed_source']=='costed_ECO/isolated-route-r01'
        for kind in ['setup','hold']:
            t=gzip.decompress((system.parent/(kind+'.txt.gz')).read_bytes()).decode()
            value=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',t)[1]);assert rows['opentpu_aux'][kind+'_ns']==value<0
        assert rows['opentpu_aux']['violation_marker_rows']==gzip.decompress((system.parent/'checks.txt.gz').read_bytes()).decode().count('(VIOLATED)')
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
        assert audit['GDS_deck_findings_not_repaired']==rows['gemm']['available_deck_findings']==1460
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
