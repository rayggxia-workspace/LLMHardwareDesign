2026-10-27 22:05 CST：五宏主线实际推进。M新RTL的1200组随机/边界tile、尾块、多tile、S8/S16/P15样例、K=65535守卫、跨组合并、RNE/饱和和背压通过（282066检查/203846周期）；S全1024地址与10000随机事务通过（91035检查）。M完整映射77203单元；S保留原131072bit标准单元存储，展开后376059单元，其中131201DFF，映射面积978028.268um²，不能称SRAM。186六独立16CPU实际并跑；186映射Yosys路径语法失败、187调度缺receipt mode、188 signed导入/scopeinfo元数据失败均保留，不冒充P&R通过。修正沿用已通过数值RTL和映射，没有重复ABC。189/92444 node26/96CPU中M已完成floorplan/place/CTS，正在route；190/92446 node24/96CPU中S展开/完整库存通过，独立原生流程已进入floorplan。当前仅这两块的物理输入就绪，V/R尚待RTL，节点内并发因实际依赖低于六；未启动虚构或重复工作占资源。本任务六旧baseline+两新allocation共八，其他成员不计入且未动。T真实最终GDS渲染和386个M10信号pin实际导出通过，图/pin已保存delivery/T。五块仍未全部完成，V/R实现与硬化、M/S最终全流程/独立完整接收继续，Issue保持in_progress、草稿PR122未合并。

2026-10-27 CST：用户明确冻结M/V/R/S/T五种基础宏，每种一个实现，要求全部最终M1–M10布局布线。裸M8/混合VS不是最终边界；旧四边界计划已归档，完整系统/两产品/一般十二层提取移至后续。92426在PENDING、0CPU、0elapsed时因边界改定取消，未执行EDA。T选定C实际叶块证据保留；新M/V/R/S尚未最终P&R通过。当前规格与执行入口为docs/BLOCK_LIBRARY_V1.md、docs/plans/block-v1-library-implementation.md，任务继续in_progress。

# Issue 121 执行记录

2026-10-27 21:01 CST：新四块独立功能/映射队列185已部署并实际提交92426，96CPU、六个16CPU任务；当前资源排队，本任务六RUNNING＋两PENDING共八allocation，不追加节点。源码8d6f3b77、archive12db5fe0741f10c5ffcb419d6f1232191d61f4d95cd0e9985e9b51b99868f4b0；Linux路径/DAG预检通过，不当功能/映射通过。T6K选择既有C结果，重新核对同源RTL、三类回执和10份最终产物SHA；完整单块物理/三初态最终功能通过，层次模型仍未合格。M8/VS/S16K新单块最终P&R仍待完成，本轮不能只交文档或综合。

2026-10-27 20:50 CST：用户明确将本轮目标收回“首版物理Block清单、规格、每个入选块的最终M1–M10布局布线及接收”。阵列/多实例/跨块预连/两个产品/通用十二层提取移至后续；历史实验与已提交作业自然收尾。当前从真实C8提出M8乘积、VS向量归约状态、独立S16K及既有T6K四种候选；M8并非完整MAC，最终边界须由真实pin/面积/时序验证。新增独立RTL及可逆源码重接准备，尚无新单块P&R通过；刚写的生产via草稿已封存且未部署。主线以docs/plans/block-v1-library-implementation.md为准，必须交最终逐块结果。

2026-10-27 20:16 CST：182/92402两份真实wire/via/pin并集与封存科学几何一致，六种SPEF原生读回/拒绝实际通过（50秒/CPU5.432秒/组MaxRSS12280K）。184/92404实际直接节点位置接收通过：branch六/via七个实际Iterm变换后pin中心、层与ID全匹配；各自移2DBU/交换同层左右锚点的原生反例保留完整导体并集和全部电气值，却被位置门拒绝（12秒/CPU3.903秒/组MaxRSS0为无有效采样）。183原尝试10秒因FIRM实例保护提前拒绝，完整失败保留；184只改变测试副本且恢复status，不修改封存源。当前两科学fixture来源闭环增强，不等于生产0.6um via、一般十二层提取/拼接/完整Block资格。固定PR128 fbbd5ec显式输出RC十二个实际小例记录已读取，全部输出差逐项复算；它的内部core参考面不可直接替代公开M10pin Lib，真实宏资格仍false。178/181完整C8接收、两全deck GDS检查继续等待实际终态；完整P0–P6未完成。

2026-10-27 19:49 CST：172/92341完整旧C8 A/C严格LEC实际全部通过（输入289078/输出291263全匹配、UNSAT/IDENTICAL），不借此资格167新源。180/92385实际原生耦合SPEF接收通过：branch六节点/八对C/四R，via七节点/十对C/五R；每几何五个原生破坏输入均拒绝，重连控制保留逐节点耦合边际仍被拒。57秒/CPU6.379秒/Slurm组MaxRSS11092K为短任务采样，不当单项峰值。两科学fixture组装/导入通过，不等于一般routed十二层提取/原生拼接/Block资格。181/92386已在node25实际领取A完整物理接收；178/92362在node23运行A/C全deck GDS检查及C完整接收，A/C各自接续不等对侧。179/92379仍PENDING于node24，唯一共享claim避免重复；当前本任务六RUNNING加一PENDING共七allocation，其他成员不计入且未操作。固定PR128 cb3a089输入残差逐项复算通过，但输出RC反例及A/C输出slew超差146/106仍阻止紧凑模型资格。完整P0–P6/冻结共同底座/两差异产品/独立审查未完成。

2026-10-27 19:39 CST：172/92341完整旧C8 A/C严格LEC实际全部通过，1:27:12/CPU2:57:14/组MaxRSS271600160K；严格接口289078输入/291263输出全匹配及UNSAT/IDENTICAL，不借此资格167新物理源。178共享队列已自动接续174 C新源完整物理接收；A受当前DRC+接收历史峰值预留阻挡（可用468GiB、余下预留额度约80GiB、所需240GiB，明确非新单项实测），新179/92379同一队列96CPU于node24接续A，尚待实际claim读回，不重投既有任务。新增节点ground/双向节点对C实测组装及完整原生SPEF读回入口；run100两几何真实场数据、对称SPEF及14破坏控制本地通过，180两独立16CPU测试源准备，实际尚未执行。完整多网物理提取/拼接/父层/宏与全部P0–P6未合格。

2026-10-27 19:19 CST：167/92333实际完整A/C最终输出组COMPLETED/1:43:46，TotalCPU4:19:55、组MaxRSS283181384K（约270GiB，不能除以2当作单项峰值）。两路各7门均通过：165接受ODB重生最终输出及RCX、完整硬件/几何/约束保持、全片原生router DRC0。该16CPU双8历史组平均约15.7% CPU使用，只是不同阶段实际占用，不是加速比；支持后继以更多独立任务填节点。严格状态边界LEC仍等172、新独立全deck GDS DRC/完整物理/精确组合功能/宏均待通过。当前本任务6个allocation（旧057三路、067、172和178），未取消任何旧作业；完整P0–P6仍未完成。

