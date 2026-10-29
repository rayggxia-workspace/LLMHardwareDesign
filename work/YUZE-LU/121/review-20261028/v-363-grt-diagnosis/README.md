# V363全局布线阶段诊断

2026-10-29 17:33:03 CST捕获9份原始文件，SHA及字节数逐份通过；input.v为02eacae3…，与同源CTS捕获一致。源423c006/archive61a504d6…，308份源文件服务器/归档/Git核验见../v-363-cts-diagnosis/source-verification.json。

全局布线setup约−0.10 ns：rsp_ready输入→stats_sumsq[1][79]；hold约+0.02 ns：cmd_data[117]→a[3][21]。原始路径和实际输入网表单元映射见path-source-mapping.json。此时尚未完成详细布线、最终RCX及独立验收，不授予最终300 MHz资格。

当前原生流程保持运行；最终失败需由实际终态与同源最终报告证明，不以本中间报告替代最终验收。
