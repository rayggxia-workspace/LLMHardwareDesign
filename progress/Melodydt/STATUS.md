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
