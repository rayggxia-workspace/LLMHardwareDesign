# 首轮 VECTOR Block 硬化与顶层集成记录

- 日期：2026-10-21（中国标准时间，UTC+08:00）。
- 任务：[Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)。
- 交付：[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)；初始脚本快照 `7e9bde5b763b19591dcbe4f49ade7b08ef093843`。
- 候选划分与后续对照：[实验计划](openTPU-llaccel-block-plan.md)。
- 复跑入口：`project/experiments/block_hierarchy/run_vec_pilot.py`；大体积输出保留在集群 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/`。

## 本次验证对象

使用 llaccel 原提交 `f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5` 的完整 `vec_engine`，保持 16 路、原整数数值规则、操作集合、FIFO／拆分／归约／开方／除法、握手和响应状态，不裁成单个算术单元。原 core 对 `u_vec` 没有参数覆写；独立 elaboration 保留原配置。原声明接口为 26 个端口、2,246 个 bit，这不是最终物理 pin 数，也不是同时发生的数据流量。

独立 Block 采用 Nangate45 研究平台、3 ns 周期及 0.6 ns 输入／输出延迟作为工程预算假设。本轮已导出的综合／floorplan SDC 未显式设置外部驱动单元、输入转换时间或输出负载，因此还不是完整边界电气模型。没有声称这是完整 llaccel 系统重新签核的约束。SRAM bank、共享 crossbar、其他引擎、DMA 与 DRAM 不在该独立 Block 内。

本次尝试的步骤为：原 RTL 的完整 VECTOR 解析 → Block 独立综合／布局布线 → 从实际阶段导出 LEF 与时序模型 → 顶层以单个真实宏实例引用该实现、冻结位置再连接。Block 内部可以展开，顶层不得重新综合宏内部。直通 shell 是工程集成验证对象，不能替代真实的跨引擎通信图。

## 执行记录

| Attempt／作业 | 实际状态与含义 |
| --- | --- |
| `vec-screen-01`／89441 | 失败：计算节点没有从作业环境找到 Singularity；保留原日志，没有产生有效宏或物理结果 |
| `vec-screen-02`／89442 | 筛查通过：修正显式工具路径后，原完整 VECTOR 的 RTL 解析通过；确认镜像中的层次支持入口，不将网上最新变量直接当成镜像能力 |
| `vec-harden-01`／89443 | `TIMEOUT`，45:00；已完成综合和放置，停在 stage 4 修复前后 Kepler 门级 LEC 的 solver；未得 LEC 结论，未完成 CTS 或布线。Slurm `ExitCode=0:0` 不能覆盖 `State=TIMEOUT` 和时限终止日志 |
| `vec-top-01`／89444 | 运行前取消，原提交与状态保留；没有产生顶层结果 |
| `vec-top-02`／89445 | 依赖 89443，因依赖失效自动取消；未执行顶层实现 |
| `vec-harden-resume-01`／89447 | `FAILED`，约 10 秒，`2:0`；父作业及输入身份检查通过，但 `make -n finish` 因尚未执行阶段应生成的 SDC 副产物缺失而失败；没有继续物理流程。保留日志，恢复检查需改为核对首个待执行阶段 |
| `vec-harden-resume-02`／89448 | c64、16 CPU；实读 `TimeLimit=UNLIMITED`，保存调度快照；身份与首个待执行阶段的 dry-run 通过，实测直接接续 CTS、没有重跑综合；终态待回填 |
| `vec-top-03`／89449 | c64、16 CPU；实读 `TimeLimit=UNLIMITED`；`afterok:89448` 等待 Block 完成，尚无顶层物理结果 |
| `vec-regression-01`／89452 | `FAILED`；c64、8 CPU、实读 `TimeLimit=UNLIMITED`；GCC 11.4 编译 `tb_math.cpp` 的 `uint32_t edge32[]` 时拒绝 `1 << 31` 的 narrowing，未执行运行期案例；日志与 fail JSON 保留 |
| `vec-physical-01`／89453 | `COMPLETED 0:0`，33:03，c64、16 CPU、`UNLIMITED`；同源 89443 checkpoint、身份与 dry-run 通过，接续 CTS，完成 ORFS `finish`。显式 `LEC_CHECK=0`，不继承其他作业的等价结论；路由几何检查通过，3 ns setup 预算未满足 |
| `vec-physical-top-01`／89454 | `FAILED 2:0`，1:08，c64、16 CPU、`UNLIMITED`；成功导出最终宏抽象并通过端口检查，顶层综合后在 PDN 阶段报 `PDN-0006`：metal7 的 VDD 接入被宏在 metal8／metal9 的 OBS 阻断；未完成顶层布线 |
| `vec-regression-02`／89455 | `COMPLETED 0:0`，17 秒，c64、8 CPU、`UNLIMITED`；独立测试副本仅做无符号位常量兼容修正。JSON `status=pass`：VECTOR 1,203／零失败、12 组全过、数学 12,000 组／零失败、16,384 组舍入检查通过 |
| `vec-physical-top-02`／89456 | `FAILED 2:0`，8:09，c64、16 CPU、`UNLIMITED`；新详细 OBS／M10 配置通过 PDN 生成与 DRT（错误 0），但最终 PSM 报 M8／M9 短接及 `PSM-0069` 连通失败；POST 最终检查未执行，不构成顶层验收 |
| `vec-physical-top-03`／89457 | `FAILED 2:0`，3:27，c64、16 CPU、`UNLIMITED`；从已提交快照 `da059f906a74d344547c9faa6cb59571638fd126` 启动，显式 `guarded-m10`；早期 VDD／VSS 均返回 `PSM-0069`，分别报告 43／22 处短接；未推进 CTS／布线，bloat1 未解决原短接 |
| `vec-pdn-audit-01`／89459 | `FAILED 1:0`，4:16，c64、1 CPU、`UNLIMITED`；在新目录只读 89456 的终态 ODB，VDD／VSS 均正确报 `PSM-0069`，分别 43／22 处短接，错误报告 hash 与89457相同；是成功识别坏网格的负向复核，目标顶层仍为失败 |

综合阶段记录了 259,349 个标准单元，标准单元面积为 460,078 µm²；这是 `1_synth.json` 的阶段指标，不是最终宏面积或制造占地。后续修复、时钟和布线还会改变资源。

同一 attempt 的 `flow/reports/nangate45/llhd_vec_original/base/synth_stat.txt` 给出更具体的资源证据：顺序单元共 4,117 个、面积 20,268.136 µm²，占该阶段总面积 4.41%；另有 43,094 个 `FA_X1` 全加器与 15,802 个 `HA_X1` 半加器。因此不能将该完整 VECTOR 的规模主要归因于宽 FIFO。源码的两只 256 bit × 4 深度读响应 FIFO 合计只有 2,048 bit，映射网表中的 2,048 个 `DFF_X1` 恰保留在这两只 FIFO 的存储命名下；其余顺序资源另含控制和流水。算术单元映射后已大量匿名化，不能据这些门的数量再把面积精确分摊给某个 RTL 算子。该观察只用于解释当前配置的综合资源，不证明换粒度、缩减 lane 或复用算术单元能保持同一吞吐及接口行为。

本轮代码初次运行时尚未提交。运行器、配置和源输入的 SHA-256 用于绑定实际执行快照；事后保存的项目代码 commit 见页首与 PR 回执。各 attempt 之间确有版本差异，实际身份以各自的 `runner-inputs.sha256` 为准，不把基线仓库 commit 或某一后续快照冒称为所有作业的精确执行版本。[轻量结果索引](../../project/experiments/block_hierarchy/results/issue-7.json)收录各作业、工具与输入身份、阶段指标及远程日志路径。镜像已记录 SHA-256，OpenROAD 版本字符串为 `unknown`；实际二进制哈希可核对，未推断其版本号。

按用户后续明确指示，撤销早期试跑的人工运行时限。集群实读 c64、c96 的 `DefaultTime=NONE`、`MaxTime=UNLIMITED`；后续提交不设有限时长，并读回作业实际 `TimeLimit`。上述 45 分钟超时与已终止恢复作业仍属于真实历史，不删除或改写。

默认完整检查路线 89448 的阶段门级 LEC 为单个 KISSAT miter 求解，无分区进度输出，进程仍在计算；尚无通过结论。为并行验证后续物理流程，89453 从同一个终态父作业另开目录，仅为 make 显式加入 `LEC_CHECK=0`，不改变 RTL、SDC、放置或修复参数。89448／89449 原输入不改、继续无限时运行。物理路线复制得到的历史 LEC 日志标为继承日志，不能当作本 attempt 已执行或通过的检查；即使另一路随后通过，也须先证明被比较网表身份相同，才能讨论证据复用。

## 实际 Block 路由结果

89453 已生成最终 `6_final.odb/v/sdc/spef/gds` 和计算节点输出哈希索引。以下来自该作业的实际 ORFS 报告；属于单角研究平台检查，没有额外重放独立 STA，也不等于 foundry 签核。

| 项目 | 实际值与判断 |
| --- | --- |
| 详细布线 | `5_2_route.odb` 与收尾指标均产生；DRT 错误从初始 57,736 经迭代降至 0，`5_route_drc.rpt` 为空；天线 net／pin 违例均为 0。该计数只覆盖本次工具及平台规则 |
| 块内线长／过孔 | DRT 阶段工具统计线长 6,798,427 µm、过孔 2,193,396；不是顶层跨 Block 布线量 |
| 最终 setup | 最差 slack −4.16659 ns、TNS −1056.05 ns、287 个 setup 违例，**未满足 3 ns 预算** |
| 最终 hold | 最差 slack +0.0253833 ns、TNS 0；仍须结合覆盖及电气检查判断，不据此宣称系统签核 |
| 电气 | 最终报告 max-capacitance 违例 59 个，max-slew／max-fanout 违例均为 0；**电气验收未通过** |
| 最终资源 | 报告非 filler 面积 524,749 µm²；非 filler 实例 321,725，含 tap／时钟／修复等。另有 411,821 个 filler，因此总实例 733,546 不能当作活跃计算单元数；最终宏 footprint 按实际导出 LEF 另列 |

最终 `flow/reports/nangate45/llhd_vec_original/base/6_finish.rpt` 的最差路径仍为 `u_f0.rp[0]$_DFFE_PN0P_ → wr_data_r[187]$_DFFE_PN0P_`，是同一时钟上升沿寄存器间的 library setup 检查，arrival 约 7.62 ns、required 约 3.45 ns、slack 约 −4.17 ns。GRT 同一路径约 −4.19 ns。该证据说明块内部已有预算瓶颈，不能仅凭端点名称把全部延迟分摊给某个算子或跨块接口；也不能与原完整 core 的最坏 recovery 路径直接比较来归因分块代价。报告按该角计算的 `period_min` 约 7.17 ns／139.54 MHz 是工具时序摘要，尚不代表完整系统可用工作频率。

同一工具报告给出 VDD worst voltage drop 0.688493 V、VSS rise 0.629844 V，两者最坏位置并不配对，不能相加。最终 `6_report.log` 明确打印 `Total power : 2.27e+01 W`；这是 22.7 W 的工具模型结果，不是把 Liberty 的 nW 单位误当 W。只读核对实际镜像配置后，确认其使用 VDD 1.1 V／VSS 0 V，未指定外部 `vsrc` 或覆写 source 类型，因此沿用 Tcl 的 `BUMPS` 默认；未追溯该二进制的 C++ 默认 bump 尺寸／间距／外部电阻。该流程也未载入 VCD／SAIF 或显式活动，工具帮助给出的输入默认活动为每最小时钟周期 0.1 次转换、占空比 0.5，再结合库模型传播。核对记录保存在远程 `psm-policy-observation.txt`，没有另跑电源分析。当前结果是严重的默认模型供电警示，不能当作真实应用功耗或供电实测，也没有将电源完整性标为通过。几何 DRC 为零不能覆盖这些时序、电气与电源问题。

## 宏抽象与首轮顶层结果

89454 的生成日志确认载入 89453 的最终 ODB／SDC／SPEF，抽象输入哈希与 Block 输出索引相符。LEF 尺寸为 1148.52 × 1148.52 µm，footprint 约 1.31910 mm²，区别于标准单元面积。原 26 个端口、2,246 个信号 bit 及方向全部保留，另有 VDD／VSS；实际宏模型与原声明端口检查通过。

独立审读最终网表与 Liberty 得到 765 组 setup／765 组 hold 弧、363 组 clk→output 弧及 7 组组合弧，相关表格非空且数值有限。最终网表有 766 个与 cell 相连的输入（含 clk）；其余 810 个输入在固定参数优化后未连接 cell，也没有模型弧。307 个无弧输出均由 tiecell 直接给常量，363 个动态输出均有时钟弧。这里依据最终产物分类，没有用原 RTL 的候选统计代替物理证明。

Liberty 不包含 `minimum_period` 检查，只含时钟树路径信息，因此父级时序报告不能自动覆盖块内部寄存器间的失败。端口齐全、时序弧存在与“该宏能按 3 ns 使用”是不同结论。[独立审读记录](../../project/experiments/block_hierarchy/results/issue-7-abstract-audit.json)保存输入哈希、交叉计数、限制与顶层实际验收状态；它不代表额外重跑 STA 或完成源 RTL 到物理网表的形式比较。

该 Liberty 也没有有效的 `internal_power`／漏电／宏电流或活动模型；仅有单位与标称电压元数据。因此父级 PDN 的几何连通检查可以独立验收，父级 IR-drop 结果则不能替代包含完整宏电流的电源完整性分析，更不能覆盖上述 Block 内部的 PSM 警示。

首轮顶层在供电网生成时失败。默认父级 PDN 的跨层连接与宏的实际 PG 引脚／整层阻挡发生冲突，不能用跳过 PDN 或删掉实际阻挡来制造成功。该 attempt 的输入和失败日志保留；后续在全新 attempt 中核对真实供电接入方式，暂不宣称顶层冻结、信号布线或接口最终验收已通过。

89456 在独立 `macro-view/` 中读取同一最终 ODB，执行实际镜像支持的 `write_abstract_lef -bloat_factor 0` 导出详细 OBS；这保留真实几何，区别于原视图的整层 cover。该选项的含义可对照 [OpenROAD 官方 API 文档](https://openroad.readthedocs.io/en/latest/main/src/README.html#abstract-lef-support)，运行行为仍以本次镜像日志为准。新 LEF 约 397 MB，2,248 个 pin（含 PG）、全部引脚几何和宏尺寸与原视图匹配；Liberty 为原已审模型的逐字节副本，来源仍指向 89454 的最终 SPEF 抽象日志，未冒称本作业重做时序提取。

父级新配置保持外围供电层，并增加 M10 条带；宏 grid 尝试对既有 M7 PG 引脚建立到 M10 的 via stack，不在宏上新铺 M5／M6。M8／M9 的真实阻挡保留。这是 H1 的新供电资源和抽象视图对照，尚非 H2。89456 的 PDN 日志仍有 VDD 1.5%／VSS 1.3% 局部阻挡告警，三处各移除 4 个 via；没有独立 failed-via 报告不等于零失败。

89456 虽完成顶层 DRT、计数为 0，但最终 PSM 明确报 `PSM-0043`：`u_vec` 的 M8／M9 与 VDD shape 短接，随后 `PSM-0069 Check connectivity failed on VDD` 使作业失败。`VDD.rpt` 保存短接坐标。因此路由器的几何计数不足以证明跨层供电接入安全，最终宏位置／信号接口的 POST 检查也尚未执行。后续修复须审查 via stack 的中间层 landing 与宏内真实金属，不能关闭 PSM 或删除阻挡来通过。

独立坐标审读发现 43 处短接（M8 21 处、M9 22 处）均与同层真实 OBS 有正面积交叠。计算节点的只读 ODB 诊断进一步定位到首例：via 中心 `(477.07, 758.40)` µm 在 OBS 外，但 2×2 via7 array 的 M8 landing 为中心 ±0.62 µm，右边达到 477.69 µm；实际宏 OBS 从 x=477.495 µm 开始，两者交叠与 PSM 报告完全匹配。另一 M9 示例的中心本身已经落入 OBS，不能将全部 43 处都泛化为同一种 enclosure 问题。候选接入点的中心与整块 landing 均须检查。

89457 使用独立 `guarded-m10` 视图，由同一 ODB 请求 `bloat_factor 1`，原 pin／尺寸／Liberty 保持身份校验，父级供电布局参数不改。实际读回发现，该参数未按预期扩大致错的 M8／M9 OBS：首例 M8 仅拆成几个矩形，原边界不变，M9 原矩形仍逐字相同，不能把文档参数含义当成已经形成有效保护。早期 VDD／VSS 检查均报 `PSM-0069`，本方案未修复短接。

在实际镜像已核实的 POST_PDN hook 中，于写完成 ODB 之前严格要求 VDD／VSS 检查均无 Tcl 错误且返回真，同时检查宏两只 PG ITerm 的网络。89457 两个 ITerm 归属正确，但几何连通检查失败，流程正确停止在此门槛；没有仅凭网络名正确而通过。成功、失败均保存 JSON／日志／输出哈希。后续应调整实际 PG 接入几何并独立复核，不能盲目增大抽象 API 参数。

镜像默认 PDN 脚本注释了 `check_power_grid`；新增 `pdn-audit` 模式用于在独立计算作业读取顶层 ODB，显式检查 VDD／VSS 连通和宏 PG ITerm 的网络，记录报告存在性。实际镜像的失败反例已在独立诊断中验证抛 Tcl error，失败没有被成功退出掩盖；审计同时检查命令返回值，不能把 `pdngen` 完成当作连通通过。

## 原实现的时序背景

本轮还定向读取了远程已有的 `llm_routing_analysis/runs/llaccel-v1-sta-final01/`。其 `audit_manifest.json` 记载使用原 `6_final.odb/sdc/spef`、Nangate45 typical 库、原约束和例外，且未修复或放松约束；OpenROAD 二进制哈希与本次镜像实际程序一致。既有 `run.log` 报告 `worst slack max=-4.44 ns`、`worst slack min=+0.01 ns`、`tns max=-8038.83 ns`。这是读取已有报告，未在本轮重跑该独立 STA，也未重新核对其全部输入。

其中最坏路径示例包括 `rst_n` 到 ATTENTION 寄存器的 recovery 检查；不能把上述最大延迟 slack 笼统解释为某条 VECTOR 算术路径的延迟。该背景表明原 3 ns 全 core 结果本身也不能当作时序闭合基线。新 VECTOR 若出现负 slack，仍须建立相同功能、包装、约束和实现阶段的 F0/H1 对照，不能把差异直接归因于 Block 划分。

## 验证及证据边界

筛查的 `hierarchy -check`、`check -assert` 等检查属于 elaboration／结构检查，不证明 RTL 与软件参考等价，也不证明新网表或路由后功能正确。原功能仿真、形式比较及独立全系统 STA 没有因本次选择了相同源码而自动完成。

本轮独立 `tb/vec` 回归 89455 已通过，随机种子为 1、未减例数：六种 VEC 操作在 0%／30% 拒绝授权下各 100 例及三个定向例，共 1,203 例零失败；原数学测试的 12,000 组输入和 16,384 组舍入检查均通过。测试比较 `numerics.h` 参考和完整 1 MiB 行为 SRAM，并检查请求保持、写载荷、busy/done/tag 及原地操作。使用 Verilator 5.042、容器 GCC 11.4；工具及测试源哈希、完整日志和机器可读结果保存在独立 attempt。首试 89452 编译失败，不能计为运行期通过；89455 仅在独立测试副本将上述位常量明确为 `1u << 31`（仍是 `uint32_t 0x80000000`），记录兼容修改前后哈希和 diff，原始 archive、RTL 与数值参考头文件不改。此项只覆盖原 RTL、单指令及行为存储，不代替综合／物理网表等价、真实 SRAM、完整 core 或路由后验证。

后续按实际生成阶段记录 Block 产物、顶层的真实宏实例及位置、LEF／Liberty 是否来自最终路由、是否读入 SPEF、实际未布通与 DRC、setup/hold 报告、约束覆盖和失败项。工具退出为零、DRC 数字、某项 WNS 和整体签核是不同证据，不互相替代。

普通 H1 流程允许顶层常规 CTS／修复新增有源单元。本项目 H2 的固定底座验证还需冻结这些资源，声明定制金属／通孔／接点集合，并验证多个真正不同的计算图。当前单 VECTOR pilot 不提供后加工制造、预埋轨道收益、多计算图覆盖或能耗／成本优势结论。

## 后续实验

1. 用同一功能与相同接口包装建立 F0 扁平对照，先隔离硬宏边界带来的面积、端点、时序与布线代价。
2. 扩展到 llaccel 的完整引擎粒度 L0，保持原共享存储请求语义；独立 VECTOR shell 的结果不能外推为完整 core 的结果。
3. 对 openTPU 实施 ACT／MXU 分离与合并的同资源物理对照，复用已有 128 bit 链路的行为证据，补物理实现与活动／功耗，不重做同一轮等待注入扫描。
4. 从成功的 H1 实例建立冻结底座和受限定制 H2，最后检验至少两个实际不同的通信需求；各阶段分别报告失败和适用范围。