2026-10-27 19:16 CST：已实际收集167 C候选独立leaf成功终态：7项原生最终输出门、从165接受ODB重生RCX/最终文件、完整网表/几何/约束保持、全片原生router DRC0。其严格状态边界LEC、独立GDS完整DRC、完整物理/精确功能和宏资格均仍false；A候选及167group/172group未终态。178/92362继续在原始全deck DRC阶段，实际候选接收仍受172依赖阻挡。

2026-10-27 19:12 CST：178/92362实际RUNNING于node23，Slurm申请96CPU，共享队列两项完整C8 GDS检查已分别领取；当前其余四项由真实167/172或各自物理接收依赖阻挡，未发生内存装箱阻挡。节点实际RAM503.5GiB、读回可用约491GiB（瞬时值）；70/200GiB预算明确是历史不同阶段估计，非当前单项实测。完整队列按CPU动态装箱/完成即补位，当前实际两路不冒充6路EDA吞吐。177/92361因Windows反斜杠路径被前置校验拒绝，10秒FAILED，未启动EDA子项；完整失败保留，新178仅修正POSIX配置、Linux验证与实际依赖预检。178/177源2255b197b2ea67136c56e0bf16e500fc52a59b53，archive f2488e8e481b88123cbf00662937860728549d4e8a0777575dc46da8051ebf0f。175实际控制通过，174/176旧小group仍无job；本任务7个RUNNING allocation，其他成员不计入且未操作。PR128固定f3f5df8私有min/max原型24对照改善输出min，但真实T6K仍955/897诊断超差；不替换服务器/主线工具、不宣称宏合格。完整P0–P6继续。

2026-10-27 19:04 CST：按用户纠正改为本任务6～8节点、c96实际96CPU队列默认6×16、完成即补位；只有内存不足或真实依赖才降并发并记录具体依据。原计划第9.2节已修订并保留审查原版。新增共享claim/CPU装箱/独立分支失败隔离/依赖等待释放节点调度，真实生产路径的六任务计时控制通过，非EDA加速比。175/92352初始化与38个物理来源合同破坏控制实际通过（57秒/CPU8.623秒/MaxRSS16756K为组数据）；176已部署无job。未提交174/176旧小分组停止后续调度，计划由177整节点队列直接运行其各自leaf，保留旧manifest。177代码及六工作项准备，尚未部署。167/172仍待实际终态，完整P0–P6/宏/两产品未完成。

2026-10-27 18:36 CST：新增修复后167 C8/S16K与160 T6K的完整组合接收入口，绑定174/161完整物理报告、严格形式证明和实际full-view/proof/Liberty；独立数学接收再次复核，不沿用旧128/133源。准备175同节点8CPU初始化+1CPU物理合同控制、176同节点A/C各12CPU完整三初态×两背压模式；每模型4线程，受RAM预检限制并发3/1模型，案例不缩减。模块SHA变化须重新实跑初始化，旧140/141保留。实际161 A/C索引合同正例/破坏反例、py_compile/管理结构/diff通过；175/176尚未部署。167/172实际仍RUNNING，174无job；完整P0–P6继续，宏/一般十二层RC/两产品未合格。

2026-10-27 18:22 CST：173/92348实际组合控制双1CPU通过，16秒、CPU9.489秒，Slurm MaxRSS=0无有效采样；真实常量两极性、保护负载、改名tie/改驱动强度DFF正例严格4输入/4输出、UNSAT/IDENTICAL，错误tie/clock均SAT拒绝。新增174完整C8接收已不可变部署到node22/16CPU，源码2937f9c、archive26c12abad3caf6dc77e56f259458e12babd512a82e725b45057ea2a7b8136def；严格等待167/172/173，目前tasks为空、无job。准备节点内双8CPU，200GiB/路加20%RAM；167/172仍运行，当前六allocation，未取消旧作业。PR128固定bd91c42已独立接收168/169供电/full timing V/真实OBS（A9208361/C9206675矩形、未覆盖0），时序958/900诊断项仍失败，宏仍不合格。完整P0–P6、组合功能/一般十二层RC/共同底座/两产品/独立审查仍未完成。

2026-10-27 18:15 CST：准备173真实常量/保护投影组合正反例（同c96双1CPU）与174新C8完整物理接收（双8CPU、200GiB/路加20%余量）。174严格依赖167新源、172完整旧图严格LEC、173组合控制实际通过，并对167重新完整严格LEC；不借旧图证明新源。新增实际实例化master的statetable/state_function拒绝门。原inspect的AST逐项相同，本地支持FF/两种不支持构造反例、py_compile、管理结构和diff检查通过；173/174尚未部署、无job。167/172继续运行，完整P0–P6及宏/两产品未完成。

2026-10-27 16:58 CST：164/92293实际双8CPU T6K候选视图导出/原生读回通过，0:57/TotalCPU2:53.470/MaxRSS2976540K，160物理源及161完整物理/最终功能绑定，仍无宏边界资格；group/A/C终态已收集。134/92255实际FAILED/1:26:19/CPU3:04:44/MaxRSS364273800K，严格LEC虽UNSAT/IDENTICAL，但输入diff1004/1032且PI差28，完整对应门保持拒绝，未跑独立完整GDS。新165 C8障碍事件有限接入已准备未执行；SHA绑定实际几何预检A45/C29网文本变更、15/4落点路线，全部报告网基础spacing与完整upper接触0，仍非实际修复。16:47本任务5allocation（057三路、067、141）继续，其他成员未操作；完整P0–P6未完成。下一步实际165、定位严格对应、T6K同源bundle交#127独立边界；登记/看板/审查状态保持。

2026-10-27 16:39 CST：161/92264完整T6K A/C物理18门及三初态最终功能全部通过，49:10/TotalCPU3:36:58/MaxRSS72319928K，仍非宏冻结；终态在results/run161-group-terminal、run161a/c-receive-terminal、run161a/c-final-terminal。163/92268真实只读定位全部86标记/95网通过，2:58/CPU5:38.336/MaxRSS4073888K，源未改；索引run163-group/a/c-terminal。164 T6K同源view双8CPU代码准备，绑定160/161/145并保持独立宏边界未验收。新增真实来源18反例、原合同13反例、7种stub编排通过；C8有限文本重写/全upper索引实际与声明控制见同目录164/163控制JSON，尚无实际C8修复。16:33本任务6allocation（057三路、067、134、141），其他成员未操作；下一步实跑164及C8合法化/完整重验，原P0–P6范围和最多8的统一预算保持。

