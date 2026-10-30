# 架构与运行

Issue126工具规模诊断：`probe_upper_fullframe_subset.py`/`upper_fullframe_probe_job.sh`只读原770边实际模式的闭合placed_adapter检查点，保留全frame/全部原M10 PG与OBS、实际4个hook，只在独立scratch保留2条真实边并启用GRT verbose；原770边及共同下层作业不附加/暂停/改动。此诊断不代表全块/完整系统或允许层可行性，所有成功仅限子集。实际执行以runtime_submissions/原生回执为准。

Issue126新终态复现：`incremental_diode_eco_job.sh r01`的真实658diode源已完成native/全网几何/原数字及位置合同/RCX/原SDC检查，完整GDS仍独立。`route_representation_job.sh r01`按三份真实SHA比较全部268637网的WIRE/VIA矩形多重集，15/77网不同表示不等于物理并集/线长/RC；完整逐网digest留授权存储。`export_real_diode_view.py`/`real_diode_view_job.sh`为该确定源导出真实clean ODB/LEF/OBS/DEF/网表、SPEF研究模型并逐bit/方向/层/尺寸核查，独立重读模型和余量；未提交/未执行状态由runtime_submissions及新回执明确，不因代码存在称视图已完成。`audit_path_liberty_tables.py`只读诊断真实141段cell arc的原库表，不把独立grid最小值当STA或可行/不可行证明。`plot_actual_diode_access.py`分别绘制原GDS bbox及新真实cell放置框，定位符号和真实尺寸区分，发布PNG/SVG需目视核验。

Issue126剩余天线：`post_diode_netmap_job.sh cap-r01 cap`/`run_post_diode_netmap.py`只接受匹配DEF/GDS/RDB/原生几何SHA，将真实多边形精确关联实际网，逐项核查已有diode集合。`run_incremental_diode_eco.py`/`incremental_diode_eco_job.sh`据37项/22网证据复用636diode+两换型真实源，旧单元/diode全部FIRM后放置22新ANTENNA_X1，恢复原状态；原guide的start/end incremental GRT及普通DRT不等于只改22条网。全量图、原pose/端点、pin/PG/外框/OBS、fresh DRC、RCX及原SDC检查独立保留，新GDS原deck须再执行，不能以插入数量或native0替代规则资格。

Issue126增量复现：`diode_cap_eco_job.sh r01`/`run_diode_cap_eco.py`只在636真实diode后的确定源上按原Liberty逻辑/状态合同换型INV/XNOR两实例，保存增量接线、fresh DRC、全网几何、RCX及完整原SDC报告，成本独立。`antenna_diode_stream_job.sh cap-r01 r01 cap`按源SHA执行严格GDS及未修改的原deck，与旧diode源37项天线分开。`run_full_upper_adapter.py`/`full_upper_adapter_job.sh`实现两个770-edge适配层独立试验，输入为同一个真实但未合格的下层检查点；每条实际overlay M10矩形须包含在原hook内，M1–M9/cut1–cut9不得新增，不以适配层试验替代下层冻结/完整系统RC/STA。源码/命令/工具/作业由gate-r14及后续不可覆盖回执绑定。

本仓库含研究资料、参考结果和实验性分层物理实现代码。`project/experiments/` 下保留 `block_hierarchy/`、`parallel_blocks/` 和 `opentpu_compare/` 的实验及证据；正式预制底座和制造工具链尚未冻结。[项目说明 v1.0](../预制计算底座项目说明_v1.0.md) 中标注的候选架构不能当作已实现硬件。

## 研究系统边界

拟研究的流程是：目标计算图与需求 → 预制 Block 资源映射及调度 → 预埋资源选择和受限布线 → 定制互联与成本／性能／能耗评估。预制内容、制造时定制内容和运行时状态必须分别建模；工艺堆栈、端点电气合法性、存储供给与时钟网络不能省略。

## 目录约定

