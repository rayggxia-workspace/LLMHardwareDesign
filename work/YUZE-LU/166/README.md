# Issue166 — R local-state implementation

Independent branch task/166-r-local-state, based on frozen PR160 delivery 9b3e7248.
Existing accepted R256, PR160, control/S worktrees and remote jobs are unchanged.

Scope: 16-row lane-local DFF state tiles; two versions; 1R1W; registered read
selection/data/merge; shared host read path; original integer arithmetic.
R256 and R1024 require separate complete physical acceptance at original 300MHz.
R256 standalone macro is fully qualified and locally received; see [report](R256_QUALIFIED.md). R1024 remains unqualified and work continues. Dated snapshots below are historical.

First component contract: read E0 acceptance → E1 local selection → E2 local data
→ E3 output. Write E0 acceptance → E1 local write selection/data → E2 storage.
Simultaneous E2 access is read-before-write. Reset invalidates control, not state.

References:
- https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1p_adv.sv
- https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1r1w_adv.sv
- https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/ram/README.md
- https://yosyshq.readthedocs.io/projects/yosys/en/0.41/cmd/memory_map.html

Registration: management-hub PR5 pending. No board.json: board unverified,
synchronization pending; administrator/reviewer unassigned.

## 2026-11-03T07:34:05.018564+08:00：#166 标准物理视图往返通过，完整原生与R1024继续

固定上游2eba27b2 checker已在独立Slurm237真实构建成功，binary SHA944848ca2b5181d570e21841fa9c54e53c062b4ebea74cd3955a6c5b30343ee0；使用官方//:tarfile同一CLI目标，保留153因pandoc缺失失败的文档安装证据。228构建后完整源码复核及6组新旧真实规则正反例通过，但源ODB0.141/工具0.139格式不兼容，整块明确失败。未改二进制schema头、源ODB或工艺规则。

249由原工具导出全部LEF库与完整DEF，再由固定checker读回、重新导出。全部LEF及DEF的28456945个字段严格核对通过，数值改写0；仅规范化无序DEF GROUP成员的输出顺序，成员/重复项/全部属性完整比较，其他规则/层/形状/坐标/网络/顺序不排除。完整导出DEF SHA6c0d07b183b6963b5c6677f86255cd0b5b271ce51ae075c51c5caefbcabab4a8与111原最终DEF一致。250/95612重新完整源码核验、全部6组规则对照、相同视图全die检查；251/95613总门、252/95614最终绑定包在其后。原容器095/101/116检查保留。R256111虽已有完整原GDS0、300MHz时序/电气0、精确最终192/192，仍未完成全部资格和本地整包实收。

R1024原179最终提取setup−55.3353ps/2、hold−77.6225ps/600、cap93/slew1，不合格；不能以DRT0或修复器中间hold0替代。202新物理宿主规则的实际GRT初值setup+60.0175ps、hold−9.6807ps/1、cap26/slew1，优于旧179 GRT253/110/5，但仍未过门。192/202均继续实际GRT RC闭环→DRT→最终RCX，未签发资格。253–255绑定202完整原生/总门/包，256–258对应192候选。精确最终功能220→221→222仍依赖205原300MHz/电气前置门，数组每项16CPU、最多36项动态补位；224真实少186项的负例被完整收集器拒绝，失败回执已实收。

实际作业、取消前命令核验与依赖变更见ATTEMPT_SCHEDULER_INDEX.json；所有失败和源保留。取消仅限本任务尚未运行的旧代码链。当前并发受真实依赖和Slurm可用槽位限制，没有宣称内存不足。Issue166 in_progress、PR167 draft；登记PR5 pending、无board.json看板unverified/同步pending，管理员/审查人待指定。不改main、旧交付或其他任务，不自行合并，持续双容量全部成功与六文件/版图/整包SHA实收。


## 2026-11-03T08:14:40.200867+08:00：#166 R1024按真实失败路径和负载约束继续

