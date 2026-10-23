# Issue56：Llama-3.2-1B本机跨模型最小验证

2026-10-23，Asia/Shanghai，Liangruizhi。[Issue56](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/56)/
[PR57](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/57)，task/56-llama-cross-model，base PR54。
正式推理/整数/服务源码628c093db2a62a94be30ab22bb4fa176cd081761。全部本机执行，复用已有环境与模型，未增加远端作业或下载。

## 输入与实际架构

先读用户指定HANDOFF.md、MAIN_CHAT_PROMPT.md、download_receipt.json与offline_smoke.json。
9文件重新逐项核SHA；来源ModelScope d3e551343d4d81508a0d226656b826c217e463cd，
对应Meta官方公开元数据9213176726f574b556790deb65791e0c5aa438b6。
权重2,471,645,608B，SHA256 1ff795ff6a07e6a68085d206fb84417da2f083f68391c2843cd2b8ac6df8538f。
原BF16 checkpoint转FP32计算，不称独立原生FP32权重，也不把旁支BF16 smoke作为整数验收。

| 本次固定模型 | 既有Qwen3-0.6B | Llama-3.2-1B |
| --- | --- | --- |
| 层/hidden/MLP | 28/1024/3072 | 16/2048/8192 |
| Q/KV头、head_dim | 16/8、128 | 32/8、64 |
| 一组GQA | 2Q/1KV | 4Q/1KV |
| 独立Q/K norm | 有 | 实际Attention代码无此步骤 |
| RMS epsilon | 1e-6 | 1e-5 |
| RoPE | 固定配置、theta1e6 | llama3频段缩放、theta5e5 |
| tied embedding | 配置声明true | 配置true，运行时输入/输出weight指针相同 |

Llama实现文件SHA31bf660a663259134324bc65da4e155951dc89c5ca46471d2325a9938e859e26，
cache实现与torch2.10.0+cpu/transformers4.57.6/NumPy版本、模型配置全部随manifest绑定。
两模型都声明tied embedding，不能把它编成架构差异。此处只覆盖该1B变体，不代表全Llama家族或原R1 MLA/MoE。

## 冻结协议与精度

B1、layer0、Q0..3/KV0，head_dim64；校准32 token，另两段systems/arithmetic各prefill32+decode8。
规则原样复用Issue47：静态KV、当前行Q scale、校准独立且全GQA共享的dyadic Q/K变换，P15、相同LUT/RNE/饱和。
Q/K/V与attention输出在post-RoPE/pre-o_proj边界采集；模型norm/RoPE/其他层仍是FP32参考，不是全整数模型。
完整与cached的所选Q/K/V/输出通过1e-4绝对/相对门，最大观测差约3.81e-6；cache及因果mask显式核对。
未把局部误差设为模型语言质量验收；三段文本不是质量集，也不在评价数据上重拟合scale。

线性：q_proj取覆盖本GQA的256个完整输出、K2048；down_proj取16输出、完整K8192。
W8每输出dyadic scale；A8为校准静态或当前行动态、范围[-127,127]；K128部分乘积与完整K累加均INT32。
M=2^30、r0..63、RNE/Sat8，输出scale由独立校准Y两倍裕量编译。bias不存在，本次不证明RQ33。
量化/scale/M/r生成离线浮点；NumPy INT32计算和宽整数参考不等于真实8位阵列内核或INT8速度。
P15×V8沿用多次8位乘/宽合并；除法、LUT、状态版本等成本保持原候选边界，不宣称完整硬件已支持。

KV为每头静态dyadic scale的INT8，score为INT16/f8，P15存INT16非负容器；exp表U32/f24、sum_exp U64，
PV宽对齐/累加I64后RNE/Sat到INT16/f12。共享g为I8，scale exponent为I8，M为31有效位U32、r为U8。
本模型没有递推R状态，本轮不能验证R合同；norm/RoPE与模型其余非线性仍浮点，未通过转换/宽乘/查表完整硬件实现。

## 数值结果：通用算术可复用，统一静态scale不能直接冻结

| 局部输出相对RMSE | systems | arithmetic |
| --- | ---: | ---: |
| 直接Q/K/V8注意力 | 3.778% | 4.022% |
| 校准共享QK变换 | 3.237% | 3.107% |

全GQA共享、不可变KV和因果stream/batch均通过；所选源full/cached代码及整数输出无差异。
这里是该组attention输出的误差，不是logits/PPL或模型质量通过；不能把Qwen短切片约1.8%结果移植为Llama结论。

16个线性条件中的8个q_proj条件相对误差1.14%–1.36%。down_proj静态A scale误差70.34%–82.87%，
动态行scale降至6.17%–16.86%。各条件输入裁剪和最终INT8饱和均0，INT32无溢出；这些检查通过仍不意味着量化误差小。
静态down输入约99.84%–99.89%变0，动态约33.45%–43.53%；当前校准全张量A scale过粗的风险明确暴露。

保存张量的浮点反量化消融（辅助诊断，非硬件执行）显示：静态down在最终RQ前已有约70.40%–82.64%误差；
仅量化激活已产生约70.40%–82.61%误差，不能把大部分错误归咎于最终RQ位置。
单独权重量化的局部误差约1.37%–6.48%，与激活误差不作可加因果分解；详见work/Liangruizhi/56/stage-diagnosis.json。
动态行scale仍未达到可接受应用质量的证明，不能依据较小误差就宣布合同成立。