| 路径 | 用途 |
| --- | --- |
| `README.md`、`研究资料导读.md`、`预制计算底座项目说明_v1.0.md` | 项目入口、阅读导引与初版研究定义 |
| `docs/` | 当前项目简介、架构、状态，以及专题研究文档和重要决策 |
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

新增实验应记录代码 commit、工具和配置版本、输入数据版本、输出位置及 SHA-256。大体积物理数据库、原始日志和工具环境应使用项目约定且有权限控制的共享存储，并在仓库中保留可核对的索引。本轮已获授权的集群目录见上文；更长期的共享存储和访问策略仍需明确。不得将凭据写入仓库。


## Issue #119：pin XY 候选对照

[ACT/GEMM 摘要与两块对照图](experiments/issue-119-pin-xy-candidates.md)比较真实四边、贴边多排和内部二维混合接点；完整逐 pin 清单/原层/网络/方向保持。图表、压缩 CSV、轻量证据位于 docs/experiments/issue-119-pin-xy/，只读解析/布局/绘图脚本位于 project/experiments/pin_xy_candidates/。原 ref-project 报告、ODB 和既有实验不修改，大体积物理表留授权服务器并用 SHA 索引。

本次仓库校验仅用标准库：

```sh
python scripts/check_project.py
python project/experiments/pin_xy_candidates/validate_repository.py
```

完整重画先按该目录 README 恢复独立工作目录和只读 physical/ 快照，再运行 analyze_layout.py；不能在参考报告或已有实验目录原地运行。最近端点 L1 与矩形风险不是提取线长/RC，也不是 DRC、时序或实际面积收益。本次没有启动新的 P&R。

## Issue126：完整功能分块、六块候选覆盖与真实接入

[中文入口](experiments/issue-126-full-pin.md)与[交互报告](experiments/issue-126-full-pin/report.html)在PR120之上增量扩展，代码位于 `project/experiments/full_pin_xy/`。
openTPU为ACT/MXU/SYSTEM，llaccel_core为GEMM/VECTOR/SYSTEM，SYSTEM复用Issue55真实包装和完整功能归属。
六块24,767原始信号pin，A/B/C共74,301行；未重算ACT/GEMM原有候选。命令与输入恢复见该目录README。

```sh
python scripts/check_project.py
python project/experiments/full_pin_xy/validate_repository.py
```

`prepare_trials.py`冻结同一8pin的原始、重布线控制、边界槽位重排、B/C；`physical_trial.tcl`实际改ODB并GRT/DRT/RCX，分别保留规则、连通、PDN、STA和电气回执。
`export_access.tcl`/`check_access.py`从真实各层路由、via定义和ITerm访问矩形独立检查连通；全块模式只排除不需互连的单端网络，不等于GDS/LVS。
候选检查、局部试验、完整C实现与父层资格均单列；原父层handoff/目标层仍未知，不能自行指定M8或提升至M11/M12。
远程只写 `/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027`，采用先提交、全新commit驱动目录和全新尝试名；不覆盖历史数据库或活动作业。当前物理结果以报告中的实际阶段回执为准，不将DRT0等同完整通过。

完整cohort比较、实际失败驱动的GEMM整字节/MXU整lane增量修订，见`prepare_electrical_revision.py`、`prepare_mxu_repair.py`；原ABC和当前物理补充表分别保存。`stage_incremental_evidence.py`复用真实执行输入并核对Tcl SHA。`make_physical_summary.py`按实际cohort比较DRT提取前线长/via、独立native DRC、所检全块多端连通与setup/hold/电气，原始逐net细节保留在链接回执，HTML只展示摘要。

按用户明确授权补建的受控父层由`prepare_controlled_parent.py`/`parent_job.sh`实施；`verify_parent_graph.py`在PG/布线前核对全部端点/bit/方向/原层，后续各变体冻结A的PG/外框/TOP_IO及单元位置。新TOP_IO策略与tie成本明确单列，历史handoff仍未知。父层Liberty仅物理链接、未表征，禁止用其得出父层STA/负载资格。真实GDS/LVS/宏器件模型缺项继续保留。