R256完整资格/本地实收保持，见work/YUZE-LU/166/R256_QUALIFIED.md。R1024尚未合格。270对179最终SPEF只读诊断：全部600个hold失败中519个来自15外部输入、81个内部；两条setup失败同源dot[3][5]→failed/rsp_error长组合路径。271从同一165 CTS按这15个实际输入添加53个延迟单元和15个驱动，实际审计及输入路径绑定已实收；内部/最大延迟失败不被忽略。272–280依赖同一候选完成全部物理/几何/192最终用例/包。260分离setup150ps优化目标与hold修复setup保护0ps，保留hold60ps目标与逐轮真实ODB/SDC/路径；192/202老对照继续。原最终300MHz/IO与全部非负/零计数门不变。

281用完全相同RTL SHA进行显式驱动BUF_X2、每组合边界50fF、时延目标3000ps的ABC综合对照；容器实际help先核验参数，官方依据https://yosyshq.readthedocs.io/projects/yosys/en/0.47/cmd/abc.html。综合/完整选择锥通过，mapped JSON SHA583ccecb4aca725d02e9424beed4d03d625bf2ea30563c9659d81920fab9d4be。面积790663.188µm²，比原703543.134约增12.4%；ABC无布线WireLoad时延2844.62ps不是物理通过证据。282严格全状态ABC等价与283实际1800µm/0.35/原16区布局并行，284新CTS→285完整路由→286–294全部验收/最终192数组/包；不借用原映射的证明或最终功能资格。

当前在依赖允许时运行独立物理/形式任务，最终功能数组每项16CPU、最多36个动态补位，8个允许c96节点、每节点最多6个；实际proof/placement及最终时序依赖未完成，未声称内存限制。完整源、作业和取消回执见ATTEMPT_JOBS/ATTEMPT_SCHEDULER_INDEX，所有失败与原始源保留。Issue166 in_progress、PR167 draft；登记PR5 pending、看板unverified/同步pending、审查人待指定。不动main、旧合格包或其他任务，不自行合并，继续R1024完整成功。


## 2026-11-03T08:50:12.484755+08:00：#166 依据缓冲上限失败改为有限批次后重测RC

R256完整资格及816文件本地实收保持，R1024仍未合格。192/202真实失败均为RSZ-0060：在同一272340/D端点约14ps停滞，分别插入68374/68342个hold缓冲达到上限。完整原日志保留，失败回执、原日志SHA及末尾见work/YUZE-LU/166/evidence/CLOSURE192_202_FAILURES.json。260/271分离setup保护后也观察到相同端点停滞，作为对照保留。

297/95673、298/95674从同一165 CTS独立执行每批最多200次hold修复，再合法化/真实增量全局布线/重测RC；298另含270实测输入修复。实际容器296/95672帮助已确认-max_iterations，生成策略绑定192/202失败回执与完整日志SHA；最终原300MHz/IO及全部零门不变，达到迭代上限不算通过。source297-runners.tar冻结20742cf0代码，正式生成钩子和实际策略随包绑定。300–308对应297、309–317对应298、318–326对应新映射299，均串联原完整GDS、完整原生、几何、严格最终LEC、精确最终192数组与交付包。

281新映射的283布局实际成功，面积838393µm²（placement统计，不是最终面积）。282完整状态等价仍在实际solver；284新CTS不必等形式证明，核验283成功及实际3_place.odb后仅修改调度依赖，源码和原SUBMISSION不改，DEPENDENCY_REPLACED记录保留。最终294/326包仍必须接收282完整证明。285原优化和299有限批次对照均依赖284真实CTS。新旧映射不借资格。

约08:18起主登录新SSH认证停顿，08:38已通过已知主机node15正常SSH通道恢复，只改变连接路径，账号/主机校验/作业未改。已关闭本任务冗余本地重连循环。16个依赖192/202明确失败的尚未启动旧下游作业，逐项核验Command/状态后取消并保留完整scontrol/原因/失败源SHA；不按时长取消，不动其他任务。最新调度回执继续同步。动态最终数组每项16CPU、最多36任务，8个允许c96节点内每节点最多6项；限制来自真实依赖/槽位，无内存不足声明。

Issue166 in_progress、PR167 draft；登记PR5 pending、无board.json看板unverified/同步pending，管理员/审查人待指定。不改main、PR160旧包，不自行合并，继续直至两容量完整成功及本地整包实收。


## 2026-11-03T09:04:45.884413+08:00：#166 新映射全状态等价通过，继续最终物理闭环

