# 当前状态

## 接续247的独立四轮研究（2026-11-10 Asia/Shanghai）

[Issue248 / PR249](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/249)由 YUZE-LU 在冻结 PR243@9d987151 上另开研究分支，评估有限权重直供、W8A8/A16、新增外存资源与状态相关贪心/DP，原生产 RTL/底座及 Melodydt 四轮任务不改。[报告](experiments/issue-248-stream-quant-synthesis.md)分别记录条件模型、独立 RTL 和真实权重量化筛查；未达10 token/s、未证明20%纯算法收益，也不转移300MHz物理资格。细节与实际Slurm终态见回执；待独立审查、未合并，登记PR5 pending，看板unverified/同步pending。

## 停止场景澄清（2026-11-10 Asia/Shanghai）

Issue247/PR243：用户确认任一原评估场景（包括prefill）达5 token/s或完成4轮即停止。已复核72条本轮及21条历史完整场景，本次16KiB最高3.69669737899；原64KiB未实装参考4.54743400007，均未达5，仍按4轮停止。[口径补充](experiments/issue-247-speed-iterations.md)覆盖冻结PDF中的临时decode-only停止假设。本次无新仿真；管理结构检查通过。下一步独立审查，状态in_review、未合并；登记pending、看板unverified/同步pending、CI限制见PR，处理人待指定。

## 四轮迭代交付完成，进入独立审查（2026-11-10 Asia/Shanghai）

Issue247/PR243，Melodydt，in_review（待正式审查/合并，不done）。四轮研究、方案、RTL和旧体系评估已完成；四份PDF均已完成内容和逐页视觉QA，4/4轮完整交付，按轮数上限停止。第四份5页/141内容单元，报告固定f4be5c50507fec202551e45e39fb2215fc18876c，PDF SHA85ae41e4c79712710e078af3f1bcf033d17a8fd35e7896cb90a705b46dc5a741。最终主W8 decode512 ideal 3.67621308212/shared 3.38396291561 token/s，未达5；本次不再增加第五轮。R4采用best R2基础仅op12四EXP lane，默认2，普通N保留；生产启用需BATCH1/DIRECT1/LANES4。R3双buffer退化独立保留，SRAM没有扩容，物理时钟/完整原生生成未验收。

run22/101884源7048c35ed2912e80e62bd7827deaec480d4a7e1a，5:45；run23/101888源e6209544086f2460662bf7edfc91cbfb2c63cd9b，00:02:55；均c64/node1/4核COMPLETED0:0。21build/63run（3预期非法lane拒绝）及11门通过，fee[7,7,7,7,14,14,14,14]；旧模型16case、8精确回归/2fallback、128篡改及原测试通过，独立审计完成。run22结果SHA5abb31227f0c7b2c7ac9ff7eb8f80687569fab0b64bf74eb1a9ea6ccb54b518d，run23结果SHA52c5faaad4d67a30577a5b4bc6d564866627105d492ea37aabc31d5b5b5372ff。

所有源码、日志、结果持久保存在yuzelu@10.129.166.172本人/public/home/yuzelu/Melodydt/issue247-area-speed/run16至run23；全部作业终态，无自动监测。R3/R4共92大raw由retention索引明确服务器/本地归档保存，仓库核验内容和远端索引不混称。扩通道备份task/247-nexp4-area-r4@7048c35ed2912e80e62bd7827deaec480d4a7e1a及R2/R3备份均读回。追踪sacct -j 101884,101888 -X --format=JobID,State,ExitCode,Elapsed,NodeList。

非Git本地快照work/Melodydt/242/r-load-bounds/repo，远端task/242-r-load-bounds供PR243审查，未合并main。恢复第一步核对最新PR head、四轮报告/PDF及正式审查意见；已达到四轮停止条件，不自动增加第五轮。登记management-hub PR5 pending；缺board.json/Projects能力，看板unverified、同步pending，处理管理员/正式审查人待指定；GitHub CI以最终PR回执为准，不冒称通过。

## 第三轮RTL与旧体系评估通过，候选未超第二轮（2026-11-10，Asia/Shanghai）

Issue247/PR243，Melodydt，in_progress。run20/101872（源a3149d69a23f52efb808dbbb46b5558dffce4df7）41秒；run21/101878（源010ae8d0d8839967f96b94227d2224fade0edf37）6:06，均c64/node1/4核COMPLETED0:0。RTL六run×66场景、有限控制299064周期比对及实际S数值通过；模型24case/8精确回归/8fallback、192篡改及原测试通过。R3双buffer主ideal3.66041657326/shared2.75864978939，低于第二轮；当前最快仍3.66958239533/3.37834376557，未到5。

