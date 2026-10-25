# Issue93 实际 gamma streaming RTL 的物理验证准备

日期：2026-10-25；操作者：Liangruizhi（认证 login/ID182389313 已读回）。本文件为只读准备，不是实验结果；本轮没有启动 EDA、Slurm、RTL 或张量计算，没有安装工具，没有修改项目工作树、Issue88、成员55/63或 ref-project，没有创建/修改远端任务。Issue88 发布由主代理负责。

## 1. 当前资格与来源

结论：现有服务器材料足以开始**实际 Issue93 网表的研究库逻辑区域布局和线长 RC 估计**；也有 CTS、global/detail route 与 OpenRCX 的脚本及研究工艺输入，可在前级通过后分阶段执行。尚不能进行真实 SRAM 集成签核，更不能宣称设计可制造。

依据：
- Issue91 `docs/BLOCK_LIBRARY_ACCEPTANCE.md` 和 `docs/V_S_INTEGRATION_CONTRACT_V1.md`，读取分支 `task/91-v-integration` @ `034fe463ebdae85361bdd8e7cf473548c92e6b8a`。L2 实际 RTL、L3 物理资格与 L4 六块集成必须分开。
- Issue92 报告，读取分支 `task/92-epoch-boundary` @ `55a2b3e153d15f569ab8d58a617f698a30e810ff`；其中最终实际计算源码 `71824cc8bbe0fe53b0b770abacd1b74e6f1b942c`，禁止 epoch 回绕，reset/abort 的 cfg 接收及终止态迟到应答已修订。
- Issue93 最新正文和评论已保存于 `github-readback.json`；查询时 updated_at 为 `2026-10-25T04:37:51Z`。本轮尚无冻结的93实际 RTL commit，不得预填其通过状态。
- Issue88 @ `62ff8f64f63e735048b3326e6db6aec90c9e5a5c` 只为84静态核心建立了研究库、无寄生、理想时钟的电气证据；不能传递到92/93。

93 必须保留：8个S8乘法、一个S32乘法、一个U128 SFU、16KiB/128bit/1RW；H2560用X/Y10KiB、gamma1KiB、frame512B、A4KiB，共15872B，512B空洞不能免费充当缓冲。H1536是六个真实M完整消费者回归，H2560当前仅全行归一化；不能改称 H2560 M 或全模型验证。全H同一sum/den，gamma流式且有限信用，所有新增控制/标签/描述符/mux计费。

## 2. 已存在的工具与物理输入

路径缩写：
```
D=/public/home/yuzelu/opt/eda/cache/bazel-repacked/0472cb7817e9c4d6e974e10cde266a63/external/bazel-orfs++orfs_repositories+docker_orfs
F=$D/OpenROAD-flow-scripts/flow
P=$F/platforms/nangate45
```

| 输入 | 当前证据 |
|---|---|
| OpenROAD / OpenSTA | 既有88验证过 OpenROAD 26Q1-1961-g63ed2e0fe5 / STA3.0.0；可执行在 `$D/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/`；通过既有SIF和显式loader调用，本轮未再次启动 |
| 工艺/单元LEF | `$P/lef/NangateOpenCellLibrary.tech.lef` 与 `NangateOpenCellLibrary.macro.mod.lef` 已存在 |
| Liberty | `$P/lib/NangateOpenCellLibrary_typical.lib`，TT1.10V/25℃，ns/fF/kΩ；与88使用库同SHA；不是多PVT库组 |
| Site | `FreePDK45_38x28_10R_NP_162NW_34O` 的实际尺寸 **0.19×1.4µm**，不得由名称推断 |
| 时钟单元 | CLKBUF_X1/X2/X3 在Liberty中存在；后续还须将选用单元与LEF精确求交，不因函数名假定可布线 |
| RC/轨道 | `$P/setRC.tcl`、`make_tracks.tcl`、`fastroute.tcl`、10金属层 `rcx_patterns.rules` 均存在 |
| PG/物理单元 | `grid_strategy-M1-M4-M7.tcl`、tapcell.tcl、FILL/TAP/tie标准单元；如采用需计面积/站点/布线占用，非免费资源 |
| GDS/研究DRC | `gds/NangateOpenCellLibrary.gds`、`drc/FreePDK45.lydrc`、CDL存在；`$D/usr/bin/klayout`存在，但本轮未启动核验其依赖或运行能力 |
| LVS | 平台配置指定 `lvs/FreePDK45.lylvs`，实际不存在；因此不能声称LVS条件齐备 |
| SRAM | 有fakeram研究lib/LEF，但没有已验证匹配本项目16KiB/128bit/1RW时序与语义的真实宏；fakeram不得充当目标宏证据 |

