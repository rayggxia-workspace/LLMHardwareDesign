# 架构与运行

本仓库含研究资料、参考结果和实验性分层物理实现代码。`project/experiments/` 下保留 `block_hierarchy/`、`parallel_blocks/` 和 `opentpu_compare/` 的实验及证据；正式预制底座和制造工具链尚未冻结。[项目说明 v1.0](../预制计算底座项目说明_v1.0.md) 中标注的候选架构不能当作已实现硬件。

## 研究系统边界

拟研究的流程是：目标计算图与需求 → 预制 Block 资源映射及调度 → 预埋资源选择和受限布线 → 定制互联与成本／性能／能耗评估。预制内容、制造时定制内容和运行时状态必须分别建模；工艺堆栈、端点电气合法性、存储供给与时钟网络不能省略。

## 当前计算宏与实现状态

七宏之上的[局部可定制 Block 提案](LOCAL_BLOCK_DESIGN.md)补充 P/U/C/F/J、两级控制、私有 S，以及 Qwen/Falcon/Granite 的两层流程图。它是文档设计输入，不替代下列叶宏合同，也不新增组合资格。图源/渲染重建与本地来源检查命令见[图册构建说明](local-blocks/README.md)。

当前实现分为 M/N/E/G/R/S/T。M、N（归约与归一化）、E（基础向量算术/RoPE）、G（激活与门控）、S、T 已完成300MHz叶子验收和本地实收；R 未完成，仅保留研究源码。每类合格宏只选一个实现，见[实际合同](BLOCK_V2.md)和[结果、文件及证据入口](BLOCK_V2_RESULTS.md)。规划背景仍见[边界分析](COMPUTE_BLOCK_BOUNDARIES_2026-10-30.md)。

RTL：M/N/E/G 在 `project/rtl/block_v2`；S 在 `project/rtl/block_feed_v1`，顶层 `block_feed_s_macro`，依赖 `block_feed_loader` 和 `block_feed_s16k`；T 为 `project/rtl/block_v1/transaction6k.sv`。未完成 R 为 `project/rtl/block_library_v1/block_v1_r.sv`。源码从研究分支 Git 对象原字节提取，并与已验收包的源 SHA 独立核对。

运行及验证入口在 `project/experiments/block_v2`；`block_v1` 和 `block_feed_v1` 中的复用依赖保留原路径/原算法，不能将依赖目录理解成又一套已交付宏。原研究全过程仍在 #143/PR144；本次从最新 main 独立整合，不接管 #121/#130，原始数据库放授权存储，Git只收轻量回执、SHA及代码。

交付完整性检查：

```powershell
python -X utf8 scripts/check_project.py
python -X utf8 project/experiments/block_v2/check_release.py
# 有索引指定的本地物理文件时：
python -X utf8 project/experiments/block_v2/check_release.py --local-artifacts
```

上面检查不重跑 EDA。需要重跑时，在固定Linux/ORFS/Slurm环境依次使用 `run_rtl.py --model <m|n|e|g> --out <新目录>`、`map.py --help`、`physical.py --help`、`qualify.py --help`；原始参数、工具/库SHA和候选选择以每宏原始回执为准，禁止将单阶段完成写成宏合格。此次整合未重新执行 RTL 仿真/综合/P&R。具体输入输出及限制见结果入口。

## 目录约定

| 路径 | 用途 |
| --- | --- |
| `README.md`、`研究资料导读.md`、`预制计算底座项目说明_v1.0.md` | 项目入口、阅读导引与初版研究定义 |
| `docs/` | 当前项目简介、架构、状态，以及专题研究文档和重要决策 |
| `docs/COMPUTE_BLOCK_BOUNDARIES_2026-10-30.md` | 当前 M/V/R 边界、位宽/部分和候选与 R 保留分析；规划与实现分开 |
| `docs/model-analysis/` | 八模型实验分析、精简字符算子图、完整图册及轻量导出证据；不保存权重 ONNX |
| `sources/` | 手写笔记、讨论澄清和原始研究资料 |
| `project/experiments/block_hierarchy/` | Issue #7 的隔离实验运行器、配置生成与运行说明；不放大体积物理输出 |
| `docs/experiments/` | 实验设计、结果摘要与证据边界 |
| `ref-project/llm-routing/` | 参考布线结果；Agent 不主动或例行维护，用户更新可按要求提交 |
| `progress/<github-handle>/`、`work/<github-handle>/<issue-number>/` | 个人进度和任务辅助资料，不作为正式研究成果的默认目录 |
| `.github/`、`config/`、`scripts/` | 协作模板、状态配置和管理结构检查 |

实验代码位于 `project/experiments/`；Issue #15 的 `opentpu_compare/` 使用原集群冻结源、现有ORFS容器和Slurm，不安装新工具。原始物理数据库留在授权集群，仓库保留脚本、提交身份、轻量终态及SHA索引。它是研究工程流程，不是冻结底座实现。

`extracted_eco.py` 是已完成详细布线后的恢复分支：只接受有终态清单的源，核验文件、宏视图、初末PG和实际引脚，并用同一SPEF复现源时序后做定向缓冲／驱动ECO。普通信号线清除后完整重布线及提取，special PG保留；最终沿用原生PG、真实分层STA和全部终态资格门槛。GRT估算单独保存为诊断，不代替真实提取验收。命令示例（尝试名必须全新）：

