# Issue247 原生P前三项优化接续

2026-11-09，Asia/Shanghai；负责人 Melodydt，独立审查人/优先级待指定。

- 仓库 https://github.com/rayggxia-workspace/LLMHardwareDesign ，[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)，[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。继续 `task/242-r-load-bounds`，实施起点 `3a66f8de0889925846e9d737690e2d9e297bb173`。
- 本地正式源是非Git快照 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`。通过本人 GitHub tree/commit/ref 租约上传，未宣称本地 checkout/pull。并行工作隔离在外层 `work/Melodydt/247/popt-policy`、`popt-memory`、`popt-context`；仅根整合正式文件。
- 起点458个PR文件Git blob与本地逐项一致，无无关变更；保留既有R修复及研究，不操作ref-project。
- 本轮修改P仲裁、可选bank并发、可选M contexts及B-only LOAD。默认参数保持旧语义。数据S仍16KiB，未实现48/64KiB扩容、真正独立64B读+64B写或外存自适应预取描述符控制。
- [设计与具体做法](../experiments/issue-247-p-native-optimizations.md)。正式源 `project/rtl/`，服务器运行器 `project/experiments/p_native_opt/`。
- 本地 `python scripts/check_project.py` 通过仅管理结构；已完成代码生成与Python AST，EDA未在本地执行。当前尚无本轮仿真作业受理回执；后续上传精确源码后运行独立Slurm作业，立即补充job/commit/目录/命令/SHA。
- 历史run01–09均终态，本轮不会覆盖这些目录。新run10位于本人 `/public/home/yuzelu/Melodydt/issue247-area-speed/`，2026-11-09已确认尚不存在；未提交前不称已运行。
- 源码修改使历史研究的“当前生产源必须与冻结SHA相同”条件不再成立；旧研究冻结源与结果继续保留于各原run，不改旧检查器来掩盖漂移。本轮独立记录新源锁并重跑受影响P业务验证。
- 状态in_progress，未done。登记management-hub PR5 pending；缺board.json/Projects能力，unverified/同步pending，处理人待指定；历史CI无step失败原因待管理员核实。未配置自动监测。

恢复第一步：核对PR实时head与本轮实际源码commit，检查本交接追加的run受理/终态回执；若已提交不得重复提交。随后查看结果JSON及所有失败组件日志，保留失败现场，在新run修复复跑。成功判据为主作业COMPLETED0:0、四组件通过、真实数值/回写ACK/守恒与负例证据齐备，并通过SHA复核；这不等于物理或整模型验收。
