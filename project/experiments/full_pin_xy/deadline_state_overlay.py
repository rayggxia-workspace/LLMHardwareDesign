"""Apply only source-bound new facts to the unique execution state."""
def apply(rows,facts):
    if not facts:return
    for r in rows:
        case=r['id']
        if case in facts['electrical_cases']:
            e=facts['electrical_cases'][case];types=e.get('by_electrical_type',{})
            r['electrical_classification']='当前匹配源原检查输出：'+('；'.join(k+'实际违规'+str(v['actual_violating_rows'])+'行' for k,v in types.items()) if types else '未列出max slew/max capacitance违规行；完整适用规则覆盖仍单列')
            r['electrical_evidence']=facts['electrical_evidence']
            for kind,check in types.items():r['actual_failures'].append(kind+'检查实际失败：'+str(check['actual_violating_rows'])+'行，见匹配源原文')
        if case=='llaccel_aux':
            e=facts['current_LL'];r.update(selected_version=e['source'],source_ODB=e['source_ODB'],source_ODB_SHA256=e['ODB_SHA256'])
            r['actually_completed']=['完整分块/13507位接口与既有A/B/C清单','当前源真实接点编辑：保留10261，再修正2832；不等于从A边界移动数','2827处旧pin金属以真实WIRE保留；全部原WIRE/VIA＋指定方块逐网核对','当前源RC提取/STA与匹配13507位物理/模型视图完成；未重跑GRT/DRT搜索']
            r['checks_passed']=['当前源独立native DRC0（原生覆盖范围）','725253网/2325528端点所检真实几何连通','双PG原生命令执行，原pin功能/层/尺寸/网络/外框/单元保持','当前c494源RECT审计0；原SPEF负时序逐字重放']
            r['actual_failures']=['setup余量−3.909000ns；min余量−0.587515ns（含removal，不能统称hold）','max slew1091行、max capacitance7784行实际失败；不是全部时序失败数量']
            r['next_minimum_action']='使用当前13507位匹配视图接续共同父层；针对剩余87位做真实first-hop预检/重接；电气修复成本独立记录。'
            r['evidence']=[e['evidence'],e['coordinates'],e['views'],facts['electrical_evidence']]
        if case=='common_base':
            r['selected_version']='common_checkpoint_def_import/r01：当前c494 LL＋其他5源；旧93460的实际接入失败单列保留'
            r['actually_completed']=['六块实际布局、供电生成及双PG连通检查完成','256原生FIXED M10共享导体与全局布线检查点已生成']
            r['actual_failures']=['详细布线实际失败：DRT-0073，u_llaccel_aux/bit_1011（M5、dram_rsp_rdata[329]）没有合法接入点；这个口负责外部存储返回数据。当前c494版此pin未移动，不能假设换版本即修复。']
            r['unverified']=['未生成完成布线的共同底座，不能冻结','最新c494 LL源尚待父层接续，不将f0b2源资格继承给新源','完整系统功能/规则/GDS/RC/STA尚未闭合']
            r['evidence']=[facts['common_base_actual_failure']['evidence'],facts['common_base_actual_failure']['native_log']]
            r['next_minimum_action']='复用已完成PG/固定预连检查点，接续当前LL及保守低层视图，保持M10连接对象/层级与几何不变，取得真实父层回执。'
            trials=facts.get('latest_engineering_trials')
            if trials:
                r['actually_completed'].append('新当前源经DEF检查点导入及双PG检查完成；原父层逐bit图/端口/PG/实例位置及256 FIXED保持；不是详细布线完成')
                r['unverified']=['当前导入源尚未完成父层详细布线，不能冻结','完整系统功能/规则/GDS/RC/STA尚未闭合']
                r['evidence'].append(trials['common_checkpoint_import']['evidence'])
                r['next_minimum_action']='先处理LL全部接口真实首级接入，复用已通过读回的检查点；保留旧NoAP和宏swap崩溃，不重跑已证明失败的调用路径。'
        if case=='memory_material':
            m=facts['original_RAM_mapping'];r['actually_completed'].append('原64×64同步读/位掩码RTL实际映射：17043单元、37608.676μm²')
            r['actual_failures']=['这个具体标准单元映射面积超过原5156.676μm²外框，不能直接替换；不是已证明所有SRAM实现不可行']
            r['evidence'].append(m['evidence'])
