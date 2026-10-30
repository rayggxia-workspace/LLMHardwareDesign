# 六项独立短桥控制的真实结果

Refs #121 / PR #122。615/93833/node13自然终态；616封存49原始小文件、31稳定输出绑定、321源归档Git及远端SHA。六项实际并发、六组不交叠16CPU（0–95），启动相隔0.49秒，实测峰值各约14.24GB；队列内存540676042752B充足，未降并发。

| 独立控制 | 原生计数 | 新增/消除 | 结果 |
| --- | --- | --- | --- |
| alt-both-stack | 172→172 | 1/1 | FAILED |
| alt-corner-lower | 172→171 | 0/1 | PASS |
| alt-corner-upper | 172→173 | 2/1 | FAILED |
| alt-lower-stack | 172→172 | 1/1 | FAILED |
| alt-upper-plain | 172→172 | 1/1 | FAILED |
| alt-upper-stack | 172→172 | 1/1 | FAILED |

四个M4桥都新引入一个异网短路，M3桥转角新引入两个异网短路；只有M1桥转角172→171/0新增。每项结果独立，不能相加；全部原始失败与post-receipt日志追加SHA保持。marker-differences.json只投影实际报告差分，不是测量。

六项均只针对旧598副本；原557412普通NETS/精确目标路径和RECT/其余网token及原输入不变。无当前588、端点连通/RCX/STA/完整GDS/最终功能/LEC/交付资格。618仅四项真实依赖就绪的M5桥后续；worker先绑定实际失败615 receipt和M4短路差分，保留原导线并新增明确via4，不替换失败。
