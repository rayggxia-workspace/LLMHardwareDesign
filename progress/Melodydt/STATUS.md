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
