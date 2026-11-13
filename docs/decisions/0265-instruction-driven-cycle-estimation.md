# 0265 指令驱动的快速周期评估

- 日期：2026-11-13（Asia/Shanghai）
- 状态：proposed
- 负责人：Melodydt
- 关联：[Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) · [PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) · [#234 整机验收](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234)

## 分工

用冻结的母控/局控二进制和部署拓扑构造事件驱动的周期估算器。接收并行分支的短程 RTL 仿真作为校准和留出验证基准，复用 #265 已冻结的 checkpoint、参考输入和平台版本记录。全程 decode 吞吐仿真由并行分支负责。#265 输出估算周期、估算吞吐、校验误差和适用范围。

## 已有证据

对 #251 的两份独立归档重算 SHA-256，直接从二进制展开 MC v3 的循环和调用，从 LC v2 镜像核对 `EXEC → WAIT → END`，校验 192 个 128 B 描述符的 CRC32、SHA-256、地址和目标 P。两个作业的镜像和描述符逐字节一致。每个作业包含两种运行模式及每种模式下三种 SRAM 初态。解码本身只读取镜像，归档 manifest 和 RTL 日志用于事后对账。

| 历史作业 | 模式 0 FFN 与 DOWN 周期之和 | 模式 1 FFN 与 DOWN 周期之和 |
| --- | ---: | ---: |
| 102603 | 849,914 | 941,907 |
| 102604 | 860,202 | 948,626 |

同模式的三种初态在各自作业内得到相同周期。两个作业每个用例均为 192 次调用、1,123,200 次后端请求与回包、71,884,800 B 确认读取、96,256 B 片上写确认。102603 启用提前发起 `EXEC`，102604 是原发起时序。同一压力模式下的阶段周期分别相差 10,288 和 6,719。这些阶段数据来自三 P FFN 和合成 DDR provider。详见[上游归档索引](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/250/native-services/ffnnative/index.json)与[本次回执](../../work/Melodydt/265/fast-cycle-input-audit.json)。

## 模型需要的输入

| 输入 | 必须绑定的内容 |
| --- | --- |
| 控制镜像与运行状态 | 母控/局控 ISA 版本、实际端点和镜像、`CALL/WAIT` 的 token 与释放条件、局控任务表、描述符、实际控制分支和循环边界。数据相关控制需要已验证的分支或地址轨迹。 |
| Block 内及 Block 间拓扑 | 路由、链路宽度、FIFO 深度、共享资源和仲裁、Block 内端口和 SRAM bank 映射、实际时钟和 CDC 边界。每条依赖绑定对应的完成事件与可见性。 |
| 算子和本地传输服务 | 依操作码、形状和数据布局选择启动延迟、发起间隔、并发数以及各阶段资源占用。区分计算完成、输出可读、缓冲区可复用。用短仿真观测这些边界。 |
| DMA、片外 DDR 与初态 | 物理地址、突发拆分/合并规则、通道和 bank 映射、队列深度、读写调度、行状态、刷新与读写切换。绑定事务 ID、返回和写可见性、排空条件，以及测量窗起点的 KV、SRAM、队列和 DDR 状态。 |

未知的指令、服务、路由或必需初态应输出缺项及其位置。预测必须使用预先冻结的配置。RTL 实测等待、事件时标和完成周期只用于校准或留出对账，分别登记来源。

## 实施与验证顺序

1. **建立片上时间轴。** 在已审核的 MC/LC 解码上绑定单个短程实际拓扑和服务参数，以 `CALL` 接受、局控派发、输出可读、DMA 返回、跨 Block ACK、`WAIT` 释放、credit 归还等事件推进仿真时钟。同周期事件按硬件协议规定的顺序处理。复用 [#235 母控 SystemC](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/eaf3008868982e5ac6c2f70878250c148ec6d009/project/experiments/systemc_benchmark/systemc_mother.cpp) 的端口语义及 [#257](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a326d04e170cb84d273e96e7906bdf23775a0ca8/project/experiments/block_synthesis/EVENT_FRONTIER.md) 的有限资源、credit 和 ACK 定义。输入为既定程序时，按指令语义发射，保留原有依赖和仲裁规则。第一组用现有三 P FFN 的短前缀或同类有时间戳的小用例，逐项核对完成事件。
2. **把 DMA 和 DDR 放到同一时间轴。** 先用可控延迟、有限队列的 provider 验证同址事务、背压、可见性和排空；再以实际地址驱动 DRAMsim3 等详细后端短窗。每次接受或拒收和每次完成都应反馈给片上事件调度。计算与访存重叠，DDR 延迟通过依赖或资源冲突进入关键路径。现有 [#235 DDR 桥](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/eaf3008868982e5ac6c2f70878250c148ec6d009/project/experiments/systemc_benchmark/systemc_dram.cpp) 使用离线请求列表和按地址匹配的回调，接入前验证逐笔事务身份、同址顺序及写入语义。对 FFN 归档只有聚合计数的段，后续接收地址生成器或可审计的逐笔轨迹。
3. **分开校准和留出。** 在查看留出结果前冻结服务参数、DDR 规则、周期误差上限和最低加速比。留出用例改变背压、地址模式或拓扑。先核对调用次序、数据量、请求/返回、跨 Block ACK 和 DMA 排空，再报各阶段与整体的周期绝对误差、相对误差和最坏误差。样本足够后报告中位数及 p95。按相同输入和起止事件计时，在同一主机上分别记录模型与 RTL 的计算时间及轨迹输出开销。缺少对应日志时，标出受影响区间。旧回放将实测等待作为输入，可作接口回归参考。
4. **扩到整机 decode。** 收齐实际 Qwen2.5-3B 的完整层、Attention/KV、控制、词表头、时钟及 DDR 绑定后，先核对单层短窗、跨层短窗及少量完整 token，再扩展到与并行分支一致的场景。请求过多时仅在依赖、地址模式和边界状态经逐笔模型验证的区间聚合，并单独报告聚合误差。任何未覆盖的 Block 或额外排空区间都要单独列出。

在单一参考时钟下，用 `估算 tokens/s = 参考时钟 Hz × 窗口内完成 token 数 / 窗口周期数`。多时钟时将各时钟域事件统一到真实时间，再按同一退休边界取差。沿用 P512/D128 的历史主口径时，从首个生成 token 退休后到第 128 个退休包含 127 个缓存 decode 间隔，使用 `127 / (t128 − t1)`。明确首 token、KV 可见性及额外排空的边界；报告各阶段周期、端口/队列等待和 DDR 拥塞时段。留出仿真证据与估算分别展示。

## 其他可用方案

- 用依赖关键路径、每类资源工作量/并发能力及通道字节量/带宽计算下界，可作为模型的快速自检。其精度取决于真正依赖与资源边界。
- #241 的工作量模型用于口径和数量级交叉检查；#251/#257 的时间回放用于验证已有轨迹与已知边界。两类结果的参数来源各自保留。

## 当前交付与恢复

实际运行了[控制输入审计](../../work/Melodydt/265/README.md#快速周期评估)和现有项目管理检查。本阶段没有估算器周期、同机加速比或整机估算 tokens/s。下一个门槛由 Melodydt 负责，选择一组具备发射、接受、完成和 ACK 时标的短 RTL 记录，冻结该用例的服务参数和端点映射，交付首个可独立出周期并与留出用例对账的片上事件模型。已知后续依赖为部署拓扑和地址/队列配置。