```powershell
python project/experiments/opentpu_compare/launch.py <全新提取后修复名> top --cores 16 --spec project/experiments/opentpu_compare/top-split-extracted-15.json
```

`top-split-extracted-16.json`示例启用`extracted_drive_guardband`，按真实提取报告选择35%电容／20%转换优化余量不足的驱动并修复；这只改变有源缓冲开销，最终Liberty和SDC门槛不变。若源作业尚未封存，可显式传`--after <真实源作业ID>`等待afterany终态，运行时仍独立核验源文件及PG资格，不假定依赖成功。

最终逐层线长来自封存原生`5_2_route.log`，采集时核对其SHA及各物理修复TSV；比较还要求原生表总线长／通孔与JSON指标完全一致、逐层四舍五入之和与总长相符。分别保存块内、父层和总逐层线长，用于判断本轮实际依赖的层资源；不能据H1层分布直接断言任何其他受限定制层方案可行或不可行。

`compare.py`还把功能／库存／STA／RC审计实际读取的`input-sha256.json`逐项绑定到对应源输出清单中的映射网表、终态网表／SPEF及边界SDC摘要，并要求源清单SHA自首次终态回执后未变。采集器同时核对输入摘要表本身的封存SHA；新增核对不重写旧证明。已用三块证书、库存证书及合并13的真实文件完成24处绑定检查，修改摘要的内存负例被拒绝；最终成对比较已在十一份选定来源／证明上完整通过这些门槛，冻结快照为f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d。

最终`stitch_proof`须选择`stitch-two-child.json`（`stitch_selftest: two_child`）产生的通过证书：源子块输出、父层、接收子块输入三段RC与独立显式拼接的平坦参考比较，最大／最小时序一致，漏父层RC的负例须检出。实际通过作业为`stitch-two-child-02`／89798；旧单子块自检继续保留。

最终比较还核对每项来源／证书实际计算节点的`image.sha256`、`tools.sha256`，这两个身份文件本身须属于封存输出。镜像、OpenROAD和Yosys ELF摘要须与固定实验一致，scheduler与allocation两处均须显示UNLIMITED。已在13份真实封存记录中验证，内存中修改工具摘要的负例被拒绝，旧终态回执未改写。

合格选择完成后的本地生成顺序：`compare.py <选择文件>` → `plot.py` → `report.py`。后两者只读取通过比较后冻结的`results/comparison-inputs.json`，核对其SHA；不从实时采集中间值生成合格结论。`report.py`生成中文`docs/experiments/issue-15-opentpu-results.html`，图表为同目录`assets/`中的PNG／SVG，另写`results/report-manifest.json`绑定生成commit和产物SHA。最终须目视检查三张实际科研图及HTML；已在合格selection-reuse20-merged13.json上生成并实际目视核验三图及中文HTML，最差完整路径起终点也与原生WNS核对；生成回执见results/report-manifest.json。

`plan_extracted_wires.py <已封存只读检查名> <全新下一轮名>`只提出方案，不启动作业或接受PPA。它核对检查作业终态、SPEF时序复现和原生100条max报告的封存SHA，选择路径余量<120ps、线延迟>90ps、单负载标准单元之间的数据线，生成BUF_X8中继配置及逐路径依据；时钟网和冻结宏不参与此规划。实际插入仍逐项断言连接、布局／重布线并通过全部最终门槛。已在89811真实报告上选出17段用于89812；每次必须使用全新配置名，不能覆盖既有轮次。

`extracted_size_probes`只在各自全新OpenROAD进程恢复封存源ODB／SPEF，更换实际缓冲模型并输出旧RC上的setup／hold／电气估计，随后退出；不合法化或重布线，没有物理验收资格。例为top-split-clock-probe-18.json／89816及top-split-clock-probe-17.json／89820，用于选择父层时钟和数据驱动规格。19轮新DRT后仍电气失败；20轮从电气已合格的17轮仅替换3个时钟及1个关键数据缓冲，另在新目录完整物理实现，保持原SDC，最终必须验证时钟变化后的完整setup／hold和电气。`extracted_receiver_guardband`只给接收硬宏输入的slew留20%优化余量，最终Liberty阈值不变；该选项用于19轮，20轮未启用。所有支持面积与布线计入。

可选实验标志`extracted_preserve_unchanged_routes`由`route_reuse.tcl`处理，仅接受不增删实例、不改变信号接线的规格ECO。remove_fillers后保存全部实例的master／坐标／方向／连接；实际替换和合法化后只清除规格或位置改变单元关联的普通线路，保留其他普通线路及全部special PG。重建GRT后再次核对保留线路数，再交给原生DRT和完整提取；不声称DRT只能修改这些网络或最终线路冻结。真实89829仅1个单元变化、2条线路清除、11952条线路保留到DRT输入，已自然COMPLETED0，完整实际门槛及匹配功能／标注／成本证明全部通过；不宣称最终线路冻结。

本试验的线索来自[官方DRT导入源码](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/drt/src/io/io.cpp)和[迭代源码](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/drt/src/dr/FlexDR.cpp)中对已有普通线路的处理；2026-10-23读取到io.cpp Git blob为3bae748dcf7ded65d01bab0f3084350eb6bf3c5b。官方master不等于本机unknown版本的精确源码，只用于提出可测假设；是否保留输入线路、原生DRT及提取能否通过均以本机证据为准。

