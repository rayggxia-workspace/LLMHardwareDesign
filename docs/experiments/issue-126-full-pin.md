# 全功能分块、全块二维 pin 与实际接入（Issue126）

2026-10-29T15:08:17.562325+08:00 R41接续实际终态：93240已完成LL bit_1025最新实际源匹配物理/RC视图，13507信号pin及PG/层/尺寸/当前XY精确一致，clean ODB SHA 5e7e3b7c6b7a5bccb7f4c71aacccecf65b08c5e3be3c063a4d65ac162ebe781b，原SPEF逐字重放、独立模型重读0；setup/hold仍−3.909029/−0.587515ns、8876文字VIOLATED，minimum_period/父层/完整规则/功能未闭合。不继承旧三点源模型，不把导出成功当物理资格。11个原生小文件逐SHA追加data/gate_terminal_updates/llsys-parent-tip-views-r01，原R38不覆盖。

已实际提交93243：driver936822309dcdcd8e928549898abeed850b70b14f、独立common_integration/boundary-r01/Aopt。对全部24767个真实Aopt信号pin逐项检查确在边界，使用同六块资源/布局外框/256×32μm真实FIXED拓扑预算，实际执行placement/PDN/CuGR/DRT及独立规则/连通检查。最新只为RUNNING，尚无终态。源epoch与两侧既有ECO差异单列，非最终纯XY收益对照；原C及活动驱动不变。93239最新MXU实际M6接点父层重接仍RUNNING，未宣布NoAP解决。92690/92691、92855、93197/93218及93217两770-edge guard15均保留，不按耗时取消。共同合格冻结/两完整功能/公平系统对照仍未完成，整体in_progress/Draft。

[93243真实提交与公平性边界](issue-126-full-pin/data/common_boundary_r01_submission.json)。


2026-10-29T14:33:20.815069+08:00 实际接入增量（R40）：MXU93219已完成真正dbWire/BTerm ECO，只有act_data[12] M6 XY移到原via5帽、4条旧末端M6 WIRE删除；全部2172 pin及PG/单元/网络/外框、所有via及其余191437多端网矩形表示保持，全网所检连通/双PG/RCX/原STA执行。初次fresh驱动误用LL的M2–M8范围，被原有M9 guide以DRT-0155拒绝，未产生DRC结果；失败不改写。93223按实际原源fresh.tcl的M2–M10信号/M4–M10时钟范围、精确相同ODB/SPEF独立fresh0，未重跑接线/提取或放宽原范围。setup/hold0.246690/0.038538ns、0文字VIOLATED，非完整规则资格。新ODB848f80449c9dd83a6138738376297d4ec66ca199436da20309c07d1320ead6fd、SPEFf6596ef24bddd6c397721a51782fea058d47369102e0272bac2419e528cc33eb。

93228新MXU默认/详细OBS/真实网表/RC时序模型已完成并fresh重读0，2172位和PG/当前XY精确匹配、SPEF余量逐字重放，minimum_period仍缺项。新M6详细OBS与真实via帽/pin仍完全重合0.0196μm²，没有剪去占用，父层影响未知；不能仅凭子块native0称父层可达。原M6源与其父层native1/CLOCK失败保留为历史，新源主矩阵更新且父层NOT_VALIDATED/完整GDS-SRAM-规则缺项明确。36幅PNG/SVG中新增真实24→20行目标网前后图和同倍率局部，已打开目视核验。

LL93205亦终态：native/fresh均0、fresh0，完整13507位/PG/单元/外框保持；只bit_1025 XY及3末端WIRE改变，所有via/其余725252多端网矩形表示保持，保留此前三点及13184-move内部C。725253网所检几何连通、双PG/RCX/STA完成，但−3.909029/−0.587515ns及8876文字VIOLATED仍整体FAILED。新变体独立原文/13507逐pin CSV追加，匹配新视图及真实父层尚未完成，不继承前三点源模型。父层驱动已准备从原闭合父层保留PG/2172端点及M10目标，仅重接新MXU M6接口，不剪OBS；时钟模型绑定后保存、独立read_db核对全部2245宏pin，任何额外材料变化如实报告。

当前已发布head3c28051e990c1a05dd1b4366001e3fc137bed392两在线CI40824668698/40824668745 success、矩阵及原35PNG/SVG blob读回一致；本增量新head/36图/CI以推送后实际读回为准。原93197/93218、93217两模式guard15、92690/92691和92855均保留，不能按耗时取消；新LL视图和新MXU父层后续作业只在独立驱动提交。整体active/in_progress/Draft，六块完整资格/共同合格冻结/两完整功能/公平系统对照未完成。


2026-10-29T13:38:51.363236+08:00 增量终态（接续已发布2059cd4，非重做候选）：upper_guard_api/r01原生返回1，getLayerRules输出参数调用错误原文保留；r02原生0且770网赋值成功，但实际M1–M10 NDR spacing为0，未用于全布线；r03/93211显式12层1.5μm hard spacing、M11/M12线宽0.8μm，实际规则读回与全部770网赋值通过，仍仅API探针。三份独立终态各4个原生文件按SHA保存data/gate_terminal_updates/upper-guard-api-r01/r02/r03，原R38及其运行中记录不覆盖。后续guard15真实两模式770边路由将只用M11/M12，保持原hook、256真实FIXED及原下层材料，并分别做NDR/原技术规则fresh，任何一项失败都不通过；额外保守约束成本不混为纯XY收益。

代码审查发现MXU r03先保存ODB后绑定库，内存合同不能证明磁盘USE正确；新驱动改为绑定后保存，并独立read_db再导出全部2245条宏pin合同才允许宣称持久恢复。当前93197仍在跑，不覆盖/取消。另已准备MXU act_data[12]原M6实际via-tip原生修复：真实24行网/hold19330-A，移到原via5 M6帽、只删除4条原末端M6 WIRE，保留其余191437多端网、全部2172 pin、via/PG/单元/原约束并重新提取验证；尚未启动，不称已修复。原生Tcl-list的bus括号解析已用真实2172位before/after数据和PG合同核验。93205的LL bit_1025真实修复仍运行；原92690/92691及92855保留，完整共同冻结/两完整功能/公平系统对照未完成。


2026-10-29T13:17:14.263730+08:00 R38后追加原生终态93190（不覆盖快照）：LL新native0三点源的默认/详细OBS视图、DEF/真实网表/RC时序模型已导出；原生export与fresh model read均0，全部13507信号及原PG/层/尺寸/当前XY匹配、clean ODB SHA d97f1ccd9749f5492277fca820fda02702926ac6694ba96539b36af2cd6d3402与实际源相同。原SPEF余量逐字重放−3.909029/−0.587515，仍失败；minimum_period覆盖仍缺失，父层/完整规则/系统资格未完成。11份小型原生终态文件逐SHA后无损归档data/gate_terminal_updates/llsys-tip-views-r01，capture.json记录原文SHA与捕获时间，不重复采集全部历史试验；大物理视图及模型仍有原始SHA索引。主矩阵模型状态相应升级，原R38运行中记录不改写。


2026-10-29T13:12:49.893042+08:00 R38：全部24767真实父层轨道审计/bit_1025完整535行原网及374条局部真实金属PG/OBS已收齐。LL原R02有13184 preferred中心未对齐，其余五块0；仅几何风险不等于NoAP判定。bit_1025原via5_0落脚已取得且原网对齐，可尝试删除3旧末端WIRE后保留原M5/0.14μm尺寸重新接入；只是待验证方案。新增三处原native4→0修复真实前后图，M4–M7/via4–via6及实际pin矩形，35组PNG/SVG，周边异网未画不代表空闲。原STA −3.909029/−0.587515仍失败。

