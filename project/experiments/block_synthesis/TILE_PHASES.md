# 原生 tile 的描述符阶段协作

2026-11-09，Issue219/PR220。[结果与失败记录](../../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_11.md)。
这是所有基线共用的执行能力，不作为 DP 的独立算法收益；不是一般中间值驻留。

## 为什么需要

此前两个多列 tile 的 U/E 都绑定通道1，整段服务独占通道，使独立的 M/S/局控也不能并行。
现在根据原配方的实际 LOAD、P feeder、M 命令、E 服务和 STORE ACK 顺序生成有限阶段程序。
每个孩子继续独占自己的 M、私有 S、局控和可选 E；只有描述符阶段争用外存通道，按
`FCFS-request-age-then-worker-ID` 仲裁直到输入 S commit 或输出 STORE ACK。
**父服务从共同开始到最后一个 ACK 仍预约全部资源并集**，没有跨父任务任意插入或提前释放。

`tile_phases.program()`保持原生操作和顺序：

1. 16次真实零包 LOAD，初始化实际 feeder padding。
2. 每个网格、完整 K：读 B，再依次读三个 A 分量，执行 cold/reuse-B feeder、Scale、Execute。
3. 单列执行原生 final store 和外存 STORE；多列先保存所有 packed final，再执行
   E LOAD/符号服务/STORE，最后原生 M scatter 和 canonical S32 STORE。

所有 LOAD/STORE、格式转换和最终一次舍入保持；不提供免费 gather、copy、packing 或理想带宽。
P/feeder/E 的测量边界已经含本地适配和确认，不再重复加一份 S 成本。

## 准入、状态和候选

`tile_partitions.variants_for(ir, phased=True)`先保留完整旧池，再加入共享通道协作族。
两个族分别采用原来的每任务64个候选上限，不让新族挤掉旧合法方案。当前最多三个孩子。
孩子的私有资源必须互不重叠，数量不能超过外存 queue/credits/slots 中的最小值。
第一版要求相同 rows/K/row-tile/column-tile 网格配方；不同网格是未实现动作，不是硬件不可能。
保留每种资源/端点/网格的候选，不能提前只留下孤立运行最快的一种网格。

每次 DP/贪心扩展均按当前资源释放、输入就绪和缓存状态执行：重新核对有限 S、失效被覆盖的
只读前缀，重建每个孩子的实际阶段，再模拟通道等待。得到完成时间、流量、静态网并集和新资源尾部。
当前原生 tile 不保留只读前缀，也没有新增一般脏中间值驻留。
阶段程序/时间缓存的 key 包含全部形状、网格、资格化服务、S IO 和外存时序参数；只有在声明的
常量描述符模型下才不计张量名称/地址。它是编译器计算缓存，不是片上数据缓存或 DRAM 行缓冲模型。

## 检查及证据边界

`verify_tile_phases.py`不导入生成器，独立重建实际阶段；`verify_tile_partition.py`核对原生列覆盖、
源步幅、临时外存区、私有资源和有限 credits；`verify_phased_compounds.py`复核工作/读写/阶段顺序、
实际 FCFS 等待以及完整资源并集预约，再产生只供旧检查器验证的投影视图。
投影中的 channel-hold 孩子不是执行程序。检查器与生成器共享整数 FCFS 引擎，不能称两个独立计时引擎；
该引擎另与完整逐事件参考及关闭快进的结果比较。

Windows/Linux各221项通过，含25组随机阶段完整展开、K2048长循环守恒、共享私有资源/等待/
协议/事件/credits篡改拒绝。四个 literal/C++ 有限 S 双回放（含尾块/K2048/极值）通过。
C++只加快宿主数值回放，不是硬件时间。原生 P/E/feeder 和 SRAM RTL 的既有资格保持原范围；
本轮没有增加真实 DMA 仲裁、MC/LC 二进制、整机 RTL、物理、能量或 token/s 资格。

```
python -B -m unittest discover -s project/experiments/block_synthesis -p 'test_*.py' -q
python tile_review.py REGISTERED_IR NEW_OUTPUT --registered-ir --tile-phase-partitions --incumbent STRONG_PLAN --wire-budget 18 --width 8 --write-ir
python tile_partition_probe.py QUALIFIED_NATIVE_HOST_WORKER NEW_PROBE_OUTPUT --phased
```

已经包含该候选族的 IR 不要再次传 `--tile-phase-partitions`。
服务器冻结入口是 `tile-phase-review.sbatch`；具体源、资格输入、SHA及作业终态见结果回执。
