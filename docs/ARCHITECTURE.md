2026-10-29 09:24 CST：329六项全部通过，443391单元映射，93097.4自然COMPLETED/0:0；源ddf2ed5/RTL4c0d3647…，五行为项三初态各565599检查/413506拍，公共42/扩展36案例、组合和延迟通过。333七项实际占用/有限S16KiB-V/模型长度全过，93097.5自然COMPLETED/0:0约49秒，无新allocation；53原始/39稳定绑定、305源Git blobs/receipt输入核验。135有限场景与327完全相同，当前全局统计Softmax入口周期不变；新增2拍仅本地组合Softmax。已按333新源重算80预算、成本字段完全相同。330全新原生ready，但8个本任务allocation满额，未分配；331最终四门/六文件/完整几何和332接口按真实前置。R309 ABC映射/311/312/313继续；原322/316/306/291/236不因慢取消。M/S/T接收保持，V/R最终未齐；Issue121=in_progress、PR122=draft、目标active；登记pending、看板unverified/同步pending、管理员及独立审查待指定。

当前V修订（2026-10-29 08:33 CST）：321分母流水五项行为验证已过、映射运行；后继选择322→323→324及325有限S/V/占用重测。下文315/319/316为上一版源的已记录结果，不能转移到当前RTL。R309→311/312/313、M/S/T接收保持。见[分母流水决定](decisions/2026-10-29-block-v1-v-norm-denominator-pipeline.md)。

# 架构与运行

2026-10-29修订主线：[五宏实现合同](BLOCK_V1_REVIEW_CONTRACT.md)、[300MHz验收计划](plans/block-v1-review-300mhz.md)及[新版交付入口](../work/YUZE-LU/121/delivery-300mhz/README.md)。当前最终接收M/S/T；V315全部六项验证通过，316原生P&R进行，后继317最终门/文件/完整几何及318接口等待真实前置。R309数值/端口及310占用通过、映射进行，后继311原生/312最终门/313接口等待真实前置。原306/291/236正常收尾，旧源物理资格不转移；307/308只退役未分配未来选择。

当前V复现使用worker.py模式`revision300-test-v`、`revision300-map-v`、`revision300-bench-v-{revised,extended}`、`revision300-vector-boundary-{composition,latency}`，各16CPU，真实源/工具/命令/输入SHA见run315逐项receipt。主RTL的8共享乘法器前增加操作数寄存，逐元素total/RNE分级；实测逐元素5拍、统计4拍。用`revision300-sv-workspace`及`revision300-model-sv-bench-{0,1,2,3}`复现319有限S/V调度，五项各27场景×两初态，初始S写入、实际S响应、全组屏障、回放及消费均计价。3072元素RMS/L2各10479拍、Softmax16707拍；不授予集成物理或系统吞吐资格。

当前占用模式`revision300-occupancy-{v,r}-{revised,extended}`，各16CPU：V319绑定315公共测量，R310绑定309，公共结果/周期/流量必须逐项一致。`--public-flat-rw`只读实际phase/valid/operand_valid/fetch_done/row_valid，使能与填排空分别计数；不是功耗或有用MAC峰值。旧268/269/273/274保留历史证据，不能充作新流水占用。有限预连实际试验为282的`revision300-preconnect-trial-{m,t}`，M/T副本16路径、原生DRC0及缺via负例通过；生产宏未采用下层固定预连，未来可变连接依赖M11/M12。

有限预算命令：`python project/experiments/block_v1/revision300_resource_budget.py work/YUZE-LU/121/review-20261028/RESOURCE-BUDGET.json`；当前输入283真实矩阵、309递推/卷积和319真实S/V周期，保留每层屏障及有限容量。80候选已重算；300MHz与主机10ms预留是规划假设，结果不授予整模型10token/s/整数质量。已有通过实验不为填槽重复运行。

只读路径诊断模式`revision300-checkpoint-timing-v`读取源归档中selector选定的已完成placement；320只绑定316，实际do-place未完成前无allocation。前后核对ODB/SDC/网表/配置/库/setRC SHA，原流程继续，不改数据库。全部EDA与Verilator仍经worker.sh/worker.py在Slurm内执行，不在登录节点运行。

[V/R端口性能](../work/YUZE-LU/121/review-20261028/vr-bench-0225/README.md)的真实命令、工具SHA及源码commit见逐任务receipt。268的模式为revision300-bench-{v,r}-{baseline,revised,compare}；269的模式为revision300-bench-{v,r}-extended。source_commit分别0d001311ff49fd86e58b7e2dceedb68ee5fceaca和074a5365439e8c789f126649010609ae8283f150。每模式16CPU，容器和编译器由worker.sh固定；受控原队列见[node-queue-268.json](../work/YUZE-LU/121/review-20261028/node-queue-268.json)及[node-queue-269.json](../work/YUZE-LU/121/review-20261028/node-queue-269.json)，完整allocation argv见对应stage manifest。复现必须先用bundle.py从实际Git blob建立新源归档，选新run目录，经dispatch.py的八节点上限/unknown提交核验；不得覆盖封存目录或重交已通过队列充数。

旧/新公共测量使用完全相同数值参考，基线RTL另按baseline-vr-sha256.json与ad3c2b3核对；长组扩展先全统计后有限回放。所有相位、应答、状态导出、容器/填充开销明示；模型速度、内部lane占用和实际S执行均不由这些测量自动取得资格。

以下旧实验入口及100MHz结果保留其历史证据范围，不代表新版通过。

当前第一版计算积木为 **M/V/R/S/T五个物理宏，每种一个基础实现**；逐块最终M1–M10布局布线是本轮交付。见[规格](BLOCK_LIBRARY_V1.md)与[逐块计划](plans/block-v1-library-implementation.md)。M新最终物理/功能已通过部分接收但原生M2 DRC未过，R实际RTL已通过，V新实现待实际回归，S独立route中，T沿用已接收C叶块；不能以旧M8/VS四边界替代这五块。下方历史实验保留原证据范围。

