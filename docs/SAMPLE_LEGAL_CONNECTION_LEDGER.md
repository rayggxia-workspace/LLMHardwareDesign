# 样本域角色槽、规范配方与准入边界（步骤2）

基线39bd7bf；七宏继承643c6012固定RTL。用户范围：现有八样本作研究输入、未知规模保守估计、暂不考虑外存。此稿建立角色账本和静态规则，实际任务/PR同步由本轮统一回执；未修改RTL。

实际枚举 **23源×27数据目的=621数据槽**，以及 **23源×20受控参数目的=460参数槽**；49个宏类别有向对均有下钻。M的A/B各保留S8/S16子格式，N Norm原值/gamma分开，R decay/beta分开。完整列名继承all-legal-connection-contract.json；输入6份文件的实际字节SHA在JSON provenance。

这1081槽不是1081条已证明合法边。当前已证明合法实例0、新系统RTL0、组合验证0、物理资格0。数据槽状态为：{'conditional_uninstantiated': 405, 'schema_or_semantic_binding_unresolved': 216}。需要具体FamilySpec、角色意义、字段、Fin/Fout、shape/布局、lineage、状态和容量后才能接受实例；缺RTL始终保留implementation gap。

## 1. 如何读账本

`data_slots`每行只索引source/destination、共享recipe_id、额外condition/guard/gap；长规则集中在recipes和各规则表。默认每槽还有G_BIND/G_SYS。`applicability`明确条件适用范围：G_WIDE只针对真正需要宽转换的已选字段；G_ARITH只在源尚未提供正确算法数量时成立；同实例REENTER/Tspool不强加给不同实例或同context RESUME。参数槽独立走PARAM_BIND，不允许把payload裸接成完整命令。profile与字段尚未绑定的槽为未决，不自动全绿。

语义guard失败表示拒绝**该profile实例/裸接方式**，不是永久禁止宏对。未就绪/pending违反状态guard时是等待或原生协议错误；容量/线路/缓冲不足是mapping gap；实现缺失是implementation gap。无外存不改变语义判定，也不偷偷回退DRAM。

## 2. 必要分支

| 源/目的特例 | 规范配方及限制 |
|---|---|
| 普通numeric→numeric | 导出→精确NUM_CAST→合成布局→BITPACK→有界片上中转→目标owner导入；零变换允许identity，不能为凑配方无限cast |
| M.RESULT64/partial、U48字段 | 保留完整宽度；通用S64/U64转换为gap。M.op5只覆盖本M结果的受限出口，不能给其他宽源当通用算术器 |
| N.EXP/PROB | EXP可明确作为未归一化数值参与算术，但不自动变概率；SOFT_REPLAY必须是该factor所绑定的确切EXP codes |
| EXP经S/T或其他无损路径 | 继承schema/context和精确码等价证明即可回放；不以生产者opcode是否N.EXP作永久黑名单。数值改变则不得沿用旧lineage/factor |
| ID→数值/score | ID_AS_INT F0是显式新语义；MoE score须ID_RESOLVE/gather。TopK record需score/ID JOIN，单个ID输入不能完成整记录 |
| STATS/META | 字段schema按位提取；count/owner/epoch等F0，max/min/sum沿input_F，sumsq用2Fin；保留位不是数据 |
| S/T opaque | 必须继承已知写入/初始化/租约schema再递归分派，不能从128bit宽度猜类型 |
| S ACK-forward | 保存同版本write echo、take ACK后才重入同S端口；不是任意ACK都产生新张量 |
| S loader额外输出 | 串行S基线采用独立预制1024B最大描述符spool，完成全部A/B义务再普通S写；不是暗增S端口 |
| 同T→T | 全批最多6144B先暂存S并等ACK→末读→release→新generation BEGIN回装；计算workspace另计，两个弹性槽不能替代 |
| 参数输入 | 字段提取/必要数值转换→值域/保留位/授权窗口检查→唯一owner构造命令；无验证opcode、地址、ID截断/取模非法 |

R inject/decay等若尚需算法计算，recipe显式依赖单独算术生产任务；CAST不生成缺失的系数/注入。N.gamma与E.C也检查目标操作的数学单位。

## 3. 容量和拓扑

运输只允许现有S16KiB/T6KiB与显式预算的新片上支持存储；不包含外存。S不足、loader1024B新增spool不存在、Tspool与其他live张量冲突都报mapping gap。S中的T输入spool、其他中间量和新增寄存spool必须分别计价，不可重复使用同一个活跃区域。

fork保存每消费者引用/接收状态；join独立保持各输入。N/R需要RESUME的同context阶段不强迫先关组/提交再开始；下一独立context才REENTER。T/R提交不形成跨宏原子；反馈需要明确初值、版本和存储延迟，不能把所有图环一律当非法，也不能由静态DAG宣称无死锁。

## 4. 已做与未做

生成器实际校验621/460唯一键、49宏对、23/27/20目录匹配和52项正/负/条件静态guard案例；案例涵盖宽bitcast、ID语义、EXP lineage、字段提取、ACK-forward、loader spool、T重入、R pending及片上不足。规则正例仍返回implementation gap，而不是硬件通过。

复现：`python -X utf8 <本报告同目录>/generate_edge_ledger.py --base <steps123-39bd7bf/integrated> --output-dir <独立输出目录>`；实际脚本位置在work/Melodydt/151。默认仅在脚本同目录输出两个文件。

未决：完整模型定点边实例的接受；本轮样本连接义务已在sample-connection-obligations.json登记、有限家族/shape/尺度域、字段与companion全部实例、操作/布局参数域穷举、片上预算、宽数值oracle与误差接受、RTL/活性/物理验证。没有把有限参数空间都实例化；报告不使用“1081条均合法/全通”表述。
