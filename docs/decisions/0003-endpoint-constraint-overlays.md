# ADR0003：最大库存与反事实约束分开记录

- 状态：proposed，待PR审查；2026-10-22（UTC+08:00）。[Issue13](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/13)，负责人Liangruizhi。
- 问题：上一轮轨道／段长／接入库存同时变化，不能仅凭成功率把失败归因于端点容量，也不能用更多搜索次数证明新算法。
- 决策：每组冻结最大合成库存，显式overlay限制连接白名单与wire-tap容量；配对例固定mapping、算法、seed和搜索预算，分别保存master/overlay/effective哈希。原wire和driver不可拆，不插入新有源资源，pin容量保持1。
- 验收：同因子条件的另一限制完全相同；受限臂恢复原模型资源；成功连接可跨臂重验并留来源；完整数据与闭合cut证书、精确微例和确定性重放。
- 代价：这是反事实限制研究，不提供可制造接点密度、金属层或PPA结论。输入图已经被观察，不称新盲测；qualified宏尚未齐全，真实端点接入独立冻结输入。
- 后续：按MACRO_ENDPOINT_CONTRACT导出真实视图；下一映射对照另立Issue并固定K个映射与总路由预算，不在当前消融中混入映射策略。
