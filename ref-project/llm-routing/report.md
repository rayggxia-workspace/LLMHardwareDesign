# LLM 加速器功能级物理布线分析

**当前交付范围（2026-10-19）：按用户要求整理已完成的 OpenTallas、Gemmini 4×4、openTPU small、fable5 完整 matvec，四个项目共六个案例；llaccel 不纳入本轮结果。下文保留的早期作业状态仅为当时记录，不代表当前运行状态。最新图文统计及逐项目 UNKNOWN 功能分析见本节和交付总览，原验收限制继续保留。**

本实验回答“每层真实金属布线连接什么功能、哪些模块”，而不是用 RTL 位宽或架构图估算线长。所有已发布数字均来自本次详细布线数据库。大型源码、数据库、网表和原始日志保留在远程 `/public/home/yuzelu/project-circuit/llm_routing_analysis`；本地保留轻量报告、统计和图片。工具安装于 `/public/home/yuzelu/opt/eda`。

<!-- unknown-qualitative-start -->
## 2026-10-19 补充：各项目 UNKNOWN 单元与线网的定性功能分析

### 共同口径：UNKNOWN 是证据状态，不是一个模块

布局图中的 UNKNOWN 表示物理单元尚未可靠映射到原功能模块；线长表中的 UNKNOWN 表示网络在专用网络优先分类后，仍含无法可靠归属的端点。未知单元的个数与未知线长的比例没有直接换算关系：一个辅助单元也可能连接很长的线。

判断分三个层次：单元库可确认“它是什么门”；实际连接可确认“它服务哪些端点或最终通向哪些寄存器”；综合前后身份和层次证据才能确认“它来自哪个 RTL 模块”。下面分别写明已确认事实、功能解释与限制。所有解析视图与原主表覆盖同一批线，不能相加。

PHYSICAL_ONLY 单独包含 filler、well tap 等物理单元，不属于图中剩余 UNKNOWN。普通线长不含电源/地 special-wire 中心线，也不含标准单元或宏内部金属；这些不可见量不记为 UNKNOWN 线长。

### openTPU small：UNKNOWN cell 确认为缓冲、反相和常量单元

已确认：60,639 个非 PHYSICAL_ONLY 的 UNKNOWN cell 中，CLKBUF 系列 28,516 个、普通 BUF 系列 23,241 个、INV 系列 6,907 个、LOGIC1_X1 1,780 个、LOGIC0_X1 195 个，合计恰好覆盖全部 UNKNOWN。BUF/INV 功能由实际 Liberty 导出的模型确认；LOGIC1/LOGIC0 的模型输出分别为常量 1/0。没有在这批 UNKNOWN 中发现其他算术门或触发器类型。

定性解释：这批单元主要提供信号驱动/分发、反相及常量供给。缓冲器可能用于驱动负载、分解扇出或时序/电气修复；反相器也可能承担逻辑极性要求。具体每个单元因哪条优化规则插入，仍需对应工具日志，不能仅凭门型断定。尤其 CLKBUF 只是单元型号，不能把其全部实例认定为时钟树。

UNKNOWN 线长原为 8,428,613.395 μm（总长的 49.47%）。通过实际 BUF/INV 连接链，其中 8,188,655.375 μm（原 UNKNOWN 的 97.15%）能解释为已知模块内部端点之间、跨模块共享或顶层接口连接。剩余 239,958.020 μm 未通过这轮完整缓冲链判定，不能未经逐网核对就全部称为常量线。

与模块的关系：这类工程辅助单元可以服务 VPU、MXU、TMEM、控制或接口连接，但不因此获得原 RTL 来源。现有已解析组件包含 22,388 个不同 UNKNOWN 单元：19,080 个的已知边界只涉及一个模块，3,308 个涉及多个模块或顶层接口；其余 38,251 个未被这轮组件结果覆盖。单元覆盖率不是上述线长解析率。原布局仍保留灰色，解析后功能图是独立的连接解释。

### Gemmini 4×4：UNKNOWN 主要包含真实功能组合逻辑

已确认：43,827 个 UNKNOWN cell 按实际单元库模型分为 43,656 个组合单元和 171 个时序单元；其中透明 BUF/INV 合计 9,037 个（BUF 4,134、INV 4,903）。其余 34,790 个不能用纯缓冲/反相模型解释。匿名单元中可见 AO/OA、AND/NAND、OR/NOR、XNOR 等门，以及 1,503 个半加器类型、913 个全加器类型实例。

定性解释：这批 UNKNOWN 同时包含数据计算、条件组合、状态更新和信号驱动所需的电路，不能概括为“布局布线额外加入的 buffer”。加法器类型说明其中确有算术逻辑，但单凭门型不能判定它属于 PE 乘加、地址生成还是其他加法用途。主要障碍是综合后的匿名组合逻辑未保留足够细分层次身份。

UNKNOWN 线长原为 168,065.425 μm（总长的 95.54%）。在仅针对原 UNKNOWN 的接收端视图中，90,691.892 μm 通向单一已认证接收组，63,973.184 μm 为多个已知接收组共享，13,400.349 μm 仍有不明或不适用边界。已知去向包括计算 PE、MESH_PIPELINE、SHIFT_DELAY、TRANSPOSE 以及标签/行数队列，说明未知线不只是工程修复连线。

限制：接收端为 MESH_PIPELINE 或某个 PE，只证明它最终服务这些数据接收端，不能据此把整段组合逻辑和线长记为该模块内部。剩余无法判定的原因包括顶层输出、缺少认证的时序数据端以及悬空输出；这反映本分析边界，不能直接等同于电路缺陷。

### OpenTallas：主表为零，细分 lane 后仍有功能未知

numeric e1、numeric e4 的主表均按整个 ot_numeric_dot 模块归类，vadd8 主表按整个 ot_vector_add_unit 归类，因此三例主表 UNKNOWN 线长及布局图中的非物理 UNKNOWN 单元均为零。原始 numeric RTL 没有可直接映射成 expert/lane 子模块的细层次；不能从 UNKNOWN=0 推断每个 expert 的算术、状态、控制和连接均已分别识别。

定性解释：整模块内部线路包含该点积或向量加法实现的计算、局部状态及控制连接，不能全部称为算术线。时钟、复位、明确控制/握手与顶层 IO 已按优先级独立统计。vadd8 的结构还包含 BF16 加法流水线和 credit/FIFO 控制。

更细的 vadd8 lane 来源视图只认证了 3,524 个具名状态单元；匿名组合逻辑及未通过身份核验的其他单元不能强行分配给某条 lane。该细分视图的排他 UNKNOWN 线长为 70,292.713 μm。它可能涉及 lane 数据运算、非 lane 状态更新、握手/队列和辅助驱动等功能，但这些作用尚未逐门归属，不能用位置推断。

