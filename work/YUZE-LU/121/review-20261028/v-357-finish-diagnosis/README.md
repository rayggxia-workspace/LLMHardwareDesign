# 旧V357最终提取诊断

2026-10-29 17:47:00 CST捕获9份服务器原始文件，SHA与字节数核验；308份源文件服务器/归档/Git核验见source-verification.json。原始日志保持完整字节。

原生六阶段均完成，但这不是最终300 MHz接收。最终重新提取报告6_finish.rpt显示setup约−0.15 ns：offset[2]→stat_block_max[16]；hold仅舍入0.00 ns，不作为独立正裕量资格。实际单元映射见path-source-mapping.json。

这仍是旧修订f231的offset相关归约路径，不将其资格转移到当前V363。当前V的operand_a/operand_reduce_mask预取修订已由361/362验证，363自身的CTS与GRT报告分别保留于相邻诊断目录，仍待其最终详细布线、RCX与独立验收。旧357正常收尾，未取消或重启。
