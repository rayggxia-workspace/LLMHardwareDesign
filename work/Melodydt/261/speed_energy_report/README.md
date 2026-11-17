# Issue #261 速度与能效报告来源包

2026-11-17（Asia/Shanghai），负责人 Melodydt。关联 [Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261) / [PR #262](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/262)。

## 交付

- 正式报告：`docs/experiments/issue-261-llm-speed-energy-report.pdf`。
- 逐模型原值及换算：`docs/experiments/issue-261-llm-speed-energy-data.json`。
- 输入文件、工具版本及成果校验值：`docs/experiments/issue-261-llm-speed-energy-manifest.json`。
- 本目录的 `sources/` 保存文献提取记录；`root_data.py` 保存其余原始数值和方法；`build_report.py` 生成 PDF、数据文件和校验清单。

本地交付文件在 `output/pdf/`；远端正式目录在 `docs/experiments/`。旧版21篇科研ASIC报告保留。新版覆盖32项论文工作、34个来源条目（两个GPU参照复用现有论文）、133组模型/配置/阶段记录；111组有原报、换算或条件换算的tokens/J。

## 复现与验证

在仓库根目录运行：

```powershell
python -X utf8 scripts/check_project.py
python -X utf8 work/Melodydt/261/speed_energy_report/build_report.py
pdftoppm -scale-to 1400 -png output/pdf/issue-261-llm-speed-energy-report.pdf work/Melodydt/261/speed_energy_report/final-page
```

实际使用 Codex 捆绑 Python 3.12.14、ReportLab 4.4.9、pypdf 6.21.4、Poppler；Windows 微软雅黑字体。跨平台时需显式调整字体路径。现有 `sources/` 优先；共享工作目录只用于首次收集来源，不是已有来源包重建的必要依赖。

实际验证：项目管理结构 PASS；133行正数/缺项和来源标识核验通过；ProQuant原始ms/mJ换算通过；CENT、Coffee、FPGA等关键算式经独立复核；33页Poppler渲染逐页检查完成，80个外链及内部索引页码核对通过。管理结构检查不代表业务或物理验收。

PDF SHA-256：`becfb58612e2fd912bea15830d233beea81f5ee7fd99ebe46d4d38e263f1cd05`。基线commit：`9a7309d0b5325a4f69cbc4cbdbd9463ab2890e4b`，分支：`task/261-llm-asic-benchmarks`。本任务目录独立使用；仓库根目录是无`.git`的本地管理参考副本，交付使用Melodydt GitHub连接与受保护的分支预期SHA更新。

## 证据限制和待办

- 所有内容是文献摘录或换算；无新服务器仿真、板测或流片。
- TOM/ROMA为总体功耗条件换算，VitaLLM片外能量未明；CHIME功耗图不一致，逐模型能效留空。
- CENT使用作者每token能量公式；Hummingbird不沿用归一化模型规模的能效；TerEffic仅decoder层且是MatMul-free/RNN变体。
- 数据缺项、不同阶段、模型质量、batch与能量边界均保留；不能把这些记录作为同条件排行榜。
- 项目状态保持in_review，独立审查人待指定。登记PR #5待合并；任务分支缺`config/board.json`且工具无Projects字段操作，实际看板状态未核验、同步待具权限维护者处理。
- 恢复第一步：读回Issue #261 / PR #262的最新head，再核对manifest和当前来源版本；不要覆盖其他任务分支或本地无关变更。
