# 有约束的 Block 综合规划器（Issue #219）

2026-11-08：[状态相关成本v2](../../../work/YUZE-LU/219/STATE_COST_RESULTS.md)。`full_plan.py --read-cache --state-cost`启用部分前缀命中和显式保留策略，宽度1/8共用纯函数转移。完整3B六次回放及105项测试通过；五组/同预算不变，九组模型代价略退化，详见结果。

**2026-11-08 只读分片复用入口：** [算法与状态](DOT_CACHE.md)、[完整3B回执](../../../work/YUZE-LU/219/READ_CACHE_RESULTS.md)。`full_plan.py --read-cache` / `reuse-plan.sbatch` 生成实际Dot的有限S前缀、B/零包候选，DP将各M.S内容纳入状态并独立核对驻留与静态互斥。完整五组/九组各三输入与旧整数结果逐位一致，100项测试通过；复用贪心模型代价减少17.16%，九组DP另降26.14%伴随10→18束，同预算无额外收益。下文“全部spill”描述此前基线；本版仍不搜索一般跨层脏结果，整网控制编码与真实布线另验。

**2026-11-08 审查后入口：** [静态互斥修复与生成控制程序](../../../work/YUZE-LU/219/MUTEX_CONTROL_RESULTS.md)。`loop_dp.py` 和独立 `verify_loop_dp.py` 均检查整个产品的已选／固定静态连接互斥；90 项测试及完整 3B 计划重验通过。`control_backend.py` 登记实际 U_64 共同控制子集，生成官方编码的母控／局控镜像；`control_replay_plan.py` 在当前独立母控、真实母控程序 SRAM、两组 U_64 及实际数据 SRAM 上执行，`control_verify.py` 独立核对数值／写 ACK／源释放。当前控制后端只覆盖固定放置的小图，不是通用整网 DP→控制程序编码器。

**2026-11-08 当前入口：** [完整3B结果与边界](../../../work/YUZE-LU/219/FULL_RESULTS.md)。真实 Qwen2.5-3B 的完整 B1/S2 图已完成量化、Gather、动态矩阵/地址布局、生成整数IR的数值回放和五组/九组16KiB计划；75项测试通过。整网后端是 `wide_program.py → streaming_ir.py → loop_dp.py`：从同一份已执行原语生成原生命令循环、搬运与静态接口并集，再做有界前沿搜索和独立检查。全部原语间spill，尚未优化tile/cache；等连接预算没有整网收益，不能把“可编译”写成论文级加速。以下较早的链覆盖/CP/原生混合服务流程继续保留，历史“Gather首先阻塞整网”已由本轮修复。

完整数值回放 `wide-replay.sbatch ROOT MODEL WEIGHTS ACTIVATION_CALIBRATION LOGITS NATIVE_HEADERS`；完整规划 `full-plan.sbatch ROOT MODEL HARDWARE NUMERIC_TRACE NATIVE_QUALIFICATION QUALIFIED_PROGRAM`；单测 `test.sbatch ROOT ENV_ROOT`。均经 `work/YUZE-LU/219/launch_fix.py` 冻结并提交Slurm；具体绝对路径和收回SHA见 FULL_RESULTS。作者输入仍为模型产物、硬件清单、运行参数；校准、测量、内部IR和程序均为工具产物，无须手工维护每个算子的JSON。

```text
ONNX + 全量真实权重 + 原生能力/资源 + 执行范围
 → 规范化图/实际量化校准
 → 生成、序列化、回放整数向量循环IR（8850条）
 → 从同一IR展开有限原生命令/外存循环（1083个调度内核）
 → 候选实例/就绪任务 → 有界前沿DP（资源时间＋静态连接并集）
 → 独立原语成本/地址/资源/存储验收 → 离线图册
```

## 较早的细粒度混合服务流程