2026-10-27 15:50 CST：163 C8原生最终DRC只读定位代码与真实49/37条报告解析控制已准备，尚未部署/运行；逐项记录完整几何/固定pin/源route及有限固定via提案，不修改ODB。A59/C36个报告网络，4个零宽/高marker用1DBU包络，拒绝未知尾部/非法层/非网/非网格坐标。c96单allocation内两路各2CPU，按每路24GiB加20%余量决定并行。161四路完整接收、134完整C8物理和141组合仍运行，15:45共7allocation；完整物理宏及P0–P6未完成。

2026-10-27 15:41 CST：160/92259实际两路最终输出/LEC/新RCX/全片原生DRC均通过，8:54、TotalCPU34:45.937、MaxRSS41580320K；源159接受几何/全部物理Verilog/原SDC和DRC前后DEF严格保持，新全片报告两路均0。161/92264已在node20/32CPU四路8CPU完整物理/最终功能接收，未终态，不能冻结。162/92261实际C8最终全片原生门FAILED/4:22、TotalCPU46:08.830、MaxRSS18331828K：A49=5cut spacing+37metal spacing+7short，C37=2+30+5，源ODB和检查前后DEF均不变；原route报告0不覆盖这些失败。完整失败组/两子均保留。134/141继续；当前7个本任务allocation。宏边界QA已由独立#127支线跟踪，正式输入仍等主线完整物理合格来源，不增加节点预算。完整P0–P6、宏/一般十二层RC/两产品/登记看板审查仍未完成。

2026-10-27 15:31 CST：159/92258有限短接修复实际A/C各12门均通过，1:49、TotalCPU3:09.295、MaxRSS1350256K；A改11网/C改3网，完整上层3087/2919形状、386/389网的跨网短接为0，原实际三对短接精确复现，原18/2间距及全mask身份也复现，after上层原生子集0。仍非完整资格。160/92259同node22/32CPU两路16CPU已实际运行新原生输出/RCX/全片DRC，161四8CPU完整资格已部署无job等160全部成功；134/92255与141/92256继续。本次补充162 C8最终ODB全片原生DRC独立门（16CPU内两8CPU、每路200GiB加20%余量），因为route报告0不能覆盖新发现；尚未部署/运行。当前7个本任务allocation，162仅能占第8槽。完整P0–P6、宏资格、登记/看板/审查仍未完成。

2026-10-27 15:24 CST：128 C8 A/C原生全流程均实际成功；A4:19:48/TotalCPU17:03:13/MaxRSS183436004K，C4:17:11/17:01:55/185234252K，仍需独立物理和完整功能。134/92255已在node23/64CPU两路32CPU完整物理接收，141/92256已在node21/48CPU两路24CPU最终C8/S16K/T6K+实际glue完整组合运行。157/92253实际FAILED/8:50/TotalCPU34:56.338/MaxRSS41813472K，真正全片DRT报A4/C1个Short/Cut Short，严格最终DEF/全部网表/约束读回在此之前均通过；158无job停用。159准备保留固定pin/所有M1–M8，原有简化之外只调整实际重叠的两个via9并连回原via8，新增全部上层网络含PG的短接审计；声明控制通过，实际159未执行。当前6个本任务allocation，完整P0–P6仍未完成。

2026-10-27 15:12 CST：155/92248实际FAILED/8:05、TotalCPU19:39.463、MaxRSS41807612K；两路原生do-6_report完成，随后因安装版缺少公开check_drc Tcl命令而失败，尚未实际执行新全片DRC/几何与功能接收。156已读回空state/无job，依赖失败停用。原失败不改写。157改用实际二进制存在的六参数drt::check_drc_cmd，在重提取前先核对实际命令/参数签名，零box全片检查、全部原读回与资格门保持；158完整物理/最终功能仍须等待157全部成功。本源码提交时157/158尚未部署。15:03当前5个本任务allocation，128 C已完成，A仍最终输出；134/141仍等两路完整成功。完整P0–P6未完成。

2026-10-27 14:36 CST：154实际有限探针通过，stage150；组/两子终态索引`run154-group-terminal`、`run154a-terminal`、`run154c-terminal`。源e1beb5821428bf57e8cbe02e06a6260f161cb22c，归档4c2b48a868c38970690e16322ee4f490611e6b51966a09c8e21a6e0cd92dc4d9（162成员/1095680字节）。92243/1:43/TotalCPU3:01.781/MaxRSS1897412K，A/C各10门通过，完整源18/2复现、upper mask XOR0、after upper0、所有via身份/坐标保持；并非完整宏资格。155/156后继全门代码已准备尚未部署，见正式有限修复决策；14:36现有6allocation保留，128无终态。

2026-10-27 14:27 CST：153源码2533cff07db1210c1870197bb798c4dbf77ae9b9，归档3b6fc298071931b1ed2fb1524c493ceaaf8c2fd53ffa39ecfe270e5fb1b28c68（162成员/1095680字节），stage149。92241实际FAILED/1:20/TotalCPU2:21.279/MaxRSS1322944K，组/两子终态索引`run153-group-terminal`、`run153a-terminal`、`run153c-terminal`；`run153-initial`采集时已终态。原GDS DBU0.0001µm与probe0.0005µm的单向换算保护拒绝，尚未XOR/DRC。154仅改为共同细网格整数放大，物理候选不变，实际尚未运行。

2026-10-27 14:22 CST：152源码3c0bc644d5ab1fab9a7889b591b7ce9271de5c10，归档b936b365906670e37fa6d942d6474ce04038190021714740a63470fb4f14ecf5（162成员/1095680字节），stage148。92239实际FAILED/1:19/TotalCPU2:19.502/MaxRSS1324944K；组与两子终态索引`run152-group-terminal`、`run152a-terminal`、`run152c-terminal`，实际绑定报告与网表诊断`native-escape-152-diagnosis.json`。153固定via原坐标/身份、M9树投影与M10确定性L，新GDS mask XOR/原GDS复现门；`escape-controls-153.json`及fixture通过，实际153尚未运行，全部完整资格仍待验收。

2026-10-27 14:12 CST：151源码06f1c39523c30e7fe74aeb9fee0b7bfa0553ea85、归档806812a4896bc9dbe1e03524e292138d1141db7674369937ef19b2bfaaf74dd7，162成员/1085440字节；stage147，实际92237 FAILED/1:14/TotalCPU2:09.700/MaxRSS1322996K，A/C导入10/1网后端点换序触发原header顺序检查。证据`run151-initial`、`run151-group-terminal`及两子；完整失败保留。152严格端点身份/USE检查及新增六反例在`escape-controls-152.json`和fixture，尚未部署实际EDA，其余所有门槛保持，完整目标未完成。

