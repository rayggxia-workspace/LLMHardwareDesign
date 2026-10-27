2026-10-28 05:50 CST：将main 6a681d6632e7f7be537ff96eae1827df834bcfe8合入任务分支以消除四份共同文档冲突，保留模型分析/阶段冻结及本任务历史记录，README/架构入口转向当前五宏清单和最终交付索引。没有修改封存RTL、block_v1实验代码、物理配置或服务器源；原183份模型归档SHA/40 SVG/10成功回执及236本地引用通过原校验。全量相对旧父的diff --check报告来自主线原样归档的CRLF/历史日志空格，未改写证据；四份冲突解决文档及新V回执的差分检查单独通过。S/V完整DRC及R两门继续；整体in_progress、PR122草稿，登记pending、看板unverified/同步pending，审查待指定。

2026-10-28 05:48 CST：V228新最终源严格LEC通过，43776输入/43765输出全部匹配、UNSAT/IDENTICAL；回执91a09580b988f127229f8840b003c9bed1fedb85da58e45ca8ecd0775bf0b8f8，精确绑定228 native与三初态最终功能回执，见work/YUZE-LU/121/results/v-formal-054725/index.json。S/V均仅余完整GDS DRC；R230继续DRC/最终网表功能，待功能通过后即补严格LEC。05:46逐进程/全部线程掩码与CPU增长确认各任务仍实际计算，未重启或取消EDA；231仍真实等待R三门。另以git merge-tree只读确认任务分支与main存在四份共同文档冲突，准备保留双方内容合入main到本任务分支；不改变任何封存RTL/配置/服务器源。整体仍in_progress、PR122草稿，登记pending、看板unverified/同步pending，审查待指定。

2026-10-28 05:43 CST：V228实际最终网表功能回归通过，三种初态各416344检查/310231周期（800逐元素、1250函数、270组合、100TopK用例），回执38d8bc6883bc033f4e45f8f4405ff1420fe78d844451af760e4e0121ce2b1773，精确绑定228 native回执2309320c…和最终ODB 42804986…；证据work/YUZE-LU/121/results/v-final-function-053914/index.json。严格LEC已自动补位，与完整GDS DRC并行；不能沿用旧222资格。S225只余完整DRC，R230继续DRC/最终功能编译；全部五块已有最终布局布线与通过的独立物理门，M/T已接收，S/V/R尚未最终交付。六allocation及原6×16队列保持，231观察器等待真实R门，不增加虚假任务占满CPU。Issue121=in_progress、PR122草稿，登记pending、看板unverified/同步pending、审查待指定。

2026-10-28 05:34 CST：S225新最终源严格LEC实际通过，262545输入/262532输出全匹配、无未匹配边界、UNSAT/IDENTICAL；回执978f02b063b10a2878f8e93b06020e049e884777e7ddec1ac0a8ac65e035ee3c，精确绑定225 native回执26166d19…与三初态最终功能回执d684dadd…，证据results/s-formal-053020/index.json。S现仅剩完整GDS DRC，不能用旧207结果代替；通过后225会自动交付/导出完整几何。V228/R230的完整DRC和最终功能继续。S/T接口文档据封存RTL明确S请求间隔2拍、T自动sealed/提交后1拍valid/无背压读出每2拍；吞吐只标协议上界，不宣称新增峰值或系统测量，T单租约标签不冒称通用鉴权。R交付231已stage、仍真实waiting/未提交，观察器41631继续；旧222总体FAILED不等于R业务失败。当前六allocation，五宏整体in_progress、PR122草稿，登记pending、看板unverified/同步pending，审查待指定。

2026-10-28 05:25 CST：R最终交付接续入口231已实际stage，dispatch-state.tasks={}、未sbatch、没有新allocation。原222/92523经sacct确认FAILED/1:0/01:44:12（旧V物理失败保留），R208物理PASSED而r-delivery仍未claim、208交付CWD不存在。231与222的node-queue字节完全相同、SHA6aacc5427e7ba03da7d46e97c73d1d0fe63b03d5375881fcd3996ded0a92d7eb，共用222 state/lock；原archive ebfdfebd1ff39d8451670c375c1b857e37c333bc3a6e659d26cc9a96ed62fc07、source c16739a432ccf3612e9f0f59f8c004516fb96428、生产scheduler c86a7f27…均实际核验。新controller仅在207三项R验收真实passed、交付仍未claim且总allocation≤8时提交；不会重跑旧V失败任务、已有R物理或230补测。当前六allocation，S225严格LEC已进入solver，与完整DRC并行；V228/R230的DRC和最终功能继续。证据results/r-delivery-resume-staged-052218/index.json。首次只读预检因squeue已过期单job查询报Invalid job id而退出，未写入任何231或启动EDA；改用当前用户完整squeue精确过滤并结合sacct终态证明后stage通过，原队列/预算不改。

