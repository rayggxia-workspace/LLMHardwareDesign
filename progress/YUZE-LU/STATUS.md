# YUZE-LU 的进度

- 2026-10-27 10:44 CST：118/92179通过7:03、MaxRSS6895360K；原C8前后各14条已使用网无驱动，原adebug[6]/mdebug[4]均为零。显式映射2837个LOGIC0_X1和293个LOGIC1_X1后，逐比特恢复原常量与改变常量负例通过。123准备通过10秒，124 A/C各30秒、4389端口/496784单元/1157095.478um²，498287条已使用网均有驱动，原M10接点和轨道一致；125边界通过9秒。121/92183完整ODB信号网表功能通过14:50、MaxRSS20343472K，三初态各242事务/264051周期/3295817检查；120独立原生DRC仍运行。新增128/129完整新源预制修复/接收链，纳入已资格的真实输入保护、M10 via-in-pin、cap40与5ps hold目标，尚未部署；126/127只部署未提交，不再自动调度。完整宏、一般RC/拼接及P4–P6未验收。

- 2026-10-27 10:20 CST：111原生route/final完成23:43、MaxRSS12560612K；106完整独立DRC失败202项，其他14门槛通过，仍不能冻结。116/117实际网表与ODB定位C8未匹配输出为adebug[6]/mdebug[4]，最终缓冲根网仍无驱动；118原始常量、tie映射及完整已使用网驱动探针运行，严格LEC零未匹配不豁免。112因标准ORFS导出过滤天线单元而失败，新增从实际ODB保留全部信号单元的功能视图，精确核除输入-only保护外的全部连接；120/92182独立物理与121/92183三初态完整信号网表功能并行运行。119超长任务ID提交前拒绝，无job；原失败均保留。当前八allocation，其他成员任务未动。完整物理宏、一般分布式RC/拼接、共同底座、两产品与参数库仍未验收。

- 2026-10-27 09:40 CST：108实际库门面积/Liberty探针通过，BUF_X1与CLKBUF_X1输入门面积分别0.02625/0.0205um²，与原DRC一致。110实际GDS二极管对照通过：完整原deck下接通为零DRC，不接/断线/去contact均检出天线；输入-only逻辑投影精确逆重建、严格零未匹配LEC及真实逻辑改错/三种投影坏输入通过。113实际CTS合法化与M10 via-in-pin接入通过（1:52、MaxRSS1590156K），189个真实ANTENNA_X1，增加50.274um²、合计4.428081fF输入负载。111/92171完整预制修复在node20/32CPU运行；112独立接收已部署、尚无job。105/92157完成23:11、MaxRSS21286428K；106/92165独立STA中104356端点无负值、最差hold约+2.42ps，完整DRC仍在运行。094A终态失败210项（21间距/cut+189天线），原四hold失败保留；114/92172只读定位在node23/8CPU运行。09:39本任务八个allocation均RUNNING。完整物理宏与P4–P6仍未验收。

- 2026-10-27 09:04 CST：100/92147双向joint-node科学验证通过：31:20、MaxRSS7392852K、96CPU内两48CPU；分支与via两方向的细化/外推/远边界/offset/统计/局部电容/互易/保边际错误重连全部通过。103/92154只读原生定位通过：33秒、MaxRSS685692K，扫描220361网/5734869形状、236次命中，61个标记无遗漏。M10三间距项对应read_index[7]/[8]，间距0.13um对0.8um规则；58天线项经原正交多边形精确面积筛选全部单网候选，marker42排除begin_words[5]、保留begin_words[6]，共53个输入网络。105/92157严格5ps边缘T6KA修复在node20/32CPU运行，106独立接收已部署、尚无job。094A完整DRC仍活跃；080 C8C进入RCX，但LEC日志两个未匹配输出边界仍需严格接收。

- 2026-10-27 08:52 CST：新增原生DRC只读定位与严格5ps hold修复入口：真实61标记解析/五坏输入、Linux实际源码的配置正例/八负例通过，未替代物理接收。103定位已部署（源码5449132、归档c41fffa3946f15c1ccaa18cd225fe358668285f86f7230204e39fba1e88c7bd5，8CPU/node24）；105边缘T6KA修复与106独立接收已部署（源码a504854、归档d932b5930e7e1e61bfe4108612088be5a6be5d49f811436602c57d4df8372a17，各32CPU/node20和node24），均121成员/849920字节，当前无Slurm job，依统一八槽预算等待。104在预检发现小写策略不兼容后停选，实际未提交，未覆盖原manifest。080 C8C进入最终LEC，中间日志有两个diff1 outputs，严格完整对应门槛保留；094A仍在完整DRC、100双48CPU科学验证仍运行。

