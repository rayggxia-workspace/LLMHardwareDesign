# huangpingyang04-lgtm 的进度

2026-10-29 Asia/Shanghai：92855已实际写入256条M10导体，92931独立核验原生FIXED/逐网/32×0.8μm几何通过，仍未冻结或证明两模式实际复用。GEMM636真实diode92910已完整布线/fresh native0/所检连通及RCX，但新cap2失败保留；92929全量原端点+636真实非驱动负载的数字图合同通过。新增实际导体PNG/SVG与256行CSV，原24767 pin/74301候选行保持。下一步修复INV_X1/XNOR2_X1实际cap违例，并收集GDS92912及其他活动作业；[新交接](../../docs/handoffs/2026-10-29-issue-126-fixed-conductors-and-diode.md)。任务in_progress/Draft，完整系统未完成。

2026-10-29 01:07 CST：92925复用同一1262-buffer检查点的独立无STA合法化/check_placement及原连接/非选中位置合同通过，完整原层接线继续；92921 Signal11失败仍保留。gate-r12原文及已关闭阶段SHA独立保存，最终DRC/连通/RC/STA尚未终态，任务仍in_progress。

2026-10-29 01:05 CST增量：SYSTEM现有输出buffer重排92921在Diamond后Signal11（-11），未布线；772链/1262个现有buffer真实移动检查点及gate-r11保留，后续分离几何进程复用，不重复选点。前阶段aab4619两CI成功、29图已上传核验；GEMM真实diode92910/92912及共同集成/LL/父层其他作业继续，未完成总目标。

## 2026-10-29 00:55 CST：VECTOR终态已收集，真实diode接线继续

VECTOR92872全详细布线/fresh native0/375675网所检连通及双PG通过，但提取setup−4.140220ns、83文字违例，整体FAILED；成本180新增buffer/818换型/875移动，非纯XY。92913全量有向数字合同通过，92914/92915实际SPEF关键路径证明VECTOR深链cell arc与SYS长输出net arc两类问题，新增PNG/SVG及原文SHA随HTML发布。GEMM92910的636真实ANTENNA_X1已插入/合法化，正重布线；92912等待严格GDS原deck，原1460项尚未修复确认。共同集成92855双PG检查完成，仍不是冻结或两完整M11/M12功能。Issue126 in_progress/PR129 Draft；[新交接](../../docs/handoffs/2026-10-29-issue-126-physical-continuation.md)，下方旧运行中说明均保留为历史。

## 2026-10-29 00:40 CST：真实验证继续，未完成整个目标

SYSTEM 92886已完成全量映射相对数字合同：438852个原非filler实例、1539803个原端点、2229个端口、529989个原网络分量保持；5829个新增identity缓冲与980处换型的有向可达性/无环性通过。这是同SRAM合同下的相对网表证明，不是RTL形式验证或时序通过；源setup/hold仍−0.462192/−0.125999ns。

GEMM原GDS 1460项天线多边形已逐项唯一关联636条真实布线网；实际ANTENNA_X1 GDS的原deck识别面积0.0081μm²已核实。尚未插入真实diode，1460失败保留。MXU局部M6报项的重叠OBS被真实同网金属覆盖，新PNG/SVG展示原生几何；不是删除OBS或豁免规则，原父层2项失败保留。

最新核验：92690 LL完整窗口、92841 GEMM父层落脚修复、92855六块共同集成、92872 VECTOR实际重布线、92892 MXU落脚修复均RUNNING，92691依赖等待。VECTOR新检查点合法化完成但最终RC/STA尚无终态。没有合格共同M1–M10冻结、两完整M11/M12模式或端到端系统比较。继续当前作业和真实天线修复，不重复提交。详见[最新交接](../../docs/handoffs/2026-10-29-issue-126-physical-continuation.md)、[中文HTML](../../docs/experiments/issue-126-full-pin/report.html)。Issue126保持in_progress/PR129 Draft；登记pending、看板unverified/同步pending、审查人待指定。

## 2026-10-28（中国标准时间）：Issue126 持续验证

