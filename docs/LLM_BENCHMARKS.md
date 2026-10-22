# 面向通用硬件底座的 INT8 LLM 功能模块 benchmark

2026-10-22｜[Issue #25](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/25)｜资料与配置调研，未执行模型或硬件实验。按用户修订：**以 INT8 计算为基础，按多模型功能覆盖选择模块；模型之间没有优先级，也不分配先开发、后验证的角色。**

承接 [Issue21 的算子/Block 研究][partition]和 [Issue23 的真实 Qwen3 轨迹][trace]。模型提供结构、真实尺寸和输入来源；共同算术能力、模型间不同的状态/通信方式都要进入底座合同。语义模块不自动等于一个独立硬件 Block。

## 功能覆盖与并列最小实验

下面各行为并列覆盖项，行序不代表接入顺序。纯文本推理统一建议 `B1、prefill S32、16 次单 token teacher-forced decode`；真实尺寸实例都保留。只实现其中一个片段，只能验收该片段。矩阵计算采用 **INT8 输入/权重、INT32 累加**；归约、非线性和持久状态的格式另列，不能由 W8A8 自动推定。

| 功能/模块 | 真实结构与最小片段 | 计算与状态边界 | 对 Block 间布局、映射、预连线的要求 |
|---|---|---|---|
| **线性投影、GEMM/GEMV** | 三模型的 Q/K/V/O、gate/up/down；如 Qwen dense Q `1024×2048`、Llama Q `2048×2048`、MoE router `2048×128` | Prefill `[BS,H]×W`、Decode `[B,H]×W`；W8A8→INT32→重定标；转置、尾块及归约长度保持真实尺寸 | 可复用矩阵资源、权重流式供数、部分和存储、矩阵↔bank 双向路径；不能为每个投影隐含新增阵列 |
| **门控 FFN / 专家 FFN** | 并列实例 `H/I=1024/3072`（Qwen dense）、`2048/8192`（Llama）、`2048/768`（MoE 单专家）；`gate/up→SiLU×up→down` | 三投影为 INT8 计算；SiLU、逐元乘和残差需明确尺度与宽中间结果；INT8 三矩阵 payload 分别 **9/48/4.5 MiB**（推导） | 输入分叉、门控汇合、向量→矩阵反馈；同时记录中间存活、down 累加与权重重读；一个专家 FFN 不等于完整 MoE |
| **GQA Attention 与 KV** | Qwen dense `(nQ,nKV,d)=(16,8,128)`、MoE `(32,4,128)`、Llama `(32,8,64)`；含投影、RoPE、mask、QK、softmax、PV、KV append | W8A8 投影；QK/PV 采用8位乘法须另定 Q/K/V/概率的符号、尺度和转换；KV 格式独立。prefill 分数 `[B,nQ,S,S]`；追加前 C 个词元时 decode 为 `[B,nQ,1,C+1]` | KV 就近共享、多消费者读取、可变长度/因果控制与在线 softmax 状态；prefill/decode 共用冻结库存，运行中不重做金属连接 |
| **归约、归一化、位置与逐元运算** | RMSNorm、Qwen Q/K head norm、SiLU、RoPE、softmax、残差；归约宽度取上述真实 H/d/C | 平方和、倒平方根、指数、倒数、旋转系数、门控乘法与残差对齐均需定点/LUT/宽中间态合同；精度、近似、舍入及溢出规则待冻结，不预设浮点计算路径 | 局部归约、统计回放、系数供给、转换及反馈；按 token 求量化尺度也增加归约、缓冲和控制，不能免费省略 |
| **MoE 动态选择、分发与聚合** | Qwen MoE `E128/k8/H2048/I768`，router `2048×128`；`router→softmax→top-k→所选权重重归一化→dispatch→expert FFN→weighted combine`；无共享专家 | router 线性计算可用 INT8；top-k 前对齐可比较尺度、固定并列规则；概率/加权归约格式另定。`ΣN_e=8BS`，需测集中与均匀负载 | 专家索引/队列/重排、背压、完成标记、权重驻留/换入及归约路径；运行时路由由预制控制实现，静态金属决定可达关系 |
| **MLA 与递归状态：独立结构覆盖轴** | [DeepSeek-V3 MLA 配置][dsconfig]的 latent512、RoPE64；[Qwen3.5-0.8B 纯文本配置][gdnconfig]的线性注意力与全注意力混合 | MLA 的 latent 缓存/展开、递归矩阵状态读改写与跨 token 依赖，不能等同 GQA KV；源配置不是 INT8 版本，需各自的状态精度/更新合同 | 需明确压缩投影、共享 latent、状态反馈和寻址；与上面各项无优先级关系。[现有账本][cases]不含完整 MLA/线性注意力，须登记覆盖缺口，不能据前三模型宣称通用覆盖完成 |

**真实尺寸与缩小调试对应**：FFN 按 Qwen dense/Llama/MoE 的 `H/I` 可分别缩为 `64/192、64/256、64/24`；GQA 按 Qwen dense/MoE/Llama 的 `(H,nQ,nKV,d)` 分别缩为 `(64,8,4,16)、(64,8,1,16)、(64,4,1,16)`，保留对应 Q/H 和 GQA 共享比。缩小核用 `B1/S8/T2、种子0`，真实缓存 `32→48` 对应缩小 `8→10`。MoE 控制调试可用 `H64/I24/E8/k2`，E/k 比例已改变，只验证索引/队列等控制。缩小核不能替代真实形状映射、量化模型或完整层验证。

## 同级模型例证、来源与容量

记 `L/H/I/nQ/nKV/d` 为层数、隐藏宽、FFN 中间宽、Q/KV 头数、头宽。实现审阅固定 Transformers **v4.57.6**：[Qwen dense][qcode]、[Qwen MoE][mcode]、[Llama][lcode]。三者共同提供 GQA、RoPE、RMSNorm、门控 FFN 等例证，MoE 提供额外动态专家结构；不意味着所有 LLM 都有这些模块。

- **Qwen/Qwen3-0.6B**，非 `-Base`，revision `c1899de289a04d12100db370d81485cdf75e47ca`：[配置][qconfig]、[模型卡][qcard]。`28/1024/3072/16/8/128`；Q `1024×2048`，K/V 各 `1024×1024`，O `2048×1024`。显式 `d=128`，不能用 `H/nQ=64` 代替。公开无门控，[Apache-2.0][qlicense]；embedding/head 共享。矩阵/embedding 按 INT8 存储的 payload **595,984,384 B ≈0.555 GiB**，另有 **65,536** 个归一化参数需独立计格式。B1/S128 的 INT8 X **128 KiB**，每路重定标后 gate/up **384 KiB**。
- **Qwen/Qwen3-30B-A3B**，非 `-Base`、非 `-Instruct-2507`，revision `ad44e777bcd18fa416d9da3bd8f70d33ebb85d39`：[配置][mconfig]、[模型卡][mcard]。`L48/H2048/nQ32/nKV4/d128`，每层128专家选8，专家 `I768`（不是 `intermediate_size6144`），Q `2048×4096`，K/V 各 `2048×512`，O `4096×2048`。公开无门控，[Apache-2.0][mlicense]；embedding/head 不共享。INT8 矩阵/embedding payload **30,531,911,680 B ≈28.435 GiB**，另 **210,944** 个归一化参数；单专家 **4.5 MiB**，每层专家池 **576 MiB**。B1/S128 的 INT8 X **256 KiB**，每专家重定标后 gate/up 为 `N_e×768 B`。官方约3.3B activated 不等于总权重容量。
- **meta-llama/Llama-3.2-1B**，base、非 Instruct，目标权重 revision `4e20de362430cd3b72f300e6b0f18e50e7166e08`：[元数据][lmeta]、[官方 SKU][lsku]、[模型卡][lcard]。`16/2048/8192/32/8/64`，Q/O `2048×2048`，K/V 各 `2048×512`；`I=256·ceil(int(1.5·int(2·4H/3))/256)=8192` 由 SKU 与[官方 FFN 实现][lffn]推导。共享 embedding；INT8 矩阵/embedding payload **1,235,746,816 B ≈1.151 GiB**，另 **67,584** 个归一化参数。B1/S128 的 INT8 X **256 KiB**，每路重定标后 gate/up **1 MiB**。需获 Meta 授权并遵守[自定义许可][llicense]；本次未获 HF config 访问，尺寸依据公开 SKU，获权后仍需核配置/分词器/权重。

**以上容量全部为推导值**，不是已获得的 INT8 checkpoint 或实测内存。令 `Q=nQ·d,K=nKV·d,V=词表大小`，每层注意力矩阵数 `A=2H(Q+K)`、FFN `F=3HI`。共享 embedding 的 dense 模型 `P8=VH+L(A+F)`；MoE 为 `P8=2VH+L(A+128F+128H)`；V 分别151936/151936/128256。归一化参数 `Pn=L(2H+δ)+H`，Qwen的δ为2d、Llama为0。完整存储为 `P8 B + Pn·b_norm + scales/zero-points/乘数移位 + 对齐/副本/workspace`；主权重8位不代表归一化参数也8位，源模型需另行量化/校准。

KV payload 为 `2LB·C·nKV·d·b_KV`：三模型全层每 token 分别 **56/48/16 KiB × b_KV**，B1/C128 为 **7/6/2 MiB × b_KV**，`b_KV` 是每元素字节数（格式待定）；若选 INT8 KV，取1并额外计尺度/转换，不能由 W8A8 直接断言。INT8 激活 `X=BSH B`、每路门控输入 `BSI B`；尚未重定标的 INT32 张量为4倍。B1/S128 显式 INT32 QK 分数分别 **1/2/2 MiB**；在线 softmax 的统计、宽输出累加和回放仍须计入。若 MoE 分发与专家回传均用 INT8，dispatch/combine **各** `BS·8·2048 B`，B1 单 token 各 **16 KiB/层**；这是逻辑 payload，实际跨块/外存流量还取决于驻留、复制、包头和布局。

## INT8 整数合同与输入/评价口径

**初始整数合同建议（尚未实现或验收）**：

- 无 bias 线性片段取有符号 INT8、对称零点0，激活尺度按 token/行、权重按输出通道/列；冻结 scale、轴、布局、输出尺度与整数乘数/移位。动态求尺度所需 max 归约和缓存单独记成本，静态校准为另一可比较方案。
- `acc[m,n]=ΣqA[m,k]·qW[k,n]` 目标 INT32；整数参考用 INT64 求和、断言 INT32 范围，溢出即失败。归约分块须保持同一完整累加语义，不能每个 K tile 随意重定标。最坏8位乘积界为16384，`K8192` 时无 bias 的绝对和界为 **134,217,728**（推导）；加 bias/残差或更长归约需重核。
- 冻结 `qY=clip[-128,127](RNE(INT64(acc)·M/2^r))`，RNE 为 ties-to-even；M/r 对应输入、权重、输出尺度比，随 token/输出通道变化或按冻结规则分解生成；不能假定全张量共用一个乘数。冻结中间乘法范围，验证负数半值、饱和、全零和 K 分块一致。先检查整数逐位一致、累加范围与元数据传递，不能用浮点误差门槛替代整数合同；模型量化质量、校准集和接受阈值另定。
- RMSNorm、SiLU、RoPE、softmax、残差、路由概率/聚合、KV/递归状态逐项声明输入/输出/内部位宽、scale、近似、舍入与饱和；同一底座可分时复用这些能力，但不能把尚未定义的转换当成免费能力。Attention 归约轴的尺度（尤其 PV 中按 token 量化的 V）及 top-k 的跨专家比较尺度须对齐或显式转换。

依据：[ONNX v1.17.0][onnx] 的 MatMulInteger-10、QLinearMatMul-21、QuantizeLinear 规定整数/量化算子语义；上述粒度与整数合同是本项目建议，不能据此宣称 ONNX 图已可直接映射。[Jacob 等 v1][integer]提供宽累加和定点重定标依据，其附录右移舍入规则不同，不宣称位精确兼容。[SmoothQuant v6][smoothquant]支持 W8A8 的方法依据，论文对非线性采用混合精度；不能推断本项目这些模型已量化，也不把浮点 fake-quant 当整数硬件参考。

**Benchmark 实例**应同时绑定“功能子图 + 来源模型/版本/层或专家 + 输入 + 整数量化合同 + 执行场景 + 指标”；模型、数据集、场景、指标分别记录：

- **输入**：[Issue23 固定 token][traceinputs]仅可复用到对应 Qwen3-0.6B；既有浮点轨迹只提供输入/shape/生命周期线索，不作 INT8 数值参考，也没有可直接重放的原始激活。其他模型用各自固定分词器编码。量化模块用例需另冻结整数张量、尺度和参考摘要/SHA；无权重时用合成整数，只称结构/算子验证。
- **自然文本候选集（未提取）**：[Salesforce/wikitext][data]，revision `b08601e04326c79dfdd32d625aee71d232d685c3`，`wikitext-2-raw-v1/test`。按原行序去掉空白 text，其余原文用 `\n\n` 拼接；各模型固定 tokenizer、`add_special_tokens=False`、无 chat 模板，取前32个不重叠 `S+T` 窗口。冻结行范围/拼接文本 SHA、tokenizer revision、token IDs/偏移/SHA。若用于校准，须与质量评测窗口分离、冻结校准统计；这32个窗口仅是模块输入候选，不能冒充完整语言质量评测。数据卡的许可元数据 CC-BY-SA-3.0/GFDL 与正文4.0不一致，待核；本PR不复制语料。
- **场景**：所有模型/模块并列覆盖 B1/S32/T16；尺寸敏感性统一包含 B1/S128/T16、B∈{1,4}/S2048/T128，属于相同覆盖合同中的不同规模，不区分模型先后。无填充、不跨窗口保留状态、teacher-forced 单 token 追加、不采样/提前 EOS；模型专有位置编码与状态更新语义保持不变。不能将某配置未能映射的情况静默删除。
- **指标**：整数逐位一致/溢出/饱和，量化尺度与索引一致性；权重/激活/状态逻辑字节、bank 同时存活峰值、服务窗口/端口竞争、跨块流量、映射与布线合法性/失败、固定/定制资源占用。MoE 加每专家 `N_e`、热点、队列、换入和聚合成本；合成均匀/集中路由不能冒称真实模型热点。真实量化后的质量/误差、周期/PPA仍须另测。本次无 TTFT/TPOT/tokens/s；端到端才参考 [MLCommons v5.1 LoadGen][mlperf] 固定请求/输出口径，模块结果不是 MLPerf 合规成绩。

## Block 输入合同与转换缺口

Block 同学需提供：**INT8 MAC/INT32 累加及重定标**的精确能力、scale/乘数/移位格式与存储；向量/归约/近似函数、比较/索引/路由、状态读改写与转换能力；tile/转置/尾块、周期/流水、逐 bank 容量/读写端口、FIFO/背压、外存接口和“每多少周期服务多少字节”的带宽合同。精度未定义的模块列为能力缺口，不能先从模型名字指定物理 Block。

布局/预连线共同输入包括：匹配同版网表的 LEF/Liberty、尺寸/朝向、逐 bit pin/可接入形状、OBS、PG/时钟、驱动/负载及时序预算；块内固定连接、矩阵↔bank↔向量反馈、KV共享、专家分发/归约、MLA/递归状态路径及裕量候选。冻结计算/存储/控制库存、位置和有源缓冲，明确允许定制的金属/通孔及连接点/轨道预算；运行时选择器与队列须预先存在并计成本。

**待团队冻结**：量化/校准与非线性、KV/状态精度合同、模块覆盖边界、同资源布局/映射对照与输入保留集、外存/片内容量和端口/带宽、吞吐/延迟目标及定制层；Llama访问、WikiText许可标注和审查人。所有模型例证参与同一功能覆盖目标，不因大小、新旧或可下载性排出先后。

**当前缺口**：openTPU small/llaccel_core 是流程案例，[物理案例证据][physical]不等于固定底座已支持 LLM。还需逐模块完成：模型/子图与状态语义 → 整数量化/近似合同和参考 → 合法 tile/生命周期 → 计算与 bank 映射 → 协议/周期/队列/带宽模型 → RTL/整数等价 → 匹配物理视图/合法端点 → 固定布局/预连线与限定层定制。既有浮点轨迹、抽象图和 H1 物理案例不能替代这些环节；单模块结果不能外推完整层、模型或全部 LLM。

[partition]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/adf077d04a5f0a3cc2ae13b77f16371bb637591d/docs/OPERATOR_BLOCK_PARTITION.md
[trace]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7e0e82b7175525b3e113c791b7f1fc499b249443/docs/experiments/issue-23-qwen3-real-trace.md
[qconfig]: https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/config.json
[qcard]: https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/README.md
[qlicense]: https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/LICENSE
[mconfig]: https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39/config.json
[mcard]: https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39/README.md
[mlicense]: https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/ad44e777bcd18fa416d9da3bd8f70d33ebb85d39/LICENSE
[qcode]: https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3/modeling_qwen3.py
[mcode]: https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py
[lcode]: https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/llama/modeling_llama.py
[lmeta]: https://huggingface.co/api/models/meta-llama/Llama-3.2-1B/revision/4e20de362430cd3b72f300e6b0f18e50e7166e08
[lsku]: https://github.com/meta-llama/llama-models/blob/0e0b8c519242d5833d8c11bffc1232b77ad7f301/models/sku_list.py#L608
[lffn]: https://github.com/meta-llama/llama-models/blob/0e0b8c519242d5833d8c11bffc1232b77ad7f301/models/llama3/model.py
[lcard]: https://github.com/meta-llama/llama-models/blob/2dee240a2c2e8d3b6ecff3305759fcde4a9cde45/models/llama3_2/MODEL_CARD.md
[llicense]: https://github.com/meta-llama/llama-models/blob/2dee240a2c2e8d3b6ecff3305759fcde4a9cde45/models/llama3_2/LICENSE
[data]: https://huggingface.co/datasets/Salesforce/wikitext/blob/b08601e04326c79dfdd32d625aee71d232d685c3/README.md
[traceinputs]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7e0e82b7175525b3e113c791b7f1fc499b249443/project/experiments/qwen3_trace/results/issue-23-run01/evidence.zip
[cases]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/adf077d04a5f0a3cc2ae13b77f16371bb637591d/project/experiments/operator_partition/model-cases.json
[physical]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ec749b17784e49e2123bff033264c2ed7ae9dd5c/docs/experiments/issue-15-opentpu-comparison.md
[mlperf]: https://github.com/mlcommons/inference/blob/75f297d44c5e68d24a2f7643fe1eb11e49313238/loadgen/logging.cc#L441
[dsconfig]: https://huggingface.co/deepseek-ai/DeepSeek-V3/blob/e815299b0bcbac849fa540c768ef21845365c9eb/config.json
[gdnconfig]: https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/2fc06364715b967f1860aea9cf38778875588b17/config.json
[onnx]: https://github.com/onnx/onnx/blob/v1.17.0/docs/Operators.md
[integer]: https://arxiv.org/html/1712.05877v1
[smoothquant]: https://arxiv.org/html/2211.10438v6
