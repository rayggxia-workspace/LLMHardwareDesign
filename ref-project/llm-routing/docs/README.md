# 布局与接口研究报告

- [Block 布局与接口分布报告](Block布局与接口分布报告.html)：五个 block 的布局与引脚图、数量/面积/层分布表、逐引脚筛选与 CSV 导出，以及接口聚集和方向约束讨论。图片和数据均内嵌，可单独离线阅读。
- [模块与接口报告](模块与接口报告.html)：Gemmini、openTPU、llaccel 的模块、数据流、端口和互连分析；图片与附件仍引用上一级 `outputs/`，分享时需要连同相关资源。
- 原包入口：[总报告](../总报告.html)、[线长报告](../线长报告.html)、[阅读说明](../阅读说明.txt)。

## 本次工作归属

- 整理日期：2026-10-23（中国标准时间，UTC+08:00）。
- 仓库：`rayggxia-workspace/LLMHardwareDesign`。
- 关联任务：[Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)；已有并发实验 [PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)。
- 本地 worktree：`D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-7-parallel-blocks`。
- 分支：`task/7-parallel-blocks`。图集包含主线 VECTOR 快照及该并发工作线的 GEMM、ACT、MXU、合并块快照，并非仅 Issue #15 的新物理对照结果。
- 初次归档为本地整理；2026-10-23 用户明确授权将两份 HTML、主线、并发及 H1 成果提交并合入 main，沿用 PR #8、#10、#17，实际合并状态以 PR 为准。
- `D:\Data\电路实验\LLMHardwareDesign` 是 `main` 的检出目录；本次通过现有 PR 合入后，以该目录为统一阅读入口。原实验工作树保留用于来源追溯，不改变 H2 工作树。

## 来源与边界

Block 报告复制自 `D:\Data\电路实验\block-placement-20261022-172122\block-layout-and-pins.html`，保留外部源文件作为绘图与打包产物；该 HTML 自身包含图片、CSV 和数据来源，不依赖这个绝对路径。原始脚本和导出数据仍在源目录。

模块报告由本工作树 `ref-project/llm-routing/模块与接口报告.html` 移入此目录，只调整 HTML 内相对资源 URL；正文、表格、图片数量和片内锚点保持不变。对应来源清单只更新报告路径，没有重算参考资料或更新历史完整性结论。

本次核验两份报告的本地引用及项目管理结构，不重跑 EDA。参考包的证据范围与各报告的快照/违例状态仍有效。看板与登记沿用原任务交接，本次不改变其状态。
