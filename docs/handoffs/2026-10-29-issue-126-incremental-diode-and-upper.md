# Issue126：658真实diode终态、全网增量接线证据及770边适配

2026-10-29T13:18:10.802504+08:00 R38与独立93190终态发布前验证：管理检查、24767原pin/74301 ABC、34952文件SHA/176链接/26380 raw、全部当前LL pin/PG与实际源逐行Counter、SPEF余量逐字重放验证通过；未修改的5项buffer合同测试、编译及CRLF保真的diff检查通过。独立Edge QA-r50加载35图/常量精确查询/无溢出通过；新增真实LL三组前后图已打开检查，补画原M7落脚并修复图例遮挡。所有实际时序/规则/父层失败仍单列，非完整资格。最新在线head、两CI、矩阵与新PNG/SVG blob待推送后实际读回。


2026-10-29T13:17:14.263730+08:00 R38后追加原生终态93190（不覆盖快照）：LL新native0三点源的默认/详细OBS视图、DEF/真实网表/RC时序模型已导出；原生export与fresh model read均0，全部13507信号及原PG/层/尺寸/当前XY匹配、clean ODB SHA d97f1ccd9749f5492277fca820fda02702926ac6694ba96539b36af2cd6d3402与实际源相同。原SPEF余量逐字重放−3.909029/−0.587515，仍失败；minimum_period覆盖仍缺失，父层/完整规则/系统资格未完成。11份小型原生终态文件逐SHA后无损归档data/gate_terminal_updates/llsys-tip-views-r01，capture.json记录原文SHA与捕获时间，不重复采集全部历史试验；大物理视图及模型仍有原始SHA索引。主矩阵模型状态相应升级，原R38运行中记录不改写。


2026-10-29T13:12:49.893042+08:00 R38：全部24767真实父层轨道审计/bit_1025完整535行原网及374条局部真实金属PG/OBS已收齐。LL原R02有13184 preferred中心未对齐，其余五块0；仅几何风险不等于NoAP判定。bit_1025原via5_0落脚已取得且原网对齐，可尝试删除3旧末端WIRE后保留原M5/0.14μm尺寸重新接入；只是待验证方案。新增三处原native4→0修复真实前后图，M4–M7/via4–via6及实际pin矩形，35组PNG/SVG，周边异网未画不代表空闲。原STA −3.909029/−0.587515仍失败。

时钟原生小探针93193：read_LEF后MTerm SIGNAL，read_Liberty后CLOCK，link与原create_clock后保持；旧/新源LEF都SIGNAL而真实时序模型均clock:true，说明绑定阶段是必要环节。整父层93194先载库再swapMaster实际Signal11，未执行fresh，原始失败保留；93197已改为先swap再载同一别名真实时序库后检查，R38快照时仍运行，不以小探针当实际修复成功。LL当前native0源匹配视图93190仍运行，未把导出作业提交当完成。

R38/93201，driver3c97d7c273638eb390d498b19ba803b95faa0eb2，UTC05:10:15.651555，tar SHA256 bd6b4a98a769ca1be00b86237033f2c226987178de9c354701c51c7c207728f8，25483795字节，1412原文逐SHA核验。原R35–R37/原ABC/所有失败保留。完整目标仍active/in_progress/Draft，合格共同冻结/两完整功能/公平系统对照未完成。下一步先收齐93190/93197，运行源绑定bit_1025真实接线ECO（保留新失败并做全块native/连通/PG/RC/STA），继续适配异网短路、子块电气/时序及原92690/92691/92855。


2026-10-29T12:55:41.957292+08:00 R35/R36/R37发布前实检：check_project通过；validate_repository完整24767原pin/74301 ABC、33516文件SHA/166链接/24968 raw通过；未修改的5项buffer合同测试、Python编译、diff通过。Edge独立QA-r48加载全部34图、精确常量查询、无横向溢出通过，当前六块矩阵已打开目视核验。MXU clk USE实际回归仍FAILED，验证器对照2245条原始before/after行记录失败，不降低接口或物理检查。在线head/CI/图片blob待推送后读回；整体任务active/in_progress/Draft，非完整物理资格。