`wire_audit.py`用views模式的`wire_audit_sources`映射读取封存完整最终ODB，执行本机`report_wire_length -net * -detailed_route -summary`，统计所有实际有普通线路的信号网，另读源DRT指标。实际API探针89830通过。两种原生线长统计允许保留其观测差异，1%阈值仅防明显漏计，绝不替代原有零违例验收；主表统一使用DRT口径。线路复用候选的最终选择必须另有`wire_audit_proof`，覆盖全部五个实现；核对输入ODB／路由指标／复用记录的封存SHA、来源匹配、完整网数与原生汇总。该证明与原五种证明共同冻结，共十一份来源／证明回执。

正式结果再生成（保留冻结对照；collect只是刷新实时观测，不自动改写comparison-inputs）：

```powershell
python project/experiments/opentpu_compare/compare.py project/experiments/opentpu_compare/selection-reuse20-merged13.json
python project/experiments/opentpu_compare/plot.py
python project/experiments/opentpu_compare/report.py
```

首次生成runner为8a646d8；依赖本机Matplotlib及已合格集群回执。不同时间重跑compare会更新冻结观测时间和SHA，必须随之重生成图与报告、重新核验manifest，不能混合旧新产物。原始DB仍在集群，报告可直接本地打开。

合格全量重布21的补充对照可独立生成，避免改写主快照及其报告：

```powershell
python project/experiments/opentpu_compare/compare.py project/experiments/opentpu_compare/selection-split21-merged13-audited.json --output-dir project/experiments/opentpu_compare/results/alternates/full-clear21
```

该选择也有五个物理来源及六类证明（含89835完整ODB成本），全部通过才创建输出目录；主表仍为selection-reuse20-merged13。实际两套结果及其边界见实验记录，不把单次耗时或极小差值推广为一般算法优势。

后续正式实现继续由关联 Issue 定义；当前实验代码沿用项目说明建议的 `project/experiments/`。不要为了填充目录创建空实现，也不要把全部业务代码放进个人 `work/`。

## 本地阅读与验证

- 阅读：从仓库根目录直接打开 `ref-project/llm-routing/总报告.html` 或 `ref-project/llm-routing/线长报告.html`；其图片和下载链接使用包内相对路径。
- 管理结构检查：`python scripts/check_project.py`（Python 3.9+，无第三方包）。
- 本次用户授权的报告更新检查：`python work/YUZE-LU/3/sync_reports.py`（Python 3.9+，需要 `beautifulsoup4`）；只读核验两份报告的资源、锚点、清单及图片展示状态。该任务脚本不是例行维护入口；再次同步需用户明确要求，并传入 `--sync --source <源报告目录>`。
- 初次接入的来源记录见 `docs/DATA_PROVENANCE.md`；后续例行检查不覆盖 `ref-project/`。
- openTPU实际对照：先阅读[实验定义](experiments/issue-15-opentpu-comparison.md)，运行 `python project/experiments/opentpu_compare/collect.py` 获取已有作业状态，`python project/experiments/opentpu_compare/quality.py` 核对严格终态门槛。启动新实验用 `launch.py`，必须使用全新尝试名，先提交runner。所有新作业 `--time=0`，并实际核对UNLIMITED。完整命令见实验定义；仅本地仓库不足以重跑，仍依赖授权集群的冻结输入与容器。
- 父层续跑示例：`python project/experiments/opentpu_compare/launch.py <全新尝试名> top --cores 16 --spec project/experiments/opentpu_compare/top-split-route-m9-07.json`，验证共同封存CTS和实际IO后执行。共享边界RC自检：`launch.py <全新尝试名> views --spec project/experiments/opentpu_compare/stitch-selftest.json`；平坦RC参考必须与分层结果一致，漏父层RC负例须产生差异。最终`compare.py <选择文件>`要求五份严格终态、三块／父层功能证书和RC自检，再运行`plot.py`生成静态科研图；不从中间布线数据生成合格PPA结论。
- 联合修复使用`top-*-route-m9-08.json`配置：`joint_repair.py`在独立OpenROAD进程中从真实ODB／SDC检查点交替执行时序修复、电气修复和独立审计，每次重新全局布线与估算寄生参数，保留中间检查点。用于避开手工ECO后当前二进制的EST-0104状态问题，不清空错误状态或跳过质量检查。
- 完整分层RC覆盖审计用`views`模式，spec中`annotation_sources`映射`top_split`／`top_merged`到实际父层目录；逐一解析未标注驱动，原生flat/all-arcs fanout必须为0，部分未标注驱动必须为0，并运行连接时钟正控制。最终选择JSON除`implementations`外要求`functional_proof`、`parent_functional_proof`、`stitch_proof`、`inventory_proof`、`annotation_proof`五个实际证明作业名；采集其封存SHA并匹配证明来源后才允许`compare.py`输出。

- 完整底座的业务构建、功能仿真和复现实验：**尚未配置**。结果包不含全部物理实现输入与工具，不能以结构检查代替业务验证。

## Issue #7：Block 分层实现试验

研究计划见 [openTPU 与 llaccel 的候选划分及实验矩阵](experiments/openTPU-llaccel-block-plan.md)。运行器使用当前成员已获授权的 SSH 与 Slurm 环境；需要 Python 3.9+、`ssh` 和 `scp`。原工程、工艺及固定工具镜像保持在集群，路径在运行器中明确列出，不复制进仓库。

