# 新V537完成放置阶段

Refs #121 / PR #122。15原始文件与311源Git/远端SHA核验，源cf1fc48e/archive22dd145a；只读已完成do-place检查点，未修改DB或启动EDA。详细放置合法性0项，放置估算setup WS−1.07198ns/TNS−58.1768ns/121项、hold WS−0.00726111ns/1项，cap/slew0。以上为CTS前的放置估算，不是最终寄生资格，也不直接证明流水修复成功或失败。

实际报告首个max路径cmd_index[2]→stats_sumsq[0][79]、min到group_unit.count[0]，input.v实际网表SHA和对应单元声明见index.json。当前CTS仍正常执行，必须继续完整route/final及538独立门、539接口。既有522拒收与543/544功能/LEC记录不转移到新源。