追加核验：93074不仅fresh native1，原生宏接口不变检查也False。完整2245条before/after宏pin矩形记录中仅clk的USE CLOCK→SIGNAL，几何/层/尺寸/方向/网络相同；这是真实时钟元数据合同回归，不能忽略或当接口保持。报告/验证器均明确其FAILED并对照全部原始行，不改旧回执、不删时钟检查；后续须依真实RTL/SDC在原生视图生成流程修复并重新核对。


下一实际步骤已启动：parent_noap_grid_audit/r01从真实父层R02的六份alias LEF/原生实例与TRACKS数据核对完整24767信号pin，并从已闭合LL native0全网导出提取bit_1025和三条已修复原网的真实完整矩形。只是几何对齐/真实端点诊断，不是access或DRC判定，未修改源或编造内部端点；作业/固定驱动见data/runtime_submissions/parent_noap_grid_r01.json。结果以实际回执为准，不把提交当完成。


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


R33/R34阶段发布前复核：管理检查、24767原pin/74301 ABC、29565文件SHA/165链接/21041 raw业务验证、Python编译、未修改的5项buffer合同测试、diff通过；Edge加载34幅图与逐常量位查询通过（gate-report-qa-r46），最新矩阵、SYS实际前后图及预连上下文失败/770边诊断段已打开目视检查。原native/STA/完整资格失败不提升。最新head/在线CI和图blob以推送后实际读回为准。


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

GEMM下一实际接入已准备：run_escape_fixture.py显式real_diode658入口绑定diode_views/r01的clean ODB ac4702d5b6ff9e35e9030eabe767505aa54d93cd9cc708430e57cd5919f8b3d0、真实非零timing.lib及全部3753原pin/PG；原92841旧源成功不借用。原128号新父M10成功修订位置只作proposal，会再次对当前真实M10 OBS/新PG/其他landings筛查并重新布线/检查。尚未提交作业，不称可达通过。

2026-10-29 05:59 CST（gate-r24）：SYSTEM修订93038已实际进入DRT，容器Lib SHA前置通过；尚无终态，不称修复通过。MXU93040因旧叶回执没有setup_ns字段在路由前KeyError，原日志保留；93041改为按SHA读取原生setup/hold原文，已实际完成M6临时ring及增量GRT、进入DRT。原act_data[12]层/XY/0.14×0.14μm尺寸及所有原实例/连接/PG/OBS/约束保持；临时ring不删除原占用，父层还未用新视图检查，不能把它说成M6–OBS问题已解决。93030独立200次搜索继续，92690/92691和92855保持活动/依赖，不按耗时取消。93042/driver8b4a80a73808903b5f2cbbe35c9c7bd2225246dc收集不可覆盖gate-r24，tar SHA256 0a57b1069aedff0bccfce873db1f1a51198bd314187974582793020fe1f99870。上一854379b两CI40775280767/40775280876均success，新M2 PNG/SVG已在线读回与本机blob c3fbd28dc2cb89e2124b8228095cd624437c4b63/212b30305629a94e1bfc2a0a58b95334e74327ba完全一致。任务active/in_progress/PR Draft，整体未完成。

2026-10-29 05:50 CST增量（gate-r23）：93028对新SYSTEM重排源真实ODB/SPEF/原SDC完成只读重放，setup/hold精确一致−0.056303/−0.119814ns。当前setup由u_slice.u_quant.ackw寄存器到bit_114845（15 cell arc约0.7707ns、16 net arc约0.3261ns，工具JSON舍入，排除时钟/required项），hold由bit_1216到_28604_[223]寄存器；不是旧92781路径，也不是零线延迟下界。新增真实_215139_网络19行矩形CSV、两M2原生DRC bbox及局部PNG/SVG，空白不当无金属。93031 clean_patches前置在host读取container Lib路径而失败，未路由；日志保留，修正为同一原工具镜像内前后SHA核验，新r02尚未提交。93030独立FastRoute预算50→200实际运行，规则/轨道/端点/PG/OBS不变，原GRT/DRT失败保留。93032/driverdc2b248f1475603b755effdfad6f251938ec361c收集不可覆盖gate-r23，tar SHA256 58149f16a80ed96266c7fb98939d23cb786cf18b8cb557b1921b60f6dfc0d323。上一4d04c4a两CI40774247463/40774247712 success，图片在线SHA一致；本地32幅图加载/常量查询及实际M2图打开视觉核验，完整目标active/in_progress/Draft，未合格冻结/未完成两系统及公平对照。

