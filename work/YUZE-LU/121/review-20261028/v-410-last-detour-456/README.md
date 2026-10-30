# 456 隔离旧V副本原生DRC清零

Refs #121 / PR #122。453merge最后一个net104114的M2三段折返换为同端点直连，全部via/anchor/M1/cell/port不变，M2线长减少100DBU=0.05µm。实际whole-chip native1→0、删除1/新增0；完整DEF/相同网表/端点/全栈连通通过，原453probe.odb SHA保持。

此副本来自旧410→445→453，旧410时序仍失败；没有此副本的RCX/STA、全部194定义的完整GDS XOR/deck/最终功能/LEC资格。451单点的28层完整GDS XOR0另见452，不能转移成456或新V的最终资格。当前V/R源未被此诊断修改。
