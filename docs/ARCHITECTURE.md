# 架构与运行

本仓库含研究资料、参考结果和实验性分层物理实现代码。`project/experiments/` 下保留 `block_hierarchy/`、`parallel_blocks/` 和 `opentpu_compare/` 的实验及证据；正式预制底座和制造工具链尚未冻结。[项目说明 v1.0](../预制计算底座项目说明_v1.0.md) 中标注的候选架构不能当作已实现硬件。

## 研究系统边界

每个Block的[私有S局部仲裁](BLOCK_LOCAL_S.md)实现位于 `project/rtl/block_local_s/`，服务器九实例验证及实际结果见[Issue177报告](experiments/issue-177-local-s-results.md)。本地核原件/源绑定用 `python -X utf8 -B work/huangpingyang04-lgtm/177/check_evidence.py`；服务器Slurm运行入口为 `project/experiments/block_local_s/job.sh` 和 `run_server.py`。原RTL阶段为九实例隔离/通用综合验证；追加的三种16KiB局部S叶宏独立300MHz物理验收与六文件实收见下方物理报告。

新增局部S的[物理实施与验收记录](experiments/issue-177-local-s-physical.md)使用 `project/experiments/block_local_s/physical_job.sh` 和 `physical.py`。在获授权的新任务目录准备Git原始blob副本及 `source-snapshot.json`，以Slurm执行，不能在登录节点直接跑重计算。长布线使用c96/UNLIMITED；每作业16CPU。命令形态为：

```bash
sbatch --partition=c96 --time=UNLIMITED --cpus-per-task=16 --mem=0 \
  --job-name=hpy-s-n4-resume --output="$task_root/slurm-%j.out" --error="$task_root/slurm-%j.err" \
  "$task_root/source/project/experiments/block_local_s/physical_job.sh" "$task_root" \
  --mode resume --variant n4 --resume-after grt --route-repair none \
  --physical "$prior_physical" --out "$task_root/physical/n4"
```

`task_root`必须是新建的本人任务目录，`prior_physical`指向本次任务内已验证的源检查点。全新实现先map、prepare，再按六阶段stage执行；续跑只复制回执/日志证明成功的前缀。resume-after grt核验原生成功退出后的哈希表，只执行剩余原生详细布线、填充与别名输出目标。所有依赖使用afterok，输出目录不得复用。完成后seal，再独立执行physical、drc、function、formal（依赖function）和deliver；只有全部门通过才可报告资格。各精确源码、命令及输出SHA由运行回执绑定，当前验收状态见上述物理报告。

N5实测单端点hold修复使用同一Slurm入口，参数为`--mode repair --variant n5 --repair-instance wire1414 --sealed <本次原N5封存目录> --gates <原N5失败验收目录> --out <新的物理目录>`。它核实际失败来源，只允许测量路径上的单缓冲等价替换，并核完整DEF、实际A/Z/VDD/VSS导体接触和完整原生DRC；之后重新原生final-report/RCX。它保留原六阶段来源与独立ECO回执，不将历史阶段重新冒充执行。新输出仍须seal并重新运行全部四门；原失败目录不得复用。

拟研究的流程是：目标计算图与需求 → 预制 Block 资源映射及调度 → 预埋资源选择和受限布线 → 定制互联与成本／性能／能耗评估。预制内容、制造时定制内容和运行时状态必须分别建模；工艺堆栈、端点电气合法性、存储供给与时钟网络不能省略。

局部S最终实收复核：

```powershell
python -X utf8 -B work/huangpingyang04-lgtm/177/check_physical_evidence.py
python -X utf8 -B work/huangpingyang04-lgtm/177/check_physical_evidence.py --raw-root /absolute/received/evidence/raw --files-root /absolute/received/files
```

默认只重读提交的原始报告子集；第二条才重读完整小原件和21份文件/图，实际路径见物理报告。P4两缓冲ECO入口为`--mode repair --variant p4 --repair-instance reset-prefix --repair-count 2`，仍须提供实测失败来源的`--sealed`和`--gates`并使用新`--out`；N5为`--variant n5 --repair-instance wire1414`。ECO原生最终LEC/RCX/读回后，重新seal及physical/drc/function/formal/deliver，不能省略四门或重用失败来源资格。

## 当前计算宏与实现状态

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
