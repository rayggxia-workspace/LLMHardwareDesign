# Issue #7 并发实验进度补充

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- 任务：[Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU；本补充由用户新授权的并行会话维护。主线的 `STATUS.md` 由原会话维护，此处使用独立文件避免冲突。
- 已完成：独立工作树及 branch `task/7-parallel-blocks`；作业 89458 在 node7 同时跑四个 16 CPU step，总计 64 CPU，实际 `UNLIMITED`；GEMM 与 openTPU ACT／MXU／合并版均通过 elaboration，后三路 SRAM 模型类型与实例数一致。
- 终态：四路及批次 89458 均 `COMPLETED 0:0`，批次 41:33；各路 DRC／天线 0，setup／hold WS 均正、TNS 均0，最大电容违例仍为 GEMM 49、ACT 2、MXU 12、合并41，四路均未通过完整电气验收。
- 审计：89460 一次性依赖审计已 `COMPLETED 0:0`／21秒；438个产物条目校验全部通过。已取回[冻结终态](../../project/experiments/parallel_blocks/results/parallel-blocks-01-completion.json)，字节 SHA 与计算节点记录一致 `4e6d7c24518f8ef55d45b57eb5325d0e7329dfc773273f8c339c4496fd885903`。
- 诊断：新增89478／node7／1CPU／UNLIMITED，已完成，仅在计算节点读取同一镜像的 ORFS 源码。放置优化时四路电容违例均0，最终提取后出现违例；本轮 repair_design 未设置 CAP_MARGIN，流程确认支持该裕量。只形成候选解释和下一轮对照方案，未发起新PNR、未宣称修复。
- 监视改进：明确打印校验与失败门槛，保存逐阶段电容数量、最终违例原文和 Slurm 资源账单。实际重新采集、核对行数49／2／12／41与metrics一致；[轻量索引](../../project/experiments/parallel_blocks/results/parallel-blocks-01-latest.json)。临时侧聊不支持后台助手唤醒，未创建定时通知。
- 限制：synthetic SRAM 研究模型、`LEC_CHECK=0`、未做源到物理网表完整等价和独立系统签核；分开两宏尚未重连顶层，无 H2 结论。
- 交付：[草稿 PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)，补充主线 PR #8，Refs #7；执行 runner `2568623f91f871e139c4b7544d00d0181ce4cb01`，监视／审计代码快照 `017a0a7e16c40e47a837e75101789c57b34625e6`。每次实际执行以计算节点输入 SHA 为准，后续 commit 不覆盖运行历史。
- 验证：结构／Python／Bash／Git whitespace 检查通过，增强监视器实际运行及SHA／行数核对通过；前一交付`7908208`的 Project structure CI success，当前提交CI以PR回执为准，非物理签核。
- 下一步：ACT固定16线程先对照电容裕量10／20与原0基线，再决定其它三块是否重跑；补齐包装回归／等价及边界驱动负载，再推进ACT＋MXU分开硬块的实际顶层。尚无新参数执行结果。账单CPU使用／分配约22.1%，短ACT占槽结束后长期空闲，可另行测试线程数与动态补位，不把未测配置称最优。详见[实验记录](../../docs/experiments/issue-7-parallel-blocks.md)。更新同一条[固定 Issue 回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7#issuecomment-6312241685)，由主线决定合入顺序。审查人／优先级待指定，整体 Issue 仍以主线实际状态为准，不自标 done／合并。
- 接入：管理中心 PR #5 OPEN，登记 pending；无 board.json／缺 read:project，看板 unverified、同步 pending，管理员待指定。详见[恢复交接](../../docs/handoffs/2026-10-21-issue-7-parallel-blocks.md)。
