# DeepSeek 推理算子与 Block 划分证据

本记录服务于 Issue 21 的首轮推理研究，覆盖 prefill 与 decode；训练仅作为结构和数值格式约束。核实日期：2026-10-22。只读取官方论文、官方配置和官方源码。没有下载模型权重，没有执行训练，也没有测量硬件 PPA。辅助工作目录为 `D:/Projects/Codex/operator-partition-20261022/deepseek`，未修改仓库或在线资源。

## 1. 首轮应采用的模型边界

建议以可明确追溯的 V2/V3/R1 原始模型作为 MLA/MoE 主案例，以 R1-Distill-Qwen-7B 作为“同一训练标签、不同计算架构”的对照。V3.2、V4 与 V4.1 已有官方资料，不能将 V3 称为截至本次核实的最新架构；较新模型作为可迁移性检查，首轮无需实现所有新机制。

| 官方配置 | hidden / layers | attention 关键配置 | MoE 关键配置 |
|---|---:|---|---|
| DeepSeek-V2 | 5120 / 60 | 128 heads; query rank 1536; KV rank 512; non-RoPE 128 / RoPE 64 / value 128 | 160 routed + 2 shared; top-6; expert intermediate 1536; 第一层 dense |
| DeepSeek-V3 | 7168 / 61 | 128 heads; query rank 1536; KV rank 512; non-RoPE 128 / RoPE 64 / value 128 | 256 routed + 1 shared; top-8; expert intermediate 2048; 前三层 dense |
| DeepSeek-R1 | 7168 / 61 | 本次固定配置的架构字段与 V3 相同 | 本次固定配置的架构字段与 V3 相同 |
| R1-Distill-Qwen-7B | 3584 / 28 | Qwen2 架构；28 query heads / 4 KV heads，属于 GQA | dense intermediate 18944，没有 MLA/MoE 配置 |
| DeepSeek-V3.2 | 7168 / 61 | MLA 相关维度保持；新增 index_n_heads=64 / index_head_dim=128 / index_topk=2048 | 256 routed + 1 shared; top-8 |
| DeepSeek-V4-Flash | 4096 / 43 | 64 heads; head_dim=512; query rank 1024; sliding_window=128; 分层压缩配置 | 256 routed + 1 shared; top-6; expert intermediate 2048 |
| DeepSeek-V4.1-Flash | 5120 / 40 | text_config 中 64 heads; head_dim=512; query rank 1280; 跨层 KV / index 来源列表 | 384 routed + 1 shared; top-6; expert intermediate 2304 |

表中字段来自固定 revision 的 config.json，而非根据模型名称估算。精确 revision、URL、SHA-256 见 `hf-config-manifest.json`；展开的字段见 `config-comparison.json`。V3 与 R1 两份 JSON 本次实际逐字段比较，只有 `transformers_version` 不同。这不表示权重相同，也不能外推到后续 R1-0528 等不同发布。

