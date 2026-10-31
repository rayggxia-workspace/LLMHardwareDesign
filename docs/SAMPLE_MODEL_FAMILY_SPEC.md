# 仓库八样本FamilySpec与证据边界（步骤1）

本稿为 Issue151 前三步中的 FamilySpec 独立交付，父版本 `39bd7bf66c47e17c18aa39483c1d974a1e079aa2`；对应机器规格为同目录 [family-spec.json](../work/Melodydt/151/family-spec.json)。已完成选定源码/配置/图的提取、形状与来源规格，待主负责人整合评审。**没有执行推理、RTL/SystemC、服务器作业或EDA，没有完成整模型或系统硬件验收。** 不把前三步的规格形成写成全部合法连接已实现。

## 1. 范围与证据口径

本轮仅保留仓库现有八个具体样本和十种层型，不扩大到其他同名尺寸/权重版本，不考虑多模态路径或MTP。成品入口、层表/形状/尺度等永久参数由M11/M12绑定，不依赖bootload控制程序。暂不考虑外存：不能用外存、host流或不存在的无限缓存解释缺失容量，也不能把H/I/头数偷偷缩成适合当前S的mini模型。

已通过Melodydt连接读取固定提交中的三主文档、十份实际导出config、成功manifest、GDN/Falcon简化图及实际导出脚本。19份原始UTF8快照只保存在本地 `family-sources/`，`source-index.json`记录path/ref/Git blob SHA/SHA-256/bytes/行数；全部Git blob一致。十份config的SHA-256也逐一匹配原导出manifest，native_export.py/v3的SHA分别匹配原运行源码。**完整graph快照不作为正式上传内容**；通过固定GitHub链接和指纹追溯。

来源层级必须分开：

