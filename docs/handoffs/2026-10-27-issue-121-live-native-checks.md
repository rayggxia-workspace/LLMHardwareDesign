2026-10-27 23:58 CST：M205实际完成补铜后的最终report/RCX重生（104秒）；新ODB/DEF全部导体与硬件、约束均与204接受候选精确一致，原生全片DRC0，五份新final V/SDC/DEF/ODB/SPEF已生成。仍须用新产物重新跑所有独立接收，不能沿用193的STA/功能资格。203现准备21项独立/DAG工作：V唯一基础版P&R；M/S/R/V各四项最终接收；每块通过后自动生成同源最终文件索引、实际M10 pin清单和全层版图图。节点默认6×16即完即补，尚未新增allocation；本任务八槽已满，长任务等待自然释放，旧实验保留。Issue121继续in_progress、PR122草稿未合并。

2026-10-27 23:55 CST：M/V/R/S/T五种基础宏，每种一个实现；全部最终M1–M10布局布线仍是本轮交付，不扩展阵列/两产品。V196原样RTL通过416344检查/310231周期，函数声明域逐Q16.16输入通过6291472检查、两路3级II=1；映射388350单元。R195原样RTL通过397971检查，完整映射707287单元/145877DFF、面积1328464.116um²，唯一外框1870×1870um；R196原生P&R运行，S190原生route运行，T保留既有C叶块证据。

M204补铜几何验证实际通过：M193同一条网添加[282460,530600,282650,531160]DBU的M2矩形，完整GDS所有多边形层精确差分只允许该新增并集，原生全片DRC0。尚不能据此沿用旧SPEF/STA或声称M最终合格；205仅最终report/RCX重生，之后逐项重新独立验收。197因路径迭代器漏RECT而严格失败；198/199为只读API诊断失败、200仅诊断通过；201普通线段同并集仍有一条原生DRC；202因GDS单位换算校验失败；204修正精确整数公约单位后通过，全部失败保留。204首次部署字符串替换误改日期目录，前置读取失败且未启动EDA；正确20261027目录新预检后运行，误目录无job。

资源仍为六旧baseline+190/196两allocation，共八；其他成员作业未动。204/205为现有196 allocation内有硬时限、经剩余CPU/RAM预检的短step，不额外占节点；长P&R及完整接收必须等独立allocation容量，不重复192父job退出终止长route的问题。203准备17项V布线及M/S/R/V独立接收DAG，默认6×16、完成即补位，尚无新增allocation；准备不等于提交/通过。Issue121=in_progress，PR122草稿未合并；登记pending、看板unverified/同步pending、独立审查人待指定。

2026-10-27 23:08 CST：五种基础宏主线继续。M193同560×560um外框/接口完成新route/RCX；独立全部端点setup最小1.737254ns、hold最小0.014780ns及电气/PG/连接通过，三初态实际最终网表功能与严格LEC通过（10558输入/10549输出全匹配、UNSAT/IDENTICAL）。完整FreePDK45 deck 0项，但独立原生全片DRC仍有同一处M2 Metal Spacing/NS Metal，不能验收M；196只读定位准备。原191的-2ps hold和5条时钟天线违规、192随父191退出被终止均保留；193以单独队列修复，并未增加裕量版本。

R首版真实RTL测试195通过240组GDN/SSM和100组四抽头卷积，397971检查/197111周期，包含长度256/128、溢出不改旧状态、候选commit/revoke、epoch耗尽、背压、reset失效；实际综合正在运行，尚无R最终P&R。V三通路RTL/内部RMS-L2-Softmax回放/40选8已写；195的V解析失败来自定宽十进制常量紧贴三元问号，196已修正待执行。独立V组级U128除法/平方根4000例与软件全Q16.16域系数扫描通过，不能代替V实际RTL函数/组合回归或模型质量。S190已完成place/CTS，进入独立route；T仍沿用既有完整C叶块证据与交付。195曾实际六个16CPU同时领取，结束即补位扫描；196尚无allocation，等待195释放第八槽，不提交第九个。194从未提交作业，其R工作已并入195；六旧baseline保留，其他成员未操作。全部五块仍未完成；Issue121=in_progress、PR122草稿未合并，登记pending、看板unverified/同步pending，独立审查人待指定。

