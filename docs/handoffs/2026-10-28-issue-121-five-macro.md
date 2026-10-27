# Issue121 五宏实施接续

2026-10-28 01:34 CST：**S完整物理门208通过，S最终验收仍待其余三门**。来源S190回执SHA256=`211665746082e21f4529bd643d0e140e9f4d1e1643d1ea38335b860f2c6a3ea0`；新物理回执=`39b90006945e5e934613924eb7a5342eb0ecef2ad48ff4003646a81be52cc3bd`。273接点按原执行Tcl精确匹配、8种反例全拒绝；131331有效端点（完整报告277649，另146318显式未使用内部输出）setup/hold最小5.995658/0.008125ns；所有时序、电气、RC、供电、连接门通过。见[完整原生接收与终态](../../work/YUZE-LU/121/results/run208-five-macro-013337/index.json)。原207失败保留，207完整DRC及三初态最终网表功能继续，严格LEC依赖实际功能回执；交付须四门同源，不能提前发布S合格。

208实际部署源2c03b5a65e6844cb7fc0189306ea3d8bda38338f、archive SHA256=f816cec893d362bd027ab485eaebfd40590b8e50785305d99b4b6fb6772ff6c6，queue SHA256=1dabb6001660acb63db57182c8fada6adf2a015095223cd240316a0098ad6bbc。原[部署清单](../../work/YUZE-LU/121/stage204-manifest.json)保留node24；92498尚PENDING/零elapsed/无allocation时发现node24已mixed，核node22 IDLE96后只更新同一job的ReqNodeList=node22，未新增job或取消任何任务。[放置变更与实际执行观察](../../work/YUZE-LU/121/results/acceptance-20261028-013327/index.json)保留前后原文及哈希。92498已COMPLETED0:0，elapsed5:34、CPU6:03.659，批组MaxRSS4615200K；500ms采样过程树峰值4777484288B（约4.45GiB），不是LEC/DRC峰值。其余任务只等外部依赖，故自动park释放node22；queue_all_tasks_passed=false。**下一步只在208有真正ready工作时新建peer，复用208源/队列/共享claim；不重提原job、不重复已通过S物理门、不恢复已排空203。** 目前四旧baseline+R196+V203+207共七allocation。R已全局布线、V详细布线，见[观察](../../work/YUZE-LU/121/results/live-20261028-013227/index.json)。

在线分支与PR122已由CLI GraphQL独立核为2c03b5a65e6844cb7fc0189306ea3d8bda38338f，账号YUZE-LU、OPEN/draft；后继元数据提交需重新核head，不能沿用此核验冒称后继提交已发布。

2026-10-28 01:20 CST：207独立S物理接收失败，仅`exact_m10_pin_geometry=false`，全部实际端点时序、电气、RC、PG、连接等门通过，见[原始失败](../../work/YUZE-LU/121/results/run207-five-macro-010821/index.json)。已定位为旧生成器`%g`六位有效数字序列化：S273接点中128个输出的未格式化JSON和实际执行Tcl相差5nm；实际Tcl与ODB精确一致。源文件与失败不重写。新`pin_contract.py`严格核完整脚本、源回执SHA、整数DBU及全位号矩形；原始native TSV的8种错误全拒绝，无容差。见[取舍](../decisions/2026-10-28-block-v1-executed-pin-contract.md)与[控制](../../work/YUZE-LU/121/results/pin-contract-controls-20261028-0119/pin-contract-controls.json)。尚不能把软件控制当完整物理门通过。

新208六项DAG已本地validate，通过后将重新运行S/R/V完整物理接收，并只在新physical及207同一未改动源的DRC/function/formal全部通过后生成交付。queue SHA256=`1dabb6001660acb63db57182c8fada6adf2a015095223cd240316a0098ad6bbc`，尚待源码提交/部署，不可冒称已运行。207保留运行，无新取消；旧physical失败不会取消其独立DRC/function/formal。当前S仍未验收，M/T已接收，V/R继续物理；下一步提交新源、部署208到自然释放的node24（届时不超八allocation），再核真实门结果。

2026-10-28 01:05 CST：**S190全流程COMPLETED/0:0**，elapsed2:58:57、CPU11:23:34、Slurm batch MaxRSS147104644K（约140.3GiB，包含最终LEC，不冒充独立单进程峰值）。最终V/SDC/DEF/ODB/SPEF及来源SHA已生成，[终态](../../work/YUZE-LU/121/results/run190-five-macro-010130/index.json)。尚无S最终接收资格。

