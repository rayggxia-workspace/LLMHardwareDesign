# Issue162：较小die真实必要电容0，继续完整物理链

更新时间：2026-11-05T04:13:13+08:00。[Checkpoint91](../../../work/YUZE-LU/162/continuation-checkpoint-91.md) / [385项原件及5项外置大文件](../../../work/YUZE-LU/162/continuation-proof-91/index.json)。全部23物理类型/138六文件、main六宏、R256、S1350内部驱动和345状态宿主保留。

source1670新增29固定宏组平移候选验证；16060原10676x10892die不扩大，整数4um平移最大232um，成员相对位置/固定mask/外部端口/朝向不变。source/archive1029文件与反向补丁审计通过，实际16800全真实信号/PG接点重建和原nativeground/mininputpin low/base/high必要电容均0违例，1693复核通过。数学解与必要电容0仅准入完整测试，绕线、过孔、耦合和分布时序仍未通过。首次1672遗漏seed>=24上下文被输出创建前拒绝；1680补seed16800，实际复用坐标、不跑RNG、不改门，原失败保留。

端口parity诊断16600仍1379494DRC，跨网占用拒绝；其17499项部分报告4396禁用过孔obstruction、实际端口位置0项。同引导/端点/摆放/16线程/同一轮数legacy16780为1383828DRC，总体只略改善，不能把端口症状修复当成拥塞根因全部解决。完整legacy/parity统计见本地索引中的paired-16780-16600-analysis.json；两者都未获得路由资格。

source1690只在已有opt-in搜索模式将全局奇数过孔阻挡1nm扩大为1um：最近合法中心仍2.5um净距，大于原2.2um；所有原合法棋盘中心保留，默认Tcl及两种markerLEF逐字一致，工艺/固定宏/RTL/最终门不变。1029文件/反向补丁审计通过，实际16920五例空DRC/原网格/棋盘/连通和九项非法导入拒绝通过。16960基于actual16800进入原完整七阶段；1697严格当前函数、原六键与自己的geometry/PG/三档RC绑定，1698核实实际11149网/24760接点、四组互斥16CPU、224GiB预测需284.8GiB可用及原1um阻挡。三份后继224GiB STA在已有node6/source269上限256控制器。

本轮仅fresh验证替换本任务14781/source1470子步骤95155.208：16日志全部40+轮、无最终输出、specSHA/UID/job/node/PID/全命令/当前图/实际内存核验通过；原规格/源码/日志/部分结果留存。其余35链、8父节点及外部R不动；新预检/对照/完整链动态自然补位，c96六16CPU、c64四16CPU。旧10711此前guard拒绝未动，所有历史失败保留。首次端口诊断unique_sites统计因defaultdict查询插入空键而膨胀，修正为get并同时保留原helper/JSON；碰撞/阻塞0结论未变，独立必要匹配也通过但不构成路由证明。

**仍无全图零冲突、实际native几何/XOR/PG及low/base/high分布RC300MHz setup/hold/电气联合通过；继续定位迭代，不在检查点停止，不放宽门，不借单块宣布系统通过，不自行合并。** 35251行原始诊断JSON已逐字压缩保留在91本地归档，原路径改为精确hash索引，便于审查。登记PR5 pending；看板缺配置/unverified、同步pending；审查待指定。

[远程原件](continuation-proof-91/index.json)、[本地来源/同参数对照](continuation-proof-91/local-index.json)、[实收](continuation-proof-91/reception.json)，承接[90](continuation-checkpoint-90.md)。