当前Block主线见[首版逐块实施计划](plans/block-v1-library-implementation.md)。`python project/experiments/block_v1/make_library.py --check`验证新M8/VS/S16K独立候选及源码逆重建；它不代表数值或P&R通过。`library-v1-source`、`library-v1-byte`及`library-v1-map-<top>`提供原生层级检查、八lane数值与完整标准单元映射，后继仍须逐块完整物理接收。

`native-c8-formal-diagnosis-group` 在2CPU内两路1CPU对134实际失败作只读图/边界诊断，子模式 `native-c8-formal-diagnose-<a|c>`；只诊断未匹配输入，不改变任何LEC验收门，详见[严格对应诊断](decisions/2026-10-27-block-v1-c8-formal-input-diagnosis.md)。

C8有限预制前实际修复探针为 `native-c8-probe-group`（4CPU内两路2CPU）及 `native-c8-probe-<a|c>`，绑定128/162/163；完整原生/宏资格仍独立。离线命令 `python project/experiments/block_v1/native_c8_legalize_control.py work/YUZE-LU/121/results <含c8-upper163-a/c.tsv的授权目录> <全新JSON路径>` 校验真实源几何、确定性、完整upper接触及12组独立穷举spacing对照；算法边界见[障碍事件接入](decisions/2026-10-27-block-v1-c8-obstacle-escape.md)。`native_upper_index_control.py` 接受位置参数 `<含upper159-a/c-before/after.tsv的授权目录> <全新JSON路径>`，没有额外help子命令。

T6K修复后同源视图使用 `native-escape-view-group`（16CPU，两路8CPU、保守内存门2/1路）及 `native-escape-view-transaction6k-<a|c>`，绑定160成功原生最终输出、161完整物理及最终功能、145真实Lib pin/bus控制；配置 `native_pipeline_escape.json`。`python project/experiments/block_v1/native_escape_view_control.py work/YUZE-LU/121/results <全新JSON路径>` 重放真实161来源绑定和18个破坏副本。现有 `native_view_control.py` 另含7种真实stub编排控制，均不能替代实际EDA。实际161证据和视图限制见[完整接收与视图入口](decisions/2026-10-27-block-v1-t6k-received-views.md)。

`native_c8_escape.py` 是有限C8文本候选构造，尚无实际ODB编辑资格；`native_upper_index.py` 加速全部上层跨网接触候选筛选，谓词与原穷举相同。`python project/experiments/block_v1/native_upper_index_control.py <授权159几何目录> <全新JSON路径>` 重放四份SHA绑定159几何及声明控制的完整对照；原始几何仅在授权存储/本地诊断目录，仓库保留报告。不得把语法/index控制当作实际修复或原生DRC通过。

Block v1 新预制候选的同源候选视图入口为 `native-prefab-view-<shared109|transaction6k>-<a|c>`；单32CPU内四路8CPU的 `native-prefab-view-group` 根据实际内存选择4/2/1路。必须先有128/134（C8）及133/135（T6K）的完整成功物理回执，再使用其最终ODB/SDC/SPEF/GDS生成并读回LEF/Liberty；不会使候选视图自动成为合格宏。`python project/experiments/block_v1/native_view_control.py <全新JSON路径>` 仅验证来源反例及实际stub编排。来源、内存估计与尚未验证的输入线阻/边界时序限制见[同源视图决策](decisions/2026-10-27-block-v1-prefab-view-sources.md)。

`native-timing-model-probe-group` 是独立的实际封存T6K模型导出/接口诊断：单16CPU allocation内A/C两路8CPU，逐文件绑定133完整生产者与最终五文件、准备pin来源，保存真实timing arc类型/数量和原生库读回；不读取未封存数据。它允许物理接收尚未结束时诊断，但所有资格标志保持false，`diagnostic.lib`不能代替正式源资格视图或完整边界验证。

本仓库含研究资料、参考结果和实验性分层物理实现代码。`project/experiments/` 下保留 `block_hierarchy/`、`parallel_blocks/` 和 `opentpu_compare/` 的实验及证据；正式预制底座和制造工具链尚未冻结。[项目说明 v1.0](../预制计算底座项目说明_v1.0.md) 中标注的候选架构不能当作已实现硬件。

## 研究系统边界

拟研究的流程是：目标计算图与需求 → 预制 Block 资源映射及调度 → 预埋资源选择和受限布线 → 定制互联与成本／性能／能耗评估。预制内容、制造时定制内容和运行时状态必须分别建模；工艺堆栈、端点电气合法性、存储供给与时钟网络不能省略。

## 目录约定

| 路径 | 用途 |
| --- | --- |
| `README.md`、`研究资料导读.md`、`预制计算底座项目说明_v1.0.md` | 项目入口、阅读导引与初版研究定义 |
| `docs/` | 当前项目简介、架构、状态，以及专题研究文档和重要决策 |
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

### Block v1 原生十层预制与新增两层互联（Issue 121）

当前授权范围为[五宏逐块实施计划](plans/block-v1-library-implementation.md)：M/V/R/S/T，每种一个基础实现，完成各块最终M1–M10布局布线与接收。[五宏规格](BLOCK_LIBRARY_V1.md)、[命令合同](BLOCK_V1_COMMANDS.md)及[当前最终交付索引](../work/YUZE-LU/121/delivery/README.md)是当前入口；[原多阶段计划](plans/block-v1-nangate45-m11-m12.md)和以下C8/overlay流程保留为历史工程基础，不将其全部系统目标追加到本轮。执行代码见 [block_v1](../project/experiments/block_v1/README.md)：

```powershell
python scripts/check_project.py
python project/experiments/block_v1/make_wrapper.py --check
```

`project/rtl/block_v1/transaction6k.sv`为真实有限事务壳，`shared121.sv`将其与四profile C8集成，结果端口改为已提交数据流，旧provisional driver必须适配后才可用于新顶层验收。服务器worker的transaction、完整存储映射、core-build、overlay、fixtures模式通过同一dispatcher在获授权目录运行，命令/资源/输入输出SHA与失败均保留。几何overlay和early RC不是十二层提取/DRC资格；尚未完成部分不得表述为已硬化Block库。

