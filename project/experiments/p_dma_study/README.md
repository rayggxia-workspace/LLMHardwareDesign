# P/DMA 供数与重复流量专项

[Issue #245](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/245)，接续#244；按用户要求在当前分支/PR243推进。冻结PR241 `e7aeed2097f57a5f910cae70eb51a220c49a8a14`，原模型及检查程序保存在upstream，Git来源和SHA见source.json。没有改动其他任务工作树、生产RTL或已验物理宏。

## 本轮假设和固定预算

使用PR241的候选原生S32/96位M、E32及512位接口模型，非当前已交付RTL。固定2P/1U、每组16KiB S、2通道17.1GB/s聚合峰值、32beat及32描述符信用；W8和W16分开。没有真实新量化/KV张量数值或能耗资格。

- observe：只加逐通道/类别/形状计数，必须与同源原版全部原指标一致，并复现上游W8/W16基线。
- prefix：全A驻留失败时，依据实际双缓冲、96位部分和及工作区剩余空间，按完整K块保留有限A前缀；每行真正LOAD并等ACK，K块命中才省外存读取，局部S→M供数保留。分配按64B对齐，仍≤16KiB；新增前缀控制元数据预算16B/P为控制器假设，查表每块1拍，prefix_slow按3拍。
- pair：N16列组分配给同一P，再按N8完整K执行，保持2P和完整覆盖。未改变每个输出的K顺序或最终舍入。
- combine/pair_combine：每P最多8条64B写缓冲，512B数据**另占私有S**；另列128B/P控制元数据假设，每片1拍簿记。不能借用原1024B工作区。只合并同64B行内已产生的连续有效字节，跨行拆分、冲突/结束真实写回并等ACK；不覆盖邻数据。candidate已有字节写掩码仍为必要条件。
- queue_off、buffer1、credits8：单独检验描述符在途、双缓冲和beat信用。k64/k128及前缀组合在原K≤256候选范围内比较命令摊销与S空间，不扩大硬件范围。

新增控制容量和时延均未取得RTL/物理资格。比较的是同M/数据S/总线预算下的架构候选，不把控制状态当作现有免费能力，不计为PR220的DP算法收益。

## 计数的含义

detail.hpp增加通道、A/权重/动态B/Dot输出/U/KV字节及描述符、bank/row/换向/信用/S计数。矩阵形状单独归因。内存各类排队时间可能互相重叠，不能相加解释墙钟占比；只允许同一P消费者的ready等待、输入ACK等待、服务及输出四段相加，须恰等于该消费者elapsed。

instrument.py要求原模型SHA完全匹配，锚点唯一才生成instrumented.cpp；额外计数没有wait或timing变化。matrix.inc明确实现有限候选。audit.py独立重推矩阵工作/静态权重/动态B/输出字节并核对分类、通道、形状和阶段守恒。oracle.py只证明软件地址/分区/整数前置合同，不冒称SystemC包含真实张量算术或RTL写合并。

## 运行

实际服务器实验待执行；本地仅完成源身份、确定性生成和Python语法检查。源码与输入归档后，通过Slurm在本人全新目录运行job.sh。它使用固定容器和SystemC3.0.2，4核、c64/c96、UNLIMITED，记录容器/库SHA，不使用其他成员的Python环境。

```bash
# 在已分配节点、容器中，使用全新结果目录：
python3 -B project/experiments/p_dma_study/run.py --inputs /本人冻结输入目录 --out /本人全新结果目录 --workers 4
```

输入四个trace、m-profile.log、baseline-results.json、原manifest.json来自冻结PR241；LF身份见source.json。本地转服务器的校验清单必须显式写LF并在提交前sha256sum -c。run.py先编译原版和观测版并比较所有原指标，再做消融，最后对最优已测候选补context128/2048及prefill2；保留负结果。完整日志、大trace/二进制留获授权服务器，Git收轻量结果和SHA。