2026-10-29 05:43 CST（gate-r22）：93025全770原生guide详细接续已FAILED，两模式均完成pin access后报DRT-0352 Input route guides are congested；未产出适配布线，fresh DRC/全边物理连通/M10包含检查未执行。原GRT-0116、全部真实DB guide和同一未合格下层SHA保留。93027/driverb2ef98a5396ef3170505eae2494a771e101df7ce收集不可覆盖gate-r22，tar SHA256 6c8ed682d0f8c8df0cb24a5b2f94e0868cda725441678ea75174b9a9e580273b。新SYSTEM实际SPEF关键路径/两DRC真实net诊断93028已提交；它是只读诊断，不是修复通过。已准备独立FastRoute搜索50→200次预算及native clean_patches试验，尚未提交，物理规则/原SDC/目标pin不变。上一发布f704b49的两CI40773146675/40773146774均success，PNG/SVG在线blob匹配；不是物理资格。完整目标继续，底座未合格冻结/两完整系统和公平对照未完成。

2026-10-29 05:34 CST增量终态（gate-r21）：93015在相同全frame、原M10 PG/OBS下完成2/770边详细布线、fresh native0和2网/4端点所检连通；同时真实导出失败检查点全部770网的原生DB guides，不是770边已布通。原92974两模式GRT-0116失败完整保留。SYSTEM92968已FAILED：完整接线/RCX/原SDC后fresh native2，setup/hold−0.056303/−0.119814ns、1233文字VIOLATED；两DRC均net _215139_的M2（Metal Spacing及NS Metal），未放宽规则。GEMM父层92841 native0/3753网连通、MXU92892 native1/2172网连通（剩M6 act_data[12]与宏OBS）；两者只各改一个新父M10接点，使用旧叶源，不能替代当前成本ECO/658diode视图验证。原叶pin/PG保持。92690/92691及92855仍运行/等待，不重提或取消。gate-r21由93021/driver7934616e88776497fe3e086c751e43e1ac82bbc1收集，tar SHA256 a7fd0381b6b1a67f535321bd54ede0f69ff60c88e8044340c4345aca5bfd5e68。下一步在新目录复用原770网真实guides推进DRT，原GRT仍失败；共同底座未合格冻结、两完整功能/系统对照未完成。任务active/in_progress，PR129 Draft；登记pending、看板unverified/同步pending、审查人待指定。

2026-10-29新终态：GEMM658diode源的92976严格GDS合并和未修改原FreePDK45可用deck均return0，实际RDB报项0，源receipt/DEF保持；不是完整制造覆盖、RTL形式、父层或系统签核。旧1460/37/37来源分别保留，native0/RC/原SDC/3753-pin视图证据仍独立。另一项同时明确FAILED：92974两模式各770边均GRT-0116拥塞失败，未执行DRT/fresh/全边连通/实际landing验证，绝不写成完成。gate-r20含新GDS原生零项RDB及两模式原congestion.rpt（估计网格，不当金属DRC），原文和大产物SHA均保留。下一步同frame/全部PG与OBS受控工具诊断并继续其他块与共同底座完整目标。

**2026-10-29更正优先：92974已FAILED41m59s。** R19原文实际已包含终态，先前renderer只显示前置prepare、遗漏终态摘要，导致“运行中”过时；本次按原文更正，失败未删除。openTPU/llaccel两个770边子试验均GRT-0116拥塞失败，分别UTC19:56:29/19:43:47终态，未进入DRT；fresh DRC、完整边连通与M10 landing包含核验未执行。source同一真实但未合格下层8bfddd007d2cc07df5d0f74ebee91799e592185ed7d1e1a0a11a32690ed53cc5保持。原始congestion.rpt有2.85μm估计网格、capacity1/usage2或capacity2/usage3等水平过载，原报告未标具体层；不能当真实金属DRC或原架构不可行证明。下一步读取全量拥塞数据并作同frame/PG/OBS的受控工具诊断，不重提相同试验、不改规则制造通过。