2026-10-27 14:07 CST：`run149-not-submitted`读回无dispatch-state/tasks/job，16G申请被原集群内存保护拒绝。`run150-initial`、`run150-group-terminal`、`run150a-terminal`、`run150c-terminal`保留实际92236 FAILED两路读回错误：INCREMENTAL未导入NETS路由；1:14/TotalCPU2:09.030/MaxRSS1326488K。stage145/146分别是149/150原manifest；源61748febed2b1532a6d705951678abc80f1f5ee0和归档f9a2774c46ec26494a7183d95800ccd2dac6a1ed366118fbdcd322041accd387（162成员/1085440字节）。151将从新源码修正为FLOORPLAN既有网络导入，尚未部署；所有资格门槛保留。完整目标未完成，14:07仍6allocation，128最终输出未终态。

2026-10-27 14:01 CST：新增149预制接入线修复探针和`escape-controls-149.json`、`escape-controls-149b.json`及各自合成DEF fixture；149b新增真实矩形边接触的声明合成反例。149拟在同一c96/4CPU/16GiB allocation内A/C各2CPU，实际EDA尚未执行。所有133/135/148原始源及失败不改，149诊断通过也需新寄生与完整物理/功能接收，详见[有限修复决策](../../../../docs/decisions/2026-10-27-block-v1-native-escape-repair.md)。13:58实际128两路均已do-finish但尚无回执；134/141等待完整成功，147旧失败依赖继续停用。计划SHA重新核验不变，完整目标未完成。


2026-10-27 13:24 CST：148/92231同节点A/C各8核只读定位通过，1:11、TotalCPU54.043秒、MaxRSS1299772K；两路实际重叠约26.75秒。A扫描5743302形状/83命中，C扫描5738655形状/8命中，18+2标记零遗漏。M10标记均涉及相邻边缘接口异网，A的两项M9标记涉及read_data[43]同网凹口，仍未修复。147已读回确认无job/空state，因135失败停用；134/141继续等待128完整成功，当前6个本任务allocation。安装原生DRC脚本固定threads(4)，已新增节点内并行决策，按实际阶段CPU/内存配置并发；全部验收门保留。


2026-10-27 13:18 CST：135/92222完整资格组已终态FAILED，48:10、TotalCPU4:55:06、MaxRSS73373228K。A独立DRC18项（M10间距16/M9间距2），C独立DRC2项（M10间距2）；原生DRT均0，全部其他接收门均通过，A/C最终功能三初态通过。两路不能冻结为合格宏。原始失败及全量DRC索引已保存，147依赖失败且从未提交job，停用；新148准备以一个16CPU c96 allocation内A/C两路8CPU只读定位，不修改ODB、pin或任何DRC规则。135按64CPU分配的整体CPU利用约9.6%，仅代表此批（含串行DRC等待段）；后续分阶段并发，并保留实际内存/CPU证据。128 C8两路进入详细布线；134/141继续等待128完整成功，当前6个本任务allocation，最多8个。

2026-10-27 13:03 CST：当前正式四视图入口147/node20/32CPU，已部署无job，见`results/run147-deployment`及stage143 manifest，源码0e65b27/归档df998dd76f17b0e06b31507b32047a446fd37d33efa078582062239357b07d44。146同归档node21部署也无job，见`run146-deployment`/stage142；因141整RAM占同节点，已停用146而以147独立node20承接，不取消任何任务。后续统一dispatcher只调度134/141/147及当前有效依赖，不再调度142/146。计划文件SHA重新核验仍为2ef18149c806cfbda996bbc91b69c84b31781ad9553e7093630d1f7a2ddc20cf。完整目标仍未完成。

2026-10-27 12:59 CST：145实际组/两子通过，51秒/3108328K，索引`run145-group-terminal`、`run145a-terminal`、`run145c-terminal`及stage141 manifest；真实386 signal bit和11bus容器/成员一致。正式视图新增145成功证明/共享脚本/实际工具SHA门槛，146待部署并等待134/135/145，`view-controls-146.json`再次通过13来源反例及4stub控制。143/144失败和142无job停用原样保留，宏边界/一般RC/共同底座与两产品未资格。

2026-10-27 12:54 CST：144实际49秒严格失败，组/两子索引`run144-group-terminal`、`run144a-terminal`、`run144c-terminal`保留，stage140 manifest对应实际144。真实386signal bit无缺失/错方向，但限定查询另有11个bus容器；已补对象类型/成员逐项证明，待145实际诊断。146保留正式视图编号；142无job停用，不覆盖旧输入或回执。

2026-10-27 12:49 CST：143/92226自然FAILED/51秒，MaxRSS3002100K；组与A/C子任务失败索引为`run143-group-terminal`、`run143a-terminal`、`run143c-terminal`，旧局部pin/全名前缀不兼容原因与共享限定查询修复见同源视图决策。`view-controls-144.json`再次通过来源/编排控制。142未提交停用，144/145拟采用新不可变源码，尚未运行；原失败与部署不覆盖。

2026-10-27 12:43 CST：142四视图组已不可变部署无job，依赖134/135完整成功，部署索引`results/run142-deployment`和stage138 manifest；135最终功能A/C子任务均成功，各三初态完整242事务，整组物理DRC继续，索引`run135a-final-terminal`、`run135c-final-terminal`绑定父allocation仍RUNNING而非冒称整组终态。另准备143实际封存T6K时序模型双路诊断，尚未运行，不是正式宏视图。

2026-10-27 12:41 CST：新增严格绑定128/134与133/135的四路同源视图组，尚未部署/执行；`view-controls-142.json`仅为13坏来源反例与4种实际stub编排控制，不是EDA资格。生成LEF/Liberty仍保留所有宏边界/功能/十二层标志false。参见[来源决策](../../../docs/decisions/2026-10-27-block-v1-prefab-view-sources.md)。线上已核PR122 head d560bb7与Issue/PR描述一致，完整目标仍未完成。

2026-10-27 12:26 CST：133完成，135四路资格实际运行；140初态实测通过，141完整最终叶+映射glue组合已部署但尚无job。证据见`results/run133-group-terminal`、`run133a-terminal`、`run133c-terminal`、`run135-group-first`及四子快照、`run140-first`、`run141-deployment`。阶段136/137 manifest对应140/141，旧139无job并停用。当前完整P0–P6目标未完成，当前7allocation；保持8槽与真实内存/线程约束，其他成员未动。详细初态数值、所有失败与资格边界见[组合决策](../../../docs/decisions/2026-10-27-block-v1-final-composition.md)。

