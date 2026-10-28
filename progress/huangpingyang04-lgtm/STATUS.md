# huangpingyang04-lgtm 的进度

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
