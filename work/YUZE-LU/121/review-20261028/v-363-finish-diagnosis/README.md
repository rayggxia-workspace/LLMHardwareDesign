# V363 最终 RCX 诊断

Refs #121 / PR #122。2026-10-29 18:52:43 CST 原始快照，9 文件 SHA/字节核验，input.v 与已核验 CTS 源绑定一致。

最终报告 setup −0.13 ns、TNS −12.04 ns；cmd_valid→stats_sumsq[1][79]。hold 仅舍入 0.00 ns，不能作独立正余量。此时六阶段流程仍收尾，不声称完整最终验收；300 MHz 不合格。原始路径和 input.v 单元映射见 path-source-mapping.json。

流程内最终 LEC 已通过；完整独立门仍须据实运行。保留当前生产任务正常收尾。