- 2026-10-27 08:29 CST：101/92144精确最终T6KC网表功能接收通过：8:43、MaxRSS3810680K，全1及随机121/122三个初态均242事务/264051周期/3295817检查，保留原映射存储和Liberty单元；回执b4b7ec85ca9d5f4b1bd9ac277d4480401d002fbd1ce5d9b5527c390785cd3075。102/92148实际SPEF导入通过：43秒、MaxRSS12820K，8节点/7边身份、逐C/R、单位和总量七门槛，实际错误单位/保总量换节点C/换边R三负例均正确拒绝；回执a8a81b3db9acbd12cdce56251d6eb9ea543fa0bc829269264bbe3f9300fd6ae6。该单隔离网络仍无本路由独立局部FV/一般跨网节点耦合与全Block提取资格。100/92147双48CPU科学对照继续；094边缘T6KA独立接收已提交92149，源hold count=4待精确STA诊断。内部094的61项DRC失败仍阻止冻结；095宏视图不绕过依赖。

- 2026-10-27 08:25 CST：102修复回装已部署（源码5f43b4e、归档7d4cd3c6f3055312eba84680ab35a77168fddb88e0b44bef7fa84c7879063356，118成员/829440字节），8CPU/node24，目前尚无Slurm作业；保持全局8槽。100/92147确认在node23/96CPU运行；101/92144完成构建并已进入三初态并行模拟，尚无通过回执。093 T6KA源报告实际hold violation count=4（setup=0，报告SHA1333ec4d1431bcf37096c79cd4c5d4d4089123832b5aa83df74bfc20e9d0ea69），不能因源作业COMPLETED宣称时序通过；独立精确STA和修复仍待完成。

- 2026-10-27 08:22 CST：094/92123独立完整原生物理接收FAILED：61项DRC（3项METAL10.2间距，58项天线：M4=2/M6=1/M7=8/M8=4/M9=42/M10=1），39:36、MaxRSS6480224K；其余14项门槛通过，仍不能冻结。完整lyrdb和61项摘要已留索引，新增接收器自动保存分类及逐项证据，零违例门槛不变。实际tech LEF无天线规则，macro.mod LEF的ANTENNA_X1扩散面积0.0；需按真实GDS/网/门面积诊断并在预制阶段修复，不能关闭天线或放宽300比值。098/92143实际回装因默认内部节点重编号未过身份检查，8秒；已按OpenROAD collapseInternalCapNum精确规则输出canonical编号和坐标映射，局部重评估及保总量换C/换R、错误单位、缺节点控制通过，新实际导入待部署。099/92146真实构建完成1:04、MaxRSS102292K，默认goldens/平面/原图、联合边际、线程及7非法输入控制通过；100双向联合节点FV/场解已提交92147/96CPU，科学结论待结果。101最终T6KC/92144在node20/16CPU实际构建；093 T6KA/92135完成23:12、MaxRSS21274744K，完整独立接收待运行。

- 2026-10-27 08:10 CST：100双向capture-node科学验证已部署，源码d8400bf、归档fde3931f66029b20cb8ed127b9ffc3b358e96afc9546bb0ec2159d68c7509327，116成员/819200字节，96CPU内两路48CPU；依赖099构建成功，尚无Slurm作业。新增101最终T6K网表行为接收代码，保留实际6_final.v及全部Liberty映射单元，独立队列scoreboard242事务，三初态（全1及两随机种子），原生LEC身份/状态边界先检查；仅解析器合成控制通过，尚未部署或运行。094官方DRC、093 T6KA及其他8个allocation继续。

- 2026-10-27 08:06 CST：新增双向capture-node科学接收链，branch/via合成正例及六负例通过，FV与场解收敛/互易/局部及保边际错误重连门槛已锁定。实际100尚未部署执行，须依赖099构建成功；098回装修复、099构建仍等8槽内空位。094原生DRC和其余8个allocation继续运行，不修改既有作业。

- 2026-10-27 07:58 CST：096/92133真实路由8节点测量已通过六门槛，55秒、MaxRSS12184K，总C13.281272325 fF；097/92134实际导入因Tcl SWIG显式uint32_t参数失败，原件保留。修复后的098已部署但尚无Slurm作业。099实际capture-node研究构建已部署亦未运行，等待本任务全局8槽；局部FV边界基函数变换在branch/via精确稀疏LU上保持原Maxwell矩阵至3.4e-16 fF，双向互易及边际一致，仅证明参考变换。094/92123独立DRC仍运行，093 T6KA/92135已运行；其他057/080/067持续，不按耗时取消。

