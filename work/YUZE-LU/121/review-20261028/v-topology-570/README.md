# 三条实际网络的只读拓扑核对

Refs #121 / PR #122。完整原生DEF SHA与562实际receipt绑定；只提取原marker0/249/250对应三条普通网原始记录，记录自身SHA；解析helper的实际SHA与571归档中同一Git blob一致，query.py SHA与实际远程脚本一致。

在已分配R404/93555的额外overlap控制step上只读运行，未新增allocation。最初两个1CPU step的早期绑定保护在任何DEF读取之前退出（第二次实际mask为CPU0）；后用现有96CPU allocation的无绑定step，进程自己固定到CPU16，实际初始0–95/最终仅16见index。R主任务仍限0–15；本查询单线程/单CPU，不改EDA/队列/原库。

原marker0对应M1短线连接两个via1_7，两端已有M2线；M3两条样本网在同网M3线上有相邻via2_5。后续单例571保持原M1线与一端via，在M2增短桥替代另一via连接。这里只是三个真实拓扑记录，未宣称自动修复全部剩余标记或物理验收。
