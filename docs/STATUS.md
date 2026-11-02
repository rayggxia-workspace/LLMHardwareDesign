# Issue162：S交接四门通过，继续完整组合验收（2026-11-02 12:55 CST）

[Checkpoint06](../work/YUZE-LU/162/continuation-checkpoint-06.md)：新S适配器四门及六文件/版图已完成；20种26实例零上层RC诊断setup +0.039856ns，但尚未取得完整组合资格。node25已实际6×16动态补位；固定PG、fresh RC、最终网表组合与新边界全图布线继续。R保留并由正在修改它的任务负责，当前组合尚缺R适配。Issue162 in_progress，PR163 Draft，未合并。

# 组合失败定位与修复候选（2026-11-02 12:00 CST）

Issue [162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / PR [163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，继续实现，未合并、未完成系统验收。main 六宏原始源未改，R保留且正在修改；当前已测组合尚未接入R，后续正常适配。

[Checkpoint 05](../work/YUZE-LU/162/continuation-checkpoint-05.md)

## Issue162 续接实际进展（2026-11-02 10:10 CST）

任务 [#162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，仍为 in_progress / Draft，未完成系统验收，未自行合并。

- main 基线4b1df2c7的M/N/E/G/S/T源保持不变；R保留且正在修改；当前已测组合尚未接入R，后续正常适配。
- 新增13种叶块已有300MHz最终四门与六文件：C、端点队列、AXI-Lite、D、六个适配器、固定路由、S仲裁器、错误状态块。D d-07全门通过：setup +68.936ps、hold +6.663ps；新增status-01 setup +2082.473ps、hold +15.248ps。原失败候选保留。
- status补齐顶层错误汇总的物理归属：protocol_error同步采样并sticky到系统复位。完整拓扑检查通过，19种块、25实例、6853条有效网络、无未归属活动逻辑和常量输入连接。
- 当前真实RTL三组合system-07三初态各485893项检查/152836周期、CPU张量搬运0。八模型C轨迹三初态各236222检查/129364周期；使用oracle完成包，仅验证控制容量及阶段调度，不能代替端点数值或整模型验证，Qwen3.5/Falcon的R路径仍拒绝。
- C与队列的70线M11/M12实际接入六候选全部通过ODB/DEF/GDS读回、native XOR及研究规则检查，仍不代表整个组合时序。50份原始证据及逐文件SHA见work/YUZE-LU/162/continuation-proof-03/；status六文件与门绑定见status-qualification/。
- 18块旧拓扑最终网表组合94992/node26、当前19块最终网表组合95001/node25仍编译；两者都未宣布通过。原始全单元视图和SPEF继续复用，不以RTL替代最终网表。
- 全图布线24个参数/排布候选经95020完整预检通过后，95021～95026运行在node2～7。c96可用节点均已分配，因此在空闲c64按每节点4×16动态补位（64核硬件上限），加node25/26共8个本任务节点；每槽32GiB初始预算、1.2裕量及16GiB守卫有实际MemAvailable回执。此前启动器参数引用、缺少native尺寸字段的失败保留，未授予资格；尺寸现来自实际DEF及SHA。
- 必须继续完成：全图实际几何读回、完整组合RC/300MHz/电气、时钟复位与PG、严格组合等价、交付六文件和源绑定索引。物理预检发现M的PG只至M7，不能将M10信号接入当作完整供电接入；固定PG接入尚待完成。既有新增M11/M12模型是明确未校准的研究模型，不冒充制造签核。

规则rayggxia-project-collab1.0.0；登记management-hub PR5 pending；无board.json/Projects条目能力，条目unverified、同步pending、处理人待指定。管理结构检查通过不替代业务验收。

# 当前状态

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
