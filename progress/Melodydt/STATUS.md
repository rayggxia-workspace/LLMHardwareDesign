2026-11-02T16:00:42+08:00（Asia/Shanghai）：[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)/[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，task/151-six-connection-study，base task/143-seven-block-v2，输入f9a90c8。W5-IF三层有界逻辑合同v0.1成稿待审查，真实端口/适配和六profile样本边界、CMD/数据/独立storedACK及关闭/复用/partial、B8预算和因果时序有表。无新RTL/仿真/服务器作业，非L5实现/物理冻结；A8/F8不能裸接且完整hidden数值、N257以上/容量/供参未接收。独立API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/w5if-f9a90c8/integrated，无GitHEAD/暂存。下一步L4完整A/F数值/残差/布局及有界Norm存储映射；外部审查待指定，登记pending/看板unverified同步pending，交付commit以PR回执为准。

2026-11-02T15:00:44+08:00（Asia/Shanghai）：[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)/[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，task/151-six-connection-study，base task/143-seven-block-v2，输入714cab4。三层互联问题已安排L4/W5-IF合同前置、L5/W2控制网/双岛+W6拓扑、L8/W10/W11真实系统和物理；固定控制网仍proposed。只更新计划/决策/索引，未改RTL/未新增仿真或服务器作业。独立API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/control-boundary-714cab4/integrated，无GitHEAD/暂存。下一步继续L4先编接口/事件/资源表；具体合同与L5实现未完成。独立SSH/Slurm/Verilator策略保留。外部审查待指定、登记PR5 pending/看板unverified同步pending。交付commit以PR回执为准。

2026-11-02T14:10:10+08:00（Asia/Shanghai）：Issue151/PR152，继续task/151-six-connection-study，base task/143-seven-block-v2，输入1d72247。已实现有界A8 M/N/S/T，server95116/c64/node1/8CPU/1m51s成功N29/F825/A826；旧32SV/SVH不变。独立包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/a8-1d72247/integrated为API副本，无GitHEAD/暂存；服务器真实源码/结果位于/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102，r01..r03失败保留，authoritative r04。下一步继续L4完整A/F及真实shape/容量，L5未启动；外存保留灵活性。未完整模型/物理，非lint clean。审查待指定/PR未合并；登记PR5待最终核验、看板unverified/同步pending，处理人待指定。交付commit及在线状态以PR回执为准。

2026-11-02T00:47:39+08:00（Asia/Shanghai）：Issue151/PR152 主线四有限N+preNorm F8待审查；研究分支task/151-six-connection-study，base task/143-seven-block-v2；基线merge0e8e970（01+d1）已读clean。已实现2RTL/2TB、mathoracle/EXP回放/poison与RNE3窄化；本地真实N29/F8 25及旧114回归通过，源SHA/4运行证据保留。正式docs/W4_*，隔离包work/Melodydt/151/w4-0101cc7/integrated（API副本无GitHEAD/暂存；上游大subtree由远端SHA继承，非完整本地checkout）。下一步继续L4完整F/A/实际形状映射并处理审查；完整L4/NUM/MEM/TopK/物理未验收，不启动L5。外部审查人待指定、登记pending/看板unverified同步pending；无新服务器作业。新交付commit从PR头/在线回执读取。

2026-11-01 21:30 CST（Asia/Shanghai）：[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151) / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152) 进入W3有限E/G＋FFN8待审查交付。已完成3新RTL/2TB、独立整数参考、ModelSim adapter46/FFN21/旧P2W1回归47检查；叶宏/P2/W1未改。下一步：外部审查后按八主线进入L4 N归约/回放，不能把本内核当完整F。阻塞/限制：外部审查待指定、登记PR5 pending、看板unverified/同步pending；未做PPA/完整模型/服务器作业。隔离工作目录work/Melodydt/151/w3-99d6df2/integrated，远端task/151-six-connection-study；父commit99d6df2，新交付commit见PR头与执行回执。

# Melodydt 的进度

既有接入与仿真记录保留在[PR148固定版本的个人进度](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b44a31b7ab4a6d572601c0adc3c80a7dbbbff79d/progress/Melodydt/STATUS.md)。该文件尚未进入本研究基线main；本PR新增同路径研究摘要，合并PR148/150时必须保留各项实际进展。

- 接入规则：[Issue147](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/147) / [PR148](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/148)，待审查。
- E宏仿真：[Issue149](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/149) / [PR150](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/150)，原交付记录Slurm94188通过；本研究不重跑或接管。


## 2026-10-31T16:22:44+08:00：Issue151六类连接方案第一阶段研究

- 当前研究：[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)，负责人Melodydt；远端分支`task/151-six-connection-study`，基线`a103da352b7e431cedc69f54b9f71c05371be1b3`。
- 已完成：六项数据/控制/格式/布局/存储与改动归属研究；核实S内loader、pair test mux、独立bridge/bank/booster/return及旧驱动修复；形成三个正式研究文档和连接/来源索引。
- 研究文档：[六项方案](../../docs/SIX_CONNECTION_SCHEMES_STUDY.md)、[bridge归属](../../docs/SIX_CONNECTION_BRIDGE_AUDIT.md)、[候选协调机制](../../docs/SIX_CONNECTION_COORDINATION_CANDIDATE.md)。
- 本地隔离目录：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/`；delivery为API提交资料包，非完整Git checkout。未覆盖其他会话的根目录管理副本或任务分支。
- 实际核验：管理结构PASS；选定来源Git blob/SHA-256与文档/清单检查以work/Melodydt/151/verification.json为准；RTL/SystemC/EDA未执行。
- 下一步：独立审查六项的改动归属；确定GDN/SSM系数与MoE宽归并边界，再做最小RTL组合。研究候选未冻结，不授予整链资格。
- 审查/合并：[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)已上传，第一阶段研究待独立审查；不自审、不自合并，不标done。首份研究commit为796d413458fd267200ab9dbff6d8e1b0b6468cdd，当前head以PR读回为准。登记PR5仍pending；缺board.json和Projects条目工具，看板unverified/同步pending，处理人待指定。
- 既有Issue147/PR148与Issue149/PR150仍由各自交付记录维护；已读回PR148的b44a31b7并保留固定版本入口，合并时须整合其他任务后续进度，不覆盖其记录。


## 2026-10-31T18:31:13+08:00：Issue151第二阶段总方案

- 用户前提：同一M1–M10底座，M11/M12定制模型，运行期间无需更换任意图。
- 成果：[总方案](../../docs/SIX_CONNECTION_SYSTEM_DESIGN.md)、[控制规格](../../docs/SIX_CONNECTION_CONTROL_SPEC.md)、[六模板](../../docs/SIX_CONNECTION_TEMPLATE_SPEC.md)、proposed决策及机器合同。继续Issue151/PR152和原任务分支，不创建重复任务。
- 新发现：完整GDN/SSM跨多个R tile，全组Norm前不能把所有候选留在单R内；新增外部版本化状态/历史与发布协议作为必要候选，单tile与完整token验收分开。
- 本地独立包：work/Melodydt/151/system-delivery；原delivery与根管理副本保留，不是Git checkout。远端增量在PR152，真实head见PR回执。
- 实际检查：管理结构PASS；六模板64阶段、15项原生端口唯一归属、17个拒绝用例、43份固定版本文本Git blob/SHA-256与链接核验PASS，最终文件SHA以system-verification.json为准。文档/静态合同验证不代表RTL/SystemC/EDA，没有新增服务器作业。
- 下一步：独立评审，冻结完整产品编译/ROM预算、NUM与状态版本服务范围，再拆真实RTL实现任务。PR未合并、Issue待审查，不标done；审查人待指定。
- 登记PR5仍pending；看板配置/条目工具不足，在线状态unverified/同步pending，不能据此认定Melodydt权限不足。恢复见交接。其他Issue147/149记录保持原入口。


## 2026-10-31T19:47:17+08:00：PR144七宏实现依赖整合

- 用户授权将PR144固定643c6012合入task/151-six-connection-study，保留46b29c7研究；真实共同祖先6a681d66，双父merge commit见PR152回执。
- 当前七类RTL已进入研究分支，源project整树及相关依赖按原Git对象保留；不只复制四个v2文件。PR152基分支改为task/143-seven-block-v2，仍待审查、不合main。
- 新入口：[实现基线](../../docs/SEVEN_BLOCK_RESEARCH_BASELINE.md)，14核心文件精确SHA/限制见rtl-baseline.json；R仍未合格，PR133桥与PR146不会自动带入。
- 本地隔离集成目录merge-pr144-643c6012/integrated是检查资料包，不是完整Git clone；原system-delivery和管理根副本保留。
- 合并后管理/研究静态/源文件检查和Tcl夹具结果以integration-verification.json为准；没有服务器作业、RTL或P&R。
- 下一步在当前真实端口上拆最小FFN/257Softmax系统wrapper任务；NUM、外部状态版本及ROM完整编译仍待接收。登记pending，看板unverified/同步pending，独立审查人待指定。

## 2026-10-31T20:30:44+08:00：Issue151按当前RTL重新生成总方案

- [Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151) / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，负责人Melodydt；分支task/151-six-connection-study，输入head faabeda68b3b098ba562d68517319e02725f5bc3，七宏来源643c6012；本轮输出commit/线上CI见PR读回回执。
- 已完成：实质重写[总方案v0.2](../../docs/SIX_CONNECTION_SYSTEM_DESIGN.md)、控制规格/六模板，补七宏逐操作码审计、原生接口合同与编码核验，修正M scale/读出、N长度/mask、E/G尾字/尺度、R两遍/局部提交、T连续refill及loader取消。
- 独立目录rtl-redesign-faabeda/integrated为部分API资料包，不是Git clone；原包和根参考副本未覆盖。没有修改叶宏、服务器或ref-project。
- 实际验证：管理、研究来源36+7、6模板/64阶段/15owner/17拒绝用例、7接口与示例编码静态检查已通过；最终重跑命令与产物SHA以rtl-redesign-checks/verification为准。未执行RTL/SystemC/EDA、完整产品程序、整数oracle或模型质量，没有新作业。
- 下一步：独立评审v0.2，再明确最小FFN8/Softmax257 wrapper实现任务和NUM/外存/版本服务边界；R资格仍单列。审查人待指定，PR未合并、Issue回in_review，不提前done。登记pending、看板unverified/同步pending，在线状态以读回为准。

## 2026-10-31T21:15:42+08:00：Issue151全合法连接与有限家族设计

- 用户确认全部允许组合、有限模型类型、M11/M12永久绑定且无启动装载。继续[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)/[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，负责人Melodydt，task/151-six-connection-study，输入36f9c9db；本轮输出commit/CI见PR回执。
- 新增[全合法连接规格](../../docs/ALL_LEGAL_CONNECTION_SPEC.md)、49对/角色/profile目录与静态正负检查；总方案/控制/模板/候选决策同步。主方案有限家族ROM＋永久选择/参数，六算法仅回归；局部服务可阶段回访，缺实现与非法分轴。
- 本地all-legal-36f9c9d/integrated为隔离API资料包，无Git暂存区；仅本轮白名单文档/合同/核验和自身进度上传，不改叶宏/他人目录/ref-project，无服务器作业。
- 实际验证以all-legal-checks.json、all-legal-verification.json为准；只作管理/字节/静态一致性，不声称49对硬件已通。完整家族目录和程序、RTL/整数oracle/活性/EDA未执行。
- 下一步独立评审合法域/原语与家族目录，再落实分阶段RTL实现任务。PR未合并，Issue交付后回in_review、不done；审查人待指定。登记PR5 pending，看板unverified/同步pending，所需管理员待指定。

## 2026-10-31T22:10:32+08:00：Issue151前三步样本/角色/片上合同

- [Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)/[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，Melodydt；task/151-six-connection-study，输入39bd7bf，输出commit与CI以PR回执为准。
- 完成可评审材料：[工作报告](../../docs/STEPS_1_3_WORK_REPORT.md)、八模型/十层型FamilySpec、621数据＋460参数槽/153配方、96样本连接义务、无外存接口/信用/容量合同和可复算需求/检查工具。只完成规格/静态核验，不声明RTL实现。
- 保留源配置上下文32768..262144与真实H/I/R尺寸，小图B1/S2单列；S计算区9KiB和原生容量不足明确报gap。新增1KiB capture、32KiB控制、2MiB ROM均候选，不假设已存在。无EXT/DMA/spill、无bootload。
- 独立steps123-39bd7bf/integrated API包，不覆盖根/旧包，无本地HEAD或暂存；源19份指纹与实际检查以steps123-checks/verification为准。未运行推理、RTL/SystemC/服务器/EDA，不动叶宏/ref-project。
- 下一步审查原理/估计/缺口和资源选择，再推进适配/存储RTL。PR待审查不合并，Issue回in_review，不done。审查人待指定；登记pending，看板unverified/同步pending，管理员待指定。

## 2026-11-01T11:06:48+08:00：外存边界纠正与N接口澄清

- Issue151 / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，负责人Melodydt；输入86d5648，分支task/151-six-connection-study、base task/143-seven-block-v2。
- 用户明确系统有外存，当前暂不研究，保留接入；P0片上验证credit0/无自动spill仅是评估范围，不能推广为永久无外存架构。JSON显式区分architecture_memory与memory_policy，保留地址/服务/完成语义扩展边界。
- 核对固定643c6012：N是一个顶层module、内部共享group及独立TopK表；同一128bit应答口由op决定payload格式。七宏RTL未改，无服务器作业。
- 目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/memory-scope-86d5648/integrated，为隔离API资料包、非Git clone，无HEAD/暂存；旧包和根参考副本保留。成果入口docs/MEMORY_SCOPE_AND_N_INTERFACE_CLARIFICATION.md；本轮实际验证见work/Melodydt/151/memory-scope-checks.json。
- 未完成：外存接口/带宽/驻留/一致性与有源预制范围、实际wrapper/NUM/控制RTL及精度/活性/物理验收。恢复第一步读回Issue151/PR152最新head及本澄清，再按P0与系统范围分别判断；不接管其他成员目录/作业。
- PR待独立审查、未合并，Issue保持in_review、不done；审查人待指定。登记management-hub PR5本轮已读open/unmerged→pending；无board.json且当前工具无Projects条目能力，卡片unverified/同步pending，管理员待指定。输出commit、远端读回和当前CI以PR回执为准。

## 2026-11-01T11:57:42+08:00：按静态编译和共同底座重做前三步

- Issue151 / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，Melodydt；输入e44c4f5，task/151-six-connection-study，base task/143-seven-block-v2；输出commit/CI见PR最新回执。
- 当前入口docs/STEPS_1_3_WORK_REPORT.md、三个步骤规格及work/Melodydt/151/static-rework-index.json；新增family-binding/compile-lowering/static-execution三合同，保留旧角色/模型输入与历史回执。role主要编译期，固定硬件执行共享动作，不能逐产品重新综合。
- 目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/static-rework-e44c4f5/integrated为隔离API资料包，无本地Git HEAD/暂存，不覆盖旧包/根参考副本。无服务器作业；RTL/ref-project未改。
- 验证命令/输入与输出SHA见static-rework-checks/verification；只是研究一致性/有限整数与协议规则，不是模型编译或RTL/PPA。完整八产品程序、精度、MEM/NUM与适配/控制RTL、活性和共同底座物理未完成。
- 恢复第一步：本人连接读回Issue151/PR152最新head/base/评论/CI，再读本工作报告与index；核对真实绑定和缺口后才建立RTL子任务，不接管#143/#153目录或作业。
- PR待独立审查不自合并，交付后Issue回in_review，不done；审查人待指定。登记PR5本轮读回open/unmerged→pending；当前无board.json/Projects条目工具，卡片unverified、同步pending，管理员待指定。

## 2026-11-01T14:16:49+08:00：七阶段路线P1交付

- Issue151 / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，Melodydt；输入343f4d4，task/151-six-connection-study，base task/143-seven-block-v2，输出commit/CI与线上核对见PR回执。
- 用户采纳七阶段路线，本轮仅P1版本/接口合同与P2测试输入准备；入口docs/SEVEN_MACRO_INTERFACE_ROADMAP.md、docs/PHASE1_INTERFACE_BASELINE.md及work/Melodydt/151/phase1-index.json。七宏原生合同/149端口、源锁/升级记录、MST有界整数参考/向量与未来验证矩阵形成待评审材料。
- 固定643c6012；开始时PR144观察点adb819，14路径13相同、仅R内部变化、7顶层声明相同。旧源与新物理不混用，不自动升级；没有改叶宏/他人目录/ref-project，不运行服务器/RTL/SystemC/EDA。
- 本地目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/phase1-343f4d4/integrated为隔离API资料包，无Git HEAD/暂存，旧包与根参考副本保留。实际命令、工具与SHA见phase1-checks/verification；Python参考不是MST RTL通过。
- 未完成：独立审查和P1正式接收、P2真实MST顶层及后续阶段；审查人/实施子任务负责人待指定。P2-P7未开始，不将Issue标done；交付后保持in_review。
- 登记management-hub PR5本轮读回open/unmerged→pending；本仓库无board.json且当前工具无Projects条目读写，卡片unverified/同步pending，管理员待指定。无服务器作业或自动监测。
- 恢复第一步：用Melodydt读回Issue151/PR152最新head/base/评论/CI，再核对P1源锁和测试矩阵；源一致且P1接收后，才进入P2实现S_CTRL+M/T控制与最小top，母控/ROM骨架并行。


## 2026-11-01T14:40:15+08:00：P2最新核心RTL与MST协调原型

- Issue151 / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，Melodydt；输入be10e69bb9ad625079f68361fb47b4747d6ce040，分支task/151-six-connection-study，base task/143-seven-block-v2；输出commit/当前CI与线上读回见PR回执。
- 用户明确要求获取最新RTL并进入P2；14核心源固定707878621b2add4ed218b8c43df2e95c9a56e2ba，仅R更新，七顶层149端口相同。源码同步不授予R新资格，不接管Issue143或153。
- 新增S单在途普通端口helper、MST小顶层与固定ROM母控骨架，正式路径project/rtl/block_connection_p2/，测试project/tb/block_connection_p2/；报告docs/PHASE2_MST_IMPLEMENTATION.md。使用真实S/loader/M/T，写ACK、M状态/结果过滤、T提交/释放与协调reset分开。
- 实际命令/工具/输入输出SHA见phase2-checks/verification-status及RTL回执；只报告实际运行的有限切片，不以编译或Python代替RTL。完整模型、全部错误/形状/活性、系统物理和MEM集成未验收，P3–P7未开始。
- 本地隔离API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/phase2-be10e69/integrated，无Git HEAD/暂存；旧包、根参考副本及其他成员目录保留。ModelSim实际运行不使用服务器，不修改系统/读取凭据。
- 当前PR待独立审查/未合并，不标done；审查人待指定，P1独立接收也未凭授权冒称完成。登记PR5 pending待最终读回；无board.json与Projects条目能力，看板unverified/同步pending，管理员待指定。
- 下一步先读回PR头/本轮锁与实测，再补P2验证矩阵缺项、扩展母控与资源反馈；P3–P7按原路线推进，不提前冻结共同底座。

本轮正式路径实测：ModelSim六项工具命令exit0，helper6/MST13共19 CASE_PASS；14核心源编译通过。Sreq113/Sack112的差1来自协调abort，5个成功批次逐批16/16守恒。完整P2验收仍未完成，详见phase2-verification-status.json。


## 2026-11-01T16:27:52+08:00：粗粒度七宏执行岛候选研究

- [Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151) / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，Melodydt；输入1cc43a93a0c985587745ceba5e0d8d425d43a843，task/151-six-connection-study，base task/143-seven-block-v2，输出commit/CI以PR回执为准。
- 研究大Block本地七宏组合、粗粒度M11互联与母控；主参照为全七类型同构岛+五子层profile A/F/D/H/X，异构和整层为对照。8样本/10层型/242层序列、Norm/残差及96义务完整保留，484是逻辑调用不等于实例/ROM字数。
- 交付四份正式说明、模型/控制/资源机器表与复算工具/实际静态回执、来源索引；入口docs/COARSE_BLOCK_HIERARCHY_CANDIDATE.md。明确38KiB只是分离S/T/R主要数组、单M结果上下文与MEM/NUM/版本缺口，不宣称PPA或全模型映射。
- 独立API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/coarse-block-1cc43a9/integrated，无Git HEAD/暂存，原P2包/根副本不覆盖。当前19原图/配置/导出源blob与既有来源索引一致。
- 新RTL/仿真/服务器作业均0；P2剩余矩阵和P3–P7状态不变。用户授权仿真可在服务器，本轮未创建目录/上传；后续仅在/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue-151/coarse-block/下按REMOTE_RULES隔离运行，软件目录/Slurm命名与资源限制照规则。
- 实际命令、工具/输入/输出SHA见coarse-study-checks/verification；只作研究一致性，不作模型、活性或物理接收。候选待独立审查，不自行合并或done；审查人待指定。登记PR5 pending待最终读回；仓库无board.json/Projects条目工具，看板unverified/同步pending，管理员待指定。
- 下一步先审查profile边界与同构/异构成本口径，再细化可装载tensor数据但固定程序的岛壳/双岛传递，补P2接口/资源/活性缺项，不提前冻结物理岛数或新增有源能力。


## 2026-11-01T17:19:11+08:00：五类大操作与每Block宏数量研究

- Issue151 / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，Melodydt；输入a37e37cad757af5bfc94ed65db3e2e728023c251，task/151-six-connection-study，base task/143-seven-block-v2；输出commit/CI见PR回执。
- 基于8模型/10层型，给A_plain/A_gate/F/D/H/X六张宏数量表、各宏用途和串行调度条件；M/N/E/G/R/S/T分别为1110011、1111011、1111011、1111111、1111111、1111011。各配局控1，母控另1，NUM/MEM/适配/程序等另计。
- 仍是5语义类、242逻辑层/484调用；A_plain178、A_gate8、F210、D24、H32、X32，不按层复制宏。全chip 7/13/32叶仅复用/并发算例，非最小或最优。H拆分12叶/2CTRL保留正确Norm/join归属。
- 报告docs/COARSE_BLOCK_MACRO_BOM.md及模型/资源/控制附录，机器表/生成器/回执和技术决策已同步；实际命令和SHA见block-sizing-checks/verification。只做源/计数/单位/边界核对，不当RTL、模型或PPA。
- 独立API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/block-sizing-a37e37c/integrated，无Git HEAD/暂存，旧包/根副本保留。无新RTL/仿真/服务器部署或作业；用户服务器授权保留，后续按REMOTE_RULES本人目录执行。
- P2剩余矩阵及P3–P7不变。未完成完整数值/程序、MEM/NUM/状态发布、性能和物理准入；外围embedding/finalNorm/LMhead/sampling另研究，不以五类等同完整LLM BOM。
- 本次部分研究交付待审查，不自行合并或done；审查人待指定。登记PR5 pending待最终读回，看板缺board.json/Projects条目工具而unverified/同步pending，管理员待指定。
- 下一步审查固定串行构造及保存字节，按真正吞吐/MEM目标确定增M/N/G/R/S、预制喂数与局控；再做岛壳/双岛试验，不直接把参考数字冻结为物理数量。


## 2026-11-01T18:11:16+08:00：六配置宏间同步/连接差距与实施路线

- Issue151 / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，负责人Melodydt；task/151-six-connection-study，基分支task/143-seven-block-v2；输入051fddb9a3d2cecd4b76c43d07ec8581db9402ce，输出commit/CI见本轮PR回执。
- 大Block仍需小宏同步，局控负责端点、phase/回放/保存/计数，母控负责子层任务/跨岛依赖。提出S物化＋capture/gather/serializer，保留Sloader→M；可选已证明快路，无49直连假设。
- A_plain/A_gate/F/D/H/X逐角色依赖、同宏时间复用/真实payload自环与共享物理跳分开；D先Norm后门，H先门后全4096 Norm；MoE ID→score/专家gather和宽加权归并单列。叶宏BOM不变、NUM/MEM/CTRL另计。
- 当前真实P2为S普通ACK、loader→M、M.op3→S、S→T→sink/RELEASE，固定S8 K8/N8四包S64，有原ModelSim helper6/MST13证据；不是N/E/G/R组合或六个完整profile。当前树旧shared/m106/norm106/wide/memory_link可借但ABI/数值不同；PR133 linkclose桥不在当前树，未借其资格。
- 正式报告/角色路由/源码审计/W0–W11工作包已形成。实际静态命令/脚本/输入/输出SHA见island-connection-checks/verification；不把DAG检查当硬件死锁证明，不将管理检查当业务验收。
- 独立API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/island-routes-051fddb/integrated，非完整Git clone，无HEAD/暂存区；根参考副本、其他会话与旧包保留。无新RTL/SystemC/整数运行/EDA/服务器目录上传或作业；后续仿真授权保留，按REMOTE_RULES执行。
- W1共同壳后W2双岛/MEM边界、W3 E/G、W4 N可并行；完整F/A须N与E/G及所需MEM；NUM定义提前，R和MoE可分别集成，X不依赖R资格。P2完整退出和P3–P7状态不变。
- 本次部分研究交付待独立审查，不自行合并或done；审查人待指定。登记management-hub PR5本轮读回open/unmerged，pending；本仓库config缺board.json且无Projects条目工具，看板unverified/同步pending，处理人待指定。
- 下一步先审查端点/数值/范围合同及P2剩余门，再实施可装载tensor但程序永久固定的共同岛壳，建立输入完整/存储ACK后才启动、唯一S owner及有限capture；先用实际两个岛核验stored ACK和源生命周期。


## 2026-11-01T18:45:14+08:00：八主线的第一条/W0合同与证据基线

- Issue151 / PR152，Melodydt；task/151-six-connection-study，base task/143-seven-block-v2，输入bd7cb2f3060c61e5d28a2ece0653dd9336a024af，实际输出commit/CI/上传结果见本轮PR回执。
- 最新PR144 d1f26884十四核心与选定707逐字节相同，保持原核心；三P2 RTL/两TB按真实运行SHA/1cc来源单列，不转移R物理或SystemC资格。
- 七宏原生合同及逐172角色owner/phase/格式/生存期/ACK/未知/未来W包已形成；目录中的条件选项按源模型域限定，不删键、不把样本inactive当硬件永久禁止。原33要求、P2剩余门/未来输入预期与19旧场景分开。
- 下一W1先固定DOT8形状/程序/地址，真实输入A8+B64有效72B/整字128B、padding清零且8写ACK后RUN；必须替换literal S_INIT，frame+RUN16与RUN8事务分别计数。这是拟定合同，未实施RTL。
- 本轮实际静态命令和输入/脚本/产物SHA见w0-checks/w0-verification；无新RTL/仿真/SystemC/服务器目录上传或作业/EDA，旧P2资格不扩大。W0资料准备待独立审查，原P2完整退出未接收；主线二及后续未实施。
- 隔离API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/contract-lock-bd7cb2f/integrated，非完整Git clone，无本地HEAD/暂存；旧包/根副本和其他成员工作保留。原始GET源码仅包外drafts/native/localonly，不上传。
- 部分交付in_review，审查人待指定，不自行合并/done。登记PR5 pending；config无board.json且当前无Projects条目工具，看板unverified/同步pending，处理人待指定，最终以本轮读回为准。
- 下一步先审查W0合同/缺项与表示取舍，再依用户逐条推进主线二共同岛壳；恢复先核Issue/PR当前head/base/评论/CI及w0-index，不把本地文件、远端未合并分支和服务器状态混同。


## 2026-11-01T20:02:36+08:00：主线二固定DOT8/可变数据岛壳RTL首切片

- Issue151 / PR152，Melodydt；task/151-six-connection-study，base task/143-seven-block-v2；输入bfe62ad179af72aef591622aa5c7a000f5d8b681，输出commit/CI/远端上传以本轮PR回执为准。
- 新增block_w1_mst_top及block_w1_mother_rom，真实8×128入口/56B canonical padding/8实际S写ACK后start；slot2 INPUT_CHECK替代literal S_INIT；唯一S helper、M状态/结果分流、T输出/RELEASE和frame/DONE/reset/abort。固定S8 K8/N8/op/地址/factor1，无runtime程序/shape配置；七叶与旧P2不变。
- 实际本地ModelSim2020.4沙箱外运行：regression-r01旧P2 19CASE；w1-r01声明顺序compile2失败保留；w1-r02 28CASE/4422周期通过后独立review提出DONE计数门；最终w1-r03 TB178318...强化公开DONE+abort同拍exactly-once与frame busy，28CASE/4422周期通过。source/input/tool/config/log SHA在w1-execution-index，完整证据在w1-rtl-evidence。
- 正常frame16S请求/ACK（入口8+RUN8）、7M/应答、T4take/release按每帧检查；全局abort/reset有意丢弃的pending事务差额逐项说明，不能写成全程无条件守恒。28是检查标记，不是28完整任务。无N/E/G/R功能资格或物理/模型推理新增通过。
- 独立源码与根执行证据审阅另记，不代替外部PR审查。完整W1/general endpoints/跨岛stored ACK、NUM/MEM/六profile/P2整体退出仍未完成，主线三及后续未开始。
- 隔离API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/w1-bfe62ad/integrated；非完整Git clone，无HEAD/暂存；其他会话/旧包保留。源码快照/仿真二进制只在包外本地run目录，正式仅相关源/日志/索引；早期不同的W1源码作为小型失败/先前输入附件保留。
- 后续服务器仿真授权保留，已读REMOTE_RULES；本轮使用现有本地工具，无服务器目录/上传/作业，无安装/PATH/license/凭据查看，无ref-project修改/扫描或接管#143/#153。
- 部分交付in_review，PR未合并，审查人待指定，不done。登记PR5 pending，看板无board.json及条目工具而unverified/同步pending，处理人待指定；最终在线事实见PR读回。
- 接续第一步：本人连接核Issue151/PR152 head/base/评论/CI，核w1-index及final r03 source SHA，再依据未完成门决定扩展主线二或按用户安排进入主线三；不把有限DOT8当完整大Block或物理冻结。
