# Issue247 旧评价体系证据

负责人Melodydt，2026-11-10T00:50+08:00；[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。源码 `3e62b85c8da19caca31784cb380c40d323295157`，run15/101800，COMPLETED 0:0，00:03:22。

[正式报告](../../../../docs/experiments/issue-247-legacy-metric-evaluation.md)、[21场景分析](analysis.md)、[机器摘要](summary.json)、[原件索引](index.json)。本目录只保存本轮轻量原件和可逆gzip+base64；全量生成源码/二进制在本人服务器 `/public/home/yuzelu/Melodydt/issue247-area-speed/run15`。历史run01/04/05/12原件作为服务器根目录只读输入保存并SHA绑定；不改历史证据。

从仓库根目录执行 `python -B work/Melodydt/247/legacy-metric-eval/verify.py` 核验原件SHA、63回收输出、63当前源码、21日志及分析直接比值。分析脚本读取已通过回执，无仿真。`index.json`列原文/存储SHA，`summary.json`列实际通过项目；源/input SHA和工具版本见run15清单。原有225kernel、4validation、5smoke日志随回收证据保存。

另将提交包内16份冻结输入归档至 `run15/frozen-inputs/`；`index.json` 的 `input_artifacts` 逐项记录来源和SHA，不混入74份回收原件计数。本地验证实际校验全部16份输入，并重新调用独立审计器，对21场景和四份历史结果逐字段核对，不只相信服务器通过标志。

旧S32/S96/K256模型，3.496是理想独立读写+ctx8的条件目标；4.467/4.547是48/64KiB的prefill2，非decode。四个1RW bank不等于模型理想端口，不将本轮数字当生产RTL完整模型实测。生产RTL未再修改，扩容未实装。登记pending、看板unverified/同步pending、待独立审查，不done。无活动作业/自动监测。
