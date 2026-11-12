# 2B–4B 文本模型 ASIC 推理吞吐调研

2026-11-12（Asia/Shanghai） · [Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261) · [PR #251 的基准合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-benchmark-contract.md)

收录总参数量为 2B–4B 的公开文本模型或论文注明规模的实验模型，采用来源的型号标称规模。主指标为逐 token 解码速度，预填充速度用输入 tokens/s 表示，端到端生成速度单列。功耗和频率仅记录来源明确的测量边界。按各论文或厂商的原始工况收录，记录与项目不同的量化、带宽、上下文和测量边界。2026-11-12 扩充逐篇 PPA 与实验配置。本调研引用公开结果，无新仿真、板测或物理验收。

## 专用 ASIC 论文

| 工作 | 模型及精度 | 生成速度（输出 tokens/s） | 条件及证据 | 论文 |
| --- | --- | ---: | --- | --- |
| Slim-Llama，ISSCC 2025 | Llama-3B，论文使用二值/三值权重，混合精度处理其他数据 | — | Samsung 28 nm 流片。另一篇论文复列 1,024 输入 token 预填充用时 0.635 s，折算约 **1,613 输入 tokens/s**。公开可核对资料中，连续生成速度待核实。 | [ISSCC 原论文](https://doi.org/10.1109/ISSCC49661.2025.10904761) · [KAIST 项目页](https://ssl.kaist.ac.kr/bbs/board.php?bo_table=HI_systems&wr_id=39) · [VitaLLM 表 I](https://arxiv.org/html/2605.00320v1#S4.T1) |
| VitaLLM，2026，Mixed-Precision 版 | BitNet b1.58 3B，三值权重、INT8 激活，注意力用混合精度 | **72.46** | 预填充 64 token 用时 0.88 s。作者称为 16 nm、1 GHz、0.8 V 的原型，正文未说明板级测量方法或该点的解码上下文。权重/KV 在片外 DDR，使用 LOP 筛选 KV。 | [`IV、表 I](https://arxiv.org/html/2605.00320v1#S4) |
| VitaLLM，2026，Dependency-Aware 版 | BitNet b1.58 3B；同系列 2B 扩展，独立 checkpoint 待核实 | **70.70**（3B），**99.21**（2B） | 同一设计系列的另一篇预印本。16 nm、1 GHz，模型估算与布局后门级仿真交叉验证。64 token 预填充分别为 0.88 s 和 0.65 s。 | [`III、表 V–VI](https://arxiv.org/html/2604.27396#S3) |
| EdgeCIM，2026 v2 | Llama 3.2-3B、SmolLM3-3B，INT4 | **139.3**、**148.7** | 65 nm SRAM-CIM 设计的流片前整模型评估。B1、128 输入/128 生成，名义 DRAM 带宽 273 GB/s；按模型和精度搜索硬件配置。 | [`V、图 12、表 III](https://arxiv.org/html/2604.11512v2#S5) |
| EdgeCIM，2026 v2 | Qwen2.5-3B、Phi-3.5-mini-3.8B、Qwen3-4B，分别测试 INT4 与 INT8 | 见下表 | 同一篇论文的图 12(a)，横向比较采用各模型和精度各自搜索得到的配置。 | [原论文 PDF，图 12(a)](https://arxiv.org/pdf/2604.11512v2#page=9) |
| ROMA，2025 | Llama 3.2-3B，INT4 基础权重、FP8 LoRA rank 16、FP16 激活及 KV | **24,600**（1K KV）；**31,800**（空 KV 峰值） | TSMC 7 nm 综合评估，500 MHz，基座权重驻留片上 ROM。图 9 固定输出 4K，256 输入 token 时报告 20,078 输出 tokens/s，2K 输入时为 8,533，属于另一计时口径。表 I 的 503.7 mm² 与 33.1 W 为综合评估配置。 | [`IV、表 I、图 7–9](https://arxiv.org/html/2503.12988v1#S4) |

EdgeCIM 图 12(a) 近似读数。精确数字以论文正文或表格为准。

| 受测模型 | INT4（输出 tokens/s） | INT8（输出 tokens/s） |
| --- | ---: | ---: |
| Qwen2.5-3B | 约 150 | 约 75 |
| Phi-3.5-mini-3.8B | 约 120 | 约 55 |
| Qwen3-4B | 约 110 | 约 50 |

TENET 提供另一种三值 BitNet-3B ASIC 方案。论文 `V 公开按模型规模和输入/输出长度的相对加速，3B 档整段推理相对优化版 A100 为 1.33×，原文提供 28 nm 综合与周期仿真、512 GB/s HBM2 的评估条件。绝对输出 tokens/s 待核实。 [TENET 原论文 `V](https://arxiv.org/html/2509.13765#S5)

## 逐篇实验配置与 PPA

面积和功耗沿用原文边界。表中的功耗随负载、频率、是否计入存储而变化。峰值吞吐、持续解码、预填充和算子吞吐采用各自原始口径。无法追溯到所列模型或工况的指标写为“未核实”。

| 论文 / 受测模型 | 工艺与运行点 | 面积 | 功耗或能效 | 证据 |
| --- | --- | ---: | --- | --- |
| Slim-Llama / Llama-3B | Samsung 28 nm，25–200 MHz，0.58–1.0 V | 20.25 mm² 裸片 | 芯片 4.69 mW @ 25 MHz、0.58 V；82.07 mW @ 200 MHz、1.0 V | ISSCC 流片。0.635 s 的数字来自后来论文的预填充对照表。[原论文](https://doi.org/10.1109/ISSCC49661.2025.10904761) · [VitaLLM 表 I](https://arxiv.org/html/2605.00320v1#S4) |
| VitaLLM Mixed-Precision / BitNet b1.58 3B | TSMC 16 nm，1 GHz、0.8 V | 0.214 mm²，120 KB 片上 | 59.12 mW，外部 DDR 的功耗是否计入待核实 | 论文称原型；完整板测方法待核实。[原论文表 I](https://arxiv.org/html/2605.00320v1#S4) |
| VitaLLM Dependency-Aware / BitNet b1.58 3B | TSMC 16 nm，1 GHz、0.8 V | 0.223 mm² 核心，130.5 KB 片上 | 65.97 mW；外存能耗未与该值单独绑定 | 性能模型与布局后门级仿真交叉核对。[原论文 §IV](https://arxiv.org/html/2604.27396#S4) |
| EdgeCIM v2 / 3B–4B 五款模型 | 65 nm SRAM-CIM PE 参考，DRAM 模型 273 GB/s | 各模型专属面积见图 12(c)。另有 **44.66 mm²** 的联合搜索配置 | SmolLM3-3B INT4 为约 72.5 tokens/J。与同一段给出的 148.7 tokens/s 联算，约 **2.05 W**，为模型推导。图 13(b) 另分加速器与含 LPDDR5X 的系统能效 | 流片前系统设计空间评估，校核层级为 PE 和代表算子。[原论文 §IV–V](https://arxiv.org/html/2604.11512v2#S4) |
| ROMA / Llama 3.2-3B | TSMC 7 nm，500 MHz | 503.7 mm²，1.86 GB B-ROM + 304 MB SRAM | 33.1 W，论文表 I 的综合功耗配置 | Design Compiler 综合与 PrimeTime PX 估算。[原论文 §IV](https://arxiv.org/html/2503.12988v1#S4) |
| TENET / Sparse BitNet 3B | TSMC 28 nm，500 MHz | 91.0 mm²，256 KB 输入 + 128 KB 权重 + 1 MB KV 缓冲 | 5.7 W 为表 IV 加速器合计；HBM 未分配表内功耗值 | 综合和周期仿真，512 GB/s HBM2。[原论文 §V](https://arxiv.org/html/2509.13765#S5) |
| TOM / BitNet b1.58 2B | 7 nm，500 MHz | 56.9 mm²，约 58% 为 ROM | 5.33 W 芯片估算，启用按负载门控。禁用时 25.813 W | Verilator 周期仿真、综合和 PowerArtist；ROM 子模块做了布局布线。[原论文 §V](https://arxiv.org/html/2602.20662v1#S5) |
| MARCA / Mamba-2.8B | TSMC 28 nm，1 GHz | 221.88 mm²，24 MB 片上 | 10.44 W，表 4 的加速器模块合计 | RTL 综合、周期仿真、Ramulator 2.0 模拟 HBM。[ICCAD 2024 原论文](https://dai.sjtu.edu.cn/my_file/pdf/010527f5-f0b2-4859-8c27-9052bd14da49.pdf) |
| MARCA-v2 / Mamba-2.8B | TSMC 28 nm，1 GHz | 296.37 mm²，24 MB + 16 KB 片上 | 113.24 W，表 III 的芯片峰值估算 | RTL 综合、周期仿真，32 个 RCU。[TCAD 原论文](https://doi.org/10.1109/TCAD.2025.3624278) · [作者版](https://dai.sjtu.edu.cn/my_file/pdf/0a61722b-778e-459c-a5fe-5b01ea5e3661.pdf) |
| Platinum / BitNet b1.58 3B | ARM 28 nm 库，500 MHz | 0.955 mm²，416 PE，324 KB 片上缓冲 | **3.2 W** 对应 3B 预填充矩阵负载，含 DRAM 访问功耗；其中 DRAM 占 53.5% | 综合和周期仿真，64 GB/s DDR4。[原论文 §V](https://arxiv.org/html/2511.21910#S5) |
| HB-PIM / OPT-2.7B | 32 nm 标准单元，DuoPU 1 GHz | 1.24 mm² **每个 DuoPU** | 807.81 mW **每个 DuoPU** | Verilog 综合、CACTI 和系统仿真。16 个逻辑核与 16 个 DRAM 核，16 GB。单核跨 die 128 GB/s，核间 32 GB/s 每链路。[原论文表 2、图 8](https://doi.org/10.1007/978-981-95-1021-4_16) |
| Titanus / OPT-2.7B | 14 nm FinFET，200 MHz；CIM 宏由 22 nm 缩放 | 2.7B 档未单列 | 2.7B 档未单列 | RTL 综合、CACTI、NVMain 模拟 HBM。表 2 的面积功耗属于 125M 核。[原论文 §5](https://arxiv.org/html/2505.17787#S5) |

### 已有论文的工作负载细节

- **Slim-Llama。** 二值/三值权重用稀疏感知查找表与部分输出复用，芯片约有 500 KB 片上存储，论文报告使用 DDR3 的三值 Llama 能耗为 28.3–41.3 μJ/token。预填充的 0.635 s 与最低 4.69 mW 工况没有可核实的对应关系。原论文的 Figure 23.9.6/7 给出芯片测量及规格。[ISSCC 论文](https://doi.org/10.1109/ISSCC49661.2025.10904761) · [KAIST 芯片页](https://ssl.kaist.ac.kr/bbs/board.php?bo_table=HI_systems&wr_id=39)
- **两篇 VitaLLM。** 短版表 I 的 72.46 tokens/s 和长版表 V 的 70.70 tokens/s 各自对应上表 PPA。长版模拟双通道 LPDDR5T 峰值 76.8 GB/s，解码读峰值 63 GB/s，Top-32 LOP 先筛选 KV。长版 2B 扩展点 99.21 tokens/s、64 输入预填充 0.65 s，独立权重版本和 2B 专属 PPA 待核实。[短版 §IV](https://arxiv.org/html/2605.00320v1#S4) · [长版 §IV](https://arxiv.org/html/2604.27396#S4)
- **EdgeCIM。** 128 输入决定解码时初始 KV，128 输出用于计时。图 12(a) 的模型级速度来自各自搜索的硬件，44.66 mm² 是同一固定配置跑全部模型与精度的联合搜索结果。论文同时改变带宽作敏感性分析，273 降到 68.3 GB/s 时该组解码时延增加约 2.38×。图 12(c) 可复查各模型的面积柱，表中仅引用正文明确给出的面积。[EdgeCIM v2 §V](https://arxiv.org/html/2604.11512v2#S5)
- **ROMA。** INT4 Llama 3.2-3B 基座固定在 ROM，可换 FP8 LoRA。rank 16 时 TTFT 为 5.6 ms（256 输入）和 140.2 ms（4K 输入），逐步解码点分别为 31.8k（空 KV）和 24.6k（1K KV）。图 9 则用 4K 输出考察整段请求，引用时保留其定义。[ROMA §IV](https://arxiv.org/html/2503.12988v1#S4)
- **TENET。** Sparse BitNet 3B 由稠密模型继续训练。动态激活稀疏按 32 元素块选择约一半，稀疏注意力配置的序列参数为 1024。图 12 给不同工作量的阶段加速，正文的 3B 档 **1.33×** 为相对优化 A100 的端到端结果。绝对输出 tokens/s 未核实。[TENET §V](https://arxiv.org/html/2509.13765#S5)

### 新增论文的实验结果

- **TOM: A Ternary Read-only Memory Accelerator for LLM-powered Edge Intelligence。** BitNet b1.58 2B，三值权重、FP8 激活和 KV，16 条处理 lane，片上 ROM 498.54 MB、SRAM 37.5 MB，最大纯片上上下文 1024。论文评估含 64、128、256、512 token 的多组输入/输出组合，图 11(b) 单步 **302.4 μs/token** 对应约 **3,306 tokens/s 峰值**。内存表的 200 TB/s 为片上汇总带宽。固定权重和近存储的功耗门控是该结果的重要条件。[TOM §V、表 I/IV、图 11/12](https://arxiv.org/html/2602.20662v1#S5)
- **MARCA 与 MARCA-v2。** 都覆盖 Mamba-2.8B，32 位定点，256 GB/s HBM1.0。MARCA 图 9 用长度 1、64、512、2048、4096、8192 给相对速度和能效。MARCA-v2 图 13 用长度 1 表示 decode，64–8192 表示 prefill，报告的是相对加速，正文跨模型范围对 MARCA 为 1.00–1.01× decode。2.8B 的绝对 tokens/s 未核实。v2 采用互补 SSM 稀疏与近似非线性，表 III 的 113.24 W 是峰值功耗估算。两篇论文的功耗口径按各自表格引用。[MARCA §7](https://dai.sjtu.edu.cn/my_file/pdf/010527f5-f0b2-4859-8c27-9052bd14da49.pdf) · [MARCA-v2 §VII](https://dai.sjtu.edu.cn/my_file/pdf/0a61722b-778e-459c-a5fe-5b01ea5e3661.pdf)
- **Platinum: Path-Adaptable LUT-Based Accelerator Tailored for Low-Bit Weight Matrix Multiplication。** 3B BitNet 的三值 BitLinear 核测试用矩阵列数 N=1024（prefill）及 N=8（decode），后者对应一批 8 列计算。3B 核级 decode 对 Prosperity 加速 28.4×、对 16 线程 T-MAC 加速 1.75×。论文公开结果以提取的线性核为主，整模型自回归输出 tokens/s 未披露。[Platinum §V](https://arxiv.org/html/2511.21910#S5)
- **HB-PIM: Unifying Two Operators with One PIM。** 包含 OPT-2.7B，图 8 对 Alpaca 和 ShareGPT 报告相对吞吐性能。论文的 4.06× 相对 vLLM-GPU 是整个模型组的平均。2.7B 绝对解码速度及整堆叠 PPA 未核实。DuoPU 的面积功耗仅为 32 nm 综合估算的计算单元。[HB-PIM 论文](https://doi.org/10.1007/978-981-95-1021-4_16) · [表 2 和图 8 全文](https://eurekamag.com/research/100/402/100402060.pdf)
- **Titanus: Enabling KV Cache Pruning and Quantization On-the-Fly for LLM Acceleration。** OPT-2.7B 的纳入证据是 W8A8 SmoothQuant、INT3 KV 量化及级联剪枝的质量评估和对应的 core 设计。TruthfulQA 中该模型的 ROUGE-1 为 0.4311（原始）和 0.4289（HQE）。2.7B 档的解码速度、面积和功耗待核实。论文加速 headline 对应 6.7B。[Titanus §5](https://arxiv.org/html/2505.17787#S5)

### 商用 SoC 上的新增论文

- **SmartBench: Is Your LLM Truly a Good Chinese Smartphone Assistant?（EMNLP 2025）。** iQOO 12 的 Snapdragon 8 Gen 3 NPU（SoC 4 nm），Qualcomm QNN、W4A16、表 5 的上下文长度 2048。Qwen2.5-3B（3.1B）为 **24.9 输出 tokens/s、873.4 输入 tokens/s、6.8 W**。BlueLM-3B（2.7B）为 **27.1 输出 tokens/s、930.9 输入 tokens/s、6.4 W**。表 5 未披露生成长度、面积或电源轨测量范围，功耗按手机测试值引用。[EMNLP 论文表 5](https://aclanthology.org/2025.emnlp-main.194.pdf) · [Qualcomm 工艺规格](https://docs.qualcomm.com/doc/87-71408-1/87-71408-1_REV_D_Snapdragon_8_gen_3_Mobile_Platform_Product_Brief.pdf)
- **Apple Intelligence Foundation Language Models（2024）。** 约 3B 的 AFM-on-device，混合 2/4 bit 平均 3.7 bit/weight，使用 iPhone 15 Pro（A17 Pro，3 nm），作者报告 **30 输出 tokens/s**（无投机），TTFT 约为每输入 token 0.6 ms。该数来自作者配套说明，未披露 prompt/输出长度、独立 Neural Engine 面积和对应功耗。2025 年 2-bit QAT 版模型不沿用该速度。[技术报告](https://arxiv.org/html/2407.21075#S5) · [苹果测试说明](https://machinelearning.apple.com/research/introducing-apple-foundation-models) · [A17 Pro 工艺](https://www.apple.com/newsroom/2023/09/apple-unveils-iphone-15-pro-and-iphone-15-pro-max/)
- **When NPUs Are Not Always Faster（2026）。** Snapdragon 8 Gen 3、Hexagon v75、16 GB RAM、Android 15、llama.cpp b7588，测试 Q4_0 的 Llama 3.2-3B 和 Qwen3-4B。用约 321、641、1281 输入 token 测试不同卸载比例，6 CPU 线程，论文默认 batch 参数 128。绝对解码点见图 2(e)/(g)。表 III 的 208/210 μs 是单次矩阵算子调用时延。Llama 3.2-3B 的全层卸载配置存在 CPU 回退，三种 prompt 下的整机电池耗能较 CPU-only 增加 22%、32%、51%。芯片面积和芯片独立功耗未披露。[论文 §III–IV](https://arxiv.org/html/2605.27435#S3)

## 商用 ASIC 与片上 NPU 公开数据

| 硬件 | 模型 | 输出 tokens/s | TTFT | 配置与范围 | 来源 |
| --- | --- | ---: | ---: | --- | --- |
| Axelera Metis Edge 130p 16 GB PCIe | Llama 3.2-3B | **5.5** | 1.50 s | 1 张卡，4096 prompt；厂商定义为首 token 后的生成速度。该表未列生成长度和量化。 | [Voyager SDK](https://github.com/axelera-ai-hub/voyager-sdk/blob/latest/docs/reference/models/model-zoo.md#llm-performance-characteristics) |
| Axelera Metis Edge 130p 16 GB PCIe | Qwen3-4B | **4.7** | 2.04 s | 同一参考平台与 4096 prompt。 | [Voyager SDK](https://github.com/axelera-ai-hub/voyager-sdk/blob/latest/docs/reference/models/model-zoo.md#llm-performance-characteristics) |
| Rockchip RK3588 NPU | Gemma 2 2B | **10.37** | 598.41 ms | W8A8，128 输入/64 生成，CPU/NPU 最高频率。 | [RKLLM 官方 benchmark](https://github.com/airockchip/rknn-llm/blob/main/benchmark.md#rk3588) |
| Rockchip RK3588 NPU | TeleChat2-3B | **10.18** | 618.48 ms | 同上。 | [RKLLM 官方 benchmark](https://github.com/airockchip/rknn-llm/blob/main/benchmark.md#rk3588) |
| Rockchip RK3588 NPU | Phi-3 Mini 3.8B | **7.45** | 1,017.28 ms | 同上。 | [RKLLM 官方 benchmark](https://github.com/airockchip/rknn-llm/blob/main/benchmark.md#rk3588) |
| Rockchip RK3588 NPU | MiniCPM3-4B | **5.94** | 1,408.49 ms | 同上。 | [RKLLM 官方 benchmark](https://github.com/airockchip/rknn-llm/blob/main/benchmark.md#rk3588) |
| Rockchip RK3588 NPU | Qwen3.5-2B | **13.59** | 776.95 ms | 同上。 | [RKLLM 官方 benchmark](https://github.com/airockchip/rknn-llm/blob/main/benchmark.md#rk3588) |
| Rockchip RK3588 NPU | Qwen3.5-4B | **6.22** | 2,068.88 ms | 同上。 | [RKLLM 官方 benchmark](https://github.com/airockchip/rknn-llm/blob/main/benchmark.md#rk3588) |
| Qualcomm Snapdragon 8 Elite Mobile / X Elite / X2 Elite | Llama 3.2-3B Instruct | **30 / 19.7 / 43.2** | — | EdgeCIM v2 表 III 转录 Qualcomm AI Hub 的 INT4 结果。Qualcomm 定义为首 token 后的生成速度。该行采用论文冻结的官方数据快照，具体请求长度待核实。 | [EdgeCIM v2 表 III](https://arxiv.org/html/2604.11512v2#S5.T3) · [Qualcomm AI Hub](https://aihub.qualcomm.com/models/llama_v3_2_3b_instruct) |

Mobilint 的 ISSCC 2026 `17.3 可作为有流片的相关论文，官方模型卡列出 REGULUS 的 Qwen3-4B，公开可核对资料中该模型解码速度待核实。清华的 ISSCC 2026 `31.8 报告投机解码时延范围，公开材料中尚未核实该范围与 2B–4B 目标模型的逐项映射。 [Mobilint 论文](https://doi.org/10.1109/ISSCC49663.2026.11409083) · [Qwen3-4B 模型卡](https://huggingface.co/mobilint/Qwen3-4B-regulus-rb-usb) · [清华论文](https://doi.org/10.1109/ISSCC49663.2026.11408953)

Rockchip RK3576 也公开了同样 128 输入/64 生成条件下的量化对照。W4A16 / W8A8 的输出速度分别为 Gemma 2 2B **9.14 / 5.24**、TeleChat2-3B **8.97 / 5.12**、Phi-3 3.8B **6.58 / 3.74**、MiniCPM3-4B **4.87 / 3.01**、Qwen3.5-2B **11.03 / 6.73**、Qwen3.5-4B **5.02 / 3.03** tokens/s。 [RK3576 官方表](https://github.com/airockchip/rknn-llm/blob/main/benchmark.md#rk3576)

## 与 PR #251 的比较条件

- **同模型候选是 EdgeCIM 的 Qwen2.5-3B。** 该论文采用 128 输入/128 输出、273 GB/s 和 INT4/INT8 的设计空间搜索。项目对比条件是同一 Qwen2.5-3B 权重与数值合同、W8A16、B1、512 输入/128 输出、无投机、51.2 GB/s。相同标称参数量的 Qwen3、Qwen3.5 和 Llama 是不同计算图。 [项目合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-benchmark-contract.md) · [EdgeCIM v2 `V](https://arxiv.org/html/2604.11512v2#S5)
- **绝对值依赖权重供给与序列长度。** 在项目历史 trace 每 token 都读取 3,298,000,896 B 权重的假设下，峰值 DDR 权重供给上限为 `51.2e9 / 3,298,000,896 ≈ 15.52 token/s`，尚需支付 KV、激活、计算和协议成本。9.215647 token/s 是项目的历史条件基线。公开表中尚未找到能与该条件直接比较的同模型实测。 [基线及字节账本](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-benchmark-contract.md)
- **连续生成的计时分母**可采用从首个到末个输出 token 的时间，分子为该时间窗内的 token 间隔数，平均 TPOT 为该段总耗时除以 token 间隔数。另报 TTFT、prefill tokens/s、p50/p95 TPOT，记录 KV 起始长度、权重/KV 精度、频率、内存配置、是否含主机时间。不同内存和精度下的公开吞吐保留原条件。

## 协作交接

研究源基于 PR #251 的 `9abd46f5cbb4534bcfc614571ccd6d402ad11882`，任务分支 `task/261-llm-asic-benchmarks`，负责人 Melodydt。服务器方式沿用本人目录和 Slurm 批处理约定。需要继续做同条件仿真时，先读取当前 #250/#234 的模型、量化、输入和源码版本，并为 #261 使用独立目录与作业名，提交后记录作业号和日志。 [项目远程规则](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/REMOTE_RULES.md)

管理中心登记 PR #5 待合并。当前仓库默认分支及任务基线未读到 `config/board.json`，可用 GitHub 工具未提供 Projects 条目及字段操作。Issue #261 的看板状态待核验，同步待执行。具权限维护者待指定，恢复时先核对适用看板、受众和字段，再复用或加入本 Issue，按状态映射同步 Project ID `llm-hardware-design` 与 Issue 实际状态，并读回条目 ID 和核验时间。 [登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) · [状态映射](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/config/status-mapping.json)