本目录替代 `block_search` 作为后续开发入口。实现了服务覆盖候选、已登记逐元素服务的自动分片、外存搬运/溢出/重读、S 的时间与地址联合分配，以及按静态连接使用者成组重映射。2026-11-07 修订：**算法评估允许零数据预连，外存使用 #182 来源的虚拟 LOAD/STORE 接口；原生 DMA、MC/LC 镜像、最终 RTL/P&R 均不是算法验收前置条件。** 已增加真实M/N/E/G/R256/T的原生命令配方、跨命令状态租约和格式转换，五类混合计划三初态回放通过；此前2048元素RMSNorm和16元素Softmax原生客户端证据保留。完整五类/LLM 算子 lowering 仍未全部实现，不能把 FP32 前端对照写成原生整网映射通过。

## 当前验收范围

算法应输出合法的服务选择、分片、时间、S 地址/生命周期、外存读写与完成依赖，以及所有待接的逻辑连接。输入硬件可以没有数据预连；计算服务内部需要的 S↔宏通路也通过 `services[].nets` 计入静态连接并集，不能只登记跨块 copy。实际已预连的路径标 `fixed`，待定制路径不标 `fixed`。同一组网跨层只计一次，静态驱动冲突不能以错峰执行规避。

已有控制 RTL 直接作为目标使用。本轮没有发现必须新增控制器或适配器的证据，代码也不会以“尚未取得整体物理验收”为理由拒绝算法输入。固定放置 U_64 小图已有可执行 MC/LC 编码与回放；任意整网计划编码及原生 DMA 仍待后续接入，不是缺硬件的结论。

`memory.py` 从冻结的 #182 `test_dma.cpp` 提取时钟、延迟、信用、有限队列和银行参数。虚拟接口保留128位字、组到通道映射、槽/队列限制、LOAD等待S提交、STORE等待外存响应。为使调度约束可审查，当前按整项描述符独占共享通道及S IO资源；同一描述符内按有限信用允许多个字在途。随机背压关闭，冷银行和方向切换规则记录在模型中；这不是 #182 逐字轮询/CDC的周期等价模型，也不是HBM器件校准。没有继承 #182 的实测GB/s作为单次搬运常数。S读/写时间来自本轮同边界的真实客户端测量（4/6周期，包含该驱动行为）。参数和结果完整保存，后续可替换模型而不重写求解器。

常规输入依旧是模型产物、同一份硬件清单和调用参数；`virtual_memory` 放在该硬件清单中。工具按实际片段长度生成路径，无需作者维护每个长度的路由 JSON。未提供物理 pin 仍可得到算法计划；输出明确区分逻辑端点需求与后续物理绑定。

## 实际算法

```text
模型产物 + 硬件清单 + 调用参数
          │
          ├─ 精确匹配格式、形状、属性、domain 和已有服务证据
          │   未登记的转换/分解 → blocked_lowering
          ▼
合法分片候选 → 链内覆盖 DP → 少量候选任务图
          ▼
快速流式初解：分配地址 → LOAD/计算/STORE → 必要时 spill/reload
          ▼
独立检查器确认合法初解
          ▼
选择一个瓶颈任务组 → CP-SAT 联合调整绑定、时间、地址和搬运
          │                   │
          │                   └─ 同一静态线的所有跨层使用者一起开放
          │                      大任务组可耦合重复绑定，限制搜索决策数
          └─ 独立检查；有改善才接受；超时保留合法初解
          ▼
映射/时间/地址/外存区域/事件程序 IR/静态网需求
```

`cover.py` 的 DP 沿不含分叉和汇合的链推进。状态为“前 k 个节点的若干覆盖方案”；每次增加一个单服务或已登记的多节点服务。只隐藏没有外部消费者的中间值，显式检查模式、格式、属性和外部操作数。DP 的排序值是服务周期之和，**只用来提出覆盖候选**。保留数量受 `--cover-limit` 限制，后续联合调度再判断实际优劣，不将这项排序值当作整网执行时间或全局最优证明。

`seed.py` 先生成一个保守串行的合法基线。输入、中间值、输出均按片段处理；同一目的 S 中的有效副本可以重复消费。优先释放死值，再选择未来较晚才用的值；脏值要真正写到外存、等 ACK，再释放 S。重新使用时产生 LOAD。原始输入、临时外存和最终输出进入同一份稳定外存区域表；提供外存容量时同时验收容量，没有容量数据则明确未取得容量资格。