独立接收端视图覆盖 vadd8 全部普通网，可识别 parent 非 lane 状态和八个 lane 接收组，仍有顶层/不明边界。该视图与本报告“仅拆分原 UNKNOWN”的 Gemmini 数字分母不同，不混用覆盖率。填充与阱接触单元已从模块布局中分为 PHYSICAL_ONLY，不视为 lane 功能未知。

### fable5 完整 matvec：整体归属已知，内部职责尚未细分

主表以整个原始 matvec_engine 为边界：406,089 个 CORE 单元具有整体模块归属，普通布线 UNKNOWN 为零。另有 641,682 个 filler 和 10,187 个 well tap，合计 651,869 个 PHYSICAL_ONLY 单元；早期原始映射中的 UNKNOWN 数量不能直接拿来当作当前图中未知功能逻辑的数量。

定性解释：matvec_engine 的整体范围涵盖矩阵向量运算及实现它所需的状态、控制和局部数据搬运等电路；时钟、复位、明确控制/握手和 IO 已另行统计。属于 matvec_engine 并不意味着每个标准单元都是乘加器，也不意味着每条内部线都是乘加数据线。

当前没有需要从主表 UNKNOWN 中重新归类的线。若后续要区分具体算术单元、寄存器/缓冲、选择/控制或数据搬运路径，需要建立更细的 RTL/网表映射；不能把现有的整体已知误写为这些细功能都已解析完成。

### 证据与适用范围

本节覆盖已完成的四个项目、六个案例；llaccel 不在本轮范围。单元类型重新统计自最终几何中的实例记录，并核对各案例实例总数。主要证据：

- [逐项目 UNKNOWN 单元类型清单](unknown_analysis/unknown_cell_census_20261019.json)
- [UNKNOWN 连接分析汇总](unknown_analysis/summary.json)
- [openTPU 解析组件端点与缓冲链](unknown_analysis/opentpu/resolved_components.jsonl.gz)
- [Gemmini 实际 Liberty 单元模型](tables/gemmini_4x4_receiver_cones_v1/liberty_models.json)
- [OpenTallas vadd8 细分映射核验](tables/opentallas_vadd8/partial_lane_view/named_mapping_verification.json)
- [更新后的图文总览](index.html)

<!-- unknown-qualitative-end -->

## 1. 已完成的真实结果

三个 OpenTallas 案例均完成原物理流程验收及逐网提取，每例审核了 20 条真实网络。审核者是 Codex agent，明确记录 `human_review_completed=false`，没有冒称真人复核。数字的完整来源和跨表守恒检查见 `tables/opentallas-summary-v3/`；原验收范围见 `manifests/opentallas-final-acceptance-summary.md`。

| 案例 | 全部网络数 | 有普通 dbWire 的网络数 | 去重中心线长 μm | 过孔实例数 | 合并后线段数 |
|---|---:|---:|---:|---:|---:|
| numeric_e1_l16_tc | 7,284 | 7,282 | 10,832.402 | 42,366 | 24,455 |
| numeric_e4_l16_tc | 29,290 | 29,288 | 80,823.403 | 202,497 | 125,502 |
| ot_probe_vadd8 | 19,531 | 19,393 | 77,708.200 | 176,996 | 113,564 |

对应原路由报告的整数线长为 10,832、80,823、77,708 μm，差异均小于其 1 μm 整数分辨率；三个过孔数均精确匹配。表中线长只覆盖可见普通 dbWire，不包含尚未提取中心线的电源/地特殊布线，也不包含标准单元内部金属。

| 案例 | 完整功能模块内部 μm | CLOCK μm | RESET μm | 控制/握手 μm | 顶层 IO μm |
|---|---:|---:|---:|---:|---:|
| numeric e1 | 9,283.821 | 69.931 | 61.731 | 763.495 | 653.424 |
| numeric e4 | 71,118.814 | 98.067 | 67.178 | 4,188.304 | 5,351.040 |
| vadd8 | 68,752.733 | 5,685.178 | 1,627.555 | 102.754 | 1,539.980 |

这里的“内部”表示经过来源核对的整个功能模块，包含其局部状态与控制逻辑，不能全部称为乘加或加法算术网。时钟、复位、控制、IO 采用互斥汇总优先级，其他属性另行保留。专用网络沿实际 Liberty 定义的单输入 BUF/INV 及唯一驱动关系传播，不穿越任意组合逻辑门。

在这组具体实现中，时钟占可见中心线总长分别约 0.65%、0.12%、7.32%。vadd8 含 BF16 加法流水线与 credit/FIFO 控制，其时钟和复位占比明显不同于整数点积案例。这个差异是观测，不能单独归因于算术类型；模块状态规模、周期约束与实际布局同时不同。e4 比 e1 的总线长约大 7.46 倍，但两者周期分别为 12 ns、4.25 ns，因此不能把比值直接解释为增加 expert 数量的纯成本。

### 验收和工艺角

| 案例 | 周期 ns | 标准单元面积 μm² | setup WNS ns | hold WNS ns | DRC |
|---|---:|---:|---:|---:|---:|
| numeric e1 | 4.25 | 632.335 | +0.136856 | +0.805138 | 0 |
| numeric e4 | 12.0 | 2,603.30 | +0.0413225 | +2.36354 | 0 |
| vadd8 | 0.75 | 2,728.66 | +0.0240047 | +0.0331322 | 0 |

三个案例均为 ASAP7 RVT TT 标称库角（ORFS 名称 TC，0.7 V、0 °C），属于研究性物理实现，未执行 SS/FF 多角签核。vadd8 的 0.75 ns 是原 characterisation probe，并非系统工作点承诺。

e1/e4 保留原 mapped 和 postroute next-state ABC CEC，两案各证明 38 个输出点，未证明点为 0；原独立 unconstrained endpoint 检查、占位存储扫描和物理门槛全部通过。vadd8 历史 runner 的 PASS 表示原物理闭合条件通过，没有 numeric 的那两项正式等价性和独立端点审计，不能补称具备相同证明范围。

e1 首次作业在布线和等价性检查后，因报告路径 `relative_to(ROOT)` 不支持外置输出目录而失败。后续在新目录执行原验收尾段，未重新布线，原 139 个文件哈希均未改变。失败记录和恢复记录同时保留。

### 层次归属的可见性

numeric 的固定 RTL 只有一个真实计算 top，没有可直接映射的 expert/lane 实例子模块。主表只能归入完整 `ot_numeric_dot`。vadd8 主表归入完整 `ot_vector_add_unit`，另提供有严格名称证据的 lane 细分视图。