- 当前：原24767pin/74301候选行及完整功能归属已交付，PR129仍draft、Issue126 in_progress。20份真实SPEF叶模型全部bit/方向/重读余量通过，原探针失败和minimum_period/系统模型缺项保留。
- 新结果：VECTOR全同组C线长+1.62%、B native DRC4项；ACT C−6.40%，GEMM/MXU修订C+1.19%/+4.30%，推荐分别见HTML。llSYS全C真实固定PG冲突失败，3.04GB检查点只读锁SHA。
- 规则适用性：独立几何确认原WELL.4用separation而非width导致含义错误；实际llSYS A逐N/P mask width200/space135参考0，原式计数73006仍未精确复现72975，未删原报告或宣称DRC通过。WELL.2、via enclosure及GDS/LVS材料限制继续保留。
- 继续：父层92441/92458前置端点/双PG通过，路由运行；精确模型来源门槛的post-analysis92476/92477等待执行。固定几何预检前两次因GCELLGRID失败，92496使用真实global检查点，状态以回执为准。
- 入口：[PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129) / [中文报告](../../docs/experiments/issue-126-full-pin/report.html) / [交接](../../docs/handoffs/2026-10-27-issue-126-full-pin.md)。登记PR5 pending；看板unverified/同步pending，审查及处理人待指定。

## 2026-10-27（中国标准时间）：Issue126 进行中

- 最新终态修正：llSYS完整C真实迁移后核对全部13507pin，26pin/44矩形对与固定PG直接相交；仅停止该已确认无效的新试验92369，保存moved/ripped/global检查点及证明。完整C未布线/RC/STA，不用8pin通过替代。GEMM/MXU修订C虽当前门槛通过，实际线长+1.19%/+4.30%，本轮优先边界。父层/其余控制/GDS继续，新增9份已完成GDS视图探针含openSYS原始缺宏及WELL失败。

- 最新：完整GEMM/MXU失败驱动的混合修订实际移动3021/1931pin，独立native DRC0/所检全块几何连通/现有模型电气报告0；原GEMM2项电容、MXU3项PG短路/5项电容失败保留。VECTOR/openSYS全C原生门槛通过但时序失败，llSYS全C仍运行。用户授权补建受控父层后，openTPU6618端点/3408网逐项图/层核对与双网PG通过，正在DRT；llaccel27050端点的新基线92458独立推进。历史handoff和真实fakeram器件GDS仍缺，不用占位Liberty或几何视图声称签核。后文8pin为历史局部结果，最新阶段以HTML/physical_summary为准。

- 当前任务：[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126)，分支 `task/126-full-block-pin-xy`，以PR120未合并head4f91e098为基线，未覆盖旧工作树。
- 已完成：复用Issue55真实SYSTEM包装，补齐openTPU/llaccel六块、18项功能完整归属、逐bit接口与连接矩阵；六块24,767原始信号pin，74,301行A/B/C覆盖及保层/方向/网络/尺寸/越界/重复检查。
- 图表/报告：[中文入口](../../docs/experiments/issue-126-full-pin.md)。新增四块全pin对照、局部实际占用、真实端点PNG/SVG；ACT/GEMM原成果逐字节复用。
- 实际物理：六块局部C与ACT完整C已完成当前阶段检查，详见下列分阶段回执。其余五块完整C继续尝试，不能用8pin结果替代。
- ACT完整740-pin C已通过独立clean进程native DRC=0、全块多端几何连通；setup/hold余量1.259268ns/0.032872ns，电气违例报告0，但系统外部模型/父层仍未资格化。RCX后ODB重读不兼容已隔离，物理母本与RC/STA分析分开，失败保留。
- 本轮C终态：六块均已实际执行；ACT完整740-pin、其余五块各8pin局部。六块独立clean native DRC=0、全块多端OpenDB几何连通通过；VECTOR和两个SYSTEM仍有实际时序/电气失败，完整GDS/LVS/父层/系统时序未完成。ACT同组真实路由线长−6.40%、via−1.70%，没有时序或面积改善结论。
- 下一步：收集其余边界对照终态、全块连通和实际RC/STA/电气对照，继续查找版本匹配父层handoff层/路径与抽象接入证据。不将未知层擅自指派，也不把DRT0写成全部通过。
- PR：[PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129) 已draft上传，本轮head以PR最新读回为准；新增14组PNG/SVG及全部表/HTML在分支中，原ACT/GEMM图保留；Issue保持in_progress，不提前关闭。
- 登记/看板：复用管理中心登记PR5 pending；未配置可核验board.json，Projects工具不可用，条目unverified/同步pending，处理人待指定。

新增证据：ACT严格GDS合并因两个fakeram视图缺失失败，未豁免；不完整诊断GDS原始/C的现有deck为678/770项天线错误，native DRC0不代表完整规则通过。其余完整C、匹配cohort边界控制及严格GDS已继续提交，详见交接和原始Slurm回执。真实RC/STA路径负载/slew观察已汇总，单位与覆盖边界单列。

