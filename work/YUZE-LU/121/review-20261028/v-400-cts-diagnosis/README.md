# V400 CTS阶段证据

Refs #121 / PR #122。93529/node23，源62e3e5776c891a83f8665d0b86a99fb6aa36f188，归档d3ee6032b6124a089b825cacedeb5ce863beaf038cafa8c12a7ccbcf389a17e3。16原始文件SHA/长度、308归档源Git blobs及远端实际源SHA已核验。CTS修复内置LEC为UNSAT/IDENTICAL，51206公共输入、51195公共输出，diff0/diff1均0。

实际4983条CLOCK网全部NDR none，TSV计数/SHA与native-flow读回一致；CTS_ARGS与POST_CTS_TCL、实际hook/config原样保存。CTS setup−0.07ns/TNS−0.16ns，hold−0.25ns，仍不构成最终300MHz通过。最大cmd_index[2]→stats_sumsq[1][40]，最小reset→stats_valid[1]，对应input.v声明及实际cell见path-source-mapping.json。

已完成CTS、原任务继续route。401/402继续等待真实新前置，全部最终PG/DRC/RCX/功能/严格LEC门保持。