时钟原生小探针93193：read_LEF后MTerm SIGNAL，read_Liberty后CLOCK，link与原create_clock后保持；旧/新源LEF都SIGNAL而真实时序模型均clock:true，说明绑定阶段是必要环节。整父层93194先载库再swapMaster实际Signal11，未执行fresh，原始失败保留；93197已改为先swap再载同一别名真实时序库后检查，R38快照时仍运行，不以小探针当实际修复成功。LL当前native0源匹配视图93190仍运行，未把导出作业提交当完成。

R38/93201，driver3c97d7c273638eb390d498b19ba803b95faa0eb2，UTC05:10:15.651555，tar SHA256 bd6b4a98a769ca1be00b86237033f2c226987178de9c354701c51c7c207728f8，25483795字节，1412原文逐SHA核验。原R35–R37/原ABC/所有失败保留。完整目标仍active/in_progress/Draft，合格共同冻结/两完整功能/公平系统对照未完成。下一步先收齐93190/93197，运行源绑定bit_1025真实接线ECO（保留新失败并做全块native/连通/PG/RC/STA），继续适配异网短路、子块电气/时序及原92690/92691/92855。


2026-10-29（gate-r37）两模式全770原支路实际CuGR/DRT及原生opcode合成都已终态：各514物理网/1540端点的本网矩形连通、全部770原边成员、固定256条M10/FIXED、原hook材料包含及WIRE/VIA合成精确保留通过。按本网删去各桥实际矩形，256桥均导致该网源/汇断开；这个测试不包含跨网路径，不能当全局隔离/功能证明。独立fresh仍失败：openTPU127项，llaccel14项（8 Metal Spacing、6 Short）。实际源material保留只证明合成没改源路由，不能覆盖源路由本身的短路，不得称两完整功能或合格冻结。

93166已从llaccel闭合770支路ODB与guide做真实修复，不重做GRT；按14项原DRC选30支路，实际WIRE/VIA表示改变53网，未误称只改30网。原生详细接线/精确原生合成/fresh均0、全部514网/1540端点本网连通及256桥/FIXED/原层/原hook保持，但fresh仍10项（2 Short、8 Metal Spacing），整体FAILED。原14与当前10分别保留，未降低规则或删检查。实际规则/所有端点XY/允许层及原下层输入保持，模型RC/STA/完整LVS未执行，不能把本网连通当真实完整功能。后续须继续修复跨网短路/间距，同时处理实际共同下层NoAP bit_1025与新叶视图/时序电气。

MXU93074当前M6真实视图的全部2172位父接入重验已终态：native route/export与fresh进程0，但fresh仍1项，不能继续标运行中或提升父层资格；当前源模型/库和完整接口绑定保留，真实M6 OBS/接入问题仍需实际修复。完整六块已各有native0子块源与完整规则/RC/STA/父层/功能资格分开。旧源码/原失败/历史视图不覆盖，任务active/in_progress/Draft。

R37/93167/driver472def56122e298a9039bbcc8e26a68ffbdfbc17，UTC04:19:24.542309，tar SHA256 0c3f6afe9f281c3e477016c85fcc1d2bbeeb1d04303e58166d2b15dc9cb958c9。此快照额外保存适配器小型完整实际branch/whole几何（原native gzip再无损封装，源SHA可核对），供后续真实路径绘图/规则定位；不上传大型叶ODB/GDS/SPEF。源码、中文HTML、原34图/PNG/SVG、完整13507新实际pin CSV及R35/R36/R37证据随本阶段统一发布，当前head/在线CI/图片blob以推送后读回为准。


2026-10-29（gate-r35/r36阶段）LL SYSTEM真实via-tip/r02已闭合：93127/native编辑与fresh均0，native4→0，725253多端网/2325528端点/28517815形状所检连通、双PG/RCX/原约束STA、完整13507-pin层/尺寸/方向/网络/PG合同通过。仅三pin XY移动到原网真实via落脚，恰好八个末端WIRE矩形删除；所有via多重集与其余725250网WIRE/VIA表示保持，0新增单元/换型，cells/连接/位置/PG/外框不变。setup/hold仍−3.909029/−0.587515ns、8876文字VIOLATED，整体FAILED。主矩阵升级此native0源并保留旧PG-only native4；新匹配LEF/OBS/RC模型、真实父层及完整GDS/规则尚未完成，旧父层结果不得继承。完整逐pin当前对应CSV已单独提取为data/llsys_actual_via_tips_r02_all_13507_pins.csv。

VECTOR93112亦已终态：native合法化/路线均0、fresh native0、375723网/1073317端点/10349786形状所检连通与双PG/RCX/STA执行，但−4.148930/0.025481ns、82文字VIOLATED仍失败。93128基于两份闭合实际CSV复核：49新增非filler、365原非filler换型、325非filler移动；459这个总master变化数另含94个重复filler名，不能全称逻辑换型。排除BLOCK/filler面积增量354.046μm²，旧917.700μm²另继承。该变体未改善旧r01提取余量，保留旧可实现内部C作为当前主源，不撤回周边；均非纯XY或外框面积收益。

上层93120两模式均GRT-0116失败并先恢复全部原FIXED；93129 CuGR两模式取得完整514网guide后进入DRT，但openTPU仍256共享网未接通（258/514连通）、fresh6；guide齐全仍不代表物理接通。93148原生dbWire.append已真实验证WIRE/VIA多重集及FIXED/ROUTED属性保持，r01包装器缺Singularity PATH的启动失败保留。93150全770支路CuGR/DRT后精确原生合成514网和原256条FIXED M10已实际运行，包含全部支路材料/原hook/OBS/固定材料/fresh及256桥删除敏感性检查；仍只是适配器、不是完整功能/有效STA或冻结。

共同下层93132已越过CuGR全局阶段，但DRT-0302拒绝施工BTerm的双BPin容器；93149按同一闭合global.odb/guide接续，不重做GRT，只将256施工端口容器合一、两原矩形保持。该工具限制越过后实际DRT-0073在u_llaccel_aux/bit_1025无AP失败。原包装器pin行字节序断言也失败；后验10657行Counter完全相同，PG/实例字节相同，故不是物理坐标变化，原回执及真正NoAP均保留。只读观察：该M5 pin原aliasLEF矩形(353.85,1064.49)-(353.99,1064.63)μm，父层M5/M6轨道DBU原点190/140、pitch560，宏原点均已对齐；这只是接入疑点，尚未作为可行位置结论。下一步应版本化真实bit_1025端点/金属/PG/via诊断及合法接入修复，不擅自改布局或丢弃检查。

R35/93137/driver bae87dfdc7e9694161eb2c94f814f1a25816d69c，UTC02:40:53.200112，tar SHA256 bd80261e3a266364c98d9fba41c08e574536b78176b0a3c076c3fe5aa8046852。R36/93155/driver29537721bb607c8203a811f2b8fbafb7ec3c62de，UTC03:13:31.017168，tar SHA256 4c08ff89e0d27c60eedaf5b5e9aafed8f4558acedc13837dd501353d5de5f7f6。R35独立1252原文先验证SHA后归档，R36优先用于最新矩阵；原ABC、24767信号pin/74301行、34幅PNG/SVG、历史失败保留。

当前六块各已有其版本的native0内部源，不代表六块完整规则、父层可达性或RC/STA电气全部通过。完整目标active/in_progress/Draft；共同合格冻结、两完整功能、公平系统对照未完成。原92690/92691、92855、93074等活动不覆盖或按耗时取消。最新发布be02ca0两CI40803922706/40803922808成功，当前阶段源码/图/数据待本次验证推送后读回；登记pending、看板unverified同步pending、管理员/审查人待指定。


2026-10-29 09:57 CST（gate-r34接续R33）93117已实际FAILED，不能继续标运行中或布通：openTPU原生命令0、fresh native 8项、514物理网只有258网/1540端点整体中的部分连通，256个共享固定网各分成3个端点分量。闭合实际guide只有258网、全部256共享网均没有guide；按原770边逐一核验是258边连通、512边断开。全部256原FIXED M10属性/矩形并集覆盖、原hook/OBS/外框保持，证明保留固定金属本身不足以证明实际功能连接。llaccel在GRT-0116失败，无DRT/fresh/全网连通/RC/STA；整个93117 FAILED 1:0。所报403412.44μm的M11/M12等仅这次不完整试验的路由，不能拿来计算完整系统收益。

