# V316：真实global-place/resizer中间诊断

Issue #121 / PR #122。实际捕获时间以index为准：2026-10-29T00:24:52.740516+00:00（08:24:52 CST）。源db4905bd3534e4f89e82469980fa12efd3092727，RTL841fa5b3…。

五份原始小文件按原字节保存，index记录大小和SHA；输入映射网表保留服务器并记录SHA，端点实例片段直接从该网表提取。两份报告相同最坏max路径为cmd_data[13]→slice599370/D，Q对应group_unit.denominator[79]，arrival4.95ns/required3.20ns，setup约−1.75ns。报告精度为两位小数，JSON globalplace setup worst −1.74686ns仅对应其阶段。

这是ideal-clock、placement-RC估算，完整do-place在捕获时尚未结束；未启动新的EDA，不修改数据库，不授予最终时序或物理资格。320独立详细placement诊断仍按真实do-place依赖启动，原316流程继续。