## 原Issue119成果记录（保留）

- 更新时间：2026-10-26（中国标准时间）。
- 当前任务：[Issue #119：ACT/GEMM pin XY 候选总结](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/119)。
- 已完成：独立分析及六组 PNG/SVG、13,839 行逐 pin 坐标、来源/几何验证；按用户要求整理[中文摘要](../../docs/experiments/issue-119-pin-xy-candidates.md)、HTML、图表与脚本入库。
- 交付分支：`task/119-pin-xy-candidates`；[PR #120](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/120) 已 open / ready for review；图表与业务成果提交 53ad953e04a43c6429adce1a02cd2fc061ed7208，51 个上传文件 blob 与本机一致。Issue 为 in_review，不自行合并。
- 下一步：审查上述总结；真实采用候选前取得父层目标层/连接对象，并做局部接入与 RC/STA/DRC 验证。
- 验证：原分析完整性和交互浏览器检查通过、六图目视核验；本次仓库标准库验证通过：13,839 行、12 图、81 链接、46 文件 SHA；管理检查/编译/SVG XML/空白检查通过。成果提交的 [CI 40337360301](https://github.com/rayggxia-workspace/LLMHardwareDesign/actions/runs/40337360301) 已实际 success；本次进度回执提交的最新 CI 以 PR 为准。未执行新的 P&R。
- 阻塞：Projects 无已核验配置/工具，unverified/同步 pending；登记 PR5 仍 pending；审查人/看板处理人待指定。
- [持久交接](../../docs/handoffs/2026-10-26-issue-119-pin-xy.md)。本文件只记录已进入当前 main 基线的新任务；不覆盖其他并行分支中尚未合入的个人进度。

本次模型/规则发布验证：2204文件SHA、89链接、全部74301候选行通过；20图和逐pin筛选正常，模型/规则页截图已目视核验。保持Issue126 in_progress / PR129 draft；父层和其余远程验证继续。

## 2026-10-28：Issue126继续真实接入与共同底座

用户确认六块资源并集和共享实际固定预连。本轮已取得ACT访问窗口版全重布线native0/4819网连通、真实研究12层小例及独立检查；旧两父层分别11项DRC/GRT拥塞失败，LL全C新PG修订仍在完整布线。共同M1–M10尚未实现/冻结，两完整M11/M12功能未实现，不以候选/作业提交替代。详见[新接续交接](../../docs/handoffs/2026-10-28-issue-126-common-base-continuation.md)。PR129持续草稿，Issue126进行中。
## 2026-10-28 17时后（Asia/Shanghai）：Issue126持续执行

- [Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126) / [Draft PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)，in_progress。接受用户六块资源并集、真实共享固定导体的选择；不合并PR120/129。
- 新ACT/GEMM/MXU/VECTOR完整内部窗口叶视图独立native0/所检全块连通通过，9031个实际signal pin与完整增量表一致；GEMM3/MXU1最大电容失败、VECTOR setup−4.195674ns/118违规仍保留，两个SYSTEM还在执行。
- ACT父层256bit接入92719通过native0、860网/双PG；仅新增M10中间点r_data195修复，原叶M5/M6、其他859父pin和PG不变。四组新增PNG/SVG及旧图共24幅已打开/浏览器核验。原始失败和旧物理发布快照保留。
- 共同构造网表原生链接34954端点/17686分量双射通过，38个常量/idle驱动单列；没有共同M1–M10实际布局预连/冻结，也没有两完整M11/M12功能或系统收益结论。
- 继续收集SYSTEM、GEMM/MXU父接入、电气ECO、VECTOR时序ECO和ACT夹具RC/STA。恢复入口及本人作业ID见[接续交接](../../docs/handoffs/2026-10-28-issue-126-common-base-continuation.md)。SRAM GDS/完整规则/模型资格仍缺，登记PR5 pending、看板unverified/同步pending、审查人待指定。

- 后续终态：openSYS新窗口独立native0/460503网连通（累计五块11260实际pin），setup/hold和2016标记仍失败；llSYS新窗口未终态。VECTOR成本ECO A/C仍setup失败，GEMM/MXU电气ECO仍cap3/1失败，新增buffer/移除filler不当面积收益。ACT夹具92732真实RC/STA两方案均hold约−0.074ns且604零长度网未标注。阶段cb945271已上传、两CI成功、4对新PNG/SVG路径读回；新增终态小包与后续commit继续同PR。



## 2026-10-28晚（Asia/Shanghai）：Issue126恢复实际执行

- [Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126) / [Draft PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)，继续in_progress。重新核对28a2c93旧head及本人活动作业，保留PR120/129未合并状态。
- LL三点实际增量修复92747因另一个未移动bit_4812无AP而失败，92748无完成路由可检查；完整窗口92690/92691继续独立。13507完整候选/13184内部移动均保留，新增真实尺寸PG/旧pin/native marker/proposed图，不能报通过。
- 只读NDR/驱动审计92753/92759源SHA不变；971个所统计有NDR网的wire矩形未见名义宽度不足，不扩大到spacing/via/所有时钟。GEMM三处/MXU一处真实驱动换X2，Liberty逻辑状态/端口网络预检查，恢复填充；成本单列。MXU r04重提取setup/hold正且未列cap违例，fresh DRC现已0/所检连通通过，完整规则及形式等价仍不齐；r05是同配置读取绑定改进复测，收益不重复计算。
- VECTOR/openSYS估算状态EST-0104及合法化后Signal11真实失败保留；92770新原生GRT/合法化实现继续，不放宽SDC或删检查。原层集合、宏资源、完整接口仍为门槛。
- 新中文接续报告和PNG/SVG、完整局部坐标、raw SHA证据更新同PR；下一步收集本人未终态检查并继续真实修复，然后才可推进共同冻结底座。没有共同M1–M10实际预连/冻结、两完整M11/M12功能或完整系统对照。登记PR5 pending、看板unverified/同步pending、审查人待指定。

后续已收齐：GEMM三处和MXU一处换型均fresh native0/所检全块连通、完整原pin/PG/die保持，重提取cap违例3/1均消除；setup/hold G0.773637/0.036719、M0.246756/0.038563ns，标准单元bbox面积成本+1.596/+0.266um²。两份实际物理/研究时序视图92776/92777全部3753/2172bit及方向、SPEF重放/源SHA/OBS契约通过。仍缺完整规则、形式等价及匹配SRAM GDS，不标完成。VECTOR r09仍EST-0104、SYS r08仍工具Signal11，92778复用已存检查点独立合法化，不重复修复。正式raw更新resume-r03，图25幅保持待验收。

92780的SYS隔离合法化已成功：原生命令与check_placement执行、原macro/welltap几何和状态核对恢复、pin/PG/die指纹不变；输出placed_NOT_ROUTED.odb，尚无布线/RC/时序资格。0e5254e驱动92781（ROOT/checkpoint_route/r01）直接接续完整信号/时钟重布线及PG/RCX/STA/fresh DRC，不重新做单元修复。先独立导出原OBS对象ID+几何，检查新增OBS恰好原接入窗口；仅在详细布线后移除新约束并确认原OBS集合/几何相同，原M2–M8/clock M4–M8及SDC保持。恢复先查92781实际终态，不把提交/运行当成通过。

GEMM/MXU新ECO视图的严格GDS合并及原有完整FreePDK45 deck另以92783继续，ROOT/streamout/costed-r01；只读复用eco_views/r02，明确C_ECO而非纯XY对照。缺SRAM GDS仍报合并失败，allow-empty保持禁用，不伪造几何，不修改原deck或掩盖WELL/天线/包围等原有失败。


2026-10-28晚接续：92783的两块严格GDS在重复顶层LEF提前失败，deck未执行；安装API实测read_lef_with_def=true造成双抽象视图自动加载。9345fd3修复后92798的GEMM已严格合并0、MXU实际缺4个fakeram GDS，完整deck仍待终态；不伪造宏、不放宽检查。新增六块机器门槛矩阵JSON/CSV与latest-physical-gates中文节、不可覆盖gate-r01原文快照。详见docs/handoffs/2026-10-28-issue-126-gates-and-shared-base.md；完整共同底座/两模式/系统比较尚未完成。


## 后续已收齐终态（优先于本页此前运行中）

92700 FAILED5:13:40，但GEMM Aopt子试验native0、3753网/7506端点连通和双PG通过；旧C为DRT无AP失败。92714 FAILED4:19:36，MXU Aopt/C均路由0、2172网/4344端点连通和双PG通过，fresh native为5/2项spacing错误。C两项分别M6 inst:u_macro–act_data[12]及M10 act_data[197]–[213]；Aopt五项均M10。原生错误全部保留；旧夹具来源不是新成本ECO的叶视图，后续须精确匹配新视图。

92781 COMPLETED1:39:40：SYS成本ECO已完成全信号/时钟DRT、PG、RCX、STA、独立native0，466332网/1474481端点所检连通；路由前后cells/pin/PDN/die指纹相同、源未改。实际setup−0.462192/hold−0.125999ns，1113个VIOLATED文字标记（不当完整计数），仍时序/电气失败。先修复/合法化成本尚需从before与cell_repaired.cell_cost表独立统计；route前后单元不变不代表相对原始源没有ECO。新物理/研究时序视图尚未导出，不替换成原旧模型。

92798 FAILED51:13：GEMM严格合并0，原完整deck1460项，全部天线（M2 5/M3 108/M4 437/M5 507/M6 220/M7 66/M8 78/M9 30/M10 9）。MXU严格合并4缺fakeram，部分诊断GDS的deck1578项（含1项METAL1.5及其余天线）；不是完整MXU规则结论。新包装器失败传播已实际生效，不删规则、不以原生0覆盖GDS失败。接下来可独立检查真实LEF天线规则/实际diode单元和工具antenna API，再决定合法修复；不得先假设KLayout计数已消除。

59910b08707f20bb5d685990cfda9b310eee189a冻结驱动92812已对GEMM/MXU Aopt应用同C相同3/1处X2换型（ROOT/leaf_eco/boundary-r01），不重复C；开始增量路由/DRT，待真实终态。保存原层/尺寸/原SDC、恢复填充，成本单列，为公平基线准备。

不可覆盖gate-r02/gate-r03进一步保存父层/SYS/GDS终态；报告矩阵将新SYS成本ECO与旧原窗口版分别保存，旧源失败/运行中不能覆盖已收齐的新终态。发布后继续功能等价、逐层成本、MXU父层M6/M10真实接入修复及未合格共同集成；全部原完整目标仍active。


## 最新增量：等成本周边控制与天线只读审计

92812实际COMPLETED：GEMM/MXU Aopt同C相同3/1处X2换型，真实DRT/RCX与fresh native0、全块所检连通通过；setup/hold分别0.772449/0.053582ns、0.249090/0.053253ns，原pin/PG/die及源保持。成本分别+1.596/+0.266μm²标准单元master面积，非block面积收益。尚不是系统对照。

92825只读检查同GEMM源，原生天线0网/0pin而GDS deck1460仍未修复；实际ANTENNA_X1原Liberty存在非零输入capacitance0.023429，单位以源库为准。下一步查规则/连接和diode识别差异，不删除检查或无模型插diode。gate-r04不可覆盖快照保存上述及父层/SYS/GDS终态原文和双SHA。92690仍RUNNING、92691依赖等待，92721仍RUNNING；不重复提交。六块完整资格、共同实际底座/冻结、两个完整M11/M12模式及系统对照均未完成，目标继续active。


## 新阶段：原生天线覆盖根因、全映射合同与SYS匹配视图

92834真实只读审计：M1–M10所有default/oxide2天线规则均无，tech LEF天线关键字0，macro LEF无ANTENNAGATEAREA。原GDS deck300:1检查不变；原生天线0缺覆盖，不是通过。92837/92838对比原始ODB与成本ECO，GEMM226775非filler实例/826710信号端点、MXU179887/635434全量网络/方向/实例/时钟复位常量保持，仅3/1处等Liberty逻辑状态换型；相同未修改存储黑盒合同下相对数字功能保持，非RTL形式验证。

92835导出SYS2229位匹配新ODB/SPEF的物理/研究时序视图并准确重放原负余量；实际成本为新增5829功能实例、980原实例换型、1168移动、标准单元master面积+6918.128μm²，存储宏/全部pin/PG/外框保持，时序电气仍失败。不是纯XY收益或面积节省。

92721已FAILED，GEMM新版父夹具route/连通/双PG完成，但fresh native1：M10 gemm_a_rdata[128]/[129]间距。92841按真实异网M10/PG/OBS筛选父pin128新位置并实际重布线中，原叶层/尺寸与PG保持待核；不算通过。92690 LL完整窗口仍运行、92691依赖等待。

新图equal_cost_leaf_margins.png/svg比较实际Aopt/C提取余量，明确相同3/1处换型成本及完整规则失败。gate-r05不可覆盖原文/SHA保存上述终态。新模型准备92846/92847导出等成本G/M Aopt视图；92848为VECTOR全窗口及LL PG-only4错误源导出真实非零研究模型，其中LL明确标记UNQUALIFIED_FAILED_DRC_SOURCE，不放宽物理门槛、不把模型导出视为DRC通过。将用于用户授权的未合格共同集成，非合格冻结。

上一发布5fa66e0已核实GitHub head/图blob，CI40706845419及40706840681均success，Issue126仍in_progress/PR129 Draft。完整技术目标继续active，未实施实际共享底座/冻结、两完整上层功能及系统对照。


## 六资源实际集成与VECTOR排序对照（仍非完整验收）

3eb6bb957146be5535f6630a92241611c9458afa已从GitHub读回，CI40709632122/40709632132均success，新等成本PNG/SVG blob与本机一致。新增真实逐层DRT指标直接复用旧原生终态日志，不重新路由：GEMM同ECO C相对Aopt实际总线长−0.547%、via−0.102%；MXU+2.133%/−0.092%。这些是工具报告精度下的叶块实测，不是几何L1/提取RC或系统收益；仍保留内部方案，继续系统总成本验证。

92846/92847 G/M Aopt完整匹配视图导出成功；92848 VECTOR2246/LL SYSTEM13507位真实模型匹配与SPEF重放通过，LL原生DRC4完整保留为UNQUALIFIED_FAILED_DRC_SOURCE。固定线API92853失败（BPin不接受FIXED枚举），92854改用FIRM后原生ODB/DEF实际写出FIXED M10线及两端接入矩形；这只是API探针。

六块集成92855已实际执行，冻结驱动6b6dd8b912a6ceff59d3ecf63b5ee0140380d1e5，ROOT/common_integration/r01/C；实际六宏+38基础设施放置已导出，完整详细OBS/真实模型读取完成，PDN生成中。新图common_placement_actual严格来自placed.instances.tsv，未绘制虚构信号路径/PG/共享导体，背景不等于空白金属。复用256×32μm实际共享导体拓扑/预算，但尚未实际写线/完成底层布线，不能称共同冻结底座。原LL DRC4、GDS/STA/目标层等缺项保留。

VECTOR92861冷隔离无GRT/增量/SPEF仍EST-0104。实际411821个filler；仅把删除filler移到估算之前，92867（7c89d88ce212a3fcece0ca73b70ad491c9feda28）成功，14处换型/17缓冲，检查点位于estimator_diagnosis/r02/cell_repaired_NOT_LEGALIZED_OR_ROUTED.odb。不重复这轮电气修复；下一步从该实际检查点继续setup/hold修复、独立合法化/填充恢复、原层完整路由和全部原生/RCX/STA检查。上游固定commit82552e4的EST guard为参考推断，安装二进制仍unknown、源树不存在，不冒称版本匹配。

恢复先核实92690/92691、92841、92855实际终态；不重提同一试验/覆盖驱动。gate-r06/r07保存模型/API/排序对照及放置原文和双SHA。完整目标active，未有合格冻结/两完整M11/M12模式/公平系统对照。


## VECTOR从实际检查点接续：92872

最新已发布f3588b927a4df00989f42f98847fbccc32a5dce7已读回，CI40715927581/40715927576均success；实际放置PNG/SVG的GitHub blob0edbaac14ef46a0e683d13eb01e47ad8039c47c0/ec4d4040fbcb06a72a224d793c91875b73e730fa与本机一致。管理/业务9849文件SHA、27图及最终图目视检查通过，完整物理资格仍未通过。

新脚本run_vector_resume.py/vector_resume_job.sh已冻结为d03db1d79f14b6f75f92fd4b6a85098d3469f3bb，92872实际RUNNING，ROOT/vector_resume/r01，drivers/vector-resume-r01/code。直接读estimator_diagnosis/r02成功检查点，不重复14换型/17缓冲的repair_design；接续原约束setup/hold修复、独立进程合法化及原filler类型恢复，再按原M2–M10/clock M4–M10和准确原窗口全量GRT/DRT，RCX/完整现有STA/电气、双PG与fresh native/全块几何及原pin/PG/die核对。初始运行回执与SHA在data/runtime_submissions；作业启动不表示任何后续门槛通过。当前heuristic setup仍约−4.2ns，只是优化估算，不是最终提取余量。

最近核实92690 RUNNING约7h30、92691依赖等待、92841 GEMM landing RUNNING约49min、92855六资源共同PDN RUNNING约28min、92872 RUNNING；不按耗时取消。共同原生放置已完成但PG生成尚未收齐终态，共享导体尚未写线；恢复第一步重新查五作业与execution/stages，先收齐再增量修复，保留所有源/失败/活动驱动。目标继续active，不标完整共同底座、两完整M11/M12模式或系统对照完成。
