# 2B–4B 模型科研 ASIC 推理吞吐调研

2026-11-12（Asia/Shanghai） · [Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261) · [PR #251 的基准合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-benchmark-contract.md)

收录面向 2B–4B 模型的科研 ASIC、研究型 PIM/NMP 及流片前硬件设计，采用论文和官方模型的标称规模。多模态论文注明视觉输入和计时范围。主指标为逐 token 解码速度，预填充速度用输入 tokens/s 表示，端到端生成速度单列。功耗和频率仅记录来源明确的测量边界。按各论文的原始工况收录，记录与项目不同的量化、带宽、上下文和测量边界。2026-11-12 补充九篇科研硬件论文。本调研引用公开结果，无新仿真、板测或物理验收。

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

### 本轮新增科研 ASIC 与流片前设计

以下各行保留原始工况。标为“图读数”的数字由原论文的坐标轴或图中标签取得。按延迟折算的速度和功耗给出分母及测量边界。

| 论文 / 受测模型 | 速度与实验工况 | 工艺与运行点 | 面积 | 功耗或能效 | 证据与来源 |
| --- | --- | --- | --- | --- | --- |
| **ProQuant**，2026 / Qwen2-VL-2B-Instruct、Qwen2.5-VL-3B-Instruct、Qwen3-VL-2B-Instruct | 256 视觉 + 256 文本 token 时，W4A4 的 decode 吞吐依次为 **31.85、16.01、27.86 tokens/s**，按论文的 `1000 / 延迟(ms)` 折算。各精度的延迟及能量见下表 | **TSMC 22 nm 流片**。板上调压电路支持 0.6–1.0 V，表中工况的具体电压和频率待核实。8 GB DDR4、38.4 GB/s，片上 token 与权重缓冲区各 4 MB，INT8 峰值 2.46 TOPS | 裸片面积待核实 | 同工况 W4A4 的加速器与 DDR4 平均功耗约 **3.95、3.95、3.94 W**，由 mJ 除以 ms 折算 | 片上延迟与功耗实测，外部 DDR4 访问用 DRAMPower 模拟，整模型结果由周期模型组合。ZU5EV FPGA 提供控制及接口。[附录 E、表 A7–A12](https://arxiv.org/html/2611.08216v1#A5) |
| **NVLLM**，DAC 2026 / OPT-2.7B，INT8 | **23.2 / 29.9 / 35.4 tokens/s**，分别为基础版 / 12C / 16C（32 / 48 / 64 个 NAND plane），解码上下文 **64 token**，图 6(a) 柱上标注 | TSMC 28 nm，NPU 500 MHz、NAND CMOS 350 MHz。FFN 权重进 3D NAND，Q/K/V/O 权重和 KV cache 走 LPDDR5X | NPU **0.459 mm²**，新增 NAND CMOS 逻辑 **2.692 mm²** | NPU **240.15 mW**、NAND CMOS 逻辑 **895.68 mW**，各为表 2 的模块综合值 | Verilog 综合 + NAND/DRAM 周期模型。表 2 面积、功耗覆盖所列模块，2.7B 各规模整机功耗待核实。[§4、表 2–3](https://arxiv.org/html/2604.25699v2#S4) · [图 6(a)](https://arxiv.org/pdf/2604.25699v2#page=5) |
| **P³-LLM**，2026 v4 / Llama 3.2-3B，W4A8KV4P8 | **约 360 / 670 / 670 / 890 tokens/s**，依次对应 B1 / B2 / B4 / B8 的总解码吞吐，固定 **4K 上下文**，图 13 读数。P8 是 attention score 位宽 | PCU 在 TSMC 28 nm RTL 综合，PPA 缩放至 20 nm HBM-PIM。系统 4 个 1 GHz NPU、16 个 HBM 伪通道，PCU 500 MHz | 论文表 VII 的 PCU 计算 **8.4 mm²**、缓冲 **6.2 mm²**，HBM 面积开销 **17.5%** | PE 在表 VIII 的 1 GHz 比较下为 **0.18 pJ/MAC**，系统解码功耗待核实 | 周期仿真，Llama 使用 post-RoPE K 量化。B2 以上的总吞吐口径包含同批序列。[§VI、表 VII–VIII](https://arxiv.org/html/2511.06838v4#S6) · [图 13](https://arxiv.org/pdf/2511.06838v4#page=12) |
| **PALUTE**，2026 / Qwen3-4B，W4A4 | **1,264 tokens/s**，摘要与表 2 的端到端吞吐。论文另扫输入/输出长度，表 2 对应的长度和 batch 待核实 | LUT 生成器及控制器以 **7 nm CMOS、200 MHz** 综合。系统假设 **35 nm、768 层、24 GB M3D DRAM**，权重、LUT 和 KV 分层放置 | **112.4 mm²**，表 2 按逻辑与存储裸片中较大者计 | **0.16 W**，表 2 的端到端估算值，论文另报 **7,738 tokens/J** | 作者周期仿真 + 逻辑 RTL 综合。近存储集成与 768 层并行度属于设计假设。[摘要与 §4、表 1–2](https://arxiv.org/html/2606.08891v1#S4) |
| **CHIME**，2026 / MobileVLM 3B（LLaMA 2.7B + ViT + LDP） | **约 233 tokens/s**，图 6(b) 的 3B 端到端生成点。VQA 默认输入一张 512×512 图像与 128 个文本 token，输出 488 个 token | FP16，1 GHz。逻辑采用 **40 nm RTL 综合并缩放到 7 nm**，存储模型为 **35 nm DRAM、28 nm CNFET RRAM**。200 层 DRAM 和 8 层 RRAM | 图 7 的 DRAM / RRAM 两块逻辑 die 分别 **28.71 / 24.85 mm²** | 图 6(b) 的 3B 点约 **1.6 W**（图读数），表 V 给出的跨模型典型值为约 2 W | 自研系统仿真 + NeuroSim + RTL 综合。吞吐对应多模态端到端工况。[§IV、表 II–V](https://arxiv.org/html/2601.19908v1#S4) · [图 6–7](https://arxiv.org/pdf/2601.19908v1#page=6) |
| **TriGen**，2026 / Llama 3.2-3B、OPT-2.7B，MXINT8 激活、UINT4 权重 | 图 9 在序列长度 **2048** 给端到端相对延迟，完整优化约为各自基线的 **0.36× / 0.39×**（图读数）。绝对解码 tokens/s 待核实 | **14 nm** RTL 核对 C++ 周期模型。默认单 NPU、1 GHz、32×32 MPA、1 MiB/NPU、32 GB/s DRAM 总带宽 | 整芯片面积待核实 | 整芯片功耗待核实 | 归一化基线为该设计的 INT16/UINT4 配置。Llama 采用 SpinQuant + GPTQ，OPT 采用 AWQ + GPTQ。[§VII、表 IV–V](https://arxiv.org/html/2602.12962v1#S7) · [图 9](https://arxiv.org/pdf/2602.12962v1#page=10) |
| **FlexPosit**，2026 / Phi-2 2.7B、OPT-2.7B | 图 11 的相对 FP16 基线延迟为 **0.247× / 0.225×**，**B1、256 输入 token**、等计算面积，按 BitMoD 4-bit 的 PPL 对齐。权重 Posit 平均 **4.5 / 4.1 bit**，激活 FP16。绝对解码 tokens/s 待核实 | **16 nm** RTL，1 GHz 阵列，DDR4 采用 Ramulator 2.0，激活/权重缓冲各 512 KB | 32×16 阵列 **0.109761 mm²** | 同一阵列 **65.537 mW**，表 VIII 的综合估算 | 图 11 为等面积模型结果，表 VIII 为阵列 PPA，系统级功耗待核实。[§VI、表 II/VIII](https://arxiv.org/html/2609.04724v1#S6) · [图 11](https://arxiv.org/pdf/2609.04724v1#page=12) |
| **Pimba**，MICRO 2025 / RetNet、GLA、HGRN2、Mamba-2，均按论文 2.7B 档 | 图 12 为归一化生成吞吐。**Mamba-2 2.7B** 在 B32 / B64 / B128 时，约为 A100 基线的 **1.4× / 1.8× / 2.4×**（图读数），输入和输出各 **2,048 token**。绝对 tokens/s 待核实 | FreePDK **45 nm** 综合后缩放至 **10 nm**，SPU 378 MHz，HBM2E 总线 1,512 MHz，单 GPU + 研究 PIM 架构 | 表 3 单元 **0.092 mm²**，含 **0.053 mm²** 计算及 **0.039 mm²** 缓冲 | 计算逻辑 **8.2908 mW**，表 3 单元口径 | Ramulator2 周期模型。状态使用 MX8，GPU 与存内单元分工，面积和功耗对应所提 PIM 模块。[§6、表 3](https://arxiv.org/html/2507.10178v3#S6) · [图 12](https://arxiv.org/pdf/2507.10178v3#page=10) |
| **MX-like Tensor Core**，ASPDAC 2027 作者预印本 / Qwen2.5-3B | **204.8 GOPS**，4×16 PE + 重量化单元，用真实 Transformer 层的 **32×1024** 数据块驱动。整模型解码速度待核实 | **TSMC 28 nm，400 MHz、0.8 V、TT**，使用 2,048 次 MAC 的门级活动估算功耗 | 代表配置 E2M3×E2M1、UE5M3 为 **0.646 mm²** | 对应 **51.6 mW**，包含论文所列片上存储和移动开销 | SNAX 上的算子综合和门级评估。同一模型的算子参考。[§4、图 5(d)](https://arxiv.org/html/2610.26083v1#S4) |

#### ProQuant 解码原始值与换算

同一行的四组数据均为 256 视觉 + 256 文本 token，格式为“延迟 ms / 能量 mJ / 速度 tokens/s”。其中 W4A4 的速度区间按表 A7–A9 的四种输入组合折算。W8A8 出自表 A10–A12。 [附录 E](https://arxiv.org/html/2611.08216v1#A5)

| 模型 | BF16 | W8A8 | W4A8 | W4A4 | W4A4 解码区间（tokens/s） |
| --- | --- | --- | --- | --- | ---: |
| Qwen2-VL-2B-Instruct | 124.55 / 493.04 / 8.03 | 62.71 / 246.94 / 15.95 | 31.79 / 124.33 / 31.46 | 31.40 / 123.95 / 31.85 | 30.96–31.85 |
| Qwen2.5-VL-3B-Instruct | 248.69 / 984.06 / 4.02 | 125.07 / 492.73 / 8.00 | 63.25 / 247.63 / 15.81 | 62.45 / 246.85 / 16.01 | 15.72–16.01 |
| Qwen3-VL-2B-Instruct | 140.46 / 556.20 / 7.12 | 70.35 / 278.22 / 14.21 | 35.89 / 141.56 / 27.86 | 35.89 / 141.56 / 27.86 | 25.35–27.86 |

## 与 PR #251 的比较条件

- **同模型整模型候选是 EdgeCIM 的 Qwen2.5-3B。** 该论文采用 128 输入/128 输出、273 GB/s 和 INT4/INT8 的设计空间搜索。项目对比条件是同一 Qwen2.5-3B 权重与数值合同、W8A16、B1、512 输入/128 输出、无投机、51.2 GB/s。同样评估 Qwen2.5-3B 的 MX-like Tensor Core 给出的是算子吞吐。Qwen2.5-VL-3B、Qwen3 和 Llama 使用不同计算图。 [项目合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-benchmark-contract.md) · [EdgeCIM v2 `V](https://arxiv.org/html/2604.11512v2#S5)
- **绝对值依赖权重供给与序列长度。** 在项目历史 trace 每 token 都读取 3,298,000,896 B 权重的假设下，峰值 DDR 权重供给上限为 `51.2e9 / 3,298,000,896 ≈ 15.52 token/s`，尚需支付 KV、激活、计算和协议成本。9.215647 token/s 是项目的历史条件基线。公开表中尚未找到能与该条件直接比较的同模型实测。 [基线及字节账本](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-benchmark-contract.md)
- **连续生成的计时分母**可采用从首个到末个输出 token 的时间，分子为该时间窗内的 token 间隔数，平均 TPOT 为该段总耗时除以 token 间隔数。另报 TTFT、prefill tokens/s、p50/p95 TPOT，记录 KV 起始长度、权重/KV 精度、频率、内存配置、是否含主机时间。不同内存和精度下的公开吞吐保留原条件。

## 协作交接

研究源基于 PR #251 的 `9abd46f5cbb4534bcfc614571ccd6d402ad11882`，任务分支 `task/261-llm-asic-benchmarks`，负责人 Melodydt。服务器方式沿用本人目录和 Slurm 批处理约定。需要继续做同条件仿真时，先读取当前 #250/#234 的模型、量化、输入和源码版本，并为 #261 使用独立目录与作业名，提交后记录作业号和日志。 [项目远程规则](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/REMOTE_RULES.md)

管理中心登记 PR #5 待合并。当前仓库默认分支及任务基线未读到 `config/board.json`，可用 GitHub 工具未提供 Projects 条目及字段操作。Issue #261 的看板状态待核验，同步待执行。具权限维护者待指定，恢复时先核对适用看板、受众和字段，再复用或加入本 Issue，按状态映射同步 Project ID `llm-hardware-design` 与 Issue 实际状态，并读回条目 ID 和核验时间。 [登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) · [状态映射](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/config/status-mapping.json)
