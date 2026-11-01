# R880 组合与宽NS真实队列

Refs #121 / PR #122。94498实际RUNNING/node13，源4728365d、374文件Git/实际远程源码与f78d59e6…归档、queue/run/argv核验见[index](index.json)，11份调度原始。初始六任务各16CPU：真实209-via组合和五宽NS；组合完成即补第六NS，采样中mask0已由组合交给NS5，另五项尚在完成输出，证明没有整批等待。初始五OpenROAD加组合Python前置，后续部分进程转DEF/哈希后处理；不将采样中单个OpenROAD称为六个。前875六OpenROAD×16CPU和9645ticks/秒另有真实证据。

八个真实任务还包括依赖组合PASS的完整当前邻域，目前已补入。每项64GiB forecast，1.2余量加16GiB guard/liveRSS。原828与全部旧副本保留。阶段回执保持原字节，结果见[885](../r-880-native-885/README.md)。