粗粒度主表 UNKNOWN 为 0 仅表示“属于已核实的完整模块”，不表示每个门都已归到具体 lane。vadd8 细分视图只确认 3,524 个保留名称的状态单元；匿名组合逻辑保持 UNKNOWN。全部 19,531 个网络均接触至少一个细分 UNKNOWN 端点，涉及全部 77,708.2 μm；按专用网络优先后的排他 UNKNOWN 长度为 70,292.713 μm。粗细两种视图相互重叠，不能相加。

另有独立的“接收寄存器连接”补充视图：依据实际 TT Liberty 和最终网表，追踪所有前向组合分支，遇状态单元停止；只有全部数据接收端属于同一认证组且没有不明边界，才记 EXCLUSIVE。vadd8 得到 12,782 条 EXCLUSIVE 网、46,309.208 μm；3 条 SHARED 网、5.248 μm；6,744 条 UNKNOWN 网、31,393.744 μm。全部 19,529 条普通网完整端点集合匹配，14 个代表单元独立路径复算匹配。见 `tables/opentallas_vadd8_receiver_cones_v2/`。这是接收端拓扑属性，不代表匿名单元的 RTL 来源恢复，也不覆盖或减少上述来源 UNKNOWN。

两个 numeric 案例分别只有两条 PG 网络无普通 dbWire。vadd8 无 dbWire 的 138 条网络中，两条是 PG，另 136 条普通网络均只有一个端点，未发现普通多端点网络缺失 wire 的异常。缺失线长记录为空/null，不记成零。三个案例实际均无 BLOCK 宏接口；标准单元内部金属依然不属于顶层可观测路由。

### 交付索引

- `tables/opentallas_numeric_e1/`、`opentallas_numeric_e4/`、`opentallas_vadd8/`：逐层功能、逐网逐层、模块关系、过孔、映射与异常表。
- `figures/<同名案例>/`：真实全局布局、各金属层、功能着色和关系图。细线为可读性设置了显示最小线宽，不能据截图测量金属宽度。
- `examples/<同名案例>/reviewed/`：每例 20 张最终网络图、端点表与具体审阅记录；最终图片带 `AGENT REVIEWED` 标注。
- `manifests/opentallas-extraction-final-handoff.json`：远程原始数据、轻量交付和限制的完整目录。
- `manifests/opentallas-final-acceptance-summary.md`：三个原验收 JSON、ODB 路径及 SHA256、RTL/驱动版本与门槛差异。

## 2. 其他独立项目的当前状态

下表是 2026-10-18 本轮检查时的状态；运行中作业以 Slurm 和日志为准，不能据本表称其已完成详细布线。

| 项目 | 固定提交 | 目标与进展 |
|---|---|---|
| Gemmini/openroad-demo | `cc53cb7054218d47f68225d5cabf2adcfc811ddf` | 原 4×4 INT8 MeshWithDelays，ASAP7；89109已完成详细布线，20条网络审阅完成；时序/约束限制如下 |
| FeSens/openTPU | `f237dab2f196855a59a083b1454786df8f01291f` | 原 Nangate45 small；89060 完整原流程 COMPLETED 0:0，DRC=0、天线违规=0；最终功能统计、20网审阅与正式图片交付完成；仍有 357 项最大电容违规 |
| llaccel | `f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5` | 原完整 llaccel_core v1、DMA depth 16、3 ns；89069/node3 在 CTS 物理优化后的 Kepler 比较阶段，尚无比较终态；中间时序报告存在违规 |
| fable5_llm | `5da450c006b3ad14cf1f1c229309a5128f4cbd12` | 未修改的完整matvec_engine，MAX_NG=96、ROW_W=16；89071 COMPLETED 0:0、DRC=0；统计/绘图89161与正式审阅交付89181均完成，20条完整端点MATCH并经agent逐图/来源审阅 |

### Gemmini

使用原 `//gemmini_4x4:MeshWithDelays_route`，不改变原 1 ns 约束、4×4 配置和物理选项。依赖已完整预取，Chisel 生成和实际综合均完成。其源生成器选择 BOTH dataflow、tree reduction、tile latency 1、output delay 1。实际生成 RTL 的 Mesh 下有 16 个 Tile，每个 Tile 内是计算 `PE_16`；转置器还包含同名族 `PE`，两类必须按实际层次区分，不能仅按字符串 PE 混算。

原配置启用 `SYNTH_MOCK_LARGE_MEMORIES`，但本次实际 `synth_mocked_memories.txt` 为空。19 个实际存储对象共 797 位，全部逐项对应到映射网表中 797 个具名 DFF 位；数据库无 BLOCK 宏，详见 `tables/pre_route/gemmini_inventory_summary.v1.json`。这证明存储容量和逻辑实现保留，不代替正式等价性。综合网表多数匿名组合单元已丢失细分层次，必须如实报告细粒度 UNKNOWN。

89109 已正常完成详细布线，DRC=0、天线违规=0。原报告线长 175,904 μm、过孔 468,162；实际路径提取得到 175,904.150 μm，过孔数一致。独立保存的原始数据库及47份文件见 `raw/gemmini_4x4_route02/` 与 `manifests/gemmini-route02-archive.json`。新读取器得到50,781个网络，其中50,675个有普通dbWire；106个缺失wire中104个是单端点普通信号，2个是PG，无普通多端点缺wire异常。缺失长度仍为空值。

最终数据库的48,454个实例中，4,627个具名实例已与映射/最终网表身份对应，43,827个匿名实例保持UNKNOWN。全部50,781条网均接触至少一个UNKNOWN端点；专用网络优先后的排他UNKNOWN长度为168,065.425 μm，约占95.54%。因此目前可以严谨报告具名PE、流水、延迟、转置器端点及其关系，但不能给出完整PE内部/PE之间的可加总数据线长。不能把OpenTallas整模块粒度的UNKNOWN=0与Gemmini细粒度UNKNOWN直接当作设计质量比较。

Gemmini的20个实际样本端点与最终Verilog全部MATCH，并完成逐图审阅，覆盖长网、局部短网、时钟树、复位、握手和具名PE状态输出。交付位于 `tables/gemmini_4x4/`、`figures/gemmini_4x4/`、`examples/gemmini_4x4/`。早期两项目、三项目汇总均保留为历史快照；最新六案例/四项目结果及限制见第3节。

补充的完整端点集合核验也对 20 条样本网全部 MATCH，证据为 `examples/gemmini_4x4/netlist_endpoint_fullset_crosscheck.json`。该检查比较整网所有端点，不只检查已列出的端点能否在最终网表找到。

