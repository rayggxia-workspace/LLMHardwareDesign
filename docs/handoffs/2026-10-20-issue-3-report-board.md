# Issue #3：报告提交与看板待办

- 仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign
- 任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3
- 分支：`task/3-update-routing-reports`；起点 commit `19c9004`；本次成果 commit 和 PR 以 Issue #3 关联 PR 的提交回执为准。
- 成果：`ref-project/llm-routing/总报告.html`、`线长报告.html` 及引用资源；检查入口 `work/YUZE-LU/3/sync_reports.py`。
- 实际核验：2026-10-20 用当前 GitHub 身份 YUZE-LU 查询默认分支 registry、登记 PR 和 portfolio 配置；登记 PR [#5](https://github.com/rayggxia-workspace/management-hub/pull/5) 仍 OPEN，默认分支尚无 llm-hardware-design 登记，状态 pending。不重复登记。
- 看板配置线索：管理中心 `config/portfolio.json` 指向[组织 Projects #1](https://github.com/orgs/rayggxia-workspace/projects/1)；本仓库没有 `config/board.json`。GraphQL 读取实际看板字段时返回 `INSUFFICIENT_SCOPES`，缺 `read:project`；未改动凭据或权限。
- 看板事实 unverified；接入/同步 pending。没有读取或修改其他任务条目，也没有创建替代看板。
- 下一位处理人：具备 Projects 权限的管理员，具体人待指定。第一步：确认该私有看板受众适合本仓库，再核对真实字段和 Issue #3 是否已有条目；复用/加入条目并填写 `Project ID=llm-hardware-design`、实际 Status（PR 待审为 In review）。优先级尚未指定，不编造；读回字段并将证据补到 Issue/PR。
- PR 审查人待指定；只上传 PR，不自行合并。报告依赖检查不等同于重跑物理实现；源记录中的独立 STA 仍未完成。
