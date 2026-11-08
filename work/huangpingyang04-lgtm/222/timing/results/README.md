# 数据口径

总体解释见 [验证报告](../README.md)。本目录只封装已完成结果，不重跑时序或场解。

- `timing-comparison.tsv`：2491 信号各 max/min 两行，共 4982 行；数值单位按列名 ns/ps。裕量正为通过、负为违例；统计逐信号最差经过路径包络，不能视为独立完整路径数量。
- `timing-summary.json`：合格八场景汇总的逐字节副本，含输入来源、SHA、覆盖、误差分布及敏感性。`timing-findings.json` 为保守结论摘要。
- `false-pass-cases.json`：18 根误报通过的具体端点、明确路径、域检查、三种位置稳定性及原报告 SHA。`explicit-counterexamples.tsv` 是原显式反例表；`example-word_1599.rpt` 为其中一份详细原报告副本。
- `final-input-index.json`：141 份轻量下载文件的服务器来源、大小与 SHA；`runtime-receipt.json`：镜像/工具/原库指纹及六份原 SDC 例外审计。完整原件及日志保留服务器。
- `package-receipt.json`：输出文件 SHA、完整原比较表及冻结端点绑定 SHA，不自包含自身 SHA。

setup/hold 误差是宏与详细参考的裕量差，不是实测延迟或全 PVT 误差。百分位按 2491 个 max 或 min 包络计算。主方案沿用旧 R、旧节点权重投影更新上层 C；源端/接收端为敏感性方案，不是严格误差界。详细参考保持原内部 RC，不能用于新内部节点级耦合签核。

全部端点与同版网名见 [寄生阶段结果](../../results/README.md)及其索引。本封装冻结端点绑定 SHA 为 `a1b58e7a9cdd5972833f4ee7c688bd0d1cff8d4e4e29f9b02c9eace89e6248e0`，两阶段均对应 #206 原 2491 信号版图。
