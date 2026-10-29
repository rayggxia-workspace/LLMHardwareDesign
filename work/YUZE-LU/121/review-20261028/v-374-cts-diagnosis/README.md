# V374 CTS 诊断证据

Refs #121 / PR #122。2026-10-29 19:50:23 CST 捕获，源 f318db6eb6dc263e551004a1c32ed321525e9256，归档 16ee54c470c8929b6d89fb484b64db12f4f83b38765d86a0cfb0c63c502050a1。11 份原始文件逐字节 SHA/长度核验，308 份归档源与 Git blob、远端实际源 SHA 一致；input.v 的 SHA/长度及原报告路径映射见 index.json 与 path-source-mapping.json。

CTS setup −0.01 ns、TNS −0.02 ns；hold −0.04 ns，均尚未通过。最大路径 norm_square[1] → group_unit.denominator[127]；最小路径 cmd_data[22] → input_mem[220][22]。报告最小周期 3.34 ns / 299.15 MHz 仅属于此 CTS 阶段。

CTS 修复内置 LEC 实际 UNSAT/IDENTICAL：公共输入 51206、公共输出 51195，输入/输出 diff0、diff1 均 0。这不代替独立最终网表严格 LEC。捕获时尚未记录 CTS 完成回执；后续只读观察已完成 CTS 并进入详细布线。原始快照保持不变。

继续原 93372 的 route/finish，不根据 CTS 提前修改 RTL，不复用旧版本最终资格。最终 RCX 时序、独立验收、六文件与全端口接口门均待实际后继 375/376。