恢复第一步：读取231的dispatch-state、222的共享node-queue-state及208交付CWD；本地控制进程wait_submit231.py（exec session41631，日志.local/issue121/wait-submit231.log）已实际运行并记录真实waiting。恢复时先确认原进程与状态，不能重复启动观察器或直接重提旧manifest。若观察器退出或提交返回不明，先读回231 dispatch-state/Slurm再决定下一步；以共享Store的原claim锁避免重复任务。231的父队列总体仍可能因历史V失败返回FAILED，验收R只看208实际业务receipt与同源四门，不把父终态当R失败。

R完整几何仍由225的r-geometry在真实208交付passed后领取；若225已经park，使用另一个新bound peer复用225不可变队列/state，仅在真实工作ready时分配。不要提交旧221/224，也不要转用225中过时的V222 geometry；最终V仍由228交付与导出。

2026-10-28 05:12 CST：五块均已有原生最终布局布线产物，且各自独立物理门全部通过。新增R208物理回执bda67b1a372a604f9864bd6e1c61381d1c4cc9b5cb623c0e9048cc760945c45f：146009真实端点，setup/hold最小2.155765/0.015269ns，cap/slew余量3.054929fF/0.067521ns；V228物理回执90a6bb1944950a5c239e21521f33fa61f29105d92b196381b3dfb8336ae2c025：21949端点，setup/hold最小1.798553/0.016960ns，cap/slew余量1.007366fF/0.049695ns。两者全部PG/连接/寄生/实际M10几何通过，证据results/r-physical-050943、v-physical-051104。M/T已完整接收；S225仍跑完整DRC与严格LEC，V228仍跑完整DRC/最终功能，R230仍跑完整DRC/最终功能，后两者严格LEC依功能输出补位。V最终源回执2309320cca2b3d88c05ec7d1cecbc3aee61de1716d178e241616b50d553f1a9f、R最终源回执11af2d52a971e13a67133bef23cc0481171197e1a20f3fb50fa760f101aaad0f；不能沿用旧V222其他通过项。旧222 DRC已自然通过，但其物理失败保留；当前七allocation、6×16动态队列和实际掩码/CPU增长证据all-live-progress-050754不变。逐块PPA已汇入delivery/README，S/V/R最终交付包仍须全部四门。Issue121=in_progress、PR122草稿，登记pending、看板unverified/同步pending、独立审查待指定。

2026-10-28 05:02 CST：R196原生最终全流程通过（回执11af2d52a971e13a67133bef23cc0481171197e1a20f3fb50fa760f101aaad0f），1870×1870µm，最终ODB 736d8e10d63c134b3ea81fb7eb34d69cd947c3d5be456f09240800d5459305e1、fresh SPEF ab5c96c90495473f89d30ac1355f22f199a4bd34485ab59a1247c09937748352。92462自然COMPLETED/0:0；真实回执ready后自动提交230/92545，已在node26运行R独立DRC及最终功能，掩码0–15/16–31；严格LEC等待真实功能输出。230保留已通过v-composition且没有重跑，224继续不提交；222已自动领取208 CWD的R独立物理门，交付仍依全部四门，不能因原生flow通过就宣称R已验收。S225最终网表三初态各91035检查通过，功能回执d684dadd80afbdcaacd54ae1f8debecba84c60d19018bb2a2cf2fbc70b5057d2，严格LEC即完即补，与完整GDS DRC并行；V228流程内LEC通过、fresh RCX/最终报告继续。当前七allocation：92045/92046/92047/92523/92526/92533/92545；旧92062亦已自然COMPLETED，其他成员未动。证据results/run196-five-macro-050016、run230-five-macro-050027、run222-five-macro-050029、run225-five-macro-045746。M/T已接收，S/V/R仍未最终交付；五宏整体in_progress、PR122草稿，登记pending、看板unverified/同步pending、独立审查待指定。

