# Issue175：局部 Block 设计与三模型双层图册

- 任务：[Issue #175](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/175)，负责人/实际账号 YUZE-LU，规则 rayggxia-project-collab 1.0.0。
- 分支：`task/175-local-block-design`；基线 `4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609`，独立 worktree；不修改其他分支/任务。
- 正式成果：[设计宗旨及五候选](../../../docs/LOCAL_BLOCK_DESIGN.md)、[七宏图](../../../docs/local-blocks/SEVEN_MACRO_MODEL_FLOWS.md)、[组合图](../../../docs/local-blocks/COMPOSITE_MODEL_FLOWS.md)、[数值/来源边界](../../../docs/local-blocks/SOURCES_AND_GAPS.md)、[决策0006](../../../docs/decisions/0006-local-configurable-blocks.md)。
- PR：创建后在此记录真实链接；提交 SHA 以关联 PR 当前 HEAD 及其回执读回为准，不用自引用文件哈希冒充最终提交。
- 个人进度：[YUZE-LU](../../../progress/YUZE-LU/STATUS.md)。本轮文档进入审查，不合并、不标 done；审查人/优先级待指定。

## 辅助文件与实际验证

- [VALIDATION.md](VALIDATION.md)：实际命令、图/来源核对、未执行项。
- [render-receipt.json](render-receipt.json)：13图渲染尺寸、标签检查及工具版本；PNG 在仓库外临时目录，只提交 SVG。
- [validate_docs.py](validate_docs.py)：本地链接、固定输入 blob/字节、图/产物摘要的只读检查。
- [manifest.json](../../../docs/local-blocks/manifest.json)：正式图与来源索引。

## 协作接入及下一步

项目 `llm-hardware-design`、仓库 `rayggxia-workspace/LLMHardwareDesign`；管理中心[登记PR5](https://github.com/rayggxia-workspace/management-hub/pull/5)本次读回 open/merged=false，登记 pending。无 `config/board.json`，实际 Issue175 Projects 查询被 `INSUFFICIENT_SCOPES/read:project` 拒绝；看板 unverified、同步 pending，管理员待指定，详见[持久交接](../../../docs/handoffs/2026-11-03-issue-175-projects.md)。未更改账号/权限，也未另建看板。

下一步：用户/指定审查人审查局部粒度、开放程序边界、私有 S 容量和三模型候选路线；通过后再交给相关实施任务逐项落实数值、控制、S/端点与最终组合 P&R。这个 PR 不实现它们，不接管 #151/#162/#166，不启动服务器任务。