后续`run_timing_models.py`/`timing_model_job.sh`已实际从匹配clean ODB与原SPEF导出20份研究叶模型，逐信号bit/方向及SPEF重读余量校验通过；原占位Lib仍只用于已冻结路由阶段。`run_parent_rc_sta.py`在独立进程中读取真实导出模型，精确匹配物理ODB及来源回执SHA，并以父层native/连通/PG门槛为前提；新2.5ns基准仍缺外部I/O延时、驱动、slew、load及minimum_period覆盖，始终不输出完整系统签核。已排队92476/92477，原失败/未执行条件保留。

`run_well_semantics.py`用独立小GDS验证原WELL.4表达式与其宽度描述不符；`run_actual_well_reference.py`在严格完整llSYS A GDS上新增并集及逐N/P mask宽度/间距专项检查，原全量deck不替换。实际参考均0，原表达式仍大量报告且与原全量计数未完全复现；不把它解释为所有原项消除。原deck中WELL.2未实现及部分via enclosure实现疑问仍属规则覆盖缺项。`run_parent_preflight.py`将固定父层几何与未完成信号路由分开；旧placed输入缺GCELLGRID导致原生检查未成功，不能记为DRC0。

2026-10-28接续：`prepare_act_access_revision.py --case CASE`将真实内部候选对齐相邻层轨道，冻结输入后在`physical_trial.tcl`保留临时接入窗口、完整信号重布线，移除的只有本轮新约束。实际层/端点/PG/OBS/原允许层不变；不与旧局部rip成本混比。`compile_shared_topology.py --root R --preparation P --out NEW`检查两功能共享256有限导体的完整逐bit图，生成构造网表；`common_link_job.sh INPUT NEW_REV`读取匹配Aopt真实LEF/Lib，`verify_common_native.py`检查34954端点/17686分量双射。此阶段不布局/布线/冻结，施工端口还须降为保留金属。

`run_escape_landing.py`仅修订新父层M10中间接点，不改原ACT M5/M6；只有fresh native/860网连通/双PG/原PG及其他父pin保持全部满足才标记几何门槛通过。`escape_rc_sta_job.sh NEW_REV`对已接受Aopt/C夹具实际提取与同研究I/O约束、2/10/50fF敏感性分析，不保存RCX后ODB；所有hold/电气/604零长度网未标注提示保留。`run_leaf_eco.py`的重定尺寸/缓冲/布局成本与纯XY分开，等价仍需独立验证。

可复现发布检查：`python scripts/check_project.py`；`python -m compileall -q project/experiments/full_pin_xy`；`python project/experiments/full_pin_xy/test_zero_wire_access.py`；`python project/experiments/full_pin_xy/validate_repository.py`。完整报告用`build_deliverables.py --root R --out docs/experiments/issue-126-full-pin --keep-figures`；仅刷新新增阶段用`refresh_continuation.py`同参数；浏览器用`node project/experiments/full_pin_xy/qa_report.mjs REPORT NEW_QA_DIR`。原CSV/历史快照和PR120原图保持，新增原生文本无损gzip、大型物理文件只读留远程SHA索引。9031个新实际pin逐项与增量表比较，不能把全部24767候选的检查当全部物理完成。


2026-10-28晚接续新增：`prepare_local_pin_patch.py`/`local_pin_patch_job.sh`实施LL完整表的三点增量重接线；实际DRT无AP失败与坐标正确分开。`constraint_audit_job.sh NEW_REV`取得只读NDR规则/关联/实际wire宽度及驱动查询，源SHA不变，不当完整规则通过。`cell_semantics.py`和`run_leaf_eco.py`的TARGETED分支做实际X2驱动增强并恢复填充，成本与纯XY分开。FRESH_GRT分支先实际重建GRT，再显式用GRT估算做修复，原SPEF重放与最后RCX/STA分别记录；SYSTEM原允许层不变，合法化工具崩溃不删检查。实际冻结驱动与作业号见10月28日接续交接。