Gemmini 还使用自身实际 FF 库建立接收寄存器连接视图：全部 50,779 条普通网完整端点集合匹配，以 4,627 个具名状态单元为锚点，得到 EXCLUSIVE 32,865 网、90,707.024 μm，SHARED 14,055 网、63,973.184 μm，UNKNOWN 3,859 网、21,223.942 μm。27 个代表组合单元的独立前向路径复算全部匹配。逐网、逐层统计及图位于 `tables/gemmini_4x4_receiver_cones_v1/`。其 MESH_PIPELINE 接收组可见线长为 72,726.807 μm，16 个 PE 接收组合计 8,454.191 μm；这些数字表示网络最终通向的接收组，不能称为该模块内部线长。共享网络没有重复分给各 PE，主表中原 RTL 来源 UNKNOWN 仍维持原值。

现有互斥主分类将UNKNOWN置于TOP_IO之前，因此Gemmini主表TOP_IO为0，不能理解为没有IO布线。补充的 `tables/gemmini_4x4/top_io_view/` 依据实际BTerm列出359条顶层端口网络：357条有普通wire，另2条PG中心线缺失；可见总长1,458.320 μm，包含时钟/复位/握手端口。这是与主表重叠的端口视图，不能再次加到175,904.150 μm总长上。

原流程采用 FF Liberty、1 ns 时钟。使用相同版本工具与原约束，对未改变的最终 ODB 补做 OpenRCX 提取和 STA，生成 DEF、最终 Verilog、SPEF 和路径报告，见 `runs/gemmini-postroute-report02/`。实际时序单位为 ps，setup WNS −306.04 ps、hold WNS +16.19 ps、setup TNS −94,249.03 ps；check_setup 另报告 123 个输入端口缺 set_input_delay、233 个输出端口缺 set_output_delay。因此这是详细布线完成但原目标 setup 未闭合、IO 约束不完整的研究样本，不能声称签核通过，也没有放宽原约束。原 ODB 分析前后哈希一致。

使用全量审计 PASS 的 `orfs-26Q1-repacked.sif` 和独立 Bazel 缓存。解包树在上游 RUNPATH 修改之前也完成逐文件校验，随后原 patcher 改动的工具 ELF 和 55 个 Scala 源文件均另有来源记录。Bazel 自动修改的 MODULE.bazel.lock 已保留前后版本和差异，不能把整个仓库称为干净。见 `manifests/gemmini-repacked-provenance01/`。

原 26Q1 OpenDB 接口没有公开 getId；只读探测证明新版本读取器可读取同一数据库，最终实例数、网络数、DBU、die 和标准单元尺寸与原读取器一致。统计已固定新读取器并绑定最终 ODB 的 SHA256，物理流程和补充时序分析仍保留原工具。

### openTPU

原作业 89060 已正常完成全部 finish 流程，退出码 0，耗时 2:04:31。详细布线在第 13 轮优化后达到 DRC=0，天线违规=0，路由器报告线长 17,037,728 μm、过孔 4,275,855；独立逐路径提取与其核对的结果见下文。116 份最终数据库、DEF、Verilog、SDC、SPEF、原报告和生成配置/宏模型已独立归档至 `raw/opentpu-small-v1-final01/`；最终 ODB SHA256 为 `5669c5b381122471dd13c7ccff86853a70dd198ece2f1029bdd90b2a990b1df7`。89150 已完成提取，实际最终 DBU=2000、标准单元尺寸与选定 LEF 一致。记录见 `manifests/opentpu-small-v1-final01-archive.json` 和 `manifests/opentpu-small-final01-acceptance-v2.json`。

原 2.5 ns 约束下，最终 setup WNS=+0.0632476 ns、hold WNS=+0.025126 ns，两种 TNS 均为 0，但最大电容违规仍有 357 项，因此不能声称完整电气签核通过。原约束将端口 setup 相对虚拟时钟计时，并通过 `set_false_path -hold` 排除输入/输出端口 hold 路径；上述 hold 结果不证明被排除端口。原报表的整体 fmax 受虚拟时钟影响，648.162 MHz 不能当作核心频率；单独的 core_clock 指标为 410.382 MHz。

独立只读审计 89153 已完成：加载原最终 SPEF、SDC 和原日志指定的实际库，复现时序和 357 项电容违规；确认时间单位为 1 ns、电容单位为 1 fF，`check_setup` 在原例外约束下输出为空。ODB、SDC、SPEF 分析前后哈希均未变化，未重新修复、布线或调整约束。最终记录为 `manifests/opentpu-small-final01-acceptance-v2.json`，轻量原始报告为 `tables/opentpu_small_acceptance/`。空 `check_setup` 报告不证明被排除端口的 hold，也不等同形式功能验证。

最终数据库含 1,914,787 个实例，其中 1,290,010 个填充单元、22,599 个 tap、33 个宏、109,073 个时序单元。含 fill 的面积与功能逻辑面积不能直接比较。原 GDS 生成显式允许 `fakeram.*` 空单元，FakeRAM 仍只提供边界/时序模型，没有因此获得 SRAM 内部晶体管或金属版图；统计也不能将其内部布线按零处理。

首次独立几何提取 89150 已完成：760,910 条网络中 655,374 条有普通 dbWire，去重中心线总长 17,037,728.705 μm、过孔 4,275,855 个。过孔数与原报告精确一致，线长差 0.705 μm，低于原整数报告的 1 μm 分辨率；未据此猜测原程序是取整还是截断。105,536 条缺失 dbWire 的网络经逐条检查，其中两条为 PG，其余 105,534 条普通信号都只有一个端点，未发现多端点普通网络缺线。证据为 `manifests/opentpu-small-initial-route-totals.json` 和 `manifests/opentpu-small-unwired-audit-v1.json`。

功能映射核验首次尝试 89152 因错误假定综合网表已平坦化而被断言阻止：实际 mapped JSON 保留 91 个模块，final JSON 的 top 有 602,178 个逻辑/宏实例。修正后的 v2 只沿原 JSON 中明确的实例层次构造完整单元名，再与最终网表和物理数据库精确对应，不改写连接或物理结果。失败记录保留。89158 已完成映射核验：602,178 个最终逻辑/宏实例身份匹配，其中 541,539 个得到来源功能认证。UNKNOWN 实例 1,373,248 个中，1,312,609 个是填充/tap，另 60,639 个是未能追溯来源的逻辑单元；不能把两者都解释为未知计算逻辑。证据为 `manifests/opentpu-small-final-mapping-verification-v2.json`。专用网络分类、统计、绘图、完整端点集合检查及 20 条逐网审阅现均已完成。

最终数据库中的 33 个 BLOCK 宏也已逐实例对应生成的宏清单，涉及 10 类 FakeRAM，边界模型总容量 2,109,440 bit（257.5 KiB），且全部有已知功能归属。证据为 `manifests/opentpu-small-final-macro-inventory.json`；容量匹配不证明宏内部实现或全设计功能等价。