- 2026-10-27 07:54 CST：096/92133真实路由8节点电荷测量完成55秒，六项锁定门槛全部通过；最后offset的总C约13.2813 fF，仍仅单个隔离网络起点电荷，不是完整分布式RC。097/92134实际SPEF导入失败，已定位安装版Tcl SWIG不接受显式uint32_t corner参数；源码改用官方同义默认corner=0无参接口，不放宽逐节点/逐边检查，重跑待部署。093边缘T6KA修复已提交92135；094内部T6KC独立官方DRC仍运行，095继续等待其全部通过。

2026-10-27 07:39 CST：094/92123已成功独立导出GDS并进入官方原生DRC，之前目录缺失问题实际修复；完整接收仍运行，源报告cap/setup/hold为0不等于独立验收。新增097逐节点电容/逐边电阻SPEF读回及保总量换值负例，合成TSV正例/六负例通过，实际OpenDB与测量回装尚未执行；源已部署，依赖096。096仍等8槽内空位，095必须等094完整通过。

2026-10-27 07:33 CST：093 T6KC/92115自然完成23:59，MaxRSS20889780K；封存原生源报告cap/setup/hold计数均0，精确最差cap slack +4.12317419052124 fF。报告SHA a579f5d04636112ebeb0881fc1c474c383525491c271b0c074673fa2a44b27cb，源回执28a8a4372500bc67739277113c061edd067da6993e1084bb28d0d1f3fbc66ced。094/92123已在node24/32CPU运行独立完整物理验收；尚未通过，不能据源报告冻结宏。原080八项/088一项失败保留；40档修复未更改Liberty限值、时钟、负载或预算。095宏视图依赖094全部通过，096真实路由测量仍等槽；当前本任务8个allocation。

2026-10-27 07:24 CST：091/92117两路图节点场解/FV科学对照完成11:07，四节点分支与五节点via全部锁定门槛通过，仍仅node-to-net起点电荷。释放node21后已启动080 C8A/92120，当前8个allocation继续运行。093 T6KC CAP_MARGIN=40进入详细布线，未取得最终电气结果。新增096真实路由8节点电荷测量代码，坐标源绑定及六种负例通过，已部署、全局8槽已满尚无Slurm任务；不把长度分摊或局部通过当作完整分布式RC。全部物理宏、最终功能/边界、共同底座与两产品仍未验收。

## 2026-10-27 07:13 CST：Issue121 图节点对照与电气残留

- 088 T6KC/92106完成22:45，原生max-cap从080的8降为1，最差−1.059973598 fF，setup/hold计数0，仍不能冻结。残留OAI211_X1 ZN限值25.558500290 fF、由slack推得负载26.618473887 fF；原因未证实。093采用有界追加CAP_MARGIN=40标准重布线，92115/node20/32CPU运行；94/95接收及视图链已部署未提交。预算、负载、时钟及Liberty限值不变，不做无限margin扫描。
- 081与089自然失败在独立do-gds缺少日志目录，不是完整物理通过；GDS接收器已补齐自身logs/reports/objects，失败原件保留。092依赖失败的089不会启动。40档配置正例和六种负例（含跨pipeline替换）通过，仅配置规则资格。
- 090/92114构建完成1:43：原作者goldens、平面控制、图节点线程/全局守恒及非法节点控制通过。091/92117在node21/96CPU以两路48CPU开始四/五节点科学对照，结果未出。独立FV导体面改动在本地直接稀疏LU检查保持原矩阵响应至2.3e−16 fF，全部146/156面落在对应导体表面，偏移负例拒绝；不代替服务器PyAMG/field收敛。仍是node-to-net，完整分布式RC未资格。
- 91903被Slurm原6h时限终止（TIMEOUT，6:00:27），未完整接收，已保存终态；此前延期申请遭拒记录保留。067完整双16线程UNLIMITED回归持续，不替换RAM或缩减测试。080 T6KA/92118已在node22/32CPU开始，C8A仍待空位；C8C及旧057继续。当前8个allocation均运行，选择现有manifest任务的--only过滤仍受统一全局预算/依赖/查重控制，其余任务保持待执行。
- [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) in_progress、[PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)草稿。登记pending，看板unverified/同步pending，管理员与独立审查人待指定；尚无合格宏/共同底座/两产品。

## 2026-10-27 06:56 CST：Issue121 三维图节点电荷资格链

- 新增090研究构建与091三维节点科学对照，均已部署、尚无Slurm作业，等全局8allocation内空位。起点通量按最近三维图节点分桶，默认上游/平面路径保留；独立FV读取实际导体面坐标，分别对照四节点T分支和五节点跨层via，沿用原074/087门槛并要求局部分配及保边际错误重连负例。源码补丁精确转换和Python/生成FV编译检查通过；C++构建及科学门槛尚待实际运行。
- 此阶段是node-to-net起点电荷，不是一般capture-node耦合或完整分布式RC；真实路由图绑定、窗口所有权、新旧层拼接与规模仍未完成。088 T6KC已完成详细布线并进入final；仍无最终独立验收。其他物理与完整门级继续，不按耗时取消，不修改其他成员任务。
- [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) in_progress、[PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)草稿。登记pending，看板unverified/同步pending；管理员和独立审查人待指定，未自行合并。