- [实际配置及导出回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/render01/manifest.json) 给出原模型配置、代表层检查点绑定、版本及文件SHA，属于本轮读取到的既有证据。
- [精简图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L33-L46) 给出完整依赖与部分展开；它是人工语义核对图，不是执行过的IR。
- [FULL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/COMPUTATION_GRAPHS_FULL.md#L31-L51) 说明实际图只验证了B1/S2、FP32、eager/eval、use_cache=False；三组输入种子17/31/73，raw/native容差rtol=atol=3e-4，sim/raw为1e-5。其余九种层型加载真实指定层权重，Llama为配置重建/随机参数，不能声称原Llama检查点通过。
- [既有实验分析](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/MODEL_EXPERIMENT_ANALYSIS.md#L37-L48) 另有组级GQA、局部窗口、连续状态或整数切口证据。它们有独立输入、格式和切口，不能混成十层ONNX已经验证长序列decode或整网。

`max_position_embeddings` 是冻结config记录的源位置范围，不是本项目已证明的最大context、硬件能支持的长度或本次导出实测长度。

## 2. 八模型真实维度与源配置上界

表内Q/KV与D指常规Attention分支；Qwen3.5的GDN另列16/32 key/value头，不能把全局层D256套到GDN。

| 样本ID | 层数 | H | FFN I | Q/KV头 | D | Q宽/KV宽 | config max_position_embeddings |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen25 | 36 | 2048 | 11008 | 16/2 | 128 | 2048/256 | 32768 |
| qwen3 | 28 | 1024 | 3072 | 16/8 | 128 | 2048/1024 | 40960 |
| llama | 16 | 2048 | 8192 | 32/8 | 64 | 2048/512 | 131072 |
| gemma | 34 | 2560 | 10240 | 8/4 | 256 | 2048/1024 | 131072 |
| phi | 32 | 3072 | 8192 | 24/8 | 128 | 3072/1024 | 131072 |
| qwen35 | 32 | 2560 | 9216 | 16/4 | 256 | 4096/1024 | 262144 |
| granite | 32 | 1536 | 512 /expert | 24/8 | 64 | 1536/512 | 131072 |
| falcon | 32 | 2560 | 6144 | 10/2 | 128 | 1280/256 | 131072 |

其中：

- Qwen2.5-3B为base；Qwen3-0.6B为所读实际config；Qwen2.5、Phi和Granite的config未显式带head_dim，D由精简图明确的128/128/64确认，不泛用H/Q推断。
- Qwen3、Gemma、Qwen3.5、Falcon的Q投影宽度分别为2048、2048、4096、1280，均不能用H替代。Qwen3.5全局Wq_gate还输出双份Q宽8192，分为Q和输出门。
- Granite图册沿用“Granite-3.3B”标签，但[实验报告](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/MODEL_EXPERIMENT_ANALYSIS.md#L45-L46) 指定检查点为Granite-3.1-3B-A800M-Instruct。规格保留两种来源名称，避免把它当另一个新模型。
- [Phi config](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native02/phi/config.json) 的original_max_position_embeddings=4096、max_position_embeddings=131072，同时有sliding_window=262144。这三个字段不能互换：262144不是本轮实测长度，也不取代131072的位置配置范围；LongRoPE的48项long/short频率系数在config保留。
- [Llama config](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native02/llama/config.json) 是脚本重建的具体实例：D64、RMS epsilon1e-6，不能从其他Llama公开配置借入1e-5或其他参数冒充此图；其RoPE为llama3、factor32、original8192、theta500000。

原始config固定入口：

| config/层型 | 来源 |
|---|---|
| Qwen2.5 | [native02/qwen25/config.json](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native02/qwen25/config.json) |
| Qwen3 | [native02/qwen3/config.json](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native02/qwen3/config.json) |
| Llama | [native02/llama/config.json](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native02/llama/config.json) |
| Gemma局部/全局 | [native04/gemma_local/config.json](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native04/gemma_local/config.json)、[gemma_global](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native04/gemma_global/config.json) |
| Phi | [native02/phi/config.json](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native02/phi/config.json) |
| Qwen3.5全局/GDN | [native02/qwen35_global/config.json](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native02/qwen35_global/config.json)、[native04/qwen35_linear](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native04/qwen35_linear/config.json) |
| Granite | [native03/granite/config.json](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native03/granite/config.json) |
| Falcon | [native04/falcon/config.json](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native04/falcon/config.json) |

## 3. 十层型、归一化范围与RoPE

下表Norm括号为“每组长度×每token组数”，不是要求同时放入S。L2的32组是实际导出先RepeatHeads后的形状；只有16组独立输入，见下一节。

| 层型ID | 实际代表层index | Attention/GDN头 | RoPE通道 | Norm位置及范围 |
|---|---:|---|---|---|
| qwen25_attention | 0 | 16/2×D128 | 128/128 | input:RMS(2048×1)；pre_ffn:RMS(2048×1) |
| qwen3_attention_qk_norm | 0 | 16/8×D128 | 128/128 | input:RMS(1024×1)；query_head:RMS(128×16)；key_head:RMS(128×8)；pre_ffn:RMS(1024×1) |
| llama_attention | 0 | 32/8×D64 | 64/64 | input:RMS(2048×1)；pre_ffn:RMS(2048×1) |
| gemma_local_attention | 0 | 8/4×D256 | 256/256 | input:RMS0(2560×1)；query_head:RMS0(256×8)；key_head:RMS0(256×4)；post_attention:RMS0(2560×1)；pre_ffn:RMS0(2560×1)；post_ffn:RMS0(2560×1) |
| gemma_global_attention | 5 | 8/4×D256 | 256/256 | input:RMS0(2560×1)；query_head:RMS0(256×8)；key_head:RMS0(256×4)；post_attention:RMS0(2560×1)；pre_ffn:RMS0(2560×1)；post_ffn:RMS0(2560×1) |
| phi_fused_partial_rope | 0 | 24/8×D128 | 96/128 | input:RMS(3072×1)；pre_ffn:RMS(3072×1) |
| qwen35_global_gated_attention | 3 | 16/4×D256 | 64/256 | input:RMS0(2560×1)；query_head:RMS0(256×16)；key_head:RMS0(256×4)；pre_ffn:RMS0(2560×1) |
| qwen35_gdn | 0 | GDN K16/V32，Dk=Dv128 | 无 | input:RMS0(2560×1)；gdn_query:L2(128×32)；gdn_key:L2(128×32)；gdn_output_per_value_head:RMS(128×32)；pre_ffn:RMS0(2560×1) |
| granite_top8_moe | 0 | 24/8×D64 | 64/64 | input:RMS(1536×1)；pre_ffn:RMS(1536×1) |
| falcon_attention_ssm_hybrid | 0 | 10/2×D128 | 128/128 | input:RMS(2560×1)；ssm_after_gate:RMS(4096×1)；pre_ffn:RMS(2560×1) |

所有层型保留完整H/I。普通RMS的gamma=weight；RMS0的gamma=1+weight。Qwen2.5/Qwen3/Llama/Phi/Granite/Falcon为普通输入/FFN RMS；Gemma和Qwen3.5的输入/FFN RMS使用RMS0。Gemma每层六处Norm，Attention后与FFN后Norm都不能省略。Falcon的SSM输出先门乘再跨4096 RMS，QwenGDN则先每value头128维RMS再门乘，顺序相反。

RMS配置epsilon：Qwen2.5/Qwen3/Llama/Gemma/Qwen3.5/Granite为1e-6；Phi/Falcon为1e-5。它们是config实数epsilon，不是N原生epsilon_raw。每个实际归约位点仍须在图编译时绑定常量；整数单位换算、gamma量化和误差均未验收。**GDN L2的具体epsilon数值在所选graph JSON中未恢复**：JSON省略了Constant张量内容，不能拿rms_norm_eps直接填入。L2没有可学习gamma，也不能替换成RMS。

RoPE与缩放差异：Qwen2.5/Qwen3完整D128；Llama完整D64且使用Llama3频率规则；Gemma完整D256，局部theta10000/window1024，全局theta1000000/linear factor8；Phi仅96/128；Qwen3.5全局仅64/256，GDN无RoPE/无QK Softmax；Granite完整D64且Attention multiplier=0.015625；Falcon完整D128、theta1e11，并在RoPE前额外乘K系数0.044194173824159216。cos/sin与mask生成在导出边界之外，不能把S2层内图通过当成频率生成或长窗验证。

完整模型层型序列已逐项写入JSON，并与config数组/文档核对：Gemma34层中global=5/11/17/23/29，其余29层local；Qwen3.5为[GDN,GDN,GDN,Global]×8，即24个GDN+8个Global；Falcon32层均为Attention/SSM并行混合层。这里只记录真实序列，不表示已完成整网导出/运行。

## 4. GDN与SSM尺寸：实际小图补强证据

### Qwen3.5 GDN

- H2560/I9216；key/query原始16头×128，value32头×128；Wqkv输出8192=2048Q+2048K+4096V；Z4096；beta与a/dt各32；depthwise Conv8192组、kernel4，无bias输入。
- [实际simplified.graph.json](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native04/qwen35_linear/simplified.graph.json) 中n00034把Q排为[1,2,16,1,128]，n00035 Tile为[1,2,16,2,128]，n00036再reshape为[1,2,32,128]；K的n00037–39相同。因此该实际ONNX布局有连续重复证据：`key_head=floor(value_head/2)`。此前只有语义RepeatHeads时不能独断轴序，现在保留节点ID和shape证据。
- 实际ONNX先重复32组再L2（n00046/52 ReduceSum形状[1,32,2,1]）；语义字符图先对16个独立头L2再重复。两者针对相同重复向量表达相同数学关系，但硬件只算16组是一种需证明/验证的调度选择，不能把实测节点数或执行顺序改写成已经优化。
- Q在L2之后独立乘1/sqrt128，K不乘；state为[B,32,128_key,128_value]，每B共524288元素。输出4096通道分32个value-head，各128维RMS后与SiLU(Z)门乘，再投影回H2560。
- 无历史prefill从零state开始；带历史decode未由本次ONNX验证。官方chunk核因不支持linalg_solve_triangular，仅导出适配为官方token-recurrent等价核，参考仍是原chunk实现，不能把两个调度说成同一实际图。

### Falcon-H1 SSM

- Attention为Q10/KV2、D128；另有SSM32头，每头channel128、state256、1个B/C group。d_ssm显式4096，不能从H2560×mamba_expand2推成5120。
- [实际simplified.graph.json](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native04/falcon/simplified.graph.json) n00025投影8736，n00027分4096 Z、4608 XBC、32 dt；n00034把XBC分为4096 X、256 B、256 C。B/C一组广播32头。
- Conv为4608组、kernel4、**有bias**（n00029第三输入）；R当前卷积口没有bias操作数，完整实现需要明确偏置加法的宽度/尺度及位置，不能默默省略。
- state为[B,32,128_channel,256_state]，每B共1048576元素；输出4096先乘SiLU(Z)，再一次跨全部4096 RMS，不可每head128单独Norm。
- dt为[B,S,32]，Softplus后Clip；source time_step_limit=[0,+Infinity]，没有可直接冻结的有限dt最大值。图中A×dt结果为[1,2,32]（n00049），逐head衰减再广播；R可表达更一般逐元素decay，不说明此模型必须储存每个state元素独立数值。
- mamba_chunk_size128是原prefill扫描块，不是序列上限或state维度。真实prefill包含Pad/CumSum/Where/Einsum等；本稿的逐token语义不能冒充其实际分块图。
- MuP的z/x/B/C/dt五段系数、attention/ssm输入输出系数、MLP两个系数原样保存在JSON；不能合并成一处统一缩放。

## 5. MoE、融合和布局的有限约束

Granite40专家全部在声明域内，每token动态选8；每专家I512，融合gate_up输出1024，八专家返回[8,1536]，路由Softmax长度8，原logits长度40。selected logits需与ID/rank一致；不能把专家总数40或top8等同于每专家I。所读图没有shared expert分支，两处残差分支各乘0.22。全部专家三矩阵元素数为40×3×1536×512=94371840，若按S8估计即90MiB；这个字节数不是已接受的量化质量结论。

Phi的QKV融合输出5120=3072Q+1024K+1024V，gate_up融合输出16384；Slice、部分RoPE旁路和GQA3倍共享必须保留。Qwen3.5全局Wq_gate按每头512拆成Q256+Gate256，Gate的Sigmoid在PV之后乘上下文，不能移到QK打分前。Qwen2.5三路QKV bias和Falcon conv bias均是实际依赖。

## 6. 无外存条件的保守估计：不能缩水真实维度

小批规划候选为B1、query1、attended context256（含当前query，历史255），同时保留B1/S2源导出复现点；递推步数256仅作首批规划。**context256是缩小测试候选，不是“保守覆盖整个模型”的上限，也不是已有验证。** batch、长度最终运行域和硬件可支持范围在容量/程序评审后才冻结；source config位置上限全部保留。

以KV缓存采用共享KV头、S16元素为候选时，单层KV为2×B×T×KVheads×D×2 B。以下只是该公式和完整FFN mid的独立数据量，不含权重、状态、对齐、双版本、队列或所有活跃区之和：

| 层型 | KV宽度 | B1/T256完整KV字节 | 一个S16 FFN mid字节 |
|---|---:|---:|---:|
| qwen25_attention | 256 | 262144 | 22016 |
| qwen3_attention_qk_norm | 1024 | 1048576 | 6144 |
| llama_attention | 512 | 524288 | 16384 |
| gemma_local_attention | 1024 | 1048576 | 20480 |
| phi_fused_partial_rope | 1024 | 1048576 | 16384 |
| qwen35_global_gated_attention | 1024 | 1048576 | 18432 |
| granite_top8_moe | 512 | 524288 | 1024 |
| falcon_attention_ssm_hybrid | 256 | 262144 | 12288 |

这些KV值均超过单S16KiB。可以研究更细tile和额外片上存储，但不能把数据从容量账里消失；不假定外存或host无限供数。I11008的mid22016B、I10240的20480B、I9216的18432B都超S16KiB；I8192正好16384B仍未给权重/残差/队列留空间。

在B1、每元素4B（源FP32或候选S32；两者质量不同）时：

| 递推类型 | 单层一份state | 仅kernel−1最少history | 单份state+history | 采用old/next各一份时 |
|---|---:|---:|---:|---:|
| Qwen GDN | 2097152B=2MiB | 98304B | 2195456B | 4390912B |
| Falcon SSM | 4194304B=4MiB | 55296B | 4249600B | 8499200B |

history最少3个旧采样；实际cache接口可能存kernel4宽，本次use_cache=False没有验证真实cache对象布局，必须将3与4区分。old/next乘2是所选隔离版本方案的估计，不是所有算法实现的数学最低内存证明。跨整模型保留单份state就有Qwen24×2MiB=48MiB、Falcon32×4MiB=128MiB，另计history/KV/输出/元数据及权重。当前R的单active最多8KiB不是模型全部状态存储。

同时，多个原配置global context超过当前N单上下文65535元素：Llama/Gemma全局/Phi/Qwen3.5全局/Granite/Falcon都需要另有长度/算法/资源合同。不能把它们原来的131072/262144配置暗改为65535，或据此声称所有source长上下文已闭合。

## 7. 不确定项与交付限制

- FamilySpec只登记八个现有样本及其十层型；没有把任意同名模型变体放入允许域。未读/未确认的常量保留unknown，特别是GDN L2 epsilon、实际cache保存宽度和每边整数格式。
- 模型weight dtype配置多为BF16，实际本轮层验证FP32；现有七宏S8/S16/S32格式是后续候选数值合同，不能从“形状对上”推定整模型质量通过。
- 仓库的graph JSON/config/回执不包含数GB检查点权重；无外存完整运行仍需明确真实权重的片上部署/容量/装载与永久配置，不能用符号权重或脚本成功替代。
- embeddings、mask/RoPE频率生成、末尾Norm/LM head、采样在导出边界外；MTP及多模态未纳入。本稿不是整网模型导出，也没有证明执行L次代表层就等于已验证完整推理。
- family-spec.json提供完整层序、真实维度、Norm位点、原配置上限、B1/S2源验证边界及候选缩小工作负载；profile和覆盖规则由并行任务整合。最终“前三步规格交付”由主负责人核验完整包后报告，不把它写成全推理/RTL/物理验收。

实际检查：19源文件Git blob及SHA-256核验、10配置与原manifest SHA核验、8模型/10层型/完整层序与维度算术检查。未执行推理、RTL、SystemC、服务器或EDA；不读取/修改ref-project，不更新远端、正式包或他人文件。
