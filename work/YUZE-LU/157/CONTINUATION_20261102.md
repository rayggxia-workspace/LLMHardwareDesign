# 小容量 R 实施续办

Issue #157 / PR #160，继续执行，尚未授予新物理资格。原生产 R 和其他任务的代码、结果与作业保持隔离。

## 已完成的实际结果

|结果|终态与意义|
|---|---|
|原 A0/94708、A1/94726|12 小时上限 TIMEOUT，保留失败，不算通过|
|A1 独立恢复 attempt063|最终等价 IDENTICAL，原数据库 SHA 前后一致；setup −0.110381ns、hold −0.718791ns，未通过|
|B256 紧凑 attempt065|最终等价 IDENTICAL、router DRC0；面积327552µm²，setup −0.0743188ns、hold −0.0351025ns，未通过|
|B256 attempt068|setup150ps／hold100ps内部修复目标触发44942个hold缓冲上限，失败；原065保留|
|同步读 R1024 attempt071|63 个原有整数算例、28174656 次检查通过后综合；面积776918.702µm²，原核心源码不变|
|同步读成本074／匹配对照081|各48组真实RTL/SystemC运行PASS；48对输入、流量、算术及事务一致，额外周期精确等于每个串行128bit读包多一拍|

同步读口的合同、全部周期代价和证据见 [SYNC_READ_REVISION.md](SYNC_READ_REVISION.md)。Qwen128×8条带为18064→18320cycle（+1.42%）；24层任务+7.58%。2048连续任务的开销达到17–20%，不能推广成所有任务的收益。

## 仍在运行的物理工作

- attempt062/B1024：原异步读版本继续全流程，收集真实终态。
- attempt078：B256以setup100ps／hold60ps内部目标重新布线，最终300MHz约束、零违规标准不变；后续门及几何核验在同一allocation执行。
- attempt082：完成上述功能与匹配成本验证的两拍读R1024S，与已有CTS违规的原版并行；原版尚未终结，不把中间违规称最终失败。
- attempt083：仅一个更强时钟树候选。已完成B256的短输入控制路径在实际提取后出现hold违规；该候选从相同3_place结果重建时钟树，先用实际CTS时序／电气结果筛选，通过才继续完整布线。CTS参数由已部署ORFS源码和工具help核对，不修改验收约束。

早期未启动的门及候选因为源依赖／内部目标修正而退役，未取消正在运行的EDA。attempt070和072的构建路径错误、attempt076的调度依赖拒绝均保留，不能称功能或物理通过。各源commit、归档SHA、作业与远程路径见 [SMALL_CAPACITY_ACTIVE_RUNS.json](SMALL_CAPACITY_ACTIVE_RUNS.json)。

通过最终STA、电气和router检查后才导出GDS并运行完整原版FreePDK45 DRC deck；真实几何使用ODB/DEF/SPEF并与router线长核对。工具exit0、中间正slack和RTL模拟时间单位均不授予资格。不同die、pin跨度及布线变化如实报告。

复核命令：

```text
python project/experiments/r_architecture/verify_sync_cost.py
python project/experiments/r_architecture/small_capacity_review.py
python project/experiments/r_architecture/check_final.py
python scripts/check_project.py
```

原2096记录和772×2完整证明核验仍通过；新增96组匹配运行与63个unit算例分开计数。容量选择仍受工作集合及搬运策略约束，当前1024只是架构主候选。未替换主线R，不自行合并；Issue保持in_progress、PR草稿。登记沿用management-hub PR5 pending；无board.json，看板unverified／同步pending，审查人与管理员待指定。