282/95656于08:58:44明确UNSAT/IDENTICAL：176757输入、177228输出全部对应、差异0，全部D/CK/Q/QN及原端口边界完整。实际帮助、原源码/映射/Liberty/工具SHA与真实D/CK/输出故障对照绑定；receipt SHA23a2ee663016cce553ad8e30f306fa73b624a87109281de4a182f53751d581ac。证据work/YUZE-LU/166/evidence/mapping-proof282已本地按原输入/日志/控制SHA接收。仍信任Yosys降低，不声称通用行为RTL顺序SAT已通过。此证明不替代最终物理网表192项和物理LEC。

284新CTS完成，285及299从该真实CTS独立布线；297/298原映射有限批次对照继续。260分离setup保护的原无界hold对照也实际RSZ-0060失败，原完整日志SHA/末尾与失败回执见evidence/CLOSURE260_FAILURE.json。仅在确认260真实失败、逐项核验Command/PENDING后取消261–269未启动下游；连同192/202旧下游的25份取消前scontrol/失败源SHA已同步ATTEMPT_SCHEDULER_INDEX，原源/日志保留。271原实测输入无界对照保留。每批200次只限制优化器工作量，之后重新合法化/增量路由/测RC；原300MHz/IO、最终非负setup/hold、时序电气及完整DRC零门完全保留。

R256完整验收及816文件实收保持；R1024仍未合格。300–326串联全部物理、严格最终LEC、精确最终192用例数组、源索引/六文件/真实版图和本地整包实收，依赖未过不签发。节点内16CPU独立任务，最终数组最多36项动态补位，8个允许c96节点、每节点最多6项；当前限制是实际物理依赖/可用槽位，无内存不足声明。

Issue166 in_progress、PR167 draft；登记PR5 pending，看板unverified/同步pending，管理员/审查人待指定。不改main、PR160或其他任务，不自行合并；继续至R1024完整成功。


## 2026-11-03T09:57:32.350526+08:00：#166 R1024新流水完整RTL回归通过，修正hold批次解释

327/95703完成全部384项：256默认参数及1024 FINALIZE_PIPELINE=1，分别三初态×(63数值+1协议)，全部通过。六份原始init回执已本地实际下载并按RTL327_SUMMARY.json逐项SHA核对。256默认路径数值/周期严格等于010；1024只给op4/op5增加1周期，数值、检查数量和逐用例预期周期差全部相同，每初态总82395584周期（比010多16312）。新增512bit舍入寄存器隔开179实际dot到failed/rsp_error关键路径，不改变数值舍入规则。新328综合及选择锥通过，329完整全状态证明和330独立布局继续；331 CTS后332原hold目标对照及347新目标物理并行。当前源RTL并非已合格R256包的冻结字节，不能转移R256物理资格。

更正早先“每批最多200次”的解释：实际297/298超过数千端点操作和缓冲，272340/D停在约14ps；上游RepairHold.cc在完整repairHoldPass外检查max_iterations，内部逐端点循环只检查总缓冲上限。343实际工具Tcl参数传递及346真实链接小网表参数探测已记录；帮助存在不证明实际端点工作量有上限。297/298按这一实测语义问题替代，原日志前缀/SHA、逐项Command与取消前scontrol保留，不是按运行时间取消。新的348/349已运行，原285/299对照保留。

347/95723（新流水）、348/95724（原映射+270实测15输入）、349/95725（281负载约束映射）将hold优化目标设为0，停止追逐正60ps裕量；setup优化目标150ps，原300MHz/I/O及最终提取setup/hold非负、全部时序/电气/DRC零门不变。最终提取仍可能失败，必须据实继续修复，不因GRT通过签发资格。350–358、359–367、368–376各自包含完整GDS/原生、选择几何、严格最终LEC、精确最终192项及六文件/版图/绑定包。前者冻结source347(730d6e23)；后两者source348-oldrtl显式绑定730d6e23 runners和c7c247旧RTL，archive SHA7ed193b2c08e7d60b62ad0e11bbb93c3f597134cb88fd4151d66ddd83f1933a1，避免给旧映射混入新的源字节。

