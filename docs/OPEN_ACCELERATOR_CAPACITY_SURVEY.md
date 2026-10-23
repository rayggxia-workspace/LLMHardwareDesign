# 五个开源加速器：模型规模、资源与 Block 数量

核对日期：2026-10-23（Asia/Shanghai）；任务 [#43](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/43)。以 main `0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d` 的五项目七案例为起点。本文是官方资料/配置/代码调研，**没有新增模型运行或物理实验**。上游实测均为作者报告，本轮未独立复现；“支持”只限所列配置和验证范围，不是最大模型容量保证。

**结论：B 数不能直接换成 Block 数。** 同一组计算单元可以分时执行不同层/模型；模型增大首先影响权重容量、每 token 工作量与搬运量。只有同时冻结精度、场景、目标吞吐、可用存储及带宽，才能估计各类 Block 库存。我们继续以 INT8 计算为设计输入；下列 4-bit 和浮点行用于理解资源变化，不构成本项目改用这些精度的决定。

## 1. 对照表：精度与证据分开

B = 10⁹ 参数，GB = 10⁹ B，GiB = 2³⁰ B，MiB = 2²⁰ B。计算数量分别写乘法位置、向量 lane 或 tensor lane，不能互相等同，也不能用 LUT/标准单元数代替。W/A 分别表示矩阵权重/输入；全流程可能还含更宽的状态、累加和缩放。

| 项目/精度 | 已公开模型及规模 | 计算单元配置 | 存储容量/组织 | 带宽口径 | 验证范围与约束 |
| --- | --- | --- | --- | --- | --- |
| **Gemmini：W8A8，INT32 累加** [G1] / [G2] | 官方 DAC 2021 评估包括 BERT 和 CNN；所核对资料未给出生成式 LLM 的“几 B 上限”，不能补成 7B/13B 支持 | 默认 1 个 16×16 阵列＝256 PE（推导值）；不是本仓库 4×4 案例 | 默认 scratchpad 256 KiB、4 banks；accumulator 64 KiB；主存取决于集成 SoC | DMA 总线 128 bit＝16 B/周期（接口理想上限，推导值）；主存 GB/s 未由此确定 | 可配置生成器；论文的端到端性能来自 FireSim 周期精确 SoC 仿真，另有流片事实；均不能转述成当前配置的完整 LLM 芯片实测 |
| **openTPU：W8A8 矩阵，混合 FP32** [O1] / [O2] / [O3] | 板上报告：LFM2.5-230M、Qwen3-0.6B、Qwen3.5-0.8B/2B、LFM2-2.6B、SmolLM3-3B、Phi-4-mini 3.8B；例如 Qwen3-0.6B 21.6 tok/s、Phi 3.99 tok/s | 1 slice，D=128、MCOLS=4：512 个 INT8 乘法位置（推导值），8 路 VPU；133.33 MHz；VPU/矩阵后处理含 FP32，**不是全流程纯 INT8** | YPCB-00338：2×2 GiB DDR3，共 4 GiB；逻辑 TMEM 64K×32 bit＝256 KiB（推导值，不含读副本等物理开销）；还有 ACT/指令/FIFO 存储，未在此合计 | DDR3-1066 双 64-bit 通道峰值约 17.1 GB/s；模型运行计数器 14.4 GB/s（Qwen 0.6B）、16.0（Phi）；不是主机链路带宽 | 作者板上测量；B=1、512-token prompt、64 greedy 输出，device 时间与含主机 wall 时间分列。Qwen3.5-4B 的 INT8 image 超过 4 GiB，不能列作 INT8 驻卡支持 |
| **openTPU：FP4 存储→整数矩阵输入，A8，混合 FP32** [O1] / [O4] | 上列小模型有 4-bit 行；另有 Qwen3.5-4B，5.88 device tok/s。Phi 3.8B：6.56 tok/s，同精度行内解释 | 同一四列计算硬件；4-bit 解包及 PAIR 使用既有列，不等于所有 INT8 运算吞吐都翻倍 | 同卡 4 GiB；性能表对应的 FP4 格式含 scale，4.25 bit/weight，head 保留 INT8；不是无开销的 0.5 B/参数 | Qwen3.5-4B 15.7 GB/s（模型计数器）；外存峰值仍约 17.1 GB/s | 与上行相同的 prompt/output 口径。FP4 E2M1 **不等于 INT4**。当前源码已有 MX scale 格式，不能把旧性能行的位数/速度直接赋给新格式 |
| **openTPU MoE：4-bit 专家、INT8 head，混合 FP32** [O1] / [O5] | LFM2.5-8B-A1B：**8.5B 总/1.7B active**，10.6 tok/s、160 输出；Qwen3.5-35B-A3B：**34.7B 总/3.0B active**，3.95 tok/s、16 greedy 输出 | 同一卡/引擎；没有按 34.7B 总参数复制 34.7B 对应的并行算术单元 | 4 GiB 卡只驻留部分权重/专家槽；其余 expert pool 在主机，按需换入；不是 35B 全驻卡 | Qwen MoE：62% expert-use 命中，153 MB/token 换入，PCIe 实际约 1.41 GB/s；不能拿 DDR 峰值替代此链路 | 作者 2026-10-01 build B 记录；与 ISA simulator 逐位匹配；这是带主机换入的有限生成轨迹，不是任意上下文/任务质量或长程稳定性认证 |
| **fable5：INT4×INT8，整数定点全流程** [F1] / [F2] / [F3] | Qwen3.5-9B，32 层（24 DeltaNet＋8 full attention）；作者 R2 最佳 chat 解码 8.18 tok/s | BCU-1525/xcvu9p：4 个 matvec channel，每个 128 个 W4×A8 乘法位置，共 512（推导值），约 300 MHz；另有 128-lane DeltaNet、attention、单 lane vector ALU，不能只用 512 描述全部计算 | 4×4 GiB DDR4＝16 GiB；matvec pack 3,902 MiB，另有 1,940 MiB embedding；DDR 层状态 155 MiB；片上保留状态缓存和 scratchpad，残差/递推状态含 INT16，累加更宽 | 平台四通道 streaming probe **70.70 GB/s**（作者板上），不是 9B 整步持续带宽；70.70/(3,902×2²⁰/10⁹)≈17.28 tok/s 只是权重搬运上界（推导值） | 9B gate：4 prompts 共24个输出 token，8次整模型运行逐状态检查；不同于 R2 速度实验。KV 区物理预留 4096 positions，**算术分析仍限制上下文≤511**；不可把容量写成已合格 4K 支持 |
| **llaccel：W8A8，INT32 累加；向量/残差 INT16** [L1] / [L2] / [L3] | Qwen2.5-0.5B、SmolLM2-135M（0.135B）；Llama/Qwen dense importer 支持面更广，不等于这些规模均有完整运行证据；不支持 MoE | 16×16＝256 个 GEMM 乘法位置（推导值）；16-lane vector；64-lane attention；v1 epilogue fusion=0 | 逻辑 1 MiB SRAM＝16×64 KiB banks（推导值），存储体在 core 外；权重/KV 在模拟 DRAM；32-bit DRAM 地址最多寻址 4 GiB，**不是实装容量**。C=1024 KV：Qwen 6 MiB、Smol 11.25 MiB | DRAM 64 B/beat，理想接受1 beat/周期时≤64 B/周期；bank 合计上限16×16＝256 B/周期（推导值）；无可核验板上 GB/s。Qwen T=1024 单步仿真总读 559.857 MiB，33,192,882 cycles | 功能/RTL 仿真；短生成至64 token，1024边界用预初始化 prefix state，**不是完整1024-token RTL prefill**；无板上吞吐证据。attention 概率默认 Q0.15，不能概括成每条路径都是 INT8 |
| **OpenTallas：BF16 Qwen 规划；FP8/MXFP4 另属其他合同** [T1] / [T2] / [T3] | Qwen3-8B：配置总参数 8,190,735,360，decode active 7,568,405,504（排除 input embedding lookup）；属于架构/容量分析对象，**不是已跑通8B硅片** | 以 qwen_x5 为例：5 dies，每 die 649 tiles、41,536 lanes；合计3,245 tiles/207,680 lanes（推导值）；1 GHz/N5 密度等是**假设** | x5 每 die raw ROM 3.372847 GB、KV SRAM 320 MiB；BF16 checkpoint 16,381,470,720 B；同模型还有x4/x8规划，存储/并行划分不同 | x5 source 26,112 B/周期、实际交付预算被 SDN 限为4,608 B/周期；1 GHz下4.608 TB/s为**假设模型推导**；512-bit link endpoint只有64 B/周期，不是PHY标称900 B/周期 | 资源预算一致性、局部RTL/物理方法证据；整合token正确性/合格TPOT未闭环，无OpenTallas流片。README引用的 Taalas HC1 产品成绩不属于本项目；BF16/FP8/MXFP4 lane也不能按INT8 PE折算 |

**跨行不能排行。** openTPU 的较大 B 依赖 MoE active 参数和主机 pool；fable5 的 9B 是 dense/hybrid、W4、不同板卡与状态算法；llaccel 是仿真。openTPU 上相同 Phi 模型 INT8→4-bit 的 device 速度比为 6.56/3.99≈1.64（推导值），说明权重减少并不自动带来2倍整模型速度；量化质量必须另行验收。

### 上游版本与本仓库物理案例的对应

| 本仓库对象 [R1] / [R2] | 本次扩展的上游证据 | 可迁移的结论边界 |
| --- | --- | --- |
| gemmini_4x4，`MeshWithDelays` | Gemmini 默认16×16和DAC论文 | 本地只有16 PE及配套，不含完整SoC/LLM存储系统，不能用默认资源替换案例配置 |
| opentpu_small：D32、MCOLS2、ACT_ROWS2 | 上游板卡D128、MCOLS4；本地来源 `f237dab2f196855a59a083b1454786df8f01291f` | 本地64个乘法位置→板卡512个，数量比8（推导值）；SRAM/后处理/时钟/布线均不按8倍线性外推 |
| opentallas_numeric_e1/e4、vadd8 | 当前BF16 Qwen资源规划 | 数值单元/向量加局部案例不是完整8B部署；e1/e4不能解释成1B/4B模型；未确认与当前lane实现版本等价 |
| fable5_matvec | 当前9B系统4通道及层状态引擎 | 本地matvec案例不包含完整4通道、DDR和attention/递推状态；不能给它贴9B整系统性能标签 |
| llaccel_core | `taisirhassan/llaccel`，commit与本地记录同为 `f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5` | 16-bank存储体与外部DRAM控制器不在core内；本地布线/LEC证据不补足其存储容量/带宽和整模型时序签核 |

## 2. B 数怎样影响硬件数量

以下为**推导关系**，用于可行性筛选，不是性能预测。计数统一为 MAC（一次乘加），不混用“每MAC计2 OPS”的TOPS。

- **容量**：`M_weight = Σ(P_i × bits_i/8) + scales + padding`；dense/MoE均按**总驻留参数**计。若不全驻片上，SRAM只需覆盖调度的权重tile、活跃激活/INT32部分和、状态缓存、双缓冲和保留空间；其余容量由外存/主机提供。MoE总参数决定pool容量，active参数与命中率共同决定每步工作/传输。
- **状态**：普通GQA的 `M_KV = 2 × B × L × C × Hkv × d × bytes_KV + scales`；不能仅由模型B数确定。llaccel的Qwen例：`2×1×24×1024×2×64×1 = 6,291,456 B = 6 MiB`；Smol例 `2×30×1024×3×64 = 11.25 MiB`（推导值，与上游表一致）。混合模型另加固定维度递推状态；fable5的 `24+128+3=155 MiB` 是其具体布局。
- **计算**：单token、B=1的线性层工作量近似 `W_mat = Σ(K_i×N_i)`，dense通常随参与矩阵乘的参数数目增长；不把lookup embedding或未选MoE专家算入。普通attention另有约 `2×L×Hq×C×d` MAC，具体整数算法可能重复QK/归约，需按实际图计；prefill的GEMM有B×S行，attention还有随S²变化的部分，不能沿用decode利用率。
- **数量/吞吐**：若每个矩阵Block有 `a` 个MAC位置、频率 `f`、调度有效利用率 `u`，则必要条件 `N_mat ≥ ceil(r×W_mat/(a×f×u))`。这是矩阵项的下界，未包含非线性/状态引擎、依赖、争用和布线时序。多模型择一运行取各场景最大需求；并发运行需按各任务叠加、检查竞争。
- **带宽**：每条实际路径都需满足 `BW_eff ≥ r×D_path/token`；权重/状态不缓存时，增多MAC也不能突破外存瓶颈。端口峰值为 `width/8×clock×每周期传输数`，再受bank冲突、仲裁、协议、存储源和定制线路约束。主机换入、DDR、SRAM、Block间链路分别记账。

### 同精度的量级算例（全部为假设推导，不是建议定案）

仅为展示尺度，设线性层有效参数 `P_mat={0.5,3,8}×10⁹`，W8A8、B=1 decode、10 token/s；每矩阵Block为16×16、250 MHz、u=0.5，则每块有效 `256×250M×0.5=32 GMAC/s`。假设每次都从外存读取这些权重；表中不含scale、embedding、KV、激活、控制和冗余流量。

| P_mat（不是特指已验证模型） | INT8纯权重payload | 矩阵Block必要下界 | 纯权重读带宽下界 | 若每独立通道有效16 GB/s，通道数下界 |
| --- | --- | --- | --- | --- |
| 0.5B | 0.5 GB | ceil(5/32)=1 | 5 GB/s | 1 |
| 3B | 3 GB | ceil(30/32)=1 | 30 GB/s | 2 |
| 8B | 8 GB | ceil(80/32)=3 | 80 GB/s | 5 |

这里“3个矩阵Block”不意味着“8B总共只排3个Block”。若总有效外存带宽只有64 GB/s，8B纯权重一遍/步的吞吐上限已是8 token/s，增加第4个矩阵Block不能把它变成10。理想4-bit payload分别减半，BF16加倍，但scale、混合head、A/累加精度、解包和利用率必须重算，不能把本表Block数量也直接除2或乘2。

## 3. 对固定底座库存、布局与预连线的输入

**先形成各类型数量向量 `N=(N_mat,N_vec/reduce,N_state,N_mem,N_dma/control)`，再排布。** 不能把五项目的PE/lane数直接相加作为我们的Block总数；Block粒度由#41合同决定。现阶段可先做1/2/4个相同INT8矩阵Block的参数扫描，存储/端口与总资源逐项记账；这只是覆盖共享/分布/级联映射的算法实验点，不是完整LLM容量承诺，不给模型设置优先级。

| 要确定的库存/接口 | 五项目提供的具体线索 | 给布局/预连线算法的要求 |
| --- | --- | --- |
| 矩阵与向量/归约分别配置 | Gemmini/llaccel的256个位置与openTPU/fable5的512个位置都被跨层复用；还需要缩放、非线性与归约 | 算子tile映射到有限实例，输出跨层时用调度复用；记录布局距离、局部缓冲、INT32部分和搬运和回压，不能按Transformer层数复制Block |
| 存储和数据通道单独计数 | fable5 9B全片上状态方案需928/960 URAM且未过时序，换为DDR状态+缓存后降到182；这些不是计算阵列按B数扩张的结果 [F1] / [F2] | 区分容量bank、读端口复制、双缓冲和共享仲裁；把带宽大的compute↔bank连接作为布局权重，保留状态DMA通道；预连线须证明有限队列不会死锁 |
| GQA/KV重用不能只看缓存容量 | llaccel Qwen T=1024的KV容量6 MiB，但attention实际读84 MiB/步：每query head三次K与一次V；理想单次共享读6 MiB只是下界 [L3] | 在不改变已定整数语义前提下评估组内共享读取；分别输出“容量/实际流量/可达到带宽”。14倍字节差不代表14倍加速，优化要重测 |
| MoE需要pool/路由/换入能力 | openTPU的34.7B总/3.0B active模型仍受PCIe与专家槽命中率限制 | 不为每个专家永久分配独立GEMM；支持按层/专家切换和队列、共享/广播/汇聚，按trace统计热点、冲突和最坏突发；如禁止主机换入，重新判定容量是否可行 |
| attention与递推状态都是功能覆盖轴 | fable5同时有full attention及DeltaNet；OpenTallas的BF16 lane合同不能直接充当INT8实现 | 给状态算子提供持久对象、更新顺序、版本和写确认；定义我们INT8底座上的更宽累加/重定标/非线性合同，不因“支持矩阵乘”宣称支持这些完整模块 |
| 有限层定制的物理代价 | OpenTallas预算的PHY 900 B/cycle被内部64 B/cycle端口限制；本地案例的工艺/边界也各异 | 链路能力取source/port/fabric/sink最小值；输出每类端口位置、预留线轨、通孔、跨区路径和拥塞，不从RTL位宽直接认定可布、可达频率 |

执行入口仍是“真实模型配置/图 → INT8整数合同 → tile/状态/内存生命周期与流量 → 有限Block映射/调度 → Block间布局与固定预连线 → 限定层定制布线 → 功能/连通/资源/时序检查”。当前openTPU small和llaccel物理实验只验证其中的有限环节，尚缺完整LLM图降低、运行时/存储系统对接和全链路数值/性能验证。

## 4. 团队待冻结的信息

- Block同学提供：每类候选的实例粒度、INT8乘法/INT32累加及更宽状态能力、每周期吞吐/时延/频率、可用存储与读写端口、scale/打包/饱和规则、队列/握手、实际宏/引脚位置和固定内部连线、面积/时序与裕量。没有这些，不给最终Block总数。
- 团队共同决定：覆盖的功能与模型图、prefill/decode的B/S/C/输出长度、目标吞吐/延迟、模型择一或并发、是否允许DDR/主机换入、KV/递推状态精度、面积/功耗/定制层预算。采用INT8不代表scale、softmax、归约、状态也能无条件缩到8 bit。
- 在#41候选合同上将上面条件填入库存输入；算法侧并行做容量/带宽下界筛选及1/2/4矩阵Block映射，保持真实维度与缩小tile的参数对应。先验筛选通过才进入授权范围内的功能/物理实验；不把单层或小case扩展成完整模型支持声明。

## 5. 一手来源与固定版本

下列官方文件均在本轮实际读取；commit链接锁定本次证据，不能自动代表未来main。论文核对Gemmini DAC 2021原文§IV、Fig.6；其余四项目在本轮官方仓库/公开检索中未确认到与这些实现一一对应的正式论文，故以官方实现、配置和作者证据为准，不用同名论文或商业产品代替。

- **G** — `ucb-bar/gemmini@8c3f9923a44a2fe2c7930587be297d6d4f8c09ca`：[默认配置][G1]、[README/ISA][G2]；[Gemmini DAC 2021作者原文][GP]，DOI `10.1109/DAC18074.2021.9586216`。论文不同实验配置分别解释，不把流片事实和FireSim性能合并成同一实测。
- **O** — `FeSens/openTPU@506e81b1d297e22739dab5ecaeee684493d5c720`：[README性能与方法][O1]、[板卡配置][O2]、[D×MCOLS计算结构][O3]、[量化格式及MX迁移][O4]、[专家换入][O5]。README小模型测量分别绑定`e698dcd7`（2026-09-29）/`79c5707a` build B（09-30/10-01），不是本轮HEAD新测；targets当前默认m4的TMEM实现与历史build不同，不借用其新版BRAM节省解释旧性能。
- **F** — `coreyhahn/fable5_llm@5da450c006b3ad14cf1f1c229309a5128f4cbd12`：[README，标注2026-10-01][F1]、[架构/数值/缓存][F2]、[matvec RTL][F3]、[9B整数匹配gate][F4]、[平台带宽probe H9/H10][F5]。9B整数gate为build_041；R2 build_045测速；build_046/R3尚未加载，其预测速度不作实测。0.8B/2B历史运行需要各自配置，不视为9B位流兼容认证。
- **L** — `taisirhassan/llaccel@f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5`：[模型支持/权重revision][L1]、[架构][L2]、[KV流量/边界与image哈希][L3]、[整数语义][L4]。官方锁定Qwen checkpoint `060db6499f32faf8b98477b0a26969ef7d8b9987`、Smol `93efa2f097d58c2a74874c7e644dbc9b0cee75a2`；本轮没有下载权重。
- **T** — `bojieli/OpenTallas@bc254979296dc56bd625d53a4a70a969e9d1cde2`：[实现状态/缺口][T1]、[CHIP_RESOURCE_BUDGETS][T2]、[chip_design_v2输入][T3]、[Qwen模型账本][T4]、[SPEC-NUM 1.2][T5]。Qwen来源revision为`b968826d9c46dd6066d109eabc6255188de91218`；BF16和N5假设的地位分别保留，不把局部ASAP7/公开PDK结果转成N5整芯片性能。
- **R** — 项目固定main的[模块与接口报告][R1]、[总报告][R2]与[llaccel来源记录][R3]，仅用于本地案例范围/来源对应；未修改、重算或完整性审计参考包。

[G1]: https://github.com/ucb-bar/gemmini/blob/8c3f9923a44a2fe2c7930587be297d6d4f8c09ca/src/main/scala/gemmini/Configs.scala
[G2]: https://github.com/ucb-bar/gemmini/blob/8c3f9923a44a2fe2c7930587be297d6d4f8c09ca/README.md
[GP]: https://people.eecs.berkeley.edu/~ysshao/assets/papers/genc2021-dac.pdf
[O1]: https://github.com/FeSens/openTPU/blob/506e81b1d297e22739dab5ecaeee684493d5c720/README.md
[O2]: https://github.com/FeSens/openTPU/blob/506e81b1d297e22739dab5ecaeee684493d5c720/targets/ypcb-00338.toml
[O3]: https://github.com/FeSens/openTPU/blob/506e81b1d297e22739dab5ecaeee684493d5c720/docs/mxu_systolic.md
[O4]: https://github.com/FeSens/openTPU/blob/506e81b1d297e22739dab5ecaeee684493d5c720/docs/quant.md
[O5]: https://github.com/FeSens/openTPU/blob/506e81b1d297e22739dab5ecaeee684493d5c720/docs/offload.md
[F1]: https://github.com/coreyhahn/fable5_llm/blob/5da450c006b3ad14cf1f1c229309a5128f4cbd12/README.md
[F2]: https://github.com/coreyhahn/fable5_llm/blob/5da450c006b3ad14cf1f1c229309a5128f4cbd12/docs/ARCHITECTURE.md
[F3]: https://github.com/coreyhahn/fable5_llm/blob/5da450c006b3ad14cf1f1c229309a5128f4cbd12/rtl/matvec_engine.sv
[F4]: https://github.com/coreyhahn/fable5_llm/blob/5da450c006b3ad14cf1f1c229309a5128f4cbd12/evidence/qwen9b/g6/RD9_GATE.md
[F5]: https://github.com/coreyhahn/fable5_llm/blob/5da450c006b3ad14cf1f1c229309a5128f4cbd12/evidence/qwen2b/rb/RB_GATE.md
[L1]: https://github.com/taisirhassan/llaccel/blob/f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5/docs/HF_SUPPORT.md
[L2]: https://github.com/taisirhassan/llaccel/blob/f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5/docs/ARCH.md
[L3]: https://github.com/taisirhassan/llaccel/blob/f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5/docs/KV_BANDWIDTH.md
[L4]: https://github.com/taisirhassan/llaccel/blob/f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5/docs/NUMERICS.md
[T1]: https://github.com/bojieli/OpenTallas/blob/bc254979296dc56bd625d53a4a70a969e9d1cde2/README.md
[T2]: https://github.com/bojieli/OpenTallas/blob/bc254979296dc56bd625d53a4a70a969e9d1cde2/docs/CHIP_RESOURCE_BUDGETS.md
[T3]: https://github.com/bojieli/OpenTallas/blob/bc254979296dc56bd625d53a4a70a969e9d1cde2/configs/architecture/chip_design_v2.json
[T4]: https://github.com/bojieli/OpenTallas/blob/bc254979296dc56bd625d53a4a70a969e9d1cde2/configs/models/qwen3-8b.json
[T5]: https://github.com/bojieli/OpenTallas/blob/bc254979296dc56bd625d53a4a70a969e9d1cde2/spec/NUMERICS.md
[R1]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d/ref-project/llm-routing/docs/%E6%A8%A1%E5%9D%97%E4%B8%8E%E6%8E%A5%E5%8F%A3%E6%8A%A5%E5%91%8A.html
[R2]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d/ref-project/llm-routing/%E6%80%BB%E6%8A%A5%E5%91%8A.html
[R3]: https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d/ref-project/llm-routing/outputs/module-interface-report-20261020/llaccel/summary.json
