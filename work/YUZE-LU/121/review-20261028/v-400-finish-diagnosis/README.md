# V400 原生 finish 与最终时序诊断

Refs #121 / PR #122。93529/node23 已自然 COMPLETED/0，全六阶段完成。源 62e3e5776c891a83f8665d0b86a99fb6aa36f188，归档 d3ee6032b6124a089b825cacedeb5ce863beaf038cafa8c12a7ccbcf389a17e3。2026-10-30 02:31:57 CST 捕获21原始文件，长度/SHA、308源Git blobs及远端实际源SHA均核验。原始报告保持字节，路径映射见 path-source-mapping.json。

最终内部LEC为UNSAT/IDENTICAL，51206输入/51195输出，diff0/diff1均0。4983时钟网none的实际TSV与flow读回SHA/计数一致。详细布线最终违例0，5_route_drc.rpt为空；RCX实际完成，提取后VDD/VSS均连通。先前380的PSM短接未再发生；这不替代独立完整GDS DRC与最终门。

6_report.json给出setup WNS **−0.0965326ns**、TNS **−5.59027ns**，hold WNS **−0.0326332ns**、TNS **−1.27177ns**，所以仍不能接收为300MHz宏。最差setup从product[4][0]到output_mem[44][22]，对应N_WRITE完整合并/RNE/饱和。第一最小路径cmd_index[2]到rsp_data[52]。原报告两位小数仅为展示，不能据此放行。die1250²um、标准单元面积676936um²。

401已由407控制实际提交93578/node23，继续原V400独立验收并保留失败证据；402受真实前置限制。不取消EDA、不继承资格、不修改旧ODB。新的精确归一化等值改写与hold修复策略见 docs/decisions/2026-10-30-block-v1-v-normalization-rounding.md；新全输入证明/回归/映射及全新物理验收尚待执行。
