# 当前状态

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

2026-10-29 Asia/Shanghai新终态：GEMM92975定向增加22真实diode后，总658diode版本已fresh native0、268637网/806643端点所检连通、全量数字图和原pose/端点/pin/PG/外框保持；真实setup/hold 0.770702/0.039533ns、文字违例0，另计22 master面积5.852μm²。新严格GDS92976运行，旧37项不提前标已清除。92985证明全网中77条WIRE/VIA矩形表示不同，不能称只重布22网。新增真实接入PNG/SVG及gate-r17/r18双SHA证据；两模式各770边适配92974与SYSTEM92968仍运行。共同冻结/两完整系统/公平对照未完成。 [最新交接](handoffs/2026-10-29-issue-126-incremental-diode-and-upper.md)。Issue126 in_progress/PR129 Draft；登记pending、看板unverified/同步pending、审查人待指定。

2026-10-29 Asia/Shanghai增量终态：新换型版严格GDS92943仍FAILED37项天线；92972以同版本DEF/GDS/RDB/原生几何SHA读取7516494行，全部37个真实多边形唯一关联22条真实网，与现有636个diode网交集0。全部22网及层级CSV/原多边形证据随gate-r16发布（92973/drivercda2025d28793aeab7a4d3391058d50f3d227e51），不是修复或LVS通过。已编写定向22真实diode增量GRT/DRT脚本（尚未提交作业）；保留636diode、两换型、原功能/位置/接口/PG/OBS/层集合，新增负载/面积成本独立，路由后仍需fresh/连通/RC/STA与原deck。下一步发布读回后执行新适配r02和22网增量接入，不以native0/CI代替整个目标。SYSTEM92968、共同92855和其余LL/父层作业继续；底座未合格冻结，两完整功能/对照未完成。

2026-10-29 Asia/Shanghai：Issue126新SYSTEM恢复92968实际运行，复用同一已合法化检查点；770-edge适配92969在时钟native别名前置检查失败、未路由，已核实两个精确alias并保留gate-r15。GEMM当前矩阵改为已验证636diode+两换型源，旧等成本Aopt/C另列；共同底座未合格冻结、两完整系统/对照未完成。fa3d1a0两CI success，仍in_progress/Draft。

2026-10-29 Asia/Shanghai新终态：GEMM92940保留636真实diode/原接口，两处同功能换型修复cap，fresh native0/所检连通/双PG/RCX，setup/hold 0.770752/0.039624ns、文字违例0；另计master面积+1.330μm²。第一diode版严格GDS92912仍失败37项天线，换型后92943独立运行。SYSTEM92925 GRT/DRT后因空句柄导出失败，最终fresh/RC/STA未执行。gate-r14及中文矩阵发布，[交接](handoffs/2026-10-29-issue-126-fixed-conductors-and-diode.md)。共同底座未合格冻结、两完整功能/系统对照未完成，继续in_progress/Draft。

2026-10-29 Asia/Shanghai：92855已实际写入256条M10导体，92931独立核验原生FIXED/逐网/32×0.8μm几何通过，仍未冻结或证明两模式实际复用。GEMM636真实diode92910已完整布线/fresh native0/所检连通及RCX，但新cap2失败保留；92929全量原端点+636真实非驱动负载的数字图合同通过。新增实际导体PNG/SVG与256行CSV，原24767 pin/74301候选行保持。下一步修复INV_X1/XNOR2_X1实际cap违例，并收集GDS92912及其他活动作业；[新交接](handoffs/2026-10-29-issue-126-fixed-conductors-and-diode.md)。任务in_progress/Draft，完整系统未完成。

2026-10-29 01:07 CST：92925复用同一1262-buffer检查点的独立无STA合法化/check_placement及原连接/非选中位置合同通过，完整原层接线继续；92921 Signal11失败仍保留。gate-r12原文及已关闭阶段SHA独立保存，最终DRC/连通/RC/STA尚未终态，任务仍in_progress。

2026-10-29 01:05 CST增量：SYSTEM现有输出buffer重排92921在Diamond后Signal11（-11），未布线；772链/1262个现有buffer真实移动检查点及gate-r11保留，后续分离几何进程复用，不重复选点。前阶段aab4619两CI成功、29图已上传核验；GEMM真实diode92910/92912及共同集成/LL/父层其他作业继续，未完成总目标。

## 2026-10-29 00:55 CST：VECTOR终态已收集，真实diode接线继续