平台 `README.md` 明确该库为研究/测试用途，**purposely non-manufacturable**，版本 `PDKv1.3_v2010_12.Apache.CCL`。即便完成其布线与DRC，也不构成可制造资格。

RC口径：`setRC.tcl` 用signal metal3、clock metal5。M3 R=0.00357728kΩ/µm、C=0.103981fF/µm；M5 R=0.00149065kΩ/µm、C=0.109256fF/µm。此为既有研究平台估计，不能宣称目标工艺实测或foundry signoff。实际布线后改用同平台OpenRCX规则生成SPEF，并保留两类数值，不能混写。

## 3. 建议冻结的首轮实验配置（未执行）

只测**一个已通过 L2 的实际93候选**，优先观察其真实控制/互联代价；不重复84四版本。需要旧方案对照时另从实际92重做同条件物理流程，且限共同合法H1536范围；不能用88结果填92基线，也不能跨不同功能H2560做面积收益比较。

| 项目 | 固定建议及原因 |
|---|---|
| 核心面积 | 399×399µm，2100个site宽、285行；die `[0,0,448,448]`，core `[24.51,25.2,423.51,424.2]`，原点及尺寸对齐0.19×1.4site。这个新研究floorplan不是88名义400×400无布局结果的延伸 |
| 容量上限 | 最终功能/时钟/修复标准单元area≤79600.5µm²（core50%）且符合实际合法row容量；tap/fill/PG占用另报告并扣实际可放置站点。不能只保留≤80000而忽略合法行容量 |
| Place density | 显式0.50；平台默认0.30不应静默继承。所有对比保持同floorplan、pinmap、density、资源和约束；若不够则失败/新候选，不单独扩大某版 |
| S宏切分 | 暂沿用精确store wrapper cut：逐bit固定端口/方向/常量及排除边界，不删除debug/错误/epoch接口。切出的SRAM信号作为逻辑区域边界IO，不声称真实宏placement、clock或访问timing已通过 |
| 时钟/IO | 研究预算10ns；uncertainty0ns、clock/input slew0.05ns、IO max0.1ns/min0ns；输出负载1fF及10fF均独立报告。这是复用88的明确预算，不是目标芯片需求。CTS前理想时钟，CTS后传播时钟分列 |
| 上游驱动 | 初轮固定输入波形，逐bit列fanout/sink cap和新buffer树；不宣称实际输入driver已闭合。需要BUF_X? driving-cell敏感性时另列明确假设，不继承ABC任意3.898fF负载冒充真实环境 |
| 引脚 | H-metal5/V-metal6；确定一次有序bus/控制/cut-pin布局并保存其DEF/SHA，在候选间复用。实际IO数量可能导致pin或拥塞失败，这是结果，不能删接口过关 |
| 路由 | signal M2–M10，clock M4–M10；平台容量调整M2/M3=0.50、M4及以上=0.25；使用真实tracks，不因拥塞临时开放更多层或取消预留 |
| 随机性/并发 | 保存工具实际支持的seed/线程数与资源；首轮固定8CPU线程、独立目录，一次一个布局/时序测量，其他非性能分析可并行。先记录工具支持选项，不能把未支持的seed参数写成已生效 |
| 优化界限 | 首次先不修复、保存基线；如需要则每批准阶段至多执行一套预先冻结的 electrical→hold→electrical 配方，保留全部中间残留；禁止无限反复或自动改时钟目标。每次新增buffer/resize/CTS单元全部计费并重核功能 |

注意：切分后的存储接口被放到区域边缘，会改变引脚密度和通信距离。这一配置仅回答逻辑区域在明确边界负载下是否可布局/收敛；不能回答真实SRAM在中心或邻侧时的完整核面积/布线/延迟。后者依赖宏LEF/Liberty和位置。

## 4. 最小阶段及接受门槛

### P0：93源码和功能资格