2026-10-27 22:05 CST：五宏主线实际推进。M新RTL的1200组随机/边界tile、尾块、多tile、S8/S16/P15样例、K=65535守卫、跨组合并、RNE/饱和和背压通过（282066检查/203846周期）；S全1024地址与10000随机事务通过（91035检查）。M完整映射77203单元；S保留原131072bit标准单元存储，展开后376059单元，其中131201DFF，映射面积978028.268um²，不能称SRAM。186六独立16CPU实际并跑；186映射Yosys路径语法失败、187调度缺receipt mode、188 signed导入/scopeinfo元数据失败均保留，不冒充P&R通过。修正沿用已通过数值RTL和映射，没有重复ABC。189/92444 node26/96CPU中M已完成floorplan/place/CTS，正在route；190/92446 node24/96CPU中S展开/完整库存通过，独立原生流程已进入floorplan。当前仅这两块的物理输入就绪，V/R尚待RTL，节点内并发因实际依赖低于六；未启动虚构或重复工作占资源。本任务六旧baseline+两新allocation共八，其他成员不计入且未动。T真实最终GDS渲染和386个M10信号pin实际导出通过，图/pin已保存delivery/T。五块仍未全部完成，V/R实现与硬化、M/S最终全流程/独立完整接收继续，Issue保持in_progress、草稿PR122未合并。

2026-10-27 CST：用户明确冻结M/V/R/S/T五种基础宏，每种一个实现，要求全部最终M1–M10布局布线。裸M8/混合VS不是最终边界；旧四边界计划已归档，完整系统/两产品/一般十二层提取移至后续。92426在PENDING、0CPU、0elapsed时因边界改定取消，未执行EDA。T选定C实际叶块证据保留；新M/V/R/S尚未最终P&R通过。当前规格与执行入口为docs/BLOCK_LIBRARY_V1.md、docs/plans/block-v1-library-implementation.md，任务继续in_progress。

# Issue121 当前运行与继续入口

2026-10-27 21:01 CST：新四块独立功能/映射队列185已部署并实际提交92426，96CPU、六个16CPU任务；当前资源排队，本任务六RUNNING＋两PENDING共八allocation，不追加节点。源码8d6f3b77、archive12db5fe0741f10c5ffcb419d6f1232191d61f4d95cd0e9985e9b51b99868f4b0；Linux路径/DAG预检通过，不当功能/映射通过。T6K选择既有C结果，重新核对同源RTL、三类回执和10份最终产物SHA；完整单块物理/三初态最终功能通过，层次模型仍未合格。M8/VS/S16K新单块最终P&R仍待完成，本轮不能只交文档或综合。

2026-10-27 20:50 CST：用户明确将本轮目标收回“首版物理Block清单、规格、每个入选块的最终M1–M10布局布线及接收”。阵列/多实例/跨块预连/两个产品/通用十二层提取移至后续；历史实验与已提交作业自然收尾。当前从真实C8提出M8乘积、VS向量归约状态、独立S16K及既有T6K四种候选；M8并非完整MAC，最终边界须由真实pin/面积/时序验证。新增独立RTL及可逆源码重接准备，尚无新单块P&R通过；刚写的生产via草稿已封存且未部署。主线以docs/plans/block-v1-library-implementation.md为准，必须交最终逐块结果。

2026-10-27 20:16 CST：182/92402两份真实wire/via/pin并集与封存科学几何一致，六种SPEF原生读回/拒绝实际通过（50秒/CPU5.432秒/组MaxRSS12280K）。184/92404实际直接节点位置接收通过：branch六/via七个实际Iterm变换后pin中心、层与ID全匹配；各自移2DBU/交换同层左右锚点的原生反例保留完整导体并集和全部电气值，却被位置门拒绝（12秒/CPU3.903秒/组MaxRSS0为无有效采样）。183原尝试10秒因FIRM实例保护提前拒绝，完整失败保留；184只改变测试副本且恢复status，不修改封存源。当前两科学fixture来源闭环增强，不等于生产0.6um via、一般十二层提取/拼接/完整Block资格。固定PR128 fbbd5ec显式输出RC十二个实际小例记录已读取，全部输出差逐项复算；它的内部core参考面不可直接替代公开M10pin Lib，真实宏资格仍false。178/181完整C8接收、两全deck GDS检查继续等待实际终态；完整P0–P6未完成。

2026-10-27 19:49 CST：172/92341完整旧C8 A/C严格LEC实际全部通过（输入289078/输出291263全匹配、UNSAT/IDENTICAL），不借此资格167新源。180/92385实际原生耦合SPEF接收通过：branch六节点/八对C/四R，via七节点/十对C/五R；每几何五个原生破坏输入均拒绝，重连控制保留逐节点耦合边际仍被拒。57秒/CPU6.379秒/Slurm组MaxRSS11092K为短任务采样，不当单项峰值。两科学fixture组装/导入通过，不等于一般routed十二层提取/原生拼接/Block资格。181/92386已在node25实际领取A完整物理接收；178/92362在node23运行A/C全deck GDS检查及C完整接收，A/C各自接续不等对侧。179/92379仍PENDING于node24，唯一共享claim避免重复；当前本任务六RUNNING加一PENDING共七allocation，其他成员不计入且未操作。固定PR128 cb3a089输入残差逐项复算通过，但输出RC反例及A/C输出slew超差146/106仍阻止紧凑模型资格。完整P0–P6/冻结共同底座/两差异产品/独立审查未完成。

