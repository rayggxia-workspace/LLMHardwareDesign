# R875 实际堆叠via副本队列

Refs #121 / PR #122。94497实际RUNNING/node13阶段，源836fed0c、371文件Git/实际远程源码与归档bd15f0bf…、queue/run/argv核验见[index](index.json)，11份调度原始。[采样](actual-six-process-sample.json)六OpenROAD各独占16核、一秒9645ticks/RSS70369612KiB。每项64GiB forecast、1.2余量/16GiB guard及liveRSS。后续自然COMPLETED/0:0，终态证据见[881](../r-875-vias-881/README.md)。此处仅保存真实启动阶段，不把阶段快照改成终态。