207/92488已在node25/96CPU实际运行S的physical、full-DRC、final-function三个独立16CPU检查；见[实际领取与可用内存](../../work/YUZE-LU/121/results/run207-five-macro-010508/index.json)。当前其余项受真实依赖限制，非整批等待。207共15项S/R/V接收与交付，queue SHA256=`90b4429c1657f347880be31a891db1e7eaa577d8f5a13d34e8ebf774f98c6400`；复用原203的同一源码73b50a85395c6195d84fdb31c5faed4a51e77d20和归档15ac4bd9b3356d0f30fdef996054360d115437968185690fdf2f3a32f2b3684f，**没有新增RTL版本**。生产stage203-manifest/queue207保持原生字节，Git属性-text保证服务器哈希可跨系统复用。

原203统一64GiB接收估计被上述实际内存推翻。已对相同生产调度器做真实子进程的SIGINT排空隔离控制：停止新领取、等待已有子进程完成，必须随后独立处理遗留RUNNING claim。控制通过后，只向203调度器PID1710701发SIGINT，未取消Slurm allocation、进程组或EDA子任务。V已继续进入详细布线。控制、精确目标、来源SHA和请求后CPU增长见[排空记录](../../work/YUZE-LU/121/results/drain203-005449/index.json)。**不要恢复/重提203队列**；它只让既有Vroute自然收尾，预期父调度器最终以KeyboardInterrupt非零退出，不能把父队列失败当V子结果失败，也不能用遗留RUNNING claim当进程存活证据。M已完成的接收保持有效，后续S/R/V检查只由207领取；各块仍逐项核对实际子回执。

207内存预算（GiB，均再乘1.2并留16GiB guard）：

| 阶段 | S | R | V | 依据 |
| --- | --- | --- | --- | --- |
| 独立物理/STA | 64 | 64 | 32 | 不包含LEC；暂定预算，不把旧组合receiver的LEC峰值分配到本阶段 |
| 完整GDS DRC | 64 | 64 | 64 | 旧C8两个完整检查实测process-tree峰值约24.2/23.3GiB；不是本次实测 |
| 最终功能构建/三初态 | 128 | 192 | 96 | 暂定构建预算，继续保留500ms实际过程树采样 |
| 严格LEC | 192 | 224 | 64 | S最终流程约140.3GiB实测；R/V按145877/21816与S131201 DFF规模估计，不能称新门实测 |
| 交付导出 | 16 | 16 | 16 | 仅所有门通过后才领取 |

当前四旧baseline+R196+V203+207共七allocation，S190已自然释放；只在确有ready任务受RAM阻挡且总数不超八时增加共享claim的peer。默认上限仍六个16CPU，按live MemAvailable与保留量即完即补。207部署前验证发现移除v-route后遗留内部依赖，已改为203精确外部子回执并通过同一生产validate；修正前无job。恢复第一步：采集207、196和203真实子结果；S/R/V任何实际失败保留且修该基础版，不能提前接收或恢复旧范围。

2026-10-28 00:39 CST 续记：CLI GraphQL独立读回实际账号YUZE-LU，分支及PR122 head均为cf31e8a7fa46116c753670b221e40b7723b84522；PR仍OPEN/draft。此后本次交付入口/快照提交继续沿同一分支快进，不能以旧SHA冒称后继head。统一入口见[五宏交付索引](../../work/YUZE-LU/121/delivery/README.md)。S190详细布线完成，流程内最终LEC正在检查262545输入/262532输出（无未匹配端口），尚无独立接收资格；R196进入CTS，V203进入global route。只读记录见[00:39快照](../../work/YUZE-LU/121/results/live-20261028-003912/index.json)。

旧181/92386自然FAILED收尾，elapsed4:31:28、CPU4:51:15、Slurm组MaxRSS183501616K；共享178队列A接收失败原因包括hold=-0.047559ns，C为hold=-0.103899ns和原生DRC未通过，保留[终态摘要](../../work/YUZE-LU/121/results/run178-five-macro-003712/index.json)，不扩展旧C8修复。当前四个旧baseline（92045/92046/92047/92062）加190/196/203，共七allocation；其他成员未操作。203当前仅Vroute可运行，S/R/V独立接收均受实际最终布线依赖约束，不能为了填满节点制造重复版本或提前领取。先前00:20的八allocation仅为当时快照。

2026-10-28 00:20 CST。仓库rayggxia-workspace/LLMHardwareDesign，负责人YUZE-LU；[Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)持续in_progress，[PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)草稿、未合并。分支`task/121-block-v1-twelve-layer`；本记录正文对应代码0a34c7ad8cff2d364517ea24e283890d9d219aa8及随后本次文档/交付提交，以实际远程head读回为准。

## 主线和实际结果

用户已冻结M/V/R/S/T，每种一个基础实现，必须全部得到最终原生M1–M10布局布线及同源独立接收。旧四边界方案/裸M8/混合VS无效为最终边界。阵列、两个产品及一般十二层提取留下一轮。持续目标尚未完成，不能关闭Issue或自合并。