137实际glue通过，136失败原样保存，见`results/run137-terminal`与`run136-terminal`；原008库存成功结果重新采集于`results/run008-current-verified`，不将其mapped-suite超时改写为通过。最终叶/真实glue组合与初始化顺序的证据边界及并行配置见[组合决策](../../../docs/decisions/2026-10-27-block-v1-final-composition.md)。当前初始化控制与完整组合尚未实际运行；完整目标未完成。

真实父层glue：新增 `project/experiments/block_v1/native_glue.py` 与 `native-glue-map`，只映射现有shared121 wrapper，在两叶端点上作完整组合等价和三个真实坏连接检查，并逐master核算所有glue与tie单元。Python编译通过；当前尚未服务器运行。物理父层、实际最终C8/S16K/T6K完整组合、一般十二层RC/拼接及共同底座/两产品仍待验收。见[决策](../../../docs/decisions/2026-10-27-block-v1-real-glue.md)。


2026-10-27 11:49 CST：135四路完整T6K物理/最终功能资格已不可变部署，源码11505a8286b9abbeeedc25c42832d38765c480bc、归档b4b5392f1c8daf73c7062f6ed9df5e93c5e33476a0338b9177e399819079a30a，149成员/983040字节；依赖133 A/C组完整成功，尚无Slurm job。134也未提交，依赖128两路。133/92206仍实际运行；128两路placement完成，CTS接近本阶段报告输出，未有完整回执。当前7个本任务allocation；完整目标仍未完成。


2026-10-27 11:45 CST：133/92206已在node22/32CPU运行，A/C两个完整T6K预制route/final子任务各16CPU并行，均实际make读回原native M1–M10、RCX、LEC及cap40/hold5ps、原输入保护和完整via-only参数；源码5bf5b4d0e74b2132cc7d8b1eb392f7fe8c2e1e61、归档05a956018f53186e2521e375d181adc7b58f5d9af9c7617a2ff12f2c9e2caf13，148成员/983040字节。尚无完整候选或独立接收终态。128 C8两路已过placement、正在CTS；当前本任务7个allocation，其他成员未动。134依赖128两路成功且尚无job。正式物理Block、一般多网分布RC/拼接、共同底座、两产品和参数库仍未验收。


2026-10-27 11:40 CST：132/92204两路各8核实际封存保护CTS接入检查均通过，baseline203.216秒、via-only208.265秒；整组3:35、TotalCPU53:58.362、MaxRSS1726008K、已分配16核利用率约94.1%。确认安装ORFS的DETAILED_ROUTE_ARGS会替换默认参数，新修复必须完整保留原M10 via包围、64轮及报告参数。133已准备同节点A/C两路各16核完整route/final有限尝试，不改pin、约束、预算或native tech；尚未运行/接收。134新类型接收已不可变部署，源码cb89511、归档2b8c2b5351bc3aeb5342bfdbc66d6a0d6164551289d292ef22973f21b3c3e62f，依赖128两路成功，当前无job；130停用。完整23项间距修复、宏/一般RC/共同底座/两产品及参数库仍未验收。


2026-10-27 11:28 CST：131/92203同节点两路只读诊断通过1:09、TotalCPU33.743秒、MaxRSS697096K。23个间距标记全部定位，108形状命中、零遗漏，集中在少数边缘pin附近；M9同网短凹口和M10异网近距仍需实际修复。实际Liberty/最终ODB/真实DFF与STA证明189个ANTENNA_X1/A为纯电容负载；保留全部其余原报告后49544个有效端点全部有限且setup/hold非负，最差5.203448ns/.005355ns，电气/clock/原生计数逐项不变。真实过载/短周期/缺数据约束三反例及库timing/方向/函数/状态四反例均拒绝。新接收器仅在绑定131完整控制、同SHA库与模块、每个实际ODB根网后采用类型判定；原120失败不改写，23项DRC仍不通过。130旧接收仅部署无job，停用；后续134分组接收配置准备，等待128两路成功。


2026-10-27 11:06 CST 新终态：120/92182独立完整接收自然失败47:19，TotalCPU51:07.095、MaxRSS19936M。完整DRC剩23项：M10间距19、M9间距4，天线类别未报告违例；严格原始/最终LEC、RC覆盖、PG及189个保护实例原根网等通过。时序门槛另因189个输入-only ANTENNA_X1/A被枚举为无有限setup/hold端点而失败，须用实际Liberty/STA端点资格证明并保持真实数据端点覆盖，当前不豁免。有限端点最差setup5.203448ns/hold.005355ns，电气计数零仍不能覆盖上述失败。完整原报告及索引保留，未冻结宏。此刻本任务6个allocation运行，128两路仍placement。


2026-10-27 11:05 CST：用户要求后续加强节点内并行，尤其c96。新增完整A/C独立接收任务组：同一64CPU allocation内每路32CPU，按实际MemAvailable及旧C8约172GiB峰值留20%余量选择两路并行或串行；成功、单路失败继续及低内存控制通过，仅为编排验证。128/92195、92196在node23/24运行新源完整P&R，已过综合导入/floorplan，正在placement；130接收依赖两路成功，129仅部署无job、后续停用。080A自然完成3:32:05、MaxRSS180418880K，普通流程结束仍非严格接收；120完整DRC继续。11:00本任务7个allocation。计算模块参考openTPU/llaccel的取舍已有固定来源记录，未换新RTL。完整宏、一般分布式RC/拼接、共同底座、两产品与参数库仍未验收。

- 2026-10-27 10:44 CST：118/92179通过7:03、MaxRSS6895360K；原C8前后各14条已使用网无驱动，原adebug[6]/mdebug[4]均为零。显式映射2837个LOGIC0_X1和293个LOGIC1_X1后，逐比特恢复原常量与改变常量负例通过。123准备通过10秒，124 A/C各30秒、4389端口/496784单元/1157095.478um²，498287条已使用网均有驱动，原M10接点和轨道一致；125边界通过9秒。121/92183完整ODB信号网表功能通过14:50、MaxRSS20343472K，三初态各242事务/264051周期/3295817检查；120独立原生DRC仍运行。新增128/129完整新源预制修复/接收链，纳入已资格的真实输入保护、M10 via-in-pin、cap40与5ps hold目标，尚未部署；126/127只部署未提交，不再自动调度。完整宏、一般RC/拼接及P4–P6未验收。

2026-10-27 07:39 CST：094/92123已成功独立导出GDS并进入官方原生DRC，之前目录缺失问题实际修复；完整接收仍运行，源报告cap/setup/hold为0不等于独立验收。新增097逐节点电容/逐边电阻SPEF读回及保总量换值负例，合成TSV正例/六负例通过，实际OpenDB与测量回装尚未执行；源已部署，依赖096。096仍等8槽内空位，095必须等094完整通过。