新增快照命令：在获分配的本人Slurm作业内从远程ROOT执行`python3 -B DRIVER/collect_resume_progress.py NEW_NAME [JOB...]`；只写新的resume_snapshots目录。下载到分析目录的resume_evidence后，运行原`refresh_continuation.py`和`validate_repository.py`，25幅报告图含新增真实PG/原生marker/proposed局部图。`qa_report.mjs`检验所有图片和逐bit筛选；生成图必须打开目视核验。候选/快照校验通过不代表native/完整DRC、连通、RC、STA或冻结资格。


本轮GDS导入/规则阶段：`streamout_probe.py`显式设read_lef_with_def=false，仅保留原配置依赖的LEF清单，避免KLayout自动把导出的abstract/detailed两份顶层LEF当成子宏重复读入；实际安装API证据由`audit_streamout_reader.py`生成。allow-empty仍禁用，原FreePDK45 deck不改。`collect_gate_milestone.py NEW_NAME`在本人分配资源内收集不可覆盖的原始阶段快照；下载到analysis/gate_evidence后执行`refresh_continuation.py --root R --out REPORT --gates-only`，生成逐块qualification_matrix.json/CSV与最新门槛HTML。`validate_gate_matrix.py`由主验证器调用，独立核对旧提前失败、显式LEF配置、真实严格合并结果及实际时序数字。已知GDS缺失/规则覆盖缺口与native结果分别报告，不以Slurm/CI/空缺失列表宣布通过。


新增实际验证：`antenna_rules_job.sh NEW_REV`只读核实安装LEF/GDS deck原文、原生逐层规则存在性及源SHA；原生天线0不代表已加载有效规则。`mapped_eco_job.sh CASE NEW_REV`对原始与成本ECO ODB导出全量映射端点，比较全部实例、信号/时钟/复位/常量/顶层网络及实际Liberty换型合同；相同存储黑盒合同的相对数字保持证明不替代RTL形式验证。`eco_view_job.sh opentpu_aux r01 NEW_VIEW_REV`导出实际检查点布线的SYS2229位视图，原始成本表与最终原生实例表分别核算；G/M可追加Aopt参数导出等成本周边视图。

`plot_equal_cost_controls.py`只读取实际Aopt/C余量及独立成本，由gate_report刷新PNG/SVG；原A/B/C图不覆盖。`prepare_actual_landing_repair.py NEW_REV`以新版GEMM父夹具1项实际M10错误为触发，筛查原生异网金属/PG/OBS并移动新父层接点，原叶层/尺寸和PG不改；真实重布线、独立规则及全块连通仍必须执行。新集成模型只在显式`PINXY_UNQUALIFIED_MODEL_EXPORT=1`且LL完整PG-only原生错误数确为4时允许诊断导出，状态保留FAILED_DRC_SOURCE；不是放宽物理通过条件，不用于合格冻结。


实际共同集成（明确未合格）：`common_integration_job.sh C NEW_REV`读取冻结来源的六块真实详细OBS与匹配提取Lib，复用common-topology-r02全图及既定256×32μm导体拓扑/预算；先实例放置/PDN，再筛查真实M10金属、PG与OBS后写FIXED dbWire并执行底层GRT/DRT。原叶pin不改；新父层M10施工接点与原层定义分开。原生API由`fixed_wire_probe_job.sh NEW_REV`先验证，BPin的实际枚举为FIRM，DEF信号wire实际为FIXED；原错误版本保留。施工端口未降为合法模式几何前不冻结，不把LL失败DRC源或负STA来源提升为合格底座。

`estimator_diagnosis_job.sh NEW_REV`复现VECTOR EST-0104；用`PINXY_EST_FILLERS_BEFORE_ESTIMATE=1`进行单变量对照，将remove_fillers移到估算之前。r01冷隔离仍失败，r02同命令/源/约束下修复执行成功，检查点仍NOT_LEGALIZED_OR_ROUTED。`plot_actual_common_placement.py`只绘制原生44实例放置来源；`gate_report.py`复用已完成DRT最后原生报告统计同ECO两侧逐层线长/via，不重复路由，也不把此表称系统收益。


