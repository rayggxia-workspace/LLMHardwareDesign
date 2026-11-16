# 实际阶段窗口、外存物化与同预算前沿搜索

2026-11-09；Issue219/PR220迭代9。默认仍使用既有配方；`--materialized-windows`
显式加入实验候选，不修改宏、S容量、频率或虚拟外存参数。不把本轮功能扩展计算成DP的20%。

## 为什么需要完整区间

假设一个Dot在0开始，只在100–110使用E。另一个服务若使用E的0–20，二者可以并存。
只存“E到110才空闲”会错过该解；把E状态清零又会忘掉100–110的冲突。
现在前沿保存E及选定共享通道的已占用区间，另保留M私有资源的串行日历、S缓存、依赖完成时间及静态网并集。
相邻已占用区间可合并；有不同空档的状态不可只按最晚结束时间合并。

对绑定b、当前状态s：先按缓存内容重新计算实际工作量和duration，再求最早开始a。
非窗口资源满足`a >= available[r]`及输入到齐；窗口资源的实际占用为`[a+lo[b,r],a+hi[b,r])`，
不得与s的已有区间重叠。冲突时将a推进到冲突区间末尾减lo，再检查全部资源。
这里是整数端点跳转，没有逐拍展开K循环。普通服务的lo=0、hi=实际duration。

优化目标仍是完成时间、逻辑搬运、静态连接成本的字典序；没有另换数值格式或隐藏加速系数。
网集合代表同一产品的静态金属，不能因时间错开就解除物理互斥。

## 新候选真正执行什么

旧多列tile按grid循环：完整K计算、保存packed、E求符号、M把packed恢复成canonical S32。
新候选可选地把整Dot改成三段：

1. P逐grid计算完整K；所有packed结果通过实际STORE ACK保存到该Dot独占的外存临时区。
   一列尾块仍直接写canonical结果，任务完成事件不提前。
2. E依次LOAD这些完整128位字、执行原生ASR15、STORE符号字并等ACK。
3. P实际重新LOAD十六个零包，然后按原三次M基向量服务恢复每个S32输出，STORE并等ACK。

M的上下文、P.S/端口和P局控在整个Dot期间保留。E及其S端口、局控只在第二段保留。
若E与P共用外存通道，该通道仍被P整段保留；只有不同通道才能释放E侧的前后空档。
E组不得同时拥有受只读缓存管理的M。所有M私有IO继续按决策顺序串行，保持缓存生命周期的物理顺序。

代价不是“删去闲置E时间”：新总ticks=旧ticks+16×真实LOAD成本，外存读取多16条128位记录。
packed/flag的读写次数不变，但临时区从每grid复用扩大为整Dot的`2×packed_outputs`个记录。
每个Dot有独立地址区间并计入外存容量。该变换不消除一般跨算子写回，也不提供新打包器、DMA或多个M上下文。

## 搜索和独立检查

- `window_calendar.py`纯转移不修改输入状态。DP和贪心共用缓存重算、最早插入和实际窗口。
- `verify_materialized_tile.py`从原生服务、形状及保留的旧候选独立重建三段时间、额外读写、临时区和资源。
- `verify_window_schedule.py`重建顶层实际区间并查冲突；原排程检查继续查依赖、有限S、缓存、搬运和全部静态网。
  E.S仅在E段占用，P.S整段占用。已有compound的内部事件及保守整段共享通道合同继续核验。
- 排序的资源尾部也读取当前区间。价格下界按辅助资源的短工作量计费，已安排窗口只累计真实区间长度。
  未解析compound仍用乐观放松，不能把它写成最优保证。
- `--incumbent-order`将已检查好计划的拓扑决策顺序提供给每个基线和DP，重新搜索绑定与成本。
- `--incumbent-backbone`在同一beam宽度内保留一个重新执行得到的好计划前缀，其他位置继续探索。
  不复制原时间戳、不省略状态转移，也不扩大beam。非法输入计划先被拒绝。

强基线和新搜索共用扩展后的候选。以前最强的合法计划仍进入最终选择及收益分母，避免新候选使窄beam退化后换弱分母。
有限beam/ready截断、固定顺序及前缀保留均是启发式，无全局最优保证。

## 证据范围

Windows与独立Linux各204项通过。区间最早插入与300个随机整数例的独立穷举比较；
未来空档、源状态不变、多槽非窗口资源、compound时间平移、错误窗口/缓存顺序及原生成本篡改均有检查。
C++有限S执行器通过68例，其中60例实际采用三阶段顺序，与原逐命令解释器/独立矩阵数值及计数对照。
宿主C++速度不是硬件加速。

冻结的原M/E/P/S RTL在三组明确指定的SRAM初态各347例通过；本地packed副本被破坏后仍从完整外存字恢复，
E和M仍执行全部符号/散布运算，实际写ACK、完成背压和16次零重填保留。篡改黄金结果被拒绝。
这证明命令顺序与数据通路，不证明完整MC/LC程序、真实DMA调度、DRAM带宽、系统时间或能耗。

真实FFN、完整36层及各轮正负结果见[迭代9记录](../../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_9.md)。
一般脏中间结果驻留、KV decode、校准整机SystemC、token/s和最优适配ASIC/FPGA比较仍待完成。

运行示例（输入是已注册tile且NExp已修正的IR）：

```text
python tile_review.py IR OUT --registered-ir --materialized-windows --incumbent BEST_PLAN --incumbent-order --wire-budget 18 --write-ir
python tile_review.py IR OUT_BACKBONE --registered-ir --materialized-windows --incumbent BEST_PLAN --incumbent-backbone --wire-budget 18 --policies old-dp resource-dp
python native_tile_probe.py WORKER NUMERIC_OUT --materialized
```
