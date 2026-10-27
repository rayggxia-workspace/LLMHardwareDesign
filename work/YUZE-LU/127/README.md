# #127 支线交付与恢复入口

更新时间：2026-10-27 CST（Asia/Shanghai）；各批次时间与 commit 见 PR 回执。

- 仓库：[rayggxia-workspace/LLMHardwareDesign](https://github.com/rayggxia-workspace/LLMHardwareDesign)，project_id：`llm-hardware-design`；负责人：YUZE-LU。
- 任务：[Issue #127](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/127)；依赖：#121 / PR #122；交付：[PR #128](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/128)，未完成整个宏边界验收。
- 分支：`task/127-macro-boundary-qa`；固定起点 `8b62c2cf21f4d1b44e9a1f18e44713e0a73bec4d`。独立工作树：`D:/Data/电路实验/LLMHardwareDesign-worktrees/issue-127-macro-boundary-qa`。PR 暂以 `task/121-block-v1-twelve-layer` 为 base，便于只审查支线增量；正式 PR/交付 commit 记录在 Issue，避免文档自引用 commit。
- 正式代码与合同：`project/experiments/block_v1/macro_boundary_qa/`。本目录保存交接、合成控制、真实原生控制及候选诊断摘要；大体积原始产物留在授权存储。

## 已完成与实际验证

实现独立来源依赖检查、精确接口核验、可选时序/寄生数值合同比较、Linux 原生产物便携打包、实际 SPEF 图清单、原生 STA 双进程对照与证据复算、OBS 精确矩形并集覆盖及 ODB 导出入口。不导入主线 verifier，未改主线脚本/RTL/状态，不提交服务器任务、不占额外节点。二进制大文件使用流式哈希；本机 WSL 运行原生实验，真实大候选每进程一线程。

已执行：

```text
python -B -m unittest discover -s project/experiments/block_v1/macro_boundary_qa -v
python -B scripts/check_project.py
git diff --check
```

首轮为 36 项 synthetic 测试；第二批增至 73 项，另实际执行原生控制及 T6K 候选诊断。最终数量以测试回执为准。`synthetic-report.json` 的 passed 仅表示接收器逻辑控制通过，所有正式资格保持 false。生成用法：导入 `test_audit.Fixture` 在临时目录构造，再调用 `audit.audit(index_path)`；不使用任何真实候选文件。

第二批真实发现：run164 T6K A/C 均未通过 Liberty PG direction 门；A 的原生对照有超差，且 exact final.v/SPEF 中二极管实例/网络无法完整对应。失败不豁免，原生数字不能归因成单一模型误差。详见本目录真实诊断报告与 JSON 摘要。小 DFF 控制说明，导出输入驱动上下文和输入线阻敏感性需要分别检查，固定 transition 的独立诊断变体也不能普遍消除误差。

## 未完成与下一步

1. 主线修复或明确 PG 表示合同；提供完整物理 timing 源或 ODB flat 对照，解决源 V/SPEF 中二极管无法对应的问题。支线保留全部失败，不平行修改主线 exporter。
2. 在主线统一预算内执行只读 ODB 几何导出，运行已实现的 OBS 精确覆盖；支线已通知主线安排资源，尚无实际 ODB coverage 结果。
3. 审查正式 flat/abstract 场景、全部适用弧/例外/corner/electrical 覆盖和容差。现有原生测量是 worst-per-boundary-edge 聚合，不能冒称全部弧等价。
4. 对修正后的 T6K、合格 C8 A/C 新候选逐一复验，补真实寄生归属与完整适用覆盖。不能把读回成功、小 OBS 清单、无 active-net 判断的 annotation 清单或自报 ledger 当作完整证明。
5. 主线负责生产、物理/功能接收与正式冻结，支线交付可复算的通过或失败报告。#127 不关闭、不标 done；本批 PR 审查不代替整体完成。

恢复第一步：读取 #127 最新 Issue/PR 回执与本目录真实报告，核对 run160/161/164 来源；先复算现有失败，再接收主线修正版。不要从旧首批记录推断“尚无真实数据”。无需重新派生分支或接管主线活动作业。

## 协作接入回执

规则：rayggxia-project-collab 1.0.0。项目登记沿用 pending（management-hub PR #5 未确认合并）；没有 `config/board.json`，当前工具不具备 Projects 查询/写入能力，条目/字段 unverified、同步 pending，管理员待指定。优先级/截止时间未指定，不代填。审查人待指定，由主线安排集成；不自行合并。

共用 `progress/YUZE-LU/STATUS.md` 与主线 `docs/STATUS.md` 正由主线更新，本支线使用本任务独立记录及 Issue/PR 回执，避免覆写并行进度。
