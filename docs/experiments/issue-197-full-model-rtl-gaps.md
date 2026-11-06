# 整模型 RTL 仿真缺项

Issue #197 / PR #198。以七模型文本推理为目标，范围为 SystemC 对照和数字 RTL。已有模块分别验证过算术、控制、存储与局部交接。整网验收要求同一个 RTL 顶层接收检查点与程序，执行所有层和 token，并产生可与 SystemC 对比的结果。

| 缺项 | 可复用的现有证据 | 整模型仿真需要的模块或接口 |
| --- | --- | --- |
| **统一顶层与地址表** | #168 的 `control_system` 有 M/N/E/G/R/S/T、C/D、AXI-Lite 配置和 128 位 AXI 数据。#195 验证了 P16/U16/C16/F16/J16 的实际服务适配器。 | 固定一个整网 RTL 顶层及其资源清单。若以 #184 的九实例为目标，实例化 P×3、U×2、C×1、F×1、J×2，绑定端点 ID、私有 S、程序存储器、时钟域及复位，冻结 host 装载、启动、完成和错误接口。#168 的拓扑可继续作七宏参考。 |
| **模型图到可执行控制镜像** | #180 有母控/局控 ISA、装载读回、完成、恢复和若干真实双局控交接。#196 有真实 Qwen FFN 切片的编译器和同源映射，但使用独立试验镜像。 | 给七种模型的完整图生成母控/局控程序，统一镜像、操作码、张量格式和地址绑定。覆盖层/头/块循环、残块、依赖、prefill/decode、动态 token 和分支。每个调度任务应能追溯到 SystemC 算子和具体 RTL 命令。 |
| **块间数据面与完成面** | #195 的 `stored_link` 通过静态一字链路验证 C0↔U0，目的 SRAM 写确认后释放源。#180 验证多种丢确认、复位和代次隔离。#206 端点审计定位了 C0/U0 多源单 RX 和 P/J 请求响应接口。 | 实现父层地址/路由选择、多源仲裁、独立 RX 预约和有限队列。统一 128 位数据、地址、`valid/ready`、目的写确认、错误和 tag/epoch 路径。多字传输需处理顺序、背压、部分完成、协调复位和迟到应答。 |
| **外存、权重与 KV 访问** | #168 有现有 AXI 端口。#182 的 `hbm_group_dma` 有 40 位外存字节地址、每 S 描述符、128 位数据、带 ID 的请求/应答及双时钟 FIFO。 | 选定整网搬运接口。使用 #182 时需要把母控描述符及完成语义接到分组 DMA，把数据接到每个私有 S；使用 AXI 时需要实际的多块地址和访问调度。补齐权重预取和分片、KV 追加/读回/分页、尺度元数据及源/目的地址分配。数字仿真可使用显式有限容量和带宽的行为内存。 |
| **递推状态、分支与模型特有计算** | #168 的 R256 适配已覆盖 GDN/SSM 代表链路，现有 N 支持 TopK，五类 Block 各有原生服务。 | 固定跨层/跨头的 R 状态与卷积历史存放位置、装载、候选写回、版本发布和复位恢复。把 Qwen3.5 GDN、Falcon 并行 Attention/SSM、Granite 专家选择和 top-8 专家权重搬运接进整网程序。确认 dense Attention、因果掩码、RoPE 和 Gemma 滑窗的完整端口覆盖。 |
| **模型边界与数值格式** | #154 在 host 完成权重索引、部分动态尺度、原始 KV/R 状态管理等职责，冻结 SystemC 的 E 操作与 main RTL 存在版本差异。#198 已有 M 的实权重投影对照。 | 给 embedding、词表投影、argmax 与 token 回送定义职责归属。允许 host 执行的部分需通过固定输入/输出接口声明。固定每条边的有符号位宽、尺度编码、舍入/饱和、大小端、填充和部分字掩码。逐层补齐 host 格式服务对应的 RTL 命令或显式接口。 |
| **整网测试台与计数** | #168、#195、#196、#198 有独立定向回归、真实操作数和周期记录。 | 实现检查点内存镜像加载和完整输入输出驱动。以逐层边界、逐 token logits/argmax、缓存与状态为对照，分别统计计算发射、供数等待、背压、各 S 占用、外存读写、FIFO 和两个时钟域的周期。把 host 发射和测试台提供的行为与 DUT 事务分列。 |

## 数字仿真的验收顺序

1. 用一个 dense 模型的完整单层和真实输入打通从权重读取、KV 读写到该层输出的往返，检查 RTL 自己发起并退休全部内存事务。
2. 使用同一套接口执行该模型全部层、至少一个 prefill 和多个 decode，逐 token 对账，确认有限 S 和外存模型下可以持续运行。加入背压和错误响应。
3. 扩到 GDN、SSM 和 MoE，再用同一计数和数值合同评估七模型。将各模型的顶层、镜像、检查点、时钟配置和日志绑定。

[参考七宏顶层 #168](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/168) · [控制研究 #180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180) · [DMA #182](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/182) · [九实例计划 #184](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/184) · [五类 Block 控制 #195](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/195) · [编译切片 #196](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/196) · [接线端点审计 #206](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/206) · [整模型 SystemC #154](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/154)
