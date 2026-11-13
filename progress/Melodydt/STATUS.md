# Melodydt 的进度

## 2026-11-12 19:17（Asia/Shanghai，UTC+08:00）

- 任务与负责人：[Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261)，Melodydt。
- 已完成：从 PR #251 的 `9abd46f5cbb4534bcfc614571ccd6d402ad11882` 创建 `task/261-llm-asic-benchmarks`，整理 2B–4B 模型的公开 ASIC/NPU 解码吞吐和测试条件。见[调研报告](../../docs/experiments/issue-261-llm-asic-benchmarks.md)。
- 交付：[PR #262](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/262)，基分支 `task/250-w8a16-base-contract`，待独立审查。本地管理参考副本无 Git 元数据。远端文件由 Melodydt 的 GitHub 连接提交。
- 验证：在本地参考副本执行 `python -X utf8 scripts/check_project.py` 通过。文档表列、22 个 HTTPS 引用格式、两处换算、行尾空白通过；核查论文和厂商数据。未启动服务器仿真或板测。
- 下一步：审查来源、计时阶段、硅片与仿真证据及图读数。用于同条件性能验收前，仍需同模型、量化、带宽和 512 输入/128 输出的证据。
- 阻塞与待同步：项目登记 PR #5 待合并。当前没有可用 Projects 条目和字段工具，适用看板待核验、同步待执行，由具权限维护者处理。恢复入口见调研报告的协作交接。

## 2026-11-12 21:43（Asia/Shanghai，UTC+08:00）

- 按用户补充口径使用各论文的原始工况，扩展 TOM、MARCA、MARCA-v2、Platinum、HB-PIM、Titanus、Apple AFM 和手机 NPU 阶段测量，补齐已有论文的 PPA、位宽、内存和计时边界。
- [Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261) · [PR #262](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/262) · [扩展报告](../../docs/experiments/issue-261-llm-asic-benchmarks.md)。待独立审查。
- 验证：本地参考副本 `python -X utf8 scripts/check_project.py` 通过，4 个表格、36 个 HTTPS 引用的格式、关键换算和行尾空白通过。实际服务器作业和板测未执行。
- 审查重点：核对硅片、仿真及算子数据的可比范围，确认后续引用使用原表工况。看板和登记交接见报告。线上检查以 PR 的运行回执为准。

## 2026-11-12 22:10（Asia/Shanghai，UTC+08:00）

- 依据用户更新的范围，调研报告现聚焦科研 ASIC。新增 ProQuant、NVLLM、P³-LLM、PALUTE、CHIME、TriGen、FlexPosit、Pimba、MX-like Tensor Core 共九篇，记录模型、精度、上下文、吞吐、面积、功耗和证据范围。
- [Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261) · [PR #262](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/262) · [调研报告](../../docs/experiments/issue-261-llm-asic-benchmarks.md)。独立审查待执行。
- 本地参考副本的 `python -X utf8 scripts/check_project.py` 通过。报告 5 张表、39 个不同 HTTPS 引用格式和 ProQuant 的速度/功耗换算通过校验。图读数从原论文 PDF 核对。未启动服务器仿真或板测。
- 审查重点为 NVLLM 64-token 上下文、P³-LLM 4K 多 batch 和 ProQuant 硅片测量与外存模拟的计时边界。登记及看板同步待维护者处理，见报告的协作交接。

## 2026-11-13 12:52（Asia/Shanghai，UTC+08:00）

- [Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261) · [PR #262](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/262) · [9 页科研 ASIC PDF](../../docs/experiments/issue-261-llm-asic-benchmarks.pdf)。
- 将调研快照 `893622cb1919c1c5b86734cdd9f5f50ccf4028ec` 整理为 21 篇论文索引、逐模型数据与 PPA。根据原图补齐 EdgeCIM INT8 和逐模型面积、Pimba 四个 2.7B 模型的批量吞吐，均标为图读数。
- PDF 由 ReportLab 4.4.9 生成，SHA-256 `39bd02b431bccf6c02101992ff8f675528d3560b1a1daf360c8c4089ea758a8b`。Poppler 逐页渲染、pypdf 6.21.4 核验页数及链接，项目结构检查通过。文献整理未执行新仿真或板测。
- 独立审查待执行。登记 PR #5 待合并，Projects 实际条目未核验，待具权限维护者处理。
