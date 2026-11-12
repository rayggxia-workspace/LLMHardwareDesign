# 2B–4B 文本模型 ASIC 推理吞吐调研

2026-11-12（Asia/Shanghai） · [Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261) · [PR #251 的基准合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-benchmark-contract.md)

收录总参数量为 2B–4B 的公开文本模型或论文注明规模的实验模型，采用来源的型号标称规模。主指标为逐 token 解码速度，预填充速度用输入 tokens/s 表示，端到端生成速度单列。功耗和频率仅记录来源明确的测量边界。本调研引用公开结果，无新仿真、板测或物理验收。

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