R1 的贡献位于后训练：V3-Base 经冷启动监督训练、强化学习及后续多阶段训练得到 R1；R1-Zero 的起点流程不同。Distill-Qwen 和 Distill-Llama 是基于各自 dense 模型训练的学生，不能继承教师的 MLA/MoE 算子图。出处：[R1 报告 v1，2025-01-22](https://arxiv.org/html/2501.12948v1)。

新版本的迁移约束：V3.2 官方卡确认 DSA；V4 官方卡确认 CSA/HCA 混合注意力与 mHC，expert 使用 FP4，其他多数参数 FP8；V4.1 官方卡确认 20 层 causal encoder + 20 层 decoder、跨层共享 KV/index 和复用 Top-K，另含 token lookup 条件记忆。因此接口不能预设“每个 attention 层必定拥有一套私有 KV”，也不能把所有模型表示成只有 GEMM 的链。上述为资料事实；将其作为 Block 兼容性约束是本研究的推论。出处：[V3.2 官方卡](https://huggingface.co/deepseek-ai/DeepSeek-V3.2)、[V4 官方卡](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash)、[V4.1 官方卡](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash)。

本次未阅读 V4.1 完整技术报告；较新版本仅核实模型卡与固定配置，不声称复现其全图。V4.1 官方新闻发布日期为 2026-09-10；当前页面和配置可能随发布更新，故本记录保留观测日期和配置 revision，不把“当前 main”当成不可变版本。出处：[官方新闻](https://deepseek.com/en/news/deepseek-v4-1-flash/)。

## 2. MLA 的精确数据流与合法融合

代码依据是 DeepSeek-V3 官方仓库 commit `9b4e9788e4a3a731f7567338ed15d3ec549ce03b`：

- [model.py 的 MLA，396–497 行](https://github.com/deepseek-ai/DeepSeek-V3/blob/9b4e9788e4a3a731f7567338ed15d3ec549ce03b/inference/model.py#L396)。
- [671B 配置](https://github.com/deepseek-ai/DeepSeek-V3/blob/9b4e9788e4a3a731f7567338ed15d3ec549ce03b/inference/configs/config_671B.json)。
- 原始论文：[V2 报告 v5 的 MLA，2024-06-19](https://arxiv.org/html/2405.04434v5)。

采用行向量约定，先忽略 batch 轴。X 为 T×d，H 为 head 数；r_c 为 KV rank，d_n/d_r/d_v 分别为 non-RoPE / RoPE / value 维度。U_K,h 为 d_n×r_c，U_V,h 为 d_v×r_c。

1. 低秩 Query：`Q = RMSNorm(X W_DQ^T) W_UQ^T`，reshape 为 `[T,H,d_n+d_r]`，拆成 Q_C 和带位置旋转的 Q_R。
2. KV 输入投影拆为 `[C_raw, K_R_raw] = X W_DKV+KR^T`；`C = RMSNorm(C_raw)`，`K_R = RoPE(K_R_raw)`。K_R 在 heads 间共享。
3. 展开形式：`K_C,h = C U_K,h^T`，`V_h = C U_V,h^T`。
4. 因果 attention：`S_h = (Q_C,h K_C,h^T + Q_R,h K_R^T) * scale`，`P_h = causal_softmax(S_h)`，`O_h = P_h V_h`，最后拼接各头并乘输出投影。

其中基础 scale 为 `(d_n+d_r)^(-1/2)`；官方代码对长上下文另做 YaRN 相关缩放，本次小实验仅用基础 scale 和普通旋转，未覆盖完整 YaRN。

对于相同权重与实数算术，矩阵结合律允许：

`Q_C,h K_C,h^T = (Q_C,h U_K,h) C^T`

`O_h = (P_h C) U_V,h^T`

因此官方 `absorb` 分支直接存 C 与 K_R；`naive` 分支显式存每头 K/V。这两种路径可作为同一逻辑接口的两种实现。这里是把线性乘法重新结合，并非穿越非线性取消计算。RMSNorm、softmax、位置旋转、量化舍入均必须保留对应语义；低精度下运算重排可能改变舍入误差，float64 的相等不能推出 FP8 bit-exact。

缓存的解析计数（不包括 allocator、page table、scale、对齐、跨设备重复）：

- compressed：`B*T*(r_c+d_r)` 元素；V3 为每 token / layer 576 元素。
- 官方 naive 分支：`B*T*H*(d_n+d_r+d_v)` 元素；V3 为每 token / layer 40960 元素。
- 假设 BF16、61 层、B=1，compressed 每 token 为 70272 字节；T=8192 时为 575668224 字节，即 549 MiB。

71.11 倍只是上述两个具体数组布局的元素比，不是论文相对 DeepSeek-V1 的整体缓存压缩指标，也不是任何端到端性能倍率。

Prefill 中 query 数通常较大，可以用 GEMM 重用权重；causal attention 的有效配对数随长度二次增长。Decode 中每序列通常只有一个新 query，却需访问历史缓存，算子的矩阵形状和瓶颈发生变化。连续批处理、KV 分页、稀疏选择、量化与 tensor parallel 会改变实际工作集，应列为显式参数，不写成单一固定吞吐。

一个有价值的内部预连线候选是 `QK → online softmax → PV`：在分块局部保持 running max、normalizer 与输出累加器，不把完整 S/P 矩阵送出 Block。对全矩阵物化的基线，仅 S 与 P 两条跨 Block 边各占 `B*H*T_query*T_key*b` 字节；这两个边的消除不等于 KV、Q 或权重传输消失。共享 compressed C 的读取能否在 heads 间重用仍取决于 local SRAM / multicast / scheduling。

## 3. MoE 路由、专家与通信边界

V3 的一个专家是 `f_e(x) = W_down,e (SiLU(W_gate,e x) ⊙ W_up,e x)`。shared expert 对每个 token 计算；routed experts 由动态门控选取。矩阵方向可按实现存储约定转置，三次线性运算的依赖不变。

官方 [Gate/Expert/MoE，535–693 行](https://github.com/deepseek-ai/DeepSeek-V3/blob/9b4e9788e4a3a731f7567338ed15d3ec549ce03b/inference/model.py#L535) 的 V3 路由：

1. `s_e = sigmoid(x^T w_e)`；保留原始 s。
2. 选择用的分数是 `s_e + bias_e`。
3. 将 256 个专家分为 8 组；每组用该组最高两个选择分数之和排序，保留 4 组；再在可选专家中取 top-8。
4. 最终组合权重为 `g_e = 2.5*s_e / sum_selected(s)`，不是用带 bias 的分数重新归一化。
5. `y = shared(x) + sum_selected(g_e*f_e(x))`；shared 不参与这组 top-k 权重归一化。

V2 的配置使用 softmax、8 组取 3 组、top-6、route scale 16，且不对选中概率重归一化。不可把 V3 的 sigmoid 规则套给所有 DeepSeek。训练产生的负载平衡偏置也不意味着每个推理 batch 的专家 occupancy 严格平均。

专家内部较适合形成参数化复合 Block：两个输入投影可共享 X，SiLU/乘法为局部消费者，down projection 消费局部中间结果。若将 gate-GEMM、SiLU、up-GEMM、乘法、down-GEMM 全部分开，四条中间边各有 `T_e*m` 个元素，总计 `4*T_e*m*b` 单向 payload；融合可消除这些跨 Block 边，但必须容纳 tile 中间结果与累加器。这是明确基线下的解析计数，不是 DRAM 实测。若基线已有 epilogue 融合，收益应重新计算。

每个专家每 token 的线性部分为 `3*d*m` MAC；V3 d=7168、m=2048，权重共 44040192 元素。prefill 的多个 token 可共享同一专家权重读取；低 batch decode 的 T_e 小且不均衡，不能用理想 GEMM 利用率代表实际吞吐。

路由/dispatch/combine 更适合作为独立可配置数据搬运接口，携带 expert id、token id、权重、分组/偏移、dtype/scale、长度和完成/credit 信息。以每专家一份完整输入发送且无目的地合并为定义，dispatch payload 为 `T*k*d*b`，combine 同量级；shared、metadata、局部命中和重复发送另算。若同一目的地多个专家共享 token，可减少跨目的地输入发送；因此这个公式不是物理链路总流量的无条件上下界。

V3 论文中的生产通信采用 expert placement、分组路由和层次网络协同；官方最小 Python 推理代码则遍历本地专家并执行 all_reduce。不能把这个演示代码的 collective 当成论文生产部署的 all-to-all 实现。出处：[V3 报告 v2，3.2.2 与 3.4](https://arxiv.org/html/2412.19437v2)。

## 4. 对首轮固定 Block 的建议（研究推论，尚未硬件验证）

| 候选 | 适合固定的内容 | 必须可配置或由外部协议表达 | 需要验证的代价 |
|---|---|---|---|
| GEMM tile + 可选局部 epilogue | MAC / reduction / tile buffer 数据通路 | M/N/K、布局、transpose、精度、scale 粒度、累加格式 | 利用率、remainder padding、带宽与局部存储 |
| SwiGLU expert tile | gate/up → SiLU× → down 的局部依赖 | expert weight 地址、m、tile、token batch、输出权重 | 中间缓存与可省的 4 条跨边流量；偏斜到达与排队 |
| attention reduction tile | QK / online softmax / PV 的局部累加 | MHA/GQA/MLA 数据形状、mask、RoPE/scale、cache descriptor、稀疏索引 | 缓存读放大、多头重用、精度、在线归约状态 |
| routing / gather / scatter | 有界选择、重排和带 tag 的发送/接收原语 | top-k、group、expert placement、combine 语义、credits | 动态 fan-out、拥塞、burst、缓冲深度 |
| cache service | 按 descriptor 读写、生命周期与同步协议 | 所有权/跨层共享、page、layout、dtype、compression、index reuse | 端口冲突、共享并发、跨 Block 距离与流量 |

不建议首轮固化一个完整“V3 Transformer layer”或按模型层号复制 Block。模型内参数不同、prefill/decode 形状不同、较新模型可共享跨层缓存；这些都需要图到资源的映射，而非一层等于一块物理实体。

Block 划分与外部互联必须联合评价。建议每条 cut edge 至少记录：source/destination 算子、张量 shape、dtype/scale、tile 顺序、单次 payload、复用次数、平均到达率、允许 burst、producer/consumer 节拍、缓冲需求、同步依赖与可容忍 backpressure。对链路 l，不能仅要求平均流量小于带宽；还需用同一 dispatch/prefill/decode trace 计算在时间窗内的积压与 deadline。接口裕量应分别约束端口数、每端口速率和 FIFO 深度，不能用单一“多留 20% 引脚”替代动态流量模型。

缓冲不足时默认采用 backpressure 或分批重排，不能为满足固定容量而擅自丢弃 token、专家或稀疏索引；这些会改变模型语义。top-k 平均负载也不能替代最坏或指定分位数的 burst 约束。逻辑张量位宽与物理引脚数之间还隔着序列化、时钟、握手、布局和布线，不可直接把 `d×dtype_bits` 当成芯片边界的所需 pin 数。

联合优化可先比较三种合法 partition：逐算子、专家/attention 局部融合、整层复合。保持同一工作负载与精度，统计 cut payload、局部峰值存储、最长依赖、端口需求和在固定互联上的排队/吞吐，再选 Pareto 点。首轮输出应称解析模型或调度仿真；只有后续 RTL / synthesis / physical evidence 才能支持面积、时序和能耗结论。

## 5. 训练仅作为约束

V3 报告说明 FP8 GEMM 包括 Fprop、Dgrad、Wgrad，activation 使用 1×128、weight 使用 128×128 分组；敏感算子保留更高精度。训练中还对 RMSNorm 和 MLA up-projection 重计算。MTP 的辅助训练路径可以在普通推理中不用，也可服务 speculative decoding。首轮不实现 optimizer、gradient、反向调度或训练通信。[V3 报告 v2，2.2 与 3.3](https://arxiv.org/html/2412.19437v2)。

本研究的约束推论：接口应携带 scale 粒度与数值类型，不能只写“支持 FP8”；为未来转置视图留下表示能力即可，不能声称 forward GEMM 数据通路已验证 backward。训练公式 `Y=XW; dX=dY W^T; dW=X^T dY` 只是说明 shape/layout 需求，不代表当前交付包含训练执行。

## 6. 已执行的独立正确性实验

运行脚本 `check_deepseek_paths.py` 是独立 NumPy 推导实现，不导入上游 PyTorch/Triton；只用随机缩小张量，不下载权重。包含 query/KV 低秩投影、RMSNorm、解耦普通 RoPE、因果 mask、输出投影。种子 19、20261022、314159；每个种子用 `(B,T)=(1,1),(1,7),(2,19)`。

实际 Python 3.13.14，NumPy 2.5.0，float64。36 项 MLA 数值比较、18 项 routing 权重比较、9 项路由索引精确检查、9 项 bias 误用负例全部通过。MLA 最大绝对误差 `8.881784197001252e-16`；routing 最大误差 `4.440892098500626e-16`；所有将 bias 错用于组合权重的负例均产生明显差异，最小最大绝对偏差 `0.042772847656759594`。

数值比较涵盖 naive 与 absorbed 概率/输出、全 prefill 与逐 token cache append 的 decode、物化 softmax 与 tile=3 的在线 softmax。它验证数据流等价，不能证明 checkpoint 精度、FP8/FP4 误差、完整 YaRN、分布式通信、稀疏 attention 或硬件性能。路由输入随机，不代表真实请求的负载分布。

复现命令（脚本和输出可移动，除 NumPy 外无额外依赖）：

```powershell
& 'D:/APP/Python/python.exe' -B 'D:/Projects/Codex/operator-partition-20261022/deepseek/check_deepseek_paths.py' --output 'D:/Projects/Codex/operator-partition-20261022/deepseek/deepseek-correctness.json'
```

结果文件记录运行时、依赖版本、脚本 SHA、上游 commit、每项误差与边界限制；重新运行时间戳会改变结果文件 SHA。首次结果 SHA-256 为 `c01bf9762d0eac90d0dcd2d9c6af5ad6976dad998e68714814c956a258919fd7`，脚本 SHA-256 为 `c2da49a86881275a76fa8972791ba0d4ccae593c933b8547e9593afce6df48e0`。

本地完成项：官方配置/源码冻结、来源与 SHA 索引、模型差异与 Block 约束说明、缩小实验及结果。尚未执行：真实权重/请求 trace、低精度量化误差、cycle-level scheduling、RTL/PPA、服务器实验。远端上传与 Issue/PR/看板同步由主任务统一处理，本子任务未执行。