2026-10-27 07:33 CST：093 T6KC/92115自然完成23:59，MaxRSS20889780K；封存原生源报告cap/setup/hold计数均0，精确最差cap slack +4.12317419052124 fF。报告SHA a579f5d04636112ebeb0881fc1c474c383525491c271b0c074673fa2a44b27cb，源回执28a8a4372500bc67739277113c061edd067da6993e1084bb28d0d1f3fbc66ced。094/92123已在node24/32CPU运行独立完整物理验收；尚未通过，不能据源报告冻结宏。原080八项/088一项失败保留；40档修复未更改Liberty限值、时钟、负载或预算。095宏视图依赖094全部通过，096真实路由测量仍等槽；当前本任务8个allocation。

2026-10-27 07:24 CST：091/92117两路图节点场解/FV科学对照完成11:07，四节点分支与五节点via全部锁定门槛通过，仍仅node-to-net起点电荷。释放node21后已启动080 C8A/92120，当前8个allocation继续运行。093 T6KC CAP_MARGIN=40进入详细布线，未取得最终电气结果。新增096真实路由8节点电荷测量代码，坐标源绑定及六种负例通过，已部署、全局8槽已满尚无Slurm任务；不把长度分摊或局部通过当作完整分布式RC。全部物理宏、最终功能/边界、共同底座与两产品仍未验收。

负责人 YUZE-LU；[任务](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)。
分支 `task/121-block-v1-twelve-layer`，独立工作树，不改变 #116 工作区。

## 当前执行快照：2026-10-27 CST

当前快照：2026-10-27 10:20 CST：111原生route/final完成23:43、MaxRSS12560612K；106完整独立DRC失败202项，其他14门槛通过，仍不能冻结。116/117实际网表与ODB定位C8未匹配输出为adebug[6]/mdebug[4]，最终缓冲根网仍无驱动；118原始常量、tie映射及完整已使用网驱动探针运行，严格LEC零未匹配不豁免。112因标准ORFS导出过滤天线单元而失败，新增从实际ODB保留全部信号单元的功能视图，精确核除输入-only保护外的全部连接；120/92182独立物理与121/92183三初态完整信号网表功能并行运行。119超长任务ID提交前拒绝，无job；原失败均保留。当前八allocation，其他成员任务未动。完整物理宏、一般分布式RC/拼接、共同底座、两产品与参数库仍未验收。 计划SHA不变。详见[常量与完整信号视图决策](../../../../docs/decisions/2026-10-27-block-v1-constant-and-full-signal-views.md)。登记PR5 pending，看板unverified/同步pending，审查人及管理员待指定。

- run069/070：研究通量分片变体保留源文件前后SHA，原作者参考和线程一致性通过；直线左右电容与独立FV、三网格/远边界/offset及交换负例全部通过。不是完整分布式RC资格。run074节点对耦合探针node19/48CPU/UNLIMITED完成7:48；独立FV和保持行列边际的重连负例通过，仍不覆盖一般分支或完整提取。
- run073：真实DFF buffer/强度调整正例、D/CK/输出三种真实负例及五个报告故障控制通过；原071脚本名、072日志重复摘要失败保留。最终接收器要求显式UNSAT/IDENTICAL、完整且非空边界相等，并另报core面积。
- 原068仅创建等待依赖，未提交Slurm，不再调度旧版；新接收器须跟随080成功封存后另开run。
- run043/044：八种实例方向、真实路由/过孔/实例pin及原生/新增特殊PG线，与独立GDS mask union完全一致。run041迭代器生命周期崩溃和042接口失败保留。
- run051：真实内部M10接入几何的场解总C、8节点/7边电阻图与SPEF读回通过；局部C分配仍是长度加权估计，完整分布式RC不合格。
- run052：清除signed显示元数据后逐模块/单元/引脚比对同构，单pin负例拒绝；没有RTL再综合。原run048/050导入与比较失败保留。
- run053核实原生命令单位ns/fF/kOhm，历史0.002直接set_load的单位错误已定位，后续统一2fF。run054重新生成；run055实际四种导入和M10坐标通过；run056STA写回完整IO/负载及负例通过。见[输入决策](../../../../docs/decisions/2026-10-27-block-v1-native-candidate-inputs.md)。
- run062/063/066：真实STA正例、过载/过快时钟/连接输入漏RC及四种端点故障控制通过；实际未放置/断PG负例已拒。独立最终物理接收器就绪、尚未取得完整候选结果。
- run064：完整有限几何与窗口对照，16μm泄漏超限拒绝，64/128μm通过；不是分布式RC资格。新客户端不改求解核心。
- [run057提交清单](stage53-manifest.json)：四个原生候选已开始独立P&R，使用原生十层TECH/RCX和固定映射来源，保留默认检查。完整STA/电气/PG/DRC/RC覆盖、最终网表功能、宏模型/共同底座/产品定制均待验收。

- run009：91905 新层路由接入和原生 SAMENET/EOL 读回通过；91907 数学/协议 8 种语义故障均被拒绝，原始证据未修改。
- run010：91909 完整同源叶块网表、4389/386 位端口和 SDC 已生成；91910 原生 GDS/图层映射审计通过。物理预算见正式决策。
- [run012](results/run012/index.json)：91914 独立 GDS 接入几何、M10 mask 不变和五类负例通过；91916 更新的官方固定场求解器通过原作者 2D/3D 参考及线程/介质缩放检查。91915 解码 133488 条线网覆盖全部十二层。
- 后续科学复核发现校准分组必须包含同实验的全部 cntxM 导体；91915 的旧分组不可用于 RC 校准，修正另开 run。见[场景决策](../../../../docs/decisions/2026-10-27-block-v1-calibration-scenes.md)。完整校准/模型拟合/留出验证、全层 DRC、正式硬化与共同底座冻结、两产品定制均未完成。
- run013/014 修正分组和新版求解器资格/先导通过。run015 实际使用 node14–node19 六台96核节点，各8×12线程；严格点估计符号断言拒绝原结果，run016按预先记录的统计接收界限独立重验全部通过，原始输出不改。
- run019：3840行场解＋3344个DC图形实际拟合；逐网R/地C/耦合C读回最大缩放误差低于6e-8。该模型只是候选。run020旧格式读取崩溃；run021现代格式可读，run022实际耦合提取崩溃，未进入留出数值比较。发现距离3校准留下1542个空表，正在准备全十二层上下文新批；不会将这些失败当作RC资格通过。

### 03:27 CST 增量

