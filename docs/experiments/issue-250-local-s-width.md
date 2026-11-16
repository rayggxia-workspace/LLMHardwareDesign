# Issue 250 的局部 S 位宽与验收口径

旧版 NoPool 使用现有 16 KiB S，显式 A 和 COPY 路径已有窄口费用。它的公共 S 服务仍以每拍 64 B 计费。后续为复用现成的普通 S 接口，把公共 S 费用改为每拍 16 B，并以单一 S128 端口实现。保留这版以验证计算、写确认和控制。产品位宽在完成宽口对照前保持开放。

## 同工作量位宽对照

Slurm 102127 使用同一条 Qwen2.5-3B B1 context512 decode trace、同一份 NoPool 配置和同一外存预算。三行仅改变 `NS_PORT_SCOPE`，均计 64 B DDR beat 和 51.2 GB/s 总外存预算。逻辑读 3,365,952,512 B、写 8,191,232 B 和 3,028,352 个 M 命令均相同。公共 S 拍数按接口宽度计算，实际银行冲突、布线和协议开销需另验。

| SystemC 公共 S 服务 | 周期/token | token/s |
| --- | ---: | ---: |
| P/U 均为 64 B/拍 | 32,524,602 | 9.223787 |
| 仅 P 为 16 B/拍 | 37,948,820 | 7.905384 |
| P/U 均为 16 B/拍 | 39,497,418 | 7.595433 |

两侧都收窄增加 6,972,816 拍，吞吐下降 17.65%。仅 P 收窄增加 5,424,218 拍，其中 Dot 跨度增加 4,721,535 拍。两侧收窄的 Dot 增量为 4,849,527 拍，占总增量约 70%。较新的 5.999543 token/s 回放还替换了 FFN 实测服务和动态 Dot 成本，不能从 102127 的差额推算它换宽后的速度。9.223787 记录的是旧宽口假设下的时序；当前 S128 独立作为可复现的 RTL 对照。算法收益只从相同硬件接口和费用的 DP/强贪心对照提取。

[102127 原始回执](../../work/YUZE-LU/250/native-service/run-03/recovery.json) · [位宽复核](../../work/YUZE-LU/250/native-service/port-width-audit.json) · [#249 的接口及四权重银行记录](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/85fe7989b11a95725c9b1bc6daee085f74a500b8/docs/experiments/issue-248-followup-design-ledger.md)

## 恢复宽通路的实现范围

原 S_P 具备同一行四个 128-bit 1RW SRAM bank 一起读出的 512-bit feeder 数据路径。普通读写只选一个 bank。原 S_base 关闭了这条宽读通路，原有 wrapper 也没有四 bank 同拍写。当前 W8A16 M 的权重回传保持 512 bit，A 口为 256 bit，局控命令和普通结果回传保持各自的既有合同。

1. 优先试 P 内的 DDR 落地和 Dot 操作数路径。原四 bank 按地址低两位交错，64 B 对齐的一行可以对四 bank 各发一个 128-bit 访问。把宽读和候选四 bank 写做成有界的服务，保留普通 S128 操作。bank 同拍只能执行一次访问。每个宽请求占用四 bank，读写仲裁、结果保持和真正写确认都进入费用模型。
2. 固定同一组真实 bank、算术、源序列、地址和外存返回。对比 4 次普通访问和 1 次宽访问，回读逐位校验，分别测接受、全 bank 提交、响应消费以及 Dot 完成。覆盖普通请求竞争、背压、尾块、窗口越界、取消和迟到确认。统计真实吞吐、额外保持寄存器、控制和端点。
3. 区分片内四 lane 与跨组 512-bit 路由。片内短连由真实布局、拥塞、PG、DRC 和提取的 300 MHz 时序验收。跨组宽链路按各组流量及 M10 接入、M11/M12 容量和 RC 单独判定。外存预算、SRAM bank 数和 M 输入消费能力保持固定。
4. 宽服务经真实 SRAM 和 Dot 对照后，再按受测的银行日历、事务粒度和 ACK 费用更新 SystemC。DP 在同一份资源清单下对照。其余仍使用窄接口的服务按真实成本保留。

[现有四银行存储](../../project/rtl/s_sram/block_feed_s16k_sram.sv) · [S_P 宽读](../../project/rtl/s_sram/local_s_p.sv) · [S_base 普通端口](../../project/rtl/s_sram/local_s_base.sv)
