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
    root,out=Path(root),Path(out);sources=sorted((root/'gate_evidence').glob('gate-*'))
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
    audit=snapshot/'antenna_audit/r01/execution.json.gz'
    if audit.exists():
        q=read(audit);result['antenna_checker_disagreement']={'native_returncode':q['native_returncode'],
          'source_unchanged':q['source_unchanged'],'actual_diode_liberty_cells':q['actual_diode_liberty_cells'],
          'GDS_deck_findings_not_repaired':1460,'full_qualification':False,
          'evidence':(dest/audit.relative_to(snapshot)).relative_to(out).as_posix()}
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
<p>这些旧夹具绑定各自记录的旧叶ODB，不是新成本ECO视图的父层资格。每块只有256个新的父层M10中间接点，原叶M5/M6 pin不改；其余点真实同层重合，非遗漏。</p>
<h3>公平周边控制：相同单元成本，不重做C</h3>
<div class="scroll"><table><thead><tr><th>优化边界Aopt</th><th>相同X2换型数</th><th>fresh native DRC</th><th>所检全块连通</th><th>setup ns</th><th>hold ns</th></tr></thead><tbody>'''+boundary+'''</tbody></table></div>
<p>92812已COMPLETED，两块Aopt均实际增量DRT、RCX、独立native0和所检全块连通通过；GEMM与MXU分别沿用C相同3/1处换型、标准单元master面积+1.596/+0.266μm²，原pin/PG/外框和源保持。原SDC/允许层不变；setup/hold分别0.772449/0.053582和0.249090/0.053253ns。它们是等成本叶块对照，不是共同底座或完整系统收益结论。</p>
<h3>天线规则分歧仍未修复</h3>
<p>只读审计92825在同一GEMM实际ODB上check_antennas报0网/0pin，而严格合并GDS原deck仍报1460项天线。源SHA保持，未调用修复。实际ANTENNA_X1物理单元和原Liberty模型均存在，输入A的非零capacitance为0.023429（须按原库单位解释）；未加入零电容占位。接下来比较真实LEF规则与GDS公式、连接/层覆盖及diode识别；native0不抹去GDS失败。</p>
<p>后续已收齐92781：SYS隔离合法化后的成本ECO完成真实详细布线、RCX及fresh native0，466332网/1474481端点所检连通通过；本轮路由前后cells/pin/PG/die原文指纹相同，单元修复/合法化成本另算。实际setup−0.462192ns、hold−0.125999ns，1113条VIOLATED文本标记（不是全部违例计数），仍时序/电气失败。原窗口版−1.779887/−0.389230和历史崩溃保留，不把成本ECO改善混成纯XY收益。</p>
<p>共同M1–M10尚无实际预连/合格冻结，M11/M12尚无两完整功能。按用户新授权，可以继续明确标为未合格的集成试验发现问题；不会把构造链接、研究探针或未合格试验标成最终底座。</p></section>'''
