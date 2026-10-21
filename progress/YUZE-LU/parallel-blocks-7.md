# Issue #7 并发实验进度补充

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- 任务：[Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU；本补充由用户新授权的并行会话维护。主线的 `STATUS.md` 由原会话维护，此处使用独立文件避免冲突。
- 已完成：独立工作树及 branch `task/7-parallel-blocks`；作业 89458 在 node7 同时跑四个 16 CPU step，总计 64 CPU，实际 `UNLIMITED`；GEMM 与 openTPU ACT／MXU／合并版均通过 elaboration，后三路 SRAM 模型类型与实例数一致。
- 首个结果：ACT／89458.1 `COMPLETED 0:0`、5:59；DRT／天线 0、setup +1.22599 ns／hold +0.0322719 ns、TNS 0，最大电容仍有 2 个违例。其它三路继续实现，不能提前标成功。
- 监视：当前快照见[实验记录](../../docs/experiments/issue-7-parallel-blocks.md)与[轻量索引](../../project/experiments/parallel_blocks/results/parallel-blocks-01-latest.json)。89460 为1 CPU、`afterany:89458`、`UNLIMITED` 的一次性终态／哈希审计；临时侧聊不支持后台助手唤醒，未创建定时通知。
- 限制：synthetic SRAM 研究模型、`LEC_CHECK=0`、未做源到物理网表完整等价和独立系统签核；分开两宏尚未重连顶层，无 H2 结论。
- 交付：[草稿 PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)，补充主线 PR #8，Refs #7；执行 runner `2568623f91f871e139c4b7544d00d0181ce4cb01`，监视／审计代码快照 `017a0a7e16c40e47a837e75101789c57b34625e6`。每次实际执行以计算节点输入 SHA 为准，后续 commit 不覆盖运行历史。
- 验证：结构／Python／Bash／Git whitespace 检查通过；`017a0a7` 的 Project structure CI success，非物理签核。
- 下一步：读取四路终态及89460 `completion.json`／SHA，分别保留时序、电气及PSM失败；更新[固定 Issue 回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7#issuecomment-6312241685)，由主线决定合入顺序。审查人／优先级待指定，整体 Issue 仍以主线实际状态为准，不自标 done／合并。
- 接入：管理中心 PR #5 OPEN，登记 pending；无 board.json／缺 read:project，看板 unverified、同步 pending，管理员待指定。详见[恢复交接](../../docs/handoffs/2026-10-21-issue-7-parallel-blocks.md)。
