# R870 额外过孔副本实际运行

Refs #121 / PR #122。94496实际RUNNING/node15，源85f3483b、370文件Git/实际远程源码及归档2ff21b26…、queue/run/argv核验见[index](index.json)，11份实际调度原始字节保持。64个869候选分六组，6×16CPU。[实际采样](actual-six-process-sample.json)确认六个OpenROAD进程及互不重叠16核掩码、一秒9590 ticks，合计RSS63502924KiB。每项64GiB forecast、1.2余量加16GiB guard/liveRSS。原828不改写，结果尚待；不授予R资格。