`parallel.py` 对独立分支构造更好的初解：先为各私有S形成地址合法的本地执行流，再按声明的计算、S端口和外存通道资源安排重叠。同一外存输入允许显式加载到不同实例，不能因此免除流量。合并后检查静态连接预算和驱动冲突；存在跨站生产值依赖时该构造明确不适用，保留一般规划路径。当前局部对照的改善来自此构造，不归给DP或尚未求得改善的CP搜索。

`solver.py` 的联合子问题用下列变量表达，而不是遍历所有完整方案：

| 变量/约束 | 含义 |
| --- | --- |
| 每项任务的服务选择、开始/完成时间 | 同一算子允许多个真实服务/实例；资源占用用 interval、NoOverlap/Cumulative 表达 |
| 每次搬运的路径、各阶段时间 | 计算、S 端口、链路和等待确认的保持槽分别登记；源数据保留到真实目的确认 |
| 每份有效副本的地址与存活区间 | 用二维不重叠约束检查“时间上相遇且地址上相遇”的冲突；不是只数总字节 |
| 直接消费/共享副本/单独重读/spill | 同时比较保留副本和释放后重读，不要求完整张量同时进入 S |
| 静态网启用变量 | 等于所有使用该网的路由选择的 OR；跨层只计一次，但冲突驱动不能因错峰而被接在一起 |

目标是**在可选的连接预算内最小化完成时间**；证明该候选时间最优后，再固定完成时间、优化外存字数与静态代价。没有把“周期”和“线数”随意相加。计算时间来自已有服务测量；外存时间可来自明确选定的虚拟模型，不按 FLOP 猜宏吞吐。新原生 N/E 清单的连接代价单位为“逻辑通道束”，尚非实际 bit 网数、几何线长或电容。

大邻域改进同时考虑三种任务组：一条新增静态网的全部使用者、长寿命缓冲的生产/消费端、竞争同一宏或局控资源的相邻任务。组外只冻结实例绑定，全部时间仍可传播。超过 64 个任务的组，把已有相同绑定且合法备选一致的重复任务耦合成组决策；保留全部跨层使用者，未把“只改前几层”误作整条线已删除。这个 64 是搜索策略阈值，不是硬件资源数量。各次证明范围、固定/耦合绑定和 UNKNOWN 均记录；有界覆盖和局部搜索不宣称整网最优。

`verify.py` 不导入求解器，也不信任求解器输出的资源汇总。它从硬件服务和实际搬运重建占用，逐项核对数据副本来源、写确认、源释放、S 地址、外存区域、输出交付和静态网并集。小链的最优结果另与独立闭式参考对照。测试中的人工数字只用于算法正确性，不用于硬件或 LLM 性能结论。

## 输入与输出

常规作者输入仍只有模型产物、**合并的硬件清单**和 CLI/函数参数。ONNX 中保留形状、格式、状态及权重引用；不复制一份手工模型图。硬件清单含存储、资源、已登记服务、路径及物理端点约束。内部 tile IR、测量记录和输出 JSON 是工具产物，不要求用户维护更多输入文件。

本轮清单由 `native_catalog.py` / `native_rows.py` 从冻结U源码和三初态测量生成，原 `native_plan.py` 保留四项加法回归。存储字采用该接口的128-bit记录，容量由实际地址位数核对；原生ABI中固定的10位地址属于U编码器，不写进通用求解器。更换实例、容量、服务或端点后重新读清单，核心无Qwen名称或P/U/C/F/J数量判断。**硬件变化按新清单重做算法评估；若要继承物理时序签核，另补相应证据。** 不把物理签核作为本阶段算法门槛。

硬件主要字段：`sites`（S容量）、`resources`（容量/互斥资源）、`services`（op/numeric/domain、精确input_words/output_words、属性、时间、所属S、占用资源及所需静态网）、`routes`（源/目的、适用字数、完成协议、各阶段和保持资源、net ID）、`nets`、`incompatible_routes/nets`、可选`external_capacity_words`和`virtual_memory`。搬运路径可由虚拟接口生成，不要求预先物理接通；没有算子数值规则则明确是软件未完成。各服务时间归一到同一声明基准，协议完成条件明确；ABI编码可后接。