2026-10-28 04:48 CST：230补充V RTL验证实际通过：320个成对RoPE tile、65535元素跨命令统计和三项错误保持，93091检查/68868周期，给定Q16.16系数下非饱和样例误差最大1.49999e-5。四RTL SHA及原driver与196一致，不改硬件、不宣称最终网表直接实测或模型质量。实际借用92523/node17的80–95 CPU约25秒，父222不可变DAG最大反链5×16=80 CPU、最大内存320GiB；加本任务16GiB后1.2裕量+16GiBguard为419.2GiB，低于节点实际约503GiB。S225父队列最坏448GiB的尝试被资源预检拒绝（未启动EDA），预算未降低；第一次Slurm控制因cleanenv缺SLURM_JOB_ID在claim前自然失败，原日志保留；第二次显式传入且经父PID/cgroup/UID/CPU核验后，严格使用生产Store.claim/execute/finish，230 state中v-composition=PASSED、R三门未claim、dispatch-state仍tasks={}。后续230实际allocation会跳过已通过V项，224仍不得提交；待R196原生final passed且容量释放，才提交230 R门。R流程内LEC已通过、fresh RCX继续；S独立物理通过，DRC/function继续；V228详细布线继续。证据results/v-composition-044706、all-live-progress-043937；当前八allocation，原生P&R/既有任务未取消。

2026-10-28 04:27 CST：逐项复核实施计划发现V的RoPE此前仅有乘法/成对重排原语用例，缺少独立命令组合用例。准备补320个相邻成对RoPE tile（外供Q16.16 cos/sin，逐阶段RNE/饱和、尾对和背压）及65535元素跨命令统计、count/ID/final错误保持测试；新test复用原传输driver，RTL不变且须与196 SHA完全相同。尚未运行/通过，不沿用为最终网表实测。230准备在一个六槽16CPU队列中补该RTL验证与原224三项未领取R独立门；224保留但不再提交，R业务源207/CWD保持。当前仍八allocation，不启动第九；230先stage，真实容量释放后才提交，各R门仍依196真实final passed。S225独立物理现已全通过（131331端点，setup/hold5.995658/0.008125ns），其余门继续；原222严格LEC也通过但不能转移给新228。

2026-10-28 04:18 CST：S225原生全流程通过，最终ODB与已证明edited.odb精确相同（de0775b46044c99879cc7907766cb7f156604677638e645f9b539348f2f417b4），fresh SPEF 909cbba47d7552d4f3baf8e2048b78960df7ca4eb099fc2f83689b66c440e7ef；原生回执26166d19b20b34c6cd22e39e1a9589b77cd8b8a6efa194f3d472dc76f5bff502。实际已即完即补三路独立物理/完整GDS DRC/最终功能，硬绑0–15/16–31/32–47，进程CPU增长及所有线程掩码已读回；严格LEC依最终功能实际输出等待。旧222最终功能已通过，formal自动补位0–15并与DRC16–31并行，不能转用到新V228。R196原生最终LEC、V228详细布线继续。当前8 allocation，224未ready/未提交；M/T已接收，S/V/R仍未最终交付。证据results/run225-five-macro-041707与finish-progress-041719。

2026-10-28 04:07 CST 最新恢复入口：228/92533已在node25实际RUNNING（源码760d1b9f8a57fa2f4321181d38289a81113655a2，archive b963834e1521586137470cccbb31517460c708138f590c40e8edcf7279d21d9b）；7BUF+1DFF原生换驱动/信号保持及全PG检查通过，合法化0illegal，继续新详细布线。先跑228独立四门/完整几何，再按新delivery收集V。探针227通过、226失败，原222物理失败与其他正在跑的验收全部保留。225中的旧v-geometry依赖222已过时，不能领取为最终V；V geometry改由228拥有。R196详细布线进入post-processing，尚无最终receipt，224继续不提交；222仍可领取R208 physical/delivery。S225原生最终LEC正在solver，未验收。四旧baseline+196+222+225+228共八allocation，禁止第九；224须真实196passed且释放容量后提交。不要重提旧203/207/209/215/221/223，不覆盖旧receipt。

2026-10-28 03:43 CST：V222最终原生flow已通过，最终V/SDC/DEF/ODB/SPEF齐；立即三路并行物理、完整GDS DRC、三初态最终功能，实际16CPU掩码0–15/16–31/32–47不相交，进程CPU均增长。S225/92526 node13已实际从223证明过的edited.odb接续，当前native最终LEC进行中；实际kepler16线程限0–15且CPU增长。R196 node26详细布线第1轮优化继续（迭代中违规数不是最终接收结果）。本任务四baseline+196+222+225共七allocation；224三R独立门已暂存但依真实196最终回执仍未ready，未sbatch。M/T已接收，S/V/R仍未最终交付；225新源不得沿用190或203旧资格。

