# 当前状态

2026-11-09，Issue230九组690网共同GDS的实际路由读回、40083个原生cell-layer几何对照及全部12402850层级实例身份/变换检查通过。
全部1698914实例/678871物理网ODB对照、共同1380端点连通、五类源GDS身份及113006927矩形的共同场几何通过。
完整原版DRC为0；690/690共同场电容和9档原约束TT300MHz全部通过，最差setup/hold +73.082209/+0.211775ps，全部电气违规为0。
严格六文件交付门100774及便携包真实DEF/ODB重读、名义STA回放101473均通过。
809MB交付包已回收，40项包内文件及全部六文件SHA核验通过。57项后端及119项综合器检查通过。
预连/外部边界/新金属通过显式资源合同分别降低，不把完整控制或外存开发作为通用EDA前置。
见[后端交付与复跑入口](../work/YUZE-LU/230/HANDOFF.md)及[完整迭代记录](../work/YUZE-LU/230/README.md)。
PR231工程验收通过、待独立审查；范围为九组690条实际晚接网与声明研究RC栈，整模型及未运行控制程序资格另列。


2026-11-08，[Issue230](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/230)
接入main五类_64（U使用#221修复包），核对合格包并从真实ODB导出端点，新增通用
DEF/ODB/GDS写出与独立物理读回。362根晚接接口已通过上层研究几何及全原生层XOR；
完整原版DRC作业100406五项均0违规。#220的九组资源定义和真实IR确实存在；此前将共同已验收
ODB/完整母控作为通用路由开发前置的判断撤回。新增资源库装配和统一综合后端入口，实际九组
生成28个独立叶宏、1380个M10端点（100559），36项本地检查通过。后续继续端点合同降低、
完整路由与物理反馈，不要求先开发新控制/外存RTL。见[说明与证据](../work/YUZE-LU/230/README.md)。

2026-11-08，Issue #228 实现通用M10接入/双层A*、多接收端树、拆线重布及独立几何/连通检查，消费#227绑定合同。21项算法测试含128位及30个独立Dijkstra对照通过，拆线重布示例两网完成；全部为合成几何，不针对Qwen3.5，不声称实际底座DRC/RC/STA。见[算法说明](../project/experiments/upper_router/README.md)。隔离分支待独立审查。

2026-11-08，[Issue #226](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/226) 在PR220最新综合算法上新增逻辑束展开、协议依赖、候选底座端点绑定及分级反馈接口，自动输出路由需求。真实双U样例306个位信号仍未物理绑定；不声称实际路由或RC/STA通过。隔离分支待审查，详见[合同](../project/experiments/block_synthesis/ROUTE_CONTRACT.md)与[回执](../work/YUZE-LU/226/README.md)。

2026-11-08 综合算法补充：[Issue219/PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220) 已加入有限S只读Dot分片及缓存感知DP状态；完整真实3B五组/九组各三输入与旧整数结果逐位一致，100项测试及独立地址/容量/静态互斥重验通过。复用贪心较原基线模型代价降17.16%、搬运降25.40%；九组DP另降26.14%但束数10→18，同10束无额外收益。仅覆盖只读Dot分量；整网控制编码与真实布线另验。见[本轮说明](../work/YUZE-LU/219/READ_CACHE_RESULTS.md)，下方“全部spill”系旧基线。

2026-11-08 审查修复及控制接入：[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220) 原整网 DP 与独立检查器遗漏 incompatible_nets，现已分别修复。90 项测试（含 150 个互斥小 DAG 穷举对照）、完整 3B 计划重验通过；当前独立母控含实际程序 SRAM、两组 U_64 局控的小图自动镜像完成 9 次数值／写 ACK／源保持与释放回放。原完整清单声明互斥对为 0，不代表物理无冲突；固定放置小图不代表任意整网 DP 控制编码、九目标或物理通过。见[修复与控制证据](../work/YUZE-LU/219/MUTEX_CONTROL_RESULTS.md)，旧数值及同预算无收益结论保留。

2026-11-08 算法整网里程碑：[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220) 修复Gather、实际量化、动态矩阵/地址与完整S32原语分解。完整真实Qwen2.5-3B B1/S2三输入生成IR数值回放通过（L2 0.5265%/0.7251%/0.5592%，两位置argmax一致）；各S16KiB、预连0、#182虚拟外存，整网计划与独立检查通过。75项测试、原语三初态通过；同连接预算DP尚无整网收益，全部spill后端仍需tile/cache优化。不继承系统RTL/物理资格，其他bench未获完整整网资格。见[完整结果及回执](../work/YUZE-LU/219/FULL_RESULTS.md)，下方11-07的Gather阻塞为已修复历史。

2026-11-07 算法后续：[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[Draft PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220) 新增M/N/E/G/R256/T原生命令配方、跨片状态保留和显式格式转换。服务器46项检查、五类混合图38任务及R256跨片三初态回放通过，私有S各16KiB、预连0、虚拟外存。完整Qwen2.5-3B仍缺Gather、量化与动态布局等软件转换，未称整网通过。[结果与回执](../work/YUZE-LU/219/LEAF_RESULTS.md)。

2026-11-07 算法分支进展：[Issue #219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) / [Draft PR #220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220) 已修正零数据预连、虚拟外存和算法验收边界；服务器34项检查、真实N/E客户端三初态回放及5组16KiB调度对照通过。[证据与未完成项](../work/YUZE-LU/219/FIX_RESULTS.md)。完整3B模型的数值/尺度/布局等软件转换尚未完成；控制镜像、原生DMA和最终物理不作为当前算法验收前提。此进展不改写其他硬件任务的资格或状态。

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
