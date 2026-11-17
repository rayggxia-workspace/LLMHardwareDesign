# 大模型推理速度与能效综述

2026-11-17（Asia/Shanghai） · 负责人 Melodydt · [Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261) · [PR #262](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/262)

[33页PDF报告](issue-261-llm-speed-energy-report.pdf)收录32项论文工作、133组模型/配置/阶段记录，111组附原报、换算或条件换算的tokens/J，并新增同记录的J/token；其余22组能量数据继续留空。范围包括科研ASIC、CIM/PIM、FPGA与论文实测GPU参照，保留原2B–4B调研中的21项工作。

[逐模型数据](issue-261-llm-speed-energy-data.json)包含原始值、阶段、条件、来源和换算；[校验清单](issue-261-llm-speed-energy-manifest.json)记录输入SHA-256、生成工具版本与PDF校验值；[来源和复现包](../../work/Melodydt/261/speed_energy_report/README.md)提供重建命令及范围。

## 阅读边界

- J/token = 1 / tokens/J，表示每个token消耗的焦耳数，越低越省能量；tokens/J是能效，越高越省能量。倒数采用数据中tpj值，显示约3位有效数字，继承原报舍入、图估读、条件换算和聚合边界。prefill按输入token，decode按生成token；端到端及作者特殊聚合口径分别注明。
- 实测、综合/周期仿真、图估读和条件换算分开。功耗注明芯片、外存、模块、板卡或系统；不能按本表直接进行跨模型总排名。
- 纠正/保留VitaLLM能效算术差异、CENT聚合分母、Hummingbird归一化能效、CHIME功耗不一致等问题。未披露的绝对能效不从TDP/TOPS或单算子功耗补算。

## 实际验证

本地管理结构检查PASS。133行来源标识与数值、111条倒数换算、22条缺值一致性、24条ProQuant和9条CENT原始能量回算复核通过。33页Poppler渲染逐页目视检查、80个外链和内部索引页码检查通过。无新服务器仿真、RTL/物理实现或板测。

PDF SHA-256：`5e7a68c3d3765da46baefc246d24d4939164520dedfa13d2b171926d897f9b29`。本次J/token补充基线commit `33c9743b8a50362501accb56bba08796e6e0f88d`，任务分支 `task/261-llm-asic-benchmarks`；本地输出在 `output/pdf/`，远端正式成果在本目录。旧版Markdown/PDF保留作历史快照。

## 交付与接续

规则rayggxia-project-collab 1.0.0；项目llm-hardware-design；负责人Melodydt。当前任务待独立审查，不标done、不合并PR。项目登记[PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)于2026-11-17读回仍open/unmerged。任务分支缺config/board.json，工具不提供Projects条目操作，看板实际状态未核验、同步待具权限维护者（待指定）处理。

本地仓库目录是无.git的管理参考副本，本轮仅使用本任务辅助目录和输出文件；远端通过Melodydt连接上传，并以预期head保护分支更新。恢复时先读回Issue/PR最新head和检查结果，再核对manifest；线上CI结果另在最终PR回执记录。