最终功能统计已生成，实际普通走线覆盖 metal2～metal10；不能套用固定的 M1～M9 列表。排他 UNKNOWN 为 35,760 网、8,428,613.395 μm（总线长约 49.47%），接触未知端点的属性视图则为 57,492 网，两种计数口径不同。已认证单元数量较多并不代表所有网络均可完整归属：新插入/改名单元会使关联整网保守落入 UNKNOWN。当前结果没有按几何位置猜测这些单元的功能。

对全部 UNKNOWN 网络再次逐网核验发现，最长 20 网只占 UNKNOWN 线长的 0.4255%，因此高比例并非少量极端长网造成。驱动 master 为 BUF_X1/X2/X4/X8/X16/X32 的 22,131 条 UNKNOWN 网络合计 6,155,813.065 μm，占 UNKNOWN 线长约 73.03%。例如最长网 `u_slice/u_vpu/net47399` 的驱动为未通过源身份认证的 `place47400/BUF_X8`，还有多个未认证缓冲负载。此处只报告实际驱动 master 和身份缺口，不凭名称前缀将其重新归入 VPU。证据为 `manifests/opentpu-small-unknown-length-concentration-v1.json`，主分类保持不变。

已认证内部线长中，VPU 为 1,862,035.560 μm、MXU 为 1,767,364.710 μm、Sequencer 为 1,365,133.195 μm；时钟为 933,657.695 μm，复位为 59,981.715 μm，明确控制/握手为 179,270.450 μm。恰好连接两个已知功能模块的普通网络合计 457,429.895 μm，其中 ACT_RAM–MXU 约 282,682.51 μm，TMEM–VPU 约 42,461.87 μm。这里只计可确认的网络，不代表这些模块之间全部互联，也不是按模块物理边界裁切的线长。正式交付在 `tables/opentpu_small/`、`figures/opentpu_small/`、`examples/opentpu_small/reviewed/`；`*_pre_review` 为保留的历史快照。

20 条样本网的全部端点与最终网表均 MATCH；已逐图检查其功能标签和金属几何，并把观测写入 `manifests/opentpu-agent-review-notes.json`。样本覆盖九类已知模块内部网、两模块/多模块网、宏接口、时钟、复位、仲裁握手及 UNKNOWN。握手样本网 597573 沿六级 BUF 回溯到 `gnt[2]`，原 RTL 明确定义 `G_VPU=2`；复位样本网 446444 沿 BUF–INV–BUF 回溯到 `srst`，保留反相信息。宏写掩码网 660431 和高扇出网 693899 的实际库函数为常量 1，不能将其解释为数据、时钟或复位。正式图明确标注 agent 审阅且非真人签核。

依据实际 BTerm 的补充 IO 视图共有 1,322 条网络，可见总长 263,571.630 μm，4 条缺少普通 wire。该视图包括专用端口并与主表重叠；主分类中没有 TOP_IO 行不等于没有 IO 布线。轻量交付共 73 个文件、约 8.08 MiB，本地已逐项核对 SHA256；另 24 项较大表格或原 PENDING 图片保留远程，位置和哈希在 `manifests/opentpu-small-light-delivery-v1.json`，没有把远程完整数据裁减成轻量样本。

早期 floorplan 实测 618,922 个实例：596,290 CORE、33 BLOCK 宏和 22,599 CORE_WELLTAP。依据原 RTL 和实际层次建立 MXU、VPU、Sequencer、DMA、TMEM、ACT RAM、Quantizer、Collective、slice 顶层逻辑的初始映射，记录在 `manifests/opentpu_small_mapping.v1.json`；正式统计使用上述已经过最终数据库身份核验的 v2 映射。

`manifests/opentpu_small_mapping.pre_route.v2.json` 进一步根据实际 RTL 声明记录外部存储、sequencer/unit、仲裁及 collective 的握手和使能根网，以及源码明确声明的单元复位根网。注册后的复位是独立的源码根网，不是把复位属性任意穿过寄存器传播。最终仍须核对这些名称是否保留，并仅沿实际 Liberty BUF/INV 连接扩展专用网络。

`points` 显示值和生成配置存在差异：生成的顶层参数未传 COLL_GATHER，RTL 默认 1，实际网表确有 g_coll.u_coll。本次记录真实生成配置，未中途改参数。FakeRAM 宏仅可见边界接口，内部存储金属不可见，不能与 fable5 全部逻辑展开的存储直接比较。

### llaccel

保留原全核心 RTL 和物理配置。新 Yosys 内置 read_slang，因此仅从生成脚本移除过时的 `plugin -i slang`，原文件及 diff 均保留。没有缩减计算逻辑。当前已经完成综合、全局和详细放置，继续原流程；中间时序修复报告仍有 hold 违规。原 3 ns 约束未放宽，不能从活跃进程或中间阶段宣称最终布线或时序成功。

布局前实际数据库含 895,641 个实例、1,106,481 条网络。将保留名称逐一与实际综合网表对应后，8 个源码功能块共确认 85,278 个实例，另 810,363 个实例保持 UNKNOWN；其中包含匿名组合逻辑和物理辅助单元。一个未能精确对应的 `u_gemm.a_tag` 单元已明确排除，未按名称相似度猜测。该视图只表示已保留的层次证据，最终数据库须重新验收，见 `manifests/llaccel_mapping.pre_route.v1.json` 和 `tables/pre_route/llaccel_inventory_summary.v1.json`。SRAM bank 存储位于该核心边界之外，不能声称本设计包含 bank 内部金属。

独立RTL测试89207使用相同固定提交的251文件源码快照，未修改原RTL/测试，已在6分13秒后以FAILED 1:0结束。GEMM两种fusion各500项检查、DMA 120项、xbar 10,011项、Attention/KV_WRITE 724例、HALT 12种场景均通过，DRAM仲裁深度1/4/64分别通过。失败来自两处编译兼容问题：系统目标的SIMILARNAME告警规则不被Verilator 5.042识别，vec目标的测试常量`1 << 31`进入uint32_t初始化列表触发GCC窄化转换错误。这些原失败保留，不写成数值计算失败或通过。工具为Linux Verilator 5.042、GCC 11.4.0，与项目声明的Darwin工具组合不同。

独立兼容复跑89208已COMPLETED 0:0（26秒）：新目录只删除无效告警屏蔽并将测试常量写为`1u << 31`，所有计算RTL不变；原两处文件及SHA/diff明确保留。系统真实引擎集成在fusion=0/1各60项检查通过，数学单元12,000组操作数零失败，向量1,203例零失败。其覆盖包括DMA队列、GEMM→QUANT→存储、KV_WRITE/Attention、HALT及重复启动。独立源码对照确认原测试251文件均与物理工作树相同，两次测试及物理工作树的28份SV/SVH逐文件一致。这不是完整LLM模型验证或布线后网表仿真，不代替89069的形式比较终态。证据为`manifests/llaccel-functional-repro01-result.json`、`llaccel-functional-repro02-result.json`、`llaccel-functional-source-comparison-v1.json`及`tables/llaccel_functional_validation/`。