已实际提交93120/driver f63ad792c145db656a1b50cbb5e8f586953713af在新upper_preconnected/r02接续：保持同一514物理网/770原边/1540 hook/256固定导体及原规则，只在helper的guide搜索内存副本临时移除256条FIXED片段，GRT返回后无论成功/失败均精确恢复原M10 FIXED定义并保存实际ODB/DEF；若GRT成功，必须全部514网都有native guide才允许DRT。原底座文件、PG/OBS、pin层及最终材料不改，原r01失败保留。当前两模式均已实际执行guide-only detach并进入GRT，尚非新的物理通过，后续真实连接/材料/FIXED/DRC和RC/STA门槛不降低。

93122/driver e7ae24d37ac26ce460a509d5a8026e64b19b5437收集不可覆盖gate-r34，UTC01:54:49.531042；tar SHA256 bf52787d56a77fc1438016b96473485892469bb0325ecb62459d9a073036c10b。R33与R34来源/终态分开保留；全部514网/770边guide与端点分量CSV加入报告，34图及既有候选原始数据保持。完整六块资格、共同冻结、两完整功能及公平系统对照未完成，任务active/in_progress/Draft。登记pending、看板unverified同步pending、审查待指定。


2026-10-29 09:43 CST（gate-r33）VECTOR93112已从93106同一严格关系通过的实际五输入恢复源继续P&R，不重复启发式setup/hold修复。原生独立合法化、placement检查及411243个原filler恢复已执行，保存回执legalization=0；全局/详细布线已实际运行，尚无fresh DRC/全块连通/RC/STA终态，主矩阵仍保留旧r01负setup源。新增49 BUF/365换型及+354.046μm²等此前成本独立记录，不当纯XY或外框面积收益。

新增93117是两模式全量预连上下文试验：复用同一R02未合格底座与全部770边/1540原hook/256实际FIXED M10导体，原本已被固定导体连接的两支路合为同一物理网交给原生路由。两个模式的实际预路由DEF均已生成；核对514个物理网（256四端+258两端）、1540原辅助端点、全部770原边成员及256条FIXED metal10属性。导体及hook不改、未删边/减预算/改协议，未断言旧分解就是拥塞根因。GRT已启动，未取得完整布通或两功能物理资格；helper中的被动接点输入标签不代表额外真实驱动，不能用于完整STA。最终还须全部实际连通/材料精确并集/FIXED/OBS/fresh DRC等验证。

93090两模式网格相位试验均已GRT-0116失败（openTPU UTC01:02:06.953141、LL UTC00:49:40.194098），DRT/fresh/全边连通/RC/STA未执行；物理轨道/规则/PG/OBS/hook保持，原50/200次及DRT失败不删。没有重提相同相位或搜索预算试验。MXU93074 fresh native继续运行且CPU活动；LL92690/92691及下层92855保持不改。

93118复用不可覆盖driver59abaccee318945168cb375fce48bb988e29bb0a收集gate-r33，UTC01:42:24.431369；tar SHA256 ac7b2b2b80fc4adee70737234e6b1141ad33c9879fafa6c7775967db7fac9756。新上层物理驱动ca1236fb869a38ab017e4dc80dc1c09664d59f85；VECTOR驱动e68df58baf804b19b9334a31a92a3dcd02f17d6c。34幅已发布PNG/SVG保留，不重做原ABC。全部目标仍active/in_progress/Draft：六块完整物理资格、共同冻结、两完整功能、公平完整系统对照均未完成；登记pending、看板unverified/同步pending、管理员和审查人待指定。


R31/R32发布前复核：管理结构、24767原pin/74301 ABC、27259文件SHA/164链接/18747 raw业务验证、Python编译、未修改的5项buffer合同测试、diff检查通过；Edge加载34幅图、常量位查询通过。最新矩阵/扩展表、SYS实际前后PNG与HTML截图已打开目视核验，图例与说明无重叠。当前head在线CI与新PNG/SVG上传以发布后GitHub实际读回为准；上述本地通过不提升物理资格。


2026-10-29 09:05 CST（gate-r32并入R31阶段发布）VECTOR93106已真实完成5输入恢复：原严格分区失败版本保留，比较器/5项测试未修改。先模拟接回place83184/Z的net83166通过同一完整严格关系，再在actual ODB中改接5输入、重导出完整native图重验通过；全部321905原非filler实例、1076467原信号端点、2246顶层端口、380561驱动分量核对，49新增BUF有向无环、365换型Liberty合同匹配，607个NULL端点逐项保留。原cell master/pose/面积、pin/PG/外框不变，本次0新增单元/换型。新checkpoint仍未合法化/详细布线/RC/STA或RTL/系统等价，旧VECTOR实际已布线r01负时序不被替换。下一实际动作是从这一已通过严格关系的真实恢复源进行P&R，不使用旧失败候选或放松检查。

93108/driver ef27ef24d8a1cfda1cbc05932a3f8dd123b8eb17不可覆盖收集gate-r32；tar SHA256 207144418489d25862cd5ad10c23df667bb6ba9a05fcf33d3f0d34d52a29e975。R31实际SYS视图、34图和严格失败、R32端点定位/实际恢复分别保存，原回执不覆盖。SYS实际新图图例/说明已调整避免重叠；原34图/全pin查询及当前矩阵待本次最终复核后发布。全部目标仍active/in_progress/Draft，完整物理/共同冻结/两功能/公平系统对照未完成；登记pending、看板unverified同步pending/审查待指定。


2026-10-29 08:54 CST（gate-r31）SYSTEM93089实际新源视图已完成：原生导出/独立模型重读均0，全部2229 signal pin及PG/原层/尺寸保持、SPEF余量精确重放，当前新源扩展STA报表执行且无文字VIOLATED；minimum_period与原负setup/hold仍保留。重接前后_215139_均由实际ODB重新导出矩形，新增真实对照PNG/SVG与完整目标网CSV；这是块内两单元间网、无BTerm，不伪装成接口pin移动示例。当前native0/负时序源与旧native2分别保留，新父层/完整GDS/RTL仍未资格化。

VECTOR93083只完成优化检查点：再增49个BUF、365处换型、master bbox面积+354.046μm²，原启发式余量−4.179502/0.014579ns仍负，未合法化/详细接线/RC/STA。93094复用两份完整原生图作未修改的严格数字关系检查FAILED：消去新增BUF后原逻辑网仍拆分，原失败不删。93102后到诊断进一步锁定1网net83166的11端点，其中5个输入改接net158807；结果尚不在本快照，另存闭合源。93106已提交受控恢复试验：先要求模拟接回原驱动网通过同一完整严格检查，再做真实native接线、重新导出完整图重验；尚无终态，不当恢复成功。未修改原比较器或5项测试，不以“均为BUF”豁免错误；新P&R驱动要求实际恢复源严格关系通过，尚未提交。

LL SYSTEM93092已完成有4项native DRC的完整PG-only备选源诊断：3网全部862行真实接入及831行局部多端信号/时钟矩形、同一ODB的VDD/VSS/OBS实际导出、全部来源SHA保持。仍native4/原负时序，未修复；原三点92747因未移动bit_4812无AP失败保留，不重提同样试验。93090两770边guide网格相位试验实际运行，物理轨道/规则/hook/PG/OBS不改；未合格共同底座仍旧R02叶输入、未冻结。MXU93074 fresh检查仍运行，不按耗时取消；原92690/92691、92855不改。

