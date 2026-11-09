# 多 M 原生 tile 列分片与关键路径诊断

2026-11-09；Issue219/PR220。保留完整 K 和最终一次舍入，不增加宏、S、端口或通道。
这是所有搜索策略共用的有限候选族；增加候选本身不计入算法约20%。

`tile_partitions.variants_for()`从已经资格化的tile服务枚举M组合、均衡/网格对齐列宽，
在每种资源/端点组合中保留较快的已有tile。每个孩子执行互不重叠的完整输出列，
共享只读prepared-A/静态B，但各自的真实LOAD全额收费。不同孩子不共享M、S、局控、E或通道。
当前有界枚举不是最优分片证明，也尚未根据当前日历动态求任意列宽。

孩子的`tile_column_view`明确原B/输出的列步幅和列区间。每个128位标量记录仍独立搬运，
没有免费gather、动态打包、外存burst或本地copy。packed/flag临时区从原stage已拥有的区域切成
不重叠窗口；放不下即拒绝，没有额外外存或隐含寄存器。每个孩子照旧失效覆盖到的只读S缓存。
DP和贪心仍逐前沿计算可用时间、当前S影响、静态网并集与后续可完成性。

`verify_tile_partition.py`独立核对列覆盖、真实源步幅、临时区范围/不重叠、原生工作和全部资源/端点。
`verify_tile_binding.py`先证明完整原B是静态共享S16，再核对子视图，不把切片解释为新权重。
最终整数回放由各孩子实际的有限S tile/scatter执行并聚合canonical结果；不以numpy矩阵乘法代替子服务。
当前仍不提供母控/局控二进制、实际DMA、整机RTL、P&R、能耗或token/s资格。

## 两种诊断，不混用边界

`search_diagnostics.py`在整个声明候选族上取乐观时长及资源工作量，给出该族的时间下界。
辅助阶段只占用其真实长度；旧的整服务计法已修正，否则可能高估下界。

`selected_order_profile.py`只解释一个已检查的计划：将资源占用和数据依赖构成事件图，
按实际区间给多容量资源分配槽，再重建最长链。普通列分片展开孩子；协作阶段父服务仍保留整个资源并集预约。
固定偏移服务在边界处分段后允许额外等待，因此是**已选绑定/槽顺序的放松诊断**。
它不是整个候选族的下界，也不是可执行的新计划。关键链服务时间必须严格守恒。

## 当前负结果和下一项需要验证的能力

真实FFN三项Dot增加18个合法候选，最终仍选4,225,968,320 ticks旧强计划，额外0。
原因之一是冻结清单中的U0/U1均为通道1。两个多列tile整段锁住通道1时不能并行；
当前生成器正确拒绝这种伪并行。该清单事实不能推广为所有底座的硬件限制。

下一步是把既有tile服务的实际LOAD/原生命令/STORE ACK顺序编成有限阶段程序，
让拥有独立M/S/局控/E的孩子在描述符完成后交接共享通道，比较同一固定硬件下的单M和多M选择。
需独立重建总工作/流量、有限请求存储与完整事件回放，再接入共同候选池；不能直接放松当前资源互斥。
一般脏中间结果驻留另需生产者写确认、地址、生命周期与消费者实际读取的合同，继续未完成。

运行：

```text
python tile_review.py REGISTERED_IR NEW_OUTPUT --registered-ir --tile-partitions --incumbent STRONG_PLAN --wire-budget 18 --width 8 --write-ir
python search_diagnostics.py REGISTERED_IR STRONG_PLAN bounds.json
python selected_order_profile.py REGISTERED_IR STRONG_PLAN chain.json
python tile_partition_probe.py QUALIFIED_NATIVE_HOST_WORKER NEW_PROBE_OUTPUT
```

详细证据：[迭代10](../../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_10.md)。