冻结93源码commit、参数/环境/输入/库SHA。实际RTL通过H1536六例完整M和H2560全行norm，独立bigint逐元素sum/den/gamma/Y核验、backpressure/abort/restart/reset/epoch/旧tile/地址alias/canary/信用上界；接收检查fail closed。逐项区分真实张量与合成边界、H2560norm与M。

导出实际93映射网表，列总库存及新增mux/控制/描述符/标签/holder；真实gate replay不能只跑84/92。映射后store cut需要独立检查全部边界bit、DFF与cell连通性；完整门级replay使用独立参考而不是RTL自身结果。零线寄生STA作为本93基线，不用88数字。

### P1：固定floorplan、布局与 placement RC（最小可独立执行）

1. `read_lef` tech+cell、`read_liberty`、`read_verilog` actual93cut、`link_design`，读被冻结SDC。
2. `initialize_floorplan` 使用上表面积/site；source `make_tracks.tcl`，冻结pinmap；如采用PG/tap，严格记录实际插入和可用容量。
3. 用显式脚本控制 `global_placement`、`detailed_placement`、`check_placement`，source `setRC.tcl`，`estimate_parasitics -placement`。
4. 输出DEF/ODB/netlist/SDC、HPWL、面积/每类cell/所有FF及新缓冲、拥塞估计、逐输入负载、所有setup/hold/电气与coverage报告；将零RC与placement RC分栏。
5. 如需修复，按照预冻结有界配方，并重做同函数buffer/resize结构证书及关键完整gate replay。不得引入额外算术/FF/端口来悄悄改变资源比较。

平台 stock `global_place.tcl` 默认timing-driven=1且会 `remove_buffers`；必须显式禁用该自动删除和flop clustering，或重新提供覆盖该变化的证明，不能套88的原cell保留证书。stock flow的buffer_ports也必须明确开关并计费。

P1通过只说明声明条件下逻辑区域可布局/估计RC；不等于CTS、详细布线或全SRAM路径时序通过。即使setup不通过也须保留有效布局与失败路径，不能给出合格Fmax。

### P2：CTS 与 global-route RC

P1证据有效后，固定root/leaf CLKBUF单元白名单、sink聚类和缓冲距离、clock routing层。执行 `clock_tree_synthesis`、合法化；所有时钟buffer/resize/必要反相器计入面积与输入负载。将clock设propagated，报告clock sink覆盖、skew/insertion、setup/hold及reset约束覆盖。只允许透明clock树变换；若工具clone功能逻辑需新的等价证明，不能按buffer放行。

应用平台fastroute的层/容量，`global_route` 后 `estimate_parasitics -global_routing`。保留stock脚本默认repair_design/repair_timing/power recovery的显式禁用或有界版本，不允许隐藏多轮优化。`write_ref_sdc`产生的建议period仅诊断，原10ns验收SDC与SHA不变。

### P3：详细布线与提取（研究级，非本轮必须先启动）

在P2可接受后执行 `detailed_route`；`SKIP_DETAILED_ROUTE` 必须为false。必须完整路由、所有pin连接、placement合法；列全DRC和antenna违例及未布线数量。后续源码实际入口已读到 `scripts/final_report.tcl`：
```
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file $P/rcx_patterns.rules
write_spef <ownout>/actual93.spef
read_spef <ownout>/actual93.spef
```
实际Tcl以冻结路径替换变量并保存。该脚本存在fallback到global-routing估计，接收器必须拒绝把fallback当SPEF提取通过。核SPEF网覆盖、R/C总量/单位/名称匹配/未注释网，所有时序端点与原SDC匹配。参考KLayout DRC可作为附加检查，但需先只读核其运行依赖；缺LVS deck不能写LVS通过。PG电压设置不等于实际功耗向量、IR/EM资格。

## 5. 独立接收、失败定义与产物

独立接收必须校验source和原始Git字节、配置/输入/工具库/全输出SHA；逐阶段netlist、cells、ports/constants、clock/reset和存储cut完全绑定，BUF/INV链折叠后原pin函数保持，resize必须同Liberty Boolean/FF函数，未知新非透明单元拒绝。CTS/repair后的完整选定消费者gate replay不能被结构检查替代；结构检查也不能被少量样本替代。

