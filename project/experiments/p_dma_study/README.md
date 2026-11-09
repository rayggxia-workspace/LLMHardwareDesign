# P/DMA 供数与重复流量专项

[Issue #245](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/245)，接续#244；按用户要求在当前分支/PR243推进。冻结PR241 `e7aeed2097f57a5f910cae70eb51a220c49a8a14`，原模型及检查程序保存在upstream，Git来源和SHA见source.json。没有改动其他任务工作树、生产RTL或已验物理宏。

## 本轮假设和固定预算

使用PR241的候选原生S32/96位M、E32及512位接口模型，非当前已交付RTL。固定2P/1U、每组16KiB S、2通道17.1GB/s聚合峰值、32beat及32描述符信用；W8和W16分开。没有真实新量化/KV张量数值或能耗资格。

- observe：只加逐通道/类别/形状计数，必须与同源原版全部原指标一致，并复现上游W8/W16基线。
- prefix：全A驻留失败时，依据实际双缓冲、96位部分和及工作区剩余空间，按完整K块保留有限A前缀；每行真正LOAD并等ACK，K块命中才省外存读取，局部S→M供数保留。分配按64B对齐，仍≤16KiB；新增前缀控制元数据预算16B/P为控制器假设，查表每块1拍，prefix_slow按3拍。
- pair：N16列组分配给同一P，再按N8完整K执行，保持2P和完整覆盖。未改变每个输出的K顺序或最终舍入。
- combine/pair_combine：每P最多8条64B写缓冲，512B数据**另占私有S**；另列128B/P控制元数据假设，每片1拍簿记。不能借用原1024B工作区。只合并同64B行内已产生的连续有效字节，跨行拆分、冲突/结束真实写回并等ACK；不覆盖邻数据。candidate已有字节写掩码仍为必要条件。
- queue_off、buffer1、credits8：单独检验描述符在途、双缓冲和beat信用。k64/k128及前缀组合在原K≤256候选范围内比较命令摊销与S空间，不扩大硬件范围。
- adaptive：仅对完整A与最小双B/部分和/工作区能放入16KiB的单行静态权重算子采用同步描述符/保留burst内并发；长A、动态B、多行prefill保留排队。算子边界必须没有未退休ACK再切换/恢复。形状规则可编译成每算子1bit，模型未另计模式解码/切换时延，实际控制格式与成本待实现。adaptive_prefix及adaptive_prefix_pair_combine分别叠加有限候选；不按工作负载ID选赢家。

新增控制容量和时延均未取得RTL/物理资格。比较的是同M/数据S/总线预算下的架构候选，不把控制状态当作现有免费能力，不计为PR220的DP算法收益。

## 计数的含义

detail.hpp增加通道、A/权重/动态B/Dot输出/U/KV字节及描述符、bank/row/换向/信用/S计数。矩阵形状单独归因。内存各类排队时间可能互相重叠，不能相加解释墙钟占比；只允许同一P消费者的ready等待、输入ACK等待、服务及输出四段相加，须恰等于该消费者elapsed。

instrument.py要求原模型SHA完全匹配，锚点唯一才生成instrumented.cpp；额外计数没有wait或timing变化。matrix.inc明确实现有限候选。audit.py独立重推矩阵工作/静态权重/动态B/输出字节并核对分类、通道、形状和阶段守恒。oracle.py只证明软件地址/分区/整数前置合同，不冒称SystemC包含真实张量算术或RTL写合并。

## 运行

实际服务器三轮成功：101612（run02，源码247657283d849d7e78450a05ec70a5ff3ed39567）26次、101614（run03，29e50549c45f5b56550081a07fcade659d5ebfbb）18次、101615（run04，727f297cd0ec3436e108e351aad5799c013c0338）18次，均c64/node1/4核/UNLIMITED、COMPLETED0:0。当前15个功能源与run04相同。首轮101611仅编译缩进告警失败，原件保留、-Werror不变。每轮原225 kernels、4 validation、5 smoke和软件oracle通过，原版/观测版/上游基线全部原指标一致；后两轮7项损坏/溢出/源SHA拒绝通过。

W8/context512基线2.714625，adaptive为3.006133（+10.7384%），叠加前缀/列分组/有限写合并为3.063655（+12.8574%）。新流量3.527148288GB/token只少2.1522%，带宽必要上限4.84811仍低于5；W16仅adaptive优于组合。完整分类、负结果和跨context界限见[中文报告](../../../docs/experiments/issue-245-p-dma-study.md)。

源码与输入归档后，通过Slurm在本人全新目录运行job.sh。使用固定容器和SystemC3.0.2、GCC11.4.0、Python3.10.12；4核、c64/c96、UNLIMITED，记录容器/库SHA，不使用其他成员的Python环境。外层run03/run04的job.sh仅在末尾分别追加`--phase followup`/`--phase adaptive`，实际部署脚本及SHA单列保存，未伪称与源码中的默认job.sh字节相同。

```bash
# 在已分配节点、容器中，使用全新结果目录：
python3 -B project/experiments/p_dma_study/run.py --inputs /本人冻结输入目录 --out /本人全新结果目录 --workers 4
# followup：全局排队策略与缓存/写合并组合；adaptive：容量规则及跨context补测
python3 -B project/experiments/p_dma_study/run.py --inputs /本人冻结输入目录 --out /另一个全新结果目录 --workers 4 --phase adaptive
# 本地轻量回执与功能源一致性核对，无需SystemC，不重新仿真
python -B work/Melodydt/245/verify.py
```

输入四个trace、m-profile.log、baseline-results.json、原manifest.json来自冻结PR241；LF身份见source.json。本地转服务器的校验清单必须显式写LF并在提交前sha256sum -c。run.py先编译原版和观测版并比较所有原指标，再做消融，最后对最优已测候选补context128/2048及prefill2；保留负结果。完整日志、大trace/二进制留获授权服务器，Git收轻量结果和SHA。

冻结输入位于获授权服务器`/public/home/yuzelu/Melodydt/issue245-pdma/run04/inputs/`，输入和工具散列见[证据索引](../../../work/Melodydt/245/index.json)。仅仓库不足以重建外部SystemC/容器/冻结输入；须先按远程规则获得权限，使用本人新目录并记录新源码commit/输入SHA，不覆盖已结束run。结果与恢复命令见[交接](../../../docs/handoffs/2026-11-09-issue-245-p-dma-study.md)。无活动作业，未创建自动监测。
