# 有界完整 GQA A 切片

Issue102，真实 Q8/KV16 → QK32 → 三遍整数 softmax → P15×V16 → PV32；完整8个共享Q头、d128、B1、有效前缀1..1056。数值严格延续64，非online算法。

- `attention102.sv`：有限单命令控制器、8个S8乘法、八个I32 PV累加器，暴露单口S、S32、128bit除法SFU和外部读服务。
- `chain102.sv`：单16KiB128bit1RW store82、共享mul84和sfu84、有限memory_link；命令锁存、地址/缓存版本检查、epoch取消/排空、配置与完成握手。行为存储仍无宏资格。
- 正式源自a6961b7；后续driver、receiver和文档变更不冒充硬件重执行。详细[冻结合同](../../experiments/attention_rtl/PROTOCOL.md)、[接收与复现](../../experiments/attention_rtl/README.md)、[实验报告](../../../docs/experiments/issue-102-attention-rtl.md)。

S所有空间都在同16384B内：Q1024B，metadata保留256B，score4224B，P2112B，K/V共用tile4096B，输出4096B，scratch保留512B，canary64B。寄存lineholder、宽移位、round、比较、控制/计数/缓存元数据另计入实际逻辑图。外部表/有限回应FIFO不在核心映射面积内。

首版cache固定一个owner至协调hardreset；version正数单调、不回卷、旧版失效；同version K/V scale和base固定且length不退。length由调用者保证已经commit，RTL无KV写/append接口。softabort取消发布且保留registry，过期响应丢弃；epoch最大值永久停接新命令，须协调fabric/core硬复位。

下一次与M/R整合须真正共享S、8S8、S32、SFU和link并核owner lease/排空/地址覆盖；不能同时保留各切片的独立资源再称同库存。当前8S8在attention控制器内，抽成共享service还需真实mux/仲裁/计费。没有投影/RoPE/output projection、KV追加/淘汰、整模型质量或物理时序资格。