93098/driver43d1f49df571b2467e5ebc0604b25ef2baf208b2不可覆盖收集gate-r31，tar SHA256 da50b6c0f0831bcf6be5f24c443e051eba2ccbb0be6a37d96102f1db0c4708af。上次01e0d81两在线CI40793244114/40793244111 success，矩阵blob179d49efb97ab627231aa731165abae9b64a9542与本机相同，33图已核验上传。新34图/数据/脚本随本次发布再读回。全部目标active/in_progress/Draft，未合格冻结/两完整功能/公平系统对照未完成；登记pending、看板unverified同步pending、管理员/审查人待指定。


发布合并补核：gate-r29本身已包含93030两模式最终GRT-0116失败，openTPU终态UTC2026-10-29T00:09:54.320170+00:00，LL终态2026-10-28T22:42:10.391225+00:00；两者均无DRT/fresh/全边连通/RC/STA，不把失败guide线长当真实布线长度。R28与R29管理/业务验证25068文件SHA、160链接、16573 raw、24767原pin/74301 ABC、Python编译/diff和33图浏览器/常量查询通过；最新native0且负时序矩阵、六块含实际源列的扩展表已打开目视核验。登记management-hub PR5刚读回open/unmerged（head11b65cf39b85a2d893e48544b2eb7b4183db4372），仍pending；无Projects工具/board.json，未伪报看板同步。


2026-10-29 08:15 CST（gate-r29与r28合并阶段发布）SYSTEM93072已实际终态：原网_215139_的M1端点/原via1与via2定义原生接线，fresh native DRC从2降0；466332网/1474481端点/14634126形状所检连通、双PG/RCX/原SDC均完成。所有原cell/pose/信号连接/pin/PG/外框保持，全部466332多端网WIRE/VIA矩形多重集仅该网变化、其余466331网表示相同；不是几何并集或RC等价证明。setup/hold仍−0.056396/−0.119919ns、1233文字违例，整体Slurm FAILED 1:0因保留完整验收门槛，不当全部资格。当前矩阵升级native_stacked_via/r01，旧native2失败与各源余量保留，未导出匹配模型/未做新父层或完整GDS；此前六块扩展STA的SYSTEM源是旧system_patch_route/r02，表内已明确来源，不能借用于新源。

93085复用不可覆盖driver4b3c577afa397aea71db632470a88d8f47e2683f收集gate-r29，tar SHA256 778bfcd59095b1c1fbb2cc312b92a432c9b363550fb8fee1bf1b0977e770ce0b；gate-r28全部六块扩展STA及旧时序失败也在本阶段上传。SYS新实际模型/前后目标网原生矩形导出及新源扩展检查已编写，可复用现有view流程，尚未提交。上层grid相位试验亦未提交。新脚本只准备不算执行；发布读回后实际提交，两者分别保持约束/原层，不修改活动驱动。

全部目标继续active/in_progress/Draft；未合格冻结、两完整功能/公平系统对照未完成。原92690/92691、92855、93030和MXU93074、VECTOR93083继续，不按耗时取消。新终态资料与历史压缩前的Issue/PR全文均保存，不删除规则、原失败或缺真实SRAM GDS/目标层/minimum_period等缺项。


2026-10-29 08:06 CST（gate-r28）93076全部六块源绑定扩展STA已完成：ACT/MXU/openSYS/GEMM/VECTOR/llSYS均native0、原setup/hold原文精确重放、原ODB/SPEF/SDC及库源保持，新增检查报表无文字VIOLATED；缺失规则与原负时序/电气/未标注寄生独立保留，不称完整STA或系统资格。LL终态UTC2026-10-28T23:56:19.376144+00:00，已从R27运行中准确更新。

VECTOR93083新受控试验实际读同一安装repair_timing body，证实routed状态会强制detailed_routing寄生来源；仅在内存副本移除375675条原SIGNAL/CLOCK dbWire，原生design_is_routed由1变0，原文件/单元/pin/PG/SDC保持，进入placement优化。driver3b5ab3f9a9c5209d1d58f23a5fd5d016278a48c4；仍在运行，原RSZ-0074/Signal11保留，新合法化/详细接线/RC/STA/功能合同未完成。SYS93072/MXU93074的fresh检查继续，未给零/通过。

两模式各1540个实际M10 hook上的计划via10 cut逐对筛查1185030对，最小矩形间距2.4μm，假设0.88μm下无成对冲突；来源/逐hook最近邻CSV与脚本已保存。这不是已放置via或实际DRC/OBS/PG/包围/全布通，不能当GRT根因已找到。已准备独立上层guide grid相位试验：只改全局guide原点为2850/2850 DBU（1.425μm），保留原770边、物理轨道/层/规则/pin/PG/OBS及默认50次预算；尚未提交，不称已布通。DBU单位来自实际安装Tcl传参及OpenROAD官方Global Routing文档，实际DEF仍需核验。

93084/driver4b3c577afa397aea71db632470a88d8f47e2683f不可覆盖收集gate-r28，tar SHA256 1dd0f3e6b751e954610102bbedf85339d5d04f4df6e59bad1248159545a845df。R27发布f36b328两在线CI40790785732/40790785691已成功，33图PNG/SVG在线blob与本地一致。GitHub旧PR/Issue描述完整归档data/github_description_history/pre-r28.json，接下来压缩在线摘要、保留原目标和历史证据链接，避免重复几十段旧运行状态妨碍审查。任务active/in_progress/PR Draft；六块完整资格、合格共同冻结、两完整功能与公平系统对照未完成，登记pending/看板unverified同步pending/管理员及审查人待指定。


R27发布检查：管理结构、24767原pin/74301 ABC、23008文件SHA/158链接/14525 raw业务验证、Python编译及diff检查通过；独立Edge加载33图、常量位查询通过，最新扩展STA表与MXU实际M6图已打开目视核验。新扩展检查只覆盖指定源/已定义规则，不替代原时序失败或整体物理资格。


2026-10-29 07:54 CST（gate-r27）实际阶段：VECTOR93073完成原guide/GRT上下文初始化并进入setup多轮优化，随后RSZ-0074（_362545_/ZN、_080826_，路由树找到1端点、应为2）FAILED；不是Signal11根因已修复，也未产出可用检查点/after合同/合法化/新详细布线或RC/STA，原−4.140220ns及闭合源SHA保留。原回执固定repair_model文本与r02实际加载GRT不一致，报告按实际脚本/阶段纠正解释，原回执不改。

93030的llaccel子模式200次搜索仍GRT-0116 FAILED，未进入DRT/fresh/完整连通/RC/STA；openTPU子模式仍运行，不能因同一Slurm未退出就把已失败子模式写成运行中。SYS93072已完成实际单网via叠放接线、双PG及RCX/原SDC，fresh/全合同仍在取得；MXU93074完成新actual视图替换/2172网导出/双PG，fresh检查仍在运行，均不是通过或完整资格。

93075原生能力输出完成但Python元数据阶段漏导入sha而NameError，Slurm FAILED，原日志保留；已修正供复用，不重复跑探针。93076新增全部六块源绑定扩展STA中，快照时ACT/MXU/openSYS/GEMM/VECTOR五块native0、setup/hold原文重放一致，LL仍运行。补查pulse width/gating/skew等、库规则声明/约束/寄生覆盖；新增报表无文字违例不等于规则齐全或修复原负时序。typical库有45处min_pulse_width timing_type、minimum_period timing_type为0。

不可覆盖gate-r27由93079/driver8bb16b5222006a1eb20ac18ea04ccafafcc97928收集；下载tar SHA256 acb8d94cb4692c121b38226daeb79e3fc8227a4b236fe622f369a345e4ddc429。R26发布e85a4eb两在线CI40789109126/40789109144 success；33图已在线读回，新MXU PNG/SVG blob分别b77d9f069f0ff0ab7fcab12ea3f00c5eaccb9f16/deb8f8383a97f951fc45eb0a49e1159a912d4c5c与本地相同。当前阶段实际验证/上传以新回执为准。六块完整资格、共同冻结、两完整M11/M12模式与公平系统对照均未完成；active/in_progress/Draft继续，登记pending、看板unverified/同步pending、管理员/审查人待指定。


