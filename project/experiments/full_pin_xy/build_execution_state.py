"""Canonical current execution state for the user-requested hard deadline."""
from pathlib import Path
import datetime,hashlib,html,json,sys
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/experiments/issue-126-full-pin';DATA=OUT/'data'

def build():
    now=datetime.datetime.now(datetime.timezone.utc);deadline=json.loads((DATA/'deadline_run.json').read_text(encoding='utf-8'));q=json.loads((DATA/'qualification_matrix.json').read_text(encoding='utf-8'))
    titles={'act':'ACT 激活数据块','mxu':'MXU 矩阵计算块','opentpu_aux':'openTPU SYSTEM 控制/搬运块','gemm':'GEMM 矩阵计算块','vector':'VECTOR 向量计算块','llaccel_aux':'llaccel SYSTEM 控制/搬运块'}
    next_steps={'act':'保留当前实际源；完成同源父层/完整规则核查，补真实存储宏GDS。','mxu':'保留当前实际源；研究夹具保持失败，继续真实系统父层连接并补存储宏GDS。','opentpu_aux':'当前源可集成；核对具体迟到/过早路径并保留时序失败。','gemm':'只用658 diode当前源；父连接此前在全局布线拥堵失败，按新公共父层重查。','vector':'当前2246位匹配视图93448已完成且SPEF重放匹配；仅用当前源集成，保留−4.140220ns时序失败。','llaccel_aux':'复用新13507位视图；先查剩余2832贴线候选和87点的原金属保留/父层接入条件，再做最小真实修改。'}
    rows=[]
    for r in q['blocks']:
        label=q['all_current_six_leaf_RECT_audit']['case_evidence_labels'][r['case']];a=q[label]
        odb,sha=next((p,v) for p,v in a['source_SHA'].items() if p.endswith('.odb'))
        failures=[]
        if r['setup_ns']<0:failures.append('数据最慢路径未赶上原时钟：setup余量'+str(r['setup_ns'])+'ns')
        if r['hold_ns']<0:failures.append('最小延迟检查失败：min余量'+str(r['hold_ns'])+'ns（需分清hold/removal）')
        if r['case']=='gemm':failures.append('当前658版父连接曾在全局布线拥堵检查失败，详细布线未执行')
        if r['case']=='act':failures.append('研究父层夹具hold约−0.074ns；与块内正余量分别记录')
        if r['case']=='mxu':failures.append('研究父层夹具hold−0.333124ns；1916直接接触网未标注寄生')
        rows.append({'id':r['case'],'object':titles[r['case']],'selected_version':r['completed_source'],'source_ODB':odb,'source_ODB_SHA256':sha,'signal_pins':r['original_signal_pins'],
          'actually_completed':['完整分块/逐bit接口清单','现有C版真实接入及详细布线源','该当前源的RC提取/STA已执行'],
          'checks_passed':['源native DRC报项0（只限原生检查覆盖）','导出多端信号几何连通检查','当前源原生RECT审计0，无此漏项影响'],
          'actual_failures':failures,'unverified':['完整适用规则/GDS LVS','完整设计RTL形式验证','真实共同系统父层及适配连接','时钟/电气规则的完整覆盖'],
          'electrical_classification':'原检查原文已保存；尚需将电容/转换时间与混合时序报项分别归类，不能只用总违规数判断',
          'next_minimum_action':next_steps[r['case']],'evidence':['report.html#latest-physical-gates',a['evidence']], 'full_qualification':False})
    for item in [
      ('common_base','共同M1–M10底座','common_integration/deadline-current-r01/C（当前六源，93460实际运行中）',['六块布局与256条原生FIXED M10共享导体已实际生成'],[],['当前源底层路由尚未终态','六源SHA已锁定；未通过真实接入/规则，不能冻结'],'已选齐六块当前源；93460按原资源/256固定导体构建，先收真实AP/布线回执；旧92855保留。'),
      ('adapter_open','openTPU 的M11/M12适配','闭合770支路组合试验/guard15独立试验',['770支路/514组合的所检逐网连接及256桥用途已检查'],['闭合源独立native曾127项报错'],['完整模式功能/RC/STA未执行','没有合格冻结底座'],'回查具体违规对象并局部修复；以同一冻结下层验证，不能把helper图当完整功能。'),
      ('adapter_ll','llaccel 的M11/M12适配','upper_branch_repair/r02 与 neighbors/r01',['770支路/514组合所检逐网连通及256桥必要性通过'],['两处M11异网Short尚在；单段及两邻线搜索无路'],['完整模式功能/RC/STA未执行','没有合格冻结底座'],'保持M10/via10/hook，联合处理相关上层线及via11；先真实局部验证，不再扩同一搜索窗口。'),
      ('perimeter','优化周边pin系统基线','Aopt 现有叶对照/93243底座运行中',['优化边界叶块对照已有实际结果'],[],['未完成同当前修复成本/源版本口径的全系统对照'],'完成统一源/资源/约束口径，分别列ECO成本，不混入纯XY收益。'),
      ('memory_material','ACT/MXU存储宏物理资料','原fakeram模型；93317真实RAM物理试验运行中',['原逻辑模型和缺失GDS来源已核实','64×64显式包装的4160状态点行为等价已证明'],[],['匹配原宏的真实GDS仍缺失','新RAM物理试验未终态，不能替代原宏'],'先测原RTL同容量实现的真实单元面积/端口合同；保留原宏，不拿空几何替代。')]:
        ident,obj,version,done,failed,unknown,nxt=item
        rows.append({'id':ident,'object':obj,'selected_version':version,'actually_completed':done,'checks_passed':[],'actual_failures':failed,'unverified':unknown,'next_minimum_action':nxt,'evidence':['report.html#latest-physical-gates'],'full_qualification':False})
    state={'schema':1,'authority':'唯一当前选用版本/阶段状态表；qualification_matrix为版本化技术证据库，不与本表竞争当前状态','as_of_utc':now.isoformat(),'as_of_Asia_Shanghai':now.astimezone(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'hard_deadline_utc':deadline['hard_deadline_utc'],'hard_deadline_Asia_Shanghai':deadline['hard_deadline_Asia_Shanghai'],'evidence_commit':'ede7c445150c2281156a76d99c496ff0cd7a9f0d','source_matrix_SHA256':hashlib.sha256((DATA/'qualification_matrix.json').read_bytes()).hexdigest(),'original_objective_complete':False,'delivery_forecast':'按期交付实际结果；原目标全部成功目前风险高，不能承诺。共同底层尚未布完，部分块时序失败，上层还有短路。','critical_path':['当前VECTOR匹配视图完成；推进LL父层接入','仅用六块当前真实源推进共同底层实际路由和固定连接','合法后冻结M1–M10几何/连接manifest，双模式只改允许上层','同源资源约束的优化周边基线和完整系统验证'],'active_job_ids_at_recovery':['92855','93217','93243','93269','93317','93460','93462'],'native_driver_outputs_are_evidence_not_completion':True,'not_new_experiments':['不重复候选覆盖','不为报告扩写或图美化阻塞工程','不按耗时取消原活动作业'],'rows':rows}
    phase=DATA/'deadline_engineering_receipts.json'
    state['delivery_forecast']='目前预计无法在12小时内把原目标全部验收通过；继续实际工程，并在北京时间09:19前交付已完成、实际失败、尚未验证与未执行的证据，不自行延期。'
    snapshots=sorted((DATA/'deadline_phase_snapshots').glob('actual_access_stubs_r03_*.json'))
    if snapshots:
        snap=snapshots[-1];state['actual_access_edit_phase_snapshot']=json.loads(snap.read_text(encoding='utf-8'))
        state['actual_access_edit_phase_evidence']='data/deadline_phase_snapshots/'+snap.name
    if phase.exists():
        facts=json.loads(phase.read_text(encoding='utf-8'))
        from deadline_state_overlay import apply
        apply(rows,facts)
        state['legacy_evidence_commit']=state.pop('evidence_commit')
        state['current_LL_physical_driver_commit']='459e32a2c48280474c39b8262dcdbaeff0f30357'
        state['source_deadline_stage_facts_SHA256']=hashlib.sha256(phase.read_bytes()).hexdigest()
        state['current_engineering_evidence']='data/deadline_engineering_receipts.json'
        state['current_hourly_report_observations']=['第1小时14:21UTC已报告','第2小时15:19UTC已报告','第3小时16:19UTC已报告；此前误看日志尾部导致漏收LL终态，现已纠正，以闭合回执为准','第4小时约17:19UTC已报告','第5小时约18:19UTC已报告：9517实际编辑/完整清单；预计无法在12小时全部验收，仍继续并按期交付']
    (DATA/'execution_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    esc=html.escape
    def listing(items):return '<br>'.join(esc(x) for x in items) if items else '无新增实际失败；不等于全部通过'
    table=[]
    for r in rows:
        src=esc(r['selected_version'])+('<details><summary>真实源/SHA</summary>'+esc(r['source_ODB'])+'<br>'+esc(r['source_ODB_SHA256'])+'</details>' if r.get('source_ODB') else '')
        table.append('<tr><td>'+esc(r['object'])+'</td><td>'+src+'</td><td>'+listing(r['actually_completed']+r['checks_passed'])+'</td><td>'+listing(r['actual_failures'])+'</td><td>'+listing(r['unverified'])+'</td><td>'+esc(r['next_minimum_action'])+'</td></tr>')
    text='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>12小时工程交付：唯一当前状态</title><style>body{font:15px/1.6 "Microsoft YaHei",sans-serif;color:#17283c;background:#f3f6fa;margin:0}main{max-width:1400px;margin:24px auto;background:white;padding:28px}h1{font-size:27px}table{width:100%;border-collapse:collapse;table-layout:fixed}td,th{border:1px solid #d8e1eb;padding:9px;vertical-align:top;overflow-wrap:anywhere;font-size:12px}th{background:#eaf1f7}details{font-size:11px}a{color:#176c9c}.warn{border-left:4px solid #b57723;padding:12px;background:#fff7e8}</style><main><h1>任务尚未全部完成；12小时硬交付正在执行</h1><p>硬截止：<b>北京时间2026年10月30日09:19</b>；采用更早的21:19作为保守起点，不自行延期。</p><p>已经做成：六块已有真实内部引出版本；LL的一万多个点保留，已发现的两处块内间距违规修成零，匹配的新物理视图也已导出。还没做成：共同走廊的线路未全部完成，两套系统尚未在同一合格冻结底座上通过验证，部分数据赶不上原定时钟节拍。</p><p class="warn">'+esc(state['delivery_forecast'])+'</p><p>以下是唯一当前状态表。已完成是产物确实生成；检查通过仅指列出的范围。未验证和未执行都不是已经证明失败。状态截至 '+esc(state['as_of_Asia_Shanghai'])+'。</p><table><thead><tr><th>对象</th><th>当前版本/来源</th><th>实际完成/已检查通过</th><th>实际检查失败</th><th>尚未验证/未执行</th><th>下一步最小必要动作</th></tr></thead><tbody>'+''.join(table)+'</tbody></table><p><a href="report.html">详细中文报告和真实对照图</a> · <a href="data/execution_state.json">唯一状态JSON</a> · <a href="data/deadline_run.json">期限与每小时报告时点</a></p></main></html>'
    if phase.exists():
        text=text.replace('<table>', '<p class="warn">最新实物来源：LL c4947012b239，累计修正13093个接入点（非从A边界移动数），13507位接口视图匹配、native0、725253网所检连通及双PG/RCX已执行；原负时序和8875电气违规保留。<a href="data/deadline_receipts/llsys-wire-pin-retention-r01/all_13507_actual_pin_correspondence.csv.gz">完整实际逐pin坐标</a> · <a href="data/deadline_engineering_receipts.json">阶段证据/SHA</a>。共同父层正在接续，尚非整套功能通过。</p><table>',1)
    if snapshots:
        e=state['actual_access_edit_phase_snapshot']
        text=text.replace('<table>','<p class="warn">独立新试验，尚未晋升选用源：9517个接点已实际编辑并补线，13507位完整坐标及24个原生单端声明口保留；编辑和双PG已执行。独立native DRC、全口AP、RC/STA等待终态，不能提前写通过。<a href="'+state['actual_access_edit_phase_evidence']+'">带时间的实际编辑阶段快照</a> · <a href="'+e['coordinate_artifact']+'">新13507位实际坐标</a>。</p><table>',1)
    (OUT/'status.html').write_text(text,encoding='utf-8',newline='\n')
    p=OUT/'report.html';text=p.read_text(encoding='utf-8')
    if 'id="deadline-status-link"' not in text:
        assert '<main>' in text
        text=text.replace('<main>','<main><p style="padding:12px;background:#fff4da"><a id="deadline-status-link" href="status.html">12小时硬交付：先看唯一当前状态表（截止北京时间10月30日09:19）</a></p>',1)
        p.write_text(text,encoding='utf-8',newline='\n')
    index={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='artifact_index.json'}
    (DATA/'artifact_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');print('CANONICAL_EXECUTION_STATE',len(rows),'objects; full objective incomplete; deadline',deadline['hard_deadline_Asia_Shanghai'])
if __name__=='__main__':build()
