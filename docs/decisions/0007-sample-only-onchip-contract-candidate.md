# 0007：仓库样本域与无外存片上合同

- 状态：**proposed / 待独立审查**；用户范围约束已确认，不代表以下具体预算已验收。
- 任务[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)，交付[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，负责人Melodydt。
- 设计父39bd7bf；七宏来源643c6012，核心RTL不改。

用户要求执行前三步，仅现有八样本；未知规模保守估计并给依据；暂不考虑外存；M11/M12永久绑定且不依赖控制程序启动装载。

候选取舍：固定八模型/十层型，源配置和小导出范围分开；49索引下钻621数据/460受控参数槽，按配方/语义/状态/映射判定，缺实现不改语义非法。当前系统只允许片上region，EXT credit0、EXT valid0，无DMA/自动spill；放不下报具体容量缺口。

S原生16KiB中保守预留loader快照1KiB、T批次spool6KiB，计算区9KiB；互斥复用须证明。loader另需独立1KiB capture避免串行S策略闭锁。新控制存储32KiB和程序/参数ROM2MiB是明确公式的逻辑预算，未实现/未综合，不是模型权重或动态scratch。

外侧task/handle/event/phase lease及64bit控制flit为候选实现合同；保持唯一原生owner、RESUME与新context区分。当前原生资源不能保证完整样本权重/KV/state驻留，不能用缩小维度、隐含外存或代码地址位数冒充容量。

动机、证据、具体字段/预算与未完成项见[工作报告](../STEPS_1_3_WORK_REPORT.md)及三个步骤规格。旧0006/v0.3全系统存储候选保留历史，当前阶段按本片上合同准入；NUM/完整程序/数值/RTL/物理验收均另行完成。
