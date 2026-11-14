# #265 Qwen2.5-3B 整机 Decode 快速评估交接

2026-11-14（Asia/Shanghai）。负责人 Melodydt。仓库 [LLMHardwareDesign](https://github.com/rayggxia-workspace/LLMHardwareDesign)，[Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265)，[PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266)。任务分支 `task/265-qwen3b-system-evaluation`，快评源 `4a3fabade7687da46fe83091a4ab29eeb8b84dfa`，DDR 关闭修复与恢复源 `713461a04d3c831328b86b48d56f20665385e4fc`，原生入口验证源 `f89b9e2153737ffab9087e24e44ba53ec200ce69`。分支提交和审查状态通过 PR 读回。Windows 项目目录是文件副本，诊断用 `.local` 文件留在本地。服务器作业使用以下各自目录。

| 结果 | 范围及状态 |
| --- | --- |
| 110666 + 111176 | 110666 在 c64/node10 完成两步退休，Slurm 01:30:11，之后因读已关闭的 DDR 统计退出 1:0。111176 在 c64/node11 单核 4 秒通过真实 DDR 关闭回归及完整审计恢复。582 页及两次退休与 107361 一致，第二步 0.9568497254 tok/s |
| 110707 | c64/node7 单核，COMPLETED 0:0。512 输入位置和 127 个缓存反馈阶段。结构上界 1.3317315170 tok/s |
| D128 估算 | 127 间隔 143.489733463362 s，0.8850807437 tok/s。第二步吞吐误差 +0.05633%。校准仅使用 107361 第一步 |
| 111111 | c64/node1 两核，COMPLETED 0:0。105530 两种模式下前四页完整对账，随后 FFN 激活、PM 和首批三 P 服务接受 |

在已授权的 `yuzelu@10.129.166.172` 核对原件。

```bash
sacct -j 110666,110707,111058,111111,111176 -o JobID,NodeList,State,ExitCode,Elapsed
cd /public/home/yuzelu/Melodydt/runs/issue-265/qwen-fast-tlm-recovery-20261114-01
sha256sum -c output.sha256
tail -n 19 slurm-111176.out
cat recovered/execution.json recovered/timing-audit.json
```

其他路径、封存输入、代码和产物 SHA-256 在[整机回执](../../work/Melodydt/265/qwen-decode-evaluation-107361.json)。本地 `python -B scripts/check_project.py` 和 `python -B -m unittest discover -s project/experiments/instruction_cycle -p 'test_*.py'` 通过 30 项现有测试。九页同机计算原版 170 s、DDR 批推进 70 s、再启用原生整数运算 60 s。前两步完整回放使用 DDR 批推进。关闭修复通过真实双通道短回归。修复版完整两步及原生算术的完整回放仍待重跑。

恢复快评的第一步由 Melodydt 在相同部署、缓存口径、时钟和 DDR 下冻结长上下文的 C576/C639 独立完整 token 基线，在开始前冻结误差和速度判据，再取退休及分阶段用时对照。105530 原生周期建模从第 5 页首批三路 P 权重请求恢复。每种模式的第一组为 204 个读生命周期事件，普通读归档的第 781101–781304 行。后续需要并发权重、三 P/中间 SRAM 和 G 的发起及仲裁、64 组 WAIT 所覆盖的整个 FFN 页和跨页状态。第 6–8 页候选曾用归档 DDR 回调延迟及第 5 页终态作条件检查，独立原生链路仍待复核。候选源码和替身诊断当前留在本地 `work/Melodydt/265/`。

[`#234`](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234) 独立跟踪正式全程 P512/D128、数值验收和首 token 延迟。其 107343 作业截至本次快评核验 在 c64/node2 为 `RUNNING`；该作业沿用全请求 TLM。PR #266 的独立审查人待指定，Issue #265 保持进行中。项目登记 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待合并。仓库缺 `config/board.json`，具权限维护者需核验 #265 看板条目及 `Project ID=llm-hardware-design`、负责人 Melodydt、`In progress` 后再同步。
