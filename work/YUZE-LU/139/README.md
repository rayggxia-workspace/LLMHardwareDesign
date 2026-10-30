# Issue #139：计算积木规划文档同步

- 仓库：rayggxia-workspace/LLMHardwareDesign；project_id：`llm-hardware-design`。
- 任务：[Issue #139](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/139)；实际身份/负责人：YUZE-LU；审查人、优先级待指定。
- 独立分支：`task/139-compute-block-docs`，基于 `main` 的 `6a681d6632e7f7be537ff96eae1827df834bcfe8`。未切换或修改 #121/#130 等现有工作树。

## 成果

- [M/V/R 边界、位宽与 R 保留分析](../../../docs/COMPUTE_BLOCK_BOUNDARIES_2026-10-30.md)。本机原 `V拆分与MV位宽压缩讨论总结_2026-10-30.md` 已重命名为 `MVR计算积木边界与位宽讨论总结_2026-10-30.md`，保留原内容并加入 R 分析；本机副本与仓库正文一致。
- [项目说明](../../../预制计算底座项目说明_v1.0.md) 增加 2026-10-30 架构规划补记；保留原文件名作为稳定入口与原版本记录。同步 README、导读、简介、架构及共同状态。
- [决策 0005](../../../docs/decisions/0005-compute-block-v-split-r.md)：V 三宏、首版 R 保留、各种一个实现、逐宏最终布局布线。

原本地分析稿修改前 SHA-256：`6502a0576c048aacdbb76da538aecc69a9211b12f3f712c9b31a2ada184767f6`。旧稿的数值/部分和候选和证据边界保留；新增 R 内容绑定固定源码提交，不复制未经封存的运行结果。

## 实际验证与限制

实际命令和结果见本目录 `validation.json`。检查仅针对本次文档与管理结构；未运行模型、RTL、综合、布局布线或服务器作业。无源码/实验配置变更，不把文档同步写成新宏实现完成。

## 协作状态与恢复入口

规则版本：rayggxia-project-collab 1.0.0。PR/最终 commit 及线上检查以 Issue #139 的交付回执为准；待独立审查，未合并前不标 done，不自审/自合并。

登记沿用 management-hub PR #5 的 pending 证据；提交时再读回。无 `config/board.json`，仅有 `config/status-mapping.json`，当前 GitHub 连接工具不提供 Projects 条目读写：条目/字段 unverified，同步 pending。管理员（待指定）需先确认实际目标看板，再补充配置、加入/复用 #139 条目，设置 Project ID=`llm-hardware-design`、实际 Status 并读回；未定优先级/日期不代填。

下一步：独立审查并合并本次文档；后续实现由主线按新规划明确规格和逐宏验收，原 #121/#130 状态与运行任务保持原有事实。本任务不负责新建服务器实验。