### fable5_llm

本任务新增 Nangate45 ASIC 配置，原 matvec_engine.sv 未修改，保留 128 条 W4A8 乘法通路、归约/缩放、输入输出握手与 98,304 位激活存储。3.334 ns 是新增探索约束，非原项目提供的 ASIC 签核结果；未启用大存储 mock。

本次综合实际产生 394,146 个标准单元，其中 111,699 个 DFF，面积 983,940.65 μm²。mem.json 中激活存储被重组为2个字、每字49,152位（size=2、width=49152）；实际映射网表确认 98,304 个不同 x_mem DFF Q 输出，见 `manifests/fable5-matvec-synthesis-memory-inventory.v2.json`。该证据证明容量保留，不代替功能等价性。

原测试台和数值参考保持不变。tb_matvec 的基础数值、非分块 ping-pong 和 bank 案例通过，但 `+pingpong +chunk=3` 未满足“预加载最后一字时仍 busy”的重叠断言：三次预加载只有两次满足。具体是在 K=1024 的 vec_s1 运行期间预装 vec_s4 的 512 字，末字写入时 busy=0。失败没有被跳过、放宽或从报告删除。

独立 tb_matvec_ng 通过 NG=1/2/3/4/32/36/48/64/96、四种随机种子、间隙/分块/连续/混合形状和越界自检。它不抵消上述重叠条件失败。最终应区分数值验证、并发要求和物理实现各自的证据。

fable5 原作业 89071 现已 COMPLETED 0:0，耗时3:07:48。最终 `6_final_lec` 比较 `1_synth_lec.v` 与 `6_final_lec.v`，在17:39:30报告 UNSAT/IDENTICAL；更早的 `4_rsz_lec` 也报告相同结论，223,991 个比较输入、223,450 个比较输出全部匹配。这里把 DFF 的 Q/QN 作为组合比较输入、D/CK 作为输出，是物理网表的比较边界，不等于原始 RTL 的端到端验证，更不消除测试台的重叠断言失败。两次比较的实际输入网表、YAML及日志均已归档。llaccel 89069仍在 CTS 阶段运行 `4_rsz_lec`，尚未返回结论。

fable5最终 ODB SHA256为 `72d2965352c6ddfcc47f99581f26126706d18cde3ceb3eaeab2ad167e75af173`，远程归档 `raw/fable5-matvec-v1-final01/` 包含80个文件。原详细布线报告DRC=0、天线违规=0、线长7,624,305μm、过孔2,825,388。原3.334ns约束下setup WNS +1.13133ns、hold WNS +0.0850418ns，两者TNS=0；仍有54项最大电容违规，不能描述为完整签核。最终实例1,057,958，含111,699个时序单元，BLOCK宏为0，存储以逻辑实现。

归档/提取89160已成功完成，读取513,833条网络，其中403,161条有dbWire；实际中心线总长7,624,305.845μm，与路由报告整数口径一致。缺少普通dbWire的110,672条网络已由89174逐网核验：110,670条为单端点普通网络，另2条为带特殊布线的PG网络，各有1,057,959个端点；未发现多端点普通网络缺失dbWire的异常。缺失几何仍保留为空，不能记作零长度。证据为 `manifests/fable5-final-unwired-audit-v1.json`。

独立只读STA作业89162也成功完成，原ODB/SDC/SPEF哈希不变，`check_setup`未输出问题。`report_checks -unconstrained`本次输出包含受约束路径，不能以其文件非空推断存在未约束路径。最终身份核验认证406,089个CORE实例属于完整matvec_engine；651,869个UNKNOWN恰为641,682个填充与10,187个tap单元。该映射粒度是完整模块，不声称恢复模块内部全部算术功能。轻量验收与STA原报告见 `manifests/fable5-matvec-final01-acceptance.json`、`tables/fable5_matvec_acceptance/`，16份文件共129,629字节，均已与远程证据哈希逐一核对。

统计/绘图89161已COMPLETED 0:0，生成43张图；实际普通中心线2,181,331段，总长7,624,305.845μm、过孔2,825,388。按互斥主类：完整模块内部6,875,333.315μm、CLOCK 691,247.550μm、RESET 3,350.425μm、显式CONTROL_HANDSHAKE 4,562.635μm、TOP_IO 49,811.920μm。普通有线网络没有UNKNOWN端点；2条含未知填充/tap端点的PG网使用特殊布线，中心线指标为空。这是单一完整模块范围的归属，不代表细粒度算术来源全部恢复；跨模块对表为空有明确设计边界原因，不补造子模块。

独立顶层端口视图覆盖647条网络、50,928.095μm，其中2条PG没有普通dbWire。该视图包含时钟/复位/控制端口，与主类重叠，不能与主表相加。20条最终样本完整端点均MATCH；agent查看5张联系表覆盖全部20图，并核对源码、实际Liberty缓冲链和端点master。样本包括10级BUF/CLKBUF链上的时钟分支、由x_we延伸的写使能、经过CLKBUF_X1但属于rstn的复位分支、x_waddr[11]地址输入，以及x_mem逻辑实现的Q输出和D输入短网。DFF附近的引脚bbox中心不一定落在可见走线上，已明确作为显示锚点处理。

正式审阅/导出89181已COMPLETED 0:0，最终审阅清单SHA256为 `9c7ec168e0ccece0f409bcc9701771554f92de8164551ef65ab81107d5c9f0c7`。本地交付71个文件、约6.59MiB，全部逐文件SHA256核对；24项大型逐网表、映射、原PENDING图片等仍保留远程。索引为 `manifests/fable5-light-delivery-v1.json`；正式样本在 `examples/fable5_matvec/reviewed/`。所有审阅均标注Codex agent，human_review_completed=false。

## 3. 独立项目的横向分析

最新六个案例、四个独立项目的逐网守恒汇总在 `tables/routed-summary-four-projects-v1/`，89182已COMPLETED 0:0。该汇总只证明所列统计的来源与守恒，`completion_claim=false`仍保留，不替代整体任务完成审计。比较指标、六案例层分布及fable5分类热图在 `tables/four-project-layer-analysis-v1/`。早期三项目快照和openTPU功能热图仍保留在原目录，避免用新文件覆盖历史证据。