271实测输入无界对照已实际RSZ-0060失败，完整失败回执/原日志SHA留档；仅其9个未启动下游逐项核验后取消。342相同1024流水RTL/参数/最重GDN用例的单CPU实测77.569s，6316032检查/17630211周期严格正确；该测量不是完成的成对MT耗时比较。327已全部完成，不重跑；未来RTL独立用例可用96个单CPU槽，编译仍16CPU/构建。物理/最终mapped测试保持16CPU/项，最多36项动态补位，允许8个c96节点、每节点最多6项；当前限制为真实依赖/可用槽位，没有内存不足声明。

09:39常规mgt SSH已恢复，不改认证/主机检查。R256111/252完整资格及816文件实收保持；R1024仍未合格。Issue166 in_progress、PR167 draft；规则rayggxia-project-collab1.0.0；登记management-hubPR5 pending，缺board.json看板unverified/同步pending，管理员/审查人待指定。不改main、PR160旧包或其他任务，不自行合并，继续至R1024完整成功及本地实收。


## 2026-11-03T10:42:39.415359+08:00：#166 新流水完整状态等价通过，继续最终物理验收

R1024新流水329/95705于10:36:27明确UNSAT/IDENTICAL，177573输入/178044输出全部对应、未匹配0；receipt SHA1a193ccde79829e9dbe70595b63a8c8bd8fbacdfe2198ceecb005cd598017fca。实际回执、完整log、config和真实D/CK/输出故障对照已本地按原SHA接收，见work/YUZE-LU/166/evidence/mapping-proof329。映射328 SHA42bb3f1354d66d2a82e763bc0bc2eeebe6e4f5ce592e35939aa862323683de63；继此前完整384项RTL/精确周期差通过，330布局及331CTS已完成，332原目标/347新目标物理并行。347、348、349仍在实际全局布线/电气闭环，R1024尚未合格；全部原300MHz/I/O、非负提取setup/hold和零时序/电气/完整DRC门保持。

377/95758、378/95759、379/95760分别在347/348/349真正生成最终ODB/SDC/SPEF后只读列出全部实际失败路径，便于继续定点修复；不把空闲等待当作通过。062/95346早期R256CTS对照，仅在读回111/252完整资格、816文件本地实收与包SHA一致后核验Command及容量取消，原源/日志和取消前scontrol保留，不影响任何1024或其他任务。实际源码和调度证据已更新；当前代码注释明确200为工具外层请求，不能宣称限制端点工作量。节点内独立16CPU任务动态补位，获准8个c96节点，限制来自实际依赖/槽位；未以虚构内存不足降低并发。

R256111/252完整资格及本地整包SHA实收保持。Issue166 in_progress、PR167 draft；规则rayggxia-project-collab1.0.0；登记PR5 pending、缺board.json看板unverified/同步pending，审查人/管理员待指定。不改main、PR160旧包或其他任务，不自行合并，继续至R1024完整成功及本地交付实收。


## 2026-11-03T12:09:07.399734+08:00：#166 实际最终RCX定位89条hold失败，定点修复继续

348/95724已完成详细布线，DRT0，实际最终RCX setup+0.0612141ns、hold-0.0311528ns/89条，setup/cap/slew违规0；因此明确未合格。361最终构建门及365原生门按原时序要求拒绝，最终192项未执行，不能借GRT零违规宣布通过。378/95759按确切最终ODB/SDC/SPEF列全89条路径，其中6条外部起点；380/95779对全部端点测最大路径裕量通过。原348完整flow/metrics/回执、378路径/报告及380实测预算共18份文件已实际本地下载逐SHA核对，见evidence/closure348/RECEPTION.json。

关键240026/D同时setup仅61.214ps、hold-13.996ps，不能盲目统一插三级。按实际最大路径预算，89端点共207个CLKBUF_X1，唯一紧端点插一级，其余按实测短路径插有限链；40ps是优化储备而非验收阈值，不足setup余量时不强追储备。新增单元逐个记录实际名字、PG、fence/group与坐标，插入阶段原布局锁定不动；最终全流程依然必须非负setup/hold及全部零违规。

381/95782从原165 CTS重跑，392/95795从348确切最终拓扑重跑，两路已实际完成207单元插入并通过插入阶段合法性检查。392保留已有IO驱动/时钟/电气修复，先核对诊断ODB/SDC/SPEF SHA，删除fillers/常规走线后重新完整路由、RCX及所有验收，不重复插IO或继承资格；source_final明确入源链。382–390与393–401分别排定全部物理、几何、严格最终等价、192最终单元数组及包；391/402再次按真正最终结果诊断。冻结380/381/392混合包明确保留c7c247旧RTL、分别绑定新runners，原映射14/完整证明047不混入流水新RTL字节。