完整K INT32核对43520输出，独立INT64与Fraction RQ一致；逐K128前缀未溢出。
保守界K×127²分别33,032,192和132,128,768，低于INT32上界；此界只针对本次相同乘积scale的合同。
错误地每K128先RQ/饱和再求和会改变28950/43520输出，是“完整归约后才RQ”的真实输入反例，不能把该错算法当性能基线。
近端RQ与共享RQ的实际typed packet重放逐位一致，完整K/格式/分片/padding合同沿用已绑定工具。

## 容量与端口：先改tile，RQ位置继续条件化

复用Issue51资源：M32KiB含MC6KiB+PE2KiB，V16KiB，S8×32KiB、1RW/128bit、64B header/payload对齐、有限2KiB FIFO。
W/A预装区为S0..5，S6 META、S7结果。K8192/16行时W16×K与A16×K已占256KiB，不能在当前预装合同中再免费容纳参数/结果。
明确拒绝该点后以8行down tile测试，W128KiB+A64KiB占六bank；同一位置配对资源/精度完全相同。
这不是Llama不能运行，也不是所有可能分配都必须8行；流式外存/不同生命周期合用bank属于新合同，要重新计账。

384固定配置、192匹配位置对，各自产生资源/依赖/credit审计；两轮科学文件完全相同。
同一库存内两边各取既有窗口/调度最好值的48个描述性对照中，近端47更快、1略慢，
最大周期降低0.4049%、最差增加0.0283%。这些服务未校准矩阵/消费者/8lane硬件，因此不足以固定不可绕过近端RQ。
decode N16的INT32 64B与INT8 16B仍各占128B物理包，未节省边界物理传输；仅限当前立即发送合同，合包需另计缓冲/等待。
四次代表N16 tile重复是服务压力，**不是完整q_proj/FFN或GQA attention服务**，没有完成E2b的M/A三遍attention配对。
高误差down结果只作为固定语义结构敏感性，不能据此报可接受W8A8应用加速。

## 对Block候选的取舍

保留M/V/A/S/D模板与可配置norm/RoPE，GQA4通过共享KV/调度描述实现，不按4个Q头制造4份KV或新增模型专用Block。
每组40token K/V8为5120B，48token容量6144B；逐Q头复制会变成20480B。Q/K balance向量64B、K/V exponent2B，
当前行Q exponent与score M/r为4×40×(1+5)=960B，按实际metadata而非把FP32字节统一除4。
这些是本次逻辑数组/数值参数，另有profile身份、版本/位置等协议成本；本轮尚未给出完整GQA参数包线上编码，不能把这些成本归零。
服务对照另计实际META包。数字不含物理SRAM粒度/ECC/额外FIFO；全模型KV和接口资格未在此验收。

仍保留相同乘积scale下的完整K内部INT32与typed旁路；不冻结近端RQ必配，也不冻结所有算子的单一静态A scale。
下一项最小精度研究针对FFN激活校准/量化粒度和动态scale生成成本，不增加模型矩阵。
若改成K分组scale，组间INT32部分和不再天然同单位：须增加显式重定标/宽归约，重新验证M内留或共享V边界，
不能把“完整K INT32内留”的本次结论直接套过去。预处理、量化粒度和Block划分应联合选择。

## 验证、归档与未同步项

正式源码干净运行；三项资源/早RQ合同测试、管理/AST/whitespace通过。
GQA独立输入61440、oracle117760、Decimal参数1280、160 cache发布事件；40960 stream/batch与98304 future检查通过。
线性独立源代码2293760值、43520 INT64/Fraction输出通过。两轮18科学文件逐字节相同；不是两套硬件实现。
服务producer审计1193280节点/194496包；独立读取8 witness的33560节点及48包络重算通过，依赖篡改被拒绝。

[精简可复查包](../../project/experiments/llama_cross/results/issue-56-run01/index.json)：2,468,347B，178成员，
SHA256 6f63d89990294952da0c69ffb401e1c8eeb547e9650a0e25cf6b8fad95633652。
135份内容去重数组包含**全部编码线性/GQA整数输入输出**及原始GQA小张量；解包后独立INT64/Fraction/oracle重放43520/117760值和8服务witness通过。
对输出码改值、重算对象hash并更新索引后，独立数值重放仍拒绝；不是只靠文件checksum发现问题。
review.py不重算全K浮点线性量化校准；该项由本机audit_linear.py用完整capture执行，限制不可省略。

完整FP32线性原始捕获（gqa-group.npz约9.18MB）及全量/重复NPZ保留D:/Projects/Codex/llama-local-20261023，
其逐文件位置/大小/SHA在包中local-data-index.json；原捕获NPZ SHA b9de8825b6f063a3924aef25d3132b2ef28e7c2e445500d6d3bb123b6e96541c，
输入JSON SHA 2f7c8e706a9af7009dbe60fd53ce35938039b6c3cf14f2ca837309644b15699c。
为遵守本任务仅本机，未转存服务器；完整原始输入共享**待同步**，不能把本机数据位置说成团队已可访问。
模型权重不进Git；新模型/长上下文/GPU、全模型质量、全整数向量链和物理验证均未执行。
