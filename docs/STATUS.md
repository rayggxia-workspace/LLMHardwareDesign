# 当前状态

- 更新日期：2026-10-22（中国标准时间）
- 当前阶段：架构定义、Block物理工程尝试、抽象冻结连接实验、真实普通LEF几何输入冻结与选定接口关联；DAC为研究目标，具体届次未指定
- 资料接入：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)；资料已进入 `main`，[PR #2](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/2) 已合并，登记／看板缺项继续保留
- 当前资料：项目说明 v1.0、专题研究文档、来源笔记，以及五个参考项目七个案例的布线分析包；三份 HTML 报告、llaccel 引擎内部分析及远程服务器规则已通过 [PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4) 合入 `main`；工艺互连资料的逐层资源评估补充已一并提交
- 已确认边界：研究对象和主要问题已写入项目说明；具体工艺、Block 资源、定制层集合和工具链未冻结
- 关键限制：现有布线结果包含少量 RTL 片段，不含完整源工程、物理数据库、工具环境和日志，不能单靠本仓库复跑物理实现
- 最新业务：YUZE-LU的[Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)在[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)/[PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)保存VECTOR顶层尝试和ACT/MXU/GEMM修复，未合并；时序、电气、模型及等价缺口以最新交接为准。普通分层工程不称物理H2。
- 研究接续：[Issue11/PR12](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/12)的192例实验待审查；[Issue13/PR14](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/14)完成384例配对消融，白名单扩展44→71/96，9映射有原无路径到合法解证据，容量放宽未新增本轮成功。230解与248份cut及全量重放通过，见[实际记录](experiments/issue-13-endpoint-ablation.md)。两PR均未合并，未形成物理H2/PPA结论。
- 真实输入：[Issue16/PR18](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/18)冻结ACT20/MXU20/GEMM20原字节/SHA，6791PIN、6956PIN RECT和30OBS RECT完整保留PORT/PG/OBS；67项业务检查及确定性重导出通过，见[实际记录](experiments/issue-16-macro-endpoints.md)。PR待审查，未形成工艺合法access point或合格宏。
- 并行工作：[Issue15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)由YUZE-LU推进同资源ACT/MXU分离与合并物理对照，不重复开工；普通分层对照不等同物理H2。
- 接口证据：[Issue19/PR20](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/20)完成旧wave206两宏3032信号位、685连接与2346边界网关联，原始两处Lib缺分号及四处PG方向差异明确保留；148项检查、205390独立比较、六个篡改负例和离线重放通过，待审查。见[实际记录](experiments/issue-19-interface-contract.md)，不等同新M9宏或合法接入资格。
- 下一步：刷新Issue15/PR17新M9结果，绑定新视图版本，核对Lib/PG问题、DEF方向及技术via/OBS接入规则。条件满足后固定资源和总预算研究端点感知mapping，继续补齐宏资格。研究路线见[DAC计划](DAC_RESEARCH_PLAN.md)
- 任务入口：[本仓库 Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues)
- 项目登记：[管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待审查；合并前状态为 pending
- Projects 入口：[组织总览看板](https://github.com/orgs/rayggxia-workspace/projects/1) 为管理中心配置的候选入口；本仓库无 `config/board.json`，本次Liangruizhi会话无Projects工具，账号在线权限及Issue11/13/16/19条目未核验／同步pending；Issue #3关于缺少 `read:project` 的旧交接属于其他会话，不能据此推断本账号权限。具备工具与权限的管理员待指定

本页只记录全项目阶段和关键限制；具体任务进度以 Issue 和 PR 为准。