347新流水已在实际GRT round3时序/电气零违规（setup153.875ps），349负载约束映射GRT也零违规；两者详细布线继续，不冒充最终通过。仅在348真实负hold且361实际拒绝后，逐项核验Command/PENDING取消362/363数组/364/366/367五个未启动下游，失败源/SHA与取消前scontrol保留；未按时长取消运行任务，不动其他任务。允许8个c96节点、节点内独立16CPU任务，最终数组%36动态补位；限制来自真实依赖/槽位，未虚构内存不足。

R256111/252完整资格及816文件实收保持，R1024尚未合格。Issue166 in_progress、PR167 draft，不改main/PR160旧合格包，不自行合并；持续到两容量完整成功和本地整包实收。规则rayggxia-project-collab1.0.0；登记PR5 pending，看板无board.json为unverified/同步pending，管理员/审查人待指定。


## 2026-11-03T12:47:55.330405+08:00：#166 三条最终RCX均定位为hold失败，有限修复四路继续

三条真实最终结果均未合格：348原映射 setup+61.2141ps/hold-31.1528ps/89条；349负载映射 setup+15.6559ps/hold-36.1648ps/28条；347新流水 setup+86.5361ps/hold-33.3485ps/58条。三者setup/cap/slew与DRT违规均0，但原非负hold门不容省略，最终构建/原生门均按实际hold拒绝，三组最终192项未执行。378/379/377完整最终SPEF路径与380/403/415逐端点最大路径预算全部完成。三个候选各18份原flow/metrics/回执/路径/预算证据，共54份文件已实际下载逐SHA实收，见evidence/closure348、closure349、closure347各RECEPTION.json。

381/95782原CTS+207单元、392/95795原最终拓扑+207单元、404/95814负载映射最终拓扑+66单元、416/95827新流水最终拓扑+129单元，四路实际插入审计与插入阶段合法性均已通过，继续完整布线/RCX。原348唯一紧端点240026/D只有61.214ps setup、-13.996ps hold，因此按实际预算插一级；403的28端点最小setup1.18399ns，415的58端点最小setup0.495479ns，都满足有限链预算。所有预算只是修复规划，绝不替代原300MHz/I/O、最终非负setup/hold和零时序/电气/完整DRC门。

404的405–413、416的417–425已串联完整GDS/原生、几何、严格最终等价、精确最终192数组和六文件/实际版图/源索引包，414/426只在真正最终ODB/SDC/SPEF生成后再次诊断。416 archive SHA7c5dc6886af2dedc5e52950dce1f772efcf4fd3120bdae7d1661c2c5813249e0，保留已证明e49df957新流水RTL，绑定328映射/329完整状态证明；404沿用source392旧RTL包，绑定281映射/282证明。两者均不重复插IO/时钟单元；重新完整路由与提取，资格不继承。392当前GRT round0时序计数0，仍3项cap/1项slew，不当作最终通过；381仍在实际GRT闭环。

332原60ps全局hold目标实际RSZ-0060失败，完整失败源/log SHA留evidence/CLOSURE332_FAILURE.json；仅核验Command/PENDING后取消333–341九个未启动下游。347和349真实最终hold失败及各自构建门拒绝后，只取消353/354数组/355/357/358、371/372数组/373/375/376两组各五个未启动下游，逐项取消前scontrol留档；不按时长取消运行任务。旧285/299仍保留对照。348几何360通过，完整原GDS规则仍在实际运行，不把进行中描述为通过。

允许8个c96节点；物理16CPU/独立任务，最终数组16CPU/项、%36动态补位。仅真实依赖/槽位约束，未虚构内存不足或更改单账户/其他任务。R256111/252完整资格和816文件实收保持；R1024尚未合格，继续到全部门成功及本地整包实收，不动main/PR160旧合格包、不自行合并。Issue166 in_progress、PR167 draft；规则rayggxia-project-collab1.0.0，登记PR5 pending，看板缺board.json为unverified/同步pending，管理员/审查人待指定。