模型分析目录的归档检查命令为 `python -B work/YUZE-LU/116/validate_archive.py`，核对文档/图册本地引用、导入产物 SHA、报告迁移及原 Issue #114 证据不变。此检查不重新运行模型、onnxsim、RTL 或物理实验。

新增实验应记录代码 commit、工具和配置版本、输入数据版本、输出位置及 SHA-256。大体积物理数据库、原始日志和工具环境应使用项目约定且有权限控制的共享存储，并在仓库中保留可核对的索引。本轮已获授权的集群目录见上文；更长期的共享存储和访问策略仍需明确。不得将凭据写入仓库。

Block v1 原生候选入口为 `native-prepare`、`native-floorplan-<shared109|transaction6k>-<A|C>`、`native-boundary-audit`、`native-run-<shared109|transaction6k>-<A|C>`，经 `worker.sh <只读源码根> <模式>` 在实际Slurm allocation内运行。来源由 `native_pipeline.json` 指定不可变052/054/055/056链，必须先核对每段回执/SHA。054采用052同构证明的结构网表，生成实际ns/fF/kOhm的完整SDC；055只做导入和未放置几何检查；056独立核对STA写回。057依序运行ORFS显式do阶段，保存原生平台实际变量、只读独立输入及逐阶段SHA，不触发普通目标的RTL重综合依赖。配置、节点/CPU/UNLIMITED、源码bundle SHA见 `work/YUZE-LU/121/stage53-manifest.json`。

只读采集示例（输出目录必须全新，旧索引不覆盖）：

```powershell
python project/experiments/block_v1/collect.py block-v1-20261027-057 .local/issue121/observations/run057-new
```

该采集不是合格接收器。原生候选成功后仍须精确最终文件的功能、全端点STA/电气、PG/连接/独立几何、RC覆盖和完整资源计价；十二层研究RC与共同底座/两产品另行验收。兼容和单位修正的失败历史见[输入决策](decisions/2026-10-27-block-v1-native-candidate-inputs.md)。


Block v1 独立最终物理入口为 `native-receive-<shared109|transaction6k>-<A|C>`，从 `native_pipeline.json` 的057源候选读封存回执，并要求066真实STA/漏RC控制通过。必须通过dispatcher的对应 `after_runs` 依赖，不能在源作业结束前读最终文件。通过 `worker.sh <只读源码根> <模式>` 在32CPU allocation中运行；源码由 `python project/experiments/block_v1/bundle.py <新归档>` 精确打包。完整门级的 `mapped-parallel-suite` 保持同004网表/单元模型/13命令/两背压接收，32CPU内同时两模型各16线程，非缩减测试。轻量索引新增STA/物理/窗口结果名，原历史索引不覆盖。


原生候选当前版本转向 `native_pipeline.json` 的075准备/076导入/077边界/078 P&R链。054–057为保留的历史输入/运行，不能因其pin坐标与旧计划一致便当作实际track资格。新planner读取原生M9/M10 make_tracks与via9 cut规则，实际DEF track读回及旧偏移负例属于076门槛。完整状态看对应回执，不能按run编号推断已执行。`native-formal-control` 的073版本通过真实DFF buffer/drive-strength正例、D/CK/输出变化及五类报告负例；最终接收严格要求完整归一化的非空PI/PO、零差集和显式UNSAT/IDENTICAL，不以grep无报错代替证明。


当前原生链已更新为077准备/078四组floorplan/079边界/080原生P&R；075/076失败链与旧057运行保留。078的实际DEF轨道和全部pin精确对齐验证已通过，076的`%g`序列化偏差不得以容差豁免。最终独立接收器读取当前080且必须等对应源回执通过；源数据库不能在接收期间改变。074外部节点对局部通量/FV探针11项门槛通过，仍不是完整分布式RC资格。


`partial-geometry-group`在96CPU allocation内通过两个独立worker各48CPU并行`partial-branch-fv`/`partial-via-fv`，生成`partial-geometry-group.json`绑定所有子回执与结果；双方都通过才组通过。084为当前待调度版本，082/083未提交、不再调度。仍通过同一dispatcher，不能额外绕过节点预算。`collect.py`在没有job ID时保留空sacct，不以空`-j`查询其他作业。


当前场解合并运行是087，已成功封存；084同082/083从未提交，不再调度。原生080 T6KC仍有8个电容违例，新增 `native_pipeline_cap20.json` 的088/089独立修复链，使用 `native-cap20-run-<top>-<A|C>` / `native-cap20-receive-...` / `native-cap20-view-...`。从封存080 CTS只重跑标准route/final，配置严格原077加CAP_MARGIN=20，预算和电气限值不变。详见[电容修复决策](decisions/2026-10-27-block-v1-native-cap-margin.md)。默认080/085/086链和历史057/081不改；接收及宏视图按明确pipeline/source绑定，不能混用。


三维图节点资格链：090模式`fsv-graph-build`从同一固定原作者源码包构建明确记录的研究patch，重跑默认goldens/平面与线程/非法节点控制。091 `graph-geometry-group`在一个96CPU allocation内两路48CPU运行`graph-branch-fv`/`graph-via-fv`，依赖090成功；独立FV按真实导体面位置分桶，保持原矩阵/边界/求解器和锁定阈值。当前均只部署未提交；具体限制见[图节点电荷决策](decisions/2026-10-27-block-v1-graph-charge-partition.md)。collector保存graph patch/build control/FV及合并回执，不能把构建通过当作局部科学或完整分布式RC资格。


088封存结果仍有1个cap违例，093/094/095是有限CAP_MARGIN=40候选/接收/视图链，入口`native-cap40-run-...`、`native-cap40-receive-...`、`native-cap40-view-...`。20和40档均绑定原080 CTS、原077配置加唯一margin行，保留原限值及LEC/预算；GDS显式do-target先在独立输出树准备logs/reports/objects。`dispatch.py MANIFEST --submit --only EXISTING_TASK_ID ...`只选择现有任务，不改manifest/依赖/8节点上限，记录实际dispatcher源码SHA；080 T6KA已经用该过滤启动，C8A保持待执行以避免与node21科学任务争用。

