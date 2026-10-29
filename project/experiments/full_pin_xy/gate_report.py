"""Evidence-based six-block gate matrix; a failed/unknown gate never becomes a pass."""
from pathlib import Path
import csv,gzip,hashlib,html,json,re,shutil

CASES=['act','mxu','opentpu_aux','gemm','vector','llaccel_aux']
TITLES=['openTPU ACT','openTPU MXU','openTPU SYSTEM','llaccel GEMM','llaccel VECTOR','llaccel SYSTEM']
COUNTS=[860,2172,2229,3753,2246,13507]


def read(p):
    raw=p.read_bytes();return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)


def existing(data,relative):
    candidates=list((data/'continuation/native').glob('*/'+relative+'.gz'))
    candidates+=list((data/'continuation/resume').glob('resume-*/'+relative+'.gz'))
    candidates+=list((data/'continuation/terminal_updates').glob('*/'+relative+'.gz'))
    return sorted(candidates)[-1] if candidates else None


def stage_set(path):
    if not path or not path.exists():return {}
    with gzip.open(path,'rt',newline='') as f:return {r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}


def slack(path):
    assert path and path.exists()
    text=gzip.decompress(path.read_bytes()).decode();m=re.search(r'worst slack (?:min|max)\s+([-\d.]+)',text)
    assert m;return float(m[1])


