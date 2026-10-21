# Issue #7：登记与看板核验交接

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- 仓库：<https://github.com/rayggxia-workspace/LLMHardwareDesign>。
- 任务：<https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7>；负责人 YUZE-LU。
- 工作分支：`task/7-block-routing`；从 `origin/main` 的 `19c900462c60bc55f534ceabc7eedc64dad4a0a6` 创建独立工作树。成果 commit 与 PR 以 Issue 最终回执为准。

## 本轮实际核验

`gh api user --jq .login` 返回 `YUZE-LU`，GitHub 连接器亦以该账号操作；目标私有仓库可读写。

管理中心登记 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 本轮读回为 `OPEN`、`mergedAt=null`；继续记录为 `pending`，没有另建登记 PR。

本仓库没有 `config/board.json`。按历史交接指定的候选 [组织看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1) 发起只读 GraphQL 查询，返回 `INSUFFICIENT_SCOPES`，缺少 `read:project`。因此未读取看板真实字段、Issue 条目或当前状态，也没有执行加卡或字段同步。现有 GitHub 插件未提供 Projects 操作工具。

看板状态：`unverified`；加卡与同步：`pending`。本轮没有扩大令牌权限或新建替代看板。

## 恢复动作

由具备该看板访问和编辑能力的项目管理员处理，具体人员待指定：

1. 确认看板 #1 与本项目及其私有资料的受众匹配，并确认 `config/board.json` 应采用的实际配置。
2. 查询 Issue #7 的既有条目，复用既有条目或在授权范围内加卡。
3. 核验 `Project ID=llm-hardware-design`、`Status`、负责人 YUZE-LU；优先级未指定，不猜填。
4. 根据 Issue 的实际唯一 `status:*` 标签同步状态，读回并在 Issue/PR 回执补看板 URL、条目 ID、字段与时间。
5. 登记 PR 合并后核对默认分支记录，再把登记从 `pending` 改为 `registered`。

本轮研究成果、物理作业、验证与未完成项的继续入口为 Issue #7 和 `project/experiments/block_hierarchy/`；这些工程工作继续推进，不因看板缺权限而停止。没有审查、合并及验收证据时不得把 Issue 标为 `done`。