VECTOR92872全详细布线/fresh native0/375675网所检连通及双PG通过，但提取setup−4.140220ns、83文字违例，整体FAILED；成本180新增buffer/818换型/875移动，非纯XY。92913全量有向数字合同通过，92914/92915实际SPEF关键路径证明VECTOR深链cell arc与SYS长输出net arc两类问题，新增PNG/SVG及原文SHA随HTML发布。GEMM92910的636真实ANTENNA_X1已插入/合法化，正重布线；92912等待严格GDS原deck，原1460项尚未修复确认。共同集成92855双PG检查完成，仍不是冻结或两完整M11/M12功能。Issue126 in_progress/PR129 Draft；[新交接](handoffs/2026-10-29-issue-126-physical-continuation.md)，下方旧运行中说明均保留为历史。

## 2026-10-29 00:40 CST：真实验证继续，未完成整个目标

SYSTEM 92886已完成全量映射相对数字合同：438852个原非filler实例、1539803个原端点、2229个端口、529989个原网络分量保持；5829个新增identity缓冲与980处换型的有向可达性/无环性通过。这是同SRAM合同下的相对网表证明，不是RTL形式验证或时序通过；源setup/hold仍−0.462192/−0.125999ns。

GEMM原GDS 1460项天线多边形已逐项唯一关联636条真实布线网；实际ANTENNA_X1 GDS的原deck识别面积0.0081μm²已核实。尚未插入真实diode，1460失败保留。MXU局部M6报项的重叠OBS被真实同网金属覆盖，新PNG/SVG展示原生几何；不是删除OBS或豁免规则，原父层2项失败保留。

最新核验：92690 LL完整窗口、92841 GEMM父层落脚修复、92855六块共同集成、92872 VECTOR实际重布线、92892 MXU落脚修复均RUNNING，92691依赖等待。VECTOR新检查点合法化完成但最终RC/STA尚无终态。没有合格共同M1–M10冻结、两完整M11/M12模式或端到端系统比较。继续当前作业和真实天线修复，不重复提交。详见[最新交接](handoffs/2026-10-29-issue-126-physical-continuation.md)、[中文HTML](experiments/issue-126-full-pin/report.html)。Issue126保持in_progress/PR129 Draft；登记pending、看板unverified/同步pending、审查人待指定。

## 2026-10-28晚新终态：SYS真实重布线完成但时序失败；GDS规则仍失败

SYS成本ECO92781已有fresh native0、466332网所检连通及真实RCX/STA，setup/hold仍−0.462192/−0.125999ns和1113文字标记，不能宣布修复完成。GDS修复92798终态：GEMM严格合并通过但原deck1460项天线，MXU缺四宏GDS且部分诊断deck1578项，全部保留。GEMM Aopt旧父夹具native0/连通/PG；MXU Aopt/C父夹具5/2项native spacing失败。等成本Aopt ECO92812继续，不重复已有C；共同底座/两M11/M12功能与系统对照尚未实现。


## 2026-10-28晚：Issue126严格GDS读取修复，完整物理门槛仍未闭合

92783两块因KLayout自动读取DEF目录中的双顶层LEF而提前失败，完整deck未执行。实际API确认后，新9345fd3/92798仅保留原显式依赖读取，GEMM严格合并0错误；MXU检出4个缺失fakeram GDS，不以空单元豁免。原deck正在执行，未宣布完整规则通过。六块最新门槛矩阵及原文SHA快照已补充，旧运行中不覆盖新终态。SYS92781及LL92690/92691、父夹具仍须收集；用户允许明确未合格的共同集成试验，但当前尚无合格M1–M10冻结或两完整M11/M12功能/系统对照。


## 2026-10-28晚：Issue126已恢复实际修复，尚未完成物理资格

PR129保持draft/in_progress，六块候选完整覆盖不当作硬化完成。接续新增LL三点实际增量重接线92747，因未移动bit_4812无access point而DRT-1231失败，92748没有完成路由可检查。NDR只读审计92753/92759保留源SHA，四视图971个常规wire矩形未见小于名义NDR宽度；不是spacing/via或实时LL窗口作业的完整检查。GEMM三处/MXU一处实际驱动X2换型、填充恢复及新RCX/STA作为单列成本ECO执行；MXU r04重提取setup/hold正、未列cap违例，但fresh DRC现已0/所检连通通过，完整规则及形式等价仍不齐。VECTOR/openSYS估算切换EST-0104和合法化后Signal11失败保留，92770改为原生GRT模型和支持的替代合法化，检查不删。共同M1–M10未实现冻结，两完整M11/M12功能及系统比较未完成。新增真实PG/旧pin/原生marker/proposed局部PNG/SVG与原24图一起发布；看板/登记/审查缺项保持原状态。