`routed-graph-field`严格绑定run051原真实接入路由的DC图、run043导体mask、run090图节点二进制与run091两几何科学资格，三档offset各33554432 walks、三路线程总和不超过allocation。输出`routed-graph-field.json`，只接续单隔离网络origin-node电荷；尚无该长路由独立局部FV、一般capture-node耦合、新旧层拼接或全Block资格。

`routed-graph-view`依赖run096真实测量成功，逐节点/边原生OpenDB读回SPEF，并以实际导入的单位错误、保总量节点电荷/边电阻调换作负例；输出`routed-graph-view.json`。当前仅本地合成读回接收控制通过，实际工具与测量回装未执行。


实际捕获节点研究：`fsv-capture-build`在固定原作者源码、partial及graph补丁后应用`capture_field_patch.py`，重跑默认goldens/原node-to-net和新终点节点的线程、边际、非法输入与真实短路控制。099使用16CPU、全局8allocation内调度，当前尚未运行；`capture_field_verify.fv_source`导出独立FV真实导体面Dirichlet基函数的双向联合矩阵，本地精确LU变换控制见`work/YUZE-LU/121/capture-reference-transform-controls.json`，不代替科学收敛。见[捕获节点边界](decisions/2026-10-27-block-v1-terminal-node-charge.md)。


`capture-geometry-group`在96CPU内两子worker各48CPU执行`capture-branch-fv`/`capture-via-fv`；每子任务4网格单线程与6场解各7线程，均绑定099构建和033FV安装回执。独立FV真实面基函数返回双向joint矩阵；接收器检查锁定收敛/局部/互易与保边际错误重连，合成控制不代替实际科学运行。collector保存子回执/组回执及输出SHA。当前源码待部署，实际尚未运行。


最终物理网表行为：`native-final-t6k-a`/`native-final-t6k-c`绑定cap40封存源093的6_final.v和原073 LEC控制/077输入，直接用实际网表与同一Liberty导出的单元行为构建Verilator，不替换RAM、不重新综合网表。每allocation16CPU，三模型各最多6线程并行，运行完整242事务队列scoreboard，全1及两个随机初态；结果要求完整计数且三个初态响应一致。该零延迟检查不代替STA/四态、宏边界、C8最终功能或共同底座回装。当前代码未部署执行。


独立DRC分类：`python project/experiments/block_v1/native_drc.py <native-drc.lyrdb> <new-summary.json>`保留所有项、数值、原报告SHA及分类，不过滤天线/间距。native_receive后续run自动绑定summary SHA；本次实际094失败已原样保存，不能用DRT零项替代。098内部节点collapse修复参见节点电荷决策，102重跑仍须实际执行。101已实际部署并启动92144，前述“未部署”保留为提交时快照。
## 原生 Block 修复入口补充（Issue121）

`project/experiments/block_v1/native_pipeline_hold5.json` 定义从封存 CTS 增加 5 ps 严格 hold 目标的有限分支；`native_drc_locate.py/.tcl` 只读定位独立 DRC marker。配置、定位负例和资格边界见[修复决策](decisions/2026-10-27-block-v1-native-hold-and-drc-repair.md)。运行由既有 `worker.sh` 和统一 `dispatch.py` 的 manifest 入口完成；未通过完整接收不能生成合格宏。

原生扫描后，正交多边形与原矩形的精确相交面积可在本地重算：

```powershell
python project/experiments/block_v1/native_drc_geometry.py work/YUZE-LU/121/results/run103-first-native/index.json work/YUZE-LU/121/results/run094-terminal/native-drc-summary.json work/YUZE-LU/121/results/local-polygon-diagnosis.json
```

输出须使用尚不存在的路径。该步骤保留原包围盒候选，消除凹多边形空白区导致的误命中；面积命中仍不能替代 GDS 电气连通或 DRC 清零。

## C8 物理常量导入及完整预制修复（Issue121）

最新实际状态：137 glue与140初始化控制通过；141组合依赖140（138失败保留、139无job停用），已不可变部署但无Slurm job，仍待128两路。源码模块SHA95c40d9feff5a3ff5de3352ce18b27501dc8a735fa1ec34c550d3137fc352c70绑定140控制，后续改动必须重新取得同版本控制。135四路完整T6K资格已实际运行，尚无通过结论。下文“未运行”等说明保留为各源码提交时快照；最新依据见[组合实证](decisions/2026-10-27-block-v1-final-composition.md)。

`native-composed-init-control`先用安装Verilator/实际Liberty的128个DFF验证参数解析先于DUT构造、全1/两随机初态；`native-composed-group`随后以48CPU内A/C各24CPU组织实际最终两叶和映射glue的完整混合整数接收，每子任务三初态×两背压、每模型4线程。`worker.run`的可选cwd只用于叶视图隔离目录，日志记录实际cwd；旧调用不变。独立数学接收器对新物理分支再次核实际源/LEC/全信号视图/库/驱动和编译参数，原数学/旧分支不放宽。当前仅Python编译通过，实际初始化/组合未运行。见[组合决策](decisions/2026-10-27-block-v1-final-composition.md)。

新增 `native-glue-map`（`native_glue.py`）通过既有 `worker.sh`/统一 `dispatch.py` manifest 入口运行，8CPU内四个两OMP线程的实际Kepler案例并发。它只映射真实 `shared121.sv` 的父层有源 glue，保留两叶接口；Yosys原RTL/mapped完整组合边界等价、精确常量逆还原、实际命令/ACK/revoke三反例与逐master面积均须通过。结果为 `native-glue.json`，两叶及父层物理资格另验。见[glue计价与边界](decisions/2026-10-27-block-v1-real-glue.md)。当前尚未服务器运行。