| 项目/案例 | 工艺 | 可见中心线总长 μm | 过孔实例 | 第 2、3 层线长占比 | 时钟线长占比 |
|---|---|---:|---:|---:|---:|
| OpenTallas numeric e1 | ASAP7 | 10,832.402 | 42,366 | 91.19% | 0.65% |
| OpenTallas numeric e4 | ASAP7 | 80,823.403 | 202,497 | 71.03% | 0.12% |
| OpenTallas vadd8 | ASAP7 | 77,708.200 | 176,996 | 78.05% | 7.32% |
| Gemmini 4×4 | ASAP7 | 175,904.150 | 468,162 | 80.60% | 4.10% |
| openTPU small | Nangate45 | 17,037,728.705 | 4,275,855 | 68.53% | 5.48% |
| fable5完整matvec | Nangate45 | 7,624,305.845 | 2,825,388 | 80.56% | 9.07% |

这些是不同物理实现的观测，不是性能或布线效率排名。OpenTallas使用TT库，Gemmini使用FF库，openTPU使用Nangate45 typical加FakeRAM模型，fable5使用同一Nangate45 typical但激活存储以逻辑展开；周期、die尺寸、计算规模和存储边界不同。openTPU的die边长约2,811.955μm，Gemmini为120.387μm，OpenTallas三个案例为44.680～88.739μm。相同层号并不意味着相同线宽、pitch、RC或资源容量，物理长度也没有按节点缩放成人为统一值。

**完整matvec的局部与端口布线。** fable5的模块内部中心线约82.32%位于metal2/3，时钟网络约33.32%位于metal4/5；主类TOP_IO约57.27%位于metal5/6。真实样本同时包含1.93～4.48μm的激活存储DFF局部连接和超过1.7mm的模块内部多端点网络，说明“内部”不等同于“短线”。fable5的普通信号UNKNOWN线长为0来自整个单模块的边界定义；它不能与Gemmini细粒度的95.54%或openTPU子系统级49.47%直接比较为来源恢复率，也不能用这些比例证明架构效率。

**局部计算与存储/跨模块互联的差异。** 在 openTPU 已认证子集中，MXU 内部线长约 78.88% 位于 metal2/3，VPU 内部约 88.95%；TMEM 内部则约 52.17% 位于 metal4/5。恰好连接两个已知模块的网络中，metal6 占约 26.98%，metal8 占约 9.32%，其分布明显不同于已认证 VPU 内部网。真实案例也显示 TMEM 宏读出线经高层横纵段连接远端选择逻辑，MXU 的权重 FIFO 输出跨较长距离到达负载簇。这支持“本次实现中的宏边界和跨模块互联较多使用较高金属层”的描述；不能证明这些层是唯一可行方案，亦不能推广为所有 LLM 加速器的固定规律。

**数据与专用控制网络不能只按走线长短区分。** openTPU 已明确标记的控制/握手线约 93.59% 位于 metal2/3，但仍有接近 1 mm 的仲裁握手样本网。时钟线在 metal2～5 间分布，采用独立缓冲树；未获得 RTL 模块归属的 CTS 单元仍可通过实际连接确定其时钟类别。相反，样本中的常量写掩码线超过 1 mm，长度和扇出均不能用于猜测信号功能。

**共享网络必须单计。** openTPU 的 `coll_cmd[160]` 同时到达 Sequencer、slice 顶层和 Collective，主表只计一次 MULTI_MODULE_SHARED；模块关系图记录多个出现关系，不把整网线长重复分配。Gemmini 的接收端补充视图中，SHARED 线长为 63,973.184 μm，也没有被复制到各个 PE 接收组。局部与共享互联的比较必须说明使用的是整网几何、接收组关系，还是已追溯的 RTL 来源。

**归属完整度限制了能回答的问题。** OpenTallas 主表按完整模块归类，UNKNOWN 为 0，不能据此宣称细粒度算术来源全部可知；Gemmini 细粒度主表 UNKNOWN 线长约 95.54%，openTPU 子系统主表约 49.47%。三者粒度不同，不能比较为“识别准确率”或设计质量。Gemmini 当前不能严谨给出完整 PE 内部/PE 间的可加总来源线长；具名寄存器接收组视图补充了连接关系，但没有改变这一限制。openTPU 中保守未分配的缓冲网络也未强行回填到模块对。

推荐先看 `layer_length_shares.png` 的总体层分布，再看 `opentpu_function_layer_shares.png` 的分类内分布和各项目真实物理图。热图每行按该类别的自身线长归一化，类别总量不同；标签保留一位小数，极小的非零值可能显示为 0.0，精确值以对应 CSV 为准。供电特殊布线、宏内部和标准单元内部金属不纳入这些中心线百分比。

## 4. 统计口径与复现方法

实际使用 OpenDB dbWireDecoder 路径点。相同网络、相同层、共线区间取并集，防止共享主干或重走边重复计长；不同网络不互相去重。线段定义为最大连续共线区间，不等同路由器内部 segment 数。过孔按位置、类型、名称和层对去重，计实例，不计 cut 矩形数。PATCH 保留真实矩形，不用面积反推线长；虚拟连接不计物理长度。

多模块关系表非加和。只有恰好连接两个已知模块的普通网络才将整网线长记入该模块对，此值不声称是几何上切出的跨边界部分。多模块或不可归属的共享网络单列，不能复制给多个模块对再相加。宏接口表由真实 BLOCK*/CORE* master 类型决定，是主表的重叠视图。

PG 的 dbSWire SBox 几何已保存，但中心线/过孔计数尚缺失，空值不等于零。分层网络数不能跨层相加得到唯一网络数；汇总脚本直接读取逐网 ID 并检查长度、过孔与分类 CSV 守恒。

原始坐标保留 DBU。OpenTallas 的 1× LEF、BUFx2 270×270 DBU、DFF 1404×270 DBU、M1 宽 18 DBU 和 1000 DBU/μm 相互吻合，物理倍率为 1。其他镜像与最终数据库需要单独验证，不能因名称 ASAP7 就统一再除 1000。

Nangate45 的布局前核验使用实际选用的 `NangateOpenCellLibrary.macro.mod.lef`：DBU=2000，BUF_X1 的 1140×2800 DBU 对应 0.57×1.4 μm，DFF_X1 对应 3.23×1.4 μm，倍率为 1。轻量证据为 `manifests/nangate-physical-units-floorplan.json`。准备好的最终提取流程会对每个最终 ODB 再独立核验尺寸，并使用实际 Nangate45 typical Liberty 解析 BUF/INV，不沿用 ASAP7 的单元库。

提取器真实 ODB 往返 fixture 检验了分叉、重叠并集、过孔、patch、虚拟连接、缺失值及多模块去重；宏接口 fixture 检验同网多个宏和单元不会重复计量。合成 fixture 只是算法验证，不计入项目结果。详见 `scripts/EXTRACT_ODB.md`、`scripts/PLOT_ROUTING.md`。