以下是提交新作业的入口，每次必须使用新 attempt 名称；不会覆盖旧 attempt。具体结果、作业号、输入与输出索引见实验目录的运行说明与结果记录。

```powershell
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt <新的筛查名称> --mode screening --partition c64 --cpus 8
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt <新的功能回归名称> --mode regression --partition c64 --cpus 8
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt <新的物理试验名称> --mode pilot --partition c64 --cpus 16
python project/experiments/block_hierarchy/run_vec_pilot.py --attempt <新的顶层名称> --mode integration --block-attempt <已有匹配最终抽象的硬化名称> --macro-pdn legal-m10 --partition c64 --cpus 16
```

本轮 VECTOR 的完整路由宏使用 M7 供电引脚。默认整层阻挡视图与平台宏 PDN 不兼容；另用 `--macro-pdn detailed-m10` 在新 attempt 内从同一最终 ODB 导出逐形状 OBS、复用匹配的时序模型，并在父级增加 M10 供电接入。原视图和失败记录保留。该选项属于 H1 的供电／抽象集成对照；首试虽完成 DRT，却在最终供电检查发现 M8／M9 短接，尚不能作为合格配置。实际合法 via、PG 连通、宏位置及最终接口分别验收，不能用 `pdngen` 成功替代连通检查。详情见[现场记录](experiments/issue-7-vector-pilot.md)。

后续 `guarded-m10` 从同一 ODB 请求 `bloat_factor 1`，并在 PDN 后立即做严格供电连通检查。实际 89457 表明该参数未扩大致错的 M8／M9 边界，早期检查拦住同类短接；它是保留的阴性试验，不是已验证的修复方案。此模式需要已经生成且来源匹配的最终 LEF／Liberty／SPEF，不会借用其他实现的时序模型。作业统一使用本人缩写前缀 `yzl-vec-<mode>`；按新规则更新存量活动任务的名字有独立调度快照，未改变其输入或时限。

`legal-m10` 用实际 master 阻挡及完整 via 落点筛掉违规的新父级 PG 站，保留原宏几何，并继续严格连通检查。89461通过隔离修复，随后89472完整顶层和89475最终只读审计均完成；DRT、双网连通、固定宏和信号位连接的工程检查通过。父级仍有3个setup违例，块内setup／电容也失败，不能据此称时序闭合。最终 `pdn-site-audit` 只读复算几何并检查两网，绝不边修边验。各模式均须新 attempt，完整口径与限制见实验目录 README。

Tcl hook 的过程内加载回归入口为 `tclsh project/experiments/block_hierarchy/test_pdn_hook_scope.tcl <全新输出目录>`，需要已有 Tcl 环境。它用 mock API 检查实际脚本的作用域、只读不修改及严格返回值处理，不代替实际 PG／物理验证。

