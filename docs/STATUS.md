# 当前状态

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 的六模型能耗扩测已全部完成工件迁移。Granite 三窗通过冻结输出及 DDR/SRAM 对账，迁移分项估算与本地复算一致；其余五模型在 BSCC 不限时回放。结果、缺项和逐模型 PDF 更新见[扩测交接](handoffs/2026-11-17-issue-280-six-model-energy.md)。

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已完成 Qwen3 三窗的 TLM 分项能耗 v1，补入四个局控描述符静默基线并单列读 DMA 动态敏感性。读 DMA 下一步以 300 MHz 综合映射网表直接估功耗，九目标母控和整机物理归属仍待补。[结果和接续](handoffs/2026-11-17-issue-280-qwen3-tlm-power-v1.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成局控 PM 驻留静默、局控描述符取指 300 MHz 标定及 C639 共同时钟核验。Qwen3 参考小计补三类开钟空闲。读 DMA 待物理输出，九目标母控外围需匹配工件。[控制进展与接续](handoffs/2026-11-17-issue-280-qwen3-control-power-progress.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已按真实 PM 页类与四站点 TLM 次数生成 Qwen3 SRAM／母控 PM 三窗参考小计，两种 SRAM 配置保留固定时长情景。实际部署与开钟驻留待核对，读 DMA 仍待物理输出。[三窗数据与复现](handoffs/2026-11-17-issue-280-qwen3-macro-window-reference.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已完成 S_P／S_base 后布线 SRAM 等长配对功耗，以及母控三档真实页的四宏标定。三套 300 MHz 物理预检通过，下一步按实际实例和驻留积分到 Qwen3 三窗，读 DMA 仍待物理结果。[标定回执](handoffs/2026-11-17-issue-280-sram-mother-pm-calibration.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已恢复旧归档访问。S128 bank、S_P／S_base 后布线和母控 PM 归档原件在 BSCC 解包并通过散列与网表实例核对，待结合实际活动执行功耗标定。[恢复回执](handoffs/2026-11-17-issue-280-macro-views-recovered.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 将真实载荷写 DMA 与 U ADD2 增量并入 Qwen3 三窗小计，完成旧版 M 保留作用域数据的等待对照及 C639 局控 PM 运行时的活动核验与后布线分项标定。已定位 SRAM 与母控 PM 的原工件归档，旧服务器身份认证待恢复，读 DMA 仍在映射。[结果与恢复](handoffs/2026-11-17-issue-280-bscc-t6-covered-power-and-bindings.md)

2026-11-17，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成 Qwen3 旧版 M 的 18 窗 300 MHz 功耗及三窗参考估算。旧版留有 setup 和 hold 违例。新版 M 的 CTS 中止，读侧 DMA 仍在 ABC 映射，SRAM 与母控 PM 等待宏工件。[结果与恢复](handoffs/2026-11-17-issue-280-bscc-t6-m-baseline-power.md)

2026-11-16，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成 Qwen3 真实载荷写侧重测、局控阵列和 U 算术／控制 300 MHz 标定。M 进入 CTS，读侧原综合及跳过 SHARE 对照持续运行，剩余 SRAM 和母控 PM 等待物理工件。[本轮结果](handoffs/2026-11-16-issue-280-bscc-t6-actual-payload-and-leaf-calibration.md)

2026-11-16，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成 Qwen3 共享写侧 DMA 和 PM 拆拍桥的 300 MHz 配对功耗，以及 M 候选两工况产品回归。两项读 DMA 综合及 M 物理重跑仍在执行，整模型功耗待归属。[本轮物理标定与恢复](handoffs/2026-11-16-issue-280-bscc-t6-physical-calibration.md)

2026-11-16，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 已验收 Qwen3 三窗 TLM 事务与逐拍分项，确认 U/SRAM 残差的片内归属。读侧 DMA 两版仍在综合，M 的 300 MHz 路径修复候选已通过组合等价检查，整模型功耗待物理标定。 [结果与作业追踪](handoffs/2026-11-16-issue-280-bscc-t6-independent-calibration.md)

2026-11-15，Issue #280 已确认 C639 与实际布线 M60 的权重分配握手差异，六个原生活动窗未触发同拍冲突。当前 C639 的 M 叶块 18 项独立回归通过，同源映射通过，修订布线 116976 已开始。 [握手测试及同源实现](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/8a58ca82721a50939f2e4e4e988d4a556b7a6e5a/work/Melodydt/280/C639_M_PHYSICAL.md)

2026-11-15，Issue #280 的 C639 G32 两种工况门级回放完成。首次有效握手触发的两个 81.92 µs 窗口均有 64 笔 G32 输入和输出，普通／背压 G32 平均总功耗为 1.381／1.377 mW。M 同源布线、512-bit 写和控制链路校准待做。 [结果与追溯](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/524d0f1ae7e03a38114ae356bc4f4c8f81b0e253/work/Melodydt/280/C639_G32_POWER.md)

2026-11-15，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 完成 C380 普通 128-bit SRAM 的同初态空闲对照，正常／背压窗口增量 37.945／8.170 nJ。P SRAM 的 512-bit feeder 读四 bank 同址选通通过门级验证，实测 PM 接口仍为 128-bit。C639 G32 正常工况门级回放已读回，背压及四窗功耗作业持续执行。 [结果与作业追踪](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bc7ac38b5aaa8fa8d908ca6da999ed45ddbcbe76/work/Melodydt/280/PAIRED_SRAM_AND_C639.md)

2026-11-15，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 通过 C380 布线 SRAM 的完整门级回放。普通 128-bit SRAM 端口在 100 MHz 的两个 20.48 µs 活动窗口分别估算 35.664 与 34.210 mW，标注覆盖率 99.18%。空闲差分、C639 物理绑定和真实 512-bit SRAM／PM 校准待完成。 [门级回放与功耗回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cdc1acdc83594a8240ace568a002af9fc41411fc/work/Melodydt/280/C380_ROUTED_POWER.md)

2026-11-15，Issue #274 完成七模型 512-bit TLM 三 P 并行 FFN 和代表性历史复测。七模型两步 top-1 均与同历史 FP32 一致，Gemma 使用 Q12 残差和后归一化写回。短 Prefill、Decode、独立验收和复跑见[结果记录](../work/Melodydt/274/THREE_P_LIVE.md)。PR #275 为草稿，整机 RTL／物理时序验证仍待完成。

2026-11-15，[Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 完成接入 PR #272 保留调度后的七模型 512-bit 全层 TLM 重测。6 个模型的两步 Decode 提速，七模型短 Prefill 降速。独立 C380 注意力和 C639 FFN 原生 RTL 夹具复跑通过。全层吞吐、作业及散列见[重测记录](../work/Melodydt/274/PR272_RETEST.md)。草稿 PR #275 待审查，整模型 RTL／物理及尚余数值资格待完成。

2026-11-15，[Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 已完成七模型的短 Prefill 与两步 Decode 候选 TLM 回放，全部采用 512-bit SRAM 端口。吞吐、状态对账与 FP32 分歧详见[结果索引](../work/Melodydt/274/RESULTS.md)。[PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 为草稿，第一轮七模型全层优化 A/B 已完成，短 Prefill 提升 33.89%–53.98%，两步 Decode 提升 20.82%–97.53%。测量使用 512-bit SRAM，优化前后两位置残差和完整词表 logits 逐字节一致。[优化结果](../work/Melodydt/274/OPTIMIZATION.md)保留分项及 SHA-256。数值资格、RTL 和物理时序校准待完成。

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