## 5. 工具与执行环境的证据边界

使用 c64/node3、c64/node4、c96/node14 三个节点，实测各约 503 GiB RAM；按 Slurm 分配 CPU 并共享节点。长期任务不占 debug 的 30 分钟队列。计算节点无外网，依赖由登录节点预取。实际容器运行器为 Singularity CE 4.3.4，不描述成 Docker daemon 执行。

原 OCI blobs 摘要均有效，但首次 OCI→SIF 转换的三份镜像存在内容差异。三份独立重建 SIF 现在均通过全文件树审计，原失败镜像和历史 attempt 保留。OpenTallas 与 Gemmini 使用已认证重建镜像。

openTPU、llaccel、fable5 已在原 current SIF 启动，继续保留活跃计算；它的七项已查明差异是 GCC Python 调试辅助、五个 CMake 文档和 pandas 测试文件，完整审计没有发现其他对象内容差异。实验绑定其实际 SIF SHA，不声称旧 SIF 与 OCI 完全相同。后续只读提取使用重建镜像并另记工具版本。

current OpenROAD 版本字符串为 unknown，二进制 SHA 为 `0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53`；不能用未提供的版本号补写。Gemmini 原工具为 OpenROAD `26Q1-1961-g63ed2e0fe5`。镜像、来源和适配的完整清单见 README 与 manifests。

## 6. 模块接口与交付验收

`tables/module-interfaces-v1/`补齐六案例的模块类型、层次实例、端口声明、方向、位宽及实际子实例连接。Gemmini使用原canonical RTLIL，vadd8使用原源码的辅助层次/process解析，其他案例读取原mapped网表；均未重跑物理实现，也未据此填补主统计的UNKNOWN。Gemmini可见46种模块、142个层次实例，其中计算PE_16和MacUnit各16个，转置器内另有16个不同类型的PE；统计同时包含存储包装和验证模块，不能把所有实例称为计算单元。openTPU可见91种模块、114个层次实例，包含33个宏。

独立ODB端口检查89205已COMPLETED 0:0：OpenTallas e1/e4/vadd8分别235/430/414bit，Gemmini357bit、openTPU1320bit、fable5完整matvec645bit，共3401个非供电顶层端口位，名称与方向全部对应实际最终数据库；每案例另有2个PG端口。e1的单bit expert_enable保留为物理expert_enable[0]，差异明确记录。Gemmini有18个未连接子模块输出，openTPU的1251bit pf输出显式未连接；声明位宽保留，连接宽度为0，不填造网络。证据为 `manifests/module-interface-portcheck-v1.json`。

远程交付审计89203核验873份保留工件约6.19GiB，覆盖六份最终ODB、逐网/几何数据、主统计表、真实图像、物理门槛与既有120条agent审阅的绑定；七个固定源码检出和三个实际镜像另行复核。证据为 `manifests/remote-deliverable-audit-v1.json`。八个主要物理作业的Slurm记录确认使用node3/node4/node14，长期作业均在c64/c96，node3确有32+16+8+8核任务并行共享；详见 `manifests/main-physical-jobs-resource-audit-v1.json`。

当前版本提取器又通过89206真实合成ODB跨进程写入/读取测试：原始750 DBU取共线并集后650 DBU，500 DBU多模块/宏接口重叠视图不重复加到主表，过孔实例、patch、虚拟连接和缺失值均按既定口径检查。7份测试源码已快照，记录为 `manifests/extractor-current-validation-v1.json`。这仍是算法验证，不是新增项目结果。

OpenTallas新后处理入口分别在e4/vadd8完成独立再提取，89201/89200成功；各六张CSV与原基线字节一致，20条完整端点检查均MATCH。按顺序执行的复现说明见 `REPRODUCE.md`，逐项要求与证据见 `REQUIREMENTS.md`；新增复跑不增加独立项目数量。

## 7. 剩余完成条件

已为llaccel原作业安排依赖后处理：89209仅在89069成功退出后归档并提取；89210统计/绘图、89211独立STA均要求89209成功。三者均使用c64/node4，归档8核，后两者可共享16+4核；等待依赖期间不占计算节点。217份现有脚本/配置/工具输入已固定哈希，每阶段执行前后核验；不修改原物理流程、不跳过Kepler，也不会自动将20条新样本标为已审阅。提交记录为`manifests/llaccel-final01-postprocess-submission.json`。排队只表示后续步骤已安排，不表示最终结果已产生；若上游失败，须保留失败证据并处理不再适用的依赖作业。

四个独立项目的真实统计、每项目至少20条agent审阅、实际物理图和跨项目分析已经形成。llaccel须跟进原流程到真实终态，记录形式检查、DRC、时序和功能验证边界，若成功则继续同样的统计/审阅流程。固定Bazel依赖重建、三个Nangate45案例的新attempt准备、独立归档复跑及验收已验证；Gemmini新工作树/输出缓存的依赖预取已成功完成，89183已完成原4×4目标的独立物理复现，89191/89192按afterok依赖完成新归档/STA/统计。最终ODB、55份Scala源码、五张主要统计表与原基线一致；综合网表仅两处src属性的Bazel路径改变，其他文本相同，STA指标也一致。比较证据为 `manifests/gemmini-reproduction-comparison-v1.json`。新自动样本20条端点全部MATCH，未自动标为已审阅；主交付保留原基线已审阅样本，不增加独立项目计数。

Verilator 5.042已从固定源码包在新opt前缀实际重建安装，89189 COMPLETED 0:0，123个安装文件及输入哈希全部复核。独立fable5功能复跑89184保留原始5592个源码文件，tb_matvec再次触发原pingpong分块重叠断言，make返回2；tb_matvec_ng通过，总作业FAILED 1:0。所有输入前后保持一致，形状测试通过不消除原失败。轻量证据为 `manifests/verilator-5-042-repro02-verification.json` 和 `manifests/fable5-functional-repro01-result.json`。新增安装、功能验证和Gemmini后处理命令已写入README。

新安装的Verilator又用于独立测试89194，同样复现tb_matvec失败、tb_matvec_ng通过，所有输入保持不变。四项目六案例的本地交付身份核验已完成，120条既有agent审阅的样本、端点证据和图片哈希均匹配；该次审计本地约105.74MiB，后续新增接口表不到1MiB，没有大型物理数据库或工具镜像。复现步骤、逐项要求核对和当前远程交付审计已形成；仍须等待llaccel真实终态并完成对应结果/失败说明，最后更新整体完成结论。运行中、失败、仅综合或全局布线的项目不计入成功数，形式检查不以等待超时替代结论。

先前时间线和失败诊断另存 `manifests/report-history-before-opentallas-complete.md`。本报告按当前证据整理，不用历史准备状态覆盖最新实测结论。
