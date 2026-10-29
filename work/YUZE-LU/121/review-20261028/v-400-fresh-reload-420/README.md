# 四份编码副本的新进程只读重载

Refs #121 / PR #122。2026-10-30 04:38 CST。420使用R404/93555/node21现有allocation的16–31、32–47、48–63、64–79四个独立槽，并行只读重载417的clock/ns RECT副本及419的clock/ns普通路径副本。每项原生检查均COMPLETED/0，输入probe ODB前后SHA不变；源probe-result SHA、实际大ODB SHA与已有索引一致。

四份新进程报告均与原始433项报告以及同进程检查逐字节相同。因此在这四个有限样例中，重载没有改变对照结果，不支持“同进程状态令对照无效”的解释。也不能证明其他编码、整个检查器或全部违规的根因。

17原始文件/长度/SHA、启动脚本与四个CPU mask核验见index.json。固定SIF SHA及节点内MemAvailable>4×12GiB×1.2+16GiB guard生效；R原任务仍在0–15，未增加allocation、未取消或修改原任务。无源ODB写入，无修复、规则豁免、时序/功能资格或当前V410资格转移。index.passed仅表示执行/证据核验通过，hypothesis_supported=false、physical_qualified=false。