第三轮5页PDF、134内容单元及全部页面视觉QA通过，当前完整交付3/4轮。报告固定809f9820cc13157077e4399a789779aac52925db，PDF SHA00b0b6c2d6c44829808d316cb3e6658c378d8bf51e5cb7632320e790e969940d。大面积候选独立备份task/247-m-k16-area-initial@a3149d69a23f52efb808dbbb46b5558dffce4df7与前态备份均读回；S仍16KiB。run20结果SHA87842b59e42fb0773eedb82dce4981614432868fa12218c3aa15166b0b839eff，run21结果SHAbccd917afba10bb9c3f65f62b26b1eab588a85d73c364a4b4d54962b5197afb8。

服务器本人/public/home/yuzelu/Melodydt/issue247-area-speed/run20、run21持久保存source/、slurm-job.log与results/；62大raw另有retention SHA索引，不声称Git内含所有raw。追踪sacct -j 101872,101878 -X --format=JobID,State,ExitCode,Elapsed,NodeList。全部终态，无自动监测。第四轮在隔离目录实施R2基础op12四EXP lane；1KiB A缓存受DDR上限约束，仅保留方案。恢复第一步核对最新PR head/本轮报告，继续第四轮源审查、Slurm实测和旧体系复评。非Git本地快照work/Melodydt/242/r-load-bounds/repo仅根整合，R4子任务各隔离目录；远端task/242-r-load-bounds未合并main。

登记pending、Projects unverified/同步pending（缺board.json及工具能力）、审查人/管理员待指定；GitHub CI此前失败原因未核实，未绕过。当前候选不具备完整P/DMA、原生整图生成或新物理资格。

## 第二轮RTL与评估通过（2026-11-10，Asia/Shanghai）

Issue247 / PR243，负责人Melodydt，in_progress。R2源码863492081f0f512fc64fb73c787fcdcaf145a6b4，31文件blob读回通过。run18/101852/mdt-r2-nexp-rtl，2:37；run19/101854/mdt-iter2-nexp，2:53；均c64/node1/4核COMPLETED0:0。R2实际费用[7,7,9,9,16,16,18,18]，默认/DIRECT0兼容、数值、持久状态及完整U通过。16旧体系case/8默认精确回归、2prefill fallback、128篡改及profile/CLI负例通过；独立复核完成。

主W8 decode512 ideal3.66958239533（比R1+0.90184%）、shared3.37834376557（+0.83026%）；Dot224.101536667ms占82.2359%，未达5。run18结果SHAfb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78，run19结果SHAb16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098。两run在/public/home/yuzelu/Melodydt/issue247-area-speed/，源码、日志和结果持久保存；追踪`sacct -j 101852,101854 -X --format=JobID,State,ExitCode,Elapsed,NodeList`，查看各目录results/result.json。所有作业终态，无自动监测。

第二轮4页PDF及110内容单元、全部页面视觉QA完成，当前2/4轮完整交付。PDF源文档固定e531a9944ff1ae4bc55e3b6e204be48f425af1a3，PDF SHA1c28b2f2ee7a736b92d4e84308e6a067a6ec761976e78d547310248ac9850a66。第三轮在隔离目录研究/实施S32/S96 M有限供数；正式生产未改R3。恢复第一步核对PR最新head，审查R3真实buffer/nextK/commit/ACK与旧模型收费边界，并在新增大面积候选前创建独立备份。SRAM不扩容；大面积候选另备份。登记pending、看板unverified/同步pending、审查人待指定，未合并main。

2026-11-10，[Issue247/PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)按用户新授权开始[最多四轮RTL提速迭代](experiments/issue-247-speed-iterations.md)，恢复in_progress。主W8 decode512沿旧评价体系，目标5 token/s或满四轮，每轮详细PDF；起点3.230811共享口/3.496169理想端口为条件估计。R1单N批处理与U接入通过服务器RTL/16场景评估，主条件值3.636785、共享口3.350526；首轮5页PDF已通过内容与逐页视觉QA，1/4轮完成；R2单命令relative-exp隔离实施中。SRAM不扩容、备份分支已读回，不继承历史物理资格。

2026-11-10，[Issue247/PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)新增[旧评价体系复评](experiments/issue-247-legacy-metric-evaluation.md)：run15/101800的21场景全历史字段及5生成源SHA一致，旧W8 decode基线3.063655、共享口ctx8 3.230811、理想端口ctx8 3.496169；48/64KiB的4.467001/4.547434属于prefill参考。未修改生产RTL或扩容，不作为原生实测。待独立审查，登记pending、看板unverified/同步pending。

