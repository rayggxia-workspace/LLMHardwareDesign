# 显式输出 RC 的原生对照

对应 #127 / PR128，2026-10-27 CST。用户要求继续监视主线，并执行可独立分担的任务；主线尚未提供新的合格 C8 宏包。本支线在本机 WSL 完成下述原生 STA 实验，未新增服务器 allocation、未修改主线候选/工具/作业。

## 对照边界

只使用已知 DFF 小例，比较两种 timing 表示：

1. whole：整段输出 RC 留在导出源内，父层使用单个 timing macro；导出场景输出负载 2 fF。
2. core + 显式 RC：core 输出 wire R/C 和导出负载均置零；将原 q 网的两端各 1 fF、电阻及完整连接逐字保留到父层 SPEF。clock/data 网络保留在 core 内，逐字验证未变。

只改变 timing 表示，不修改任何真实 Block 版图。**core 的输出参考面在 RC 前，不能把该 core Lib 直接替换现有同名 M10 物理端口的 Lib。** 如果应用于真实 Block，必须保持公开 M10 pin 的身份与位置，并通过明确的层次 timing/RC 视图表达内部参考节点、绑定寄生归属。这个有限已知拓扑的分解器不是任意真实网表的自动抽象器，也不证明整套接口/电气/RC 资格。

每种表示分别在 R=1 Ω/20 kΩ、测量输出 load=0/2/10 fF 下运行：共 12 个 model pair，另有 2 个 exact-flat reread。工具始终是原始 pinned OpenSTA，不使用私有修补版。源 V、全/分解 SPEF、导出/测量 SDC、原模型、工具、脚本、原始 TSV/日志和独立复算均保留 SHA。

## 实测结果

| 输出线电阻 | 测量负载 | whole 最大输出 slack 差 | core+RC 最大输出 slack 差 | whole 最大输出 slew 差 | core+RC 最大输出 slew 差 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 Ω | 0 fF | 0.001777 ps | 0.002665 ps | 0.004 ps | 0.004 ps |
| 1 Ω | 2 fF | 0.007106 ps | 0.003553 ps | 0.003 ps | 0.003 ps |
| 1 Ω | 10 fF | 0.009451 ps | 0.002665 ps | 0.510 ps | 0.002 ps |
| 20 kΩ | 0 fF | 0.004441 ps | 0.001805 ps | 11.274 ps | 0.002 ps |
| 20 kΩ | 2 fF | 25.454639 ps | 0.002665 ps | 44.883 ps | 0.002 ps |
| 20 kΩ | 10 fF | 129.995570 ps | 0.005330 ps | 178.927 ps | 0.004 ps |

表中是输出聚合 slack 与端口 slew，原始有符号差也保留。六个 core+RC 场景在原 1 ps 输出诊断范围内；它不是整模 passed。输入 driver 归属未在这组原始工具控制中修复，因此整个 pair 的输入失败继续完整记录，正式资格全部 false。两个 exact reread 通过，全部实际测量上下文名称对应通过；不以零名称告警冒称任意 active-net RC 覆盖。

首个 `explicit-output-rc-001` 尝试被既有输出/输入目录隔离检查拒绝，未完成 pair；原失败目录与报告保留。后续 `002` 仅将 pair 目录放到输入目录外的同级位置，未删除隔离门或放宽数值阈值，完整运行成功。索引记录两次报告 SHA。

## 对主线的用途与剩余工作

结果支持将显式边界 RC 作为一种待审查的模型方案，能避免把已知分布输出网络压成单体表格所带来的部分负载误差。它不能直接外推真实 T6K/C8、多输出分支、条件弧、多 corner 或多网耦合，也没有解决输入工作域。

主线仍需确定实际视图/工具链兼容方式、RC 归属与误差合同，继续提供合格候选并负责物理/功能/资源与冻结；支线按其同源数据独立复验。原 T6K A192/C110 项超差与所有历史负结果保持，不能将这个小例的输出通过改写成真实宏通过。

代码：`project/experiments/block_v1/macro_boundary_qa/explicit_output_rc.py`。运行：`python -B explicit_output_rc.py --executable ORIGINAL_STA --library ORIGINAL_LIB --output NEW_DIR`。已新增丢失/重复电容、错误父层连接和未知拓扑拒绝控制，总控制数 115。

完整收据：`explicit-output-rc-summary.json`；封存/失败/来源索引：`explicit-output-rc-index.json`。两者配合源工具可重建小例并复算结果，不替代完整真实宏接收。恢复先读本报告和 #127 最新回执，再接收主线新包；协作登记/看板限制见 README。