## 2026-10-27 06:42 CST：Issue121 分支/via场解与预制电容修复

- 080 T6KC/92089自然完成39:39，但最终原生报告仍有8个max-cap违例、最差−4.763801575 fF（setup/hold计数0），不能冻结。新增088从对应080封存CTS重跑标准route/final，只有CAP_MARGIN=20这一更严格修复目标；Liberty限值、时钟、负载、预算及检查不变。92106/node20/32CPU正在运行，其他三候选等依赖/空位；089独立接收已部署但尚无作业。配置正例与缺margin、额外限值、LEC关闭、错误读回、旧哈希五种负例已通过。
- 087/92104在node20一个96CPU allocation内两路48CPU完成分支与via节点对场解/FV对照，11:12、MaxRSS7264484K，两子回执及合并回执均通过。分支/via FV总C分别1.312932515/1.293154730 fF；网格外推、细化、远边界、offset/统计及保持边际的错误重连沿用原074门槛。仍不是一般分布式RC、原生/新增层拼接或完整Block资格。082/083/084均未提交且不再调度。
- 旧057及081独立历史接收继续，不按耗时取消。完整067双16线程映射模型已编译完成，原13命令/两背压继续运行；008同样继续，无完整通过结论。085/086已部署等待，宏视图须绑定对应完整物理接收通过；尚无合格宏、共同底座或两产品。资源上限8包含PENDING/未决提交，不改其他成员任务。
- [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) in_progress；[PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)草稿，待独立审查。登记PR5 pending，看板unverified/同步pending；管理员与审查人待指定。

## 2026-10-27 06:15 CST：Issue121 首个原生完成与节点内并行

- 057 T6KC/92048自然完成1:31:17；封存最终报告setup/hold计数0、max-cap计数13、最差cap slack −5.644092083 fF。因此不能当作合格Block。081/92090独立接收继续，保留其原封存源码；其他057/080 P&R与91903/067门级工作均继续。
- 大规模报告的旧Tcl非贪婪正则性能问题已本地复现；逐行状态机保持54837条驱动严格同序同数，六类报告负例拒绝。完整native连接与物理检查仍待实际接收。
- 084部署为一个96CPU allocation同时运行两个独立48CPU分支/via电容探针，仍使用074全部预锁门槛和独立回执。目前没有Slurm作业、等空位；原082/083同样没有作业，不再提交，避免重复。只在任务最多8allocation内启动，不修改其他成员任务。
- [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)持续in_progress、[PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)草稿。尚无合格宏/完整十二层提取、共同底座或两产品。登记pending、看板unverified/同步pending，管理员与审查人待指定。

## 2026-10-27 05:48 CST：Issue121 实际轨道与节点对验证

- 076两个C8导入因Tcl `%g` 将1000.095输出成1000.1而精确坐标检查拒绝；其余两项未提交，失败保留。改为9位小数后，077准备、078四组4389/386端口的实际M9/M10轨道、逐pin坐标及旧0.8偏移负例通过；079完整边界审计通过。没有放宽任何容差或预算。
- 080新原生P&R按全局最多8allocation提交，优先内部接口C8C/T6KC；其他候选等待空位。旧057四任务继续。91903/067完整门级与编译继续，无耗时取消。
- 074/92075在node19/48CPU/UNLIMITED完成7:48，局部2×2外部耦合与独立FV、网格/远边界/offset/统计门槛通过，保持全部行列边际与负符号的错误重连被拒。仅直线小例子，不是完整分布式RC资格。
- [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) in_progress、[PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122) 草稿；原计划SHA不改，完整物理接收/宏视图、十二层提取、新旧层拼接、共同底座/两产品仍未验收。登记pending，看板unverified/同步pending，管理员及审查人待指定。

## 2026-10-27 05:35 CST：Issue121 输入修正与资格探针

- 原生M10实际轨道偏移0.095/0.07、via9中心距≥1.68已核实；旧0.8偏移及1.6相邻轨道规划不能作为已验证接入。保持旧057继续，另开075准备通过/076导入在跑/077约束审计与078P&R待执行，同映射、外框及预算。
- 070局部电容独立FV与offset/网格/远边界/负例通过；074节点对探针48CPU进行中。073实际LEC正负例与完整边界接收控制通过，尚无完整候选验收。
- 91903原门级回归继续（时限延长被Slurm拒绝），067同网表双16线程编译中。本任务最多8allocation，重I/O两路；不改其他任务。
- [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) in_progress、[PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122) 草稿；十二层完整提取、宏模型、共同底座及两产品未验收。登记pending、看板unverified/同步pending；管理员/审查人待指定。


