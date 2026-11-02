# 小容量 R：本轮交付与物理终态

Issue #157 / PR #160。本轮已获得**可交付的R-stream256独立宏**，完成容量研究和已启动物理实验的收尾。原生产R、其他任务代码/目录/作业及资格入口均保持隔离，未自行合并或替换。

## 实际可交付的宏

|项目|实际结果|
|---|---|
|状态与算术|每bank256条S32，双bank共2KiB有效载荷；标准单元寄存器阵列；8路S32×S33算术|
|物理|Nangate45 M1–M10；die1000×1000µm|
|标准单元面积|351009µm²；固定die面积另为1mm²|
|300MHz最终提取STA|setup +0.0247555ns；hold +0.0526906ns|
|违规|setup/hold/cap/slew/router及完整原版GDS DRC均0|
|物理网表等价|UNSAT、IDENTICAL|
|接点与供电|817个信号接点形状保持；168个新增BUF的VDD/VSS全部正确|
|几何与抽象|最终DEF/router逐层中心线匹配；最终ODB/SPEF生成实际LEF和typical Liberty|
|最终绑定|095的10/10检查PASS；097重核输出与095逐字节相同|

[完整绑定验收](smallcap-runs/attempt095-QUALIFICATION.json)记录各检查和最终文件SHA；[包索引](smallcap-runs/attempt095-PACKAGE.json)记录授权远程位置。包共279355327字节，含171个成员，逐成员实际读回核SHA。包SHA256为989d9e522b61e4b79b670c7e4acb0feacb8d7bf2b293b2e1e925ad1f937ced8d。

包内含GDS、ODB、DEF、Verilog、SDC、SPEF、LEF、typical Liberty、源代码和实际验收证据。[本地实收](smallcap-runs/attempt095-local-delivery.json)确认下载后的整包SHA一致；[直接视图检查](smallcap-runs/attempt095-view-check.json)确认提取的GDS仍为同一SHA、LEF/Liberty的819个接点集合完全一致。大文件不加入Git。

接口、数值缩放、实际已断言的命令延迟、读口、错误和全局提交边界见[小R宏合同](SMALL_R_MACRO_CONTRACT.md)。这是典型角300MHz独立研究宏，不是原生产R的ISA替换、多角/制造签核或完整模型/系统实现。

## 1024对照：已收齐终态，未授予资格

|试验|实际终态|
|---|---|
|异步B1024/062|完整流程exit0、最终等价及router DRC0，但最终setup −0.190275ns、hold −0.0365222ns及cap1；失败|
|同步082|放置阶段103998个hold缓冲后RSZ-0060；FAILED 2:0，无最终合格结果|
|同步093，放置20ps/CTS60ps内部目标|FAILED 3:0，CTS筛选失败；setup +0.104425ns，hold −0.252464ns，10条hold违规，cap/slew0；未进入后续路由|
|同步096，放置不额外补hold/CTS60ps|FAILED 2:0；放置阶段不再补hold，CTS插入105024个hold缓冲后RSZ-0060，实际minhold仍−0.248ns、TNS−2.130ns|

093的[真实CTS报告](smallcap-runs/attempt093-cts-final.rpt)明确给出最差路径：rd_index[7]输入到读地址寄存器D端；数据到达约0.33ns，包含时钟插入/不确定性/库hold的要求约0.58ns。因此问题已包含新增寄存器的输入最小延迟与内部时钟边界，不能只归因于状态数组大小，也不能因setup转正就称合格。

096配置的局部输入缓冲hook在PRE_GLOBAL_ROUTE阶段，因CTS先失败而**没有执行**，不能把它写成1024接入修复的已测效果。093/096只改变同一1024候选的实现策略，没有增加容量搜索点；所有冻结源检查点SHA不变。原接受用300MHz及IO/驱动/负载约束始终不变，不关闭DRC/天线检查。已启动作业均自然收尾，本轮不继续扩展搜索。

## 容量建议与明确代价

[20条容量与换页实测](SMALL_CAPACITY_REVIEW.md)完整比较256/512/1024/2048：

- **眼下可交付的第一份实物是256版**：适合≤256状态工作集，或确实可接受分块/换页的面积优先场景。Qwen128×8条带在256内需4块，实测16token为91952cycle；不能隐藏交换代价。
- **1024仍是有条件的架构候选，尚非合格宏**：恰好容纳Qwen条带，异步周期模型为18064cycle；两拍读为18320cycle。若必须获得这种驻留收益，需要另行修正并验收其物理接口/时钟边界，不能把本轮失败改名为成功。
- **512不作为默认折中**：装不下1024条带，虽比256减少部分控制等待，仍承担主要交换成本；本轮未追加完整P&R。
- **2048保留SSM/长驻留对照**：Falcon256×8条带为2048条目，在256内需8块；它在2048连续驻留任务明显有用，对1024条带则没有额外周期收益。

小容量确实降低映射面积、最大选择负载及全非时钟pin-C，但没有让译码/广播免费消失。1024同步版最大直接负载仍35843，pin-C1944.974447pF；流水切路径，没有消除选择网络。实际die、pin跨度及时钟/修复策略有差异，不把不同物理结果当作容量单变量因果实验。

[同步读合同及匹配成本](SYNC_READ_REVISION.md)：Qwen条带+1.42%，24层任务+7.58%，2048连续任务增加17–20%。S始终按冻结的16KiB标准单元版本/实际共享端口计价，不假定另一个任务的新SRAM已经可用；M/E宽算术也不免费。完整模型仅作状态尺寸和带宽下限推导，实际算例为真实维度的合成整数；不宣称完整LLM性能/精度或已标定能量。

## 失败与验证均保留

旧A0/A1为12小时TIMEOUT；A1恢复063最终等价通过但setup/hold失败。B256的065/068/078失败，083最终时序通过但完整GDS有217项天线违规；085逐项对应到128个顶层输入。089重布线后完整GDS0，但090发现新增BUF供电未连接，未授予资格。091修复PG并重做最终等价/提取STA/GDS；末尾几何目录冲突保留为批处理失败，独立094已实际恢复同一最终文件的几何核验，095显式绑定它。不存在检查跳过或资格转移。

全部源commit、工具镜像SHA、归档SHA、路径及作业状态见[实际索引](SMALL_CAPACITY_ACTIVE_RUNS.json)。原2096条记录（2056PASS/40原R超容量）和A1/A2h各772分区完整证明复核通过；同步63个unit算例、28174656次检查和48对RTL/SystemC匹配运行分开计数。A1/A2h完整证明不冒充新流式ISA与原生产R接口逐拍等价。

    python project/experiments/r_architecture/check_final.py
    python project/experiments/r_architecture/verify_sync_cost.py
    python project/experiments/r_architecture/small_capacity_review.py
    python scripts/check_project.py

## 交付状态

本轮R256技术成果、容量推荐和物理终态已齐，进入独立审查；不自行合并、不替换主线R。Issue/PR在线状态以最终回执读回为准。登记沿用management-hub PR5 pending；无board.json，看板unverified/同步pending，审查人与管理员待指定。审查重点是小R是否符合可接受的换页预算，以及新流式ISA的后续接入；这不授予其他候选或整个系统资格。
