# #127 支线交付与恢复入口

更新时间：2026-10-27 CST（Asia/Shanghai）；具体提交时间见本批 PR 回执。

- 仓库：[rayggxia-workspace/LLMHardwareDesign](https://github.com/rayggxia-workspace/LLMHardwareDesign)，project_id：`llm-hardware-design`；负责人：YUZE-LU。
- 任务：[Issue #127](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/127)；依赖：#121 / PR #122；本批为诊断工具首批交付，未完成整个宏边界验收。
- 分支：`task/127-macro-boundary-qa`；固定起点 `8b62c2cf21f4d1b44e9a1f18e44713e0a73bec4d`。独立工作树：`D:/Data/电路实验/LLMHardwareDesign-worktrees/issue-127-macro-boundary-qa`。PR 暂以 `task/121-block-v1-twelve-layer` 为 base，便于只审查支线增量；正式 PR/交付 commit 记录在 Issue，避免文档自引用 commit。
- 正式代码与合同：`project/experiments/block_v1/macro_boundary_qa/`。本目录仅保存交接与合成测试回执。

## 已完成与实际验证

实现独立来源依赖检查、精确接口核验、可选时序/寄生数值合同比较，以及 Linux 原生产物的便携打包入口。不导入主线 verifier，未改主线脚本/RTL/状态，不提交服务器任务，不占额外节点。二进制大文件使用流式哈希。

已执行：

```text
python -B -m unittest discover -s project/experiments/block_v1/macro_boundary_qa -v
python -B scripts/check_project.py
git diff --check
```

首轮业务控制为 36 项 synthetic 测试通过；复验结果以本批最终 PR 回执为准。合成正例报告在 `synthetic-report.json`，其 passed 仅表示接收器逻辑控制通过，所有正式资格保持 false。生成用法：导入 `test_audit.Fixture` 在临时目录构造，再调用 `audit.audit(index_path)`；不使用任何真实候选文件。

## 未完成与下一步

1. 主线给出合格且不可变的同源 C8/T6K、A/C 原生 views/source/physical/prepare 目录和 budget/pipeline，明确现有 final DRC/功能接收状态。当前本侧未接收真实 bundle，不能宣称真实接口或宏边界通过。
2. 支线核验/保留来源与接口结果；发现 exporter 问题反馈主线，支线不平行修改主线 exporter。
3. 审查 flat/abstract 场景、测量覆盖和容差，然后补原生 STA/寄生适配与 producer 收据；当前仅实现声明式比较器，没有原生对照测量器。
4. 补 OBS 保守覆盖的几何证明、完整 endpoint/arc/electrical 覆盖及 SPEF 到 segment 的实际对应；不能把小 OBS 清单或自报 ledger 当作完整证明。
5. 在主线统一资源预算中安排实际接收，出中文真实验收报告。#127 不关闭、不标 done；本批 PR 审查不代替整体完成。

恢复第一步：读取 #127 最新 Issue/PR 回执和主线交接候选身份；运行本目录说明中的本地控制，再对 sealed bundle 运行 audit。无需重新派生分支或接管主线活动作业。

## 协作接入回执

规则：rayggxia-project-collab 1.0.0。项目登记沿用 pending（management-hub PR #5 未确认合并）；没有 `config/board.json`，当前工具不具备 Projects 查询/写入能力，条目/字段 unverified、同步 pending，管理员待指定。优先级/截止时间未指定，不代填。审查人待指定，由主线安排集成；不自行合并。

共用 `progress/YUZE-LU/STATUS.md` 与主线 `docs/STATUS.md` 正由主线更新，本支线使用本任务独立记录及 Issue/PR 回执，避免覆写并行进度。
