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
                w=csv.DictWriter(f,fieldnames=['native_net','actual_marker_count','actual_layers','already_connected_real_diode','source_receipt']);w.writeheader()
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
            incremental_text='<p><strong>92975定向22个新增真实diode：</strong>原层接线/详细布线、原视图合同、双PG及RCX/STA原生命令均已执行；闭合原生进程报告setup/hold='+str(partial.get('setup_ns'))+'/'+str(partial.get('hold_ns'))+'ns，文字违例='+str(partial.get('literal_VIOLATED_markers_not_complete_failure_count'))+'。独立fresh DRC、全量数字图及源合同以最终receipt各自为准，未终态不记0/通过。92976为对应严格GDS原deck依赖作业；不把提交视为规则通过。旧37项原样保留。</p>'
        if q.get('completed_utc'):
            incremental_text+='<p>92975最终回执：fresh native='+str(q.get('fresh_DRC_count'))+'，全量22新增负载数字合同='+str(q.get('all_original_instances_and_signal_graph_preserved_with_only_22_real_diode_loads'))+'，原pose/端点='+str(q.get('all_prior_functional_and_636_diode_poses_and_terminals_unchanged'))+'。无论Slurm结局，完整规则/RTL/系统资格仍未通过。</p>'
    prepared=snapshot/'upper_adaptation_trial/r02/preparation.json.gz'
    if prepared.exists():
        q=read(prepared);result['upper_all770_actual_hook_preparation_r02']=dict(q,evidence=(dest/prepared.relative_to(snapshot)).relative_to(out).as_posix())
        upper_text='<p>92974已核查同一真实下层检查点的1541个M10接点、两唯一时钟alias及via10下层0.8×0.8μm落脚；两模式各770条边/1540个实际hook，256共享资源分别使用真实A/B两端。当前适配层GRT运行，计划与真实下层绑定不等于上层布通或两完整功能；私有下层、叶块与完整检查未闭合，未冻结。</p>'
    for revision in ['r01','r02']:
        p=snapshot/('tool_api/grt-start-'+revision+'/execution.json.gz')
        if p.exists():result['native_GRT_capability_'+revision]=dict(read(p),evidence=(dest/p.relative_to(snapshot)).relative_to(out).as_posix())
    diagnosis=root/'vector_table_diagnosis_r02'
    if (diagnosis/'summary.json').exists():
        folder=data/'vector_Liberty_table_diagnosis';shutil.copytree(diagnosis,folder,dirs_exist_ok=True)
        q=read(folder/'summary.json');result['VECTOR_exact_Liberty_table_grid_diagnosis']=q
        incremental_text+='<p>VECTOR只读库表诊断：实际关键路径141段cell arc合计6.7401ns；FA_X1/HA_X1/OAI33_X1在当前同函数系列无更大驱动型号。逐arc表格最小值混合不同slew/负载/跳变/条件，不是可同时实现的STA，也不是零线延迟下界或不可行证明；原约束与物理输入未改变。<a href="data/vector_Liberty_table_diagnosis/arcs.csv">141段实际master/arc及库表CSV</a>。</p>'
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
    target=data/'qualification_matrix.json';target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    columns=['case','block','original_signal_pins','partition_and_all_interfaces','candidate_ABC','completed_source','actual_internal_route',
             'native_DRC_count','all_multiterminal_signal_clock_geometry','power_grid','setup_ns','hold_ns','violation_marker_rows',
             'complete_rules','historical_parent_target_layers','mapped_design_formal_equivalence','RTL_system_formal_equivalence','parent_access','full_qualification']
    with (data/'qualification_matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');w.writeheader();w.writerows({k:r[k] for k in columns} for r in rows)
    labels={'COMPLETED':'已完成布线；非完整签核','COMPLETED_COSTED_ECO_NOT_PURE_XY':'成本ECO已布线',
      'COMPLETED_BUT_NATIVE_DRC_FAILED':'已布线；native失败','NOT_TERMINAL':'尚未终态',
      'NATIVE_VDD_VSS_COMMANDS_EXECUTED':'双PG原生命令执行','NOT_YET_READ_FROM_STAGE_RECEIPT':'PG回执待核',
      'NOT_PASSED_OR_INCOMPLETE_COVERAGE':'未通过/规则覆盖不全','GDS_MERGED_DECK_NOT_TERMINAL':'GDS合并通过；deck未终态',
      'FAILED_STRICT_GDS_MISSING_CELLS; partial-deck results diagnostic only':'缺宏GDS；全设计失败',
      'AVAILABLE_DECK_HAS_FINDINGS':'原deck仍有错误项','AVAILABLE_DECK_0_COVERAGE_STILL_INCOMPLETE':'原deck零项；完整覆盖未闭合',
      'COMPLETED_REAL_DIODE_AND_TWO_SIZE_ECO_NOT_PURE_XY':'真实diode/换型已布线',
      'costed_real_diode_and_sizes/r01':'diode+两换型/r01',
      'CURRENT_GDS_PENDING; PRIOR_REAL_DIODE_GDS37_FAILED; COVERAGE_INCOMPLETE':'当前GDS待验；旧37失败/覆盖不全',
      'CURRENT_REAL_DIODE_SIZE_GDS37_FAILED; COVERAGE_INCOMPLETE':'当前GDS37失败/覆盖不全',
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
<p>新版GEMM父夹具92721也已终态FAILED：完成实际路由、所检信号连通与双PG，fresh native仍有1项M10 gemm_a_rdata[128]/[129]间距错误。92841只针对已证实位置，用实际异网M10走线/via、PG、macro OBS和1.5μm的该层PRL上限筛选新的父层接点并重新接线；其原叶M5/M6及PG不改，等待真实终态，不宣布通过，也不把旧源夹具冒充成本ECO叶视图资格。</p>
<h3>MXU M6局部层次归属：同网占用仍不是规则豁免</h3>
<p>92891只读取得父层、旧叶块与成本ECO叶块的真实局部线段、via落脚、pin、PG及OBS。两叶源所导出的M6矩形/网络标签一致；与原生M6红框相交的父层OBS由实际同网叶金属覆盖。这提示该报项与抽象的网络归属有关，不能把OBS当空白、删除OBS或直接豁免原生DRC。两叶源各有2项OBS变换未核对，完整层次/跨层规则仍待验证。92892另行修订父层act_data[197]的M10接点并重布线，保留全部原pin/PG和另一M6报项，不提前宣布通过。</p>
'''+ownership_image+'''
<p>这些旧夹具绑定各自记录的旧叶ODB，不是新成本ECO视图的父层资格。每块只有256个新的父层M10中间接点，原叶M5/M6 pin不改；其余点真实同层重合，非遗漏。</p>
<h3>公平周边控制：相同单元成本，不重做C</h3>
<div class="scroll"><table><thead><tr><th>优化边界Aopt</th><th>相同X2换型数</th><th>fresh native DRC</th><th>所检全块连通</th><th>setup ns</th><th>hold ns</th></tr></thead><tbody>'''+boundary+'''</tbody></table></div>
<p>92812已COMPLETED，两块Aopt均实际增量DRT、RCX、独立native0和所检全块连通通过；GEMM与MXU分别沿用C相同3/1处换型、标准单元master面积+1.596/+0.266μm²，原pin/PG/外框和源保持。原SDC/允许层不变；setup/hold分别0.772449/0.053582和0.249090/0.053253ns。它们是等成本叶块对照，不是共同底座或完整系统收益结论。</p>
<img src="assets/equal_cost_leaf_margins.png" alt="同换型成本叶块提取余量实测，不是系统资格" loading="lazy"><p><a href="assets/equal_cost_leaf_margins.svg">同图SVG</a>；四份数据均来自实际提取回执，非几何线长预测。</p>
<div class="scroll"><table><thead><tr><th>同ECO叶块方案</th><th>DRT实测总线长 μm</th><th>DRT via数</th><th>相对同ECO Aopt线长</th><th>相对via</th></tr></thead><tbody>'''+route_table+'''</tbody></table></div>
<p><a href="data/equal_cost_leaf_actual_metrics.json">实际逐层线长、via及原生日志SHA</a>直接复用已完成DRT最后一组报告，没有重复路由。数值按工具报告精度取整μm，逐层取整和总数可能有小差异；via按DRT口径，不当完整PDN via统计。与候选几何L1、提取RC及系统收益分别记录。即使叶块内部成本增加，也保留内部方案，继续共同底座/适配层系统总成本验证，不能据此撤回边缘并结束研究。</p>
<h3>天线规则分歧仍未修复</h3>
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
<p><strong>真实提取路径诊断：</strong>92914/92915精确重放源setup/hold。VECTOR最差路径为p0_r[18]到wr_data_r[18]，发射Q之后141个cell arc约6.740ns、142段net arc约0.198ns；cell值含实际负载/slew影响，不是无法改善的零线长下界。SYSTEM最差输出路径有8个cell arc约0.455ns、9段net arc约1.052ns，其中最后到port约0.657ns，后续优先核对真实缓冲位置和绕行。工具JSON有舍入，不代替原文6位余量。未放宽时钟，也未宣布物理修复成功。</p>
<figure><img src="assets/actual_critical_path_diagnosis.png" loading="lazy"><figcaption>实际SPEF关键路径；不包含发射时钟/required-time项，不是线长或零连线下界。<a href="assets/actual_critical_path_diagnosis.svg">SVG</a> · <a href="data/actual_critical_path_diagnosis.json">原文SHA/数值</a></figcaption></figure>
<p><strong>SYSTEM真实输出缓冲试验92921：</strong>全部1244个输出port纳入选择，772条私有identity链、1262个已有buffer生成真实重排，不增单元、不换型、不改网络。实际Diamond合法化后OpenROAD触发Signal11（implementation=-11），没有完成路由；moved_NOT_LEGALIZED_OR_ROUTED.odb及完整失败回执保留，原pin/PG/外框和源保持。后续复用已存检查点，在独立不加载STA的进程验证合法化，不重复生成同一移动方案。原SYS源时序失败不删，当前仍非物理修复通过。</p>
<p><strong>92925独立恢复已实际推进：</strong>复用上述1262个buffer坐标，独立几何进程不加载Lib/SDC；原生合法化、check_placement及原功能master/连接与非选中单元位置合同均通过，原本无filler则未新增。原生关闭的placed ODB及两份实际合同文件另索引SHA，与原source合同相等；不是重选点或跳过检查。随后在新进程恢复原Lib/SDC及M2–M8/M4–M8约束，完整重接线继续；最终DRC/PG/连通/RCX/STA未终态，不宣布时序修复或准确崩溃根因已证实。</p>
<p><strong>GEMM真实天线ECO：</strong>92910已完成636个真实ANTENNA_X1接入、完整重布线、fresh native0及268637网/806621端点所检连通、双PG和真实RCX。setup/hold为0.770727/0.039500ns，但新增两个max-cap失败：_328822_/ZN（实际INV_X1，67.621605&gt;60.730000fF）、_332783_/ZN（实际XNOR2_X1，27.449909&gt;26.016199fF），并非电气通过。原功能实例位置/连接、原pin/PG/外框保持；新增636单元master面积169.176μm²、每个实际输入cap0.023429fF均单列成本，非block面积变化。</p>
<p>92929独立原生全量数字合同通过：原226775非filler实例、826710个信号端点、3753端口完全保持，新增636个真实单输入无输出/状态diode各连到已核对636网；真实负载变化不被当作RC/时序等价。'''+diode_stream_text+'''两个源cap失败及其后续尺寸修复分别记录，未降负载或删检查。</p>'''+cap_text+chain_resume_text+upper_text+incremental_text+'''</section>'''