2026-10-29 07:45 CST发布前复核：修复报告源升级晚于JSON/CSV保存的顺序问题，最新SYSTEM源现准确为native_clean_patches/r02（native2、setup/hold−0.056396/−0.119919ns），旧源完整保留。管理检查、24767原pin/74301 ABC、22000文件SHA/152链接/13524 raw业务验证、编译和5项合同测试通过；独立Edge加载33图/常量位查询通过，新MXU实际M6图和最新矩阵已打开目视核验。浏览器QA选择器转义错误已修正；不是物理规则或功能检查失败。当前未合格冻结/两完整功能/公平系统对照仍未完成。新图上传、当前head在线CI以GitHub读回为准。


2026-10-29 07:32 CST（gate-r26）MXU93060新源04e59990bd24695ba00738a5d89ab8b3ec21978f87c1209c6a45f878c8b9bbd7的clean ODB/LEF/OBS/DEF/实际网表和非零提取Lib已导出、独立重读通过；2172位/PG/尺寸/原层保持，SPEF余量精确重放。minimum_period仍缺失。新增M6真实重接前后及全目标网PNG/SVG：两版本原pin与真实OBS几何交面积均约0.0098μm²，OBS仍延伸出pin，不能当父层可达。图中真实via5/M6位置328.535/1088.710μm只是后续接入研究依据，尚未迁移pin。

SYSTEM93038已终态FAILED：fresh native仍2，同网_215139_的原M2报项，466332网/1474481端点所检连通、双PG/RCX/原SDC完成，setup/hold−0.056396/−0.119919ns、1233文字违例；所有原cell/pose/连接/pin/PG/外框保持。矩阵更新到这份最新失败源，旧−0.056303/−0.119814及原2项不丢。下一受控ECO拟用真实via定义/端点重新叠放两级via并原生重接，仅准备脚本，尚未提交；不改规则/单元/原pin。

93061 ELF诊断读到min LOAD0x200000/entry0x227f200，候选栈平移后的末帧仍比entry早4054字节，不对齐_start；地址解释/根因未闭合，不把候选函数名当精确定位。后续原guide/GRT上下文初始化只是独立能力试验，尚未提交，不能称修复CloneMove根因。93064/driverc22276e086a79f25f4d84ec9f981b2ca76ccace9收集不可覆盖gate-r26，tar SHA256 4523955011d5f8ee074f4c44a380b1e85ec190b3a1323a40208cd343fa1cb0a4。上一发布bea2622两CI40783257027/40783256957 success，32旧图已在线核验；本阶段新图需随本提交上传读回。整体active/in_progress/Draft，未合格冻结、两完整功能与公平系统对照未完成。

2026-10-29 06:43 CST新增实物终态（gate-r25）：MXU93041真正完成M6接入重接/新LEF导出，fresh native0、191438网/597343端点/5550255形状所检连通、双PG/RCX/原SDC完成；setup/hold0.246690/0.038538ns，文字违例0，所有原cell/pose/连接/pin/PG/外框前后SHA完全相同、原pin/尺寸与新LEF匹配。本次无新增单元/换型，原r04一处换型成本继承，不当纯XY收益。新RC匹配模型与父层尚未执行；旧MXU父层1项M6–OBS失败仍保留，原缺4 SRAM GDS/规则覆盖缺口不消失。

GEMM93043旧新父M10提议在当前源筛查失败，未路由；93049重新选128号M10点787.295/944.07μm后仍严格GRT-0116拥塞FAILED，DRT/fresh/连通/RC/STA未执行。绑定真实658diode视图/3753位及源ac4702d5b6ff9e35e9030eabe767505aa54d93cd9cc708430e57cd5919f8b3d0，旧92841不能替代。VECTOR93048在setup优化首次迭代前Signal11/native−11，未产出检查点、after指纹、合法化或新路由/RC/STA；缺after输出的false表示检查未执行，不当实际pin改变。93051原始addr2line与调用背景不一致，根因未闭合，下一步核对ELF加载基址/栈地址表示，不能据此认定CloneMove原因。

93052/driver4d72bcc58471419a336ff441fb0eff5bc8f00401收集不可覆盖gate-r25，tar SHA256 093a397f5bcd9434af8e50ff813cbd32780517e5f1626e30e3c4ffbe9719b80b。此前10aba9d两CI40777521996/40777521461均success，32图已上传及在线SHA匹配。新MXU源已入矩阵、旧时序/完整GDS/同成本对照另存；当前共同底座仍旧R02输入未升级，未合格冻结。两完整功能/公平系统对照未完成，任务active/in_progress/PR129 Draft。登记pending、看板unverified/同步pending、管理员/审查人待指定。

2026-10-29 05:59 CST（gate-r24）：SYSTEM修订93038已实际进入DRT，容器Lib SHA前置通过；尚无终态，不称修复通过。MXU93040因旧叶回执没有setup_ns字段在路由前KeyError，原日志保留；93041改为按SHA读取原生setup/hold原文，已实际完成M6临时ring及增量GRT、进入DRT。原act_data[12]层/XY/0.14×0.14μm尺寸及所有原实例/连接/PG/OBS/约束保持；临时ring不删除原占用，父层还未用新视图检查，不能把它说成M6–OBS问题已解决。93030独立200次搜索继续，92690/92691和92855保持活动/依赖，不按耗时取消。93042/driver8b4a80a73808903b5f2cbbe35c9c7bd2225246dc收集不可覆盖gate-r24，tar SHA256 0a57b1069aedff0bccfce873db1f1a51198bd314187974582793020fe1f99870。上一854379b两CI40775280767/40775280876均success，新M2 PNG/SVG已在线读回与本机blob c3fbd28dc2cb89e2124b8228095cd624437c4b63/212b30305629a94e1bfc2a0a58b95334e74327ba完全一致。任务active/in_progress/PR Draft，整体未完成。

2026-10-29 05:50 CST增量（gate-r23）：93028对新SYSTEM重排源真实ODB/SPEF/原SDC完成只读重放，setup/hold精确一致−0.056303/−0.119814ns。当前setup由u_slice.u_quant.ackw寄存器到bit_114845（15 cell arc约0.7707ns、16 net arc约0.3261ns，工具JSON舍入，排除时钟/required项），hold由bit_1216到_28604_[223]寄存器；不是旧92781路径，也不是零线延迟下界。新增真实_215139_网络19行矩形CSV、两M2原生DRC bbox及局部PNG/SVG，空白不当无金属。93031 clean_patches前置在host读取container Lib路径而失败，未路由；日志保留，修正为同一原工具镜像内前后SHA核验，新r02尚未提交。93030独立FastRoute预算50→200实际运行，规则/轨道/端点/PG/OBS不变，原GRT/DRT失败保留。93032/driverdc2b248f1475603b755effdfad6f251938ec361c收集不可覆盖gate-r23，tar SHA256 58149f16a80ed96266c7fb98939d23cb786cf18b8cb557b1921b60f6dfc0d323。上一4d04c4a两CI40774247463/40774247712 success，图片在线SHA一致；本地32幅图加载/常量查询及实际M2图打开视觉核验，完整目标active/in_progress/Draft，未合格冻结/未完成两系统及公平对照。

2026-10-29 05:43 CST（gate-r22）：93025全770原生guide详细接续已FAILED，两模式均完成pin access后报DRT-0352 Input route guides are congested；未产出适配布线，fresh DRC/全边物理连通/M10包含检查未执行。原GRT-0116、全部真实DB guide和同一未合格下层SHA保留。93027/driverb2ef98a5396ef3170505eae2494a771e101df7ce收集不可覆盖gate-r22，tar SHA256 6c8ed682d0f8c8df0cb24a5b2f94e0868cda725441678ea75174b9a9e580273b。新SYSTEM实际SPEF关键路径/两DRC真实net诊断93028已提交；它是只读诊断，不是修复通过。已准备独立FastRoute搜索50→200次预算及native clean_patches试验，尚未提交，物理规则/原SDC/目标pin不变。上一发布f704b49的两CI40773146675/40773146774均success，PNG/SVG在线blob匹配；不是物理资格。完整目标继续，底座未合格冻结/两完整系统和公平对照未完成。