`native_pipeline_const.json` 的123/124/125分别是常量准备、双pin导入、完整边界审计；正式长实现采用 `native_pipeline_const_protected.json` 的128/134，126/127未提交、不再调度。新worker模式为 `native-const-protected-run-shared109-a/c` 与 `native-const-protected-receive-shared109-a/c`；manifest任务ID保持 `native-run-shared109-a/c` 和 `native-receive-shared109-a/c`。各run通过统一 `dispatch.py MANIFEST --submit`、跨run依赖和八allocation预算调度。归档命令 `python project/experiments/block_v1/bundle.py NEW_SOURCE.tar` 从Git字节绑定提交；正式P&R从新源全阶段开始，不复用旧CTS。

`native_const_prepare`严格绑定118的完整常量还原、错误常量拒绝、旧14条无驱动负例和新导入/T6K零无驱动正例。`native_floorplan`与`native_receive`在实际ODB运行 `native_undriven.tcl`，由 `native_driver_report.inspect`核明细与terminal summary，保存 `used-signal-drivers.tsv`；连到dbNet不能替代真实driver证明。`native_run.checked_fresh_config`核原123配置加唯一固定保护/修复后缀、实际make变量与hash；全部原预算/端点/检查不变。当前实际导入/边界已通过，128两路正在placement，尚未物理通过。129仅部署无job、停用后续调度；130旧源未提交，停用；后续134以 `native-const-receiver-group` 组织同一64CPU allocation内两个32CPU完整独立接收器，依赖128两路成功。实际内存快照决定同时两路或串行，记录各子回执及组回执；本地声明stub编排控制不能代替物理接收。见[节点内并行安排](decisions/2026-10-27-block-v1-node-packing.md)与[计算资源参考取舍](decisions/2026-10-27-block-v1-compute-reuse.md)。


131同节点DRC/STA诊断实际通过；新 `native_receive` 的保护输入分类严格绑定其实际控制回执、同SHA库/分类模块和实际ODB精确清单，原始STA报告及全部物理负载保留。见[保护端点诊断与实证](decisions/2026-10-27-block-v1-passive-endpoint-diagnosis.md)。原120仍因23项DRC失败，不能冻结宏。


有限via-only原生修复由 `native_pipeline_viaonly.json`、`native_via_route_group.py` 和 `native-via-route-group` 入口执行；实际输入绑定与覆盖参数风险见[接入证据及完整布线门槛](decisions/2026-10-27-block-v1-via-only-route.md)。两个叶任务目录仍为tasks/native-viaonly-run-transaction6k-a/c，独立回执，父组仅合并，不代替后续完整接收。


`native-via-qualification-group`组织A/C完整独立物理接收与A/C实际最终网表三初态功能回归，共四路各16CPU、同一64CPU allocation。依赖133完整候选成功；按实际可用RAM选择4/2/1路，不缩减每路门槛。可复算编排控制：`python project/experiments/block_v1/native_via_group_control.py NEW_CONTROL.json`（输出须不存在）。当前三个实际stub控制通过，仅证明并发/失败独立/内存降级，实际EDA资格另由135产生。


135完整资格终态失败：A18/C2独立间距标记，原生DRT均0；功能通过不替代物理。148 `native-viaonly-diagnosis-group` 在同一16CPU allocation内两路8CPU只读定位，绑定133/135不可变源及全套哈希；147依赖失败且无job停用。详见[保护负载与间距诊断](decisions/2026-10-27-block-v1-passive-endpoint-diagnosis.md)。


148实际双路只读定位通过但间距未修复；阶段 CPU/内存、原生 DRC 固定4核及后续节点内并发规则见[节点内并行决策](decisions/2026-10-27-block-v1-intranode-parallelism.md)。

`native-escape-probe-group`为预制冻结前的有限M9/M10/via9接入线修复探针：同一4CPU c96 allocation内A/C各2CPU，既有整节点内存申请、实际内存预检与独立失败保留。语法/锚点/范围/连通控制命令为`python project/experiments/block_v1/native_escape_control.py NEW_CONTROL.json`，输出须不存在；149b含边接触控制。149因16G申请不兼容提交前拒绝无job；150实际读回拒绝INCREMENTAL未导入网络，失败保留，151修正为FLOORPLAN网络导入尚待实际运行。完整源绑定、OpenROAD精确读回、实际上层mask与诊断DRC、源18/2标记复现以及后续新寄生/完整接收要求见[有限修复决策](decisions/2026-10-27-block-v1-native-escape-repair.md)。诊断不等于宏资格。

152实际因源合并mask报告条数不等原完整GDS而失败，并发现A新增3条VIA9.2；失败均保留。153严格保持全部via身份/原坐标，只简化M9树枝和M10折返；新增完整原GDS upper-mask XOR，并直接在原GDS复现18/2源标记，after诊断仍需0。153声明合成控制通过、实际EDA未执行。完整物理接收与新寄生/功能仍独立必需，详见同一有限修复决策。

154实际有限探针两路10门全部通过，仍不等于完整宏。155 `native-escape-finish-group`以同一32CPU allocation内A/C各16CPU重新运行原生do-6_report/RCX/LEC，严格保持154接受副本全部几何/网表/SDC，并在实际最终ODB上重跑原生全片check_drc；156 `native-escape-qualification-group`在155完整成功后组织两物理/两最终功能各8CPU、共32CPU的四路完整接收。`native_pipeline_escape.json`统一绑定源、接收和154探针，`native_escape_finish.checked_config`拒绝未绑定/变化的配置、probe、脚本或实际DRC。实际155/156本源码提交时尚未运行；所有完整接收门保留，细节见有限修复决策。

159有限via9修复的声明控制（输出必须不存在）：
```powershell
python project/experiments/block_v1/native_escape_relocate_control.py work/YUZE-LU/121/native-escape-157-routes.json NEW_CONTROL.json
```
实际159探针与160/161全片/完整接收仍分别运行；声明控制不是物理资格。

C8最终数据库新增全片原生DRC：`native-whole-drc-group`（16CPU）在同一allocation内启动`native-whole-drc-c8-a/c`（各8CPU），绑定128成功源并要求实际新全片报告0、检查前后完整DEF及源SHA不变。`native_whole_drc.py`先保存失败报告再断言，不能仅采用route阶段0报告；仍须134完整物理、141完整组合及全部宏/十二层门。