提交前核对节点资源、源码 commit 与运行器的参数。按用户要求，不再添加人工运行时限；有效调度时限必须从集群实际配置和作业读回，不能把省略参数等同于无限时。长期工作在 c64/c96 的实际分配资源内运行，不在登录节点进行综合或布局布线。远程新输出仅进入 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/<attempt>/`；原 `llm_routing_analysis` 与工具安装为只读输入。

独立 VECTOR 的完整数值和 16 路宽度保持不变。Block 的内部层次可以在硬化时展开；顶层必须读取已硬化的宏视图，不能再把宏内部重新综合或布局。集成用 shell 若仅直通原端口，只能证明这个宏能接入顶层布线流程，不能替代完整 llaccel core、协议仿真、多计算图映射或制造时定制验证。3 ns 周期及 0.6 ns IO 延迟是本次工程试验预算；本轮 SDC 未显式建模外部驱动单元、输入转换时间或输出负载，不是完整系统边界约束或签核结论。

运行器保存源 commit、工具版本与哈希、配置、Slurm 作业和实际退出码。大体积 ODB/GDS/网表/日志保留在获授权的远程实验目录；仓库只提交轻量索引、必要摘要与脚本。

## 数据与外部依赖

模型分析目录的归档检查命令为 `python -B work/YUZE-LU/116/validate_archive.py`，核对文档/图册本地引用、导入产物 SHA、报告迁移及原 Issue #114 证据不变。此检查不重新运行模型、onnxsim、RTL 或物理实验。

新增实验应记录代码 commit、工具和配置版本、输入数据版本、输出位置及 SHA-256。大体积物理数据库、原始日志和工具环境应使用项目约定且有权限控制的共享存储，并在仓库中保留可核对的索引。本轮已获授权的集群目录见上文；更长期的共享存储和访问策略仍需明确。不得将凭据写入仓库。

## Issue179：局部 Block 接续研究的静态容量核算

设计基于未合并的PR176固定提交；[研究报告](local-blocks/CONTINUATION_RESEARCH.md)给出来源、假设及后续执行/物理门。以下命令只生成和核对紧凑payload容量下界，不运行RTL或服务器实验：

```powershell
python -X utf8 -B work/Melodydt/179/analyze_capacity.py
python -X utf8 -B work/Melodydt/179/analyze_capacity.py --check
```

输入在work/Melodydt/179/capacity-input.json，结果在docs/local-blocks/continuation-capacity.json；结果绑定脚本及输入SHA-256。bank/握手/打包/全链调度尚未验收，不能用此核算代替硬件验证。

## Issue179：母控/局控方案与控制编码参考

[方案/研究步骤](local-blocks/TWO_LEVEL_CONTROL_PLAN.md)和[ISA v0.1](local-blocks/CONTROL_ISA_V0_1.md)定义proposed两级控制。机器规范、参考codec及独立编码测试位于project/control_isa_v0_1；软件检查不证明完整编译、原生执行、RTL或物理通过。

```powershell
python -X utf8 -B -m unittest discover -s project/control_isa_v0_1 -p test_codec.py -v
python -X utf8 -B project/control_isa_v0_1/codec.py examples --output work/Melodydt/179/control-example-programs.json
python -X utf8 -B project/control_isa_v0_1/codec.py decode --role mother --word 0x10000200010000000000000000000000
```

以上仅使用Python标准库；完整镜像装配、原生ABI注册、资源/对象/令牌语义与控制器执行仍待R1及后续阶段。

### 2026-11-04：综合方案 v0.2

[Block 组网与母控／局控综合方案](local-blocks/TWO_LEVEL_CONTROL_PLAN.md)集中定义五类型组成、四类连接、24 条运行指令、程序来源／存储、配置装载互锁和任务执行。ISA v0.1 的机器规范及软件保持不变。固定控制预连和主机统一装载器为候选，宏级断电暂缓；最新依赖进展和 R0–R7 退出条件在同文档记录。

本轮仍运行上述管理／编码检查，并运行容量重算；来源与产物 SHA 见 [综合方案来源](../work/Melodydt/179/control-summary-sources.json)和[验证回执](../work/Melodydt/179/control-summary-validation.json)。这是文档／软件参考核验，未新增 RTL、服务器或物理执行；装载器 RTL／镜像装配／native 注册与系统业务测试尚未实现。

### Issue179：控制接口与原生服务合同第1步

[接口合同](local-blocks/CONTROL_INTERFACE_CONTRACT_V0_1.md)和project/control_contract_v0_1提供来源绑定的端口、12个P服务、资源／拓扑profile与静态字段检查；不实现Block或控制RTL，不执行数值。每次接续／发布先核PR176最新提交、说明、评论／review，更新work/Melodydt/179/pr176-sync.json。

```powershell
python -X utf8 -B -m unittest discover -s project/control_contract_v0_1 -p test_contract.py -v
python -X utf8 -B project/control_contract_v0_1/contract.py examples
```

依赖同仓库control_isa_v0_1和Python标准库。检查结果始终标记deployable=false，未登记服务／路线拒绝；完整镜像、指令执行和真实物理接入另行验证。来源／验证见work/Melodydt/179/control-interface-sources.json及control-interface-validation.json。

### Issue179：第2步控制用例与独立轨迹

[用例与边界](local-blocks/CONTROL_REFERENCE_CASES_V0_1.md)和project/control_cases_v0_1提供3组程序／分离记录与4条人工参考轨迹。oracle仅检查输入事件事实，不执行机器码PC或RTL；未来执行器／RTL应独立产生轨迹与之对照。

```powershell
python -X utf8 -B project/control_cases_v0_1/oracle.py encode --output project/control_cases_v0_1/encoded_cases.json
python -X utf8 -B project/control_cases_v0_1/oracle.py check
python -X utf8 -B -m unittest discover -s project/control_cases_v0_1 -p test_oracle.py -v
```

本轮源／验证为work/Melodydt/179/control-case-sources.json、control-case-validation.json。每轮进展必须补入总方案的当前摘要与逐轮记录；上游PR176检查仍在研究开始／恢复和上传前执行。

### Issue179：第3步完整镜像与配置装载参考

[镜像／装载合同](local-blocks/CONTROL_IMAGE_LOADING_V0_1.md)与project/control_image_v0_1提供完整128B头＋指令／描述符、cohort manifest／SHA、有限部署准入和单bank装载／排空／复位状态模型。Python标准库；START只准入，不执行PC／RTL；配置总线编码、硬件互锁和provider复位确认未实现。

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B project/control_image_v0_1/image.py build --output image-bundles-check.json
python -X utf8 -B -m unittest discover -s project/control_image_v0_1 -p test_image.py -v
```

生成文件应与project/control_image_v0_1/bundles.json逐字相同，临时文件不上传。同时运行上文ISA、接口、轨迹单测；轨迹现28组（本轮纠正CALL arg0快照），镜像30组，合计81组。实际回执为work/Melodydt/179/control-image-validation.json；代码commit、输入与SHA见control-image-sources.json。未使用远程服务器，无新作业或自动监测。

### Issue179：第4步二进制控制执行模型

