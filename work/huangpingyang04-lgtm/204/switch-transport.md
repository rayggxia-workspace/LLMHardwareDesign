# Qwen 九实例传输与 C0 四选一

任务 [#204](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/204)，草稿 [#206](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/206)。接续 #176 的 23 条 Qwen 候选传输和 #194 的宏版图。按用户选择，已有计算宏内部连接留在原生层，新增上层试布只连接传输模块与计算宏。

## 实现与范围

- C0 有 P2、U0、U1、F0 四个接线输入。一次只选一路。C0 的 SRAM 写确认返回给所选发送端，随后才能释放源数据。[C0 实现](../../../project/rtl/qwen_transport/c0_receive.sv)
- 九实例版按实际的 P/J SRAM 请求/响应和 U/C/F 的 TX/RX 信号接入，检查 23 条许可关系。仲裁由传输命令选择，硬件每次只保留一笔 128 位传输。目的地址与接收预约来自控制器。[九实例实现](../../../project/rtl/qwen_transport/nine_transport.sv)
- 布线输入包括跨宏数据、地址和握手，C0 版 711 根，九实例版 2,491 根。每根有两个实际 M10 端点和唯一输出驱动。C0 版另外 30 个传输模块控制端点，九实例版另外 44 个传输模块控制端点，属于父层控制、预约、时钟及复位的接入边界。外存权重/KV/状态及系统供电与时钟另行集成。

## 功能验证

Slurm `98443`，Verilator 5.042，两种配置均成功退出。C0 版逐一测试四个来源。九实例版覆盖 9×9 源宿组合及两个越界选择，许可路径进行真实数据比较，其余要求拒绝。覆盖读等待、接收预约、延迟写确认和未确认时的协同复位。端口驱动由独立协议模型提供。源提交 `96889ecf8d72eee514ea1a98beb4f2af84b1a367`。[测试代码](../../../project/experiments/nine_block_route/tb_qwen_transport.sv)

## 物理流程

原生版图在 Nangate45 做 M1–M10 P&R，以可接 via10 的真实 M10 落点输出 LEF。首轮综合的 ABC 持久进程已写出映射文件，但在等待完成信号。改用同一二进制的批处理模式后恢复。旧卡住的自有作业 98429、98437、98438、98445、98446 在新流程开始实际布线后释放资源，日志保留。

| 源提交 | 作业 | 范围 |
| --- | --- | --- |
| `415834ff7d56204189fa42be3449358129e5f4a6` | 98449–98452 | 两种边缘落点原生版图及上层搜索 |
| `385444d16c5b09e7a4f2085751e5082e13a64ab9` | 98456–98457 | 独立上层通道对照 |
| `44521a9d9c438e3f69f5b07da1b29d836e84c226` | 98461–98462 | OpenROAD 上层详细路由 |
| `0b59f26c18aec9a54fd875899ae4c84d649a5e84` | 98463–98466 | 网格落点原生版图及上层通道 |
| `1c61cc5c21a740fec371bd1ff6f0579646470579` | 98467–98468 | 保留已绑定端口的 OpenROAD 详细路由 |
| `b1f5ec4c4a4dcc7ce24bfa4f2eacc5b64a5c9a4a` | 98471–98472 | 上层多转弯引出 |
| `82a47c633072e70896680e18c4449a42445d7917` | 98478–98480 | C0 输入天线保护、上层布线及独立 GDS 复核 |

复跑入口为 [原生构建](../../../project/experiments/nine_block_route/run_switch.sh)、[真实 M10 绑定](../../../project/experiments/nine_block_route/bind_switch.py)、[独立几何路由](../../../project/experiments/nine_block_route/run_switch_upper.sh) 和 [OpenROAD 详细路由](../../../project/experiments/nine_block_route/run_switch_drt.sh)。上层作业以 #194 的五份验收 LEF、同版研究叠层和已经跑完原生布线的传输模块 LEF/GDS 为输入。