C8最终原生全片失败的只读定位：`native-c8-locate-group`（4CPU）在一个allocation内启动`native-c8-locate-a/c`各2CPU；绑定128最终成功源及162真实失败，输出`native-c8-location.json`、完整源DEF/几何和实际固定port、逐标记命中/未匹配、固定via文本提案及不支持列表。不编辑ODB，不替代完整物理资格。


T6K完整接收后的供电/时序交付入口为`native-typed-view-group`（16CPU）、`native-typed-view-transaction6k-a/c`（各8CPU）。保留candidate-raw.lib，candidate.lib只转换两个经严格验证的PG伪输入，原生native_pg_pins.tcl独立检查power/ground类型。candidate-timing.v为161物理接收完整ODB信号Verilog的SHA副本；完整SPEF的flat对照不可使用过滤保护单元的6_final.v。实际控制命令：

```powershell
python project/experiments/block_v1/native_view_pg_control.py RAW_LIB_FOLDER work/YUZE-LU/121/results NEW_CONTROL.json
```

RAW_LIB_FOLDER需提供已按164收据封存的candidate164-a.lib/c.lib。只读占用入口`native-qa-occupancy-group`（2CPU）、`native-qa-occupancy-a/c`（各1CPU），使用qa127_pinned/source_occupancy.tcl固定PR128/5eda23a字节与原odb_geometry.tcl，在独立目录导出actual wires/special wires/transformed pin/master OBS/NET→PORT。新170`native-c8-graph-inputs-group`（2CPU）及a/c各1CPU从134失败后的完整图补查driver/use，诊断通过与LEC资格分开。


原生常量前端对照：native-tie-formal-control-group（2CPU）两路0/1各1CPU；完整旧C8图严格重验：native-c8-tie-lec-group（4CPU）及native-c8-tie-lec-a/c各2CPU。后者强制171实际控制、原失败134所有图SHA、实际库/Kepler一致，真实常量函数替换的精确逆变换与Yosys发射后全cell/pin-bit重读回均需通过，native_formal.inspect全部严格门保持。正式物理/最终功能接收尚未接入该候选编码。


节点耦合组装原生读回入口（准备，未实跑）：`joint-rc-native-branch` / `joint-rc-native-via`由`joint_rc_native.py`接收run100实际完整科学证明、逐节点ground和双向节点对C，`joint_rc.py`显式均值对称化后输出唯一物理C的对称SPEF表示。每候选4CPU内动态执行六种独立原生import；逐节点ground、每条R和每一对CCSeg分别读回，错单位/丢C/节点ground交换/R交换及保节点耦合边际的错误重连均须拒绝。小型无源LEF锚仅绑定电气ID，无布线物理资格。纯组装检查命令：`python project/experiments/block_v1/joint_rc_controls.py work/YUZE-LU/121/results/run100-terminal/index.json`。见[耦合RC组装边界](decisions/2026-10-27-block-v1-joint-rc-native.md)。


180实际接收已通过：`results/run180-native-node-queue-terminal`及两joint-rc-native peer索引；fixture科学资格与纯组装/原生读回分开记录。完整原生输出/SPEF/ODB仍为宏时序参考；固定PR128 cb3a089输入残差已逐项复算，输出RC反例及输出slew超差未被修正或豁免，详细来源`work/YUZE-LU/121/macro-qa128-update-cb3a089.json`。


新增`joint-routed-branch` / `joint-routed-via`：真实wire/via/pin三维导体并集逐体元匹配封存场几何，再在routed ODB原生导入六个SPEF正反例。九个纯几何控制通过，实际运行尚待182。via为单独科学fixture假设，无生产/完整DRC/一般提取/拼接资格。合同见docs/decisions/2026-10-27-block-v1-joint-routed-source.md。


新增joint-node-binding-branch/via从182封存routed ODB原生接收实际变换后的pin位置/层/ID；183准备运行，原生锚点位移/交换反例必须在并集与电气值保持相同下被拒绝。182真实导体并集与耦合读回已实际通过。


182真实导体来源与184直接实际位置门均已原生通过，183固定实例保护失败也保留。完整结果见work/YUZE-LU/121/results/run182-*、run183-*、run184-*。固定PR128 fbbd5ec显式输出RC十二个pair的记录输出逐项复算见macro-qa128-explicit-output-rc-fbbd5ec.json；只作为待审查的层次timing/RC方向，不替换物理M10pin或签发真实宏资格。
# 当前 Block v1 五宏执行入口（2026-10-27）

用户选定 M/V/R/S/T，每种一个实现，必须逐块交最终M1–M10布局布线。规格见 `docs/BLOCK_LIBRARY_V1.md`，计划见 `docs/plans/block-v1-library-implementation.md`。旧裸M8/混合VS为历史工程来源，非最终边界。

业务任务由 `project/experiments/block_v1/worker.py` 调用：`five-macro-matrix-test` / `five-macro-matrix-map` / `five-macro-store-test` / `five-macro-store-map` / `five-macro-t-pins` / `five-macro-t-layout`，各16CPU；前两对各自通过后 `five-macro-route-m/s` 独立补位。以 `bundle.py` 从精确Git对象生成不可变输入、`native_node_queue.py` 管理96CPU的6×16动态队列，`dispatch.py` 统一限制本任务6～8allocation；独立全deck/STA/PG/最终网表接收不能省略。实际结果由每任务 receipt 和业务JSON判定，不以命令列存在当已通过。

管理检查：`python scripts/check_project.py`；Python语法：`python -m py_compile project/experiments/block_v1/five_macro.py project/experiments/block_v1/five_macro_physical.py project/experiments/block_v1/five_macro_delivery.py`。数值/RTL与P&R实际执行在授权EDA容器的Slurm计算节点，不能在登录节点运行重EDA。