2026-10-28 03:39 CST：S223三网几何修正实际通过：全片native DRC0；567102网仅addr[7]/din[43]/din[55]变化，其余567099网/全部非NETS/信号网表/全部via/BPin/其他层保持，真实连通、跨网短路及0.8um基础间距检查通过。随后脚本漏导入Path导致自然FAILED，未进入final/RCX；补import并准备225只接续已封存edited.odb，全部独立门仍须新源重验，不重跑布局布线。223实际输出路径生成误写block-s1，已留不可变记录和显式目录链接；后续225回到规范block-v1路径，不复用错误旧queue。209旧V完整GDS deck0但native2处M2违规，故原203仍失败；209已自然结束，R三项独立门均未领取。224已暂存三R门，未sbatch，须待196真实native回执ready再提交。当前四旧baseline+R196+V222共六allocation；225准备提交至≤8。V222原生最终LEC仍运行，S/V/R未验收。

2026-10-28 03:31 CST：222/92523已实际在node17接续V收尾（原生fillcell、route别名及SDC完成，最终LEC/RCX进行中），S只读定位已通过。S实际三个M10 U形接入addr[7]/din[43]/din[55]准备缩为1/1/2条直连，BPin与全部via/其他层/逻辑保持；真实190 DEF正例roundtrip通过，坐标改2DBU的源被拒。223准备从原190最终库内修三网并原生全片DRC/几何连通检查，再fresh final/RCX及全部四门重验；不是已修复通过。新几何队列同属223，依S223、V222、R208真实最终delivery，替代未提交的221。当前七allocation，223若提交仍受总上限8；六槽16CPU即完即补，S原生收尾含LEC按实际140.3GiB组峰值预留192GiB及1.2裕量/16GiBguard。

2026-10-28 03:25 CST：新终态已读回：S207完整GDS deck实际10项METAL10.2，原生7标记（addr[6]/addr[7]、din[31]/din[43]间距及din[55] NS Metal），不再记DRC运行。V215详细布线自然完成且router报告0，但随后do-finish缺5_route.odb失败；查安装原生Makefile确认漏do-5_3_fillcell/do-5_route/do-5_route.sdc，保留失败，222从封存5_2_route.odb接续这三步及完整final/RCX，全部独立门重验。222仅准备未提交，同时只读定位S及接续从未领取的208 R物理/交付；R交付只依实际207子回执，不依已排空FAILED父。03:18本任务六allocation，R196详细布线与209旧V DRC仍继续、其他成员未动。M/T已交付，五宏整体仍未完成。221几何队列未提交，V依赖旧215交付路径已过时；后继必须另建匹配新最终交付的几何队列，不覆盖221历史。

2026-10-28 03:11 CST：M/T完整原生占用与M10底部几何数据已齐，原版图未改。216/217迭代器历史不当作完整结果；219/220通过全部原生DEF RECT补全（M=1，T=0），完整文件索引见delivery/{M,T}/native-geometry。实际CPU/DAG证明、原始218 API语义失败和全部step终态见results/native-geometry-030826/index.json；仅短只读step复用既有92511，实际硬绑16CPU，无额外allocation。R已进入详细布线；V修复详细布线继续，S完整GDS DRC继续；全部五宏尚未交付完成。221三项S/R/V几何队列已实际暂存、Linux验证通过、dispatch-state.tasks={}，三个最终delivery依赖全waiting，故未sbatch、不占第九节点；源2278615562da6c691793cc5f4a25d145272f9c5d/archive7a3c613e…，见results/geometry-staged-031051/index.json。后续只在真正ready且总allocation≤8时提交，不能根据父调度器park/排空状态冒称子门失败；恢复入口见最新交接。

2026-10-28 03:07 CST：219M/220T真实RECT补全通过，约23/42秒，沿用同一2278615业务源码。M原DEF中恰1处补铜精确补入，232310201B完整占用SHA8df4ee9448fa26ff95f1aaca00dea8b4d08f1d14c134f722ceeaf1f5fadc67c7；T原DEF普通RECT=0、664909090B占用SHAe17dda9a29187203161b0c9d0326846b167cbf92af5f1cf9faf2534a189becda。新小型报告/底部access/候选LEF在delivery/{M,T}/native-geometry；原geometry文件夹保留迭代器历史，coverage-status明确不以其原scope认定完整。原ODB哈希保持，native M/T叶块资格不变；候选LEF abstract coverage、层次Lib/M11-M12系统仍false。R已进入详细布线，V继续迭代，S完整GDS DRC及原V完整DRC未终态；原V功能和严格LEC已过，不能复用到新V。

