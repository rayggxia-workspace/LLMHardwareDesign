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