2026-11-09，[Issue247/PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)新增[实施PDF](experiments/pdf/issue-247-p-native-optimizations.pdf)与[新版吞吐核验](experiments/issue-247-native-token-throughput.md)。run12历史重现、run13实际P校准、run14九场景条件模型均通过；W8 decode512条件速率0.06758→0.08174（+20.95%），prefill保持相同。原始S32整图仍被原生准入拒绝，不把条件数值当实际生成；本轮生产RTL不再变更，S不扩容。成果待独立审查，登记pending、看板unverified/同步pending，最终CI以PR回执为准。

2026-11-09，[Issue247/PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)由性能研究进入原生P可选RTL实现：消费者仲裁、固定16KiB四1RW bank并发、八组S64上下文与A复用，两轮服务器回归通过，待独立审查。默认参数关闭新功能；未实装SRAM扩容，未获得新物理或整模型token/s资格。[实施方案、局部收益及短K退化](experiments/issue-247-p-native-optimizations.md)。登记pending，看板unverified/同步pending，CI失败原因待管理员核实；未自合并。

2026-11-08，#214 合并后 U_128/U_64 的普通三源 FMA 入口拒绝和双向 SEND 死锁由 [PR #221](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/221) 修复。两版均通过完整原版 GDS DRC 0、原生 TT 300 MHz 时序、电气/PG及代表上层三档 RC；最终网表 48/48、78/78 次全部通过。交付包及全部 1,389/2,101 个清单文件已本地回收核验。U_64 原生 hold +0.212 ps，只证明当前条件通过；九实例顶层和其他 PVT 不在范围。详见[最终回执](../work/YUZE-LU/212/u-native-fix.md)和[机器索引](../work/YUZE-LU/212/u-native-fix.json)。P 和 C/F/J 未修改，历史 U 功能覆盖不足已更正。用户已授权将 PR #221 并入 main，实际合并状态以在线回执为准；登记 pending，看板 unverified/同步 pending。