- run024–026 完整上下文与六分片参考场解通过；run029 候选拟合通过，2472表的有效覆盖检查通过。188个官方未使用格式槽位为空是合法的，不放宽实际必需表检查。
- run030 实际提取完成但跨层耦合留出失败；run031 的2.0/2.2/2.3均未解决，旧模型未验收。
- [run034](results/run034/index.json)：91986–91991，node14–node19六台机器，六种小几何的直接场解与独立有限体积参考全部通过，三网格、远边界、残差和预先锁定阈值均通过。
- [run036](results/run036/index.json)：六例真实DEF/SPEF/OpenDB及独立GDS mask集合核对通过；错误电容单位和折掉耦合的负例均被拒。短线π网络尚不代表完整Block分布式RC。
- [run037](results/run037/index.json)：实际路由ODB路径/过孔/端口可直接导出，实例pin与PG尚需补齐；run038实例坐标API探针失败保留，修正另开run039。详见[直接场解决策](../../../../docs/decisions/2026-10-27-block-v1-direct-field-extraction.md)。
- 91903完整映射门级已编译，正在运行两种背压混合回归；未取得完整回执，不提前记通过。正式Block P&R仍未开始。

以下保留各早期阶段的历史记录；其中“尚未”以本节当前快照为准。

## 初期状态：P0/P1，尚未进入正式 Block P&R

按 `docs/plans/block-v1-nangate45-m11-m12.md` 全部阶段执行，不能将以下局部工作等同于 v1 完成。

- 原计划 SHA256 `2ef18149c806cfbda996bbc91b69c84b31781ad9553e7093630d1f7a2ddc20cf`；源闭包33文件全部满足原科学SHA与发布Git blob，见 source-manifest/source-import。
- 2026-10-27 CST，探针91865/node13失败：计算节点PATH缺Singularity，原日志保留。修正显式PATH后91866/node13 `COMPLETED 0:0`；Python3.10.12、Verilator5.042、Yosys0.68+post、KLayout0.30.12可用；OpenROAD版本字符串unknown，按二进制SHA绑定。
- 探针镜像SHA `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`；实际tech LEF SHA `834a79295054cd4209178d1bade67c353863c47bb4b3c22ee38b862b7cec37f2`；原生最高metal10、cut到via9、RCX LayerCount10。
- `transaction6k.sv`：真实384×128bit，顺序填充、整事务commit/revoke、同步读取、背压保持、消费者单引用lease释放；复用前必须完整覆写，无RAM reset假设。测试/映射结果须看实际作业回执，源码存在不代表通过。
- `shared121.sv`：保留C8控制器/观察接口，内部接真实T6K，只有core DONE成功后发布payload；候选接收后等待root提交完成；DONE ACK等消费者release。基线数学/外存桥/单一S16K不改。新顶层回归尚未验收。
- `technology.json`/`overlay.py`：十二层几何研究起点，M10 landing不需后增补；原生字节精确保留。early RC明确仅估算，完整RCX/耦合校准和新层DRC尚未完成。
- 单dispatcher跨本Issue各run共用预算锁；六基础/八上限，排队及未知提交计槽，节点内线程显式分配。只轮询本任务jobID，不改其他作业。
- 003批91872–91877全部在启动时失败（exit2）：Git archive受Windows core.autocrlf影响导出CRLF，未进入业务计算。blob实为LF，新增bundle.py直接逐Git blob打包、shell LF负检查及worker逐文件SHA验证，另开新run，不改旧日志。

