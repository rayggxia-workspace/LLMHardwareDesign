# Issue247：原生准入和条件 token/s 分开验收

2026-11-09，Asia/Shanghai。负责人 Melodydt；关联 [Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)、[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。

## 决定

当前原生 P 的 S8/S16/S40/S64、K≤32、四个1RW bank合同与历史整模型条件仿真的S32/S96/理想宽端口不同。新版吞吐测试不得继承旧token/s作为原生成绩，也不得按局部百分比外推整网。

先执行原始trace的严格准入；缺少S32无损转换、S96合并、完整指令/DMA编译和原生U路径时明确拒绝。可独立开展的整图时序实验以实际P命令校准为基础，显式计入候选硬件、有限存储、转换及ACK费用，结果使用`conditional_tokens_per_second`字段；原生整模型速率保持`null`。

## 代价与后续

该选择会得到与旧候选架构明显不同的绝对速度，不能将两个模型的数字解释为版本性能回退。新旧接口程序的公平对照保持相同trace、时钟、外存、原生端口与共同候选适配器；每P2712B额外适配器寄存器显式列账，面积待验。串行P程序不报告尚未安排的bank并发和预取收益。

下一阶段若要求真实原生整网token/s，需交付可执行指令流、真实权重/激活格式合同、转换和完整控制/DDR路径、数值验证及物理频率证据，再取消准入拒绝。当前研究既不实装SRAM扩容，也不自动启动这些新增硬件工程。[测试报告](../experiments/issue-247-native-token-throughput.md)。