2026-10-29 05:34 CST增量终态（gate-r21）：93015在相同全frame、原M10 PG/OBS下完成2/770边详细布线、fresh native0和2网/4端点所检连通；同时真实导出失败检查点全部770网的原生DB guides，不是770边已布通。原92974两模式GRT-0116失败完整保留。SYSTEM92968已FAILED：完整接线/RCX/原SDC后fresh native2，setup/hold−0.056303/−0.119814ns、1233文字VIOLATED；两DRC均net _215139_的M2（Metal Spacing及NS Metal），未放宽规则。GEMM父层92841 native0/3753网连通、MXU92892 native1/2172网连通（剩M6 act_data[12]与宏OBS）；两者只各改一个新父M10接点，使用旧叶源，不能替代当前成本ECO/658diode视图验证。原叶pin/PG保持。92690/92691及92855仍运行/等待，不重提或取消。gate-r21由93021/driver7934616e88776497fe3e086c751e43e1ac82bbc1收集，tar SHA256 a7fd0381b6b1a67f535321bd54ede0f69ff60c88e8044340c4345aca5bfd5e68。下一步在新目录复用原770网真实guides推进DRT，原GRT仍失败；共同底座未合格冻结、两完整功能/系统对照未完成。任务active/in_progress，PR129 Draft；登记pending、看板unverified/同步pending、审查人待指定。

2026-10-29新终态：GEMM658diode源的92976严格GDS合并和未修改原FreePDK45可用deck均return0，实际RDB报项0，源receipt/DEF保持；不是完整制造覆盖、RTL形式、父层或系统签核。旧1460/37/37来源分别保留，native0/RC/原SDC/3753-pin视图证据仍独立。另一项同时明确FAILED：92974两模式各770边均GRT-0116拥塞失败，未执行DRT/fresh/全边连通/实际landing验证，绝不写成完成。gate-r20含新GDS原生零项RDB及两模式原congestion.rpt（估计网格，不当金属DRC），原文和大产物SHA均保留。下一步同frame/全部PG与OBS受控工具诊断并继续其他块与共同底座完整目标。

2026-10-29最新更正：92974两个770-edge适配子试验都已GRT-0116拥塞FAILED，未进入DRT，fresh DRC/全边连通/M10 landing包含核验未执行；原R19快照已收终态，但旧renderer仅显示prepare造成“运行中”过时，现逐模式补入终态，失败不删除。这个构造适配试验失败不等于真实完整系统不可行证明。GEMM658源native/原SDC与3753-pin物理/提取视图已完成，严格GDS92976仍独立执行；共同下层/系统接入及整个目标未完成。

2026-10-29 Asia/Shanghai新增实际视图终态：92997/driver206052c721a7c910a7767a94cbd914d482e96bc3在ROOT/diode_views/r01/gemm-C完成clean ODB/LEF/OBS/DEF/真实网表和提取时序模型导出，全部3753 signal pin及PG/尺寸/原层匹配、SPEF余量重放一致、模型独立重读通过。minimum_period=false，完整规则/新父层/RTL/共同冻结/系统资格仍未闭合。gate-r19由93003/drivereff6bfa6c31bf29d196061b4a116b2564fd8aae3不可覆盖收集。此前发布206052c两CI40758759432/40758759459均success，31幅图已打开及在线PNG/SVG blob读回一致。新658diode负载/两追加换型不能与旧3换型Aopt直接做纯XY收益；旧对照来源另列。严格GDS92976、全770边适配92974及SYS92968等继续，当前任务仍active/in_progress/Draft。

2026-10-29 Asia/Shanghai新终态：GEMM92975定向增加22真实diode后，总658diode版本已fresh native0、268637网/806643端点所检连通、全量数字图和原pose/端点/pin/PG/外框保持；真实setup/hold 0.770702/0.039533ns、文字违例0，另计22 master面积5.852μm²。新严格GDS92976运行，旧37项不提前标已清除。92985证明全网中77条WIRE/VIA矩形表示不同，不能称只重布22网。新增真实接入PNG/SVG及gate-r17/r18双SHA证据；两模式各770边适配92974与SYSTEM92968仍运行。共同冻结/两完整系统/公平对照未完成。 [最新交接](../handoffs/2026-10-29-issue-126-incremental-diode-and-upper.md)。Issue126 in_progress/PR129 Draft；登记pending、看板unverified/同步pending、审查人待指定。

2026-10-29 Asia/Shanghai增量终态：新换型版严格GDS92943仍FAILED37项天线；92972以同版本DEF/GDS/RDB/原生几何SHA读取7516494行，全部37个真实多边形唯一关联22条真实网，与现有636个diode网交集0。全部22网及层级CSV/原多边形证据随gate-r16发布（92973/drivercda2025d28793aeab7a4d3391058d50f3d227e51），不是修复或LVS通过。已编写定向22真实diode增量GRT/DRT脚本（尚未提交作业）；保留636diode、两换型、原功能/位置/接口/PG/OBS/层集合，新增负载/面积成本独立，路由后仍需fresh/连通/RC/STA与原deck。下一步发布读回后执行新适配r02和22网增量接入，不以native0/CI代替整个目标。SYSTEM92968、共同92855和其余LL/父层作业继续；底座未合格冻结，两完整功能/对照未完成。

gate-r15接续：SYSTEM92968复用原合法化检查点运行；770-edge适配92969在两个时钟canonical别名检查失败，未执行路由。精确alias修订与原失败分别保留，不改变连接语义。主矩阵反映最新GEMM真实diode+两换型源，旧等成本控制单列；原30图和逐pin数据保持，完整系统尚未完成。

任务：[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126)，进行中。
起点：[PR120](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/120)，已重新核实 open、未合并，head `4f91e098127b4320ce50dcb29165a7af1fca559c`。
本分支在其上增量提交，不合并或覆盖旧成果。

直接查看：[中文交互 HTML](issue-126-full-pin/report.html)。

最新gate-r14：GEMM真实636 diode后两换型已native0/所检连通/RCX，setup/hold 0.770752/0.039624ns、文字违例0；第一diode版严格GDS仍37项天线失败，新版本原deck运行。SYSTEM92925路由后空句柄导出失败，最终fresh/RC/STA未执行。原失败和物理版本分别保留，共同冻结及两完整系统未完成，详见最新交接及矩阵。

新里程碑：真实256条M10导体原生FIXED属性已独立核对，新PNG/SVG/逐导体CSV随报告；GEMM真实636 diode布线完成但cap2失败，全量数字图保持。仍无合格共同冻结或两完整M11/M12功能，详见[最新交接](../handoffs/2026-10-29-issue-126-fixed-conductors-and-diode.md)。

最新状态以HTML的六块物理门槛矩阵和[2026-10-29交接](../handoffs/2026-10-29-issue-126-physical-continuation.md)为准：已增加SYSTEM全量有向缓冲合同、GEMM天线1460多边形/636网的实际关联及MXU真实M6局部PNG/SVG；实际diode修复和完整资格尚未完成。旧运行中记录保留为历史。

## 2026-10-28 接续：真实接入与六块共同底座（进行中）

用户明确确认六块资源并集、交错布局，并让两功能共享实际固定预连；本轮包含研究M11/M12建模。下方旧阶段的“不扩展M11/M12”和优先边界结论不替代本轮范围；保留内部方案继续系统比较。

