# R866 实际副本修复队列

Refs #121 / PR #122。94494在node13实际RUNNING，源dd2b1f5b、369文件Git/实际远程源码及归档447a7645…、queue/run/argv一致。9份调度原始见[index](index.json)。[实际采样](actual-six-process-sample.json)确认六个OpenROAD进程分别固定不重叠16CPU，一秒9375 CPU ticks，合计RSS67505672KiB。

10个真实任务：314角部组合（绑定864六组真实失败，排除四改动网）、53个via对的六分片、三个NS接缝网格补片副本。每项64GiB预估、1.2余量加16GiB guard及liveRSS，c96六槽动态补位。NS依据实际net131530/583号原始标记，不向2DBU非网格标记直接布矩形。未改原828数据库，不给修复或最终资格；全部检查结果仍待。
