# V401 原生全芯片 DRC 违规快照

Refs #121 / PR #122。2026-10-30 03:17 CST 捕获 8 份原始文件，逐份 SHA/字节见 index.json。原生全芯片检查已经完成：433 项，包括 Metal Spacing 432、NS Metal 1；层分布 M2 266、M3 167。**V400 不满足最终原生 DRC 门。**

同存 V400 空的 5_route_drc.rpt。它只是详细布线阶段报告，不能替代对最终数据库重新进行的全芯片检查。native-drc.tcl 使用的最终 ODB 路径与 final-source 回执一致；最终来源报告绑定原始 V400，且这两份来源文件与已核验的三初态功能测试绑定文件逐字节一致。

这是原生检查的完成快照；node-queue-state.json 仅表示捕获瞬间的队列状态。完整未修改 GDS deck 与严格 LEC 当时仍运行，未宣称终态，也没有豁免或排除规则。下一步只读比较 route/fill/final 原始数据库以定位来源；不得从本报告推断新 V410 的 DRC 结果。