## 2026-10-27 04:59 CST：Issue121 增量

- 原生十层4候选P&R继续：C8布局、T6K详细布线；新完整映射并行回归92062/32CPU/UNLIMITED编译中，合计6节点。原91903时限延长被Slurm拒绝，保留独立调度记录。
- 真实STA/寄生覆盖正负例和物理断PG负例通过，完整最终物理接收器待候选完成；16μm窗口拒绝、64/128μm窗口诊断通过，分布式RC/新旧层拼接仍未资格。
- [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) 持续实施；[草稿PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122) 未合并。原计划不改。登记pending、看板unverified/同步pending；处理人待指定。下一步独立接收最终候选并继续十二层资格。


## 2026-10-27 Block v1 十二层实施

- 最新快照：2026-10-27 04:17 CST。run052精确映射结构兼容导出与负例通过；run055四个实际原生导入/固定M10坐标通过；run056完整STA写回的IO、驱动及每输出2fF审计通过。run057的92045–92048已在node14–node17各32CPU/UNLIMITED开始原生候选P&R，覆盖C8/T6K × A/C；91903映射门级在node13继续。run043/044八方向实例pin与原生/新增PG导体的独立GDS集合核对通过。十二层完整分布式RC仍未验收，不发布合格Block。详见[输入决策](../../docs/decisions/2026-10-27-block-v1-native-candidate-inputs.md)。以下时间标记保留早期事实，以本条为当前状态。
- 任务：[Issue #121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)，独立 `task/121-block-v1-twelve-layer`，P0/P1及P2功能资格进行中，[草稿PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)；不接管原#116。
- 已完成：授权计划封存；33份原科学源码与发布Git blob均校验；服务器探针91865失败/PATH原因保留，91866成功核实实际工具及原生十层平台。
- 实际通过：T6K随机242事务；完整四profile13命令及44条恢复命令、两种等待模式的独立整数接收；91901完整库存642253单元／1538342.904 μm²（真实S16K＋T6K）；91905内部M10接点经新层连通，原生27条SAMENET与新层EOL数据库核实；91899官方固定场求解器2D/3D参考与线程/介质缩放检查。
- 新增通过：91907数学/协议8种内存故障注入均拒绝且原始文件未变；91909同源完整叶块网表/端口/SDC；91910原生GDS层占用审计；91914独立GDS接入几何及5类负例、M10 mask不变；91916新版官方场求解闭包的参考算例、线程/介质缩放检查。见run009–012索引。
- 进行中：91903精确完整映射网表构建（两份存储不替换）；十二层校准场景修正，必须将cntxM导体与信号目标放在同一场景。91915只通过几何解码，旧分组不具备校准资格；[决策](../../docs/decisions/2026-10-27-block-v1-calibration-scenes.md)记录原因。全层独立DRC/寄生边界及完整物理尚未验收。
- 下一步：新不可变run重建场景和先导场解，再做完整模型拟合/留出验证；资格满足后正式硬化。标准单元S16K内置C8、T6K独立叶块的[物理预算](../../docs/decisions/2026-10-27-block-v1-physical-inputs.md)已选定，不沿用旧逻辑面积预算。
- 02:27 CST增量：修正分组后的先导和六分片接收通过；重场解实际使用node14–node19六台96核节点。3840行场解与3344个DC图形完成候选拟合及约6e-8逐网单位/计数读回。实际提取尚失败：旧格式读取崩溃，现代格式进入耦合阶段后仍崩溃；发现1542个未校准空表，下一批覆盖完整十二层上下文并禁止空表。旧候选未验收，完整门级91903仍在构建，正式Block P&R尚未开始。
- 03:27 CST增量：完整上下文候选已实际提取，跨层耦合仍失败，2.0/2.2/2.3亦未解决。直接场解另经node14–node19六台机器、六种几何、三网格和远边界独立有限体积校验全部通过；六例真实SPEF/OpenDB/GDS与单位/耦合负例通过。详见[决策](../../docs/decisions/2026-10-27-block-v1-direct-field-extraction.md)。完整分布式提取尚未合格，正式P&R尚未开始；91903已编译、混合回归运行中。
- 证据：[work121](../../work/YUZE-LU/121/README.md)、[运行入口](../../project/experiments/block_v1/README.md)。登记pending；看板unverified/同步pending，管理员待指定。

## 2026-10-26 模型实验分析报告

- 任务：[Issue #114](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/114)，负责人及实际账号 YUZE-LU。
- 成果：[阶段性分析报告](../../docs/MODEL_EXPERIMENT_ANALYSIS.md)，补充 README 与研究资料导读入口；来源与检查见 [work114](../../work/YUZE-LU/114/README.md)。
- 已完成：读取九份固定版本报告及十个来源 PR 的状态，梳理八个模型的目的、范围、结果、失败和能力/接口约束；读取后续 #102/#106/#109/#110 的范围，避免将旧批次限制误写为当前无 RTL。
- 集成：用户明确要求合入 main；本次通过独立文档 PR 交付，最终 PR/commit/CI 以 Issue #114 的读回回执为准。不合并其他实验 PR，不冒充独立审查批准。
- 验证：文档检查与管理结构的实际结果见 validation.json；未重跑模型、原始数值接收、RTL 或物理。
- 接入：登记 management-hub PR5 仍 pending；无 board.json，实际 Projects 查询缺 read:project，看板 unverified、同步 pending，管理员待指定。
- 下一步：完成当前文档检查、PR/CI 及按本次授权入 main 的读回；原实验审查和后续实现另按原任务推进。

## 历史阶段：Issue #7（2026-10-21）

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- Issue：[候选 Block 边界及分层布线流程](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU，当前 `in_review`；审查人和优先级待指定。
- 已完成：读取两个项目的接口／RTL／报告和已有 ACT—MXU 实验；形成 [候选划分及对照矩阵](../../docs/experiments/openTPU-llaccel-block-plan.md)；核实用户授权的集群工程与工具可访问；在独立分支 `task/7-block-routing` 增加正式实验运行器，原参考包和原工作区改动保留。
- 实验：完整16-lane VECTOR的screening 89442通过；早期89443人工时限超时及89447恢复预检查失败保留。89448从checkpoint进入stage4、不重综合，仍在默认LEC、未得CTS完成产物，继续 `UNLIMITED`。89449因旧默认PDN已知不兼容，在确认PENDING后取消，非按求解耗时终止48。终态以[试验记录](../../docs/experiments/issue-7-vector-pilot.md)和[轻量索引](../../project/experiments/block_hierarchy/results/issue-7.json)为准。
- 运行约束：用户明确要求不设时限；后续作业取消人工有限时长，实读 c64/c96 `MaxTime=UNLIMITED`，每次提交后核验实际 `TimeLimit`。早期超时与恢复预检查失败保留，不通过删除历史制造成功。
- 新增验证：独立RTL回归89455通过，VECTOR 1203例／数学12000组／舍入16384组；测试副本唯一 `1u << 31` 兼容修正有diff/hash，原RTL与参考不改。89453及后续顶层是另开的 `LEC_CHECK=0` 物理路线，89448默认检查路线保持运行，不混用二者证明。
- 实际物理结果：89453完整Block和89472单宏顶层均完成最终布线，DRT错误0；89475最终只读审计通过，双网连通、唯一固定宏／2246位接口与逐位映射、M7–M9接入几何复算闭合。Block setup WS −4.16659 ns／287违例、最大电容59违例；父级setup WS −0.0429892 ns／3违例，质量仍未通过。父层新增2245个IO buffer，single-sink实际跳过CTS，无多宏时钟树验证。历史PG／hook失败均保留。
- 验证：`python scripts/check_project.py`、Python 脚本语法编译、远程 Bash 语法检查和 `git diff --check` 通过；镜像阶段门级 LEC 已调用、尚未得结论。完整 core 回归、原 RTL 到物理网表的完整形式比较、多计算图、受限定制和系统签核未执行。
- 下一步：审查本轮工程实现和失败证据，保留内部／父级时序、电容、异步复位抽象和缺少宏功耗模型的限制；再准备同资源F0/H1对照、多Block和H2冻结资源规则。89448继续无限时求解，其后续匹配模型必须来自其自身最终实现，不套用89453模型。
- PR：[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)供审查；89472／89475实际运行代码快照 `357dd98a7a07f370a1cc2c67b066c7ecccf3bf9a`，75启动时仅文档／结果dirty并如实记录。最终采集器精简及成果记录由PR当前HEAD回执绑定；每个attempt的SHA-256独立保存，未合并或验收前不标 `done`。
- 接入：管理中心 [登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 本轮读回仍 `OPEN`，登记 `pending`；Projects 缺 `read:project`，无 `config/board.json`，看板 `unverified`、同步 `pending`，由具备权限的管理员处理（待指定），见[持久交接](../../docs/handoffs/2026-10-21-issue-7-projects.md)。




## 2026-10-22 ACT/MXU 同资源物理对照

- 更新时间：2026-10-23 04:37 CST，中国标准时间UTC+08:00；负责人／实际GitHub账号YUZE-LU。
- [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)，分支`task/15-opentpu-compare`，[PR #17](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17)，依赖PR10基线2b76f69；独立工作树，未修改PR8／PR10工作树、VECTOR或89448。
- 已完成：三种块内实现与拆分两宏／合并一宏父层实际布局布线。保持169109初始映射单元、37023DFF、12个SRAM及相同计算／状态逻辑；统一1662bit外部引脚、die、2.5ns时钟及0.5ns IO预算，全部物理支持成本计入。拆分89829／34:01自然COMPLETED0，五个物理来源和六类证明共十一份记录全部通过compare；功能89831、覆盖89832、完整ODB89833通过。旧20的act_data[145] slew违例经单一驱动X4→X8并重新DRT／提取消除，没有放宽门槛。
- 实测：拆分／合并总叶面积484240.4／482252.4µm²，总信号线6647739／6204600µm，通孔1322289／1284106，完整setup WNS +0.102306／+0.065642ns、hold +0.036146／+0.013027ns。拆分块内线长−249953µm，被父层+693092µm抵消；总线长+7.142%，不能将父层IO／时钟全归为685bit边界成本。
- 成果：[中文HTML和三类图表](../../docs/experiments/issue-15-opentpu-results.html)，[过程及失败证据](../../docs/experiments/issue-15-opentpu-comparison.md)。生成代码8a646d8，冻结输入SHA f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d；report-manifest绑定9个产物。实际查看三PNG、浏览器核验页面／表格／三图／路径和完整ODB展开，临时页面服务已关闭。delivery-validation记录实际检查和两个成本证明负例，均拒绝且未改变合格输出。
- 补充已完成：全量清线重布21／89826自然COMPLETED0（1:02:26），匹配功能89827／RC89828／五ODB成本89835全通过；另存完整十一来源对照，快照72b9829d0df7ac7d30c5b7a6f8e602f11e317c2070cbacab4f55e466299cce0f。与主拆分叶面积相同，总线长多42µm、通孔少2、setup多0.000008ns；原主报告和9产物SHA不变，不能当作显著改善。两套合计15份唯一封存来源全部自然完成、UNLIMITED。Issue in_review、PR17待独立审查。
- 限制：H1允许新增有源缓冲和全父层路由，M10以下父层线长占比约99.39%／99.26%，不代表H2少量定制层冻结底座；单small／typical／固定布局与引脚，synthetic SRAM无GDS、上游RTL通用等价和制造签核未完成。
- 下一步：PR独立审查／合并及最终验收由人处理，审查人待指定。不自合并或标done；审查人／优先级待指定。H2预算及限定制层是后续独立实验。
- 接入：登记管理中心PR5本次核验仍OPEN未合并、pending；本仓库无board.json，连接器无Projects条目工具、CLI实际GraphQL查询返回INSUFFICIENT_SCOPES缺read:project，看板unverified、同步pending，管理员待指定。

## 历史记录：2026-10-21 资料与规则交付


- 更新时间：2026-10-21（中国标准时间，UTC+08:00）
- 当前任务：[Issue #3：同步两份布线报告并补入 llaccel 引擎分析](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3)。负责人 YUZE-LU，优先级待指定。
- 已完成：同步最新总报告、线长报告及其引用资源；总报告增加 llaccel 三个引擎的中文分析与 9 张图。保持图片直接展示、长表可展开；不创建备份或多余首页。更新来源边界和包说明。
- 验证：管理结构检查、报告依赖/锚点检查、包内清单哈希、正文/表格保留和差异检查；具体结果见本任务 PR 回执与 `work/YUZE-LU/3/validation.json`。没有重跑物理实现或 STA。
- 交付：[PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4)，分支 `task/3-update-routing-reports`，报告成果 commit `b041d53`；2026-10-21 按用户明确要求已合并到 main，合并提交 `1d80491`。
- 下一步：继续审查[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)。登记仍为 pending。
- 阻塞/接入缺项：报告上传可独立完成；本仓库没有看板配置，当前凭据缺少 `read:project`，无法核验或同步 Projects。由有相应权限的管理员处理，处理人待指定；详见[交接](../../docs/handoffs/2026-10-20-issue-3-report-board.md)。不自行扩大凭据权限。
- 历史：Issue #1 的初期资料由 PR #2 导入，后续参考资料提交 `695587d`、`5c86109` 已进入 main。`ref-project/` 仍不属于 Agent 主动或例行维护范围。

## 2026-10-21 补充交付

- 按用户要求补入 `ref-project/llm-routing/模块与接口报告.html`，保留原文，并复制其引用资源；README、研究资料导读及阅读说明补充入口。
- 本次仅检查新报告的本地引用是否存在及管理结构、文档差异；不执行哈希检查，不重算参考数据，不修改原有清单。原清单不覆盖此次新增文件。
- 沿用 Issue #3、任务分支及 PR #4 上传；2026-10-21 已按用户要求合并到 main。看板权限缺项沿用上述交接。

## 2026-10-21 远程服务器规则

- [Issue #9](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/9)：记录服务器节点、`/public/home/yuzelu` 下的目录权限和 sbatch 任务命名要求，README、AGENTS.md 提供规则入口。
- 任务名采用“本人姓名缩写-任务缩写”，如 `hpy-block`；脚本和提交时覆盖的任务名均应遵守，便于在 squeue 的 NAME 中辨认。
- 验证：管理结构检查及所改文档的差异检查通过；未登录或修改远程服务器。通过 PR #4 上传，2026-10-21 已按用户要求合并到 main；看板同步仍待具备权限的管理员处理。

## 2026-10-21 main 集成

- 按用户“最新状态都提交到 main”的明确要求，将报告、远程规则及此前未提交的工艺互连资料补充一并纳入 PR #4 并合并。合并提交 `1d804912927602900aa074339db33156a805c582`；本地已同步到 main。
- 管理结构及文档差异检查通过；未重算参考数据。其他成员的独立 PR 未合并。登记、看板的既有待办继续保留，不宣称已完成。

## 历史记录：2026-10-19

- 更新时间：2026-10-19（中国标准时间，UTC+08:00）
- 当前任务：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)
- 已完成：初期研究资料已进入 `main`；PR #2 已合并。本次按用户要求直接在 `main` 提交并推送更新后的研究资料导读与用户提供的 `ref-project/` 改动；成果提交为 `695587d`、`5c86109`。
- 下一步：完成[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 的审查；由具备 Projects 权限的管理员核验或配置项目看板。`ref-project/` 不纳入 Agent 的主动或例行维护，用户更新后可按要求提交；无需逐项审查或做哈希检查。
- 阻塞：物理实现原始代码、数据库与工具环境未包含在当前资料包；共享存储位置和实际可访问性待核实。
- 本次验证：`python scripts/check_project.py` 通过；导读的 6 个本地相对链接存在；变更文档的 `git diff --check` 通过。未检查参考包内部改动或哈希，未执行业务构建／仿真。本地未配置 `config/board.json`，看板仍待管理员处理。

## 2026-10-23 布局与接口报告本地归档

- 按用户要求，沿用 Issue #7 并发工作树 `issue-7-parallel-blocks` / 分支 `task/7-parallel-blocks`，将两份报告集中到 `ref-project/llm-routing/docs/`，并修正相对资源 URL 与 README、资料导读、阅读说明中的入口。详见[报告目录说明](../../ref-project/llm-routing/docs/README.md)。
- 已核验移动前 56 个不同本地资源 URL 均存在；移动只调整 URL，报告正文和标签结构保持不变。新 Block 报告从外部生成产物原样复制，保留源文件。项目管理结构检查通过；未重跑 EDA。
- 交付状态：仅本地文件整理，尚未 commit / 推送，现有 PR #10 尚不包含此修改；Issue 状态、项目里程碑及看板未变。登记/看板缺项沿用原任务交接。下一步可按用户后续提交要求并入现有 PR，不能把本地归档视为已合入 main。

## 2026-10-23 按用户授权整合实验与 HTML

- 用户明确授权完成 PR #8、#10、#17 及两份 HTML 的提交与合并；H2（Issue #31）继续独立运行。HTML 的来源和范围不变，先前“仅本地”的记录为归档时快照。
- 本次技术复核：H1 主/补充对照从现有封存记录重算，全部成本与质量字段一致；9 个报告产物 SHA 未改变。缺少成本审计、错源审计两负例均拒绝；并发电气门槛、Tcl 修复与配置覆盖回归通过。不是新跑 EDA 或上游 RTL 通用等价证明。
- 合并权限来自本次用户明确指令；不冒充独立 GitHub APPROVED 审查，不绕过保护规则。登记 PR5 仍 pending；看板实读缺 read:project，unverified / 同步 pending。

## 2026-10-23 用户授权整合

用户明确授权将主线PR #8、并发PR #10及H1 PR #17合入main，并将两份参考HTML归档到ref-project/llm-routing/docs/。以上旧记录中的待授权／不自合并描述是当时状态，本次按用户的新授权执行，不伪造独立审查批准。H2工作树及运行任务保持独立。本次验证与限制见[整合回执](../../docs/handoffs/2026-10-23-h1-html-integration.md)。

网络恢复续办：PR #8 已合并为 a30d598，PR #10 已按匹配 head 成功合并为 a77d288；完整 H1 整合树由 PR #17 交付，最新 CI 和合并状态以在线记录为准。本地 8 项检查、58 份 Python 语法、两份 HTML 资源／锚点及 9 产物不变检查通过。Issue #7 的 VECTOR 质量缺口保留；H1 交付与 H2／Issue #31 分开，项目登记及看板待办不变。
