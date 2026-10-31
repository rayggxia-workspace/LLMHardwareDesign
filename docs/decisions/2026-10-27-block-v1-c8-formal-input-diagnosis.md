# C8严格原生LEC输入对应的只读诊断

134 A/C与141完整组合均在实际最终C8的严格LEC对应门失败，尚不能进入后续物理/组合功能资格。134实际日志给出UNSAT/IDENTICAL，但归一化后common inputs=289078、diff0=1004、diff1=1032，PI=290082/290110，全部PO=291263对应；保留原失败，不删除“无未匹配边界”或“全部输入正向对应”要求。

新增166双1CPU只读诊断入口，独立读取134原失败收据、完整原生日志/配置、before/after逻辑JSON和投影proof，并按失败收据逐文件核SHA。实际大JSON解析放计算节点，24GiB/路估计加20%余量决定2/1并发；不在登录节点运行全图分析。分别列出原始未匹配输入标签、真实Liberty中的时序单元类别、两图全部单元/顶层接口统计、逐类型输入常量x/z、state实例的共同/新增/删除/换master或pin接口情况。仅做标签到同名cell/alias的词法候选，明确不是已经证明的对应。

这次诊断不运行新的LEC、不改物理数据库/逻辑图/原日志、不移除任何边界或改变验收门。报告passed仅表示SHA绑定的诊断完成，native_lec_qualified及qualified_hard_macro固定false；没有实际证据时不推断28个额外PI属于无害浮空或自动豁免。源码提交时166尚未部署/运行。

165已提交job92314；先在node22因Resources排队，实际sinfo显示node22全96CPU已分配、node25空闲，故只对同一待运行job原地改ReqNodeList=node25，未取消/重建/增加allocation，原manifest保留并另存run165-scheduler-amendment.json。17:05读回job仍92314、已RUNNING于node25，两路2CPU实际启动。其他成员未操作。

T6K同源交接索引为work/YUZE-LU/121/t6k-qa127-handoff-164.json，含A/C各24个原始角色路径、生产/完整物理/最终功能/视图/prepare收据和SHA、实际工具/容器SHA。仅整理已封存收据，没有复制或重新hash大产物；独立打包时仍需前后hash及完整QA，不能把索引当便携bundle或边界通过。实际164模型没有pg_pin、VDD/VSS为普通input（cap=0、max_transition=.199），与LEF的INOUT POWER/GROUND表示不同；#127原接口拒绝保持，待主线核正确PG合同并以新版本验证，原164不改。


## 2026-10-27 17:28 CST 实际终态与后继入口

165/92314实际C8 A/C探针全部11门通过，4:36、TotalCPU7:29.230、MaxRSS4128260K，node25同allocation双2CPU。A45/C29网改动，其中15/4处via9落点；原生upper诊断合并标记A37/C25降至0，完整upper接触0、固定低层/其他网/完整V及源SHA保持。这不是162原raw49/37项的完整GDS接收。166/92326只读严格LEC诊断双1CPU实际通过，0:50、CPU1:20.266、MaxRSS71428K；A/C时序实例143988逐名相同，无新增/删除，A501/C277处DFF_X1变DFF_X2，无字面x/z输入，但尚未证明原生未匹配PI对应，不豁免严格门。141/92256实际FAILED/1:40:06/CPU3:20:52/MaxRSS358556384K，同样被严格C8 LEC拒绝，未完成组合功能。新167准备从实际165接受ODB重新原生最终输出/默认flow LEC/RCX及全片DRT，c96双8CPU，200GiB/路加20%余量；本次提交时尚未运行。T6K161完整接收和164视图通过仍不等于宏边界资格；164 Liberty PG及完整flat timing源另以新版本修正。17:25本任务4个RUNNING allocation（057三路、067）；统一预算基础6/上限8，含PENDING/未知；其他成员未操作。完整P0–P6未完成。

证据：results/run165-group-terminal、run165a/c-terminal、run166-group-terminal、run166a/c-terminal和run141-group/a/c-terminal（均位于work/YUZE-LU/121/）。167采用native_pipeline_c8_escape.json、native-c8-finish-group / native-c8-run-shared109-a/c，保持严格状态边界LEC未通过标志；不启动已知依赖失败的完整接收。
