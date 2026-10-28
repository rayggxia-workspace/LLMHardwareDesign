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
            value=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',text)[1]);assert rows[case][kind+'_ns']==value
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
    print('PASS_GATE_MATRIX_NATIVE_EVIDENCE',len(rows),'blocks;',native_files,'raw files; duplicate-LEF failure and real strict-merge outcomes preserved; NOT full qualification')
