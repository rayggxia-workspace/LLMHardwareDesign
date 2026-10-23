# Issue32 Qwen 局部精度候选与主线接口

状态：实验候选，待主线审查。关联 [Issue32](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/32)、[PR36](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/36)、主线 PR26@2cd9ca15。不替代全项目最终合同。

## 采用候选的原因

在固定官方真实权重上，只有权重 INT8 的假量化对照通过原门槛，而激活 INT8 和原始逐行 W8A8 产生主要质量损失。校准平滑改善但仍有失败。改为 K 分组可缩小异常激活对同组其他通道的影响；实际矩阵调用仍为 INT8×INT8→INT32，代价是更多 scale、部分和与控制。

Qwen2.5 的 K128 已通过4096个新预测 token 和原4个回归样本。Qwen3.5 的 K128 通过新4096-token集，但原回归一项 KL=0.070306>0.05；失败保留。更细 K32 的方法及新样本选择已在运行前冻结，新样本排除所有既有 K128 验证源行。是否通过以结果报告为准，不能从工具存在推断。

## 逐边界格式

| 边界 | 本任务实测形式 | 尚未证明的硬件替代 |
| --- | --- | --- |
| 覆盖的投影、FFN、门控投影矩阵 | W/A INT8，K32或K128；每组INT32累加，真实CUDA内核，INT64样本独立核对 | 不含embedding、lm_head与卷积矩阵；不能说全模型所有矩阵INT8 |
| 每组 scale、bias、部分和 | FP32 dequantize后累加，最终转FP16 | 整数 M/r 编码、统一输出scale、RNE、饱和、部分和位宽需要主线冻结与核对 |
| QK/PV attention、softmax/RoPE/归一化/SiLU/sigmoid/exp/softplus | 原生浮点 | 非线性查表、归约、倒数平方根及误差预算未验证 |
| KV | 原生FP16；独立INT8/16/24/32量化—反量化扰动 | 即使INT16敏感性通过，也未证明整数attention或整数scale |
| Qwen3.5卷积状态 | 原生FP16；FP32对照中提升为FP32；分种类扰动 | INT16量化—反量化对照不等于整数卷积更新通过 |
| Qwen3.5递推矩阵 | 原生FP32；FP32计算对照中独立扰动 | INT16扰动失败；INT24/32敏感性通过不等于整数递推更新通过 |

## 容量、端口与通信必须计入的差异

W/A 每 K 个 INT8 值配4-byte FP32 scale：K128增加3.125%逻辑字节，K32增加12.5%。权重按每输出/每K组存scale；激活按每token/每K组生成scale。K32比K128需要4倍scale条目及4倍部分GEMM调用，不能用此前逐行scale的数量估算通信。

部分和输出是FP32，每组需要重定标并读改写输出tile，或在本地寄存器/SRAM中累加。若跨Block传输，必须说明发送INT32原始部分和与scale，还是发送FP32已缩放值；这两种都不同于只发送INT8激活。GPU观察到的是逻辑操作和实际分配，不是目标芯片总线流量或收益。

Qwen3.5 原生缓存为固定49.5MiB（48MiB递推+1.5MiB卷积）加32KiB/token的KV；8224 tokens约306.5MiB。Qwen2.5为36KiB/token，8224 tokens约289.125MiB。FP32计算诊断会把KV/卷积升为FP32，必须独立分组，不能用该分配当最终缓存容量。

若采用独立扰动中较保守的 INT16 KV/卷积与INT24递推提案，Qwen3.5：KV16增加每head/token/vector一个FP32 scale（8224词元约2.008MiB）；卷积16加每channel scale约0.75MiB；递推24若真打包仅36MiB，加每head/key-row scale约0.375MiB。合计约297.633MiB，仅比原生306.5MiB减少约2.9%。当前量化器的INT24代码用未打包INT32临时保存，**实际分配不享有这12MiB节省**。动态scale还需amax、舍入与状态重写的控制/带宽。

递推状态不能因矩阵INT8就按INT8容量计算。以24-bit状态和16-bit系数为一个待验证的整数方案，单乘积需要40位；128项不舍入求和需要再留7位；若继续乘16-bit门控而不重定标，可能进入63-bit中间量范围。这里仅是条件位宽上界说明，未冻结系数格式和舍入位置，不是已通过的INT64状态更新合同。

原生FP32递推状态若每token完整读写，24层的逻辑读+写约96MiB/token；在片上驻留也需要相应本地端口预算。INT24真打包可降到约72MiB/token但另有scale访问。它们是逻辑下界示例，不能当作测得的DRAM流量；状态复用、分块流水、缓存驻留与并行head数会改变外部通信。

## 主线的可审查输入

本任务提供固定短/长teacher-forced token IDs、真实Q/K/V、g(log-decay)、beta(sigmoid)、选定状态和实际INT32分组部分和。捕获边界明确区分内部QK L2归一化之前与之后。主线可用这些真实输入验证 M/r 与整数状态更新，而不需要重复下载模型或采集每层每步大状态。

待主线冻结：整数scale编码/更新规则、INT32部分和统一重定标、KV/递推/卷积状态格式及打包、非线性近似、逐步舍入/饱和与质量验收。用户通知主研究线检查仓库后整合；本任务不自行合并PR、不替主线发布最终合同。
