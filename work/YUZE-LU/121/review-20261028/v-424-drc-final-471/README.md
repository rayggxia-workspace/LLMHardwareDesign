# 旧V424最终DRC自然终态

Refs #121 / PR122。旧423的独立最终验收424/93603自然结束，父任务FAILED/1:0。原生全芯片DRC464项；完整未删改FreePDK45 GDS deck实际129规则类别/0项，不能用后者覆盖前者的失败。精确类别/层计数、原始报告/日志、实际GDS大小与SHA、同一最终源回执绑定见index.json。与先前401实际deck SHA逐项一致。

此前同源最终网表三初态功能与严格LEC通过；setup和maxcap物理门已失败，因此旧423仍不可接收。该结果不转移到新463，未据此修改或重启新463/R404。worker在封存receipt后向child log追加失败traceback，原始回执空日志SHA及追加后的SHA分别保留，其余稳定输出逐SHA核验。
