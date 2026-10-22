# 面向固定硬件底座的 LLM benchmark 候选

2026-10-22｜[Issue #25](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/25)｜选型与输入合同建议；本次未运行模型或物理实验。

承接 [Issue #21 / PR #22 的结构与划分研究](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/adf077d04a5f0a3cc2ae13b77f16371bb637591d/docs/OPERATOR_BLOCK_PARTITION.md)及 [Issue #23 / PR #24 的真实 Qwen3 轨迹](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7e0e82b7175525b3e113c791b7f1fc499b249443/docs/experiments/issue-23-qwen3-real-trace.md)，二者尚待审查。此处给出块间布局、映射和预连线的接入顺序，正式对照集合仍需团队冻结。

## 候选对照

记 `L/H/I/nQ/nKV/d` 为层数、隐藏宽度、FFN 中间宽度、Q/KV 头数、头宽。三者均为纯文本因果推理、全注意力 GQA、RoPE、RMSNorm、SiLU 门控 FFN；Qwen3 另有 Q/K 头归一化。统一实现审阅版本为 Transformers **v4.57.6**：[dense Qwen3][qcode]、[MoE Qwen3][mcode]、[Llama][lcode]。以下容量均为 **BF16、推导值**，激活示例统一按 **B1/S128、单层**；不是峰值内存或实测流量，MiB/GiB 为二进制单位。

| 候选与固定来源 | 结构、代表性矩阵（逻辑输入×输出） | 权重、激活、KV | 用途、硬件启示与获取难点 |
|---|---|---|---|
| **Qwen/Qwen3-0.6B**，非 `-Base`；revision `c1899de289a04d12100db370d81485cdf75e47ca`；[配置][qconfig]、[模型卡][qcard] | `28/1024/3072/16/8/128`；Q `1024×2048`，K/V 各 `1024×1024`，O `2048×1024`；gate/up 各 `1024×3072`，down `3072×1024`；GQA 共享比 2 | 去重参数 **596,049,920**，权重下界 **1.110 GiB**；B1、S128：X **256 KiB**，gate/up 各 **768 KiB**；全模型 KV **112 KiB/token**，128 tokens 为 **14 MiB** | **首选开发**：已有固定权重轨迹，能检验矩阵→向量→矩阵反馈及 KV 共享。公开无门控，[Apache-2.0][qlicense]。`d=128`，不能按 `H/nQ=64` 推断；embedding/head 共享使逻辑参数容量与文件大小不同。 |
| **Qwen/Qwen3-30B-A3B**，非 `-Base`、非 `-Instruct-2507`；revision `ad44e777bcd18fa416d9da3bd8f70d33ebb85d39`；[配置][mconfig]、[模型卡][mcard] | `L48,H2048,nQ32,nKV4,d128`；Q `2048×4096`，K/V 各 `2048×512`，O `4096×2048`；每层 **128 专家选 8**，每专家 `I=768`、三矩阵；router `2048×128`；无共享专家 | 总参数 **30,532,122,624**，权重 **56.871 GiB**；官方约 **3.3B activated** 不代表总权重只需 3.3B；单专家权重 **9 MiB**，每层专家池 **1.125 GiB**；X **512 KiB**，每个专家的 gate/up 为 `N_e×768`；全模型 KV **96 KiB/token**，128 tokens 为 **12 MiB** | **第二个开发子图**：同族 GQA 下单独增加动态专家分发/聚合，避免同时引入 MLA。公开无门控，[Apache-2.0][mlicense]；先做真实尺寸 MoE 层/专家图，完整权重运行须另评资源。top-k、归一化权重、热点、重排、背压与专家换入不能省略；配置 `intermediate_size=6144` 不是专家宽。 |
| **meta-llama/Llama-3.2-1B**，base、非 Instruct；目标权重 revision `4e20de362430cd3b72f300e6b0f18e50e7166e08`；[元数据][lmeta]、[官方 SKU][lsku]、[模型卡][lcard] | `16/2048/8192/32/8/64`；Q/O `2048×2048`，K/V 各 `2048×512`；gate/up `2048×8192`，down `8192×2048`；GQA 共享比 4；I 为官方公式推导 | 共享 embedding；参数 **1,235,814,400**，权重下界 **2.302 GiB**；X **512 KiB**，gate/up 各 **2 MiB**；全模型 KV **32 KiB/token**，128 tokens 为 **4 MiB** | **方法固定后跨实现验证**：不同头宽、FFN 比例与共享比，检查布局/映射是否过拟合 Qwen。需获 Meta 授权并遵守 [Llama 3.2 Community License / AUP][llicense]；本次 HF config 未获访问，尺寸取公开 SKU，权重/配置/分词器须获权后再核。 |

**计算依据（推导值）**：令 `Q=nQ·d, K=nKV·d, V=词表大小`。无 bias 时每层注意力权重 `2H(Q+K)`；dense FFN 为 `3HI`；两处层 RMSNorm 为 `2H`，Qwen 另加 `2d`。Qwen0.6B/Llama 的去重参数 `P=VH+L[2H(Q+K)+3HI+2H+(Qwen:2d)]+H`，V 分别为 151936/128256。MoE 将 `3HI` 替换为 `128·3H·768+H·128`，embedding/head 不共享，首项为 `2VH`。BF16 权重为 `2P` 字节，不含运行时副本、量化元数据或 workspace。Qwen0.6B checkpoint 含分开保存的 embedding/head，[官方文件][qweights]实际为 **1,503,300,328 B**（含头部）；不能用逻辑去重容量当下载大小。

Llama 的 `I=256·ceil(int(1.5·int(2·4H/3))/256)=8192`，来自 [SKU][lsku] 的乘数/对齐参数及[官方 FFN 实现][lffn]。激活 `X=BSH·2`，每个 gate/up 为 `BSI·2`；MoE 中 `ΣN_e=8BS`，不能令每专家都处理全部 tokens。KV **不复制 GQA 共享头**：`2·L·B·C·nKV·d·2 B`，C 为已缓存总词元数；Decode 每追加一个词元按此线性增长。上表未计残差、FP32 累加、FIFO、双缓冲和临时区，不能将各张量简单相加当实际峰值。

## Benchmark 定义与运行条件

每个候选均定义为“表中模型快照 + 下述输入集合 + 运行场景/精度 + 指标”，不能仅以模型名或数据集名充当 benchmark。

- **首个固定输入（仅 Qwen3-0.6B）**：复用 [Issue23 experiment.json][traceconfig] 与[归档内 inputs.json 的 token IDs][traceinputs]，B1、prefill 32 + 16 次单 token teacher-forced decode；96+8 作为已有确认集。输入是项目正确性用例，**不是语言质量评测数据集**。其他候选须从原始文本以各自分词器重新编码，不能跨模型照搬 token IDs。
- **自然文本候选集（尚未提取/执行）**：[Salesforce/wikitext][data]，revision `b08601e04326c79dfdd32d625aee71d232d685c3`，`wikitext-2-raw-v1/test`。按原行序过滤空串，以 `\n\n` 连接非空 text；各模型用同 revision 分词器、`add_special_tokens=False`、无 chat 模板，再顺序取前 32 个不重叠的 `S+T` token 窗口。冻结源文件 SHA、行序/拼接规则、分词器版本、token IDs 与 SHA；各模型窗口对应的文本范围可能不同。数据卡元数据为 CC-BY-SA-3.0/GFDL、正文却写 CC-BY-SA-4.0，标注不一致待团队核实；本 PR 不复制语料。
- **规模/精度建议**：首个 FFN 复用 B1/S32/T16；随后规模点 B1/S128/T16，资源模型稳定后扩 B∈{1,4}、S2048、T128；均不填充、不跨窗口保留 KV、无采样/提前 EOS。先沿用 CPU FP32/eager 数值参考；目标数据流按 BF16 权重/激活/KV、FP32 累加和归约记账，BF16 舍入/误差门槛须另定并验证。INT8/INT4 留到定点及缩放合同确定后。Qwen 本轮不用聊天/思考模式；未来生成场景需另固定模板、`enable_thinking` 和停止条件。
- **Prefill / Decode**：prefill 投影为 `[BS,H]×W`、注意力分数 `[B,nQ,S,S]`；有权重跨 token 复用和二次方分数空间，允许相同合法 chunk/tile 基线。Decode 为 `[B,H]×W`，读既有 KV 并追加；令追加前长度 C，则本步分数 `[B,nQ,1,C+1]`。不能让两个阶段重新定制金属。若显式物化，B1/S128 的 BF16 分数为 Qwen0.6B **512 KiB**、另外两者各 **1 MiB**；在线 softmax 可避免整张物化，其状态/回放/数值成本仍须记账。
- **评价指标**：首轮报告与固定 FP32 参考的数值误差、缓存长度/字节、跨 Block 逻辑传输、bank 同时存活峰值、端口竞争/服务窗口、合法映射与路由失败、固定/定制资源占用。MoE 另报每专家 `N_e`、最大/平均负载、队列峰值和权重换入；预制有源路由控制承担运行时 top-k，金属只决定可达连接。当前没有 TTFT、TPOT、tokens/s 或 PPA 实测。以后端到端时固定请求边界，测提交到首 token 的 TTFT、`TPOT=(末token时间−首token时间)/(输出数−1)` 和吞吐；语言质量另报完整规定集的 NLL/PPL 或任务指标，32 窗口不能冒充完整质量评测。[MLCommons v5.1 LoadGen][mlperf]仅作指标口径参照，本候选集不等同 MLPerf 合规测试。

## 推荐与首个最小实验

**先接 Qwen3-0.6B 的 layer 0 SwiGLU FFN**：`X[1,32,1024] → gate/up[1,32,3072] → SiLU×up → down[1,32,1024]`；Decode 对应 `[1,1,1024]`。它直接检验同一矩阵资源经局部存储/向量单元再返回矩阵资源的路径，且已有真实模型输入与轨迹依据。验收范围限该 FFN，不能外推 Attention、KV、完整层或完整模型。

1. 复用 Issue23 固定模型/输入及 Transformers4.57.6、torch2.10.0+cpu 的 FP32/eager 参考口径；**现有归档只有 token、边界元数据和比较摘要，没有可直接重放的原始激活**。后续由该实验负责人或获授权执行者重放，补导出 layer0 MLP 实参（post_attention_layernorm 输出）、参考输出和三矩阵索引并绑定 SHA；权重/原始激活留授权存储。本次不重放。
2. 先冻结同一矩阵/向量资源、总 SRAM、bank/端口、带宽、FIFO 与反馈能力；比较合法的物化/流式调度，再比较布局/预连线。真实 FFN 三矩阵 BF16 共 `3·1024·3072·2` = **18 MiB**，不能默认全放片内。B1/S32 的 gate/up 各 **192 KiB**（FP32 参考各 384 KiB）；需同时计输入、down 累加、双缓冲及权重重读。记录无法映射或溢出，不能暗加存储。
3. 缩小调试可用 `H64/I192/B1/S8/T2`、固定种子0的合成数值，保持 `I/H=3` 和相同三投影/门控依赖；标记为缩小核。真实映射仍用 `H1024/I3072`，只调整已声明 tile，例如 `token_tile=8/intermediate_tile=256`；这是调度分块，不能替换真实矩阵尺寸。缩小核通过不能证明真实权重/尺寸通过。
4. FFN 合同稳定后，再接同层 GQA（含 Q/K 归一化、RoPE、causal mask、softmax、KV append）及 MoE 分发/聚合子图。Qwen 两候选用于开发；Llama 在方法冻结后作跨实现验证。三者已有配置探索，均不能宣称盲测；需要盲测时另预注册未参与调参的输入场景。[既有 DeepSeek-V3 MLA/共享专家候选][cases]保留到后续结构泛化，当前用同族 Qwen MoE 分离专家通信变量；Qwen3.5 递归状态暂不加入首轮。

## Block、布局与预连线的输入合同

- **计算与局部反馈**：Block 同学提供 MAC/向量/归约/SiLU/softmax/top-k 能力、精度/舍入/累加格式、tile/转置与尾块约束、流水/启动间隔、状态可重入性。给出矩阵↔bank↔向量反馈、FFN 分叉汇合及残差路径的已有连接；布局方只对可用能力映射。
- **存储与通信**：逐 bank 容量、读写端口、同时服务限制、KV/权重/激活归属、FIFO 深度与背压、权重外存接口。GQA 优先评估 KV 就近共享/多消费者读取；decode 的线性 KV 扫描和权重供数须与 prefill 共用库存。MoE BF16 跨专家逻辑 dispatch/combine **各** `BS·8·2048·2 B`，B1 单 token 各 **32 KiB/层**；单专家权重 9 MiB，需比较移动激活与换入权重。上述是语义字节，实际跨块/外存流量取决于驻留与路由，不能直接换算引脚数。接口带宽必须给“每多少周期送多少字节”的服务窗口、时钟/仲裁/突发开销，不能仅给总字节。
- **物理与冻结资产**：提供与同一网表版本匹配的 LEF/Liberty、尺寸/朝向、逐 bit pin 及可接入形状、OBS、PG/时钟、驱动/负载和时序预算、块内预连线及备用端点。共同冻结计算/存储/控制库存、位置与有源缓冲；声明允许改动的金属/通孔、连接点/线宽/轨道预算。布局与预连线至少覆盖 FFN 反馈、GQA 共享和 MoE 分发/归约；运行时选择器、控制/队列均须预先存在并计成本。

**仍待团队决定**：Block 候选及接口合同、外存/片内容量与带宽、吞吐/延迟目标、BF16 数值门槛、映射并发/分时策略、定制层集合、正式开发/泛化场景；Llama 获取授权与配置核验、WikiText 许可标注核实、审查负责人。不能先用任意带宽或 SRAM 余量反推“已满足”。

**当前流程缺口**：openTPU small/llaccel_core 用于工程案例；[Issue15 物理对照][physical]仍有资格/收敛限制，H1 允许的新增缓冲不能充作 H2 冻结资产。真实 LLM 到最终布线尚需：固定模型与 token → 含持久状态/路由语义的算子图 → tile/生命周期/数据精度 → 计算与 bank 映射 → 周期、协议、带宽/队列模型 → 数值/RTL 等价 → 匹配物理视图与合法端点 → 固定布局/预连线和受限定制验证。现有 CPU 轨迹、抽象资源图和局部物理案例分别提供输入证据，尚不构成完整 LLM 硬件支持。

[qconfig]: https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/config.json
[qcard]: https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/README.md
[qlicense]: https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/LICENSE
[qweights]: https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/model.safetensors
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
[traceconfig]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7e0e82b7175525b3e113c791b7f1fc499b249443/project/experiments/qwen3_trace/experiment.json
[traceinputs]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/7e0e82b7175525b3e113c791b7f1fc499b249443/project/experiments/qwen3_trace/results/issue-23-run01/evidence.zip
[cases]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/adf077d04a5f0a3cc2ae13b77f16371bb637591d/project/experiments/operator_partition/model-cases.json
[physical]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ec749b17784e49e2123bff033264c2ed7ae9dd5c/docs/experiments/issue-15-opentpu-comparison.md
[mlperf]: https://github.com/mlcommons/inference/blob/75f297d44c5e68d24a2f7643fe1eb11e49313238/loadgen/logging.cc#L441