2026-11-08，用户授权将母控 [PR #224](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/224) 合入 main，并在[五类 Block 与母控统一入口](experiments/assets/five-leaf-bases/README.md)并列索引源码、图册及双格式验收包。工程证据不变；合并结果以 PR 在线回执为准，授权整合不冒充独立审查或九实例系统验收。

2026-11-08，[Issue #223](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/223) / [PR #224](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/224) 的母控64位后128位工程门均通过。两格式各54项RTL、54项最终母控网表、69项实际Block/局控RTL组合回归；共用同一组六文件，TT300MHz setup/hold +374.917/+7.629ps、原版完整GDS DRC0，电气/RC/PG/SRAM时钟通过。64/128包及3860/3148个内部文件均已本地校验。范围为两驻留目标、有限原生profile；不是九实例联合物理或完整ISA验收，局控PM仍为行为夹具。详见[正式验收报告](experiments/mother-control-dual-format.md)。进入待独立审查阶段，不自合并；登记及看板缺项沿用下方交接。

2026-11-07，[PR #213](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/213) 的 C/F/J `_128` 独立交付保留，C/F 同时发送死锁已由独立 TX 槽修复并通过真实 SRAM 和母控/双局控程序回归。新增 C/F/J `_64` 固定 #180 2a66b918，完整原版 GDS DRC 均为 0；PG、电气、LEC、TT 300 MHz 提取时序及最终网表回放全部通过。三包已回收并逐项核验全部316/273/548文件，工程交付按用户授权随 #213/#214 整合，最终合并回执以 PR 在线状态为准。后制 RC 为研究模型，九实例顶层及跨 PR 控制合同另验。详见[验收索引](../work/YUZE-LU/211/control64-acceptance.json)和[五类两版实际摆放图册](experiments/assets/five-leaf-bases/README.md)。

面向 main 的六块交付：[PR #161](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/161)；已提交待独立审查，尚未合并。R 仍未完成。

## 2026-11-01：六块成果先交付，R 未完成

按用户决定先提交 M/N/E/G/S/T 六块，不等待 R；六块全部适用最终门及源绑定本地实收通过，R 标为未完成且不在合格清单。Issue #143 保持开放，研究 PR #144 保留；当前 `task/143-six-block-main` 基于 main a103da35，面向 main 的成果整合待独立审查。规格和结果见 docs/BLOCK_V2.md、docs/BLOCK_V2_RESULTS.md；核验命令见 docs/ARCHITECTURE.md。登记 PR5 pending；缺 config/board.json，看板 unverified/同步 pending；审查人待指定。历史记录保留在下方。

- 更新日期：2026-10-30（中国标准时间；本次只更新共同文档规划，不重跑物理实验）
- 当前规划补记：[Issue #139](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/139) 记录 M＋V 三宏（归约与归一化、基础向量算术、激活与门控）＋独立 R＋S＋T，详见[决策 0005](decisions/0005-compute-block-v-split-r.md)。各种先一个实现，逐宏交付最终布局布线；新三宏尚待实现、具体规格仍待验证，原 V 结果不转移资格。现有 #121/#130 实验保留，阵列/多实例/裕量版本/预连后移；本次未改变原实施任务状态或服务器作业。
- 当前阶段：首轮 Block 实现与表征推进；共同底座和任务定制分阶段验证。具体实现状态以 [Issue #121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) / [PR #122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122) 为准；历史 H1/H2 证据保留如下。
- 本次共同文档澄清：[Issue #123](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/123) 记录[当前实施边界与分阶段冻结](decisions/0004-block-library-base-freeze.md)：首轮叶块不要求同时确定多实例、不同裕量物理版本组合或预连拓扑；这些在共同底座阶段确定并统一冻结。原实施任务的多阶段范围和验收状态不因此缩减。
- 历史 H1 工程：[Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15) 已完成openTPU ACT/MXU同功能／资源的块内及父层对照。三块和两父层、六类证明共十一份封存来源严格通过；拆分叶面积+0.412%、总信号线+7.142%、通孔+2.974%，完整setup／hold两组均满足2.5ns／0.5ns预算。[中文结果与三类图表](experiments/issue-15-opentpu-results.html)已生成并目视核验，详见[实验记录](experiments/issue-15-opentpu-comparison.md)。独立全量重布线21亦已自然完成并通过十一项来源／证明对照；本次整合不启动、终止或改写既有远程作业。
- 资料接入：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)；资料已进入 `main`，[PR #2](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/2) 已合并
- 当前资料：项目说明 v1.0（含 2026-10-30 架构规划补记）、专题研究文档、来源笔记，以及五个参考项目七个案例的布线分析包；三份 HTML 报告、llaccel 引擎内部分析及远程服务器规则已通过 [PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4) 合入 `main`；工艺互连资料的逐层资源评估补充已一并提交
- 已确认边界：第一版采用 Nangate45 原生 M1–M10、via1–via9 预制，新增研究 M11/M12、via10/via11 后定制；叶块冻结与共同底座冻结分别验收。技术模型、完整宏、共同底座及多产品结果须按实际证据接收，不能将本次文档更新视为实现完成。
- 关键限制：现有布线结果包含少量 RTL 片段，不含完整源工程、物理数据库、工具环境和日志，不能单靠本仓库复跑物理实现
- 历史 H1 工程里程碑（2026-10-23 04:37 CST）：拆分89829自然完成全部严格物理、PG及完整STA，功能89831／RC覆盖89832／五个完整ODB成本复核89833也全部通过。快照f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d，主对照不随实时采集变化。全量DRT21／89826及功能89827／覆盖89828／完整ODB89835也全部自然通过；补充快照独立保存，不改写主报告。全部作业UNLIMITED，无耗时取消。
- 整合交付：PR #8、#10 已合入 main，H1 完整整合树通过本地核验并由 PR #17 交付，其最终 CI／合并状态以在线记录为准。后续 H2 由[Issue #31](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/31)独立推进，本次不修改其工作树或运行任务。项目登记及看板权限仍待管理员处理，详见[整合回执](handoffs/2026-10-23-h1-html-integration.md)。

- 首轮结果：完整 VECTOR 已完成详细布线并导出最终寄生／宏模型，DRT错误0；3 ns setup及电容检查未通过。修复宏PG接入后，89472完整顶层 `COMPLETED 0:0`，DRT错误0、最终双网PSM和2246位接口检查通过，89475最终只读审计通过；父级仍有3个setup违例。历次失败保留，这些工程结果不构成合格硬核或系统签核
- 任务入口：[本仓库 Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues)
- 项目登记：[管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待审查；合并前状态为 pending
- Projects 入口：候选[组织看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1)；本轮查询因缺少 `read:project` 失败，且无 `config/board.json`，实际看板与条目 `unverified`、同步 `pending`。恢复动作见 [Issue #7 看板交接](handoffs/2026-10-21-issue-7-projects.md)

本页只记录全项目阶段和关键限制；具体任务进度以 Issue 和 PR 为准。