2026-10-27 19:19 CST：167/92333实际完整A/C最终输出组COMPLETED/1:43:46，TotalCPU4:19:55、组MaxRSS283181384K（约270GiB，不能除以2当作单项峰值）。两路各7门均通过：165接受ODB重生最终输出及RCX、完整硬件/几何/约束保持、全片原生router DRC0。该16CPU双8历史组平均约15.7% CPU使用，只是不同阶段实际占用，不是加速比；支持后继以更多独立任务填节点。严格状态边界LEC仍等172、新独立全deck GDS DRC/完整物理/精确组合功能/宏均待通过。当前本任务6个allocation（旧057三路、067、172和178），未取消任何旧作业；完整P0–P6仍未完成。

2026-10-27 19:12 CST：178/92362实际RUNNING于node23，Slurm申请96CPU，共享队列两项完整C8 GDS检查已分别领取；当前其余四项由真实167/172或各自物理接收依赖阻挡，未发生内存装箱阻挡。节点实际RAM503.5GiB、读回可用约491GiB（瞬时值）；70/200GiB预算明确是历史不同阶段估计，非当前单项实测。完整队列按CPU动态装箱/完成即补位，当前实际两路不冒充6路EDA吞吐。177/92361因Windows反斜杠路径被前置校验拒绝，10秒FAILED，未启动EDA子项；完整失败保留，新178仅修正POSIX配置、Linux验证与实际依赖预检。178/177源2255b197b2ea67136c56e0bf16e500fc52a59b53，archive f2488e8e481b88123cbf00662937860728549d4e8a0777575dc46da8051ebf0f。175实际控制通过，174/176旧小group仍无job；本任务7个RUNNING allocation，其他成员不计入且未操作。PR128固定f3f5df8私有min/max原型24对照改善输出min，但真实T6K仍955/897诊断超差；不替换服务器/主线工具、不宣称宏合格。完整P0–P6继续。

2026-10-27 19:04 CST：按用户纠正改为本任务6～8节点、c96实际96CPU队列默认6×16、完成即补位；只有内存不足或真实依赖才降并发并记录具体依据。原计划第9.2节已修订并保留审查原版。新增共享claim/CPU装箱/独立分支失败隔离/依赖等待释放节点调度，真实生产路径的六任务计时控制通过，非EDA加速比。175/92352初始化与38个物理来源合同破坏控制实际通过（57秒/CPU8.623秒/MaxRSS16756K为组数据）；176已部署无job。未提交174/176旧小分组停止后续调度，计划由177整节点队列直接运行其各自leaf，保留旧manifest。177代码及六工作项准备，尚未部署。167/172仍待实际终态，完整P0–P6/宏/两产品未完成。

当前资源规则以[节点内队列决策](../decisions/2026-10-27-block-v1-intranode-parallelism.md)顶部为准。不得提交174/176旧group；177共享queue按候选直接运行174完整接收leaf、176完整组合leaf。各leaf的实际父job以node-queue-state.json的owner为准，不伪称旧group有Slurm job。队列无本地活跃项且只等外部依赖时保存未领取项并释放节点；以后继allocation恢复同一不可变队列，不占96CPU空等。


2026-10-27 18:22 CST。目标仍为批准的完整P0–P6，不是只交单个探针。仓库rayggxia-workspace/LLMHardwareDesign，Issue121、草稿PR122，分支task/121-block-v1-twelve-layer。172生产源码5614eff28472bf2bf54329c4f40b59c200ae7dfe；173/174源码2937f9c90bc4d55772b2a477407e254f3738efaf，archive26c12abad3caf6dc77e56f259458e12babd512a82e725b45057ea2a7b8136def。全部有源资源/位置/PG/CTS及M1–M10先冻结，后续两产品只改变M11/M12/via10/via11。当前没有冻结宏。

## 恢复先读实际作业