标准输出是带验证结果的计划、分片/存储/外存表、事件级程序 IR 和同一静态网集合。`emit.py` 的程序 IR **不是可部署 MC/LC 镜像**，其资源顺序和事件需要目标 ISA lowering。`native_plan.py` 另生成 #195 U 适配器字段格式的描述符并回放原生服务客户端；没有把这件事称作完整局控取指通过。

```bash
# 在本目录/Slurm 工作目录运行；依赖见 requirements.txt
python -B -m unittest discover -v -p 'test_*.py'
python -B run.py model.onnx hardware.json new-output --audit-only
# 已登记逐元素语义：自动枚举合法分片、DP 覆盖并生成计划
python -B run.py qualified-model.json hardware.json new-output --seconds 30 --rounds 6
# 调试/回归可显式输入工具内部 tile IR；不是额外常规作者格式
python -B run.py tiles.json hardware.json new-output --lowered
```

自动 tiler 已接入**同形状逐元素**和**完整 N 行统计/回放**。`native_catalog.py` 将原生 E 两种操作及N多阶段命令登记成服务；`lowering.py` 按形状生成行任务，保留共享 gamma/epsilon，N 上下文从统计开始到回放完成始终归同一实例。当前已验证2048元素 RMS 和16元素 Softmax；没有把每个分片分别归一化，也没有提前释放N上下文。超过S工作区的行仍需独立的流式配方，不能自动填补。

后续原生规则已加入 `leaf_lowering.py` / `leaf_catalog.py`：真实 M 的 K 分片与最终舍入、G 四种激活及门控、紧凑 E 算术和尺度/宽度转换、N 分阶段流式统计/回放、R256 跨片 GDN 和 T 提交/交接/释放。`contexts.py` 在内存搬运期间保留 M/N/R 的状态租约；求解器和独立检查器禁止中途迁移、覆盖，覆盖DP也不能吞掉这些边界。M原生返回四个S32槽，即使按S16饱和也不是紧凑S16；当前配方用真实E op13转换，并登记额外服务、S窗口和线路。

这些规则要求显式整数格式：`format={bits,exponent,lanes,unsigned?}`，实数值为raw×2^exponent，每128位记录的布局固定。ONNX可在metadata `llmhardware.native_formats`提供每个整数张量的格式；工具核对真实dtype。FLOAT重贴整数、免费换lane布局和隐形主机转换均拒绝。常量权重的M-B布局是显式离线配方；运行时动态B重排仍待实现。R256按已测的最多32行一片读写S，点积/更新上下文跨片保留，到整个点积结束才舍入；实际检查至256行，未使用#198的R1024扩大配置冒充R256。

`native_probe.cpp`复用#198实际整数引擎和原生驱动，紧凑E与T直接使用更新RTL。M/N/E/G/R/T逐命令与参考比较；E op13额外使用独立S32→S16 RNE参考。`native_s_io.sv`在实际P/非P SRAM叶接口测量普通访问，覆盖四银行首尾。原#198驱动首次读R时会先查地址相关ready，当前探针显式初始化合法空闲读地址，三种初态均验证；不修改R硬件。

`leaf_replay.py`从这些实际测量生成五类资源清单，编译混合图并生成原生C++回放；输入数据、N→M→G→E→T和128行R→E输出与独立完整算子参考核对。程序IR带原生命令、控制归属、状态组和地址/事件；仍不把IR称作MC/LC机器码。服务时间为实际叶命令加实际S IO的保守串行组合，标记 `integrated_lc_timing_qualified=false`，不继承组合局控时序资格。

导入的完整 Qwen2.5-3B 仍为FLOAT；新增整数规则不自动赋予FLOAT语义。完整模型仍需量化策略、动态矩阵布局、位置编码及其余图转换、KV/MoE等。该软件未完成项不能归因于缺控制器、数据预连、DMA或物理验收；本次原生混合图也不是另一个小参数模型benchmark。