## 2026-10-28（中国标准时间）：Issue126 新增验证里程碑，仍进行中

全部六块候选和功能归属维持完整覆盖。已补齐20份匹配实际SPEF/物理版本的研究叶模型，全部信号bit/方向与重读setup/hold通过；不是器件表征库，仍缺minimum_period/完整外部模型。VECTOR完整同组对照已收集：C实际线长约+1.62%，B独立native DRC4项，继续优先边界。llSYS全C固定PG冲突的约3.04GB失败检查点已锁SHA保存。

原GDS全量deck的WELL.4存在实现/描述不一致，已用独立几何证实漏检窄井及错误的宽度解释，并新增实际GDS逐N/P mask宽度/间距参考。原始所有计数不删；参考0不等于完整DRC通过，原表达式计数尚有31项未精确复现，WELL.2及via enclosure覆盖仍未闭合。两个新父层双电源检查通过、路由仍在运行，92476/92477后续RC/STA依赖严格物理与模型来源门槛，尚未执行。Issue126保持in_progress，PR129 draft。

- 更新日期：2026-10-23（中国标准时间）
- 当前阶段：H1同资源分块／合并物理对照已完成，主线、并发成果及HTML按用户授权整合；H2在独立工作树推进，尚未验收
- 当前工程：[Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15) 已完成openTPU ACT/MXU同功能／资源的块内及父层对照。三块和两父层、六类证明共十一份封存来源严格通过；拆分叶面积+0.412%、总信号线+7.142%、通孔+2.974%，完整setup／hold两组均满足2.5ns／0.5ns预算。[中文结果与三类图表](experiments/issue-15-opentpu-results.html)已生成并目视核验，详见[实验记录](experiments/issue-15-opentpu-comparison.md)。独立全量重布线21亦已自然完成并通过十一项来源／证明对照；本次整合不启动、终止或改写既有远程作业。
- 资料接入：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)；资料已进入 `main`，[PR #2](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/2) 已合并
- 当前资料：项目说明 v1.0、专题研究文档、来源笔记，以及五个参考项目七个案例的布线分析包；三份 HTML 报告、llaccel 引擎内部分析及远程服务器规则已通过 [PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4) 合入 `main`；工艺互连资料的逐层资源评估补充已一并提交
- 已确认边界：研究对象和主要问题已写入项目说明；具体工艺、Block 资源、定制层集合和工具链未冻结
- 关键限制：现有布线结果包含少量 RTL 片段，不含完整源工程、物理数据库、工具环境和日志，不能单靠本仓库复跑物理实现
- 最新工程里程碑（2026-10-23 04:37 CST）：拆分89829自然完成全部严格物理、PG及完整STA，功能89831／RC覆盖89832／五个完整ODB成本复核89833也全部通过。快照f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d，主对照不随实时采集变化。全量DRT21／89826及功能89827／覆盖89828／完整ODB89835也全部自然通过；补充快照独立保存，不改写主报告。全部作业UNLIMITED，无耗时取消。
- 整合交付：PR #8、#10 已合入 main，H1 完整整合树通过本地核验并由 PR #17 交付，其最终 CI／合并状态以在线记录为准。后续 H2 由[Issue #31](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/31)独立推进，本次不修改其工作树或运行任务。项目登记及看板权限仍待管理员处理，详见[整合回执](handoffs/2026-10-23-h1-html-integration.md)。

- 首轮结果：完整 VECTOR 已完成详细布线并导出最终寄生／宏模型，DRT错误0；3 ns setup及电容检查未通过。修复宏PG接入后，89472完整顶层 `COMPLETED 0:0`，DRT错误0、最终双网PSM和2246位接口检查通过，89475最终只读审计通过；父级仍有3个setup违例。历次失败保留，这些工程结果不构成合格硬核或系统签核
- 任务入口：[本仓库 Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues)
- 项目登记：[管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待审查；合并前状态为 pending
- Projects 入口：候选[组织看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1)；本轮查询因缺少 `read:project` 失败，且无 `config/board.json`，实际看板与条目 `unverified`、同步 `pending`。恢复动作见 [Issue #7 看板交接](handoffs/2026-10-21-issue-7-projects.md)

本页只记录全项目阶段和关键限制；具体任务进度以 Issue 和 PR 为准。

## 2026-10-27：全功能分块与二维pin增量里程碑

最新失败确认：llaccel SYSTEM完整C的13184pin已实际迁移，全部13507信号pin回读匹配；26pin/44矩形对与不变PG同层直接相交。保留检查点及逐矩形证明后，仅停止新无效试验92369，未完成全C布线/RC/STA。其余父层、控制和GDS作业继续。新增严格GDS中VECTOR原始/8pin C均36项天线；openSYS原始缺4个fakeram，诊断deck52486项（含46014项WELL），均非完整规则通过。

完整C增量：GEMM原全C有2项电容失败，恢复对应18pin整字节后3021pin在内部；MXU原全C有3项VDD短路/5项电容失败，保留33pin lane并修复2处内部点后1931pin在内部。两修订独立native DRC0/全块所检几何连通通过，现有边界模型下违规报告0，完整资格仍未通过。VECTOR1022及openSYS1768全C已真实布线，native/几何门槛通过但时序失败；llSYS完整C继续运行。新受控父层按用户授权补建，原历史handoff未知不改写；openTPU完整6618端点图和双电源连通已通过，父层路由进行中。严格GDS已暴露GEMM天线及ACT/MXU缺失fakeram视图，失败单列。

匹配全组原XY重布线对照显示，GEMM/MXU修订C真实线长分别约+1.19%/+4.30%，当前优先保留边界；ACT完整C约−6.40%，setup略差，不泛化为系统或面积收益。已通过工程门槛与是否值得迁移分别判断。

[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126)进行中：[PR120](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/120)未合并head4f91e098为起点，复用Issue55完整SYSTEM包装，补齐两系统六块、18项功能归属和全部接口连接矩阵。
六块24,767原始信号pin、74,301行A/B/C候选覆盖通过；其他四块对照图、端点依据、实际金属/PG/OBS筛查和逐pin数据已生成。
六块C已实际接入：ACT完整740pin，其余五块各8pin局部；独立clean native DRC=0、全块多端OpenDB几何连通均通过。VECTOR与两个SYSTEM独立边界时序/电气失败保留。ACT同组C相对原XY重布线线长−6.40%、via−1.70%，setup略差，外框未变。其他五块完整C进入独立尝试，失败与待验证独立记录。
完整父层接入/目标层、完整规则/GDS/LVS、系统RC/STA及电气资格尚未完成，不能把候选覆盖写成物理全部完成。详见[中文入口](experiments/issue-126-full-pin.md)。原参考包、PR120工作树、Issue55/121活动任务不修改。

进一步严格GDS探针：ACT原始/完整C均因两个fakeram缺失GDS而合并失败；未豁免缺失单元。未修改的FreePDK45 deck在不完整诊断布局上分别678/770项（当前均天线类别），保留原始失败，不将native DRC0写成完整规则通过。其余块严格GDS/全C试验继续执行。

## 2026-10-28：Issue126继续真实接入与共同底座

用户确认六块资源并集和共享实际固定预连。本轮已取得ACT访问窗口版全重布线native0/4819网连通、真实研究12层小例及独立检查；旧两父层分别11项DRC/GRT拥塞失败，LL全C新PG修订仍在完整布线。共同M1–M10尚未实现/冻结，两完整M11/M12功能未实现，不以候选/作业提交替代。详见[新接续交接](handoffs/2026-10-28-issue-126-common-base-continuation.md)。PR129持续草稿，Issue126进行中。

最新接续：ACT/GEMM/MXU/VECTOR/openTPU SYSTEM五块新完整窗口视图native0/所检多端连通通过，11260个实际pin与完整表一致；GEMM3/MXU1电容、VECTOR及openSYS setup/hold/电气仍失败，llSYS新窗口未终态。ACT新增父层M10接点修复后256-bit实际接入native0、860网/双PG通过，原叶M5/M6不变；随后同研究I/O条件下实际RC/STA仍有hold和电气失败、604零长度网未标注，不视作签核。共同构造网表已原生链接34954端点/17686逻辑分量，尚未布局、预连或冻结；研究12层小例不代替完整系统。新增4对PNG/SVG和阶段HTML已上传，原失败/旧发布命名空间保留；电气/时序ECO未解决的失败和成本单列，不以局部成本撤回内部方案。

Issue126晚间后续终态：GEMM/MXU定点ECO均已native0/所检全块连通，重提取setup/hold正且cap3/1未再列违例；标准单元bbox面积分别+1.596/+0.266um²，完整规则/形式等价仍待验证。两份实际物理/研究时序视图eco_views/r02已导出并核对全部3753/2172位及SPEF重放，不能替代制造签核。VECTOR估算器与SYS工具崩溃仍失败；SYS92778复用检查点独立合法化。共同底座/两完整上层功能仍未实现。


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