`vector_resume_job.sh NEW_REV`从estimator_diagnosis/r02实际成功检查点继续，不重跑repair_design；各原生进程隔离timing_repair、legalization、route，分别保存阶段账本。恢复原filler类型集合、原pin/PG/die、原OBS及准确临时窗口，最后RCX/STA和独立DRC/信号时钟/双PG均保留。返回0也只表示已执行的研究门槛，不代表完整规则/形式/系统资格。

## Issue126：实际有向合同、局部金属归属与天线网追踪（2026-10-29）

本地复核：`python project/experiments/full_pin_xy/test_buffer_graph_contract.py`，包含反向buffer/循环/改变原网/NULL端点的失败反例；`python project/experiments/full_pin_xy/validate_repository.py`。完整报告刷新：`python project/experiments/full_pin_xy/refresh_continuation.py --root work/huangpingyang04-lgtm/126/analysis --out docs/experiments/issue-126-full-pin --gates-only`；独立浏览器QA：`node project/experiments/full_pin_xy/qa_report.mjs docs/experiments/issue-126-full-pin/report.html work/huangpingyang04-lgtm/126/analysis/gate-report-qa-r10`。

远程冻结驱动分别运行buffered_eco_job.sh / parent_region_job.sh / antenna_netmap_job.sh；实际参数、源码SHA、输入SHA、native命令及失败在gate-r08原文中。前者证明同硬存储合同下原映射端点有向关系，不是RTL形式等价；区域图使用真实矩形，不删除OBS；天线按原RDB实际金属多边形正面积相交追踪，不用bbox或几何关联冒充LVS。真实ANTENNA_X1仅完成库存核实，尚未插入/路由或通过原1460项天线规则。[KLayout原生antenna_check语义](https://www.klayout.de/doc/about/drc_ref_netter.html#h2-antenna_check)仅用于解释原规则行为，不能作为制造签核资格。

实际成本diode驱动run_antenna_diode_eco.py/antenna_diode_access.tcl保留原单元/所有端点/原pin/PG/OBS/外框/SDC/路由层，以原生636网实际receiver为定位依据；只新增真实库diode及真实负载，源SHA和逐diode坐标入回执。独立run_antenna_diode_stream.py在源结束后严格合并并执行不修改原deck，未完成路由明确不执行，不能由Slurm/native0代签。audit_actual_leaf_paths.py使用相同SPEF重读完整关键路径；plot_actual_critical_paths.py按真实相邻arrival统计cell/net arc，非线长或无线下界；全量VECTOR有向合同复用verify_buffered_eco.py并传入vector。具体driver commit/作业号/原命令见2026-10-29交接与gate-r10快照，禁止复写活动输出。

SYSTEM同网表buffer重排使用output_chain_placement.tcl/run_output_chain_placement.py，所有输出纳入选择，仅移动真实私有identity链，不新增/换型/改网；原失败92921及检查点保留。resume_output_chain.py在无Lib/SDC的新原生进程合法化同一检查点，恢复真实原状态并核查连接/非选中位置；再新进程按原Lib/SDC重布线/提取/STA。成功的中间合法化不替代最终物理门槛。gate-r12对已关闭native阶段的ODB/合同文件索引SHA，检查点及原命令由交接和原回执绑定。

Issue126原生共享导体：audit_actual_shared_conductors.py从真实fixed_prewires_NOT_FROZEN.odb导出DEF，逐项核对256个FIXED metal10属性、net/port绑定和实际bbox；r02按SHA复用已完成r01导出，保留真实缩进解析失败。plot_actual_shared_conductors.py绘制真实PG/OBS/施工port，不画未知via或把总览ROI冒充金属占地。verify_passive_load_eco.py全量核对原映射端点和新增真实非驱动负载，原生图导出来源、观察中的receipt与稳定ODB分别记SHA，不能因metadata继续记录DRC就重算/伪称几何变更。原生接线/RC通过与新增cap2失败分开报告；完整规则/RTL形式/两个系统资格仍未闭合。重现命令及driver commit在2026-10-29固定导体与diode交接及gate-r13原文。


Issue126 R47：`all_llsys_access_caps_job.sh NEW_REV via_then_wire`只读审计真实同网via及WIRE双轨道点，`llsys_residual_pin_job.sh NEW_REV`逐位读取剩余87位真实端点；不能将候选/未使用声明与实际接入混写。`llsys_owned_cap_access_job.sh NEW_REV`在新目录执行原生pin-only接入ECO，保留原WIRE/VIA/stub成本，独立完整pin/单元/PG/全网/fresh/RC-STA，父层AP另验。`obs_union_api_job.sh NEW_REV`核实已安装KLayout含孔整数并集分解；`obs_union_compaction_job.sh NEW_REV`对闭合四tip源实际M1-M3 OBS做整数XOR/非目标字节/pin/尺寸及OpenDB逐矩形导入核对。几何分解等价仍不替代router/DRC、PG、父层接入或系统资格。所有脚本使用获授权ROOT、已提交独立driver及hpy-Slurm资源，不覆盖活动输出。最新运行/终态与raw SHA见qualification_matrix.json及R47交接。


Issue126 R48：`guide_free_drc_probe_job.sh NEW_REV`对真实770支路失败只移除dbGuide副本元数据，独立核对物理导出及两份同命令DRC；r01计数被导出器覆盖的原文保留，r02实际11115→0且两Short不变，未证明性能收益。`sbatch --cpus-per-task=2 .../guide_free_drc_probe_job.sh NEW_REV owned_cap_stage`进一步对当前10261-pin实际源做同物理全叶控制，绑定已完成的原编辑/DRC阶段、BPin及全网输出，保留原M2-M8信号/M4-M8时钟范围。只有完整物理导出与原生失败marker相同，`owned_cap_wire_restore_job.sh NEW_REV`才会尝试一个M5线尾恢复；预备驱动保持10261新接点及原层/尺寸/语义/全部via。原93343的native2与负时序不会被小样、脚本准备或Slurm状态掩盖。`owned_cap_spacing_diagnosis_job.sh NEW_REV`及`plot_owned_cap_spacing.py TERMINAL_DIR REPORT`复用真实前后71行，量化旧BPin移走的0.0049μm²金属，不把图中候选线尾当已执行。


R49当前MXU父层RC/STA：冻结driver后由`mxu_actual_parent_rc_sta_job.sh r01`执行`run_mxu_actual_parent_rc_sta.py`，只读93239终态、真实模型与原SDC；每负余量/电气违规单列，不将研究I/O夹具当系统约束。`wire_shape_coverage_job.sh r01`执行`probe_wire_shape_coverage.py`，先独立核实RECT/patch导出覆盖，再审计原叶与父层；不直接替换活动导出器。终态均用`fetch_closed_terminal.py`归档双SHA，然后refresh_continuation/validate_repository及qa_report.mjs复验。


R51原生覆盖交叉验证：`wire_shape_coverage_job.sh r03 decoder_rect`仅对闭合PATH/POINT/RECT小样读取当前真实dbWireDecoder，未修改叶块。`upper_local_bypass_job.sh r01`对闭合upper_branch_repair/r02真实全部支路/OBS搜索两处Short的M11/M12局部替换，固定M10/hook不改；搜索结果不是实际接线，必须另做原生重编码、独立DRC/全770及514图/真实256桥和下层冻结检查，RC/STA与功能另验。


R53：`native_patch_audit_job.sh r01`以0–9数组/最多3并发、每例1核执行run_native_patch_audit.py；源只读，native decoder与raw RECT逐网对照，补充PATCH用实际getCoord+delta，完整规则及PG另验。`real_diode_view_job.sh r01 llsys_owned_restored`复用真实视图导出器绑定93375新源及原SDC/SPEF，导出完整13507位LEF/详细OBS/非零时序模型；不会把负时序或缺规则写成通过。
