# Issue #7 独立并发实验记录

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- 用户授权：并发运行、监视并同步记录，避免与主线冲突；允许同节点多实验；不设置人工时限。
- Issue：[候选 Block 与分层实现 #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU，状态沿用 `in_progress`；审查人、优先级待指定。
- 独立分支：`task/7-parallel-blocks`；本地工作树 `D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-7-parallel-blocks`。
- 代码：[parallel_blocks](../../project/experiments/parallel_blocks/README.md)。主线 `task/7-block-routing`／[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8) 继续负责 VECTOR 和 PG 修复。本会话不修改其文件、输入、时限或作业。

## 实验与资源

| Case | 对象与目的 |
| --- | --- |
| `llaccel-gemm` | 原完整 GEMM，含双缓冲、累加、尾处理及写回 FIFO，固定 v1 `EPILOGUE_FUSION=0`；补充第二种计算 Block 的独立物理结果 |
| `opentpu-act` | small ACT 独立实现，保留宽读和写入状态／全部容量；为 O0-W 准备 |
| `opentpu-mxu` | small MXU 独立实现，保留任务、取数、FIFO、计算与 FP32 后处理；为 O0-W 准备 |
| `opentpu-act-mxu` | 同配置 ACT＋MXU 的原连接内化，作为 O1-W 合并实现；不加缓存、不串行化、不加周期 |

一个 c64 节点分配 64 CPU，四个 step 各 16 核，以 `srun --exclusive --cpu-bind=cores` 隔离。任务名 `lyz-par4`。调度器使用 `select/cons_tres`／`CR_CORE,CR_PACK_NODES`、`task/cgroup`；实际 node／CPU 与 `UNLIMITED` 以提交回执、allocation 和 step 记录为准。主线正在使用 node3，本批选择当时空闲的 node7。

## 验证与边界

- 主线原回归／形式结果不自动授予新包装或网表；每路执行自身 elaboration、`hierarchy -check`、`check -assert`，记录真实端口及 RAM 实例清单。
- 源 RTL 不改，包装不加寄存器；openTPU 合并连接对照原 `otpu_slice` 的 `u_act`／`u_mxu`。物理流程显式关闭阶段 LEC，因此不声称门级等价；主线默认 LEC 不取消。
- openTPU 使用原 revision 的 synthetic fakeram LEF／Liberty 研究模型，不是实际 SRAM、GDS 或签核；分开与合并使用同一模型规则和资源参数。工具 DRC／STA 均按实际报告分别记录。
- 四路产物不能直接相加后宣称已完成 O0-W 顶层；还需分开宏的实际顶层布线、同边界时序覆盖、面积／时钟／PDN／通道成本。H2 固定资源、多计算图及受限定制尚未执行。

## 执行回执

准备中；提交后回填实际作业与每路状态。机器记录保存于 `project/experiments/parallel_blocks/results/`，远程大文件保留在独立 attempt。

## 接入与交付

复用 Issue #7，不接管其整体状态。登记沿用管理中心 PR #5 的 pending 记录；本项目无 `config/board.json`，已知 Projects 查询缺 `read:project`，实际看板 unverified／同步 pending，不扩权限或另建看板。并发成果将保存独立 branch commit 和同 Issue 回执，供主线合入现有 PR；不覆盖主线回执。最终状态仍以远端核验为准。