准备221几何队列仅S/R/V三项，必须各自最终delivery同源回执通过才运行，不提前导出失败或中间ODB；全部receipt依赖不再绑定会park/排空的父Slurm状态。当前尚未部署/提交，不能占第九allocation。注意215原R-delivery继承208的207父dispatch-state依赖：若207排空父终态导致R门尚未生成就BLOCKED，而209共享207逻辑队列仍正常，则不能把该父状态当R叶门失败；核实际R子回执和215的BLOCKED后，只能在业务CWD尚未创建且旧task终态不可再领取时用新队列补交付，不能并发重复claim或改旧队列。

2026-10-28 03:01 CST：216M/217T只读迭代器导出和M10底部几何检查实际通过（约63/153秒），但**不能把原报告scope当完整占用资格**：复核已知197/200发现安装版dbWirePathItr漏DEF RECT，M205有真实M2补铜。218实际API探针确认Tcl没有dbWireShapeItr，返回0但语义probe失败已保留。原216/217文件不覆盖，本地coverage-status明确完整性未合格；现准备219/220：对封存最终DEF全部普通NETS的RECT按原生net身份严格补入新副本、逐矩形多重集核对，M必须包含GDS已证明的[282460,530600,282650,531160]补铜。原ODB/GDS和M/T叶块验收不变，不重跑P&R；不能在完成真实RECT核对前交付“完整占用”。软件fixture/拒绝反例、Python编译/check_project/diff检查通过，实际补全尚未运行。

2026-10-28 02:46 CST：核对当前实施计划第7项及五宏规格71行后，补充只读five_macro_geometry导出器：封存最终ODB的wire/via/PG/pin、master及block OBS保持net身份完整导出；原生candidate.lef仅候选，abstract coverage/层次Lib/M11-M12资格仍false；实际M10矩形按固定0.6µm cut+0.1µm enclosure作底部几何检查，三个拒绝反例。源码已准备，未运行，不能声称几何导出/接入验证通过。不会修改宏或加新版本。拟在既有215 allocation空余16CPU上做有硬时限的只读M探针；必须先证明不可变215 DAG的最大反链5个16CPU（最多80CPU）及生产始终取最低空闲CPU，故80–95始终保留给一项诊断，核实际job/CPU/RAM后才启动；不新增第九allocation，不并行两项诊断，不执行长P&R或完整验收。

2026-10-28 02:31 CST：215/92511已实际在node17运行同一V基础版局部驱动修复，7BUF替换/连接控制通过、合法化0illegal后进入详细布线（pin access），尚未通过最终接收。[真实probe/214失败/215运行记录](../../work/YUZE-LU/121/results/v-drive-repair-023019/index.json)。214/92510自然FAILED1:0（1分钟），失败保留；215使用原生已通过probe，完整约束不变，未来最终源为215，四项独立检查必须全部重验。S严格LEC已通过、仅完整GDS DRC未终态；R全局布线继续。当前四旧baseline+196+207+209+215共八allocation，209仍保留原V其他接收，其他成员未动。依赖允许后默认六组16CPU硬绑定即完即补；新V目前仅一个路由前置任务ready。原203/207/208/210/214均不可重提。五宏整体仍未完成，Issue121保持in_progress，PR122草稿未合并。

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

后续恢复约束：旧207/209/215/223均不得重新提交。224未sbatch，196真实native receipt passed后且allocation≤8再用224 dispatch --submit；它只领取从未创建的207 R DRC/function/formal CWD，207共享历史state里R三项均无claim。222负责208新R physical/delivery；若222在R ready前park，使用新bound peer继续同一222不可变queue/state，不重复业务CWD。225负责S全四门/delivery以及S/V/R最终geometry；若225先park，真实delivery ready后新bound peer继续原queue/state。221只暂存且源/路径过时，绝不提交；223 Path失败与输出拼写历史均保留，225全为规范路径。92507.2 CANCELLED为只读Makefile cat探针超时，不是EDA取消；旧V fullDRC本身自然完成并实际native两项失败。
