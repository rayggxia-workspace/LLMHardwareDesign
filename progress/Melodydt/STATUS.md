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


## 2026-11-17（Asia/Shanghai，UTC+08:00）

- [Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261) / [PR #262](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/262)：按用户扩大范围，交付[33页速度与能效报告](../../docs/experiments/issue-261-llm-speed-energy-report.pdf)、133行数据、来源与复现包。32项论文工作，111组有原报或带限定的tokens/J。
- 保留精度、模型、batch、阶段、输入/输出、内存和能量边界；修订CENT、Hummingbird、VitaLLM、CHIME等口径。旧版21项ASIC报告保留。
- 实际验证：管理结构PASS；算式/数值/来源检查通过；33页Poppler视觉检查和80外链及索引核对通过。PDF SHA-256 `becfb58612e2fd912bea15830d233beea81f5ee7fd99ebe46d4d38e263f1cd05`。未做新仿真、板测或物理验收。
- 分支task/261-llm-asic-benchmarks，基线9a7309d0b5325a4f69cbc4cbdbd9463ab2890e4b；独立任务目录work/Melodydt/261/speed_energy_report。线上提交与CI以PR最新回执为准。
- 下一步：独立审查文献数据、能量边界和图读数，审查人待指定。Issue保持in_review；登记PR5读回仍待合并；缺board.json和Projects操作能力，看板未核验/同步待维护者处理。

## 2026-11-17 J/token补充（Asia/Shanghai，UTC+08:00）

- [Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261) / [PR #262](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/262)：为33页报告中的111组能效记录增加J/token列及倒数推导说明；总记录仍为133组，22组缺值不补算。
- 采用同记录的J/token = 1 / tokens/J；保留模型、阶段、能量边界、批量、设备数量、原报舍入、估读和条件换算。CENT保留原作者聚合公式；平均能效倒数不称为逐请求能耗算术平均。
- 实际验证：管理结构PASS；111条倒数和22条缺值一致性通过；24条ProQuant与9条CENT原始能量回算通过；33页逐页渲染检查及两页换行修正后复查通过，80外链。PDF SHA-256 `5e7a68c3d3765da46baefc246d24d4939164520dedfa13d2b171926d897f9b29`。无新服务器仿真或板测。
- 分支task/261-llm-asic-benchmarks，本次基线33c9743b8a50362501accb56bba08796e6e0f88d；任务目录work/Melodydt/261/speed_energy_report，本地输出output/pdf。线上commit/检查结果见PR回执。
- 下一步：待指定独立审查人复核。Issue保持in_review；登记PR5仍pending；看板实际状态unverified、同步pending，待具权限维护者处理。恢复先读取Issue/PR最新head及manifest。