2026-10-29 Asia/Shanghai新增实际视图终态：92997/driver206052c721a7c910a7767a94cbd914d482e96bc3在ROOT/diode_views/r01/gemm-C完成clean ODB/LEF/OBS/DEF/真实网表和提取时序模型导出，全部3753 signal pin及PG/尺寸/原层匹配、SPEF余量重放一致、模型独立重读通过。minimum_period=false，完整规则/新父层/RTL/共同冻结/系统资格仍未闭合。gate-r19由93003/drivereff6bfa6c31bf29d196061b4a116b2564fd8aae3不可覆盖收集。此前发布206052c两CI40758759432/40758759459均success，31幅图已打开及在线PNG/SVG blob读回一致。新658diode负载/两追加换型不能与旧3换型Aopt直接做纯XY收益；旧对照来源另列。严格GDS92976、全770边适配92974及SYS92968等继续，当前任务仍active/in_progress/Draft。

2026-10-29 Asia/Shanghai；仓库rayggxia-workspace/LLMHardwareDesign，[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126)/[Draft PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)，负责人huangpingyang04-lgtm。分支task/126-full-block-pin-xy；此前已发布51bcac124844b344ade86a64031bec14648bfac0，两CI40752386668/40752386573均success；本阶段发布head和CI以PR最新读回为准。整个目标仍active，不能把本文当作全目标完成。

## 新的真实终态

ROOT=/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027。

92975/driver51bcac124844b344ade86a64031bec14648bfac0，ROOT/antenna_incremental_eco/r01/gemm-C：26m41s COMPLETED0。基于严格GDS的37个真实多边形/22条唯一网，定向增加22个真实ANTENNA_X1，保留此前636个diode和两处同功能换型。native实现、fresh DRC和全量数字图导出均0；fresh DRC0，268637网/806643端点/7517145形状所检连通通过。原实例、所有原信号端点/端口/网络、旧636 diode位置/端点、pin/PG/外框保持，源文件未改。真实RCX/原SDC下setup/hold为0.770702/0.039533ns，文字VIOLATED标记0；不是RTL形式或完整制造规则通过。

新增22个master bbox面积5.852μm²，每个真实输入负载0.023429fF，合计658个diode。成本与原3换型、后2换型、636个初始diode分别记录，不能混入纯XY/面积收益。完整GDS由92976/同driver、ROOT/antenna_diode_stream/incremental-r01/gemm-C实际运行，原deck不修改、allow-empty禁用；截至本快照没有终态，不把旧37项说成新版本已清除。

92985/driverce1c79b0c19a68531d455bc418280f0229cb24fe：ROOT/route_representation_audit/r01完成。三份源SHA匹配，全部268637条原始网均纳入WIRE/展开via矩形多重集比较。636diode→两换型有15网表示不同；两换型→新增22diode有77网表示不同（22目标、2条此前636已保护网、53其他网），其余268560网表示完全相同。不同表示可能是切段/重复差异，不等于几何并集、线长或RC变化；不能称只重布22网。两份完整逐网digest TSV.gz各约12.48MB留授权ROOT，有原文SHA索引。

新的gemm_real_diode_access PNG/SVG：区分旧636diode+两换型GDS报项bbox、22个新diode实际位置及一个真实receiver的LEF placement bbox局部。总览符号不是pin/via尺寸，局部不是GDS轮廓，不绘制未提取路径。原3753个信号pin和PG不变以实际字节/SHA证明；当前新GDS资格单独判断。原30图及24767原pin/74301行A/B/C均保留，不从头重做。

## 两模式适配与仍运行项

