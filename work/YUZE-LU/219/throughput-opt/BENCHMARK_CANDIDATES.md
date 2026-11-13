# 3–4B性能对照候选与证据边界

2026-11-09 CST。属于Issue219的后续验收准备，**尚未完成本项目SystemC性能、能耗或公平对照**。
外部数字为作者报告，不是我们复现；不按参数个数机械缩放，也不把不同量化/质量混成同条件胜负。

## 范围内的优先候选

| 候选 | 实际工作负载与原生配置 | 一手来源报告 | 仍需补齐 |
|---|---|---|---|
| llama.cpp U280后端 | Llama-3.2-3B-Instruct，Q4_K_M，同GGUF与CPU校验 | tg128为92.7 token/s，pp512为114 token/s；各五次均值 | 作者代码当时私有；频率、功耗、完整构建与长期上下文口径未给出，不能称独立复现 |
| 同一U280后端 | Qwen3-4B，Q4_K_M | tg128为72.5、pp512为83 token/s；论文式比较前保留“同版本后续构建”脚注 | 同上；还要固定具体GGUF和质量评估 |
| VitaLLM ASIC | 3B BitNet，三值权重/INT激活，预测稀疏注意力 | 作者报告16nm、1GHz，decode 72.46 token/s、64-token prefill 0.88s | 缺完整checkpoint、decode上下文/top-K及同范围质量、DDR/主机功耗边界，不能直接移用到Qwen2.5 |
| Slim-Llama ASIC | 原生二值/三值Llama | 官方论文索引可核实研究及ISSCC DOI | 当前摘要不足以建立完整prefill/decode比较；不把低频最低功耗和另一频率吞吐拼在一起 |

U280两行来自作者的[实际后端记录](https://zedongpeng.com/blog/2026/llama-cpp-on-an-fpga/)。
tg128是从空缓存生成128 token，pp512是512-token输入；不能当成长上下文稳态decode。
这两行保留作者的原生4-bit实现，**不会为迁就本项目S16/S32标量后端而把对方降级**。

VitaLLM数据来自[原文摘要及Table I](https://arxiv.org/html/2605.00320v1)。
该文使用预测稀疏注意力，现有文字未给出足以核对稀疏策略质量的实验；因此目前是ASIC候选，
不能据吞吐或芯片功耗直接宣布端到端能效胜负。
Slim-Llama保留[KAIST官方论文索引](https://pure.kaist.ac.kr/en/publications/slim-llama-a-469mw-large-language-model-processor-with-binarytern/)，
后续需要原文/可核实的完整配置。

## 只作相邻研究参考

- [TeLLMe v2](https://arxiv.org/html/2510.15926v1)实测对象为BitNet **0.73B**，不是3–4B。
  它的KV260数据流/融合方法可以参考；25 token/s不能进入本任务3–4B主比较表。
- [TerEffic v2](https://arxiv.org/html/2502.16473v2)报告2.7B HBM辅助配置727 token/s。
  它超出了本轮严格3–4B范围且模型/量化不同，只列相邻参考；旧v1的521不当成最新版。
- 30B-A3B MoE的“3B活跃参数”不等于3B总权重容量，必须另表，不冒充3–4B密集模型。

## 本项目怎样形成可比较结果

1. 固定具体checkpoint/权重哈希、质量门槛、batch、上下文、生成长度与采样；保留外部原生最优配置。
2. 新后端先用完整数值回放，确认所有转换、打包、KV和状态都由已声明能力承担。
3. 以实际指令/描述符驱动SystemC，显式模拟S/端口、队列/信用、宏上下文、控制、外存与ACK。
   先与RTL原语和系统小图校准，再给TTFT、prefill token/s、decode TPOT/token/s；S2无KV不冒充decode。
4. 能量拆分宏、SRAM、互联/时钟/控制、外存及泄漏。尚未表征的项显示缺口/敏感性，不能用任意每MAC常数凑功耗。
5. 分别报告“同质量/近似资源预算”及“对方原生最佳配置”；面积、带宽、精度不相同就明确列出。
6. 若落后，记录计算利用率、重复搬运、端口/银行、上下文、控制和带宽的证据。
   编译问题在PR220修复；确认属于硬件合同/实现的问题再建立关联Issue及独立PR，不悄悄增加硬件。

这些记录落实用户要求的比较方向，不代表当前底座已经达到任何外部吞吐。