[执行模型合同](local-blocks/CONTROL_EXECUTION_MODEL_V0_1.md)与project/control_exec_v0_1从已装载完整镜像按PC取指，有限宏／存储／链路peer生成实际观察，再与人工属性／golden及退休PC比较。S为有限Python bytearray，tick不是硬件周期；没有控制RTL或完整Block。

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B project/control_exec_v0_1/run_campaign.py --output binary-runs-check.json
python -X utf8 -B -m unittest discover -s project/control_exec_v0_1 -p test_machine.py -v
```

生成文件应与project/control_exec_v0_1/run_reports.json逐字一致，临时文件不上传；上文四套单测仍须运行。第4步新增26组、累计107组通过；9实验100次退休／193观察包含背压、M非正常peer错误及不复位连续2job。来源、工具、实际命令和SHA见work/Melodydt/179/control-exec-sources.json／control-exec-validation.json。下一步运行取消、provider协同复位与旧响应隔离；尚无服务器作业或自动监测。

### Issue179：第5步取消、协同复位与迟到响应

[恢复研究](local-blocks/CONTROL_RECOVERY_PLAN_V0_1.md)及project/control_exec_v0_1/recovery.py增加条件化安全取消、poison、模型RESET_REQ/ACK及完整重装。新30、累计137组检查；正常9次旧报告保持字节一致。无tag隔离依赖provider静默／复位合同，观察origin不是native tag；真实硬件／完整Block未验收。

```powershell
python -X utf8 -B project/control_exec_v0_1/run_recovery.py --output recovery-runs-check.json
python -X utf8 -B -m unittest discover -s project/control_exec_v0_1 -p test_recovery.py -v
```

新报告应与recovery_reports.json逐字相同；继续运行上文五套测试／旧campaign，临时文件不上传。来源、实际命令、工具及SHA见work/Melodydt/179/control-recovery-sources.json／control-recovery-validation.json。下一步局控RTL接口／状态机／写口互锁和真实provider复位清单；无服务器作业或自动监测。

### Issue179：第6步局控RTL接口／状态机候选

[局控RTL入口合同](local-blocks/LOCAL_CONTROL_RTL_CONTRACT_V0_1.md)及project/control_rtl_contract_v0_1定义92逻辑信号、状态／guard、单PM端口和部署互锁、返回信用及688B payload寄存器下界。SystemVerilog仅interface／常量声明；人工边沿样例不是DUT运行，HDL编译／lint／仿真未执行，PATH未发现iverilog/verilator/yosys。

```powershell
python -X utf8 -B project/control_rtl_contract_v0_1/generate.py --check
python -X utf8 -B project/control_rtl_contract_v0_1/examples.py --check
python -X utf8 -B -m unittest discover -s project/control_rtl_contract_v0_1 -p test_boundary.py -v
```

新36组、累计173组；继续运行上文六套单测及旧执行／恢复报告重建。来源／实际验证为work/Melodydt/179/control-rtl-sources.json及control-rtl-validation.json。下一步功能局控最小切片；无服务器／物理作业或自动监测。





### Issue179：第7步最小功能局控RTL

[实现／能力与复现](../project/control_rtl_min_v0_1/README.md)及[研究](local-blocks/LOCAL_CONTROL_MIN_RTL_V0_1.md)只覆盖空任务和M clear控制。旧七套173检查继续运行。服务器最终97215／node27／debug／4核，Verilator5.042容器内实际编译与10场景通过；M／PM为行为peer，非完整Block。

```bash
python3 -B project/control_rtl_min_v0_1/wiring.py
python3 -B project/control_rtl_min_v0_1/run.py --simulator verilator --verilator /eda/verilator-5.042/bin/verilator --out /work/results
python3 -B work/Melodydt/179/verify_control_min.py --archive evidence-97215.tar.gz --extract /tmp/issue179-evidence-check
```

前两条在既有ORFS26Q1容器、G++11.4／Python3.10.12中执行，bind实际任务目录到/work、EDA目录只读到/eda；完整实际脚本见work/Melodydt/179/control-min-job-r005.sh。第三条用于有原始证据包时重核SHA／实际轨迹／终态，默认仓库根由脚本位置确定；证据包在本任务服务器目录，非仓库内置文件。
输出report.json含环境／命令／输入与日志SHA；最终确数为10场景3926边沿，5执行轨迹3061边沿。无四态／综合／物理或母控RTL验收，无后台监测。

### Issue179 第8步：局控CANCEL／有界排空

所有RTL与控制模型仿真在服务器的ORFS26Q1／Singularity4.3.4环境运行，4核；命令如下。173既有检查仍需逐套执行，完整实际启动脚本见work/Melodydt/179/control-cancel-job-r003.sh。

```bash
python3 -B project/control_rtl_min_v0_1/run_cancel.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/cancel
```

固定总方案Markdown及同名PDF逐步更新，PDF工具为scripts/render_control_plan.py，需要reportlab和可嵌入中文字体Deng.ttf／Dengb.ttf；渲染后使用Poppler逐页检查。文档生成不属于硬件仿真。原第7步verify_control_min.py须在其固定a54cbc4源码副本运行，不要求新功能代码匹配旧版本SHA。

## 第9步故障RTL（服务器运行）

当前DUT须同时通过run.py、run_cancel.py及run_fault.py；新增命令在相同容器的源码根执行：

```bash
python3 -B project/control_rtl_min_v0_1/run_fault.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/fault
```

服务器最终目录/public/home/yuzelu/Melodydt/issue179-control-fault-96b8280/r005，源码f41158211ef69bb74a9252bd1790e53572e095e0，Slurm97222／debug／4核0:0。准确容器／挂载和七套173检查见work/Melodydt/179/control-fault-job-r005.sh；61个RTL场景的输入／输出／日志摘要见control-fault-validation.json。旧报告属于旧DUT，不能用它们声称当前源码已验证。仿真不得移至本机。

## 第10步M clear适配器（服务器运行）

```bash
python3 -B project/control_rtl_min_v0_1/run_adapter.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/adapter
```

同时运行旧run.py、run_cancel.py和run_fault.py；本次未改局控core，仍有实际重跑记录。真实依赖为project/rtl/block_v2/block_v2_m.sv（原始blob d91ffdf904bc77c19d5d0ecfd4cd11560b44a417），不修改宏。准确容器／挂载／七套173检查见work/Melodydt/179/control-adapter-job-r002.sh；服务器最终目录/public/home/yuzelu/Melodydt/issue179-control-adapter-af680f3/r002，实验commit944648b45efcf962091b3ca13c0d6dfd35501d5b，Slurm97224／debug／4核0:0。raw模型和RTL仿真均在服务器，PDF和SHA静态核验可在本机。

## 第11步对象控制（服务器运行）

```bash
python3 -B project/control_rtl_min_v0_1/run_object.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/object
```

control-object-job-r002.sh运行七套173检查、全部旧RTL和26对象；control-object-job-r003.sh仅重跑新增场景后的27对象，除runner外源码SHA一致。最终实验commit6df461bc7b4429fb83975bdae0e3ce8337b834ba，服务器/public/home/yuzelu/Melodydt/issue179-control-object-ddac1c8/r003，Slurm97226／debug／4核0:0；准确容器及挂载见脚本。对象和寄存器的有限边界见控制目录README；不以退休轨迹宣称未观测的寄存器数值。

## 第12步RAW16收发（服务器运行）

```bash
python3 -B project/control_rtl_min_v0_1/run_transfer.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/transfer
```

control-transfer-job-r001.sh运行173软件、103旧RTL后在新TB编译失败；control-transfer-job-r003.sh仅运行最终25收发用例。DUT／旧回归源SHA一致，验证索引明确关联，不能将失败作业当整体通过。最终实验commit7d8790967e46314a37e27428e5346fd209d956a9，/public/home/yuzelu/Melodydt/issue179-control-transfer-76fc765/r003，Slurm97229／debug／4核0:0。所有模拟执行均在服务器；新peer仅一个16KiB SRAM／单服务／16B接收槽，不是原生S。

## 第13步母控RTL（服务器运行）

```bash
python3 -B project/control_rtl_min_v0_1/run_mother.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/mother
```

control-mother-job-r005.sh为最终准确命令；r001～r004为失败记录，均保留。最终97234／node27／debug／4核COMPLETED0:0，实验commit3b4ef844df72346271988ce33b5941cc3fa82aba，服务器/public/home/yuzelu/Melodydt/issue179-control-mother-2384c31/r005。26场景／4突变拒绝，两个子端为有限协议peer；实际LC集成下一步。母控只5指令／2目标／8token，G_PARAM不支持，不改变ISA候选宽度。

## 第14步母控与实际双局控（服务器运行）

```bash
python3 -B project/control_rtl_min_v0_1/run_network.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/network
```

control-network-job-r001～r003.sh保存实际命令与回归范围。最终97243／node27／debug／4核COMPLETED0:0，实验commit738720d495eaf5ea53f123bfaacc67c19ef3ff68，/public/home/yuzelu/Melodydt/issue179-control-network-dc23b38/r003；10集成＋25局控回归通过，26母控回归来自r001已完成部分。母控与2LC为真实RTL，存储／ACK路由为有限peer，STALL4096／DRAIN128是本次参数。R4有界门满足，不扩大为完整Block／原生S／物理。

## 第15步R5候选控制模型（服务器运行）

```bash
python3 -B project/control_profiles_v0_1/run_profiles.py --out /work/results/profiles
```

control-profiles-job-r001～r003.sh为准确命令。最终97246／node27／debug／1核COMPLETED0:0，实验commitca954d4294cb320667d35e9741caf90acd0a6513，服务器/public/home/yuzelu/Melodydt/issue179-control-profiles-2e6d211/r003。34二进制模型、30镜像拒绝、6组114cohort／query和4突变拒绝；model ticks不等于硬件周期。本机export_examples.py仅静态编码，逐镜像SHA与最终服务器一致。新增profile／管理帧未实现RTLserializer或真实native适配，旧控制DUT不改；不能以管理CI或软件模型替代这些门。R5有界研究交付后按用户边界停止，R6／R7未执行。


R4真实provider合同：`python -B project/control_r4_v0_1/check_contract.py`；本机仅静态源／端口／地址和身份合同核验，RTL仿真仍须获授权服务器Slurm。

R4.2服务器命令：`python3 -B project/control_r4_v0_1/run_real_s.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/real_s`，Slurm／Singularity路径及输入输出版本见control-r4-real-s-evidence.json。需同时编译冻结私有S、仲裁、feeder、S16k及现有控制DUT；不在本机运行仿真。

R4.3服务器命令：`python3 -B project/control_r4_v0_1/run_real_dma.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/real_dma`；同时运行12集成及10桥接RTL边界。固定8槽／1信用、2S，实际hbm_group_dma和双向hbm_async_fifo；有限外部MEM非HBM控制器。见control-r4-dma-evidence.json。

R4.4服务器命令：`python3 -B project/control_r4_v0_1/run_reset.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/reset`；6真实cohort reset／三镜像全量装载集成＋11协调器RTL边界。实际MC／LC／S／DMA／FIFO统一reset，provider ACK为可信测试wrapper证书，生产reset／CDC不由仿真授予资格。证据control-r4-reset-evidence.json，步骤原位记录TWO_LEVEL_CONTROL_PLAN.md及同名PDF。

### R6.1 任务 IR 与目标合同

运行 `python3 -B project/control_r6_v0_1/check_ir.py` 检查任务 IR 的固定路由、16B S 对象、READY 和信用边界。目标表和两种等待布局见 `project/control_r6_v0_1`。

### R6.2 三端程序镜像生成

从 IR 构建三端镜像的命令见 `project/control_r6_v0_1/README.md`。生成的 JSON 包含 reference loader 的 manifest 和精确 little-endian 二进制。构建证据见 `work/Melodydt/179/control-r6-build-index.json`。

### R6.3 独立检查与服务器镜像联跑

在已授权服务器的 Slurm/Singularity 环境运行 `python3 -B project/control_r6_v0_1/run_campaign.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/r6`。独立静态核对可运行 `python3 -B project/control_r6_v0_1/check_bundle.py`。作业脚本与版本及 SHA 见 `work/Melodydt/179/control-r6-validation-index.json`。

### R7.1 控制成本复现

镜像和轨迹资源账使用 `python3 -B project/control_r7_v0_1/inventory.py --r6-evidence /public/home/yuzelu/Melodydt/issue179-r6-13e577c/r001/evidence.tar.gz --out inventory.json`。该命令校验 R6 证据包、装载镜像与轨迹 SHA，再统计实际握手。

映射与时序使用 `project/control_r7_v0_1/synthesize.py`。在获授权服务器的 Slurm/Singularity 环境执行 `work/Melodydt/179/control-r7-job-r002.sh`，其工作目录和二进制、库、LEF 输入见 `work/Melodydt/179/control-r7-validation-index.json`。典型库逐模块面积与 3.333 ns 寄存器间 setup 结果见综合报告。

### R7.2 真实 Block 接入

接入顺序和证据清单位于[方案第 9.1 节](local-blocks/TWO_LEVEL_CONTROL_PLAN.md#91-r72-真实-block-接入与验收清单)。静态依赖核验使用 `python -B project/control_r4_v0_1/check_contract.py`。取得生产端版本后，在服务器复用上述 R4/R6 命令作为控制回归，并加真实 P 写回和端到端 ACK 验收。LC1 整改复用 R7.1 的固定库、参数与综合脚本，另外提交实装约束和 STA。

### A2 单 P 的真实 M 与 S 接入

服务器容器内从仓库根运行以下两项。A2 编译实际母控、局控、私有 S、feeder 和 M，并用两份程序镜像跑固定形状的计算写回。R6 复跑用于核对原 ABI。

```bash
python3 -B project/control_p_compute_v0_1/run_a2.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/a2
python3 -B project/control_r6_v0_1/run_campaign.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/r6
```

[A2 作业脚本](../work/Melodydt/179/control-a2-job.sh) · [LC1 原始基线复跑](../work/Melodydt/179/control-a2-job-lc1.sh) · [校验和与结果](../work/Melodydt/179/control-a2-validation.json)

### 独立控制配置的 300 MHz 修复

在 Slurm 容器中以项目固定的 Yosys、OpenROAD 和 Nangate45 库运行。先用 R7.1 的映射命令输出母控、LC0、LC1、RAW16、DMA 桥及双 S DMA，再调用下方脚本。六个配置可占用 6 个已分配 CPU 并发。实际容器、工具路径和原映射输入见作业脚本与验证索引。

```bash
python3 -B project/control_timing_v0_1/close.py   --yosys /usr/local/bin/yosys --openroad "$OPENROAD_EXE" --platform "$NANGATE45_PLATFORM"   --mapped /work/results/mapped --out /work/results/repair --workers 6
```

[最终作业脚本](../work/Melodydt/179/control-timing-job.sh) · [时序、原件位置与 SHA](../work/Melodydt/179/control-timing-validation.json)

### A2-G 单 P 的真实 SiLU 写回

在获授权的服务器 Slurm/Singularity 容器内从仓库根运行。三个配置使用相同的 3.333333333 ns 周期。

```bash
python3 -B project/control_p_compute_v0_1/run_a2.py --silu \
  --verilator /eda/verilator-5.042/bin/verilator --out /work/results/silu
python3 -B project/control_p_compute_v0_1/silu_mapping.py --yosys /usr/local/bin/yosys \
  --openroad "$OPENROAD_EXE" --liberty "$NANGATE45_PLATFORM/lib/NangateOpenCellLibrary_typical.lib" --out /work/results/mapped
python3 -B project/control_timing_v0_1/close.py --yosys /usr/local/bin/yosys \
  --openroad "$OPENROAD_EXE" --platform "$NANGATE45_PLATFORM" --mapped /work/results/mapped \
  --out /work/results/repair --workers 2 --modules silu_mother silu_local silu_store
```

仿真独立核对 M 舍入／饱和、G 定点 SiLU、S 内容和真实写 ACK 顺序。作业另运行原 M→S、R6 与协调复位回归。[作业脚本](../work/Melodydt/179/control-a2g-job.sh) · [输入输出校验与时序](../work/Melodydt/179/control-a2g-validation.json)