- **M已完成单块原生最终接收，待项目审查**：204精确单网M2补铜，完整GDS所有多边形层差分仅预定新增矩形；205重生全部最终产物/RCX；203四项独立接收全部通过。560×560um，有源115631.264um²，物理专用153645.856um²，275个真实0.8×0.8um M10信号pin。10ns/2fF条件下全部端点setup/hold最小1.737254/0.014780ns；原生及完整FreePDK45 deck均0。三初态最终网表功能通过，严格LEC10558输入/10549输出全匹配、UNSAT/IDENTICAL。大文件在服务器，真实路径/字节/SHA与四项来源回执见[交付入口](../../work/YUZE-LU/121/delivery/M/README.md)。PNG已查看；SVG是实际ODB接点图，XML/边界/计数检查通过。通用层次Lib/M11-M12系统资格仍false。
- **V**：196原样RTL416344检查，函数域逐Q16.16实际RTL6291472检查，两路3级II=1；映射388350单元/543387.726um²，唯一外框1210×1210um。203/92475正运行独立P&R。206同源RTL命令周期测量8243检查通过：八元素函数7拍，reciprocal/rsqrt130/196拍；RMS/L2=197+5ceil(N/8)，Softmax=134+5ceil(N/8)+ceil(N/2)，N256为357/422拍；40选8为328拍。组件II不冒充宏命令II，输入/输出/背压另计，见[命令合同](../BLOCK_V1_COMMANDS.md)。
- **R**：195原样RTL397971检查，240组GDN/SSM与100组四抽头卷积；映射707287单元/145877DFF，1328464.116um²，唯一外框1870×1870um。196/92462在place；最后日志timing-driven resizer可能长时间不刷新，不凭日志静默判断挂起。
- **S**：190/92446已完成global route（实测53:32，阶段峰值约8GiB），正在detailed route。376059单元/131201DFF，1610×1610um；尚无最终接收。标准单元16KiB单1RW，不称SRAM。
- **T**：沿用已接收C叶块，6KiB标准单元结果交接，1120×1120um；既有完整DRC/时序/三初态功能证据未重跑。[交付入口](../../work/YUZE-LU/121/delivery/T/README.md)。

## 服务器与恢复入口

服务器`yuzelu@10.129.166.172`，任务根`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121`。本次任务最多八allocation，pending/未知提交也计数；其他成员作业不计入且不可操作。c96为96CPU，默认6×16独立任务，完成即补位；只按实际依赖/有依据的RAM不足降并发。

旧178/92362于4:31:25自然FAILED，A全deck通过、C检查/接收失败，输出已收回索引；不扩展旧C8修复。空出槽位由203/92475于00:00 CST接上，node23/96CPU。当前五个旧baseline（92045/92046/92047/92062/92386）加190/196/203共八allocation，不能追加第九个。

203不可变队列SHA256`efb011875050301a8084ac2f09f05bc718309e46069e53b0e3cf22e5160cc36a`，source73b50a85395c6195d84fdb31c5faed4a51e77d20，archive15ac4bd9b3356d0f30fdef996054360d115437968185690fdf2f3a32f2b3684f，21项DAG。初始Vroute与M三项接收四个16CPU并发；M功能完成立即补formal；M全deck完成立即生成交付。当前其余S/R/V接收只受各自最终布线依赖限制，已实际记录queue-live，不能冒称六路正在运行。不要改运行中的manifest或重复领取。

194无job且已被195替代，不能再提交。197/201/202失败、198/199只读API失败、200仅诊断通过均保留；204/205/206为196现有allocation内带硬时限、CPU/RAM预检的短step，已全部终态。204误日期目录仅部署预检失败、无EDA/job，保留；不能据该目录再提交。192被父191提前结束终止的经验仍适用，长P&R/完整接收用独立allocation，不能借旧parent生命周期碰运气。

下一步：只读采集190/196/203终态；203自动运行各块同源物理/完整原生+GDS DRC/精确最终网表三初态功能/严格LEC，四项都通过才生成最终索引、pin与PNG。原始失败不覆盖；真实违规按唯一基础版、原外框/接口进行冻结前修复，再重生寄生并重跑全部接收。源码/回执恢复路径见`work/YUZE-LU/121/results/`；本地`.local/issue121/collect_five.py`可采集标准队列，短step用`collect_steps.py`，不将step伪称新allocation。

## 提交和协作未完成项

已执行`python scripts/check_project.py`、相关Python编译、`git diff --check`；硬件结果以原生回执为准。M只完成本块接收，V/R/S未完成，整个五宏任务保持in_progress。管理中心登记PR5未合并为pending；无config/board.json和Projects能力，实际看板unverified/同步pending，管理员和独立审查人待指定。不得描述为登记/看板已完成、不得自审/自合并/关闭。
