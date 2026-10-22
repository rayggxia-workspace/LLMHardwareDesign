# 当前状态

- 更新日期：2026-10-22（中国标准时间）
- 当前阶段：参考资料已接入，开始同资源分块物理对照；预制底座和定制层尚未冻结
- 当前工程：[Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15) 在独立工作树开展openTPU ACT/MXU同资源拆分／合并物理对照。正式三块M9内布线、提取时序、电气及功能／资源证书通过；共同父层die与1662bit实际引脚一致。合并13通过全部物理／完整时序及独立父层功能／原生RC覆盖，setup +0.065642ns、hold +0.013027ns。拆分16／89789、合并17／89792及合并14／89776继续DRT；旧拆分15与低面积合并16仍有真实电容，严格失败封存。全部UNLIMITED，最终合格拆分、成对证据和总PPA尚待完成。详见[实验记录](experiments/issue-15-opentpu-comparison.md)。PR8的VECTOR/PG和89448形式验证不在本轮修改范围。
- 资料接入：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)；资料已进入 `main`，[PR #2](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/2) 已合并
- 当前资料：项目说明 v1.0、专题研究文档、来源笔记，以及五个参考项目七个案例的布线分析包；三份 HTML 报告、llaccel 引擎内部分析及远程服务器规则已通过 [PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4) 合入 `main`；工艺互连资料的逐层资源评估补充已一并提交
- 已确认边界：研究对象和主要问题已写入项目说明；具体工艺、Block 资源、定制层集合和工具链未冻结
- 关键限制：现有布线结果包含少量 RTL 片段，不含完整源工程、物理数据库、工具环境和日志，不能单靠本仓库复跑物理实现
- 最新工程续记（22:03 CST）：拆分16从实际提取结果完成167个宏输出隔离、213个驱动升级及hold／临界长线修复；合并17从仅剩1条真实电容的封存终态继续27个输出隔离、99个驱动升级。两组均已进入新DRT，最终资格继续按严格真实提取门槛验收。
- 下一步：完成同资源块内和父层实际对照及违例收敛；项目登记／看板的既有管理员待办继续保留
- 任务入口：[本仓库 Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues)
- 项目登记：[管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待审查；合并前状态为 pending
- Projects 入口：[组织总览看板](https://github.com/orgs/rayggxia-workspace/projects/1) 为管理中心配置的候选入口；本仓库无 `config/board.json`，当前凭据缺少 `read:project`，实际接入与本任务条目未核验，详见 Issue #3 交接

本页只记录全项目阶段和关键限制；具体任务进度以 Issue 和 PR 为准。
