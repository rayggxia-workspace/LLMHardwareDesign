2026-10-28 02:28 CST：214/92510实际在node17启动，7个BUF原生swapMaster/pin-net/真实Liberty容量控制通过，原203未改。repair在合法化（0illegal）后的额外repair_timing_helper因GRT-0232拥塞报错，未进入详细布线；保留失败，不降验收。215只去掉这轮额外的时序优化和重复合法化，依旧执行7BUF替换、合法化/check、增量GRT、详细布线/final/RCX及全套独立检查，任何最终setup/hold/cap/slew失败仍拒绝。215复用214已通过的独立probe回执，默认V最终源显式215。S严格LEC实际通过（262545输入/262532输出全部匹配，UNSAT/IDENTICAL），回执f1103e50f6a62783c6207af1f0d4f05fddd655b3db4ed51c2c6fd4010a7a3519；S仅完整GDS DRC待完成。R原生仍继续。213未sbatch的DAG拒绝发生约02:25，前一条02:28为记录时间误写。

2026-10-28 02:28 CST：213部署前Linux DAG检查拒绝：复制S交付任务时仍保留s-physical内部依赖，但该已通过任务未列入213；因此未sbatch、未启动EDA，原213输入保持。新214队列将此依赖改为208实际physical回执（仍须准确报告SHA和passed），S/R源/CWD均不变；新V最终源明确214。未放宽任何门。213无job，不计第八allocation；214需重新验证才提交。

2026-10-28 02:24 CST：已准备213不可变修复队列，尚未提交/通过。V以原203封存GRT为起点，仅对实测七个BUF增强驱动，保持RTL/1210µm外框/M10接口；先以可丢弃ODB实际验证swapMaster、全部pin/net与Liberty容量，再普通详细布线/RCX及同源四门重验。新receiver区分原203和候选最终213，旧V资格不沿用。213默认六组硬绑定16CPU、即完即补；真实依赖限制并发，S/R剩余独立项复用208源/未领取CWD和207实际回执。02:23仍七allocation，S DRC/formal、R global route继续；不恢复旧207/203/210。准备不是修复成功，五宏仍in_progress。

# Issue121 五宏实施接续

2026-10-28 02:12 CST：**V的严格物理接收失败，下一主线是修同一基础版的真实电气违规。** [210实际失败/终态](../../work/YUZE-LU/121/results/run210-five-macro-020353/index.json)：7处max-cap、1处max-slew；最差裕量-53.180515289fF/-0.02661758475ns，全部setup/hold端点最小1.794861/0.016820ns，pin/RC/PG/连通等通过。不能改阈值、声称V已验收或复用旧源检查资格到修复后ODB。92509自然FAILED1:0，elapsed4:33，节点17释放；当前四旧baseline+R196+排空中207+209共七allocation，其他成员未动。209仍继续原V的DRC/最终功能及后续formal，保留结果作原源证据，不因本次physical失败取消。

[211失败与212只读诊断原件](../../work/YUZE-LU/121/results/v-electrical-probe-021023/index.json)：212在既有209/92507内8.9秒完成、未改ODB。实际七个驱动为place81609/BUF_X1、place67728/BUF_X1、place53406/BUF_X2、wire109242/BUF_X4、place55219/BUF_X2、place58201/BUF_X2、place55816/BUF_X2。全部存在5_1_grt和final且master一致；wire109242不在4_cts，其余六个在CTS已存在。211未启动OpenROAD，因为Slurm16CPU step的cpuset不允许显式80–95；212申请同一job的96CPU step envelope后用taskset把实际诊断硬限到未使用80–95，父活跃32CPU、可用内存约485GiB，不新增allocation或触碰既有EDA。失败保持原样，不重提211/212。

**恢复的第一步**：继续核S真实DRC/formal和R原生进度；V先实现/验证七个BUF的局部增强驱动，再在独立allocation跑必要route/RCX及全套接收。212已保存确切OpenROAD帮助与global_route/detail_route源码：`size_cell`不存在，不能按此命令猜测；原生OpenDB swapMaster需先在可丢弃副本验证针脚/连接不变。可从封存5_1_grt.odb/sdc接续，使用实际PRE_DETAIL_ROUTE hook，在`global_route -start_incremental`/`-end_incremental`包围单元替换与合法化后再详细布线；是否需要时序修复及具体API仍须实际验证，尚无编辑、修复成功或新P&R作业。建议按实测负载和BUF pin的真实Liberty上限选强度，外框/引脚/数值硬件保持一版；新输出全部重新STA/RC/PG/DRC/功能/LEC，不能把准备当运行。旧213目录当前尚不存在，可用于新修复队列，但先核服务器真实目录/job再创建。

新V修复源必须显式区分原203（诊断/历史）和新最终源；现有receiver默认V仍指203，不能直接对新ODB套旧source回执。S已通过208 physical与207三初态function，待207实际DRC/formal；R196仍原生全局布线。原208/210中v-physical已FAILED、v-delivery将BLOCKED，不能恢复该失败V任务或重提job；后续S/R未领取项如需续队列，应保持独立claim与来源，不能与新修复队列重复执行。209仍是修正后CPU绑定调度器，禁止恢复旧207/203。