Linux轻量调度排空控制：`python3 project/experiments/block_v1/node_queue_drain_control.py project/experiments/block_v1 新输出目录`，输出目录必须不存在。它使用同一生产调度器和真实定时子进程，仅向隔离控制进程PID发SIGINT，检查已有子进程完成、没有新领取、遗留RUNNING claim需要独立恢复；不操作生产任务、不验证EDA。2026-10-28已对不可变203源码实际执行，来源和结果见[排空记录](../work/YUZE-LU/121/results/drain203-005449/index.json)。实际生产应用必须另核对PID、账号、allocation、代码SHA和活跃子任务，不能将该测试当作通用取消命令。当前S/R/V接收由207不可变队列接续，资源事实与恢复入口见[最新接续](handoffs/2026-10-28-issue-121-five-macro.md)。

实际M10坐标比较器控制：`python project/experiments/block_v1/pin_contract_controls.py .local/issue121/pin-contract-source .local/issue121/pin-contract-received 新输出目录`；两个输入目录分别存原source的pins.json/pins.tcl/receipt.json，以及独立接收的physical-pins.tsv/receipt.json，均按回执哈希核对。2026-10-28原始S273个接点的正例与8种拒绝反例已通过，见[记录](../work/YUZE-LU/121/results/pin-contract-controls-20261028-0119/pin-contract-controls.json)。新`five-macro-physical-*`在完整原生接收内重复这些比较器控制；`five-macro-delivery-received-s/r/v`允许新physical与207的其他三门按相同source回执汇合，额外核formal→function回执一致。实际执行脚本与未格式化计划的差别及冻结原则见[接点决策](decisions/2026-10-28-block-v1-executed-pin-contract.md)。

2026-10-28节点内CPU硬限制：`native_node_queue.py`从真实CPU affinity划分六个互斥16CPU集合，以taskset启动worker并立即补位；环境变量仍保留，但不再当硬限制证据。Linux无EDA控制命令：`python3 project/experiments/block_v1/node_queue_affinity_controls.py /absolute/new-control-directory`（控制节点须实际允许96CPU），以及`python3 project/experiments/block_v1/node_queue_controls.py`。真实32线程/后代继承、六并发/即完补位已通过；已有业务任务只原位绑定，详见[决策](decisions/2026-10-28-block-v1-cpu-affinity.md)。控制不是EDA或宏资格。


## 本轮后继队列自动准入（2026-10-29）

`project/experiments/block_v1/revision300_admission.py`只检查六个已经stage的队列：R311/312/313、V330/331/332。运行配置及启动证据在`work/YUZE-LU/121/review-20261028/admission-335/`。它每60秒检查真实叶任务前置和本成员allocation数量，复用每份不可变归档中的dispatch.py；原提交器的Issue共享锁、先写SUBMITTING reservation及包含pending/unknown的8allocation限制仍是唯一提交权威。已有任何提交记录均不重投；观察超时或会计信息缺失不视为作业结束。不会取消、修改或重启EDA。

该进程只在登录节点处理JSON、Slurm查询和sbatch，所有综合/仿真/P&R仍由Slurm内原96CPU队列执行。节点内原6×16、1.2预留/16GiB guard与即完补位机制不变。六份manifest、node-queue、dispatch.py和native_node_queue.py的SHA固定；文件变化时闭锁并记录observation_error。不是新增产品调度系统，也不改变宏或验收边界。

实际部署目录为`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/admission-20261029-335`；`status.json`是最新观察，`events.jsonl`记录状态变化，`launch.json`记录进程与源SHA。09:45捕获证实PID2121001存活且至少两轮检查。恢复先核对该目录真实进程、命令行和状态，不能仅凭旧PID或锁文件认定存活，也不能在已有控制进程时重复启动。未知sbatch结果须核对原reservation与Slurm comment，不重投。控制进程finished只表示六队列均进入可检查终态，不能代替最终五宏审计。

纯控制验证命令：`python -X utf8 project/experiments/block_v1/test_revision300_admission.py`。覆盖未知/失败/完成尝试禁止重投、前置与失败分类、8项含PENDING、其他成员及同账号无关作业不计入本任务、异常观察闭锁；本地和部署端均已通过。原EDA及最终门不能由此替代。

准入预检查只匹配本Issue目录dispatch-state记录的作业ID，不以整个账号或名字前缀单独设限。原334控制版本及暴露过度计数的同账号无关任务负例、仅终止控制进程的退役回执保留；当前335的两轮真实检查与八个原EDA作业读回见其capture-start和allocation-scope-readback.json。


## Issue130：独立供数 M 与 bank 化 S 候选

固定基线 `8b6b8d483085dd20a01e3a88a035fcc6b5db9f73` 的独立后继，合同见 [BLOCK_FEED_V1.md](BLOCK_FEED_V1.md)，实际结果与适用边界见 [Issue130证据](../work/YUZE-LU/130/README.md)。新RTL位于 `project/rtl/block_feed_v1/`，保留父任务源及运行任务。仅M/S变更，供数器固定在S中；pair为测试夹具。M已通过完整同源独立物理验收并下载，S仍待全部最终门。

Linux/WSL，Verilator5.042、g++可用时，输出目录必须不存在：
```bash
python3 project/experiments/block_feed_v1/run.py --verilator /path/to/verilator --models m s pair v r t --workers 3 --build-jobs 4 --out /absolute/ascii/new-results
```

设正确的 `VERILATOR_ROOT`；总构建核数不得超过实际affinity。Windows路径含中文时在任务自己的ASCII运行目录复制收据列出的源，避免Verilator生成Makefile的路径转义问题；只在无法读取Windows worktree元数据的WSL副本传入已核实的 `--source-commit`，真实测试源仍以逐文件SHA为准。V/R的生成夹具适配及前后字节SHA写入结果，不修改旧测试。

完整源检查／可选Nangate45映射（在Slurm计算节点执行重EDA）：
```bash
python3 project/experiments/block_feed_v1/inspect.py --yosys /path/to/yosys --abc /path/to/yosys-abc --liberty /path/to/NangateOpenCellLibrary_typical.lib --out /absolute/new-map
```