## 服务器复现与证据

最新46项检查和五类混合原生回放见[叶宏规则结果](../../../work/YUZE-LU/219/LEAF_RESULTS.md)；此前34项检查、原生N/E程序、虚拟外存对照、冻结源及输出SHA和图册见 [修订结果](../../../work/YUZE-LU/219/FIX_RESULTS.md)；此前25项检查和U加法回放见 [初轮结果](../../../work/YUZE-LU/219/JOINT_RESULTS.md)。所有求解、模型和 RTL 任务均在允许的 Slurm 节点、`yzl-*` 名称及 `--time=0` 下运行。浏览器检查仅验证本地收回图册的交互。

- `environment.sbatch ROOT WHEELS`：计算节点离线安装固定依赖到自己的 ROOT/deps。9.10.4067 支持服务器 glibc；不修改共享 Python 环境。
- `test.sbatch ROOT ENV_ROOT`：算法与负对照测试。
- `qualify.sbatch ROOT`：从 #214 验收来源包复制执行源，测量并复跑真实 U/N/E/四 SRAM bank 的原始断言。
- `native-plan.sbatch ROOT ENV_ROOT QUAL_ROOT`：从测量生成图/清单/计划/描述符/测试台，三初态原生回放。
- `export.sbatch ROOT CHECKPOINT`：固定完整 Qwen2.5-3B，B1/S2 prefill，HF/ORT 三组输入；拒绝不在 3–4B 范围的正式模型。
- `audit.sbatch ROOT ENV_ROOT ONNX HARDWARE`：只做完整图导入和覆盖检查，不将未支持的 FLOAT 算子映射为 S16。

## 借鉴与未完成项

从 [CoSA](https://people.eecs.berkeley.edu/~ysshao/assets/papers/huang2021-isca.pdf) 借鉴把映射/调度写成显式约束；从 [COSMA](https://arxiv.org/abs/2311.18246) 借鉴把调度、存储地址和替换一起优化。覆盖模式来自常规技术映射/[Collage](https://arxiv.org/abs/2111.00655) 的方向。本实现使用 [OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver)，未移植上述论文实现、未继承其最优性/加速比。前瞻/局部改进与量子编译有思想联系，本轮没有调用 LightSABRE 或 TOQM，也未把距离指标当作真实搬运代价。

完整Qwen2.5-3B声明范围的分解、数值和有限循环计划已由后续整网后端补齐，见页首；其余模型、KV/MoE/GDN完整图仍需各自证据。MC/LC机器码、原生DMA系统回放、M10几何/RC和最终P&R属于后续部署/物理验证，**不阻塞本阶段算法验收**。当前局部算法对照不代表论文级整网收益。参数量小于4B也不自动授予任意算子、状态或格式支持。

本轮新增可复现入口：`native-rows.sbatch ROOT ENV_ROOT QUALIFICATION PR182_SOURCE`（原生行程序与虚拟外存计划）、`memory-evaluation.sbatch ROOT ENV_ROOT QUALIFICATION PR182_SOURCE FULL_ONNX`（16KiB、多实例/通道/信用/连接预算对照与完整模型覆盖）。均在服务器Slurm运行，具体回执见上述修订结果。收回结果后可用 `python -B project/experiments/block_synthesis/memory_report.py work/YUZE-LU/219/results/fix-v2` 生成离线图册。

后续叶宏配方复现依次执行：`native-probe.sbatch ROOT PR198_REFERENCE QUALIFICATION`、`native-sio.sbatch ROOT QUALIFICATION`、`leaf-replay.sbatch ROOT PROBE SIO QUALIFICATION PR182_SOURCE PR198_REFERENCE`。各ROOT必须是自己的新冻结目录；参考目录只读，不在原工程内编译。最后一项包含全部算法单测、混合图编译、三初态原生回放和 `leaf_report.py` 图册生成。具体绝对路径、最终作业和源码绑定见[叶宏规则结果](../../../work/YUZE-LU/219/LEAF_RESULTS.md)。