2026-10-28 02:02 CST：**V203实际原生全流程及子回执已通过，209/210已实际提交并开始检查**，不再只是暂存。203/92475父调度器按既定排空自然FAILED2:0，elapsed1:57:39、CPU15:21:39、batch MaxRSS22012388K；不能将该父状态当V失败。V最终五文件/源码/配置SHA见[原生子结果与绑定接收实录](../../work/YUZE-LU/121/results/v-native-bound-receive-0202/index.json)。V尚无最终独立验收资格。

209/92507在node13/96CPU实际三路并行v-physical、v-drc、v-final-function，queue-live硬绑定CPU分别0–15/16–31/32–47，final-function通过后formal立即补位；这是原207业务任务的同一来源、路径、锁。210/92509在node17/96CPU已实际运行新严格v-physical，CPU0–15，复用原208业务任务及锁。scheduler源8aead40194d3f82e2947876152ec6836dd34a536、归档639fb13c…，无新RTL或物理变体。**不能再新建或重提209/210；后续先核这两个真实job和共享207/208状态。** 旧207只让S DRC/formal自然收尾，原203已退出；不要恢复这两个旧调度器。当前四旧baseline+R196+207+209+210共八allocation（含pending/unknown），其他成员未操作。若peer后续park而又有ready工作，先核旧owner是否真实终态，再建新绑定peer复用原锁，不能根据历史RUNNING claim重复执行。S物理/三初态最终功能通过但DRC/严格LEC尚未通过；R全局布线继续，五宏主线未完成。

2026-10-28 01:56 CST：**209/210已实际暂存并通过Linux队列验证，均未提交job**，不是已运行。绑定调度器源8aead40194d3f82e2947876152ec6836dd34a536，归档SHA256=639fb13ce4c8c37fe7c5e660c24426833f6dd4326fd4e7f6f1ea6f5c57b86c1b，两处native_node_queue.py均核为控制通过的c86a7f27bb4ba74a1509d601d4daf39ebb201e6ed75bfa019e5f3c601ae6632f。209的node-queue.json精确复制207（90b4429c…），原state_path/tasks/source完全保留；210精确复制208（1dabb600…）。见[实际暂存回读](../../work/YUZE-LU/121/results/bound-staged-015548/index.json)、[209清单](../../work/YUZE-LU/121/stage205-manifest.json)、[210清单](../../work/YUZE-LU/121/stage206-manifest.json)。两处dispatch-state.tasks={}；当前两队列均无ready任务，因此没有空占节点。

恢复提交入口：先核真实子回执、ready任务和本任务全部RUNNING/PENDING/unknown不超过八，再在服务器对应209/210目录运行`python3 src/project/experiments/block_v1/dispatch.py manifest.json --submit`。209续207业务验收，210续208新physical/交付；两份manifest不绑定节点，交由c96分区选择空闲96CPU。派发器同一全任务锁强制八槽限制，未知提交不重试。任一peer自然park后，后续新ready任务需要新peer复用同一不可变队列和claim，不能重提旧job。S DRC及严格LEC仍在原207活动子进程中自然收尾；其父调度器排空状态不授权重复检查。01:54观察中完整DRC已完成此前大union（1629.920秒），严格LEC已匹配262545输入/262532输出、无未匹配端口，均尚未终态通过。

2026-10-28 01:54 CST：S精确最终网表三初态功能通过，每初态全部1024地址、10000随机事务、91035检查；回执SHA256=f4ef82b5f87e0d11e3718b160361a8c81b99608c26823911acfcb0e10c7e1b3e，来源与已通过208 physical完全一致，见[207实际子结果](../../work/YUZE-LU/121/results/run207-five-macro-015115/index.json)。S完整DRC和严格LEC继续，尚未最终验收。

实际资源修正：见[决策与完整操作边界](../decisions/2026-10-28-block-v1-cpu-affinity.md)、[真实六组16CPU控制/操作](../../work/YUZE-LU/121/results/cpu-affinity-015113/index.json)及[操作后进程仍运行](../../work/YUZE-LU/121/results/active207-015305/index.json)。已有S DRC/formal分别绑定0–15/16–31；R196、V203各自在其节点绑定16CPU。未取消或重启EDA，只排空207父调度器新领取。**原207和203都不能恢复或重提。** 排空后的父job非零/残留RUNNING claim不能替代实际子回执。后续用新绑定调度器续原207/208不可变队列与锁，业务task source/cwd/数值/约束保持原样，已通过S物理/功能不重跑。拟暂存209→原207、210→原208；只有真正ready任务才提交，仍计全部pending/unknown在本任务八槽内。恢复第一步：核209/210是否已经暂存/提交、核原S DRC/formal及R/V route实际子回执，再由准备好的绑定调度器领取；不要运行旧.local/deploy_queue_peer209.py（它使用未绑定旧调度器）。

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