每份报告必须有明确BEGIN/END markers、执行状态和非空summary。全DFF R2R、全部非恒定IO/cut setup与hold分别统计；列unconstrained、missingclock、falsepath/disabled arcs、全部排除理由与blackbox覆盖。输入cap、clock root负载、所有新增库存和所有电气违例计数不能缺项。

以下任一导致对应阶段不接受：功能/结构证书失败；更换精度/容量/端口或偷用额外库存；超面积/合法row容量；浮空、多driver或丢常量/接口；任何目标端点未约束且无预冻结合法理由；负setup/hold slack；slew/cap/fanout超库/冻结限制；布局非法、routing不完整、DRC/antenna残留；提取遗漏且未解释；改period或falsepath掩盖失败。工具缺失/超时属于未执行/未完成，不能冒充设计通过或设计失败。

保存完整命令/环境/Slurm资源、每阶段日志、SDC/DEF/ODB/网表/SPEF、库/规则只读路径与SHA、JSON指标、失败原件、独立接收和负例。大文件留自有授权server目录，仓库仅索引与小样本；不把宏/GDS版权材料随意上传。所有优化前后都保存，报告区分逻辑area与真实宏/布线/时钟/PG面积。

## 6. 真正需要团队提供的原则性输入

这些缺项不妨碍上述研究库P1，但会阻止真实L3制造资格、完整S宏集成或L4结论：
1. 目标可制造工艺及合法PDK访问：多PVT Liberty、tech/cell LEF、层/via规则、真实RC与DRC/LVS/signoff规则；当前Nangate/FreePDK研究平台无法替代。
2. 目标时钟/uncertainty、真实输入driver和输出负载/线路边界、reset/CDC和供电条件。10ns、0uncertainty与1/10fF仅研究预算，不能反推产品Fmax。
3. 实际S实现的16KiB、128bit、1RW宏（或明确合法bank方案）的Liberty/LEF/GDS、时序/PVT、pin电源和读写冲突语义。改变bank/latency/byte-enable后必须重新核功能与资源。没有宏时只能做明确cut区域。
4. 若下一轮接通用V，明确外置LUT/程序桥和实际延迟，或提供128KiB ROM宏；目前93没有实现通用V/A/R/D全闭环，不能拿物理流程替代缺失RTL。
5. 与成员55/63协调制造前固定/产品金属定制层与接口的实际责任边界，不复制其未交付源，也不通过主动审查ref-project补造可复现资格。

当前恢复第一步：等待93冻结L2源码/接收记录，然后独立新任务/worktree/服务器目录固定上述P0/P1配置；先核实际网表/切分/面积与必需命令能力，再提交第一条布局作业。尚未启动。

## 7. 物理输入 SHA-256

| 文件（均相对P） | SHA-256 |
|---|---|
| lef/NangateOpenCellLibrary.tech.lef | 834a79295054cd4209178d1bade67c353863c47bb4b3c22ee38b862b7cec37f2 |
| lef/NangateOpenCellLibrary.macro.mod.lef | a43aea339f12a57a63497783e508ba16f3da2dc056d3247dec7d99707c2dedef |
| lib/NangateOpenCellLibrary_typical.lib | 8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1 |
| setRC.tcl | 4c0fdc4f96c4377e15aef8fb8f8397acad62be2660afffe7cc55223535542480 |
| make_tracks.tcl | 8f8fbff8d8e0dfd232307058f6766973742e36f8f27bd1c717ea001e142cba99 |
| fastroute.tcl | 6ee39fe360a870b0dd4731a206882d2a2b6c1e54ad8612152460e36c9e95e0dc |
| rcx_patterns.rules | 2f65fafbe2c704b378563c53a680b93cef080c2799997019d43df7d1e5a563e9 |
| grid_strategy-M1-M4-M7.tcl | 13f6979391f4e5373b6e0b9e9df6f8f07f69787e970e13e5d170f830b83006db |
| README.md | 0e3c8a8cbe5429552764c6531dc454d64f6aa7c1f7128175b5f06070a3de578d |
| drc/FreePDK45.lydrc | 4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147 |

本地审查原始记录：`github-readback.json`、`platform-readonly.log`、`flow-readonly.log`、`units-flow-inputs.log`、`rcx-readonly.log`。最后日志的补充rg搜索提示server没有rg，已通过直接读取final_report.tcl核实提取命令；不声称完成所有脚本搜索。metadata_manifest.json保存这些记录和本报告的字节SHA。
