# Issue126：658真实diode终态、全网增量接线证据及770边适配

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