- ACT新740-pin接入窗口叶视图：独立native0、4819网/15659端点连通，setup1.255988ns/hold0.031533ns、违规行0。
- GEMM新3021-pin窗口视图：独立native0、268637网连通，setup0.773657ns/hold0.036870ns，但3项最大电容失败。
- MXU新1931-pin窗口视图：独立native0、191438网连通，setup0.246862ns/hold0.040715ns，但1项最大电容失败。
- VECTOR新1022-pin窗口视图：独立native0、375495网连通，setup−4.195674ns/hold0.036847ns，118项时序/电气违规行。独立成本化ECO正在执行。
- 上述四块实际9031个信号pin均与完整增量CSV逐项回读匹配；原功能/层/网络/方向/尺寸和单元/PG/外框保持。新窗口法是完整信号重布线，不能混入此前局部rip的纯XY线长收益。
- 两个SYSTEM的新完整窗口视图仍在执行；llSYS PG修订前26pin/44对直接接触保留，修订后实际13507pin回读、PG指纹相同且直接接触0，不等于完整布通。

ACT256-bit父层实际接入：Aopt和新C均已达到当前native/所检几何/双PG门槛。C的r_data[195]仅修改新增父层M10中间接点，原ACT M5/M6不变；92719独立native0、860网/1720端点连通、PG逐字节保持。新增[真实修复PNG](issue-126-full-pin/assets/act_parent_landing_actual.png)/[SVG](issue-126-full-pin/assets/act_parent_landing_actual.svg)已打开核验；旧1项/后续2项失败都保留。此夹具不等于完整共同底座/系统通过，后续RC/STA采用相同明确研究I/O约束和2/10/50fF负载敏感性，结果单独记录。

该RC/STA已于92732实际执行：原时钟/SDC相同，明确新增研究I/O策略0.2T/0.05T max/min delay、BUF_X4驱动和上述负载。Aopt/C均有约−0.074ns hold失败；10fF时setup分别1.424290/1.353438ns、hold−0.074562/−0.073476ns，C另有4条VIOLATED标记。两者均保留604个零线长接触网的寄生未标注提示，源ODB保持不变，尚无完整RC/STA资格。标记行数不包含所有setup/hold报告行，不能当完整违规总数。先前92726的工具命令兼容性失败也保留，未假写已执行提取。

推送后新增终态：openTPU SYSTEM完整1768-pin窗口版92688/92689已独立native0、460503网/1462823端点所检连通通过；setup−1.779887ns、hold−0.389230ns、2016条VIOLATED标记，仍失败。新增小型terminal_updates/openSYS-r01原生回执补入HTML，旧快照不变。至此五块的11260个实际pin已逐项核对，llSYS完整窗口版仍未终态。

llSYS的PG-only备选完整C也已取得终态：13507实际pin/13184移动，725253网/2325528端点几何连通通过，独立native仍4项失败（3项Metal Spacing、1项NS Metal），未合格。其完整逐pin回读与PG修订表一致；该备选不同于仍运行的新access-r03窗口版，不将两者坐标或结果混用。原直接26pin/44对接触及后续直接接触0、最终DRC4各阶段都保留。

成本化ECO不等于修复成功：VECTOR A/C的原时钟ECO虽然native0/所检几何通过，setup仍−4.136094/−4.162278ns；GEMM/MXU电气专用增量ECO仍有3/1项电容失败。GEMM未增加功能单元；MXU增加1个buffer、标准单元主矩形面积+1.862μm²，但未修复该电容项。两个新ECO拷贝分别移除345005/258099个CORE_SPACER，后续若使用还须恢复填充并完成适用规则；不能说成计算资源或block面积节省，原始数据库不变。

共同构造网表已原生链接：34,954端点与17,686固定逻辑连通分量逐项双射，全部原24,767信号pin及原层保留。两模式逐bit图计划复用同一组256资源，分别770条适配图边；37个常量输出驱动各自独立，另有1个闲置时钟驱动。这是逻辑/原生链接检查，未实现共同布局/预连/时钟/PG、未冻结M1–M10、未仅通过M11/M12实现两套功能。内部施工端口还须在冻结前降为真实保留金属，不能用此网表作已完成底座。

研究M11/M12已实际完成2网/4端点小例与独立native0/几何检查，规则/层高/RC由M9/M10外推，明确研究假设，不具制造签核资格。新增[实际小例PNG](issue-126-full-pin/assets/research_upper_actual.png)、[llSYS PG修订PNG](issue-126-full-pin/assets/llsys_pg_revision.png)、[共同布局proposed PNG](issue-126-full-pin/assets/common_base_proposed.png)，各有SVG；报告连同原图共24幅可查看图像。

旧openTPU父层终态native11失败，旧llaccel父层GRT拥塞失败，92476/92477后续RC/STA未执行。缺SRAM GDS、天线/规则覆盖、模型minimum_period/外部资格及所有STA失败不豁免。详见[本轮交接](../handoffs/2026-10-28-issue-126-common-base-continuation.md)、HTML增量阶段表和原始SHA索引。PR129保持Draft、Issue126保持in_progress。

## 2026-10-28：真实叶模型与后续父层分析

已导出20份与真实叶块版本匹配的研究时序模型：六块A/C共12份，以及ACT/MXU的原XY重布线、Aopt、B和GEMM原XY/Aopt共8份。所有原始信号bit及方向核对通过，匹配SPEF重读的最差setup/hold与原试验均一致；文件、源ODB/SPEF/SDC/Lib SHA、完整端口表和实际失败探针均入库。llaccel SYSTEM C模型只对应8pin局部，不代表已失败的13184pin全C。

这些模型来自实际SPEF及现有研究Lib，区别于路由阶段零电容占位；仍缺minimum_period覆盖和完整外部I/O约束/器件级SRAM资格。原叶块时序/电气失败不删除。两个新父层已通过双电源连通，仍在实际路由。后续独立RC/STA92476/92477已排队，必须先通过native/所检全块连通/PG门槛，并精确匹配模型物理ODB与回执SHA；没有父层签核通过声明。

## 最新完整C与增量物理结果（早期8pin记录见后文）

全部六块A/B/C覆盖已完成；实际完整C和补充修订按下表分别记录。**独立native DRC与OpenDB几何连通通过不等于完整GDS/LVS、父层或系统时序资格。**

| 块/修订 | 实际移动 / 信号pin | 独立native DRC | 所检全块多端连通 | setup / hold ns | 时序/电气违规行 |
|---|---:|---:|---|---|---:|
| ACT 原C | 740 / 860 | 0 | 通过 | 1.259268 / 0.032872 | 0 |
| GEMM 原C | 3039 / 3753 | 0 | 通过 | 0.771186 / 0.041430 | 2 |
| GEMM 增量C_electrical_r03 | 3021 / 3753 | 0 | 通过 | 0.771255 / 0.041530 | 0 |
| MXU 原C | 1964 / 2172 | 3（与VDD短路） | 通过 | 0.245821 / 0.048919 | 5 |
| MXU 增量C_mxu_repair_r03 | 1931 / 2172 | 0 | 通过 | 0.247994 / 0.048823 | 0 |
| VECTOR 原C | 1022 / 2246 | 0 | 通过 | -4.166987 / 0.026787 | 103 |
| openTPU SYSTEM 原C | 1768 / 2229 | 0 | 通过 | -1.765776 / -0.400698 | 2101 |
| llaccel SYSTEM 原C | 13184已place_pin / 13507 | 实际26pin/44对固定PG直接冲突；完整DRT停止 | 完整终态未检查 | 完整C未提取/STA | 不以局部结果代替 |

GEMM恢复真实字节29/30的16data+2strobe到A；MXU恢复完整33pin写lane0，并修复pf_uv[109]、b_rdata[174]两个M5内部PG冲突点。原A/B/C未改，补充完整逐pin表在HTML新增节中，均保持原层/尺寸/网络/单元/PG/边界及相同重布线cohort。真实物理失败是修订依据，不隐藏旧结果。**GEMM/MXU当前优先边界**：修订C实际线长4548300/3132185μm，相对同组原XY重布线4494984/3003026μm分别约+1.19%/+4.30%，并无块内线长收益。VECTOR同样优先边界，两个SYSTEM不建议直接全C替换；ACT有约6.40%实际块内线长收益，仍待父层与完整规则验证。