明确的本任务活跃allocation为92045/92046/92047（旧057）、92062（067完整映射功能）、92333（167 C8新原生最终输出）、92341（172完整C8严格LEC重验）；18:22六个均RUNNING，最新实际队列与部署SHA见work/YUZE-LU/121/run174-deployment.json。173/92348已COMPLETED通过；174已部署但依赖167/172/173，dispatch-state.tasks为空、没有Slurm job，不占allocation。不得只按manifest中的旧PENDING判断实际状态，不重复sbatch；预算基础6/最多8含PENDING与提交不明。其他成员不计入且不操作；不因耗时取消旧任务。

根目录/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121。167位于block-v1-20261027-167，group native-c8-finish-group，node20/16CPU，A/C各8CPU；172位于block-v1-20261027-172，group native-c8-tie-lec-group，node21/4CPU，A/C各2CPU，200GiB/路加20%内存预检。worker保持各自日志/receipt，peer失败互不取消，独立目录。第一步用squeue/sacct和实际receipt读取终态；两路都成功前不启动完整接收消费者。新诊断/导出等串行代码按1CPU/路，不能仅增加单任务NUM_CORES凑96核。

## 已确认与未完成

161实际T6K A/C完整物理18门及三初态真实最终存储单元功能通过；168同源供电修正/完整时序Verilog交付原生读回通过；169固定PR128工具完整原生占用导出通过。交接inventory为work/YUZE-LU/121/t6k-qa127-handoff-168.json，两路30角色。完整SPEF flat必须使用candidate-timing.v或实际ODB；旧6_final.v过滤189保护单元而只保留作原流程来源。PR128最新固定bd91c42207f51127a785e4815488c3f6f50b036c已实际独立接收typed PG/full timing V和169源金属OBS覆盖，A9208361/C9206675矩形未覆盖均0、SPEF名称缺失告警0；不能再把这些已修好项写成待做。时序A958/C900项超预设1ps诊断门，仍不合格。固定报告/控制源码Git blob已读回并记录macro-qa128-update-bd91c42.json；这仍不是全部弧/例外/corner/active-net RC与正式宏准确性资格。

165实际有限C8几何11门通过，但只是upper诊断子集。162旧完整原生49/37违规、134/141严格LEC拒绝均保留。170图诊断确认前后已用输入bit/顶层输出均有驱动，原未匹配数恰等于1004/1032个tie。171实际0/1两种常量对照均通过：原生改名tie每侧产生1个未匹配PI，按真实库常量函数作可逆Boolean编码后严格4输入/4输出全匹配、UNSAT/IDENTICAL通过；错误tie极性和DFF时钟仍明确SAT拒绝。172将该严格编码用于134封存完整图，保留真实物理tie、源失败及native_formal.inspect全部门，当前未终态；即便通过也只是旧同源完整图形式资格，不能直接资格新的167物理源。

173/92348实际组合控制双1CPU通过，16秒、CPU9.489秒，MaxRSS=0无有效采样。保护单元投影与常量编码衔接后，真实两种常量正例严格4输入/4输出全匹配、UNSAT/IDENTICAL，错tie/clock均SAT拒绝；实际实例化master的statetable/state_function需拒绝。原inspect AST保持逐项相同。组及两路完整终态位于results/run173-*。

若167和172成功：读取177共享队列实际就绪项与Slurm预算，以新的96CPU allocation恢复同一队列；不要提交旧174 group。A/C各自对167新源做全部完整物理门，并各自接续176完整组合接收；不依赖对侧候选的无关完成屏障，也不借旧图结果资格新源。175新控制已实际通过；旧140/141结果保持。

当前宏Lib仍有独立min/max边界问题。已读[固定OpenSTA源码](https://github.com/The-OpenROAD-Project/OpenSTA/blob/bc7af6f02679074eaf43657488ca117c05f98eed/search/MakeTimingModel.cc#L76)，构造选择max；原生单套输出表不得未经min/hold实测就当作同时准确的min/max模型。#127正在做独立短/长路径反例及有效工作域，主线保持168为候选。可考虑经明确控制的分离min/max导出或可证明安全包络；本轮尚未实施，不通过放宽误差或吞掉warning来冻结。

一般多网分布耦合十二层提取/原生拼接和窗口归属、全部glue物理、共同底座、有源/原生层差分固定、仅新增层两产品、敏感性/参数库和独立审查合并仍未完成。python scripts/check_project.py、变动Python py_compile、git diff --check及各处声明的真实控制均通过；它们不替代上述业务验收。

规则rayggxia-project-collab1.0.0，实际账号YUZE-LU。管理中心PR5未合并为pending；无board.json及Projects工具，实际看板unverified/同步pending，管理员/审查人待指定。Issue保持in_progress，PR未合并；没有自行标done、关闭或合并。持续工作的入口为本文件、Issue121实际在线快照和当前Slurm终态。
