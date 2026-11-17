# 七模型速度与功耗综合报告

关联 [Issue #291](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/291) / [PR #292](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/292)，负责人 Melodydt。2026-11-17，Asia/Shanghai。

[完整14页PDF](../../../docs/experiments/seven-model-speed-and-energy-evaluation.pdf)；本地输出 output/pdf/seven-model-speed-and-energy-evaluation.pdf。第13页为论文“验证与主要发现”的中英文建议稿，独立文本为paper-validation-findings.txt。原论文文件未修改。

## 内容与限制

- 七模型原短Prefill、Decode，当前逐token调度的512-token Prefill条件估计。
- 误差百分比给出局部ATT中间点与全部2-512已测点两种口径。全部已测点最大约4.46%-14.83%；完整P512独立误差未知，不以局部偏差替代它。
- 功耗给出短P2、第二步Decode各自的W、J/token和token/J，分别列片上已覆盖与片上已覆盖＋DDR两种小计。读DMA代理不计入基础小计；完整512-token Prefill功耗未评估。
- 功耗采用#280 v2.1无布线寄生口径。读DMA、部分控制、特殊算术/时钟/互连、DDR PHY和板级仍未覆盖，区间为标定端点，不是整体误差界。
- 未重跑仿真、FP32、RTL、综合或物理实现；独立序列验证继续按用户指令暂缓。

## 来源和复算

速度提交0550231032102ffde7d6cf24ea659f3fd9a9dbbe；功耗报告提交78812ea98ddc5714ea3e71d789b9800a4641bb7e，功耗数据提交3ce71cc712439da45580e7c89f8533e6a5ff0d25。combined-inputs.json记录9个输入散列；七模型能量与现有在线索引逐个匹配。combined-results.json保留未舍入数值，combined-power-units.csv提供28行功耗/能效记录。

```powershell
python -B work/Melodydt/291/build_combined_report.py
python -B work/Melodydt/291/verify_combined_report.py
pdftoppm -r 95 -png output/pdf/seven-model-speed-and-energy-evaluation.pdf work/Melodydt/291/tmp/pdfs/combined
```

依赖Python 3.7+、ReportLab 4.4.9、pypdf、Deng/Dengb字体。此次使用Codex捆绑Python与Poppler；生成器不修改#280工件或原速度文件。combined-inputs.json存在时强制校验，避免不经审查换用新输入。

实际验证：9个来源SHA、7模型14窗口匹配、28行三单位、168个独立Decimal端点、482个PDF单元格/警示文本、2段论文建议；14页全部渲染目检。第一次文本核验因检查串包含空格而失败，修正归一化后通过，未放松内容要求。管理结构检查通过，不替代业务/物理验证。

PDF SHA-256：11187931d2dea7129febba62bbf696301ddddd36a499bbfac36a0a68aa73f836。

本轮沿用独立task/291-seven-model-prefill-estimate分支。Windows根为无.git参考副本，本地新增仅work/Melodydt/291及指定output/pdf；公共文档在publication隔离准备，通过本任务分支提交。PR保持草稿未合并，独立审查人待指定；登记management-hub PR5 pending；缺config/board.json与Projects工具，看板unverified、同步pending，待具权限维护者处理。没有创建新远程作业或自动监测。
