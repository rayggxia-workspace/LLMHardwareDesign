# R857 实际六槽动态调度证据

Refs #121 / PR #122。94491于2026-11-01在node13实际运行；源ae2502ef、368文件Git/实际远程源码及归档SHA、queue/run/argv核验见[index](index.json)。11份实际调度原始字节保持。

七项真实任务：一项只读拓扑及六组独立副本原生全片DRC，319候选按net分片。拓扑完成后第六组立即补位。[实际采样](actual-six-process-sample.json)记录六个OpenROAD进程、六组互不重叠16CPU affinity和1秒内3738 CPU ticks、合计RSS67170656KiB。不是把单个任务扩到96核，也不是整批等待。

每组64GiB、拓扑16GiB预估，1.2安全系数加16GiB guard，物理503.5GiB节点内六角部任务476.8GiB；同时检查live RSS。副本结果尚待；未改原828数据库，未授予最终资格。拓扑完成证据见[862](../r-857-topology-862/README.md)。原生584失败仍有效。
