# 冻结执行计划的吞吐瓶颈诊断

2026-11-09；Refs #240、#219、#220。本文先同步已确认诊断，新的 SystemC 改造仍在执行。

## 证据对象与边界

原件目录：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/side-token-probe-20261109-01`。
Slurm 101533，SystemC 3.0.2，COMPLETED 0:0。工作负载为 Qwen2.5-3B 全36层，B1/S2 prefill、无KV，包含embedding和LM head。

冻结输入来自 attempt277：

- IR SHA256：`e8a30117ab627b23d642e0e8bd3051c1721c22e758cbfb8eefcbb0c7637324b5`。
- conditional-dp.json SHA256：`b0311e8835f87b22bc89d1b234517f50d594529b7fa898722c82591473c5deb0`。
- 8,404项服务；SystemC与独立依赖/资源顺序事件图均为167,410,840,866模型ticks。
- 假定每tick为300MHz的一拍：两个输入token需558.03613622秒，条件prefill吞吐0.00358399729 token/s。
- 8,249,973,644条逻辑128位记录，名义131,999,578,304B。不是DRAM实测字节；除以总时间也不等于内存通道带宽。

这是服务级回放：时长继承编译器，不是独立命令/MC/LC/DMA/DRAM时序校准、decode吞吐、系统RTL、功耗或物理验收。
诊断针对以上冻结计划；不声称PR220后续head仍保留所有相同配方。

## 关键路径

同一冻结IR/候选池的贪心诊断为167,410,873,122 ticks，与以上DP回放相差32,256 ticks，即300MHz下0.00010752秒。

| 算子服务 | ticks | 条件秒数 | 关键链占比 |
| --- | ---: | ---: | ---: |
| Dot | 84,500,059,460 | 281.667 | 50.475% |
| Product | 34,877,867,696 | 116.260 | 20.834% |
| Add | 33,740,886,712 | 112.470 | 20.155% |
| 其他 | 14,292,059,254 | 47.640 | 8.537% |

每项均含该服务的搬运、转换等成本，不能解释成纯MAC时间。尚未把本次完整关键链逐事件分成纯计算与DRAM等待。

## 已确认的问题

1. **数值合同与执行配方。** 冻结执行器用S32标量合同，许多Product/Add经S16分量、M部分运算及读回实现。源码streaming_ir.py明确说明原语间spill。这解释了Product/Add约41%的关键链服务成本。应优先核对已新增的原生S32配方，仍缺少的服务才提议硬件扩展。
2. **M利用率。** 此冻结tile配方采用K段1；M本身有64个S8乘法器、支持更长K段。N8/K1只使用8个有效乘法位置，S16还需多轮S8分解。K8/32需要真实布局、供数、尾块、累加和ACK验证，不能只缩短ticks。
3. **流量与事务粒度。** 冻结标量ABI常用16B记录承载一个S16或低S32。只读Dot缓存/受限tile已存在，但一般脏中间值驻留尚未落实。PR182派生模型对每描述符冷计时且多为单字；S访问3拍时64次单字LOAD合计1280拍，一次64字LOAD为287拍。这只是相同抽象模型内的描述符例子，不是整机4.46倍加速证据。
4. **时间资格。** 宏/局控/端口、外存银行和队列需独立校准。服务级SystemC吻合不证明这些时长已获得硬件资格。

## 开源参照的真实边界

[openTPU](https://github.com/FeSens/openTPU#results)作者报告板上SmolLM3-3B INT8 decode 5.00 token/s、Phi-4-mini 3.8B INT8 3.99 token/s、Qwen3.5-4B 4-bit且INT8 head 5.88 token/s；其decode与本次S2 prefill不同，精度也不同，不能直接求实测加速比。
其[ISA](https://github.com/FeSens/openTPU/blob/main/docs/isa.md)提供ACT驻留、整块权重流、TMEM向量运算和连续LD/ST。

[LLAccel](https://github.com/taisirhassan/llaccel#how-it-works)提供INT8矩阵、16路向量引擎、1MiB银行SRAM、DMA及重叠调度。
已查到的[性能报告](https://github.com/taisirhassan/llaccel/blob/main/docs/RESULTS.md)主要是小模型RTL周期/流量；不作为3–4B板上数token/s证据。

## 本任务的改造边界

- 固定方法：独立功能宏＋局控/必要适配器；Block是控制归属；M1–M10有源底座与M11/M12后制数据连接。不恢复五个组合硬框，也不把不同控制组的S合成免费共享缓存。
- 宏/Block内可研究：紧凑数据布局、打包/拆包适配、K8/32供数、原生S32向量服务、局部流水及有限缓冲。
- 用户允许外部接口与外存预算参考openTPU/LLAccel；现有预算和参考预算分配置报告，新增端口/位宽/信用/缓冲逐项列出，不能偷偷提高带宽。
- 新能力按架构候选标记；有源逻辑变化需要新RTL和物理验收，不能靠M11/M12金属补出算术或缓冲。
- 实际整数图prefill与配置派生KV decode预测分栏；新增预测不继承原整数图数值资格，不把架构/共同后端收益算作DP算法约20%。

## 后续验收

命令/事务级SystemC将显式模拟有限S、队列/信用、端口争用、数据就绪与ACK；输入/源/配置/输出冻结SHA。
先测现有M更长K段的命令时间，再做数值小例、资源守恒、消融、时间与吞吐预测。RTL、物理、能耗及完整KV数值尚未完成。

协作规则rayggxia-project-collab v1.0.0；Issue240 in_progress；PR为draft，不关闭Issue、不自合并。
沿用项目登记management-hub PR5 pending；Projects缺配置/权限的既有记录需在本任务再次核验，当前不宣称已同步。