实际远程命令、不可变目录、镜像SHA及失败历史见证据README。以下本地读回不运行EDA、不产生物理资格：
```powershell
python -X utf8 project/experiments/block_feed_v1/verify_evidence.py
python -X utf8 project/experiments/block_feed_v1/test_inspect.py
python -X utf8 project/experiments/block_feed_v1/plan.py --mapping work/YUZE-LU/130/validation/remote-receive/summary.json --liberty /path/to/NangateOpenCellLibrary_typical.lib --out /absolute/new-pin-diagnostic
```

`plan.py`的全部端口引出诊断不等于新宏尺寸决定。必须重新验M/S接点、实际负载和完整P&R；不得沿用旧300MHz结果。


## Issue130：新 M/S 原生物理验收与交付重跑入口

本侧任务在独立分支/不可变服务器目录运行，不复用旧宏资格。精确实现、已接受M原始证据和当前S进度见 `docs/BLOCK_FEED_V1.md`、`work/YUZE-LU/130/validation/physical/ACCEPTED_M.md` 与 `docs/handoffs/2026-10-29-issue-130-m-feed.md`。实际EDA只在授权Slurm计算节点/固定SHA容器运行，各个门16CPU；有依赖时afterok补位，不整批等待。

在已有准确源字节/工具环境下，新的原生P&R入口为：
```bash
python3 project/experiments/block_feed_v1/physical.py --top block_feed_s_macro --mapping MAP_FOLDER --out NEW_NATIVE_FOLDER --remove-abc-buffers --input-receivers --placement-mode geometric --fanout-mode partition --hold-repair-margin 0
# 已完成GRT的限定修复：来源回执/成功CTS/RTL/config逐SHA绑定；输出须全新。
python3 project/experiments/block_feed_v1/repair.py --source EXACT_GRT_FOLDER --out NEW_NATIVE_FOLDER --from-grt --closure-hook measured_s_hold.tcl
# 以下每条需独立全新输出；SOURCE_FOLDER为成功原生输出，SEALED_FOLDER为seal输出。
python3 project/experiments/block_feed_v1/qualify.py seal --source SOURCE_FOLDER --out SEALED_FOLDER
python3 project/experiments/block_feed_v1/qualify.py physical --source SEALED_FOLDER --out GATES/physical-s
python3 project/experiments/block_feed_v1/qualify.py function --source SEALED_FOLDER --out GATES/function-s --peer EXACT_ACCEPTED_M_SOURCE
python3 project/experiments/block_feed_v1/qualify.py formal --source SEALED_FOLDER --out GATES/formal-s --function GATES/function-s
# 若已有完整成功LEC计算、但原producer仅因等待功能回执失败：
python3 project/experiments/block_feed_v1/qualify.py formal-join --source SEALED_FOLDER --out GATES/formal-s --function SUCCESSFUL_FUNCTION --computation COMPLETED_NATIVE_COMPUTATION
python3 project/experiments/block_feed_v1/qualify.py drc --source SEALED_FOLDER --out GATES/drc-s
python3 project/experiments/block_feed_v1/qualify.py deliver --source SEALED_FOLDER --out ROOT/results/delivery-s/native --gates GATES
python3 project/experiments/block_feed_v1/qualify.py geometry --source ROOT/results/delivery-s/native --out ROOT/results/delivery-s/geometry
python3 project/experiments/block_feed_v1/bundle.py --delivery ROOT/results/delivery-s/native --out ROOT/results/bundle-s
```

`remote_repair.sh ROOT GRT_SOURCE OUT --from-grt measured_s_hold.tcl` 与 `remote_gate.sh ROOT OP SOURCE OUT [--peer PEER|--function FUNCTION|--computation COMPLETED_NATIVE_COMPUTATION|--gates GATES]` 负责固定image SHA、16CPU及内存接纳。首个seal/全部门通过之前不能称最终候选；delivery要求四门同source receipt SHA。实际GDS DRC为完整未修改FreePDK45规则，禁止跳过FEOL/天线/offgrid。几何输出提供候选LEF和原生矩形/接点覆盖，不授予层级Liberty/abstract coverage或M11/M12系统资格。

S最终网表不保留`store.mem_req`等RTL内部别名。`qualify.py function --peer`生成仅用于仿真的pair夹具，通过真实外部`ready`口观测宽读：原S的`ready=!reset&&(!valid||take)&&!wide_fire`，在每个采样周期检查`reset||!valid||take`后，反推`wide_fire=!reset&&(!valid||take)&&!ready`。生成前核对原RTL等式及夹具唯一替换位置，穷举合法布尔输入；实际内存事务次数断言、数值参考与背压检查全部保留。`memory-observer.json`及生成夹具/bench随S压缩包保存逐SHA证据，最终S/M网表及接口不改。原内部别名导致的编译失败记录仍保留，不能充作已运行的功能测试。

大网表编译显式设置`--output-groups 0`，避免`-j16`默认将已拆分CPP重新合成16个超大编译单元；仍为16个构建进程动态补位，仿真每初态4线程、三个初态并行，总用核不超过16。参数含义核对[Verilator5.042官方说明](https://github.com/verilator/verilator/blob/v5.042/docs/guide/exe_verilator.rst)：0禁用文件合组。这只调整编译组织，不修改门级网表、库单元模型或测试。原qualify36/93451大合组编译保持运行，qualify38/93479为同一候选/同一测试的分散编译对照，未运行结束前不能声称其编译或功能更快/通过。

本地收到原始bundle.json及tar.gz后执行（已有unpacked时只逐字节核验，不覆盖原文件）：
```powershell
python -X utf8 project/experiments/block_feed_v1/verify_bundle.py D:/Data/LLMHardwareDesign-issue130-runtime/deliverables/M
python -X utf8 project/experiments/block_feed_v1/verify_evidence.py
```
第二条仅核验保存的原始证据及源字节，不重跑EDA。M已实收并核验；S必须等完整通过后才能同样登记。

显式formal-join不接收原失败producer的整体资格：要求原所有命令0及严格全边界UNSAT/IDENTICAL，重新哈希全部原始输入/输出/代码，重新运行实际原生正反例，并检查成功三初态功能的网表/库/封存源与证明完全相同。原失败receipt及Kepler日志/投影证明随新包保留；原生证明或成功功能缺失均拒绝。
