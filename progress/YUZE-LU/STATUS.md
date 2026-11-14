# YUZE-LU 的进度

## 2026-11-14（CST）ATT1 局部 SRAM 流水对照

[PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 增加候选 TLM 的 ATT1 SRAM 回填和取数流水。前七层 decode 的 Attention 页合计 27.367→19.104 ms，母控指令、局控调用、DDR 与 SRAM 访问量一致。候选作业 112069/112070 运行两步 decode 和短 prefill，112116/112117 待两组完成后核对吞吐。硬件实现及正式 P512/D128 仍待验收。 [配置与对照](../../work/YUZE-LU/234/AV_WEIGHT_EXPERIMENT.md#att1-的-sram-请求流水)

## 2026-11-14（CST）短程吞吐回执与复现入口

[PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 补充[配置化回放入口](../../project/experiments/systemc_benchmark/README.md)和[从 0.957 tok/s 起的瓶颈分析与证据](../../work/YUZE-LU/234/native-sram-width/PERFORMANCE_ANALYSIS.md)。[内存流水对照](../../work/YUZE-LU/234/MEMORY_PIPELINE_EXPERIMENT.md)已通过 Attention 双写在途组件回归，512-bit 的两步 decode 和短 prefill 已完成 TLM 对照审计，分别为 2.3390 和 5.5065 tok/s。V 复用待测。宽口 RTL、300 MHz 物理时序及正式 P512/D128 联合验收仍待完成。Issue #234 继续进行，审查人待指定，看板同步待核验。

## 2026-11-13（CST）指令驱动的吞吐评估

[Issue #234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234) 的 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 已补入[事务级回放、短程吞吐审计和复现命令](../../project/experiments/systemc_benchmark/README.md)。下一步核对短程实验回执并校准宽口 RTL。正式 P512/D128 联合验收仍在进行。看板配置待核验。

## 2026-11-12（CST）Qwen2.5-3B 整机吞吐交接

[Issue #234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234) 仍在执行，后续接手人待指定。[实施与验收交接](../../docs/handoffs/2026-11-12-issue-234-whole-system-throughput.md)记录远程作业 101602、103217、103220，以及真实控制、算子、SRAM 和 DDR 联合仿真的待接通路径。整机吞吐和能耗未验收。

## 2026-11-08（CST）U 原生入口和双向发送修复

[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) → `in_review`；[PR #221](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/221) 待独立审查。独立 TX 槽和普通三源入口修复后，两版重新综合并通过完整原版 GDS DRC 0、TT 300 MHz、电气/PG及三档代表上层 RC。U_128 setup/hold +255.014/+14.595 ps，U_64 +73.082/+0.212 ps；最终网表 48/48、78/78 全部通过。两包及全部 1,389/2,101 文件回收核验成功，31 硬件源文件与审查代码一致。[最终回执](../../work/YUZE-LU/212/u-native-fix.md)。P 不变。用户已授权将 #221 合入 main；五类图册 U 两版已绑定新验收包，P/C/F/J 图源不变。实际合并状态以 PR 在线回执为准，Issue 在线 assignee 未指定。登记 PR5 pending，缺 board 配置，Projects unverified/同步 pending，复用接入交接 Issue7。

2026-11-08 CST：用户已授权将 #223 / PR #224 母控双格式交付合入 main。新增五类 Block 与母控的[统一索引](../../docs/experiments/assets/five-leaf-bases/README.md)，原目录及交付散列保持不变。合并状态以 PR 回执为准；独立审查未代批，登记/看板缺项继续由 Issue #7 交接。

## 2026-11-08（CST）母控物理实现

更新时间：2026-11-08 CST。[Issue #223](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/223) / [PR #224](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/224) 已完成先64后128的工程验收，待独立审查。两格式各54项RTL、54项母控最终网表、69项实际Block/局控RTL回归；共用未改物理六文件，TT300MHz setup/hold +374.917/+7.629ps、完整原版GDS DRC0，电气/RC/PG/SRAM时钟通过。U绑定#221已验收31文件源。两包及3860/3148内部文件本地全部核验，见[报告](../../docs/experiments/mother-control-dual-format.md)与[执行记录](../../work/YUZE-LU/223/README.md)。下一步：指定独立审查人、审查PR；九目标扩展和联合布局布线另验。本任务未自行合并或标done；登记PR5 pending，缺board配置，Projects unverified/同步pending，待管理员核验。


## 2026-11-07（CST）C/F/J 独立叶宏组

更新时间：2026-11-07 21:40 +0800。

[Issue #211](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/211) · [PR #213](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/213) · [验收与回收索引](../../work/YUZE-LU/211/control64-acceptance.json)。C/F/J 独立紧凑叶宏、16 KiB 私有 S、局控与适配已交付；C/F 并发发送死锁修复并通过真实 SRAM 与双局控程序。原 `_128` 包保留，新增 `_64` 三类全部通过原版完整 GDS DRC 0、PG、电气、LEC、TT 300 MHz 及最终网表回放，本地包与316/273/548个内部文件全部核验。五类 _128/_64 摆放图及图源绑定已保存，用户已授权通过 #213/#214 主线整合，合并回执以 PR 在线状态为准；联合顶层重新绑定局控 ID、控制 profile 和实际布局并独立验收。审查人待指定；登记 PR5 pending，缺 board 配置，Projects unverified/同步 pending，待管理员处理。

## 2026-11-07 17:10（CST）P/U 紧凑指令物理版本

[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) · [PR #214](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/214)。已有合格交付保留为 P_128/U_128。P_64/U_64 均完成独立物理验收：完整原版 GDS DRC 0，原生 TT 300 MHz setup/hold 分别 +86.461/+7.498 ps、+100.376/+8.670 ps，电气/PG、信号路由、代表上层三档 RC、最终网表 9/60 次程序回归通过。两包已回收到本地，1122/1480 个清单文件和程序镜像逐项校验一致。[最终版本回执](../../work/YUZE-LU/212/compact64-physical.md)。64 指紧凑取指，PM/数据接口仍 128 位，控制仍是记录的原生服务子集。下一步独立审查和合并；Issue in_review，不自合并。登记 PR #5 pending；看板缺配置，字段 unverified、同步 pending。

## 2026-11-07 13:03（CST）P/U 独立叶宏底座

[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) · [PR #214](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/214) · [工程回执](../../work/YUZE-LU/212/README.md)。E 操作数个数 P1 已修复，[新 U 物理重验收](../../work/YUZE-LU/212/u-e-count-physical.md)通过：完整原版 GDS DRC 0，TT 300 MHz setup/hold +334.870/+3.787 ps，电气、信号和 PG 通过；130 根代表上层接入三档 RC 通过。正常/FMA 两套最终网表测试共 30 次通过。新包及 82 个清单文件已回收校验，取代旧 U 交付包。P 原包保留，新回放入口对原 P 网表三初态通过。下一步独立审查和合并；登记待合并，看板缺配置。

## 2026-11-06（CST）紧凑 SRAM S 版图图册

[Issue #207](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/207)由 YUZE-LU 执行。从 #203 最终验收产物补齐两颗 SRAM 的[版图、摆放和 M10 引脚图册](../../docs/experiments/assets/compact-local-s/index.html)，逐个比对 273／965 根引脚坐标。由 [PR #209](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/209) 交付。看板配置仍待管理员核验。

## 2026-11-06 G/E 独立宏紧凑化

[Issue #201](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/201) · [PR #205](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/205) · [源提交与作业回执](../../work/YUZE-LU/201/README.md)。G 220 µm 和单输入 E 340 µm 已通过独立叶宏全部工程门，完整交付归档回收并核对。父层互连与组合时序另验收。

[Issue #208](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/208)补齐[图册与接点坐标](../../docs/experiments/assets/compact-ge/index.html)，已核对图源、接点数及本地图册链接。

## 2026-11-06 紧凑双型局部 SRAM S

[Issue #200](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/200)由 YUZE-LU 执行。两个 16 KiB 独立宏完成详细布线和 273/965 位同时逃逸测试，实际有效占地为 82.45% 和 82.11%。结果、原生独立验收范围和复跑入口见[实验说明](../../project/experiments/compact_local_s/README.md)。[PR #203](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/203) 已合并。两颗的完整 GDS DRC 均为 0，TT 300 MHz 独立审计、选定 ODB 的三初态回归和四 bank 等价均通过。看板缺项目配置，登记沿用待合并的管理中心 PR #5。

## 2026-11-05 局部 SRAM S 交付

[Issue #155](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/155)的后续整合，执行账号 YUZE-LU。P4/N4/N5 的 300 MHz 独立叶宏验收、版图、六文件索引和 RTL 回归入口见[局部 SRAM S](../../docs/BLOCK_LOCAL_S_SRAM.md)。系统级接入单独验收。看板配置和同步由项目管理员核验。

## 2026-11-01：Issue143 六块成果进入整合审查

按用户决定先提交 M/N/E/G/S/T 六块，不等待 R；六块全部适用最终门及源绑定本地实收通过，R 标为未完成且不在合格清单。Issue #143 保持开放，研究 PR #144 保留；当前 `task/143-six-block-main` 基于 main a103da35，面向 main 的成果整合待独立审查。规格和结果见 docs/BLOCK_V2.md、docs/BLOCK_V2_RESULTS.md；核验命令见 docs/ARCHITECTURE.md。登记 PR5 pending；缺 config/board.json，看板 unverified/同步 pending；审查人待指定。历史记录保留在下方。

## 2026-10-30 计算积木规划文档同步

- 更新时间：2026-10-30（Asia/Shanghai）。任务：[Issue #139](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/139)，负责人/实际身份 YUZE-LU；独立分支 `task/139-compute-block-docs`，基于 main `6a681d66`。
- 已完成：原本地 V/M 分析重命名为 MVR 讨论总结，加入 R 的结构、数值、状态容量/共享存储、四抽头限制及首版独立保留结论；仓库[同文正文](../../docs/COMPUTE_BLOCK_BOUNDARIES_2026-10-30.md)。
- 同步：[项目说明](../../预制计算底座项目说明_v1.0.md)和 README/导读/简介/架构/状态；[决策 0005](../../docs/decisions/0005-compute-block-v-split-r.md)记录 V 三宏、R 保留、每种一个实现、逐宏最终布局布线。M/V 缩位宽和部分和精简仍为候选，未转移原 V 的物理资格。
- 验证：[本次交付记录](../../work/YUZE-LU/139/README.md)及 validation.json；仅文档/管理检查，未重跑模型、RTL、EDA 或服务器作业，未修改现有实现工作树。
- PR/最终提交与 CI 以 Issue #139 回执为准；待独立审查，不自合并或标 done。登记沿用 PR5 pending；缺 board.json 与 Projects 条目工具，看板 unverified/同步 pending，管理员待指定。
- 续补：已有 M/V/R/S/T 的电路图、存储、控制与固定源码来源已直接加入总项目说明第 5.6 节；规划中的新 V 三宏不画图，本次不新建 Block 说明文件。
- 交付：[PR #142](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/142)。用户本轮明确要求同步 main，将在检查后正常合并并读回；不代替他人审查或绕过保护。具体最终合并回执以 Issue #139 为准；主线另行落实逐宏物理验收，本次不接管运行任务。

## 2026-10-26 模型分析与计算图归档

- 更新时间：2026-10-27 14:25 CST，用户已明确授权提交到 main。
- 任务：[Issue #116](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/116)，负责人及实际账号 YUZE-LU；分支 `task/116-model-analysis-docs`。
- 本地成果：[模型分析目录](../../docs/model-analysis/README.md)，集中提供精简字符算子图、完整图册和原 PR #115 的实验分析报告；旧报告路径保留跳转，README 与导读更新入口。
- 原始图册、图结构、配置和回执按 SHA 原样复制；新说明明确 Falcon 旧手工图的已知差异。没有重新运行模型/ONNX、修改历史 Issue #114 的证据或接触服务器作业。
- 验证与导入清单：[work116](../../work/YUZE-LU/116/README.md)。本轮重验183份导入文件、196处本地引用、40张SVG、10组成功回执及原报告正文迁移均通过；正在通过任务分支和PR交付，实际PR/CI/合并回执保存在Issue #116，未合并前不标done。未重跑模型或物理实验。
- 接入：无 `config/board.json`，连接器未提供 Projects 条目能力，条目未核实、同步 pending；管理员待指定。现有登记和项目里程碑不变。

## 2026-10-27 共同文档阶段边界澄清

- 任务：[Issue #123](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/123)，负责人及实际账号 YUZE-LU。
- 成果：[决策 0004](../../docs/decisions/0004-block-library-base-freeze.md)，同步 README、项目简介、项目说明和共同状态。
- 已确认：Nangate45 原生十层预制与新增两层定制；叶块、共同底座与任务定制分别验收。同类实例/裕量版本组合、排布和固定预连线在底座阶段确定；共同底座冻结后不得按任务改变固定资源。
- 边界：保留 Issue #121 / PR #122 的既有范围与验收状态；本次没有修改实现工作树、RTL、实验配置或服务器任务。
- 验证与集成：[PR #124](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/124) 交付本次澄清；管理结构、44 处本地链接、3 张表格及暂存差分检查通过，PR CI/最终合并以 Issue #123 的读回回执为准。用户明确授权经 PR 正常合入 main，不代替独立审查或绕过保护。
- 接入：本次读回既有登记 management-hub PR #5 仍 open/未合并（pending）；无 config/board.json，当前工具无 Projects 能力，条目/字段 unverified、同步 pending，管理员待指定。此缺项不改变文档业务验收。
- 下一步：完成文档检查、PR/CI 与 main 内容读回；后续物理实现继续由原任务跟踪。

## 2026-10-26 模型实验分析报告

- 任务：[Issue #114](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/114)，负责人及实际账号 YUZE-LU。
- 成果：[阶段性分析报告](../../docs/model-analysis/MODEL_EXPERIMENT_ANALYSIS.md)，补充 README 与研究资料导读入口；来源与检查见 [work114](../../work/YUZE-LU/114/README.md)。
- 已完成：读取九份固定版本报告及十个来源 PR 的状态，梳理八个模型的目的、范围、结果、失败和能力/接口约束；读取后续 #102/#106/#109/#110 的范围，避免将旧批次限制误写为当前无 RTL。
- 集成：用户明确要求合入 main；本次通过独立文档 PR 交付，最终 PR/commit/CI 以 Issue #114 的读回回执为准。不合并其他实验 PR，不冒充独立审查批准。
- 验证：文档检查与管理结构的实际结果见 validation.json；未重跑模型、原始数值接收、RTL 或物理。
- 接入：登记 management-hub PR5 仍 pending；无 board.json，实际 Projects 查询缺 read:project，看板 unverified、同步 pending，管理员待指定。
- 下一步：完成当前文档检查、PR/CI 及按本次授权入 main 的读回；原实验审查和后续实现另按原任务推进。

## 历史阶段：Issue #7（2026-10-21）

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- Issue：[候选 Block 边界及分层布线流程](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU，当前 `in_review`；审查人和优先级待指定。
- 已完成：读取两个项目的接口／RTL／报告和已有 ACT—MXU 实验；形成 [候选划分及对照矩阵](../../docs/experiments/openTPU-llaccel-block-plan.md)；核实用户授权的集群工程与工具可访问；在独立分支 `task/7-block-routing` 增加正式实验运行器，原参考包和原工作区改动保留。
- 实验：完整16-lane VECTOR的screening 89442通过；早期89443人工时限超时及89447恢复预检查失败保留。89448从checkpoint进入stage4、不重综合，仍在默认LEC、未得CTS完成产物，继续 `UNLIMITED`。89449因旧默认PDN已知不兼容，在确认PENDING后取消，非按求解耗时终止48。终态以[试验记录](../../docs/experiments/issue-7-vector-pilot.md)和[轻量索引](../../project/experiments/block_hierarchy/results/issue-7.json)为准。
- 运行约束：用户明确要求不设时限；后续作业取消人工有限时长，实读 c64/c96 `MaxTime=UNLIMITED`，每次提交后核验实际 `TimeLimit`。早期超时与恢复预检查失败保留，不通过删除历史制造成功。
- 新增验证：独立RTL回归89455通过，VECTOR 1203例／数学12000组／舍入16384组；测试副本唯一 `1u << 31` 兼容修正有diff/hash，原RTL与参考不改。89453及后续顶层是另开的 `LEC_CHECK=0` 物理路线，89448默认检查路线保持运行，不混用二者证明。
- 实际物理结果：89453完整Block和89472单宏顶层均完成最终布线，DRT错误0；89475最终只读审计通过，双网连通、唯一固定宏／2246位接口与逐位映射、M7–M9接入几何复算闭合。Block setup WS −4.16659 ns／287违例、最大电容59违例；父级setup WS −0.0429892 ns／3违例，质量仍未通过。父层新增2245个IO buffer，single-sink实际跳过CTS，无多宏时钟树验证。历史PG／hook失败均保留。
- 验证：`python scripts/check_project.py`、Python 脚本语法编译、远程 Bash 语法检查和 `git diff --check` 通过；镜像阶段门级 LEC 已调用、尚未得结论。完整 core 回归、原 RTL 到物理网表的完整形式比较、多计算图、受限定制和系统签核未执行。
- 下一步：审查本轮工程实现和失败证据，保留内部／父级时序、电容、异步复位抽象和缺少宏功耗模型的限制；再准备同资源F0/H1对照、多Block和H2冻结资源规则。89448继续无限时求解，其后续匹配模型必须来自其自身最终实现，不套用89453模型。
- PR：[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)供审查；89472／89475实际运行代码快照 `357dd98a7a07f370a1cc2c67b066c7ecccf3bf9a`，75启动时仅文档／结果dirty并如实记录。最终采集器精简及成果记录由PR当前HEAD回执绑定；每个attempt的SHA-256独立保存，未合并或验收前不标 `done`。
- 接入：管理中心 [登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 本轮读回仍 `OPEN`，登记 `pending`；Projects 缺 `read:project`，无 `config/board.json`，看板 `unverified`、同步 `pending`，由具备权限的管理员处理（待指定），见[持久交接](../../docs/handoffs/2026-10-21-issue-7-projects.md)。




## 2026-10-22 ACT/MXU 同资源物理对照

- 更新时间：2026-10-23 04:37 CST，中国标准时间UTC+08:00；负责人／实际GitHub账号YUZE-LU。
- [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)，分支`task/15-opentpu-compare`，[PR #17](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17)，依赖PR10基线2b76f69；独立工作树，未修改PR8／PR10工作树、VECTOR或89448。
- 已完成：三种块内实现与拆分两宏／合并一宏父层实际布局布线。保持169109初始映射单元、37023DFF、12个SRAM及相同计算／状态逻辑；统一1662bit外部引脚、die、2.5ns时钟及0.5ns IO预算，全部物理支持成本计入。拆分89829／34:01自然COMPLETED0，五个物理来源和六类证明共十一份记录全部通过compare；功能89831、覆盖89832、完整ODB89833通过。旧20的act_data[145] slew违例经单一驱动X4→X8并重新DRT／提取消除，没有放宽门槛。
- 实测：拆分／合并总叶面积484240.4／482252.4µm²，总信号线6647739／6204600µm，通孔1322289／1284106，完整setup WNS +0.102306／+0.065642ns、hold +0.036146／+0.013027ns。拆分块内线长−249953µm，被父层+693092µm抵消；总线长+7.142%，不能将父层IO／时钟全归为685bit边界成本。
- 成果：[中文HTML和三类图表](../../docs/experiments/issue-15-opentpu-results.html)，[过程及失败证据](../../docs/experiments/issue-15-opentpu-comparison.md)。生成代码8a646d8，冻结输入SHA f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d；report-manifest绑定9个产物。实际查看三PNG、浏览器核验页面／表格／三图／路径和完整ODB展开，临时页面服务已关闭。delivery-validation记录实际检查和两个成本证明负例，均拒绝且未改变合格输出。
- 补充已完成：全量清线重布21／89826自然COMPLETED0（1:02:26），匹配功能89827／RC89828／五ODB成本89835全通过；另存完整十一来源对照，快照72b9829d0df7ac7d30c5b7a6f8e602f11e317c2070cbacab4f55e466299cce0f。与主拆分叶面积相同，总线长多42µm、通孔少2、setup多0.000008ns；原主报告和9产物SHA不变，不能当作显著改善。两套合计15份唯一封存来源全部自然完成、UNLIMITED。Issue in_review、PR17待独立审查。
- 限制：H1允许新增有源缓冲和全父层路由，M10以下父层线长占比约99.39%／99.26%，不代表H2少量定制层冻结底座；单small／typical／固定布局与引脚，synthetic SRAM无GDS、上游RTL通用等价和制造签核未完成。
- 下一步：PR独立审查／合并及最终验收由人处理，审查人待指定。不自合并或标done；审查人／优先级待指定。H2预算及限定制层是后续独立实验。
- 接入：登记管理中心PR5本次核验仍OPEN未合并、pending；本仓库无board.json，连接器无Projects条目工具、CLI实际GraphQL查询返回INSUFFICIENT_SCOPES缺read:project，看板unverified、同步pending，管理员待指定。

## 历史记录：2026-10-21 资料与规则交付


- 更新时间：2026-10-21（中国标准时间，UTC+08:00）
- 当前任务：[Issue #3：同步两份布线报告并补入 llaccel 引擎分析](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3)。负责人 YUZE-LU，优先级待指定。
- 已完成：同步最新总报告、线长报告及其引用资源；总报告增加 llaccel 三个引擎的中文分析与 9 张图。保持图片直接展示、长表可展开；不创建备份或多余首页。更新来源边界和包说明。
- 验证：管理结构检查、报告依赖/锚点检查、包内清单哈希、正文/表格保留和差异检查；具体结果见本任务 PR 回执与 `work/YUZE-LU/3/validation.json`。没有重跑物理实现或 STA。
- 交付：[PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4)，分支 `task/3-update-routing-reports`，报告成果 commit `b041d53`；2026-10-21 按用户明确要求已合并到 main，合并提交 `1d80491`。
- 下一步：继续审查[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)。登记仍为 pending。
- 阻塞/接入缺项：报告上传可独立完成；本仓库没有看板配置，当前凭据缺少 `read:project`，无法核验或同步 Projects。由有相应权限的管理员处理，处理人待指定；详见[交接](../../docs/handoffs/2026-10-20-issue-3-report-board.md)。不自行扩大凭据权限。
- 历史：Issue #1 的初期资料由 PR #2 导入，后续参考资料提交 `695587d`、`5c86109` 已进入 main。`ref-project/` 仍不属于 Agent 主动或例行维护范围。

## 2026-10-21 补充交付

- 按用户要求补入 `ref-project/llm-routing/模块与接口报告.html`，保留原文，并复制其引用资源；README、研究资料导读及阅读说明补充入口。
- 本次仅检查新报告的本地引用是否存在及管理结构、文档差异；不执行哈希检查，不重算参考数据，不修改原有清单。原清单不覆盖此次新增文件。
- 沿用 Issue #3、任务分支及 PR #4 上传；2026-10-21 已按用户要求合并到 main。看板权限缺项沿用上述交接。

## 2026-10-21 远程服务器规则

- [Issue #9](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/9)：记录服务器节点、`/public/home/yuzelu` 下的目录权限和 sbatch 任务命名要求，README、AGENTS.md 提供规则入口。
- 任务名采用“本人姓名缩写-任务缩写”，如 `hpy-block`；脚本和提交时覆盖的任务名均应遵守，便于在 squeue 的 NAME 中辨认。
- 验证：管理结构检查及所改文档的差异检查通过；未登录或修改远程服务器。通过 PR #4 上传，2026-10-21 已按用户要求合并到 main；看板同步仍待具备权限的管理员处理。

## 2026-10-21 main 集成

- 按用户“最新状态都提交到 main”的明确要求，将报告、远程规则及此前未提交的工艺互连资料补充一并纳入 PR #4 并合并。合并提交 `1d804912927602900aa074339db33156a805c582`；本地已同步到 main。
- 管理结构及文档差异检查通过；未重算参考数据。其他成员的独立 PR 未合并。登记、看板的既有待办继续保留，不宣称已完成。

## 历史记录：2026-10-19

- 更新时间：2026-10-19（中国标准时间，UTC+08:00）
- 当前任务：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)
- 已完成：初期研究资料已进入 `main`；PR #2 已合并。本次按用户要求直接在 `main` 提交并推送更新后的研究资料导读与用户提供的 `ref-project/` 改动；成果提交为 `695587d`、`5c86109`。
- 下一步：完成[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 的审查；由具备 Projects 权限的管理员核验或配置项目看板。`ref-project/` 不纳入 Agent 的主动或例行维护，用户更新后可按要求提交；无需逐项审查或做哈希检查。
- 阻塞：物理实现原始代码、数据库与工具环境未包含在当前资料包；共享存储位置和实际可访问性待核实。
- 本次验证：`python scripts/check_project.py` 通过；导读的 6 个本地相对链接存在；变更文档的 `git diff --check` 通过。未检查参考包内部改动或哈希，未执行业务构建／仿真。本地未配置 `config/board.json`，看板仍待管理员处理。

## 2026-10-23 布局与接口报告本地归档

- 按用户要求，沿用 Issue #7 并发工作树 `issue-7-parallel-blocks` / 分支 `task/7-parallel-blocks`，将两份报告集中到 `ref-project/llm-routing/docs/`，并修正相对资源 URL 与 README、资料导读、阅读说明中的入口。详见[报告目录说明](../../ref-project/llm-routing/docs/README.md)。
- 已核验移动前 56 个不同本地资源 URL 均存在；移动只调整 URL，报告正文和标签结构保持不变。新 Block 报告从外部生成产物原样复制，保留源文件。项目管理结构检查通过；未重跑 EDA。
- 交付状态：仅本地文件整理，尚未 commit / 推送，现有 PR #10 尚不包含此修改；Issue 状态、项目里程碑及看板未变。登记/看板缺项沿用原任务交接。下一步可按用户后续提交要求并入现有 PR，不能把本地归档视为已合入 main。

## 2026-10-23 按用户授权整合实验与 HTML

- 用户明确授权完成 PR #8、#10、#17 及两份 HTML 的提交与合并；H2（Issue #31）继续独立运行。HTML 的来源和范围不变，先前“仅本地”的记录为归档时快照。
- 本次技术复核：H1 主/补充对照从现有封存记录重算，全部成本与质量字段一致；9 个报告产物 SHA 未改变。缺少成本审计、错源审计两负例均拒绝；并发电气门槛、Tcl 修复与配置覆盖回归通过。不是新跑 EDA 或上游 RTL 通用等价证明。
- 合并权限来自本次用户明确指令；不冒充独立 GitHub APPROVED 审查，不绕过保护规则。登记 PR5 仍 pending；看板实读缺 read:project，unverified / 同步 pending。

## 2026-10-23 用户授权整合

用户明确授权将主线PR #8、并发PR #10及H1 PR #17合入main，并将两份参考HTML归档到ref-project/llm-routing/docs/。以上旧记录中的待授权／不自合并描述是当时状态，本次按用户的新授权执行，不伪造独立审查批准。H2工作树及运行任务保持独立。本次验证与限制见[整合回执](../../docs/handoffs/2026-10-23-h1-html-integration.md)。

网络恢复续办：PR #8 已合并为 a30d598，PR #10 已按匹配 head 成功合并为 a77d288；完整 H1 整合树由 PR #17 交付，最新 CI 和合并状态以在线记录为准。本地 8 项检查、58 份 Python 语法、两份 HTML 资源／锚点及 9 产物不变检查通过。Issue #7 的 VECTOR 质量缺口保留；H1 交付与 H2／Issue #31 分开，项目登记及看板待办不变。
