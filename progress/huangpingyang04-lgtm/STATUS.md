# huangpingyang04-lgtm 进度

## 2026-11-06，Asia/Shanghai

[Issue #197](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/197)。完成七模型整模型 SystemC 回放及 63 个位置的冻结数值核验，完成 28 组 SystemC 投影、84 组 RTL 投影、9 组 DMA 时钟/信用及 3 组七宏顶层回归。服务器回执和复现入口见[报告](../../docs/experiments/issue-197-seven-model-system-bench.md)。[PR #198](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/198) 已提交，待独立审查。

整模型低位宽评估待接量化导出和计算路径，逐周期评估待接整网控制映射与有限内存，能耗换算待补活动覆盖和系数。登记 PR #5 pending，仓库缺少 `config/board.json`，Projects 看板待维护者核验。


七模型长度补测已完成。每模型处理 23 或 24 个位置并生成 12 个 token，七模型独立 FP32 均完成。共 163/165 个同前缀 Top-1 一致，严格数值门 5/7。逐步 KV、R 和 C/D 搬运及两处分叉见[长度扩展报告](../../docs/experiments/issue-197-long-systemc.md)。整模型 RTL 的顶层、镜像、传输、状态和测试接口见[缺项清单](../../docs/experiments/issue-197-full-model-rtl-gaps.md)。同一 PR 待独立审查。

已将七模型位宽、内存、流水、时钟及能耗活动的对比集中到[对照表](../../docs/experiments/issue-197-seven-model-comparison.md)。表格基于已验收回执，区分整模型、投影切片和 DMA 的数据范围。

七模型能耗分项估算已补到同一 PR。复用 #155 的 SRAM 表征及既有 SystemC、RTL 计数，单列外存覆盖和端口负载假设。见[估算与系数](../../docs/experiments/issue-197-seven-model-energy-estimate.md)。


作业 98611 已对账七模型 165 个位置的 C/D 暂存接口，补齐归一化权重、KV 切片及派生操作数、R 卷积历史的流量和 SRAM 分项。移除 10% / 100% 外存比例，DDR/HBM 读写及能量待整模型接入后测量。见[外存访问核对](../../docs/experiments/issue-197-seven-model-energy-estimate.md#外存访问核对)。


Qwen3.5-4B SystemC 的权重、KV 与 R 端口已打通。两位置试跑 `98690` 数值和事务通过核验，七模型原长序列数组 `98704` 全部完成，`98729` 已汇总 165 个位置的权重、KV、R 矩阵与历史读写。七份 hidden/logits 与原输出逐字节一致，已补外存参考能量，器件能耗待校准。RTL 缺项细化到描述符、AXI/DMA、预取、KV 与 R 写回接口。[SystemC 外存接入](../../docs/experiments/issue-197-systemc-offchip.md) · [PR #198](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/198)


## 2026-11-07，Asia/Shanghai

Qwen3.5-4B 的第 0 层 GDN 与第 3 层注意力已在服务器通过完整 2,560 维、两位置联调，包含 FFN。M/N/E/G/R 原生 RTL 与 #182 DMA 通过同布局 SystemC 对账，四个层输出与冻结基准一致，R 矩阵和历史写回/重载及 KV 增量均验收。执行 99627、核验 99629 通过。[结果和接口边界](../../docs/experiments/issue-197-qwen-rtl-layer-dma.md) · [PR #198](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/198)。后续整网控制与统一时钟仍待接入，Projects 配置待维护者处理。