- 92974/driver51bcac1：ROOT/upper_adaptation_trial/r02。前置1541个M10 hook/唯一clock alias/via10落脚核验通过，但两模式已在GRT拥塞失败、未执行DRT。每模式770边/1540个实际hook、256资源A/B仅是已绑定的计划；同一下层只读输入保持，不是两完整功能或已冻结底座。首轮92969 alias断言失败仍保留。
- 92968/driver53a1b3ed8b535948f4a0e1b1bd8c4e2674c5ca58：ROOT/output_chain_resume/r02/opentpu_aux-C。复用已经完成的r01合法化ODB，不重选/移动buffer；按实际实例名查找修复空句柄导出，check_placement和原合同通过，真实GRT/DRT继续。原92921 Signal11、92925导出失败保留。
- 92690 LL完整窗口RUNNING，92691等待依赖；92841 GEMM父层接点修复、92892 MXU父层修复、92855共同下层GRT仍RUNNING。只操作本人独立ROOT，不按耗时取消、不改活动驱动/输出，不干扰Issue55或其他成员作业。
- 92855已写256条原生FIXED M10资源及1029个父层施工接点、双PG所检通过；下层私有路由尚未终态，仍不是合格共同底座。构造port下降、真实模式共享、规范化M1–M10冻结与完整功能/RC/STA/端到端公平对照均未完成。

## 独立诊断与原始证据

92979/92984只读native GRT能力探针未附加/发信号给活动进程。直接写出的Tcl body完整，实际二进制SHA仍0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。长stdout混排不能当工具源码损坏；没有因此改solver、规则或原活动作业。

VECTOR真实提取关键路径的141个cell arc合计6.7401ns，net约0.1984ns；当前同函数系列FA_X1/HA_X1/OAI33_X1没有更大驱动型号。audit_path_liberty_tables.py以实际Liberty SHA 8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1生成全部141段CSV。各arc独立表格最小值混合不同slew/负载/跳变/条件，不是可同时实现的STA、零连线下界或不可行证明；未改架构、流水、约束或物理输入。

gate-r17由92988/driverb7f9fcf1bd88cbfb12a246957bd1e37592fbe8d1收集闭合native中间阶段，gate-r18由92993/driver80c2747e976f5665bdf71c0a38a8d59ad992f6c0收集最终native回执和全网差异。两个raw/gzip双SHA快照不可覆盖，下载tar SHA分别1a16fff147512622d597de70a03dde287612e8b165940941e3ac28f56286b23d和a9905f477b472e0327144f0c14383332408a872d3bf31bd44c73dc13f2d240b7。大ODB/GDS/SPEF及完整PG表留授权ROOT，通过闭合原生阶段或终态回执SHA索引，不拿缺失本地PG表虚构几何。

## 下一条实际动作及未完成项

92997的658diode实际视图导出已经完成，不重提。下一步收齐92976严格GDS及其他实际终态，并核对两770-edge模式的真实GRT进度；继续六块接入修复/共同底座/两模式/公平对照完整目标。已编写probe_upper_fullframe_subset.py/upper_fullframe_probe_job.sh，只克隆闭合的真实placed_adapter检查点，在相同全frame和全部原M10 PG/OBS约束上保留2/770条真实边并启用verbose，定位工具规模瓶颈。本文本次更新时诊断作业尚未提交，发布读回后再执行，实际作业以runtime_submissions为准；不附加/暂停/取消原770-edge作业，不以子集代替完整覆盖或模型/系统资格。

如诊断证实默认GCell搜索粒度带来开销，可进一步研究原物理层/轨道/规则不变的粗全局guide或直接研究guide→原12层详细布线路径；这是待验证工程假设，不是已经执行/优化成功。不改M1–M10物理模型或降低最终规则检查，不以删除层/规则制造通过，所有策略最终仍需原完整研究技术下的fresh DRC/几何与真实M10 landing约束。先看实际probe日志再选择变量，不能仅因耗时宣称根因。

VECTOR/openSYS原时序失败、LL源native4及完整窗口未终态、ACT父层hold失败/604寄生未标注提示、缺实际SRAM GDS、原deck规则覆盖/模型minimum_period及历史逐pin目标层缺项全部保留。没有完整设计RTL形式证明、合格共同冻结、两完整M11/M12实现或公平系统收益结论。六资源并集/真实共享导体选择已确认，不重新询问。

规则rayggxia-project-collab1.0.0；project_id llm-hardware-design；登记management-hub PR5 pending；缺board.json/Projects能力，看板unverified/同步pending，管理员/审查人待指定。Issue in_progress、PR Draft，Refs #126，不合并PR120/129、不提前关闭任务。