def render(root,out):
    root,out=Path(root),Path(out);sources=sorted(p for p in (root/'gate_evidence').glob('gate-*') if p.is_dir())
    if not sources:return ''
    snapshot=sources[-1];meta=read(snapshot/'snapshot.json');assert not meta['full_qualification']
    dest=out/'data/gate_milestones'/snapshot.name
    for r in meta['records']:
        if r['storage']!='LOSSLESS_SNAPSHOT':continue
        p=snapshot/r['relative'];stored=p.read_bytes();raw=gzip.decompress(stored)
        assert hashlib.sha256(stored).hexdigest()==r['stored_sha256'] and hashlib.sha256(raw).hexdigest()==r['sha256'] and len(raw)==r['bytes']
    shutil.copytree(snapshot,dest,dirs_exist_ok=True)
    with (snapshot/'scheduler.tsv').open() as f:scheduler={r['JobIDRaw']:r for r in csv.DictReader(f,delimiter='|') if '.' not in r['JobIDRaw']}
    data=out/'data';base=read(data/'continuation/summary.json');byname={r['block']:r for r in base['blocks']}
    rows=[];stream_rows=[];parent_rows=[]
    for case,title,count in zip(CASES,TITLES,COUNTS):
        b=byname[title];row={'case':case,'block':title,'original_signal_pins':count,
          'current_source_internal_moved_pins':b['selected_internal'],
          'partition_and_all_interfaces':'COMPLETE_SOURCE_INVENTORY','candidate_ABC':'COMPLETE_3_VERSIONS_NOT_PHYSICAL_PASS',
          'completed_source':'act-access-r03' if case=='act' else 'access-r03',
          'actual_internal_route':'COMPLETED' if b['trial_terminal'] and b['route_returncode']==0 else 'NOT_TERMINAL',
          'native_DRC_count':b['independent_native_DRC'],'all_multiterminal_signal_clock_geometry':b['whole_geometry'],
          'setup_ns':b['setup_ns'],'hold_ns':b['hold_ns'],'violation_marker_rows':b['electrical_timing_violator_rows'],
          'power_grid':'NOT_YET_READ_FROM_STAGE_RECEIPT','RC_STA_scope':'SOURCE_SDC_EXTRACTED_RESULTS_NOT_COMPLETE_SYSTEM_QUALIFICATION',
          'complete_rules':'NOT_PASSED_OR_INCOMPLETE_COVERAGE','historical_parent_target_layers':'PARTIAL_OR_UNKNOWN',
          'mapped_design_formal_equivalence':'NOT_EXECUTED','RTL_system_formal_equivalence':'NOT_EXECUTED',
          'parent_access':'NOT_FULLY_VALIDATED','newer_attempt':None,'full_qualification':False,'evidence':[]}
        version=row['completed_source']
        stage=existing(data,'trials/'+version+'/'+case+'-C/stages.tsv')
        stages=stage_set(stage)
        if stages.get('pdn_VDD')==stages.get('pdn_VSS')=='EXECUTED':row['power_grid']='NATIVE_VDD_VSS_COMMANDS_EXECUTED'
        if stage:row['evidence'].append(stage.relative_to(out).as_posix())
        if case in ['gemm','mxu']:
            version='r03' if case=='gemm' else 'r04';p=existing(data,'leaf_eco/'+version+'/'+case+'-C/execution.json')
            assert p and read(p).get('completed_utc');j=read(p)
            row.update({'completed_source':'costed_ECO/'+version,'actual_internal_route':'COMPLETED_COSTED_ECO_NOT_PURE_XY',
              'native_DRC_count':j['fresh_DRC_count'],'all_multiterminal_signal_clock_geometry':j['whole_signal_geometry']['pass'],
              'setup_ns':slack(p.parent/'setup.txt.gz'),'hold_ns':slack(p.parent/'hold.txt.gz'),
              'violation_marker_rows':0,'power_grid':'NATIVE_VDD_VSS_COMMANDS_EXECUTED',
              'formal_subproof':'Exact Liberty logic/state and resized-cell terminal contract; not full design formal',
              'cell_master_bbox_area_delta_um2':j['separate_cell_ECO_cost']['standard_cell_master_bbox_area_after_um2']-j['separate_cell_ECO_cost']['standard_cell_master_bbox_area_before_um2'],
              'parent_access':'SELECTED_256_ACCESS_FIXTURE_NOT_YET_FULLY_VALIDATED'})
            row['evidence'].append(p.relative_to(out).as_posix())
            parent_revision='gemm-r02' if case=='gemm' else 'mxu-r01';job='92721' if case=='gemm' else '92714'
            parent_file=snapshot/'escape_fixtures'/parent_revision/(case+'-C')/'execution.json.gz'
            parent=read(parent_file) if parent_file.exists() else {}
            row['parent_access_detail']={'job':job,'scheduler':scheduler.get(job,{}).get('State','UNKNOWN'),
              'terminal_receipt':bool(parent.get('completed_utc')),'native_DRC':parent.get('independent_DRC_count'),
              'whole_geometry':parent.get('whole_signal_geometry',{}).get('pass'),'full_parent_qualified':False}
            if parent.get('completed_utc'):row['parent_access']='SELECTED_FIXTURE_TERMINAL_READ_DETAIL_NOT_SYSTEM_QUALIFICATION'
        if case=='act':row['parent_access']='256_PHYSICAL_ESCAPES_NATIVE_GEOMETRY_PG_PASS; PARENT_RESEARCH_BENCH_HOLD_FAIL'
        if case=='opentpu_aux':
            p=snapshot/'checkpoint_route/r01/execution.json.gz';attempt=read(p) if p.exists() else {}
            row['newer_attempt']={'job':'92781','scope':'COSTED_ECO_FROM_ISOLATED_LEGALIZATION',
              'state':scheduler.get('92781',{}).get('State','UNKNOWN'),'terminal_receipt':bool(attempt.get('completed_utc')),
              'native_DRC':attempt.get('fresh_DRC_count'),'route_returncode':attempt.get('native_returncode'),'qualification':False}
            if attempt.get('completed_utc') and attempt.get('native_returncode')==0 and attempt.get('fresh_DRC_count')==0 and attempt.get('whole_signal_geometry',{}).get('pass'):
                assert all(attempt['geometry_invariants'].values()) and attempt['source_unchanged']
                assert all(stage_set(p.parent/'stages.tsv.gz').get(s)=='EXECUTED' for s in ['detailed_route','remove_only_source_temporary_OBS','VDD','VSS','whole_signal_geometry','rcx','sta'])
                row.update({'completed_source':'costed_ECO/isolated-route-r01','actual_internal_route':'COMPLETED_COSTED_ECO_NOT_PURE_XY',
                  'native_DRC_count':0,'all_multiterminal_signal_clock_geometry':True,
                  'setup_ns':slack(p.parent/'setup.txt.gz'),'hold_ns':slack(p.parent/'hold.txt.gz'),
                  'violation_marker_rows':gzip.decompress((p.parent/'checks.txt.gz').read_bytes()).decode().count('(VIOLATED)'),
                  'power_grid':'NATIVE_VDD_VSS_COMMANDS_EXECUTED'})
                row['evidence'].append((dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if case=='vector':row['newer_attempt']={'job':'92775','state':'FAILED_EST_0104_AFTER_SEPARATE_SPEF_REPLAY','qualification':False}
        if case=='llaccel_aux':
            p=existing(data,'finalized/llsys-pg-r03/llaccel_aux-C/execution.json');assert p
            j=read(p);row.update({'completed_source':'llsys-pg-r03_alternative','actual_internal_route':'COMPLETED_BUT_NATIVE_DRC_FAILED',
                'native_DRC_count':j['independent_DRC_count'],'all_multiterminal_signal_clock_geometry':j['whole_access']['pass'],
                'setup_ns':None,'hold_ns':None,'violation_marker_rows':None,
                'newer_attempt':{'full_window_jobs':{job:scheduler.get(job,{}).get('State','UNKNOWN') for job in ['92690','92691']},
                                 'three_pin_job':'92747_FAILED_DRT_1231','qualification':False}})
            row['evidence'].append(p.relative_to(out).as_posix())
            for kind in ['setup','hold']:
                q=existing(data,'trials/llsys-pg-r03/llaccel_aux-C/timing.'+kind+'.txt')
                if q:row[kind+'_ns']=slack(q);row['evidence'].append(q.relative_to(out).as_posix())
            pg_stages=stage_set(existing(data,'trials/llsys-pg-r03/llaccel_aux-C/stages.tsv'))
            if pg_stages.get('pdn_VDD')==pg_stages.get('pdn_VSS')=='EXECUTED':row['power_grid']='NATIVE_VDD_VSS_COMMANDS_EXECUTED'
        if case in ['gemm','mxu']:
            folder=snapshot/'streamout/costed-r02'/(case+'-C_ECO');p=folder/'merge.json.gz'
            merged=read(p) if p.exists() else {};execfile=folder/'execution.json.gz';e=read(execfile) if execfile.exists() else {}
            row['strict_GDS_merge_errors']=merged.get('merge_errors');row['available_deck_findings']=e.get('available_deck_findings')
            if merged.get('merge_errors',0)>0:row['complete_rules']='FAILED_STRICT_GDS_MISSING_CELLS; partial-deck results diagnostic only'
            elif merged.get('merge_errors')==0:
                row['complete_rules']='AVAILABLE_DECK_HAS_FINDINGS' if e.get('available_deck_findings',0)>0 else 'AVAILABLE_DECK_0_COVERAGE_STILL_INCOMPLETE' if e.get('available_deck_findings')==0 else 'GDS_MERGED_DECK_NOT_TERMINAL'
            row['GDS_full_rule_evidence']=dest.relative_to(out).as_posix()+'/streamout/costed-r02/'+case+'-C_ECO/'
            logfile=folder/'merge.log.gz'
            missing=re.findall(r"LEF Cell '([^']+)' has no matching GDS",gzip.decompress(logfile.read_bytes()).decode()) if logfile.exists() else None
            stream_rows.append({'block':title,'strict_merge_errors':merged.get('merge_errors'),
              'missing_GDS_cells':e.get('missing_GDS_cells',missing),'deck_executed':e.get('DRC_executed'),
              'deck_findings':e.get('available_deck_findings'),'stage_outcome':e.get('stage_outcome','RUNNING_OR_RECEIPT_NOT_TERMINAL')})
        rows.append(row)
    result={'schema_version':1,'scope':'LATEST_KNOWN_COMPLETED_SOURCE_PLUS_SEPARATE_NEWER_ATTEMPTS_NOT_FULL_QUALIFICATION',
      'snapshot_UTC':meta['created_utc'],'source_snapshot':dest.relative_to(out).as_posix()+'/snapshot.json',
      'rules':'Completed version and newer repair are distinct. Unknown is null, never zero. Literal VIOLATED marker rows are not a full failure count. Full manufacturing rules/formal/system evidence remains separate.',
      'blocks':rows,'common_base_implemented':False,'common_base_qualified_or_frozen':False,
      'two_complete_M11_M12_modes_implemented':False,'fair_end_to_end_system_comparison_completed':False}
    for p in sorted(snapshot.glob('escape_fixtures/*/*/execution.json.gz')):
        q=read(p)
        if not q.get('completed_utc'):continue
        log=p.parent/'route.log.gz';text=gzip.decompress(log.read_bytes()).decode() if log.exists() else ''
        parent_rows.append({'version':p.parent.relative_to(snapshot).as_posix(),
          'route_returncode':q.get('native_route_returncode'),'native_DRC':q.get('independent_DRC_count'),
          'signal_geometry':q.get('whole_signal_geometry',{}).get('pass'),
          'signal_nets_checked':q.get('whole_signal_geometry',{}).get('checked_nets'),
          'both_PG_native_log_connected':all('All shapes on net '+n+' are connected.' in text for n in ['VDD','VSS']),
          'source_leaf_ODB_SHA':q.get('source_clean_ODB_SHA'),'parent_M10_accesses':q.get('actual_parent_M10_landing_ports'),
          'full_parent_RC_STA':'NOT_EXECUTED_OR_NOT_QUALIFIED','completed_UTC':q['completed_utc'],
          'evidence':(dest/p.relative_to(snapshot)).relative_to(out).as_posix()})
    result['selected_parent_fixture_terminal_receipts']=parent_rows
    controls=[]
    for case in ['gemm','mxu']:
        p=snapshot/'leaf_eco/boundary-r01'/(case+'-Aopt')/'execution.json.gz'
        if not p.exists():continue
        q=read(p)
        if not q.get('completed_utc'):continue
        controls.append({'case':case,'variant':'Aopt','native_DRC':q['fresh_DRC_count'],
          'whole_signal_geometry':q['whole_signal_geometry']['pass'],'geometry_invariants':q['geometry_invariants'],
          'source_unchanged':q['source_unchanged'],'targeted_master_changes':q['targeted_master_changes'],
          'setup_ns':slack(p.parent/'setup.txt.gz'),'hold_ns':slack(p.parent/'hold.txt.gz'),
          'cell_ECO_cost':q['separate_cell_ECO_cost'],'full_qualification':False,
          'evidence':(dest/p.relative_to(snapshot)).relative_to(out).as_posix()})
    result['optimized_boundary_same_ECO_controls']=controls
    actual_routes=[]
    for control in controls:
        case=control['case'];version='r03' if case=='gemm' else 'r04'
        for variant in ['Aopt','C']:
            p=(snapshot/'leaf_eco/boundary-r01'/(case+'-Aopt')/'native.log.gz') if variant=='Aopt' else existing(data,'leaf_eco/'+version+'/'+case+'-C/native.log')
            assert p and p.exists()
            raw=gzip.decompress(p.read_bytes());text=raw.decode()
            totals=list(re.finditer(r'Total wire length = ([\d.]+) um\.',text));assert totals
            last=totals[-1];tail=text[last.start():]
            lengths={k:float(v) for k,v in re.findall(r'Total wire length on LAYER (metal\d+) = ([\d.]+) um\.',tail)}
            via=re.findall(r'Total number of vias = (\d+)\.',tail);assert via and set(lengths)=={'metal'+str(i) for i in range(1,11)}
            native_path=(dest/p.relative_to(snapshot)) if variant=='Aopt' else p
            actual_routes.append({'case':case,'variant':variant,'DRT_reported_wire_length_um':float(last[1]),
              'DRT_reported_per_layer_wire_length_um':lengths,'DRT_reported_vias':int(via[-1]),
              'scope':'Actual last DRT report from completed matching costed route, rounded um; via counting follows DRT, not PDN signoff',
              'not_geometric_endpoint_L1':True,'not_extracted_RC_or_system_gain':True,
              'source_native_log_uncompressed_SHA256':hashlib.sha256(raw).hexdigest(),
              'evidence':native_path.relative_to(out).as_posix()})
    for r in actual_routes:
        baseline=next(q for q in actual_routes if q['case']==r['case'] and q['variant']=='Aopt')
        r['wire_change_vs_same_ECO_Aopt_percent']=100*(r['DRT_reported_wire_length_um']/baseline['DRT_reported_wire_length_um']-1)
        r['via_change_vs_same_ECO_Aopt_percent']=100*(r['DRT_reported_vias']/baseline['DRT_reported_vias']-1)
    result['same_ECO_actual_leaf_DRT_metrics']=actual_routes
    (data/'equal_cost_leaf_actual_metrics.json').write_text(json.dumps(actual_routes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    audit=snapshot/'antenna_audit/r01/execution.json.gz'
    if audit.exists():
        q=read(audit);result['antenna_checker_disagreement']={'native_returncode':q['native_returncode'],
          'source_unchanged':q['source_unchanged'],'actual_diode_liberty_cells':q['actual_diode_liberty_cells'],
          'GDS_deck_findings_not_repaired':1460,'full_qualification':False,
          'evidence':(dest/audit.relative_to(snapshot)).relative_to(out).as_posix()}
    proofs=[]
    for p in sorted(snapshot.glob('mapped_equivalence/r01/*/execution.json.gz')):
        q=read(p);case=p.parent.name
        proofs.append(dict(q,case=case,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
        row=next(r for r in rows if r['case']==case)
        row['whole_mapped_relative_digital_contract']=q.get('relative_mapped_digital_contract_pass')
        row['relative_contract_scope']=q['scope']+'; '+q['unchanged_memory_semantics']
    result['whole_mapped_relative_digital_contracts']=proofs
    buffered=snapshot/'buffered_equivalence/r01/opentpu_aux/execution.json.gz'
    if buffered.exists():
        q=read(buffered);result['SYSTEM_directed_buffer_relation']=dict(q,evidence=(dest/buffered.relative_to(snapshot)).relative_to(out).as_posix())
        r=next(r for r in rows if r['case']=='opentpu_aux')
        r['whole_mapped_relative_digital_contract']=q['relative_mapped_digital_contract_pass']
        r['relative_contract_scope']=q['scope']+'; '+q['memory_contract']
    system_view=snapshot/'eco_views/r03/opentpu_aux-C/execution.json.gz'
    system_text=''
    if system_view.exists() and read(system_view).get('completed_utc'):
        q=read(system_view);result['new_SYSTEM_costed_view']=dict(q,evidence=(dest/system_view.relative_to(snapshot)).relative_to(out).as_posix())
        next(r for r in rows if r['case']=='opentpu_aux')['matching_current_physical_and_research_timing_view']=result['new_SYSTEM_costed_view']['evidence']
        cost=q['separate_cell_ECO_cost'];delta=cost['standard_cell_master_bbox_area_after_um2']-cost['standard_cell_master_bbox_area_before_um2']
        system_text='<p>92835导出与新SYS实际ODB/SPEF匹配的2229位物理/研究时序视图，全部原pin/PG/外框保持、SPEF余量准确重放。相对修复前实际新增'+str(cost['added_functional_instances_excluding_fillers'])+'个功能实例、'+str(cost['changed_master_original_instances'])+'个原实例换型、'+str(cost['moved_original_instances'])+'个原实例移动，标准单元master面积增加'+format(delta,'.3f')+'μm²；未新增spacer，原存储宏资源和位置保持。这些均为独立实现成本，不能归因纯XY或称block面积节省；完整功能与时序/电气仍待修复。</p>'
    rule_file=snapshot/'antenna_rules/r01/layer_rule_presence.tsv.gz';rule_text=''
    if rule_file.exists():
        with gzip.open(rule_file,'rt') as f:rules=list(csv.DictReader(f,delimiter='\t'))
        raw=gzip.decompress((rule_file.parent/'NangateOpenCellLibrary.macro.mod.lef.gz').read_bytes()).decode() if (rule_file.parent/'NangateOpenCellLibrary.macro.mod.lef.gz').exists() else None
        proof=read(rule_file.parent/'execution.json.gz')
        result['native_antenna_coverage_audit']={'layer_rules':rules,'source_files':proof['installed_source_files'],
          'native_returncode':proof['native_returncode'],'source_unchanged':proof['source_unchanged'],
          'source_macro_LEF_has_gate_area':None if raw is None else 'ANTENNAGATEAREA' in raw,
          'full_qualification':False,'evidence':(dest/rule_file.relative_to(snapshot)).relative_to(out).as_posix()}
        rule_text='<p><strong>92834已定位原生0的覆盖根因：</strong>M1–M10的hasDefaultAntennaRule与hasOxide2AntennaRule逐层均为0；原tech LEF没有天线关键字，macro LEF只有diode相关ANTENNADIFFAREA、没有ANTENNAGATEAREA。原GDS deck则启用300:1金属/实际gate面积检查并按实际扩散识别diode。原生缺规则/缺gate模型的0不能代表规则通过；需要从真实GDS补建模型或直接以不修改的GDS检查指导修复，不放宽300:1。</p>'
    from plot_equal_cost_controls import plot
    plot(result,out)
    integration_views=[]
    for rel in ['eco_views/r04/gemm-Aopt','eco_views/r04/mxu-Aopt','leaf_timing_models/r07/vector-C','leaf_timing_models/r07/llaccel_aux-C']:
        p=snapshot/rel/'execution.json.gz'
        if not p.exists():continue
        q=read(p)
        integration_views.append({'version':rel,'native_export_returncode':q.get('native_export_returncode'),
          'signal_bits':q.get('matching_all_signal_model_pins',q.get('actual_model_signal_pins')),
          'source_native_DRC':q.get('source_native_DRC',q.get('inherited_native_DRC_count')),
          'status':q.get('status','COSTED_ECO_VIEW_EXPORTED_NOT_QUALIFIED'),
          'full_qualification':False,'evidence':(dest/p.relative_to(snapshot)).relative_to(out).as_posix()})
    result['new_actual_integration_views']=integration_views
    trial=snapshot/'common_integration/r01/C/execution.json.gz'
    trial_receipt=read(trial) if trial.exists() else None
    result['actual_common_integration_trial']={'job':'92855','state':scheduler.get('92855',{}).get('State','UNKNOWN'),
      'status':trial_receipt.get('status') if trial_receipt else 'SOURCE_VIEW_PREPARATION_OR_NATIVE_EXECUTION_RUNNING',
      'terminal_receipt':trial_receipt,'qualified':False,'frozen':False}
    api=[]
    for rev in ['r01','r02']:
        p=snapshot/'fixed_wire_api'/rev/'execution.json.gz'
        if p.exists():
            q=read(p);api.append({'revision':rev,'native_returncode':q['native_returncode'],
              'DEF_fixed_M10_wire':q.get('DEF_has_FIXED_M10_wire'),'full_qualification':False,
              'evidence':(dest/p.relative_to(snapshot)).relative_to(out).as_posix()})
    result['fixed_signal_wire_native_API_probes']=api
    est=snapshot/'estimator_diagnosis/r01/execution.json.gz'
    result['VECTOR_isolated_estimator_trial']={'job':'92861','state':scheduler.get('92861',{}).get('State','UNKNOWN'),
      'receipt':read(est) if est.exists() else None,'qualification':False}
    early=snapshot/'estimator_diagnosis/r02/execution.json.gz'
    result['VECTOR_filler_order_control']={'job':'92867','state':scheduler.get('92867',{}).get('State','UNKNOWN'),
      'receipt':read(early) if early.exists() else None,'qualification':False}
    resumed=data/'runtime_submissions/vector_resume_r01.json'
    if resumed.exists():
        submit=read(resumed);initial=read(resumed.parent/'vector_resume_r01.execution.json.gz')
        assert not initial['repair_design_repeated'] and not initial['full_qualification']
        result['VECTOR_checkpoint_resume_submission']={'job':submit['job'],'source_driver_commit':submit['head'],
          'state_at_observation':submit['state_at_observation'],'observed_UTC':submit['observed_UTC'],
          'terminal_receipt':bool(initial.get('completed_utc')),'full_qualification':False,
          'evidence':resumed.relative_to(out).as_posix()}
        r=next(r for r in rows if r['case']=='vector');r['newer_attempt']={'previous_failure':r['newer_attempt'],
          'latest_checkpoint_resume':result['VECTOR_checkpoint_resume_submission']}
    live_vector=snapshot/'vector_resume/r01/execution.json.gz'
    if live_vector.exists():
        q=read(live_vector);result['VECTOR_physical_resume_latest']={'scheduler_state':scheduler.get('92872',{}).get('State','UNKNOWN'),
          'native_stage_returncodes':q.get('native_returncodes',{}),'terminal_receipt':bool(q.get('completed_utc')),
          'separate_cell_ECO_cost':q.get('separate_cell_ECO_cost'),'fresh_DRC_count':q.get('fresh_DRC_count'),
          'setup_ns':q.get('setup_ns'),'hold_ns':q.get('hold_ns'),
          'literal_VIOLATED_markers_not_complete_failure_count':q.get('literal_VIOLATED_markers_not_complete_failure_count'),
          'full_qualification':False,'evidence':(dest/live_vector.relative_to(snapshot)).relative_to(out).as_posix()}
        r=next(r for r in rows if r['case']=='vector');r['newer_attempt']['physical_resume_latest']=result['VECTOR_physical_resume_latest']
        if q.get('completed_utc'):
            assert q['all_sources_unchanged'] and all(q['source_pin_PG_die_unchanged'].values())
            r['prior_completed_source_before_latest_ECO']={k:r[k] for k in ['completed_source','actual_internal_route','native_DRC_count','all_multiterminal_signal_clock_geometry','setup_ns','hold_ns','violation_marker_rows']}
            r.update({'completed_source':'costed_VECTOR_resume/r01','actual_internal_route':'COMPLETED_COSTED_ECO_NOT_PURE_XY',
              'native_DRC_count':q['fresh_DRC_count'],'all_multiterminal_signal_clock_geometry':q['whole_signal_geometry']['pass'],
              'setup_ns':q['setup_ns'],'hold_ns':q['hold_ns'],'violation_marker_rows':q['literal_VIOLATED_markers_not_complete_failure_count'],
              'power_grid':'NATIVE_VDD_VSS_COMMANDS_EXECUTED','separate_cell_ECO_cost':q['separate_cell_ECO_cost']})
            r['evidence'].append((dest/live_vector.relative_to(snapshot)).relative_to(out).as_posix())
    diode=snapshot/'antenna_diode_eco/r01/gemm-C/execution.json.gz'
    if diode.exists():
        q=read(diode);result['GEMM_real_diode_ECO']={'scheduler_state':scheduler.get('92910',{}).get('State','UNKNOWN'),
          'receipt':q,'full_qualification':False,'original1460_repair_not_yet_verified':True,
          'strict_GDS_followup_job':'92912','strict_GDS_followup_state':scheduler.get('92912',{}).get('State','UNKNOWN'),
          'evidence':(dest/diode.relative_to(snapshot)).relative_to(out).as_posix()}
        stage_file=diode.parent/'stages.tsv.gz'
        if stage_file.exists():
            with gzip.open(stage_file,'rt') as f:result['GEMM_real_diode_ECO']['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
        if q.get('completed_utc'):
            for kind in ['setup','hold']:result['GEMM_real_diode_ECO'][kind+'_ns']=slack(diode.parent/(kind+'.txt.gz'))
            checks=gzip.decompress((diode.parent/'checks.txt.gz').read_bytes()).decode()
            result['GEMM_real_diode_ECO']['literal_VIOLATED_markers_not_complete_failure_count']=checks.count('(VIOLATED)')
            result['GEMM_real_diode_ECO']['max_capacitance_failures']=[{'pin':pin,'limit_ff':float(limit),'cap_ff':float(cap),'slack_ff':float(s)}
              for pin,limit,cap,s in re.findall(r'^(\S+)\s+([\d.]+)\s+([\d.]+)\s+(-[\d.]+)\s+\(VIOLATED\)',checks,re.M)]
    diode_proof=snapshot/'passive_load_equivalence/r01/gemm/execution.json.gz'
    if diode_proof.exists():
        result['GEMM_passive_load_digital_relation']=dict(read(diode_proof),evidence=(dest/diode_proof.relative_to(snapshot)).relative_to(out).as_posix())
    diode_stream=snapshot/'antenna_diode_stream/r01/gemm-C/execution.json.gz'
    diode_stream_text='92912仍在独立执行严格GDS和不修改的原deck，原1460项尚未作为已修复。'
    if diode_stream.exists():
        stream_proof=read(diode_stream)
        result['GEMM_real_diode_GDS_available_deck']=dict(stream_proof,evidence=(dest/diode_stream.relative_to(snapshot)).relative_to(out).as_posix())
        diode_stream_text='92912最新严格GDS merge='+str(stream_proof.get('merge_returncode'))+'、原deck return='+str(stream_proof.get('DRC_returncode'))+'、实际报项='+str(stream_proof.get('available_deck_findings'))+'；分类='+html.escape(str(stream_proof.get('available_deck_findings_by_category')))+'。不是完整制造规则、系统LVS或电气资格。'
        if stream_proof.get('merge_returncode')==stream_proof.get('DRC_returncode')==0:
            antenna_count=sum(v for k,v in stream_proof.get('available_deck_findings_by_category',{}).items() if 'ANTENNA' in k)
            result['GEMM_real_diode_ECO']['original1460_repair_not_yet_verified']=antenna_count!=0
    cap=snapshot/'diode_cap_eco/r01/gemm-C/execution.json.gz'
    cap_text=''
    if cap.exists():
        q=read(cap);result['GEMM_post_diode_size_ECO']=dict(q,evidence=(dest/cap.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            r=next(r for r in rows if r['case']=='gemm')
            r['historical_matched_costed_source_before_diode']={k:r[k] for k in ['completed_source','actual_internal_route','native_DRC_count','all_multiterminal_signal_clock_geometry','setup_ns','hold_ns','violation_marker_rows']}
            r.update({'prior_completed_source':r['completed_source'],'completed_source':'costed_real_diode_and_sizes/r01',
              'actual_internal_route':'COMPLETED_REAL_DIODE_AND_TWO_SIZE_ECO_NOT_PURE_XY',
              'native_DRC_count':q.get('fresh_DRC_count'),'all_multiterminal_signal_clock_geometry':q.get('whole_signal_geometry',{}).get('pass'),
              'setup_ns':q.get('setup_ns'),'hold_ns':q.get('hold_ns'),
              'violation_marker_rows':q.get('literal_VIOLATED_markers_not_complete_failure_count'),
              'complete_rules':'CURRENT_GDS_PENDING; PRIOR_REAL_DIODE_GDS37_FAILED; COVERAGE_INCOMPLETE'})
            cap_text='<p><strong>92940两处真实换型已终态：</strong>INV_X1→INV_X2、XNOR2_X1→XNOR2_X2的原Liberty逻辑/状态严格一致，新max-cap分别121.46/52.0325fF。当前fresh native0、所检全网连通、双PG和原pin/PG/外框保持；真实setup/hold='+str(q.get('setup_ns'))+'/'+str(q.get('hold_ns'))+'ns、VIOLATED文字标记='+str(q.get('literal_VIOLATED_markers_not_complete_failure_count'))+'。独立全量数字图验证仅这两个master改变，636真实diode及原信号端点/网络/端口全部保持。额外两换型/一个移动/master面积+1.330μm²单列，非XY或block面积收益。以上不是原636-diode版本的cap2已经不存在于历史；两版本分别保存。换型后GDS/原deck作业92943仍独立验证，未与旧版本37项混写。</p>'
    cap_stream=snapshot/'antenna_diode_stream/cap-r01/gemm-C/execution.json.gz'
    if cap_stream.exists():
        q=read(cap_stream);result['GEMM_post_diode_size_GDS_available_deck']=dict(q,evidence=(dest/cap_stream.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            r=next(r for r in rows if r['case']=='gemm')
            r['historical_costed_GDS_findings_before_diode']=r.get('available_deck_findings')
            r['available_deck_findings']=q['available_deck_findings']
            r['complete_rules']='CURRENT_REAL_DIODE_SIZE_GDS37_FAILED; COVERAGE_INCOMPLETE'
            cap_text+='<p><strong>92943新换型版严格GDS已终态FAILED：</strong>merge/原deck命令均0，但仍37项天线，不能因native/电气通过就称完整规则合格。该版本的DEF、GDS、RDB和原生全量几何均有独立SHA，不与旧37项直接混用。</p>'
    post_map=snapshot/'post_diode_netmap/cap-r01/execution.json.gz'
    if post_map.exists():
        q=read(post_map);result['GEMM_remaining_antenna_native_correlations']=dict(q,evidence=(dest/post_map.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('native_returncode')==0:
            a=q['correlation_summary'];markers=read(post_map.parent/'marker_net_correlations.json.gz')
            with (data/'gemm_remaining_antenna_nets.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['native_net','actual_marker_count','actual_layers','already_connected_real_diode','source_receipt'],lineterminator='\n');w.writeheader()
                for net in sorted({m['native_net'] for m in markers}):
                    group=[m for m in markers if m['native_net']==net]
                    w.writerow({'native_net':net,'actual_marker_count':len(group),'actual_layers':'/'.join(sorted({m['layer'] for m in group})),
                      'already_connected_real_diode':net in a['mapped_nets_already_with_real_diode'],'source_receipt':(dest/post_map.relative_to(snapshot)).relative_to(out).as_posix()})
            cap_text+='<p>92972已按新换型版精确SHA读取7516494行原生几何：37个真实GDS多边形均唯一关联22条真实网；与现有636个diode网交集为0，22条均尚无该ECO diode。<a href="data/gemm_remaining_antenna_nets.csv">全部22网及层级CSV</a>，原多边形/各网交面积证据保留。不是按bbox猜网或GDS LVS通过；下一步定向增量接入，不重复添加已有负载，不能提前称天线修复完成。</p>'
    path_audits=[]
    for case in ['vector','opentpu_aux']:
        p=snapshot/'actual_path_audit/r01'/case/'execution.json.gz'
        if p.exists():path_audits.append(dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
    result['latest_actual_extracted_path_audits']=path_audits
    chain=snapshot/'output_chain_placement/r01/opentpu_aux-C/execution.json.gz'
    if chain.exists():
        q=read(chain);result['SYSTEM_output_chain_placement']={'receipt':q,'full_qualification':False,
          'state':scheduler.get('92921',{}).get('State','UNKNOWN'),
          'evidence':(dest/chain.relative_to(snapshot)).relative_to(out).as_posix()}
    chain_resume_text=''
    upper_text=''
    incremental_text=''
    diode_views=snapshot/'diode_views/r01/gemm-C/execution.json.gz'
    if diode_views.exists():
        q=read(diode_views);result['GEMM_actual658_diode_physical_and_extracted_views']=dict(q,evidence=(dest/diode_views.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            incremental_text+='<p><strong>92997实际研究视图已导出：</strong>与658diode确定源逐SHA绑定的clean ODB、LEF/OBS、DEF、真实网表和非零提取时序Lib已生成；3753个signal pin及PG/尺寸/原M5/M6与原真实接口完全一致，SPEF余量精确重放、独立模型重读通过。minimum_period存在='+str(q.get('minimum_period_present'))+'，完整规则/RTL/新父层可达性及系统资格未闭合，不能当合格冻结。大视图、SPEF与工具/配置由终态回执逐SHA索引，未用最终LEF坐标修改冒充真实接线。</p>'
    incremental=snapshot/'antenna_incremental_eco/r01/gemm-C/execution.json.gz'
    if incremental.exists():
        q=read(incremental)
        item=dict(q,evidence=(dest/incremental.relative_to(snapshot)).relative_to(out).as_posix())
        result['GEMM_additional22_diode_actual_attempt']=item
        if q.get('native_returncodes',{}).get('implementation')==0:
            partial={}
            for kind in ['setup','hold']:
                p=incremental.parent/(kind+'.txt.gz')
                if p.exists():partial[kind+'_ns']=slack(p)
            p=incremental.parent/'checks.txt.gz'
            if p.exists():partial['literal_VIOLATED_markers_not_complete_failure_count']=gzip.decompress(p.read_bytes()).decode().count('(VIOLATED)')
            item['closed_native_implementation_STA_reports_not_fresh_DRC_or_final_graph']=partial
            incremental_text+='<p><strong>92975定向22个新增真实diode：</strong>原层接线/详细布线、原视图合同、双PG及RCX/STA原生命令均已执行；闭合原生进程报告setup/hold='+str(partial.get('setup_ns'))+'/'+str(partial.get('hold_ns'))+'ns，文字违例='+str(partial.get('literal_VIOLATED_markers_not_complete_failure_count'))+'。独立fresh DRC、全量数字图及源合同以最终receipt各自为准，未终态不记0/通过。92976为对应严格GDS原deck依赖作业；不把提交视为规则通过。旧37项原样保留。</p>'
        if q.get('completed_utc'):
            incremental_text+='<p>92975最终回执：fresh native='+str(q.get('fresh_DRC_count'))+'，全量22新增负载数字合同='+str(q.get('all_original_instances_and_signal_graph_preserved_with_only_22_real_diode_loads'))+'，原pose/端点='+str(q.get('all_prior_functional_and_636_diode_poses_and_terminals_unchanged'))+'。无论Slurm结局，完整规则/RTL/系统资格仍未通过。</p>'
            if q.get('native_returncodes',{}).get('implementation')==0 and q.get('fresh_DRC_count') is not None and 'whole_signal_geometry' in q:
                r=next(r for r in rows if r['case']=='gemm')
                r['historical_636diode_two_size_source']={k:r[k] for k in ['completed_source','actual_internal_route','native_DRC_count','all_multiterminal_signal_clock_geometry','setup_ns','hold_ns','violation_marker_rows','available_deck_findings']}
                r.update({'completed_source':'658_real_diodes/r01','actual_internal_route':'COMPLETED_INCREMENTAL_REAL_DIODE_ECO_NOT_PURE_XY',
                  'native_DRC_count':q['fresh_DRC_count'],'all_multiterminal_signal_clock_geometry':q['whole_signal_geometry']['pass'],
                  'setup_ns':q.get('setup_ns'),'hold_ns':q.get('hold_ns'),
                  'violation_marker_rows':q.get('literal_VIOLATED_markers_not_complete_failure_count'),
                  'available_deck_findings':None,'complete_rules':'CURRENT_658_DIODE_GDS_PENDING; COVERAGE_INCOMPLETE'})
    prepared=snapshot/'upper_adaptation_trial/r02/preparation.json.gz'
    if prepared.exists():
        q=read(prepared);result['upper_all770_actual_hook_preparation_r02']=dict(q,evidence=(dest/prepared.relative_to(snapshot)).relative_to(out).as_posix())
        upper_text='<p>92974前置已核查同一真实下层检查点的1541个M10接点、两唯一时钟alias及via10下层0.8×0.8μm落脚；两模式各770条边/1540个实际hook，256共享资源分别使用真实A/B两端。该核验只属于前置绑定，路由以逐模式真实终态为准；私有下层、叶块与完整检查未闭合，未冻结。</p>'
    per_mode=[]
    for mode in ['opentpu','llaccel']:
        p=snapshot/'upper_adaptation_trial/r02'/mode/'execution.json.gz'
        if p.exists():
            q=read(p);per_mode.append({'mode':mode,'receipt':q,
              'state':'FAILED_NATIVE_ROUTE' if q.get('completed_utc') and q.get('native_route_returncode') else 'COMPLETED_NATIVE_ROUTE_NOT_QUALIFIED' if q.get('completed_utc') else 'NOT_TERMINAL',
              'evidence':(dest/p.relative_to(snapshot)).relative_to(out).as_posix()})
    result['upper_all770_per_mode_actual_receipts_r02']=per_mode
    upper_terminal=snapshot/'upper_adaptation_trial/r02/trial_summary.json.gz'
    if upper_terminal.exists():
        q=read(upper_terminal);result['upper_all770_actual_terminal_r02']=dict(q,evidence=(dest/upper_terminal.relative_to(snapshot)).relative_to(out).as_posix())
        modes={m['mode']:m for m in q['modes']}
        if all(m.get('native_route_returncode')==1 for m in modes.values()):
            upper_text+='<p><strong>92974已终态FAILED，优先于此前运行中记录：</strong>openTPU及llaccel两个770边适配子试验均GRT-0116拥塞失败，未进入DRT；fresh DRC、完整边连通及实际M10 landing包含检查均未执行，不记0/通过。两者使用相同实际但未合格下层输入，仍不证明两功能已实现或冻结。原报告估计拥塞不是实际金属DRC；下一步定位原始congestion区域与接口/网格约束，不能只因耗时归因或放宽规则制造通过。</p>'
    tool=snapshot/'upper_tool_diagnosis/r01/execution.json.gz'
    if tool.exists():
        q=read(tool);result['upper_fullframe_two_edge_tool_diagnosis']=dict(q,evidence=(dest/tool.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            upper_text+='<p><strong>93015受控工具诊断终态：</strong>相同全frame/全部原M10 PG及OBS约束下的2/770条实际边，native route/fresh DRC0、2网/4端点所检连通通过；只证明子集，不能代表完整系统。失败检查点仍有770网的原生DB guide，已真实导出，不因grt::have_routes=0猜测数据不存在。下一步复用完整DB guide继续DRT，原GRT-0116仍记FAILED，不重跑同一全局搜索或使用allow_congestion/infinite_cap改变结果。</p>'
    for revision in ['r01','r02']:
        p=snapshot/('tool_api/grt-start-'+revision+'/execution.json.gz')
        if p.exists():result['native_GRT_capability_'+revision]=dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
    p=snapshot/'upper_detailed_resume/r01/summary.json.gz'
    if p.exists():
        q=read(p);result['all770_native_guide_detail_continuation_r01']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        result['all770_native_guide_detail_mode_receipts_r01']=[]
        for mode in ['opentpu','llaccel']:
            f=snapshot/'upper_detailed_resume/r01'/mode/'execution.json.gz'
            if f.exists():result['all770_native_guide_detail_mode_receipts_r01'].append(dict(read(f),evidence=(dest/f.relative_to(snapshot)).relative_to(out).as_posix()))
        upper_text+='<p><strong>93025全770原生guide接续已FAILED：</strong>两个模式均实际进入DRT，pin access完成后报DRT-0352：Input route guides are congested。没有生成实际适配布线，fresh DRC、770边物理连通、M10 landing包含检查未执行，不能填0或通过。全部原DB guide和原GRT-0116失败保留，输入/层/规则未改变；2边成功不推广为全量成功。后续依据原生API的搜索预算参数作独立试验，不能以allow_congestion/infinite_cap绕开原失败。</p>'
    p=snapshot/'actual_path_audit/r02/opentpu_aux/execution.json.gz'
    if p.exists():
        q=read(p);result['SYSTEM_current_relocated_source_path_audit']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            from plot_actual_system_m2 import plot
            diagnosis=plot(snapshot,out);result['SYSTEM_actual_M2_and_current_path_diagnosis']=diagnosis
            upper_text+='<p><strong>93028新SYSTEM真实SPEF路径诊断已完成：</strong>精确重放92968源的setup/hold −0.056303/−0.119814ns；当前最差setup由u_slice.u_quant.ackw寄存器到bit_114845，最差hold由bit_1216到_28604_[223]寄存器，不使用旧92781源路径解释新版本。只读导出两DRC所属实际网_215139_的全层矩形，原SDC/ODB/SPEF保持；不是修复通过。<a href="data/system_actual_M2_and_current_paths.json">当前路径及来源SHA</a> · <a href="data/system_actual_M2_net_rectangles.csv">实际矩形CSV</a>。</p><img loading="lazy" src="assets/system_actual_M2_conflict.png"><p><a href="assets/system_actual_M2_conflict.svg">实际M2报项SVG</a>。只画该网，空白不表示周围无金属/PDN/OBS；红框是原生DRC bbox，显示线宽不是物理尺寸。</p>'
    failed=snapshot/'logs/system-patch-r01-93031.log.gz'
    if failed.exists():
        result['SYSTEM_clean_patch_r01_preparation_failure']={'state':'FAILED_BEFORE_NATIVE_ROUTING','job_id':'93031','evidence':(dest/failed.relative_to(snapshot)).relative_to(out).as_posix(),'full_qualification':False}
        upper_text+='<p><strong>93031新clean_patches试验前置失败：</strong>驱动在服务器端对容器内部标准单元Lib路径计算SHA，FileNotFoundError，尚未执行路由/RC/STA。原日志与空输出目录保留；修订驱动只在原工具镜像内读取同一Lib并记录前后SHA，新r02尚未提交，不能记修复通过。</p>'
    search=[]
    for mode in ['opentpu','llaccel']:
        p=snapshot/'upper_search_budget/r01'/mode/'execution.json.gz'
        if p.exists():search.append(dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
    if search:
        result['all770_search_budget200_mode_receipts_r01']=search
        upper_text+='<p>93030是新的独立搜索试验：FastRoute拥塞迭代预算由默认50增加到200，verbose记录实际迭代；相同原DB、770边、轨道、PG/OBS、pin和物理规则，原GRT/DRT失败保留。终态以原生回执为准，运行中不算通过；下层仍未合格冻结。</p>'
        for q in search:
            if q.get('completed_utc'):
                upper_text+='<p><strong>200次搜索 '+html.escape(q['mode'])+' 子试验已终态：</strong>native返回'+str(q.get('native_returncodes'))+'，原生阶段'+str(q.get('native_stage_status'))+'。GRT失败的模式没有进入DRT/fresh/完整连通/RC/STA；原物理规则与全部770边不变，不能当系统实现或架构不可行证明。</p>'
    p=snapshot/'system_patch_route/r02/opentpu_aux-C/execution.json.gz'
    if p.exists():
        q=read(p);result['SYSTEM_native_clean_patches_r02_attempt']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        state=('终态：native '+str(q.get('native_returncodes'))+'，fresh DRC '+str(q.get('fresh_DRC_count','未取得'))+'，setup/hold '+str(q.get('setup_ns','未取得'))+'/'+str(q.get('hold_ns','未取得'))+'ns') if q.get('completed_utc') else '实际运行中，最终fresh/RC/STA尚未取得'
        upper_text+='<p><strong>93038 SYSTEM native clean_patches/r02：</strong>'+state+'。在原容器内核验同一Lib，保留93031前置失败；不改pin/单元/PG/原OBS/原SDC与层集合。该新试验不是改检查或时序闭合，当前矩阵已完成源与新尝试分别记录。</p>'
    failed=snapshot/'logs/mxu-escape-r01-93040.log.gz'
    if failed.exists():
        result['MXU_escape_r01_preparation_failure']={'state':'FAILED_BEFORE_NATIVE_ROUTING','job_id':'93040','evidence':(dest/failed.relative_to(snapshot)).relative_to(out).as_posix(),'full_qualification':False}
        upper_text+='<p><strong>93040 MXU M6引出试验前置失败：</strong>旧叶回执不含SYSTEM格式setup_ns字段，KeyError，未进入路由；原日志保留。r02改为按SHA读取原生setup/hold原文，不改变物理输入或试验约束。</p>'
    p=snapshot/'pin_escape_route/r02/mxu-C/execution.json.gz'
    if p.exists():
        q=read(p);result['MXU_actual_M6_escape_r02_attempt']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        state=('终态：native '+str(q.get('native_returncodes'))+'，fresh DRC '+str(q.get('fresh_DRC_count','未取得'))+'，setup/hold '+str(q.get('setup_ns','未取得'))+'/'+str(q.get('hold_ns','未取得'))+'ns') if q.get('completed_utc') else '实际运行中，尚无最终路由/视图/RC/STA回执'
        upper_text+='<p><strong>93041 MXU实际M6接入重接/r02：</strong>'+state+'。从成本ECO/r04源保持原act_data[12]的M6层、XY及0.14×0.14μm尺寸，临时M6路由ring约束引导真实接线，完成后移除仅本次新增约束；保留原占用OBS，不剪去真实金属。gap/thickness各0.14μm只是临时约束参数，不替代M6完整spacing规则。新父层可达性/DRC未执行，不能凭叶native0宣称原M6–OBS报项已修复。</p>'
        if q.get('completed_utc') and q.get('fresh_DRC_count')==0 and q.get('whole_signal_geometry',{}).get('pass') and all(q.get('all_cells_poses_original_connections_pins_PG_die_unchanged',{}).values()):
            r=next(r for r in rows if r['case']=='mxu');r['historical_source_before_M6_escape']=json.loads(json.dumps(r))
            r.update({'completed_source':'M6_escape_route/r02','actual_internal_route':'COMPLETED_M6_ACCESS_REROUTE_ORIGINAL_PIN_XY_UNCHANGED',
              'native_DRC_count':0,'all_multiterminal_signal_clock_geometry':True,'setup_ns':q.get('setup_ns'),'hold_ns':q.get('hold_ns'),
              'violation_marker_rows':q.get('literal_VIOLATED_markers_not_complete_failure_count'),
              'complete_rules':'CURRENT_M6_ESCAPE_GDS_NOT_EXECUTED_MISSING_REAL_SRAM_AND_COVERAGE_GAPS',
              'historical_strict_GDS_merge_errors':r.get('strict_GDS_merge_errors'),'strict_GDS_merge_errors':None,
              'historical_available_deck_findings':r.get('available_deck_findings'),'available_deck_findings':None,
              'parent_access':'NEW_M6_ESCAPE_OBS_NOT_YET_VALIDATED_IN_PARENT','current_source_research_model':'NOT_EXPORTED',
              'common_base_source_selection':'ORIGINAL_R02_NOT_UPGRADED_TO_THIS_SOURCE'})
    for revision in ['r01','r02']:
        failure=snapshot/'escape_fixtures'/('gemm658-'+revision)/'gemm-C/driver_failure.json.gz'
        attempt=snapshot/'escape_fixtures'/('gemm658-'+revision)/'gemm-C/execution.json.gz'
        if failure.exists():
            q=read(failure);result['GEMM_actual658_parent_'+revision+'_preparation_failure']=dict(q,evidence=(dest/failure.relative_to(snapshot)).relative_to(out).as_posix())
            upper_text+='<p><strong>GEMM658父层93043前置失败：</strong>旧修订M10坐标未满足当前真实OBS/PG/其他接点的重新筛查，断言拒绝，未路由；不是原生金属DRC结论。旧92841只代表旧叶源，失败不覆盖。新r02复用经SHA绑定的真实detailed LEF，并在当前源内重新选择128号新增父M10点，原叶M5/M6不改。</p>'
        if attempt.exists():
            q=read(attempt);result['GEMM_actual658_parent_'+revision+'_attempt']=dict(q,evidence=(dest/attempt.relative_to(snapshot)).relative_to(out).as_posix())
            if q.get('completed_utc'):
                upper_text+='<p><strong>GEMM658父层93049终态FAILED：</strong>已通过当前源重新选点，实际使用658diode clean ODB/匹配非零模型与全部3753原信号位；严格GRT仍GRT-0116拥塞失败，未执行DRT/fresh/所检全网连通/RC/STA，不能用旧父层native0替代。原DB/LEF/模型SHA保持，256个新增M10接点与原叶M5/M6分别记录；新128号点为787.295/944.07μm，6.4μm只是局部搜索packing guard，不是通用技术规则。</p>'
    p=snapshot/'vector_clone_probe/r01/execution.json.gz'
    if p.exists():
        q=read(p);result['VECTOR_actual_gate_clone_probe_r01']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            upper_text+='<p><strong>VECTOR93048已FAILED：</strong>同一当前r01源/原SDC，在remove_fillers和placement估计后，setup优化首次迭代前Signal11/native−11；不是逻辑不可能证明，也未定位为CloneMove本身的根因。未生成修复检查点、after指纹或后续合法化/布线/RC/STA，pin/PG保持的after检查未执行，不能把缺失输出的false当实际改了pin。原闭合源文件保持，原−4.140220ns失败继续保留。24GB sbatch请求此前已被调度器拒绝且无作业号，后按实际c96内存配置复用mem=0才提交；两个阶段分别记录。</p>'
    p=snapshot/'vector_clone_probe/r02/execution.json.gz'
    if p.exists():
        q=read(p);result['VECTOR_original_GRT_context_probe_r02']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            upper_text+='<p><strong>VECTOR93073上下文试验已FAILED：</strong>原guide/GRT上下文已实际初始化，setup优化超过原崩溃位置后报RSZ-0074：无法从global routes为pin _362545_/ZN、net _080826_建立完整树（找到1个pin、应为2个）。不是Signal11根因已解决或时序改善。未生成可用检查点、after合同、合法化/新详细布线/RC/STA；原闭合源SHA保持，−4.140220ns失败不替换。原回执repair_model固定文本仍写无GRT，实际r02脚本/阶段/new_single_context_change表明已加载原guide；本段明确纠正解释，原回执不改写。下一步需原生内部route同步或不依赖残缺guide的工具修复，不无变化重试。</p>'
    for key,relative,title in [
      ('SYSTEM_actual_stacked_via_r01','system_stacked_via_route/r01/opentpu_aux-C','93072 SYSTEM原生via叠放接线'),
      ('MXU_actual_view_parent_recheck_r01','escape_view_recheck/r01/mxu-C','93074 MXU全部2172真实父层复核')]:
        p=snapshot/relative/'execution.json.gz'
        if not p.exists():continue
        q=read(p);result[key]=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        state=('终态；native='+str(q.get('native_returncodes'))+'；fresh DRC='+str(q.get('fresh_DRC_count','未执行'))) if q.get('completed_utc') else '运行中；缺终态项不记0/通过'
        upper_text+='<p><strong>'+title+'：</strong>'+state+'。SYSTEM使用原网实际via1/via2定义及原M1端点重接，不是修改最终LEF；单网物理改变、全部网连通/PG/RC/原SDC独立检查。MXU在原2172条真实父层路线/PG上换入新actual LEF/OBS，原pin层/尺寸/位置/语义保持，不剪真实OBS；它只复核接入，不是父层RC/STA或共同底座资格。原失败及输入SHA保留。</p>'
        if key=='SYSTEM_actual_stacked_via_r01' and q.get('completed_utc'):
            upper_text+='<p><strong>SYSTEM93072实际DRC修复已闭合，时序仍失败：</strong>fresh native='+str(q.get('fresh_DRC_count'))+'，setup/hold='+str(q.get('setup_ns'))+'/'+str(q.get('hold_ns'))+'ns、原文字违例'+str(q.get('literal_VIOLATED_markers_not_complete_failure_count'))+'。466332网/1474481端点所检连通、双PG/RCX/原SDC已执行，原cell/pose/连接/pin/PG/外框SHA保持；全部多端网WIRE/VIA矩形多重集比较只_215139_改变，其余466331网表示相同，不把矩形表示等同几何并集或RC等价。作业门槛保留负时序，Slurm FAILED不抹去fresh0事实，fresh0也不提升为全部资格。当前矩阵升级到实际新源，未导出新匹配研究视图或父层/完整GDS验证。</p>'
    p=snapshot/'logs/sta-coverage-api-r01-93075.log.gz'
    if p.exists():
        q={'job':'93075','state':'WRAPPER_FAILED_AFTER_NATIVE_CAPABILITY_LOG','error':'NameError: sha not imported while writing metadata','full_qualification':False,
           'evidence':(dest/p.relative_to(snapshot)).relative_to(out).as_posix()}
        result['STA_coverage_capability_wrapper_failure']=q
        upper_text+='<p><strong>93075能力探针包装失败保留：</strong>原生工具已完整输出report_check_types帮助及库声明，但Python写元数据时漏导入sha，NameError，Slurm FAILED；不伪造成功回执，也不重跑同一只读探针。原生帮助确认支持min_pulse_width/min_period/max_skew及clock_gating_setup/hold；实际typical库有45处min_pulse_width timing_type、无minimum_period timing_type声明，计数不是设计检查通过。已修正脚本供复用，新的六块逐源RC/原SDC扩展检查单独提交，空报告不能当库已定义或签核通过。</p>'
    extended=[]
    for case in CASES:
        p=snapshot/'extended_sta/r01'/case/'execution.json.gz'
        if p.exists():extended.append(dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
    if extended:
        result['source_bound_extended_STA_r01']=extended
        upper_text+='<p>93076新的六块扩展STA：按各自已闭合实际ODB/SPEF/原SDC逐SHA重读，补查原生min pulse width、min period、max skew、gating setup/hold及min slew/cap/fanout，输出真实clock/skew/latency、约束与寄生覆盖。每块终态及源余量重放分别记录；未终态不当通过，派生path minimum period与缺失Liberty minimum_period规则严格区分。这个只读覆盖审计不改变设计，也不修复原负时序。</p>'
        upper_text+='<table><thead><tr><th>扩展检查对象</th><th>实际源版本</th><th>原生执行</th><th>setup/hold原文重放</th><th>新增检查文字VIOLATED</th><th>证据</th></tr></thead><tbody>'
        for q in extended:
            complete=bool(q.get('completed_utc'));r=next(r for r in rows if r['case']==q['case'])
            r['source_bound_extended_STA_audit']={'completed':complete,'native_returncode':q.get('native_returncode'),
              'actual_source':q['actual_source'],'exact_slack_replay':q.get('source_worst_slacks_exactly_replayed'),
              'literal_VIOLATED_not_complete_rule_coverage':q.get('extended_literal_VIOLATED_rows_not_complete_rule_coverage'),
              'evidence':q['evidence'],'full_qualification':False}
            upper_text+='<tr><td>'+html.escape(q['case'])+'</td><td>'+html.escape(q['actual_source'].split('/full-pin-20261027/',1)[-1])+'</td><td>'+('return '+str(q.get('native_returncode')) if complete else '运行中')+'</td><td>'+str(q.get('source_worst_slacks_exactly_replayed','未取得'))+'</td><td>'+str(q.get('extended_literal_VIOLATED_rows_not_complete_rule_coverage','未知'))+'</td><td><a href="'+q['evidence']+'">原生回执/文件SHA</a></td></tr>'
        upper_text+='</tbody></table><p>表中0只表示新增报表没有文字VIOLATED；不表示全部规则已定义或系统时序通过。原有setup/hold、电气、未标注寄生和minimum_period覆盖缺项仍独立保留。</p>'
    p=snapshot/'vector_clone_probe/r03/execution.json.gz'
    if p.exists():
        q=read(p);result['VECTOR_placement_only_context_probe_r03']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        upper_text+='<p><strong>VECTOR93083受控placement上下文试验：</strong>从实际安装repair_timing Tcl body取得证据：design_is_routed为真时会切换detailed_routing寄生来源，不能仅凭此前estimate_parasitics -placement宣称优化过程保持placement模式。新试验只在内存副本移除旧SIGNAL/CLOCK dbWire，原文件/单元/端点/pin/PG/层集合/原SDC不改；原生谓词由1变0、375675条旧wire被移除，进入placement优化。新检查点尚不代表合法化、详细接线、RC/STA、数字等价或修复成功，旧两个失败保留。</p>'
    screen=data/'upper_planned_via10_pair_screen_r01/summary.json'
    if screen.exists():
        q=read(screen);result['planned_default_via10_pair_geometric_screen']=q
        upper_text+='<p>两模式各1540个原生M10 hook上<strong>计划</strong>的默认via10单cut接入，逐一检查1185030对矩形，最小cut矩形间距2.4μm；相对明确假设0.88μm未发现成对冲突。坐标与0.8μm cut模板来自真实hook plan，原叶M5/M6不改。这不是已放置via、实际DRC、OBS/PG/PRL/包围检查或完整布通，也不证明已找到GRT失败根因。<a href="data/upper_planned_via10_pair_screen_r01/summary.json">全部来源/假设</a> · <a href="data/upper_planned_via10_pair_screen_r01/planned_via10_nearest.csv">每个计划接点最近邻CSV</a>。</p>'
    p=snapshot/'system_stacked_via_views/r01/opentpu_aux-C/execution.json.gz'
    if p.exists():
        q=read(p);result['SYSTEM_actual_stacked_via_physical_RC_views']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            upper_text+='<p><strong>93089 SYSTEM当前源实际视图：</strong>native export='+str(q.get('native_export_returncode'))+'、独立模型重读='+str(q.get('fresh_model_read_returncode'))+'，匹配全部'+str(q.get('matching_all_signal_model_pins'))+'个信号位及原PG/层/尺寸，真实SPEF余量重放='+str(q.get('SPEF_replay_matches_source'))+'。新源扩展检查独立执行、原负setup/hold不删；minimum_period覆盖仍缺失，不是父层、完整GDS/RTL或系统资格。两份当前真实ODB各自导出完整_215139_矩形，非根据脚本猜测路线。</p>'
    from plot_system_stacked_via_actual import plot as plot_stacked
    actual_stacked=plot_stacked(snapshot,out)
    from plot_llsys_actual_via_tips import plot as plot_llsys_tips
    actual_llsys_tips=plot_llsys_tips(snapshot,out)
    if actual_llsys_tips:
        result['LL_SYSTEM_actual_via_tip_figure']=actual_llsys_tips
        upper_text+='<h3>LL SYSTEM：三处实际 pin / 末端接线修复</h3><p>真实原网的M4–M7与via4–via6矩形局部放大，左右同尺度。保留完整内部C；fresh native4→0，但负setup/hold、父层接入和完整规则缺项均保留。白底不代表无异网/PG/OBS，图不替代验证。</p><img src="assets/llsys_actual_via_tip_repair.png" alt="LL SYSTEM三处真实pin前后矩形"><p><a href="assets/llsys_actual_via_tip_repair.svg">SVG</a> · <a href="data/llsys_actual_via_tip_repair.json">原文SHA及验证范围</a></p>'
    if actual_stacked:
        result['SYSTEM_actual_stacked_via_figure']=actual_stacked
        upper_text+='<img loading="lazy" src="assets/system_stacked_via_actual.png" alt="SYSTEM实际接线前后原生矩形，native2变0但时序失败"><p><a href="assets/system_stacked_via_actual.svg">真实接入修复SVG</a> · <a href="data/system_stacked_via_actual_rectangles.csv">两份完整目标网实际矩形CSV</a> · <a href="data/system_stacked_via_actual.json">源SHA及未验证项</a>。坐标同尺度、矩形为实际尺寸；周边异网/PG/OBS未绘，白底不是空闲。</p>'
    q=result.get('VECTOR_placement_only_context_probe_r03',{})
    if q.get('completed_utc'):
        upper_text+='<p><strong>93083原生placement优化阶段已完成，尚非物理实现：</strong>原生返回'+str(q.get('native_returncodes'))+'；实际待布线检查点新增49个BUF、365处换型，master bbox面积较当前r01再增约354.046μm²，保留原负启发式余量（−4.179502/0.014579ns）。这不是提取RC或时序改善，不是block面积变化，原917.700μm²等此前成本另继承。原pin/PG/外框保持，尚未合法化/详细接线或RC/STA。</p>'
    p=snapshot/'vector_probe_equivalence/r01/execution.json.gz'
    if p.exists():
        q=read(p);result['VECTOR_probe_strict_directed_buffer_relation_r01']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc') and not q.get('relative_mapped_digital_contract_pass'):
            upper_text+='<p><strong>93094严格数字关系检查FAILED：</strong>复用原生source/repaired完整图并按SHA核验，没有重复导出或跑P&amp;R。消去新增buffer后仍有原逻辑网拆分（An original logical net split after buffer elimination），当前检查点不能提升为合格新实现；不能仅凭新增单元全为BUF或状态单元合同相同就宣布功能等价。原失败、全部原生图及Liberty保留，下一步逐端点定位；尚未排除实际逻辑损坏，也未完成更一般等价证明。新P&amp;R驱动的前置门槛要求此关系通过，尚未提交。</p>'
    p=snapshot/'vector_probe_partition_diagnosis/r01/execution.json.gz'
    if p.exists():
        q=read(p);result['VECTOR_strict_partition_failure_diagnosis_r01']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            upper_text+='<p><strong>93102原始分区失败已定位：</strong>确实只有net83166一条原网、11个原端点；5个输入被改接net158807，包含AOI/NAND输入及place83183/A。CSV枚举全部失败原网，原生图/SHA及11个实际端点均保留。这是分区检查定位，不宣称原优化必定改变布尔功能，也不豁免原失败。</p>'
    p=snapshot/'vector_partition_restore/r01/execution.json.gz'
    if p.exists():
        q=read(p);result['VECTOR_actual_five_input_partition_restore_r01']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            upper_text+='<p><strong>93106实际五输入恢复：</strong>先模拟接回真实原驱动place83184/Z所在net83166并要求未修改的严格比较器通过，再在native ODB中真实改接5个输入、重新导出完整原生图，同一严格关系检查='+str(q.get('relative_mapped_digital_contract_pass'))+'。原321905个非filler实例、1076467个信号端点、2246顶层端口及380561驱动分量核对，49个新增BUF为无环有向恒等链、365换型Liberty合同匹配、607个NULL端点逐项保持。原cell master/位置/面积及pin/PG/外框不变；本次只恢复网络，未加单元/换型。原失败版本另存，新检查点仍未合法化、详细接线、RC/STA或RTL/系统等价，不能据此提升完整物理资格。下一步才在严格通过的新源上实际跑P&amp;R；原VECTOR已布线源仍是r01负时序版本。</p>'
            next(r for r in rows if r['case']=='vector')['new_unrouted_partition_restored_variant']={'relative_mapped_relation_pass':q.get('relative_mapped_digital_contract_pass'),
              'legality_route_RC_STA':'NOT_EXECUTED','full_qualification':False,'evidence':(dest/p.relative_to(snapshot)).relative_to(out).as_posix()}
    p=snapshot/'llsys_DRC_diagnosis/r01/execution.json.gz'
    if p.exists():
        q=read(p);result['LLSYSTEM_actual_four_marker_diagnosis_r01']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            upper_text+='<p><strong>93092 LL SYSTEM实际四DRC诊断：</strong>在有完整13184个内部移动pin的PG-only备选源，全部四原生报项对应三网bit_1382013、bit_6907、bit_1389626。按闭合725253网全块原生导出SHA，保留三条完整目标网862行接入矩形及局部831行真实多端信号/时钟几何，并从同一clean ODB另读真实固定VDD/VSS与OBS。原文件/PG/约束不改；这是定位，不是修复或DRC通过。原full-window92690/92691继续，备选不冒充新窗口终态；单端未用网和库内部GDS金属覆盖缺项单列。</p>'
    phase=[]
    for mode in ['opentpu','llaccel']:
        p=snapshot/'upper_grid_phase/r01'/mode/'execution.json.gz'
        if p.exists():phase.append(dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
    if phase:
        result['all770_grid_phase_half_r01']=phase
        upper_text+='<p>93090在新目录实际运行两模式770边guide grid相位试验：原点改为2850/2850 DBU（1.425μm），保留默认50次搜索及原物理轨道/层/规则/hook XY/PG/OBS；只测试离散网格敏感性，不等于根因已定位或布通。原200次/原50次/DRT失败保留；原R02未合格底座输入仍未升级到新叶源，未合格冻结。</p>'
        for q in phase:
            if q.get('completed_utc'):
                upper_text+='<p>网格相位 '+html.escape(q['mode'])+' 子模式终态：native='+str(q.get('native_returncodes'))+'，实际阶段='+str(q.get('native_stage_status'))+'。GRT失败则DRT/fresh/全边连通/RC/STA未执行，不用Slurm另一子模式仍运行覆盖此失败。</p>'
    p=snapshot/'vector_probe_route/r01/execution.json.gz'
    if p.exists():
        q=read(p);result['VECTOR_partition_restored_actual_PNR_r01']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        next(r for r in rows if r['case']=='vector')['new_partition_restored_actual_PNR']=dict(q,full_qualification=False)
        upper_text+='<p><strong>93112 VECTOR已从严格通过的真实五输入恢复源继续P&amp;R：</strong>source_kind='+html.escape(str(q.get('source_kind')))+'，原生子阶段返回='+html.escape(str(q.get('native_returncodes')))+'。本轮不重复setup/hold启发式优化，原SDC/时钟/负载/允许层保持，单元和buffer成本继承并单列；原生合法化、placement检查和原filler恢复以实际阶段记录为准。详细布线尚无闭合回执时，fresh DRC/全块连通/RC/STA均不填写通过，主矩阵继续保留旧实际已布线负时序源。</p>'
        if q.get('completed_utc'):
            g=q.get('whole_signal_geometry',{})
            upper_text+='<p><strong>该VECTOR新变体已终态：</strong>fresh native='+str(q.get('fresh_DRC_count'))+'，所检完整信号/时钟几何='+str(g.get('pass'))+'（'+str(g.get('checked_nets'))+'网、'+str(g.get('checked_terminals'))+'端点），双PG/RCX/STA阶段='+html.escape(str(q.get('route_stage_status')))+'；真实setup/hold='+str(q.get('setup_ns'))+'/'+str(q.get('hold_ns'))+'ns，文字VIOLATED='+str(q.get('literal_VIOLATED_markers_not_complete_failure_count'))+'。整体仍失败，未完成RTL/完整规则/新源父层或系统资格。与旧r01的−4.140220/0.037989ns相比，当前修复未改善这组提取余量且增加单元成本；保留可实现的内部C源，不退回边界，也不把此变体提升为主源或纯XY收益。</p>'
    p=snapshot/'vector_probe_cost_audit/r01/execution.json.gz'
    if p.exists():
        q=read(p);result['VECTOR_actual_probe_cost_category_audit']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('all_original_uncategorized_cost_counts_reproduced'):
            upper_text+='<p><strong>93128闭合实际成本复核：</strong>新增'+str(q['added_NONFILLER_instances'])+'个非filler单元，'+str(q['changed_master_original_NONFILLER_instances'])+'个原非filler换型、'+str(q['moved_original_NONFILLER_instances'])+'个原非filler移动；另有'+str(q['changed_master_reused_CORE_SPACER_names'])+'个重复filler实例名对应的master变化。原回执459个master变化是365个非filler＋94个filler，不能全称逻辑换型。排除BLOCK/filler的标准单元master面积增量仍约354.046μm²；旧+917.700μm²另继承，外框不缩小，无面积节省或纯XY声称。原回执/实际CSV保持，未重新优化或P&amp;R。</p>'
    preconnected=[]
    for mode in ['opentpu','llaccel']:
        p=snapshot/'upper_preconnected/r01'/mode/'execution.json.gz'
        if not p.exists():continue
        q=dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        deffile=p.parent/'preconnected_adapter.def.gz';planfile=p.parent/'physical_quotient_plan.json.gz'
        if deffile.exists() and planfile.exists():
            text=gzip.decompress(deffile.read_bytes()).decode();plan=read(planfile)
            section=re.search(r'^NETS\s+514\s*;\s*(.*?)^END NETS\s*$',text,re.M|re.S);assert section
            native=dict(re.findall(r'^\s*-\s+(\S+)\s+(.*?);',section.group(1),re.M|re.S))
            assert set(native)=={g['net'] for g in plan} and len(native)==514
            assert sorted(i for g in plan for i in g['edge_ids'])==list(range(770))
            fixed=0;terminals=set()
            for g in plan:
                pins=re.findall(r'\(\s*PIN\s+(\S+)\s*\)',native[g['net']])
                assert len(pins)==len(set(pins)) and set(pins)=={h['helper_pin'] for h in g['endpoints']}
                assert not terminals.intersection(pins);terminals.update(pins)
                if g['fixed_conductor']:
                    assert re.search(r'\+\s+FIXED\s+metal10\b',native[g['net']]);fixed+=1
            assert len(terminals)==1540 and fixed==256
            q['snapshot_actual_native_DEF_context_check']={'native_nets':514,'native_terminals':1540,
              'all770_original_edge_memberships_preserved':True,'native_FIXED_M10_paths':256,
              'DEF_SHA256':hashlib.sha256(gzip.decompress(deffile.read_bytes())).hexdigest(),
              'scope':'Native pre-route DEF memberships and FIXED status only; routed geometry, native DRC, freeze and actual functional systems NOT established'}
        guidefile=p.parent/'route.guide.gz'
        geom=q.get('actual_all_net_geometry',{})
        if q.get('completed_utc') and planfile.exists() and guidefile.exists() and geom.get('checked_nets')==514:
            raw=gzip.decompress(guidefile.read_bytes());assert hashlib.sha256(raw).hexdigest()==q['files']['route.guide']['sha256']
            names={g['net'] for g in plan};guides={s.strip() for s in raw.decode().splitlines() if s.strip() in names}
            failures=geom['nets'];assert len(failures)==geom['failed_nets'] and len(plan)==514
            original=read(snapshot/'upper_adaptation_trial/r02'/(mode+'_actual_hook_plan.json.gz'))
            detail=[]
            for g in plan:
                bad=failures.get(g['net']);connected=0
                for eid in g['edge_ids']:
                    links={"B:"+h['helper_pin'] for h in original['physical_edges'][eid]['endpoints']}
                    connected+=int(not bad or any(links<=set(ts) for ts in bad['terminal_groups']))
                detail.append({'net':g['net'],'shared_fixed_M10':bool(g['fixed_conductor']),
                  'native_guide_present':g['net'] in guides,'original_edge_ids':';'.join(map(str,g['edge_ids'])),
                  'original_edge_count':len(g['edge_ids']),'connected_original_edges':connected,
                  'disconnected_original_edges':len(g['edge_ids'])-connected,
                  'native_terminal_components':bad['terminal_components'] if bad else 1})
            detailfile=data/('preconnected_'+mode+'_r01_actual_guide_and_edge_coverage.csv')
            with detailfile.open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(detail[0]),lineterminator='\n');w.writeheader();w.writerows(detail)
            q['closed_native_guide_and_original_edge_diagnosis']={'native_nets_with_guides':len(guides),
              'fixed_shared_nets_without_guides':sum(r['shared_fixed_M10'] and not r['native_guide_present'] for r in detail),
              'original_edges_connected':sum(r['connected_original_edges'] for r in detail),
              'original_edges_disconnected':sum(r['disconnected_original_edges'] for r in detail),
              'all_770_edges_enumerated':sum(r['original_edge_count'] for r in detail)==770,
              'detail_csv':detailfile.relative_to(out).as_posix(),
              'scope':'Closed native guides plus actual rectangle terminal-component result; observed skipped shared fragments, not an upstream source-level diagnosis'}
        preconnected.append(q)
    if preconnected:
        result['all770_actual_preconnected_context_r01']=preconnected
        upper_text+='<p><strong>93117两模式真实固定预连上下文试验：</strong>保持全部770条原适配边、1540个实际M10 hook及256条原FIXED M10导体不变，仅将已经由同一实际导体连接的两条适配支路合为同一物理网络交给原生路由。每模式514个物理网＝256个四端共享网＋256个两端旁路＋2个时钟网；770条原逻辑边逐条保留，不是删256条边或减少预连预算。辅助端口包含被动接点，其输入标签不代表额外功能驱动；该helper仍不是加速器RTL或有效STA模型。原两支路分开路由的失败保留，未断言其表示就是失败根因。</p>'
        for q in preconnected:
            actual=q.get('snapshot_actual_native_DEF_context_check')
            status='尚未终态' if not q.get('completed_utc') else 'native返回'+str(q.get('native_route_returncode'))+'，完成于'+html.escape(q['completed_utc'])
            context=('原生预路由DEF已核对514网、1540端点、全部770边成员及256条FIXED M10；DEF SHA256 <code>'+actual['DEF_SHA256']+'</code>' if actual else '尚未取得完整原生预路由DEF核对')
            upper_text+='<p><strong>预连上下文 '+html.escape(q['mode'])+'：</strong>'+context+'。路由状态：'+status+'。原R02底座仍未合格/未冻结、未升级新叶源；此核对只覆盖预路由连接成员和FIXED状态，尚非已布线几何或两完整功能。最终仍须全部770边实际连通、M10材料精确并集/FIXED属性、原hook/OBS、fresh DRC及后续RC/STA；无终态不报告布通或系统收益。</p>'
            if q.get('completed_utc'):
                geom=q.get('actual_all_net_geometry',{});diag=q.get('closed_native_guide_and_original_edge_diagnosis')
                upper_text+='<p><strong>该模式实际验收：</strong>fresh native DRC='+str(q.get('independent_DRC_count'))+'；所检连通='+str(geom.get('pass'))+'，已连通物理网='+str(geom.get('connected_nets'))+'/'+str(geom.get('checked_nets'))+'。M10原材料包含/FIXED保留与连通分别检查，不将native路由命令返回0当布通。</p>'
                if diag:
                    upper_text+='<p>闭合原生guide与实际端点分量核对：只有'+str(diag['native_nets_with_guides'])+'个物理网有guide，'+str(diag['fixed_shared_nets_without_guides'])+'个共享固定网没有guide；全部770原边中'+str(diag['original_edges_connected'])+'条物理连通、'+str(diag['original_edges_disconnected'])+'条断开。证据显示此流程跳过了已有FIXED片段的剩余连接，尚不等于安装二进制源码级根因。<a href="'+diag['detail_csv']+'">全部514网及770边验收CSV</a>。保留这次失败，再以只影响helper guide搜索的副本暂取下原FIXED片段、在DRT前按原生定义精确恢复的独立方案测试；不改变原底座、最终材料、PG/OBS、规则或完整验收。</p>'
    attempts=[]
    for mode in ['opentpu','llaccel']:
        p=snapshot/'upper_preconnected/r02'/mode/'execution.json.gz'
        if p.exists():attempts.append(dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
    if attempts:
        result['all770_guide_only_detach_restore_FIXED_before_DRT_r02']=attempts
        upper_text+='<p><strong>93120后续实际运行：</strong>在新目录以同一全部514网/770边/1540 hook生成guide，只在helper内存搜索副本暂取下256条既有FIXED片段，原下层文件不改；无论GRT成功或失败都先精确恢复原M10 FIXED，再保存检查点。若成功，必须确认全部514网均有实际guide才允许DRT，随后仍逐网检查真实连通、固定材料精确并集/FIXED、原hook/OBS与fresh DRC。只改变guide构造上下文，不改变规则、原层、拓扑或预连预算；未终态不称布通，更不是完整系统/冻结或RC/STA资格。</p>'
        for q in attempts:
            if q.get('completed_utc'):
                upper_text+='<p>93120 '+html.escape(q['mode'])+' 已终态：native返回'+str(q.get('native_route_returncode'))+'，完成于'+html.escape(q['completed_utc'])+'；失败原文和恢复后的实际FIXED检查点均保留，不把恢复固定线段当GRT/DRT通过。</p>'
    cugr=[]
    for mode in ['opentpu','llaccel']:
        p=snapshot/'upper_preconnected/r03'/mode/'execution.json.gz'
        if p.exists():cugr.append(dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
    if cugr:
        result['all770_CuGR_guides_restore_FIXED_before_DRT_r03']=cugr
        upper_text+='<p><strong>93129原生CuGR全量试验：</strong>依据已捕获安装版global_route的-use_cugr支持，在同一真实hook/拓扑/规则/临时guide副本恢复流程中换用CuGR；两模式均已取得全部514网的实际guide并在恢复原FIXED后进入DRT。该阶段突破不等于实际连通，原FastRoute失败不删。</p>'
        for q in cugr:
            g=q.get('actual_all_net_geometry',{})
            if q.get('completed_utc'):
                upper_text+='<p><strong>CuGR '+html.escape(q['mode'])+' 实际终态：</strong>native='+str(q.get('native_route_returncode'))+'、fresh native='+str(q.get('independent_DRC_count'))+'、连通='+str(g.get('pass'))+'（'+str(g.get('connected_nets'))+'/'+str(g.get('checked_nets'))+'物理网），原256 FIXED属性保持='+str(q.get('all256_native_FIXED_attributes_retained'))+'。即使guide完整，所检连接失败仍是失败；这进一步提示DRT对已有固定片段的剩余支路处理受限，尚不声称源码级根因或两完整系统。后续必须解决实际支路接入，不能把零/少量DRC或CuGR命令成功作为完成。</p>'
    tips=[]
    for rev in ['r01','r02']:
        p=snapshot/'llsys_actual_via_tips'/rev/'execution.json.gz'
        if p.exists():tips.append(dict(read(p),revision=rev,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
    if tips:
        result['LLSYSTEM_actual_three_pin_via_tip_attempts']=tips
        upper_text+='<p><strong>LL SYSTEM真实三pin/三网局部接线：</strong>针对已定位的四项原native报项，将bit_1382013(M5)、bit_6907(M6)、bit_1389626(M6)分别移到其真实原网既有via4/via5/via6落脚；原0.14×0.14μm尺寸/层/网络/方向/真实逻辑端点保持，删除八个明确原末端WIRE矩形，其余线与所有via定义/位置要求保持。完整13184个内部移动pin的C布局保留，不是少量内移伪装二维，也不重复92747的全pin-access失败路线。原目标父层未知项不指派。</p>'
        for q in tips:
            upper_text+='<p>via-tip '+q['revision']+'：native阶段返回='+html.escape(str(q.get('native_returncodes')))+'；完成时间='+html.escape(str(q.get('completed_utc')))+'。r01在容器读取原SDC时STA-0340提前失败，尚未改线；r02只补原issue55约束目录的只读映射，源SDC/时钟/负载/规则不改，随后实际三网编码接线及双PG检查已执行，RC/STA/独立fresh和完整13507-pin合同分别以终态回执为准。未终态不记DRC/全网连通或父层资格通过，不将原生编码器接线说成重新执行了GRT/DRT搜索。</p>'
    p=snapshot/'common_lower_resume/r01/execution.json.gz'
    if p.exists():
        q=read(p);result['actual_common_lower_CuGR_resume_r01']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        upper_text+='<p><strong>93132实际共同下层CuGR接续：</strong>从已原生审计的同一六资源/38基础设施/256 FIXED M10检查点接续，不重复布局或PDN；位置、pin/hook、实际旧R02叶视图、拓扑/预算、原signal M2–M10/clock M4–M10均保持，仅更换原生全局搜索器。原92855长期作业不取消或覆盖。新目录独立执行DRT、全部端点图/几何与双PG/fresh检查；仍未冻结、未执行该下层完整RC/STA、未实现两完整功能，原叶失败/真实GDS/规则覆盖缺项继续保留。具体native返回='+str(q.get('native_route_returncode'))+'，完成时间='+html.escape(str(q.get('completed_utc')))+'。</p>'
        if q.get('completed_utc'):
            upper_text+='<p>93132已取得终态失败：CuGR全局阶段已完成并保留带SHA的global.odb与原guide；DRT读取设计时DRT-0302：Unsupported multiple pins on bterm access_0001。原共享施工端口使用两个BPin容器，不能因此视为底层布通。保留该原生工具限制及失败，不删除原固定金属或把DRT未执行写成零项。</p>'
    p=snapshot/'common_lower_resume/r02/execution.json.gz'
    if p.exists():
        q=read(p);result['actual_common_lower_closed_guides_BPin_container_resume_r02']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        upper_text+='<p><strong>93149下层实际接续：</strong>复用93132已完成的原CuGR检查点/guide，不重复全局路由。只把256个共享<strong>施工</strong>BTerm的两个BPin容器合为一个容器内两块原矩形，原24767叶pin、两端0.8μm接点、原网络/FIXED导体、PG/OBS/位置均不改；逐项核对扁平pin几何/PG/实例保持。该表示修复尚不是冻结前全部施工端口降为固定几何，后者仍待完成。原DRT-0302保留，新DRT/全端点/双PG/fresh各自记录，尚未资格化。</p>'
        if q.get('completed_utc'):
            from collections import Counter
            before=p.parent/'before_BPin_container_fix.pins.tsv.gz';after=p.parent/'before_route.pins.tsv.gz'
            if before.exists() and after.exists():
                a=gzip.decompress(before.read_bytes());b=gzip.decompress(after.read_bytes())
                multiset=Counter(a.splitlines())==Counter(b.splitlines());assert multiset
                result['actual_common_lower_BPin_posthoc_exact_geometry_multiset']={'all10657_flat_pin_rows_exact_multiset_equal':multiset,
                  'rows_before':len(a.splitlines()),'rows_after':len(b.splitlines()),'byte_order_equal':a==b,
                  'scope':'Immutable native before/after rows; preserve original byte-order assertion failure, no physical rule waived'}
            upper_text+='<p><strong>93149实际FAILED保留：</strong>两个BPin容器问题已越过，DRT随后报DRT-0073：u_llaccel_aux/bit_1025无access point，未完成下层布线。原包装器又因pin行顺序变化触发字节哈希断言；后验逐行多重集复核10657行完全相同、无遗漏/重复，PG和实例字节本来相同，因此该断言不是几何移动的证据。原失败回执不改，真实NoAP仍是物理接入失败，不能据此说共同底座完成；后续须处理该pin的真实轨道/金属/PG/via条件。</p>'
    p=snapshot/'native_wire_append_api/r02/execution.json.gz'
    if p.exists():
        q=read(p);result['native_wire_opcode_append_API_r02']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('actual_rectangle_multisets_and_native_FIXED_ROUTED_path_flags_preserved'):
            upper_text+='<p><strong>93148原生wire合成API已核实：</strong>在同一安装工具中dbWire.append真实执行，原生重新导出的WIRE/VIA矩形多重集与源A+B完全相同，DEF中的FIXED/ROUTED属性同时保留，原输入SHA保持。这是小型工具API试验，不是接口路由或系统通过；r01包装器未设置Singularity PATH，在启动原生工具前FileNotFoundError，原失败日志保留，r02改用项目标准作业环境。</p>'
    composed=[]
    for mode in ['opentpu','llaccel']:
        p=snapshot/'upper_branch_composition/r01'/mode/'execution.json.gz'
        if p.exists():composed.append(dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
    if composed:
        result['all770_branch_route_then_exact_native_fixed_composition_r01']=composed
        upper_text+='<p><strong>93150两模式全770支路实际试验：</strong>为避免既有FIXED片段使原生路由跳过剩余连接，先在原770支路/1540真实hook的helper中完整CuGR/DRT，再通过已验证的原生opcode append合成514个物理网及同一256条实际原FIXED M10导体。原底座文件不改，所有支路矩形/通孔必须精确保留，最终逐一验证全部770原边、原hook/M10材料/OBS/FIXED及fresh DRC；另对全部256条真实固定桥作几何删除敏感性检查，区分实际必要的固定桥与冗余上层旁路。分析中的删桥不修改实际ODB。当前是实际运行的适配器流程，尚非两套完整加速器、合格冻结或有效系统RC/STA；提交本身不算通过。</p>'
        for q in composed:
            if q.get('completed_utc'):
                g=q.get('all_514_composed_geometry',{});upper_text+='<p>全支路合成 '+html.escape(q['mode'])+' 终态：原生阶段='+html.escape(str(q.get('native_returncodes')))+'，fresh='+str(q.get('fresh_DRC_count'))+'，最终几何连通='+str(g.get('pass'))+'；实际失败='+html.escape(str(q.get('actual_failure')))+'。所有门槛分别验收，不把原生0当完成。</p>'
                drcpath=snapshot/'upper_branch_composition/r01'/q['mode']/'independent.drc.gz'
                if drcpath.exists():
                    from collections import Counter
                    text=gzip.decompress(drcpath.read_bytes()).decode();kinds=dict(Counter(re.findall(r'^violation type: (.*)$',text,re.M)))
                    q['source_bound_independent_DRC_type_counts']=kinds
                    upper_text+='<p><strong>该结果仍失败：</strong>独立原生类型统计 '+html.escape(str(kinds))+'。本网连通和按本网删桥的256桥依赖不能排除跨网短路；存在Short时，不得称真实功能连接、电气隔离或完整固定预连复用已通过。原生实际支路/通孔矩形多重集与FIXED完整保留只证明合成未改变源材料，不能覆盖原路由本身的错误。</p>'
    repairs=[]
    for mode in ['opentpu','llaccel']:
        p=snapshot/'upper_branch_repair/r01'/mode/'execution.json.gz'
        if p.exists():repairs.append(dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
    if repairs:
        result['actual_native_selected_upper_branch_repair_r01']=repairs
        upper_text+='<p><strong>93166实际选择支路修复：</strong>从llaccel已完成的原770支路ODB和guide接续，按独立14项DRC中真实网络及源边对应选择支路，不重复GRT。保持原规则/层/所有hook，只做原生详细重接，再重验全部770本网连接、实际变化网清单、精确原生合成/256桥/FIXED材料及fresh DRC；不能假定只改被选择的网，也不能把子阶段返回0当完成。尚未闭合时保留旧14项（含6 Short）失败，完整底座/功能/系统RC/STA不提升。</p>'
        for q in repairs:
            if q.get('completed_utc'):
                p=snapshot/'upper_branch_repair/r01'/q['mode']/'independent.drc.gz';counts={}
                if p.exists():
                    from collections import Counter
                    counts=dict(Counter(re.findall(r'^violation type: (.*)$',gzip.decompress(p.read_bytes()).decode(),re.M)))
                q['source_bound_fresh_DRC_type_counts']=counts
                upper_text+='<p><strong>选择修复已终态：</strong>'+html.escape(q['mode'])+'选择'+str(q.get('selected_branch_count'))+'条原支路，实际WIRE/VIA表示改变'+str(len(q.get('actual_all770_branch_route_box_changed_native_net_names',[])))+'网；原生阶段='+html.escape(str(q.get('native_returncodes')))+'，fresh='+str(q.get('fresh_DRC_count'))+'，类型='+html.escape(str(counts))+'。必须以实际变化清单和完整重验为准；存在Short则仍失败，不能把本网连通或按本网删桥当全局隔离/功能通过。</p>'
    p=snapshot/'vector_clone_crash/r01/execution.json.gz'
    if p.exists():
        q=read(p);result['VECTOR_exact_native_crash_symbolization_r01']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        upper_text+='<p>93051是只读崩溃/API诊断，不附加、发信号或改变活动进程。原始addr2line结果与setup调用背景不一致，尚不能当根因；需要核对ELF加载基址与栈地址表示，完整原文/SHA保留，不把诊断程序return0当修复通过。</p>'
    p=snapshot/'pin_escape_views/r01/mxu-C/execution.json.gz'
    if p.exists():
        q=read(p);result['MXU_actual_M6_escape_physical_RC_views']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc') and q.get('native_export_returncode')==q.get('fresh_model_read_returncode')==0:
            r=next(r for r in rows if r['case']=='mxu');r['current_source_research_model']='SOURCE_BOUND_ACTUAL_RCX_REPLAY_VERIFIED_MINIMUM_PERIOD_MISSING'
            from plot_mxu_escape_context import plot
            result['MXU_actual_M6_escape_context']=plot(snapshot,out)
            upper_text+='<p><strong>93060 MXU新真实视图已导出：</strong>clean ODB/LEF/OBS/DEF/实际网表与非零提取Lib绑定新04e59990…源，2172信号pin/原PG/尺寸/层保持，SPEF setup/hold重放一致，模型独立重读通过；minimum_period仍缺失。M6 OBS仍延伸出原pin，两次pin–OBS几何交面积约0.0098μm²，不把叶native0当新父层可达。既有via5/M6接点来自真实网络，可作为后续XY研究区域，尚未迁移该pin。<a href="data/mxu_actual_M6_escape_context.json">实际OBS/接点与来源</a> · <a href="data/mxu_actual_escape_net_rectangles.csv">实际完整目标网矩形CSV</a>。</p><img loading="lazy" src="assets/mxu_actual_M6_escape_context.png"><p><a href="assets/mxu_actual_M6_escape_context.svg">M6实际重接与OBS SVG</a>。局部图同尺度；灰为实际占用OBS，红框仅属旧父层，本图采集时新父层未执行、后续93074结果另列；全网路径用实际原生矩形，没有虚构接入线。</p>'
    p=snapshot/'vector_clone_crash/r02/execution.json.gz'
    if p.exists():
        q=read(p);result['VECTOR_native_ELF_address_diagnosis_r02']=dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            upper_text+='<p><strong>93061 ELF地址诊断已完成，但根因未闭合：</strong>实际ELF最小LOAD基址0x200000，entry0x227f200；栈地址加该基址的末帧仍比entry早4054字节，未对齐_start，候选符号不能当准确故障定位。原/平移地址与完整输出分别保存；后续原guide/GRT上下文初始化只是独立能力试验，不称已找到或修复CloneMove根因。</p>'
    diagnosis=root/'vector_table_diagnosis_r03'
    if (diagnosis/'summary.json').exists():
        folder=data/'vector_Liberty_table_diagnosis';shutil.copytree(diagnosis,folder,dirs_exist_ok=True)
        q=read(folder/'summary.json');result['VECTOR_exact_Liberty_table_grid_diagnosis']=q
        incremental_text+='<p>VECTOR只读库表诊断：实际关键路径141段cell arc合计6.7401ns；FA_X1/HA_X1/OAI33_X1在当前同函数系列无更大驱动型号。逐arc表格最小值混合不同slew/负载/跳变/条件，不是可同时实现的STA，也不是零线延迟下界或不可行证明；原约束与物理输入未改变。<a href="data/vector_Liberty_table_diagnosis/arcs.csv">141段实际master/arc及库表CSV</a>。</p>'
    route_boxes=snapshot/'route_representation_audit/r01/execution.json.gz'
    if route_boxes.exists():
        q=read(route_boxes);result['actual_whole_net_routing_box_comparison']=dict(q,evidence=(dest/route_boxes.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('all_closed_source_geometry_and_receipts_unchanged'):
            incremental_text+='<p>92985按三份真实几何SHA检查全部268637条网：两换型阶段有15条网的WIRE/VIA矩形多重集表示不同；再增22个diode后为77条，其中22目标网、2条原636已保护网、53条其他网；其余268560条矩形表示完全一致。证明不能把增量DRT说成只重布22网。不同表示可能包含切段/重复差异，不直接等于几何并集、线长或RC变化；完整逐网digest表留授权远程存储并有SHA。</p>'
    final_gds=snapshot/'antenna_diode_stream/incremental-r01/gemm-C/execution.json.gz'
    if final_gds.exists():
        q=read(final_gds);result['GEMM_actual658_diode_strict_GDS_available_deck']=dict(q,evidence=(dest/final_gds.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            r=next(r for r in rows if r['case']=='gemm');r['available_deck_findings']=q.get('available_deck_findings')
            passed=q.get('merge_returncode')==q.get('DRC_returncode')==0 and q.get('available_deck_findings')==0
            r['complete_rules']='CURRENT_658_DIODE_AVAILABLE_DECK0_COVERAGE_INCOMPLETE' if passed else 'CURRENT_658_DIODE_GDS_OR_AVAILABLE_DECK_FAILED'
            incremental_text+='<p><strong>92976真实658diode版严格GDS已终态：</strong>merge='+str(q.get('merge_returncode'))+'，未改原deck return='+str(q.get('DRC_returncode'))+'，实际报项='+str(q.get('available_deck_findings'))+'。以实际源DEF/GDS/RDB SHA绑定，原1460和两个37项版本分别保留。该新版本原可用deck零项不代表完整制造规则、RTL形式、父层或系统资格；原WELL/via enclosure等覆盖缺口及其他块缺真实SRAM GDS不消失。</p>'
    upper_failed=snapshot/'upper_adaptation_trial/r01/preparation_failure.json.gz'
    if upper_failed.exists():
        q=read(upper_failed);result['upper_all770_preparation_r01_failed']=dict(q,evidence=(dest/upper_failed.relative_to(snapshot)).relative_to(out).as_posix())
        upper_text+='<p><strong>770-edge适配试验92969前置失败：</strong>尚未路由。原生Verilog将两个外部时钟alias规范化为opentpu__clk/llaccel__clk，与编译中间wire名字不同；输入检查拒绝而非忽略。原失败保留，后续只接受这两个经唯一TOP_IO组件证明的精确alias，不改变真实连接。92968在新目录复用已完成SYSTEM合法化检查点，按名称查找实例的恢复修复真实运行；作业提交不是通过。</p>'
    chain_resume=snapshot/'output_chain_resume/r01/opentpu_aux-C/execution.json.gz'
    if chain_resume.exists():
        q=read(chain_resume);result['SYSTEM_output_chain_resume']={'receipt':q,'full_qualification':False,
          'state':scheduler.get('92925',{}).get('State','UNKNOWN'),
          'evidence':(dest/chain_resume.relative_to(snapshot)).relative_to(out).as_posix()}
        if q.get('completed_utc') and q.get('route_stage_status',{}).get('preserve_contracts')=='FAIL':
            chain_resume_text='<p><strong>SYSTEM 92925已终态失败：</strong>真实GRT/DRT命令执行完成，但随后preserve_contracts在导出已移动buffer坐标时遇到空实例句柄（Empty command name）。这是恢复脚本将selected_buffers值保留为空造成的导出失败；已有原连接、非选中位置和pin/PG/外框文件仍需分别按SHA核查。没有保存最终routed ODB，fresh native、RCX/STA及最终物理合同尚未执行，空route.drc不是资格通过。原合法化检查点和全部失败保留；修复原生实例查找后在新目录复用检查点，不重新选择或移动buffer。</p>'
    resumed=snapshot/'output_chain_resume/r02/opentpu_aux-C/execution.json.gz'
    if resumed.exists():
        q=read(resumed);result['SYSTEM_existing_buffer_relocation_r02']=dict(q,evidence=(dest/resumed.relative_to(snapshot)).relative_to(out).as_posix())
        if q.get('completed_utc'):
            r=next(r for r in rows if r['case']=='opentpu_aux')
            r['historical_source_before_existing_buffer_relocation']={k:r[k] for k in ['completed_source','actual_internal_route','native_DRC_count','all_multiterminal_signal_clock_geometry','setup_ns','hold_ns','violation_marker_rows']}
            r.update({'completed_source':'existing_output_buffers/r02','actual_internal_route':'COMPLETED_NATIVE_DRC_AND_STA_FAILED',
              'native_DRC_count':q.get('fresh_DRC_count'),'all_multiterminal_signal_clock_geometry':q.get('whole_signal_geometry',{}).get('pass'),
              'setup_ns':q.get('setup_ns'),'hold_ns':q.get('hold_ns'),'violation_marker_rows':q.get('literal_VIOLATED_markers_not_complete_failure_count')})
            chain_resume_text+='<p><strong>SYSTEM92968已终态FAILED：</strong>复用合法化检查点并修复句柄导出后，完整route/RCX/原SDC已完成、466332网所检连通通过；fresh native仍2项，setup/hold −0.056303/−0.119814ns、1233文字违例。旧−0.462192/−0.125999ns、原native0及全部工具失败分别保留。原接口/PG/外框、原功能连接和非选中位置保持，现有输出buffer重排不是纯XY收益或时序闭合；旧r03研究模型不是这个新source的匹配视图。</p>'
    landing_text=''
    repairs=[]
    for case,revision in [('gemm','r01'),('mxu','r02')]:
        p=snapshot/'escape_landing'/revision/(case+'-C')/'execution.json.gz'
        if p.exists():
            q=read(p);repairs.append(dict(q,evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix()))
            if q.get('completed_utc'):
                landing_text+='<p>'+case+'父层落脚修订已终态：fresh native='+str(q.get('fresh_DRC_count'))+'，所检几何连通='+str(q.get('whole_signal_geometry',{}).get('pass'))+'，双PG='+str(q.get('both_power_grids_pass'))+'。只改一个新增父层M10点、原接口/PG保持；此夹具的旧叶源SHA='+str(q.get('source_leaf_ODB_SHA'))+'，不能代替当前658diode或成本叶的完整父层/RC/STA资格。</p>'
    result['latest_actual_parent_landing_repairs']=repairs
    from plot_actual_critical_paths import plot as plot_paths
    diagnosis=plot_paths(snapshot,out)
    if diagnosis:result['actual_critical_path_diagnosis']=diagnosis
    vector_proof=snapshot/'buffered_equivalence/r01/vector/execution.json.gz'
    if vector_proof.exists():
        q=read(vector_proof);result['VECTOR_directed_buffer_relation']=dict(q,evidence=(dest/vector_proof.relative_to(snapshot)).relative_to(out).as_posix())
        next(r for r in rows if r['case']=='vector')['whole_mapped_relative_digital_contract']=q.get('relative_mapped_digital_contract_pass',False)
    antenna=snapshot/'antenna_netmap/r02/execution.json.gz'
    if antenna.exists():result['actual_GDS_antenna_correlations']=dict(read(antenna),evidence=(dest/antenna.relative_to(snapshot)).relative_to(out).as_posix())
    from plot_mxu_region_ownership import plot as plot_ownership
    ownership=plot_ownership(snapshot,out);result['MXU_M6_bounded_ownership']=ownership
    ownership_image='<img src="assets/mxu_M6_actual_ownership.png" alt="MXU M6真实金属归属，保留抽象DRC失败" loading="lazy"><p><a href="assets/mxu_M6_actual_ownership.svg">M6实际金属SVG</a> · <a href="data/mxu_parent_region_ownership.json">原生矩形覆盖与未检查条件</a></p>' if ownership else ''
    from plot_actual_common_placement import plot as plot_placement
    placement=plot_placement(root,snapshot,out);result['actual_six_resource_placement']=placement
    if placement and trial_receipt is None:result['actual_common_integration_trial']['status']='ACTUAL_RESOURCE_PLACEMENT_EXPORTED; PDN_OR_FOLLOWING_STAGE_RUNNING'
    if (snapshot/'common_integration/r01/C/before.shared.tsv.gz').exists() and trial_receipt is None:result['actual_common_integration_trial']['status']='FIXED_M10_CONDUCTORS_WRITTEN; LOWER_ROUTE_OR_CHECKS_RUNNING'
    placement_image='<img src="assets/common_placement_actual.png" alt="六资源原生实际放置，非冻结或已完成共享布线" loading="lazy"><p><a href="assets/common_placement_actual.svg">原生实际放置SVG</a>。未显示内部金属，浅灰背景不是空白接入许可。</p>' if placement else ''
    fixed_audit=snapshot/'shared_conductor_audit/r02/execution.json.gz'
    if fixed_audit.exists():result['actual_fixed256_native_attribute_audit']=dict(read(fixed_audit),evidence=(dest/fixed_audit.relative_to(snapshot)).relative_to(out).as_posix())
    from plot_actual_shared_conductors import plot as plot_fixed
    fixed=plot_fixed(root,snapshot,out);result['actual_shared_conductor_geometry']=fixed
    fixed_image='<figure><img src="assets/common_shared_conductors_actual.png" loading="lazy" alt="256条原生FIXED M10导体与真实接点，非冻结或两模式完成"><figcaption><a href="assets/common_shared_conductors_actual.svg">实际导体SVG</a> · <a href="data/common_shared_conductors_actual.csv">全部256条native坐标CSV</a> · <a href="data/common_shared_conductors_actual.json">来源与边界</a>。固定属性/几何已核验，底层完整布线和两模式复用尚未验证。</figcaption></figure>' if fixed else ''
    from plot_actual_diode_access import plot as plot_diodes
    diode_figure=plot_diodes(snapshot,out)
    if diode_figure:
        result['actual_22_diode_access_figure']=diode_figure
        incremental_text+='<figure><img src="assets/gemm_real_diode_access.png" loading="lazy" alt="原GDS37个真实bbox与22个实际新增diode位置，非新版本天线通过"><figcaption><a href="assets/gemm_real_diode_access.svg">真实diode接入SVG</a> · <a href="data/gemm_real_diode_access.json">实际来源及局部receiver</a>。总览符号为定位标记，局部为真实LEF placement bbox；非pin/via/GDS轮廓。</figcaption></figure>'
    # Promote sources after all chronological predecessor updates.
    q=result.get('SYSTEM_native_clean_patches_r02_attempt',{})
    if q.get('completed_utc') and q.get('native_returncodes',{}).get('fresh_DRC')==0 and q.get('whole_signal_geometry',{}).get('pass') and all(q.get('all_cells_poses_original_connections_pins_PG_die_unchanged',{}).values()):
        r=next(r for r in rows if r['case']=='opentpu_aux');r['historical_source_before_clean_patches']=json.loads(json.dumps(r))
        r.update({'completed_source':'native_clean_patches/r02','actual_internal_route':'COMPLETED_ROUTE_PATCH_VARIANT_NATIVE_AND_STA_FAILED',
          'native_DRC_count':q.get('fresh_DRC_count'),'all_multiterminal_signal_clock_geometry':True,'setup_ns':q.get('setup_ns'),'hold_ns':q.get('hold_ns'),
          'violation_marker_rows':q.get('literal_VIOLATED_markers_not_complete_failure_count'),
          'complete_rules':'CURRENT_CLEAN_PATCHES_GDS_NOT_EXECUTED_MISSING_REAL_SRAM_AND_COVERAGE_GAPS',
          'parent_access':'CURRENT_CLEAN_PATCHES_SOURCE_NOT_VALIDATED_IN_PARENT','current_source_research_model':'NOT_EXPORTED',
          'common_base_source_selection':'ORIGINAL_R02_NOT_UPGRADED_TO_THIS_SOURCE'})
    q=result.get('MXU_actual_view_parent_recheck_r01',{})
    if q:
        r=next(r for r in rows if r['case']=='mxu');r['current_source_parent_access_recheck']=q
        if q.get('completed_utc'):
            r['parent_access']='CURRENT_M6_ACTUAL_VIEW_COMPLETE_PARENT_RECHECK_NATIVE_'+str(q.get('fresh_DRC_count','UNKNOWN'))+'_NOT_SYSTEM_RC_STA'
            if not q.get('all_original_macro_pin_rectangles_net_directions_layers_in_parent_exactly_unchanged'):
                from collections import Counter
                import io
                folder=snapshot/'escape_view_recheck/r01/mxu-C'
                def term_rows(name):return list(csv.DictReader(io.StringIO(gzip.decompress((folder/name).read_bytes()).decode()),delimiter='\t'))
                a=term_rows('before.child_terms.tsv.gz');b=term_rows('after.child_terms.tsv.gz')
                without_use=lambda xs:Counter(tuple(sorted((k,v) for k,v in x.items() if k!='use')) for x in xs)
                assert without_use(a)==without_use(b)
                ca=Counter(tuple(sorted(x.items())) for x in a);cb=Counter(tuple(sorted(x.items())) for x in b)
                before=list((ca-cb).elements());after=list((cb-ca).elements());assert len(before)==len(after)==1
                before,after=dict(before[0]),dict(after[0]);assert before['pin']==after['pin']=='clk' and before['use']=='CLOCK' and after['use']=='SIGNAL'
                result['MXU_current_actual_view_clock_USE_regression']={'status':'FAILED_CLOCK_USE_CONTRACT',
                  'original':before,'after_actual_view_swap':after,'all_geometry_layers_directions_networks_other_than_USE_exactly_equal':True,
                  'original_native_receipt_false_preserved':True,'requires_source_bound_native_view_metadata_repair':True,'full_qualification':False}
                r['parent_access']+='_CLOCK_USE_CONTRACT_FAILED'
                upper_text+='<p><strong>MXU父层接口合同另有真实失败：</strong>原生before/after全部2245条宏pin矩形记录比较发现，clk的USE从CLOCK变为SIGNAL；坐标/M6/尺寸、方向和网络一致，其余记录不变。旧回执的接口不变检查False保留，不能只看native进程0或native1就省略该回归。必须从真实RTL/SDC时钟合同修正原生物理视图及模型并重新核验，不只改最终LEF或把CLOCK检查删掉；当前新视图父层仍未通过。</p>'
    q=result.get('SYSTEM_actual_stacked_via_r01',{})
    if q.get('completed_utc') and q.get('native_returncodes',{}).get('detailed_edit_and_analysis')==0 and q.get('whole_signal_geometry',{}).get('pass') and all(q.get('original_cells_poses_signal_connections_pins_PG_die_unchanged',{}).values()) and q.get('all_other_exported_multiterminal_route_box_multisets_identical'):
        r=next(r for r in rows if r['case']=='opentpu_aux');r['historical_source_before_stacked_via']=json.loads(json.dumps(r))
        r.update({'completed_source':'native_stacked_via/r01','actual_internal_route':'ACTUAL_STACKED_VIA_ROUTE_CHECKS_SEPARATE',
          'native_DRC_count':q.get('fresh_DRC_count'),'all_multiterminal_signal_clock_geometry':True,
          'setup_ns':q.get('setup_ns'),'hold_ns':q.get('hold_ns'),'violation_marker_rows':q.get('literal_VIOLATED_markers_not_complete_failure_count'),
          'complete_rules':'CURRENT_STACKED_VIA_GDS_NOT_EXECUTED_COVERAGE_GAPS','parent_access':'CURRENT_STACKED_VIA_SOURCE_NOT_VALIDATED_IN_PARENT',
          'current_source_research_model':'NOT_EXPORTED','common_base_source_selection':'ORIGINAL_R02_NOT_UPGRADED_TO_THIS_SOURCE'})
    q=result.get('SYSTEM_actual_stacked_via_physical_RC_views',{})
    if q.get('completed_utc') and q.get('native_export_returncode')==q.get('fresh_model_read_returncode')==0 and q.get('all_sources_and_pre_RCX_geometry_unchanged'):
        r=next(r for r in rows if r['case']=='opentpu_aux');r['current_source_research_model']='SOURCE_BOUND_ACTUAL_RCX_REPLAY_VERIFIED_MINIMUM_PERIOD_MISSING'
        r['current_source_extended_STA_audit']=q.get('current_exact_source_extended_STA')
    for q in result.get('LLSYSTEM_actual_three_pin_via_tip_attempts',[]):
        if not (q.get('completed_utc') and q.get('fresh_DRC_count')==0 and q.get('whole_signal_geometry',{}).get('pass') and q.get('complete_pin_contract',{}).get('all_signal_pins')==13507 and q.get('all_other_725250_multiterminal_route_box_multisets_identical') and q.get('exactly_eight_actual_WIRE_rectangles_removed_no_added_wire_or_via_material') and q.get('all_actual_target_via_rectangle_multisets_preserved') and all(q.get('all_cells_signal_connections_PG_die_unchanged',{}).values()) and q.get('all_closed_sources_unchanged')):continue
        r=next(r for r in rows if r['case']=='llaccel_aux');r['historical_source_before_actual_via_tips']=json.loads(json.dumps(r))
        r.update({'completed_source':'actual_via_tips/'+q['revision'],'actual_internal_route':'ACTUAL_THREE_PIN_VIA_TIP_ROUTE_NATIVE0_STA_FAILED',
          'native_DRC_count':0,'all_multiterminal_signal_clock_geometry':True,'power_grid':'NATIVE_VDD_VSS_COMMANDS_EXECUTED',
          'setup_ns':q.get('setup_ns'),'hold_ns':q.get('hold_ns'),'violation_marker_rows':q.get('literal_VIOLATED_markers_not_complete_failure_count'),
          'complete_rules':'CURRENT_VIA_TIP_GDS_NOT_EXECUTED_COMPLETE_COVERAGE_GAPS',
          'parent_access':'NEW_VIA_TIP_SOURCE_NOT_VALIDATED_IN_PARENT_OLD_R02_NoAP_bit_1025_RETAINED',
          'current_source_research_model':'NOT_EXPORTED','common_base_source_selection':'ORIGINAL_R02_NOT_UPGRADED_TO_THIS_SOURCE',
          'current_complete_pin_contract':q['complete_pin_contract']})
        r['evidence'].append(q['evidence'])
        upper_text+='<p><strong>LL SYSTEM三pin真实修复已闭合：</strong>native编辑/RCX/STA与fresh进程均0，fresh native由4降0；725253网/2325528端点/28517815形状所检连通、双PG、完整13507-pin层/尺寸/网络/方向与PG合同通过。恰好只删除八个WIRE矩形、所有via原样；其余725250条多端网矩形多重集相同，单端未用网/真实GDS仍不在该比较范围。0新单元/换型，原功能实例/位置/连接/PG/外框不变。setup/hold仍−3.909029/−0.587515ns、8876文字VIOLATED，整体FAILED。主矩阵选此native0新源，旧native4/旧窗口作业失败保留；新匹配抽象/RC模型及父层接入仍待完成，不能继承旧父层或称六块完整物理资格通过。<a href="data/llsys_actual_via_tips_r02_all_13507_pins.csv">完整13507个实际pin逐项前后对应CSV</a>。</p>'
    for label,rel in [('ALL24767_actual_parent_track_geometry','parent_noap_grid_audit/r01'),
                      ('LLSYSTEM_actual_NoAP_local_metals_PG_OBS','llsys_noap_context/r01'),
                      ('MXU_native_clock_Liberty_binding_probe','clock_view_binding_probe/r01'),
                      ('LLSYSTEM_current_actual_tip_views','llsys_actual_tip_views/r01/llaccel_aux-C'),
                      ('UPPER_guard_API_r01','upper_guard_api/r01'),
                      ('UPPER_guard_API_r02','upper_guard_api/r02'),
                      ('UPPER_guard_API_r03','upper_guard_api/r03'),
                      ('MXU_actual_tip_ECO_r01','mxu_actual_via_tip/r01'),
                      ('MXU_actual_tip_original_range_fresh_r01','mxu_actual_tip_fresh/r01'),
                      ('MXU_actual_tip_views_r01','mxu_actual_tip_views/r01/mxu-C'),
                      ('LLSYSTEM_bit1025_actual_tip_ECO_r01','llsys_parent_access_tip/r01'),
                      ('MXU_clock_bound_parent_recheck_r02','escape_view_recheck/r02/mxu-C'),
                      ('MXU_clock_bound_parent_recheck_r03','escape_view_recheck/r03/mxu-C')]:
        p=snapshot/rel/'execution.json.gz'
        terminal_names={'LLSYSTEM_current_actual_tip_views':'llsys-tip-views-r01',
                        'MXU_clock_bound_parent_recheck_r03':'mxu-clock-bound-parent-r03',
                        'MXU_actual_tip_ECO_r01':'mxu-actual-via-tip-r01',
                        'MXU_actual_tip_original_range_fresh_r01':'mxu-actual-tip-fresh-r01',
                        'MXU_actual_tip_views_r01':'mxu-actual-tip-views-r01',
                        'LLSYSTEM_bit1025_actual_tip_ECO_r01':'llsys-parent-access-tip-r01',
                        **{'UPPER_guard_API_r0'+str(i):'upper-guard-api-r0'+str(i) for i in [1,2,3]}}
        update=root/'gate_terminal_updates'/terminal_names.get(label,'NO_TERMINAL_UPDATE')
        terminal_evidence=None
        if update.exists():
            capture=read(update/'capture.json');assert not capture['full_qualification']
            for record in capture['records']:
                stored=(update/(record['name']+'.gz')).read_bytes();raw=gzip.decompress(stored)
                assert hashlib.sha256(stored).hexdigest()==record['stored_sha256'] and hashlib.sha256(raw).hexdigest()==record['sha256'] and len(raw)==record['bytes']
            terminal_dest=out/'data/gate_terminal_updates'/update.name;shutil.copytree(update,terminal_dest,dirs_exist_ok=True)
            p=terminal_dest/'execution.json.gz';terminal_evidence=p.relative_to(out).as_posix()
        if not p.exists():continue
        q=read(p);e=terminal_evidence or (dest/p.relative_to(snapshot)).relative_to(out).as_posix();result[label]=dict(q,evidence=e)
        upper_text+='<p><strong>'+label+'</strong>：'+('已收齐终态' if q.get('completed_utc') else '快照时仍执行中，不能当完成')+'。<a href="'+e+'">源SHA、原生返回及完整原文回执</a>；完整资格仍未完成。</p>'
        if label=='ALL24767_actual_parent_track_geometry' and q.get('completed_utc'):
            upper_text+='<p>真实原R02六块父层24767pin逐项轨道审计：其余五块preferred中心未对齐数0，LL SYSTEM为13184；宏原点均已对齐实际pitch。bit_1025的M5 preferred中心偏移0.07μm；原网535条实际矩形/端点已取得，未编造端点。仅为几何风险，未对齐不等于无AP，仍须真实局部PG/OBS/via及父层接入检查。</p><p><a href="'+(dest/rel/'all24767_actual_parent_pin_track_geometry.csv.gz').relative_to(out).as_posix()+'">全部24767父层信号pin逐项轨道CSV</a></p>'
        if label=='MXU_native_clock_Liberty_binding_probe' and q.get('native_probe_returncode')==0:
            upper_text+='<p>原生小探针真实记录：read_LEF后MTerm为SIGNAL，加载同源Liberty后变CLOCK，link及原2.5ns create_clock后保持CLOCK；旧/新源LEF均USE SIGNAL、Liberty均clock:true。这里只证明工具绑定阶段行为，不证明整父层修复；未手改USE或更改时钟。</p>'
        if label=='UPPER_guard_API_r03' and q.get('completed_utc'):
            upper_text+='<p>适配器原生NDR接口探针：返回'+str(q.get('native_probe_returncode'))+'，不是实际路由或DRC通过。r01的getLayerRules输出参数调用错误保留；r02正确读回M11/M12的0.8μm线宽/1.5μm间距并给全部770原网赋规则，但未指定的M1–M10 NDR spacing实际为0，未采用。r03显式给适配网全部12层NDR设置1.5μm hard spacing，实际仍只允许M11/M12路由、原下层材料不动；12层读回及全部770赋值通过。该额外保守约束及其成本与原profile分列，不是技术规则放宽、原pin升层、完整功能或制造签核。后续布线会同时执行带NDR和去除NDR元数据副本上的原技术规则独立fresh检查。</p><p><a href="https://openroad.readthedocs.io/en/latest/main/src/odb/README.html#create-ndr">OpenROAD官方NDR文档</a>；实际安装版本行为及Tcl body见原生log。</p>'
        if label=='LLSYSTEM_current_actual_tip_views' and q.get('completed_utc'):
            assert q['native_export_returncode']==q['fresh_model_read_returncode']==0 and q['matching_all_signal_model_pins']==13507
            assert q['SPEF_replay_matches_source'] and q['all_sources_and_pre_RCX_geometry_unchanged'] and q['all_13507_current_pins_and_PG_match_actual_after_edit']
            source=read(snapshot/'llsys_actual_via_tips/r02/execution.json.gz')
            assert q['source_geometry_sha256']==source['files']['routed.odb']['sha256']
            r=next(r for r in rows if r['case']=='llaccel_aux');r['current_source_research_model']='SOURCE_BOUND_ACTUAL_RCX_REPLAY_VERIFIED_MINIMUM_PERIOD_MISSING'
            upper_text=upper_text.replace('新匹配抽象/RC模型及父层接入仍待完成','新匹配抽象/RC模型已由93190闭合，父层接入仍待完成')
            upper_text+='<p><strong>93190当前LL源匹配视图已完成：</strong>原生默认/详细OBS抽象、DEF/网表及非零真实RC时序模型导出，独立模型重读0；13507信号位及全部原PG/层/尺寸/当前实际XY精确匹配，clean ODB与真实源SHA相同。原SPEF余量逐字重放−3.909029/−0.587515ns，仍失败；minimum_period规则缺项、父层/完整规则/功能资格未通过。此闭合回执独立追加，未改写R38快照时仍运行的记录。</p>'
        if label=='LLSYSTEM_bit1025_actual_tip_ECO_r01' and q.get('completed_utc'):
            assert q['native_returncodes']=={'actual_edit_and_analysis':0,'fresh_DRC':0} and q['fresh_DRC_count']==0 and q['all_closed_sources_unchanged']
            assert q['complete_pin_contract']['all_signal_pins']==13507 and q['complete_pin_contract']['only_changed_XY_pins']==['bit_1025']
            r=next(r for r in rows if r['case']=='llaccel_aux');r['newer_actual_bit1025_ECO']={'evidence':e,'native_DRC_count':0,'matching_new_views':'NOT_YET_EXPORTED','parent_access':'NOT_VERIFIED','full_qualification':False}
            upper_text=upper_text.replace('93190当前LL源匹配视图已完成','93190此前三点源匹配视图已完成（最新bit1025变体另列）')
            upper_text+='<p><strong>93205 LL bit_1025真实重接已收齐终态：</strong>仅此M5 pin接到原网既有via5帽、删除3条原末端WIRE；原先三点修复及完整13184-move内部C保留，全部13507位接口/原层/尺寸/功能/网络、单元/PG/外框保持。725253多端网所检几何连通、双PG/RCX/原STA执行，native与fresh进程0/fresh0，其余725252多端网矩形表示及全部via保持。setup/hold仍−3.909029/−0.587515ns、8876文字VIOLATED，整体FAILED。原共同下层bit1025无AP不能据此宣布解决；新匹配视图和真实父层待完成，不继承前三点源模型；主矩阵仍明确列此前匹配视图源，此新实际变体单独记录。</p><p><a href="data/gate_terminal_updates/llsys-parent-access-tip-r01/all_13507_actual_pin_correspondence.csv.gz">本变体全部13507实际pin对应CSV</a></p>'
        if label.startswith('MXU_clock_bound_parent_recheck_') and q.get('completed_utc'):
            upper_text+='<p>实际整父层返回'+str(q.get('native_returncodes'))+'；fresh='+str(q.get('fresh_DRC_count'))+'，完整2245条宏pin/网络/方向/层/USE合同='+str(q.get('all_original_macro_pin_rectangles_net_directions_layers_in_parent_exactly_unchanged'))+'。r02在native swapMaster发生Signal11，失败保留；r03改为先swap后绑定同一真实库，结果以该回执为准，不能以小探针代替。</p>'
    mxu_tip=result.get('MXU_actual_tip_ECO_r01',{});mxu_fresh=result.get('MXU_actual_tip_original_range_fresh_r01',{});mxu_view=result.get('MXU_actual_tip_views_r01',{})
    if all(q.get('completed_utc') for q in [mxu_tip,mxu_fresh,mxu_view]):
        assert mxu_tip['native_returncodes']=={'actual_edit_and_analysis':0,'fresh_DRC':1}
        assert mxu_fresh['native_fresh_returncode']==mxu_fresh['fresh_DRC_count']==0 and mxu_fresh['all_closed_sources_unchanged']
        assert mxu_fresh['source_actual_ECO_ODB_SHA256']==mxu_tip['files']['routed.odb']['sha256']==mxu_view['source_geometry_sha256']
        assert mxu_fresh['source_actual_ECO_SPEF_SHA256']==mxu_tip['files']['extracted.spef']['sha256']==mxu_view['source_SPEF_sha256']
        assert mxu_tip['whole_signal_geometry']['pass'] and mxu_tip['all_other_191437_multiterminal_route_box_multisets_identical'] and mxu_tip['exactly_four_actual_M6_WIRE_rectangles_removed_all_vias_unchanged']
        assert mxu_tip['complete_pin_contract']['all_signal_pins']==2172 and mxu_tip['complete_pin_contract']['only_changed_XY_pins']==['act_data[12]']
        assert mxu_tip['all_closed_sources_unchanged'] and all(mxu_tip['all_cells_signal_connections_PG_die_unchanged'].values())
        assert mxu_view['matching_all_signal_model_pins']==2172 and mxu_view['all_sources_and_pre_RCX_geometry_unchanged'] and mxu_view['all_2172_current_pins_and_PG_match_actual_after_edit'] and mxu_view['SPEF_replay_matches_source']
        r=next(r for r in rows if r['case']=='mxu');r['historical_source_before_actual_via_tip']=json.loads(json.dumps(r))
        r.update({'completed_source':'actual_M6_via_tip/r01+original_range_fresh/r01','actual_internal_route':'ACTUAL_ONE_M6_TIP_ROUTE_NATIVE0_STA_POSITIVE',
          'native_DRC_count':0,'all_multiterminal_signal_clock_geometry':True,'power_grid':'NATIVE_VDD_VSS_COMMANDS_EXECUTED',
          'setup_ns':mxu_tip['setup_ns'],'hold_ns':mxu_tip['hold_ns'],'violation_marker_rows':mxu_tip['literal_VIOLATED_markers_not_complete_failure_count'],
          'complete_rules':'CURRENT_ACTUAL_TIP_GDS_NOT_EXECUTED_REAL_SRAM_COVERAGE_GAPS',
          'parent_access':'NEW_ACTUAL_TIP_SOURCE_NOT_VALIDATED_IN_PARENT_OLD_SOURCE_FAILURES_RETAINED',
          'current_source_research_model':'SOURCE_BOUND_ACTUAL_RCX_REPLAY_VERIFIED_MINIMUM_PERIOD_MISSING',
          'common_base_source_selection':'ORIGINAL_R02_NOT_UPGRADED_TO_THIS_SOURCE','current_complete_pin_contract':mxu_tip['complete_pin_contract']})
        from plot_mxu_actual_via_tip import plot as plot_mxu_tip
        result['MXU_actual_via_tip_figure']=plot_mxu_tip(snapshot,out/'data/gate_terminal_updates',out)
        upper_text+='<h3>MXU：M6实际pin/via落脚重接及原范围独立检查已闭合</h3><p>仅act_data[12] XY由(328.255,1068.870)移到原网via5的M6帽(328.535,1088.710)μm，原M6/0.14μm正方形/网络/方向/功能保持；删除4条实际末端M6 WIRE，全部via及其余191437多端网矩形表示不变，0新单元/换型，继承原1次换型成本。全2172信号pin/PG/单元/连接/外框合同、全网所检连通、双PG、RCX/原STA已完成，setup/hold仍0.246690/0.038538ns，不声称系统收益。</p><p>首次fresh驱动误用M2–M8，DRT-0155拒绝源已有M9 guide，没有实际DRC结果；原失败原样保留。93223只复用同一闭合实际ODB/SPEF，按原源fresh.tcl逐SHA/文本核实的M2–M10信号、M4–M10时钟范围独立检查，native0/fresh0，未重做接线/提取或放宽原源规则。93228当前源匹配默认/详细OBS、真实网表与RC模型已完成，2172信号及PG/当前XY/尺寸匹配、原SPEF余量逐字重放，minimum_period规则仍缺项。</p><p><strong>新位置不是已验证的父层空闲点：</strong>M6详细OBS仍有真实同网via帽矩形与整个0.14μm pin重合（0.0196μm²），没有剪去占用；它对实际父层接入的影响仍待原生布线和分层规则核验。旧父层native1/时钟标签失败不继承为新源通过；完整GDS/SRAM/规则/RTL/共同冻结未完成。</p><img src="assets/mxu_actual_via_tip_repair.png" alt="MXU真实M6单pin接线前后与局部放大"><p><a href="assets/mxu_actual_via_tip_repair.svg">SVG</a> · <a href="data/mxu_actual_via_tip_repair.json">真实来源/坐标/范围</a> · <a href="data/gate_terminal_updates/mxu-actual-via-tip-r01/all_2172_actual_pin_correspondence.csv.gz">完整2172个实际pin逐项对应CSV</a></p>'
    target=data/'qualification_matrix.json';target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    columns=['case','block','original_signal_pins','partition_and_all_interfaces','candidate_ABC','completed_source','actual_internal_route',
             'native_DRC_count','all_multiterminal_signal_clock_geometry','power_grid','setup_ns','hold_ns','violation_marker_rows',
             'complete_rules','historical_parent_target_layers','mapped_design_formal_equivalence','RTL_system_formal_equivalence','parent_access','full_qualification']
    with (data/'qualification_matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');w.writeheader();w.writerows({k:r[k] for k in columns} for r in rows)
    labels={'ACTUAL_ONE_M6_TIP_ROUTE_NATIVE0_STA_POSITIVE':'实际M6单pin重接/native0','CURRENT_ACTUAL_TIP_GDS_NOT_EXECUTED_REAL_SRAM_COVERAGE_GAPS':'新源GDS未验/缺SRAM及覆盖',
      'COMPLETED':'已完成布线；非完整签核','COMPLETED_COSTED_ECO_NOT_PURE_XY':'成本ECO已布线',
      'actual_via_tips/r02':'实际via落脚pin修复/r02','ACTUAL_THREE_PIN_VIA_TIP_ROUTE_NATIVE0_STA_FAILED':'实际3pin重接/native0/STA失败',
      'CURRENT_VIA_TIP_GDS_NOT_EXECUTED_COMPLETE_COVERAGE_GAPS':'新源GDS未验/完整覆盖缺口',
      'native_stacked_via/r01':'实际via叠放/r01','ACTUAL_STACKED_VIA_ROUTE_CHECKS_SEPARATE':'实际接线；检查分列',
      'CURRENT_STACKED_VIA_GDS_NOT_EXECUTED_COVERAGE_GAPS':'新源GDS未验/覆盖缺口',
      'COMPLETED_BUT_NATIVE_DRC_FAILED':'已布线；native失败','NOT_TERMINAL':'尚未终态',
      'NATIVE_VDD_VSS_COMMANDS_EXECUTED':'双PG原生命令执行','NOT_YET_READ_FROM_STAGE_RECEIPT':'PG回执待核',
      'NOT_PASSED_OR_INCOMPLETE_COVERAGE':'未通过/规则覆盖不全','GDS_MERGED_DECK_NOT_TERMINAL':'GDS合并通过；deck未终态',
      'FAILED_STRICT_GDS_MISSING_CELLS; partial-deck results diagnostic only':'缺宏GDS；全设计失败',
      'AVAILABLE_DECK_HAS_FINDINGS':'原deck仍有错误项','AVAILABLE_DECK_0_COVERAGE_STILL_INCOMPLETE':'原deck零项；完整覆盖未闭合',
      'COMPLETED_REAL_DIODE_AND_TWO_SIZE_ECO_NOT_PURE_XY':'真实diode/换型已布线',
      'costed_real_diode_and_sizes/r01':'diode+两换型/r01',
      'CURRENT_GDS_PENDING; PRIOR_REAL_DIODE_GDS37_FAILED; COVERAGE_INCOMPLETE':'当前GDS待验；旧37失败/覆盖不全',
      'CURRENT_REAL_DIODE_SIZE_GDS37_FAILED; COVERAGE_INCOMPLETE':'当前GDS37失败/覆盖不全',
      '658_real_diodes/r01':'658diode/r01','COMPLETED_INCREMENTAL_REAL_DIODE_ECO_NOT_PURE_XY':'增量22diode已布线',
      'CURRENT_658_DIODE_GDS_PENDING; COVERAGE_INCOMPLETE':'658版GDS待验/覆盖不全',
      'CURRENT_658_DIODE_AVAILABLE_DECK0_COVERAGE_INCOMPLETE':'原可用GDS deck零项/覆盖不全',
      'CURRENT_658_DIODE_GDS_OR_AVAILABLE_DECK_FAILED':'当前严格GDS/deck失败',
      'existing_output_buffers/r02':'原输出buffer重排/r02','COMPLETED_NATIVE_DRC_AND_STA_FAILED':'已布线；native/STA失败',
      'M6_escape_route/r02':'M6实际引出重接/r02','COMPLETED_M6_ACCESS_REROUTE_ORIGINAL_PIN_XY_UNCHANGED':'实际重接/原pin不变',
      'CURRENT_M6_ESCAPE_GDS_NOT_EXECUTED_MISSING_REAL_SRAM_AND_COVERAGE_GAPS':'新源GDS未验/缺SRAM及覆盖缺口',
      'native_clean_patches/r02':'native路由patch/r02','COMPLETED_ROUTE_PATCH_VARIANT_STA_CHECK_SEPARATE':'实际patch重接/STA另验',
      'COMPLETED_ROUTE_PATCH_VARIANT_NATIVE_AND_STA_FAILED':'已重接/native及STA失败',
      'CURRENT_CLEAN_PATCHES_GDS_NOT_EXECUTED_MISSING_REAL_SRAM_AND_COVERAGE_GAPS':'新源GDS未验/缺SRAM及覆盖缺口',
      'RUNNING_OR_RECEIPT_NOT_TERMINAL':'运行中/未收齐终态'}
    def show(value):
        if value is None:return '未知/待验证'
        if value is True:return '所检范围通过'
        if value is False:return '否/未通过'
        return html.escape(labels.get(str(value),str(value)))
    table=''.join('<tr>'+''.join('<td>'+show(v)+'</td>' for v in [r['block'],r['original_signal_pins'],r['completed_source'],r['actual_internal_route'],r['native_DRC_count'],r['all_multiterminal_signal_clock_geometry'],r['power_grid'],str(r['setup_ns'])+' / '+str(r['hold_ns']),r['complete_rules']])+'</tr>' for r in rows)
    stream=''.join('<tr>'+''.join('<td>'+('已执行（非通过）' if k=='deck_executed' and r[k] is True else show(r[k]))+'</td>' for k in ['block','strict_merge_errors','missing_GDS_cells','deck_executed','deck_findings','stage_outcome'])+'</tr>' for r in stream_rows)
    parents=''.join('<tr>'+''.join('<td>'+show(r[k])+'</td>' for k in ['version','route_returncode','native_DRC','signal_geometry','signal_nets_checked','both_PG_native_log_connected'])+'</tr>' for r in parent_rows)
    boundary=''.join('<tr>'+''.join('<td>'+show(v)+'</td>' for v in [r['case'],len(r['targeted_master_changes']),r['native_DRC'],r['whole_signal_geometry'],r['setup_ns'],r['hold_ns']])+'</tr>' for r in controls)
    route_table=''.join('<tr>'+''.join('<td>'+show(v)+'</td>' for v in [r['case']+' '+r['variant'],r['DRT_reported_wire_length_um'],r['DRT_reported_vias'],format(r['wire_change_vs_same_ECO_Aopt_percent'],'+.3f')+'%',format(r['via_change_vs_same_ECO_Aopt_percent'],'+.3f')+'%'])+'</tr>' for r in actual_routes)
    return '''<section class="card" id="latest-physical-gates"><h2>最新六块验证矩阵与GDS导入修复（优先于历史快照）</h2>
<div class="warn">本节按已收齐的具体版本区分已完成、失败、运行中、未执行和未知；native0、Slurm0或候选完整均不提升为全部物理完成。全部6块完整设计形式等价/系统RTL等价均尚未执行，历史逐pin目标金属层仍部分未知。</div>
<p><a href="data/qualification_matrix.json">机器可核查矩阵JSON（含来源/父层/功能/新尝试）</a> · <a href="data/qualification_matrix.csv">CSV</a> · <a href="'''+dest.relative_to(out).as_posix()+'''/snapshot.json">原文/SHA/物理产物索引</a>；快照 '''+html.escape(meta['created_utc'])+'''。空值不是0。</p>
<div class="scroll"><table><thead><tr><th>block</th><th>原始pin</th><th>已完成源版本</th><th>实际引出</th><th>native DRC</th><th>全块信号/时钟几何</th><th>双PG</th><th>setup / hold ns</th><th>完整规则/缺口</th></tr></thead><tbody>'''+table+'''</tbody></table></div>
<p>六块划分/全部接口及24767原始pin、74301行A/B/C覆盖保持。GEMM/MXU新成本ECO不混入纯XY；ACT父夹具仍有hold失败，VECTOR原3ns下setup失败。openSYS原窗口版与新92781成本ECO均已布线，均setup/hold失败，二者分别记录。LL PG-only的4项native失败与完整窗口92690/92691分别保留。</p>
<h3>92783：重复顶层LEF导致提前失败，完整deck未执行</h3>
<p>两块旧costed-r01都merge_returncode=1，分别Duplicate MACRO name: gemm_engine / llhd_opentpu_mxu。错误发生在DEF读取时自动载入同目录abstract.lef/detailed.lef；尚未返回严格合并检查，missing_GDS_cells=[]不能证明GDS齐全。Slurm COMPLETED 0:0是旧包装器未传递失败，不是合并通过。</p>
<p>安装KLayout0.30.12的真实API审计证实read_lef_with_def默认为true、会额外读取DEF旁全部LEF。新9345fd3驱动只读取原配置显式的标准单元/真实SRAM LEF依赖，保存并重新读回配置验证清单一致；没有删除LEF、改几何、开放allow-empty或删除规则。92798在新costed-r02实际重跑，两个同名视图不再被当成自身子宏。</p>
<div class="scroll"><table><thead><tr><th>block</th><th>严格合并错误</th><th>真实缺失GDS</th><th>deck执行</th><th>deck项数</th><th>阶段结果</th></tr></thead><tbody>'''+stream+'''</tbody></table></div>
<p>GEMM已实际完成严格合并；MXU实际检出4个缺失fakeram GDS，不能用空单元或LEF矩形代替。MXU诊断GDS上的deck即使执行也不证明全设计通过。原FreePDK45 deck及其WELL/包围覆盖疑问不修改；命令成功和0项也不自动代表制造签核。新包装器会传递合并/规则失败，仍以逐block原生回执为准。</p>
<h3>新收齐父夹具终态：批作业失败与子结果分开</h3>
<div class="scroll"><table><thead><tr><th>实际物理版本</th><th>路由返回</th><th>fresh native DRC</th><th>所检连通</th><th>信号网数</th><th>双PG日志连通</th></tr></thead><tbody>'''+parents+'''</tbody></table></div>
<p>92700与92714均已终态FAILED，不能继续标运行中：GEMM旧源C先前DRT无AP，Aopt子试验却已native0、3753网/7506端点及双PG通过；MXU Aopt/C均完成布线/2172网/4344端点连通及双PG，但fresh native分别5/2项spacing失败。C的两项位于M6的act_data[12]与macro OBS、以及M10的act_data[197]/[213]之间；Aopt五项均为M10信号间距。错误原文及来源保持，不用DRT0覆盖fresh结果。</p>
<p>新版GEMM父夹具92721也已终态FAILED：完成实际路由、所检信号连通与双PG，fresh native仍有1项M10 gemm_a_rdata[128]/[129]间距错误。92841只针对已证实位置，用实际异网M10走线/via、PG、macro OBS和1.5μm该层PRL上限筛选新父层点并重接；原叶M5/M6及PG不改，最新终态如下，不把旧源夹具冒充成本ECO/658diode叶资格。</p>'''+landing_text+'''
<h3>MXU M6局部层次归属：同网占用仍不是规则豁免</h3>
<p>92891只读取得父层、旧叶块与成本ECO叶块的真实局部线段、via落脚、pin、PG及OBS。两叶源所导出的M6矩形/网络标签一致；与原生M6红框相交的父层OBS由实际同网叶金属覆盖。这提示该报项与抽象的网络归属有关，不能把OBS当空白、删除OBS或直接豁免原生DRC。两叶源各有2项OBS变换未核对，完整层次/跨层规则仍待验证。92892另行修订父层act_data[197]的M10接点并重布线，保留全部原pin/PG和另一M6报项，不提前宣布通过。</p>
'''+ownership_image+'''
<p>这些旧夹具绑定各自记录的旧叶ODB，不是新成本ECO视图的父层资格。每块只有256个新的父层M10中间接点，原叶M5/M6 pin不改；其余点真实同层重合，非遗漏。</p>
<h3>公平周边控制：相同单元成本，不重做C</h3>
<div class="scroll"><table><thead><tr><th>优化边界Aopt</th><th>相同X2换型数</th><th>fresh native DRC</th><th>所检全块连通</th><th>setup ns</th><th>hold ns</th></tr></thead><tbody>'''+boundary+'''</tbody></table></div>
<p>92812已COMPLETED，两块Aopt均实际增量DRT、RCX、独立native0和所检全块连通通过；GEMM与MXU分别沿用C相同3/1处换型、标准单元master面积+1.596/+0.266μm²，原pin/PG/外框和源保持。原SDC/允许层不变；setup/hold分别0.772449/0.053582和0.249090/0.053253ns。它们是等成本叶块对照，不是共同底座或完整系统收益结论。</p>
<p>上述是历史3/1换型同成本来源；主矩阵当前GEMM的658diode及追加两换型另有真实负载/单元成本，不能直接与此旧Aopt作纯XY收益比较。MXU新M6引出重接也未替换此组旧r04布线/RC来源，须另列实际source。完整周边系统对照仍需匹配后续实现口径。</p>
<img src="assets/equal_cost_leaf_margins.png" alt="同换型成本叶块提取余量实测，不是系统资格" loading="lazy"><p><a href="assets/equal_cost_leaf_margins.svg">同图SVG</a>；四份数据均来自实际提取回执，非几何线长预测。</p>
<div class="scroll"><table><thead><tr><th>同ECO叶块方案</th><th>DRT实测总线长 μm</th><th>DRT via数</th><th>相对同ECO Aopt线长</th><th>相对via</th></tr></thead><tbody>'''+route_table+'''</tbody></table></div>
<p><a href="data/equal_cost_leaf_actual_metrics.json">实际逐层线长、via及原生日志SHA</a>直接复用已完成DRT最后一组报告，没有重复路由。数值按工具报告精度取整μm，逐层取整和总数可能有小差异；via按DRT口径，不当完整PDN via统计。与候选几何L1、提取RC及系统收益分别记录。即使叶块内部成本增加，也保留内部方案，继续共同底座/适配层系统总成本验证，不能据此撤回边缘并结束研究。</p>
<h3>历史天线规则分歧：原始源失败保留</h3>
<p>只读审计92825在同一GEMM实际ODB上check_antennas报0网/0pin，而严格合并GDS原deck仍报1460项天线。源SHA保持，未调用修复。实际ANTENNA_X1物理单元和原Liberty模型均存在，输入A的非零capacitance为0.023429（须按原库单位解释）；未加入零电容占位。接下来比较真实LEF规则与GDS公式、连接/层覆盖及diode识别；native0不抹去GDS失败。</p>
'''+rule_text+'''
<h3>完整映射端点图相对验证：不同于RTL形式验证</h3>
<p>92837/92838已核对原始源ODB与新成本ECO：GEMM 226775个非filler实例/826710个信号端点，MXU 179887/635434，全部实例、逐pin网络、方向、时钟/复位/常量及顶层端口一致；仅原定3/1处换型，实际Liberty逻辑与状态合同相等。未修改存储黑盒的实例和全部连接，以相同存储合同为条件的数字功能保持证据通过；不是RTL等价、模拟行为等价或完整物理签核。</p>
<p>新增SYSTEM 92886同样通过全量相对数字合同：438852个原非filler实例、1539803个原信号端点、2229个顶层端口与529989个原网络分量保持；5829个新增实例仅为已核实identity缓冲，980处原实例换型Liberty逻辑/状态相等。逐分量检查原驱动方向可达性、无新增缓冲环、无原网络误合并，9723个未连端点逐项保持，不将NULL统一短接。5个反例测试包括反向缓冲、缓冲环、误合并和未连端点改变，防止仅做无向合并误判。结论以原硬存储合同不变为条件，非RTL或模拟/时序等价；SYS负STA和规则缺项仍然失败。</p>
<h3>GEMM天线修复输入：真实多边形对应与实际diode几何</h3>
<p>92901已经完成1460项实际GDS错误多边形与原生导体的正面积精确相交对应，均唯一对应，共636个网络；不使用bbox交叉猜网。之后解析diode源层声明时失败（源deck实际使用polygons而不是input），原失败保留。92903只修正源声明读取并按SHA复用已完成对应，不重跑布线或篡改规则。真实标准GDS存在非空ANTENNA_X1，按原deck的(nplus &amp; active)−nwell识别面积0.0081μm²、contact相交面积0.004225μm²；原Liberty具有非零输入电容。上述仍是修复输入准备，未插入实际diode，原1460项仍未修复；几何对应不替代LVS或完整规则签核。</p>
<p>后续已收齐92781：SYS隔离合法化后的成本ECO完成真实详细布线、RCX及fresh native0，466332网/1474481端点所检连通通过；本轮路由前后cells/pin/PG/die原文指纹相同，单元修复/合法化成本另算。实际setup−0.462192ns、hold−0.125999ns，1113条VIOLATED文本标记（不是全部违例计数），仍时序/电气失败。原窗口版−1.779887/−0.389230和历史崩溃保留，不把成本ECO改善混成纯XY收益。</p>
'''+system_text+'''
<h3>共同集成已经实际启动，但尚非合格或冻结底座</h3>
<p>新增92846/92847实际导出匹配等成本G/M Aopt全部3753/2172位的非零研究模型；92848导出实际VECTOR完整1022-pin迁移源的2246位模型及LL PG-only完整13507位模型。后者原native4失败保留，明确标UNQUALIFIED_FAILED_DRC_SOURCE，不因模型导出提升为规则通过。</p>
<p>固定信号导体API首轮92853真实失败：BPin不接受FIXED状态枚举；改为安装工具支持的FIRM后，92854实际生成两处接入矩形及含FIXED metal10信号段的ODB/DEF。原失败不覆盖；API探针不代表共同底座实现或规则通过。</p>
<p>六资源实际集成92855在独立common_integration/r01/C目录执行：复用既有完整构造图、真实资源和交错位置、256条×32μm共享导体拓扑/预算，读取匹配的完整详细OBS与实际研究模型；PG、合法接点、固定导体、底层路由及独立验证分别留回执。当前调度状态：'''+html.escape(result['actual_common_integration_trial']['state'])+'''；当前阶段：'''+html.escape(str(result['actual_common_integration_trial']['status']))+'''。92930已成功导出真实DEF，但解析未考虑缩进而失败；92931只复用该有SHA的已完成原生DEF，实际核对全部256条FIXED metal10与逐网绑定、32μm×0.8μm几何，总中心线8192μm，原失败保留。不是仅核对计划CSV。底层GRT仍运行，构造端口尚待真实模式降为固定几何，尚无两完整M11/M12功能或合格冻结。</p>'''+fixed_image+'''
'''+placement_image+'''
<p>VECTOR 92861在无GRT、无增量路由、同进程无SPEF的隔离条件下仍EST-0104失败。实际VECTOR有411821个filler，SYS源没有。仅将remove_fillers移到estimate_parasitics之前，92867原生命令成功，实际14处换型、17个缓冲插入并保存检查点；单变量对照证明该排序足以排除本隔离流程中的错误，不能外推已解决所有工具状态问题。上游<a href="https://github.com/The-OpenROAD-Project/OpenROAD/blob/82552e4e9180fd5dd0c9cda58273029c83efb146/src/est/src/EstimateParasitics.cpp">固定源码参考</a>在增量修复入口拒绝待更新的寄生状态；安装二进制版本仍显示unknown、源树不存在，不能冒称此上游commit就是安装版本。原SDC和最终检查不放宽，新检查点尚未合法化、未重布线/提取，不是最终RC/STA通过。</p>
<p>92872已取得真实终态：从该检查点接续、不重复repair_design，独立合法化、全详细布线、fresh native0、375675条多端信号/时钟网和双PG所检通过；实际RCX后setup仍−4.140220ns、hold0.037989ns，83个文字VIOLATED标记，整体FAILED而非签核。新增180个功能实例、818原实例换型、875原实例移动，标准单元master面积+917.700μm²，全部独立成本；旧−4.195674ns源保留。92914/92915重读实际SPEF分析VECTOR/SYS完整关键路径，不放宽SDC；92913检查VECTOR实际全量有向缓冲合同。最新终态以矩阵和原文为准。<a href="data/runtime_submissions/vector_resume_r01.json">提交/固定驱动</a>、<a href="data/runtime_submissions/vector_resume_r01.execution.json.gz">初始回执</a>分别保留。</p>
<p><strong>真实提取路径诊断：</strong>92914/92915精确重放其VECTOR92872及SYSTEM92781源setup/hold；不是新SYSTEM92968的路径。VECTOR最差路径为p0_r[18]到wr_data_r[18]，发射Q之后141个cell arc约6.740ns、142段net arc约0.198ns；cell值含实际负载/slew影响，不是无法改善的零线长下界。旧SYSTEM最差输出路径有8个cell arc约0.455ns、9段net arc约1.052ns，其中最后到port约0.657ns；新buffer重排后的实际余量/DRC另列。工具JSON有舍入，不代替原文6位余量；未放宽时钟，不把旧路径当新源或修复通过。</p>
<figure><img src="assets/actual_critical_path_diagnosis.png" loading="lazy"><figcaption>实际SPEF关键路径；不包含发射时钟/required-time项，不是线长或零连线下界。<a href="assets/actual_critical_path_diagnosis.svg">SVG</a> · <a href="data/actual_critical_path_diagnosis.json">原文SHA/数值</a></figcaption></figure>
<p><strong>SYSTEM真实输出缓冲试验92921：</strong>全部1244个输出port纳入选择，772条私有identity链、1262个已有buffer生成真实重排，不增单元、不换型、不改网络。实际Diamond合法化后OpenROAD触发Signal11（implementation=-11），没有完成路由；moved_NOT_LEGALIZED_OR_ROUTED.odb及完整失败回执保留，原pin/PG/外框和源保持。后续复用已存检查点，在独立不加载STA的进程验证合法化，不重复生成同一移动方案。原SYS源时序失败不删，当前仍非物理修复通过。</p>
<p><strong>92925独立恢复已实际推进：</strong>复用上述1262个buffer坐标，独立几何进程不加载Lib/SDC；原生合法化、check_placement及原功能master/连接与非选中单元位置合同均通过，原本无filler则未新增。原生关闭的placed ODB及两份实际合同文件另索引SHA，与原source合同相等；不是重选点或跳过检查。随后在新进程恢复原Lib/SDC及M2–M8/M4–M8约束，完整重接线继续；最终DRC/PG/连通/RCX/STA未终态，不宣布时序修复或准确崩溃根因已证实。</p>
<p><strong>GEMM真实天线ECO：</strong>92910已完成636个真实ANTENNA_X1接入、完整重布线、fresh native0及268637网/806621端点所检连通、双PG和真实RCX。setup/hold为0.770727/0.039500ns，但新增两个max-cap失败：_328822_/ZN（实际INV_X1，67.621605&gt;60.730000fF）、_332783_/ZN（实际XNOR2_X1，27.449909&gt;26.016199fF），并非电气通过。原功能实例位置/连接、原pin/PG/外框保持；新增636单元master面积169.176μm²、每个实际输入cap0.023429fF均单列成本，非block面积变化。</p>
<p>92929独立原生全量数字合同通过：原226775非filler实例、826710个信号端点、3753端口完全保持，新增636个真实单输入无输出/状态diode各连到已核对636网；真实负载变化不被当作RC/时序等价。'''+diode_stream_text+'''两个源cap失败及其后续尺寸修复分别记录，未降负载或删检查。</p>'''+cap_text+chain_resume_text+upper_text+incremental_text+'''</section>'''
