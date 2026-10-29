# V374 全局布线诊断

Refs #121 / PR #122。2026-10-29 20:08:54 CST 原始快照，源 f318db6e/归档 16ee54c4；9 原始文件 SHA/长度验证。input.v 117513404 字节/SHA 47e18487c56312b1bcf8ebc2942d0e929678fb72f04ee6ccb115bf88d069a536，与既有已核验 CTS 及308源绑定完全相同。

GRT setup −0.01 ns、TNS −0.02 ns、hold +0.02 ns，最大路径 product[2][8] → output_mem[82][17]；最小路径 point_total[7][116] → 自身。原始单元映射见 path-source-mapping.json。3.34 ns/299.48 MHz 仅为此阶段报告；300 MHz 尚未通过。

原93372继续 route/finish，不按此阶段提前修改RTL或继承旧最终资格。后继375/376仍需真实最终产物；本目录不证明独立功能/严格LEC、完整DRC或最终RCX通过。CTS完整报告另外补存到 ../v-374-cts-diagnosis/capture-complete/，与原快照严格前缀相等，原快照未覆盖。
