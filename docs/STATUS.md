# 当前状态

- 更新日期：2026-10-21（中国标准时间）
- 当前阶段：架构定义与研究方案整理；开始代表性 Block 的分层实现工程试验，尚未冻结底座
- 当前任务：[Issue #7：候选 Block 边界及分层布线](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，研究 openTPU 的 ACT／MXU 粒度及 llaccel 完整引擎粒度，先以原完整 VECTOR 检验实现流程。见[实验计划](experiments/openTPU-llaccel-block-plan.md)与[现场记录](experiments/issue-7-vector-pilot.md)
- 资料接入：[Issue #1](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1) 的初期资料已进入 `main`，[PR #2](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/2) 已合并；新版参考报告沿用 [Issue #3／PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4) 的交付，本任务不重复维护该包
- 已确认边界：研究对象和主要问题已写入项目说明；具体工艺、Block 资源、定制层集合和工具链未冻结
- 关键限制：本仓库参考包不包含完整物理输入；本轮用户已授权复用集群原工程，已核实其工程及工具路径可访问。新实验独立保存于 `LLMHardwareDesign/issue-7/<attempt>/`，不覆盖原始结果。常规宏集成不等于受限定制底座、全系统功能验证或签核
- 下一步：按实际日志完成并审查首轮试验；再建立同资源扁平／分层对照、冻结资源和受限互联、多计算图验证。具体工艺与硬核库仍需决策
- 任务入口：[本仓库 Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues)
- 项目登记：[管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待审查；合并前状态为 pending
- Projects 入口：候选[组织看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1)；本轮查询因缺少 `read:project` 失败，且无 `config/board.json`，实际看板与条目 `unverified`、同步 `pending`。恢复动作见 [Issue #7 看板交接](handoffs/2026-10-21-issue-7-projects.md)

本页只记录全项目阶段和关键限制；具体任务进度以 Issue 和 PR 为准。