服务器成果根：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/`。
`block-v1-20261027-001`/`002`为以上两个探针；后续各run以不可变manifest和状态记录。

## 尚未验收的完整范围

### 2026-10-27 CST：已取得的实际业务证据

- [草稿 PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)，持续实施，未合并。
- 004批：91878 T6K随机242事务、264051周期、3295817断言通过；91879两种真实存储映射通过；91880完整C8＋S16K＋T6K映射通过，Yosys层次面积1538342.904 μm²，尚未独立库存接收或PPA验收。
- 006批：91893完整13命令混合回归、91894完整44命令恢复回归，各在两种背压条件下运行，独立整数接收全部通过；91895十二层LEF/OpenDB读回通过。见 [run006/index.json](results/run006/index.json)。
- 004/005/006结果保留原失败：旧LEF版本语法失败、旧工具缺PythonAPI失败均不覆盖；修正后使用新批次。十二层读回通过不等于路由、DRC、RC提取通过。
- 当前工具不带内置场求解接口。计划编译官方固定提交6ea4ca的独立C++场求解闭包，先校验原作者2D/3D有限体积参考算例及线程一致性，再开展研究RC校准。源码53文件257109字节，归档SHA `b2eaefce378aba09cccb966b3c56486412f1958e0a83ff3fb313fd35b3dfe2a7`；清单见fsv-source-manifest.json。尚未编译或宣称校准完成。
- 上述短作业实际由Slurm分配到node13；“六基础/八上限”是本任务并行预算，不能把同机多个allocation声称为六台物理节点已被利用。重型物理阶段依据实际分配CPU/RAM装箱。

独立全部真实存储与逻辑库存；数学/协议接收负例；精确映射门级；P0存储实体/预算定版；原生层硬化、PG/CTS、严格完整STA/电气；真实M10内部pin/OBS与边缘对照；十二层RCX/DRC校准；宏同源与最终门级；共同底座冻结；同底座两产品仅新层定制及敏感性；正式参数库/PR审查。均保留在#121，不提前关闭。

登记沿用管理中心PR5 pending。当前无board.json及Projects能力，真实看板unverified、同步pending，管理员待指定；不能以管理CI代替研究验收。


`annotation-parser-proof.json`为实际54837条原生未注释报告的离线解析身份/顺序/六种故障控制，仅语法，不代替连接检查。`native-t6kc-057-cap-observation.json`绑定原始最终报告与回执SHA，是13项cap违例的源报告观察，不是独立接收通过。原报告、数据库和运行均不改。


08:32独立STA诊断：094-A/92149运行中的独立STA已完成中间报告：104356个端点，4个hold负端点；最差hold −0.000622502 ns（约−0.623 ps），最差setup +5.227097988 ns，cap计数0、精确最差cap slack +4.102060317993164 fF。端点为slice86879/87007/87391/87519的D端，完整名字及首批展开路径保留于run094-t6ka-sta-intermediate。下载与远端再次读取SHA一致；该目录只证明已生成的独立STA中间证据，完整物理作业仍运行，不能代替终态接收。


## 2026-10-27 08:52 CST 原生修复准备

新增原生DRC只读定位与严格5ps hold修复入口：真实61标记解析/五坏输入、Linux实际源码的配置正例/八负例通过，未替代物理接收。103定位已部署（源码5449132、归档c41fffa3946f15c1ccaa18cd225fe358668285f86f7230204e39fba1e88c7bd5，8CPU/node24）；105边缘T6KA修复与106独立接收已部署（源码a504854、归档d932b5930e7e1e61bfe4108612088be5a6be5d49f811436602c57d4df8372a17，各32CPU/node20和node24），均121成员/849920字节，当前无Slurm job，依统一八槽预算等待。104在预检发现小写策略不兼容后停选，实际未提交，未覆盖原manifest。080 C8C进入最终LEC，中间日志有两个diff1 outputs，严格完整对应门槛保留；094A仍在完整DRC、100双48CPU科学验证仍运行。

证据：`results/native-drc-location-controls.json`、`results/native-hold5-config-controls.json`、`results/run103-initial/`、`results/run104-not-submitted/`、`results/run105-initial/`、`results/run106-initial/`、`results/live-105.json`；部署manifest为stage99–stage102。live-105中100 children路径为组目录下观察，空列表不能证明其真实任务目录缺文件，实际子任务另在tasks/capture-branch-fv及tasks/capture-via-fv。

恢复先读Slurm真实状态，按103→105→106优先调度，104不再选择；保留所有活跃作业，不因耗时终止。103命中仅用于确定实际网络，再决定M10间距及天线预制修复；105必须通过严格独立接收和实际最终网表功能，不能用配置控制充当时序修复。


## 2026-10-27 09:04 CST 科学对照及实际DRC定位终态

100/92147双向joint-node科学验证通过：31:20、MaxRSS7392852K、96CPU内两48CPU；分支与via两方向的细化/外推/远边界/offset/统计/局部电容/互易/保边际错误重连全部通过。103/92154只读原生定位通过：33秒、MaxRSS685692K，扫描220361网/5734869形状、236次命中，61个标记无遗漏。M10三间距项对应read_index[7]/[8]，间距0.13um对0.8um规则；58天线项经原正交多边形精确面积筛选全部单网候选，marker42排除begin_words[5]、保留begin_words[6]，共53个输入网络。105/92157严格5ps边缘T6KA修复在node20/32CPU运行，106独立接收已部署、尚无job。094A完整DRC仍活跃；080 C8C进入RCX，但LEC日志两个未匹配输出边界仍需严格接收。

证据：`results/run100-terminal/`、`results/capture-node-scientific-summary.json`、`results/run103-first-native/`、`results/native-drc-polygon-diagnosis.json`、`results/native-drc-polygon-controls.json`、`results/run105-first-native/`、`results/live-107.json`。未改动原报告、数据库、原门面积或300比值；全部原生失败仍需完整重跑，不把定位或局部RC通过当作宏签核。下一步核实际库GDS的输入门/扩散连通与可用修复单元，明确M10接入重路由方案，同时接收105与080新终态。


## 2026-10-27 17:28 CST 实际终态与后继入口

165/92314实际C8 A/C探针全部11门通过，4:36、TotalCPU7:29.230、MaxRSS4128260K，node25同allocation双2CPU。A45/C29网改动，其中15/4处via9落点；原生upper诊断合并标记A37/C25降至0，完整upper接触0、固定低层/其他网/完整V及源SHA保持。这不是162原raw49/37项的完整GDS接收。166/92326只读严格LEC诊断双1CPU实际通过，0:50、CPU1:20.266、MaxRSS71428K；A/C时序实例143988逐名相同，无新增/删除，A501/C277处DFF_X1变DFF_X2，无字面x/z输入，但尚未证明原生未匹配PI对应，不豁免严格门。141/92256实际FAILED/1:40:06/CPU3:20:52/MaxRSS358556384K，同样被严格C8 LEC拒绝，未完成组合功能。新167准备从实际165接受ODB重新原生最终输出/默认flow LEC/RCX及全片DRT，c96双8CPU，200GiB/路加20%余量；本次提交时尚未运行。T6K161完整接收和164视图通过仍不等于宏边界资格；164 Liberty PG及完整flat timing源另以新版本修正。17:25本任务4个RUNNING allocation（057三路、067）；统一预算基础6/上限8，含PENDING/未知；其他成员未操作。完整P0–P6未完成。

证据：results/run165-group-terminal、run165a/c-terminal、run166-group-terminal、run166a/c-terminal和run141-group/a/c-terminal（均位于work/YUZE-LU/121/）。167采用native_pipeline_c8_escape.json、native-c8-finish-group / native-c8-run-shared109-a/c，保持严格状态边界LEC未通过标志；不启动已知依赖失败的完整接收。


## 2026-10-27 17:44 CST 实际执行

168/92335实际T6K两路typed PG与完整flat timing网表交付通过，0:58、TotalCPU2:54.816、MaxRSS3193048K，node21双8CPU。原始模型保留，VDD/VSS仅转换pg_pin，精确逆变换证明全部其他模型字节不变；实际原生读回power/ground及is_pwr_gnd全部通过。candidate-timing.v严格复制161实际ODB完整信号导出，两路各保留189保护单元并绑定完整proof，旧6_final.v继续保留但不能充当full-SPEF flat源。169/92336用PR128固定5eda23a源只读导出实际ODB占用，node22双1CPU，2:47、CPU4:07.617、MaxRSS3592768K；A453227实例/2229968个master OBS、C451330/2232347；完整占用666023293/664926056字节保留服务器并封存SHA。仅导出通过，独立覆盖/边界资格仍待#127。167/92333仍RUNNING，node20双8CPU，不能先称C8新RC/全片DRC通过。新170准备补查严格C8前后完整图的无驱动使用bit及未使用输出，不改图/日志/严格门，本次提交尚未运行。完整P0–P6及宏冻结/两个新增层产品未完成；登记pending、看板unverified/同步pending、待独立审查。

168/169 group与全部peer终态索引均位于work/YUZE-LU/121/results/run168-*及run169-*；同源交接inventory为t6k-qa127-handoff-168.json，每路30角色，仅索引，独立pack仍需前后hash。


2026-10-27 17:58 CST：171/92340实际两路常量极性对照通过，9秒、CPU6.149秒，MaxRSS=0记为无有效采样。原生改名tie每侧1个未匹配输入；真实库常量literal编码后严格4输入/4输出全对应、UNSAT/IDENTICAL通过，错误tie极性和错误DFF时钟均有SAT/Found difference而拒绝。原inspect严格门不改。172准备对134原失败的两份完整C8图逐项逆变换/发射重读回证明，再重复完整严格LEC；同c96双2CPU，200GiB/路加20%RAM预检，本次提交尚未运行，仍非实际完整C8资格。167最终输出仍RUNNING，未取消旧作业。

完整172重验只读取134封存图，不改变其原失败、实际ODB/PG/RC/时序或功能网表。通过仍需与新167源的完整接收/最终功能绑定，不能把旧图形式结果直接宣布新物理宏合格。