严格GDS新增结果：GEMM原始及8pin局部C均严格合并成功，但未修改deck分别1346/1358项天线违规；ACT缺2个fakeram GDS，MXU缺4个，不能补造器件。其他GDS检查继续执行，逐项见HTML。没有面积节省声明。

后续严格GDS：VECTOR原始/8pin局部C都能严格合并，但deck均36项天线；openSYS原始缺4个fakeram，诊断deck52486项，含46014项WELL。不能把不完整宏GDS上的诊断当完整规则签核，也不能删除原基线失败。

llaccel SYSTEM完整C的实际place_pin回读已与全部13507信号pin逐项核对，原始/移动后PG指纹逐字节相同。26个pin/44对矩形与固定VDD/VSS同层直接相交，不能靠重布线消除；保留moved/ripped/global ODB和日志后，只停止该新无效试验92369。直接接触证明、实际回读与停止守卫均在HTML链接中；它不是完整DRC检查，也不表示完整C已布线。其他作业继续。

用户授权补充缺失材料后，新建两个**受控父层**，不冒充历史父层：openTPU 6618端点/3408网已在PG与路由前核对通过，双电源连通通过，正在详细布线；llaccel 27050端点独立启动。新TOP_IO/PG策略与37个固定tie cell成本单列，端口Liberty仅物理链接，父层STA禁止据此资格化。历史handoff仍UNKNOWN，详见[决策0004](../decisions/0004-controlled-parent-pin-access.md)。
图像：[ACT](issue-119-pin-xy/assets/act_comparison.png)、[MXU](issue-126-full-pin/assets/mxu_comparison.png)、[openTPU SYSTEM](issue-126-full-pin/assets/opentpu_aux_comparison.png)、[GEMM](issue-119-pin-xy/assets/gemm_comparison.png)、[VECTOR](issue-126-full-pin/assets/vector_comparison.png)、[llaccel SYSTEM](issue-126-full-pin/assets/llaccel_aux_comparison.png)；每块包含局部放大、真实端点图，新增四块PNG/SVG均入库。

复用 Issue55 已有真实 SYSTEM 包装补齐完整功能归属：openTPU 为 ACT/MXU/SYSTEM；llaccel_core 为 GEMM/VECTOR/SYSTEM。18项功能完整归属，两个父层未归属叶单元均为0。外部DRAM/host/封装、llaccel_core外部SRAM存储本体不虚构为已实现block。ACT+MXU合并版是替代粒度，不重复计数。

六块共24,767原始信号pin，A/B/C共74,301行；名称、位宽、方向、层、网络、矩形尺寸和逐pin对应保持。父层逻辑连接及对端pin原层已绑定；原父层真实handoff层/穿层路径仍未知。完整表、来源、候选/冲突/密度与阶段结果见HTML，不把几何L1当实际线长/RC/面积收益。

初步推荐：ACT/GEMM值得稀疏内部数据簇试验；MXU收益有限需局部对照；VECTOR本轮优先原边界；两SYSTEM建议选择性混合布局，全C冲突较多。单块保留边缘pin有可查询理由，不强迫全内移。

已在独立授权目录实际启动匹配8pin的A/Aopt/B/C重新接入，并增加原XY重布线控制A_replay。ACT已完成局部真实重接、fresh native DRC、选中网络真实几何连通及OpenRCX/独立边界STA；其他块按回执分别列示，未完成与失败不改写为通过。
完整全块连通、GDS/LVS/适用完整规则、版本匹配父层可访问性、完整系统RC/STA与电气资格仍待验证。

源码/命令：[full_pin_xy README](../../project/experiments/full_pin_xy/README.md)；完整候选覆盖回执：[coverage_gate](issue-126-full-pin/data/coverage_gate.json)；物理分阶段回执：[physical_summary](issue-126-full-pin/data/physical_summary.json)。
大体积ODB/DEF/SPEF保留于 `/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027`，远程源只读挂载，历史活动作业不修改。

验证入口：

```sh
python scripts/check_project.py
python project/experiments/full_pin_xy/validate_repository.py
```

ACT完整740-pin C现已实际完成接入和详细布线：提取前路由母本经独立进程native DRC=0、全块多端信号/时钟几何连通通过；独立边界setup/hold最差余量约1.259268ns/0.032872ns，电气违例报告为0，仍非完整系统签核。当前OpenRCX后的ODB序列化状态与DRC不兼容，已通过逐阶段对照定位并隔离，所有物理母本使用提取前routed/clean ODB，RCX/STA单独记录。新增四块候选按真实制造网格r02增量修订，r01与失败保留。

## 历史首轮局部C接入记录（后续完整范围见上表）

下表只说明已执行范围；所有六块的当前C试验均独立clean native DRC=0、全块多端信号/时钟OpenDB几何连通通过。GDS/LVS、完整规则和真实父层接入均未由此通过。

| 块 | 实际C范围 | 独立块setup余量ns | hold余量ns | 当前模型结果 |
|---|---:|---:|---:|---|
| act | 740 pin（完整C） | 1.259268 | 0.032872 | 现有独立边界模型下通过，完整系统未验证 |
| gemm | 8 pin（局部；全C未实施） | 0.775029 | 0.051618 | 现有独立边界模型下通过，完整系统未验证 |
| mxu | 8 pin（局部；全C未实施） | 0.242632 | 0.051323 | 现有独立边界模型下通过，完整系统未验证 |
| vector | 8 pin（局部；全C未实施） | -4.166532 | 0.025641 | 实际时序/电气未通过，原基线失败保留 |
| opentpu_aux | 8 pin（局部；全C未实施） | -0.402281 | -0.382246 | 实际时序/电气未通过，原基线失败保留 |
| llaccel_aux | 8 pin（局部；全C未实施） | -2.153024 | -0.547887 | 实际时序/电气未通过，原基线失败保留 |

ACT相同740-pin cohort的原XY重布线/B子集/C：DRT提取前总线长271,186 / 271,833 / 253,825 μm，via为37,557 / 37,833 / 36,918。C比原XY控制组线长−6.40%、via−1.70%，setup余量略变差；这是单次真实路由统计，不是几何L1、RC或全系统PPA，也不能证明优于所有边界优化。外框相同，不计面积节省。

父层材料继续检查了Issue55的44份已完成parent/union/top元数据，5份含精确原叶ODB哈希，但这只提供placement等来源线索，仍未建立逐pin原始handoff/实际层序；不据此指派M8或宣布父层可访问。


2026-10-28晚接续入口：[中文报告新增真实修复/失败节](issue-126-full-pin/report.html#resume20261028)、[三点实际修复尝试图PNG](issue-126-full-pin/assets/llsys_local_repair_attempt.png) / [SVG](issue-126-full-pin/assets/llsys_local_repair_attempt.svg)、[交接](../handoffs/2026-10-28-issue-126-common-base-continuation.md)。这次LL三点重接线实际DRT-1231失败；GEMM/MXU驱动增强为成本ECO，候选正确不代表完整资格。具体最新终态以原生快照/接续节为准，下方旧表保留来源，不用旧局部8pin覆盖更新的完整候选/物理状态。


2026-10-28晚接续：92783的两块严格GDS在重复顶层LEF提前失败，deck未执行；安装API实测read_lef_with_def=true造成双抽象视图自动加载。9345fd3修复后92798的GEMM已严格合并0、MXU实际缺4个fakeram GDS，完整deck仍待终态；不伪造宏、不放宽检查。新增六块机器门槛矩阵JSON/CSV与latest-physical-gates中文节、不可覆盖gate-r01原文快照。详见docs/handoffs/2026-10-28-issue-126-gates-and-shared-base.md；完整共同底座/两模式/系统比较尚未完成。
