2026-10-30 03:38 CST：V410/93585/node16和R404/93555/node21均完成CTS进入route；新30原始及V309/R308源Git与远端SHA核验。CTS setup/hold WS分别−0.0163065/−0.235032ns、−0.00195399/−0.0930063ns，仍非最终通过；内部LEC分别51206/51195、292950/292936，UNSAT/IDENTICAL/diff0，实际4984/27414时钟网none。V实际hold_margin0.08/R0.02及未修复全部hold警告原样保留。旧V400的415几何10原始/四标记23矩形和已查看图，416九原始/539行两种API形状一致；417两副本编码对照17原始/10大文件留服务器，只加被原wire包含RECT、网表不变/完整DEF单RECT差异，但433项报告仍逐字节相同，明确否定重复RECT修复，未修改新V/R或原ODB。旧401独立严格LEC新16原始/308源与同一最终来源绑定通过51206/51195、diff全0，旧时序/DRC拒收保持，完整GDS deck仍运行。M/S/T保持，V/R最终未齐；本Issue最大8、默认6×16动态补位，仅真实依赖/RAM限制，未取消EDA。目标active/Issue121=in_progress/PR122=draft；登记pending、看板unverified/同步pending、审查待指定。

2026-10-30 03:20 CST：旧V401/93578最终网表三初态功能通过，各566999检查/414906拍；11原始+2最终来源文件、308源Git/回执和实际400最终V/ODB绑定核验。独立原生全芯片DRC已完成并出现433项（Metal Spacing432/NS Metal1；M2=266/M3=167），另8原始快照；详细布线5_route_drc.rpt为空不能替代此门。414在R404已有93555/node21空闲16–31/32–47核并行只读route/fill，两项COMPLETED/0、9原始，输入ODB前后SHA不变，route/fill/final报告逐字节相同；违规已存在于route，具体根因待核实，不作RCX归因或豁免。旧V400负时序/DRC拒收保持，完整GDS deck/严格LEC仍运行。V410/93585/node16已完成place进入CTS，R404/93555/node21仍CTS内部等价检查；原任务继续，M/S/T保持、V/R最终未齐。目标active/Issue121=in_progress/PR122=draft，登记pending、看板unverified/同步pending、审查待指定。

2026-10-30 02:56 CST：413准入已实际部署，PID3818917，控制源33bb0916/配置bfee9fd7；24远端文件/六归档、正反控制、实际UID/cmdline/start ticks及两轮状态核验。只替换407轻量控制/退休未分配402，无EDA取消；V401/93578原独立验收继续。V410/93585/node16已实际RUNNING，源33bb0916/归档ec978042，7启动原始/309源Git与远端SHA核验，实际HOLD_SLACK_MARGIN=0.080、die1250²、synth完成/floorplan运行。411最终门/六文件/完整几何、412全端口/RC仅封存，待真实前置。R404/93555/node21完成place进入CTS，实际利用率33.4%；405/406等待。408八检查和409七测量已全通过/正常结束，模型80候选字段不变；V400最终负时序仍拒收，M/S/T保持、V/R最终未齐。目标active/Issue121=in_progress/PR122=draft，登记pending、看板unverified与同步pending、审查待指定。

2026-10-30 02:50 CST：408/93581八项全PASSED并自然COMPLETED，mapping413900单元/25531DFF，10原始/309源Git与回执核验。409/93583/node17七测量全PASSED/COMPLETED，源7435f406/归档f1c2bb15；51原始/38输出绑定/309源Git输入核验，另5启动原始/309远端源SHA。135有限+78公共测量逐字段同379，RESOURCE-BUDGET八模型80候选model字段不变，只重绑当前新源。选择V410全新六阶段→411最终门/六文件/完整几何→412全端口/RC；尚待部署，413准入计划替换407轻量控制。当前407仍运行，R404原任务继续、V401原验收继续，均不取消。V400最终时序拒收保持；M/S/T接收，V/R未齐。目标active/Issue121=in_progress/PR122=draft，登记pending、看板unverified与同步pending、审查待指定。

2026-10-30 02:43 CST：新408/93581/node16已实际提交并运行，源c58cb834/归档8b172433，六个互不相交16CPU槽动态补位。七项新RTL检查已通过：三初态各566999检查/414906拍、42公共/36扩展、组合/延迟、264位原carry/RNE和130位新完整S128归一化恒等式证明及实际负例；55原始/42输出绑定/309源Git输入核验，另5启动原始/309远端源SHA核验。mapping第八项仍运行，不能计新物理通过。新409测量尚待部署；V400最终setup−0.0965326/hold−0.0326332ns不接收，401/93578物理门已FAIL，原完整DRC/最终功能继续；402受前置限制。R404/93555原place继续；M/S/T保持。目标active/Issue121=in_progress/PR122=draft，登记pending、看板unverified与同步pending、审查待指定。

2026-10-30 02:36 CST：V400/93529自然COMPLETED/0，原生全六阶段/RCX、提取后VDD/VSS连通、route DRC0及最终内部LEC UNSAT/IDENTICAL51206/51195通过；21原始与308源Git/远端SHA核验。但最终setup WNS−0.0965326/TNS−5.59027ns、hold WNS−0.0326332/TNS−1.27177ns，仍不接收。setup映射product4bit0→output_mem44bit22，第一min cmd_index2→rsp_data52。401已自动提交93578/node23，原验收继续；402等待。准备同周期/全S128精确norm_merge_rne及V专用hold修复裕量0.080ns，新408八项并行证明/回归/映射尚待实际提交，全新物理与最终验收不可省略。R404/93555继续place，已完成一轮117717缓冲修复并恢复迭代。M/S/T保持；目标active/Issue121=in_progress/PR122=draft，登记pending、看板unverified与同步pending、审查待指定。

2026-10-30 01:31 CST：V400/93529/node23 GRT各层拥塞0，总需求5471082/资源9848678=55.55%，已开始详细布线优化；setup WNS/TNS舍入−0.00ns且关键路径0.00ns VIOLATED，仍未最终300MHz通过。19原始/308源Git与远端SHA、4983无NDR时钟网/M4–M10调整实际TSV核验，最大point_op[1]→point_rounded[1][118]、最小cmd_index[2]→rsp_data[74]。R404/93555/node21 floorplan运行，6原始配置读回die2330²/映射0.28/密度0.35、input.v与344逐大小/SHA一致，功能不缩减、无物理阶段继承。401/402及405/406等待真实前置，407控制保持；M/S/T接收，V/R最终未齐。目标active/Issue121=in_progress/PR122=draft，登记pending、看板unverified与同步pending、独立审查待指定。

2026-10-30 01:19 CST：407准入已实际部署，源d1aadb3e/配置72a26b71、PID3668320；24远端文件/六归档、控制正反例、实际UID/cmdline及两轮状态核验。只替换403轻量控制/退休未分配345/346，无EDA取消。R404已实际提交93555/node21，源d1aadb3e、归档f9b9db75；5启动原始文件与308源Git blobs/远端实际SHA核验，全六阶段待实际完成。405最终门/六文件/完整几何、406全端口/πRC待真实前置。V400/93529/node23继续route，401/402保持。R344原GRT失败保留，V/R最终未齐，M/S/T接收保持。默认6×16动态即完即补，仅真实依赖/RAM限制；本Issue最大8含pending/unknown。目标active/Issue121=in_progress/PR122=draft，登记pending、看板unverified与同步pending、独立审查待指定。

2026-10-30 01:16 CST：R344/93237/node21自然FAILED/1，原GRT完成额外30/30后GRT-0116；总使用111.11%，M1/M2为148.10%/135.92%、总拥塞3767456。12原始小文件及307源Git/远端SHA、失败回执输入核验；13.2MB拥塞报告和原失败/CTS ODB留服务器并核对大小/SHA。选定同一基础R映射利用率0.28/放置密度0.35，外框1950→2330um，原生默认宽时钟/M4–M10调整0.20；404全六阶段→405最终门/六文件/完整几何→406全端口接口尚待部署，407准入尚待部署。RTL/342/343测量、全部数值周期和300MHz门保持。V400已CTS完成并route，16原始/308源核验、修复LEC UNSAT/IDENTICAL51206/51195、4983时钟网none读回；CTS setup−0.07/TNS−0.16/hold−0.25ns仍非最终通过。M/S/T接收保持，V/R最终未齐、目标active/Issue121=in_progress/PR122=draft，登记pending/看板unverified与同步pending/审查待指定。

2026-10-30 00:29 CST：403准入已实际部署，源62e3e577/配置55fc2ed7、PID3589806；24远端文件/归档、正反控制、UID/cmdline及两轮读回通过。仅替换383轻量控制/退休未分配381/382，无EDA取消。V400已实际提交93529/node23，源62e3e577/归档d3ee6032；5原始启动文件与308源Git blobs/远端实际SHA核验。原生CTS apply_ndr none，全新六阶段运行；401最终门/六文件/完整几何及402全端口/πRC等待真实400/401。R344/93237/node21继续GRT extra28/30，345/346待实际前置。M/S/T接收保持；V/R仍未最终接收，300MHz及全部数值/周期/PG/DRC/RCX/功能/LEC门不放宽。103原始诊断精确Git字节核验通过。目标active、Issue121=in_progress/PR122=draft，登记pending、看板unverified/同步pending、独立审查待指定。

2026-10-30 00:22 CST：V380失败的只读384–399诊断已归档103原始文件（大文件留服务器索引）。390提取前PG通过，391提取后原坐标PSM失败；397实际getShape的M3宽140→1600 DBU、与VSS交集精确匹配，路径迭代器几何并集却未变。原ODB保持；389/394/395 API失败和385解析失败原样保留。选定同一V改原生CTS apply_ndr none，399实际API/启动前SIF核验通过；400全六阶段→401独立最终门/六文件/完整几何→402全端口/πRC尚待部署，403控制尚待部署。修正native V选择器由旧374明确指向400，不转移旧资格。RTL/378/379保持，300MHz/数值/周期及全部PG/DRC/RCX/STA/功能/LEC门不放宽；R344原任务继续GRT27/30，M/S/T保持接收。目标active/Issue121=in_progress/PR122=draft；登记pending、看板unverified/同步pending、审查待指定。

2026-10-29 23:48 CST：V380/93441/node17已自然FAILED/1：finish的PSM检测metal3上VSS-clk短接，坐标(525.910,340.150)–(526.035,340.270)um；PSM-0043/0069，最终RCX时序报告未生成，不能以route计数0/内置最终LEC通过放行。15原始文件/failed回执输入与归档核验，原ODB保留。新只读诊断384在现有R344/93237/node21空闲16–31核实际启动（srun PID3519346、step153），无新增allocation，检查真实金属/通孔与原生DRC，尚待结果。381/382被真实失败前置拦截，不重投380、不关闭PG检查；R344原任务继续、M/S/T保持接收。目标active/Issue121=in_progress/PR122=draft，登记pending/看板unverified与同步pending，独立审查待指定。

2026-10-29 23:31 CST：V380/93441/node17已完成route、原finish内置最终LEC求解中；新13原始CTS/GRT文件与308源Git blobs/远端实际源核验。CTS setup−0.07/TNS−0.16/hold−0.25ns，最大cmd_index2→stats_sumsq1bit40；GRT setup报告−0.00（仍负）/TNS−0.01/hold+0.02ns，最大low_product0bit0→output_mem93bit7，不能作为最终通过。旧375完整原生/未修改GDS DRC0、严格LEC UNSAT/IDENTICAL51206/51195、diff全0通过；11原始文件与同一final-source及最终功能回执绑定核验。旧374最终−0.1232ns仍不接收，不向380转移。R344/93237/node21已GRT extra26/30，原任务CPU持续增长；345/346及381/382待真实前置。M/S/T保持，目标active、Issue121=in_progress/PR122=draft；登记pending/看板unverified与同步pending，独立审查待指定。

2026-10-29 21:40 CST：383准入已实际部署，代码5a6e0be8/配置cdcfc85f，PID3315105；24远端文件/归档、正反控制、实际UID/cmdline及两轮读回通过。仅替换377轻量控制/退休未分配376，无EDA取消。V380已实际提交93441/node17并RUNNING，2026-10-29 13:38:26 UTC，源5a6e0be8/归档b6854770；378七项全通过（映射413216单元、25531DFF），379七测量全通过。381最终验收/382接口等待真实前置；原375仍正常收尾，物理门因374最终−0.12ns失败。R344/93237/node21全局布线extra20/30，原任务继续；M/S/T接收保持。实际本Issue提交前6个、提交380后7个allocation，最大8，默认6×16依赖/RAM约束动态补位。所有当前V/R最终资格仍未齐，Issue121=in_progress/PR122=draft，登记pending、看板unverified/同步pending、独立审查待指定。

2026-10-29 21:35 CST：378新源七项检查（含综合映射）全部通过；379在R311/93125/node18现有allocation内七测量通过，135有限场景+78公共端口测量同373，53原始/39稳定/308源核验。实际预算重绑379，八模型80候选全部model字段不变。380/381/382全新物理/最终门/接口已冻结准备但尚未分配；383控制器尚待部署。旧375物理门因374最终负时序失败，DRC和最终网表功能检查继续正常运行。R344原任务继续；M/S/T保留。Issue121=in_progress，PR122=draft，登记pending、看板unverified/同步pending、审查待指定。

2026-10-29 21:24:34 CST：378已在R344/93237/node21已有allocation内启动，父0–15、五个16CPU子槽16–95动态补位，无新增allocation。六功能/算术项通过、映射运行：三初态各566999检查/414906拍、公共42/扩展36及组合/延迟全部测量同367，实际264bit证明和单bit负例通过；47原始/35稳定/308源核验。379采样将绑定378新公共回执，380→381→382全新物理/最终门/接口及383准入尚待准备；本地选择器已改，远端377仍保持原配置。V374最终−0.12 ns不接收，R344继续原任务，M/S/T保持。目标active、Issue121=in_progress/PR122=draft，登记pending、看板unverified/同步pending、审查待指定。

2026-10-29 21:13:54 CST：V374六原生阶段完成，最终RCX setup−0.12 ns/TNS−37.33 ns，product[3][4]→stat_block_sq[66]，300MHz未接收；流程内最终LEC UNSAT/IDENTICAL与路由违规0不替代独立验收。14原始文件及源/input.v/receipt输入绑定核验。选定同一基础V的U80平方和三层树改用既有完整128位分组进位，保留U80节点、周期、尾块mask与全部数值/接口；新378验证尚待提交。已启动旧后继正常收尾，R344继续全局布线。M/S/T接收保持、V/R最终未齐；目标active、Issue121=in_progress/PR122=draft，登记pending、看板unverified/同步pending、审查待指定。

2026-10-29 20:08:54 CST：V374 GRT setup/TNS −0.01/−0.02 ns、hold +0.02 ns，最大product[2][8]→output_mem[82][17]、最小point_total[7][116]自环，9原始SHA/字节及同一input.v/已核验308源绑定。300MHz尚未通过，原93372继续route/finish；375/376待真实最终产物。另补存3份完整CTS证据，76500字节报告为旧74358字节快照原样追加2142字节，CTS时序不变，旧快照保持。R344仍全局布线、原任务保留。M/S/T接收保持、V/R最终未齐；目标active，Issue121=in_progress/PR122=draft，登记pending、看板unverified/同步pending、审查待指定。

2026-10-29 19:53:30 CST：V374 已完成 CTS 并进入 route 阶段；最新日志为全局布线修复。CTS setup/TNS −0.01/−0.02 ns、hold −0.04 ns，尚未通过；最大 norm_square[1]→group_unit.denominator[127]，最小 cmd_data[22]→input_mem[220][22]。修复内置 LEC 实际 UNSAT/IDENTICAL（51206 输入/51195 输出，差异均0），11原始文件及308源/Git/远端SHA核验；此为阶段诊断，最终RCX和375/376独立验收仍待实际结果。R344 全局布线额外迭代13/30，继续原任务，不增加版本或中断EDA。M/S/T接收保持，V/R最终未齐，目标active、Issue121=in_progress/PR122=draft；登记pending、看板unverified/同步pending、审查待指定。

2026-10-29 19:15:50 CST：377代码f318db6e/配置f61222a5、PID3065817，24原文件/归档SHA与两轮进程读回通过；仅替换372轻量控制并退休未分配369/370/371，全部EDA不取消。367/373各七项通过，80预算实际重绑373；374于19:12:31提交93372/node17，当前结构/综合检查运行，375/376按真实前置；7原始启动文件/308源核验。R344继续route。相关allocation含排队当前8个，保留上限；M/S/T接收、V/R最终未齐，目标active，Issue121=in_progress/PR122=draft；登记pending、看板unverified/同步pending、审查待指定。

2026-10-29 19:11:46 CST：367七项全部通过、415764映射单元（较361少29668，非物理面积），10原始/308源绑定；373七测量通过、53原始/39稳定/308源核验，135有限+78公共测量全同362，80预算已按373实际重绑且成本不变。368错误父类型在claim前FAILED/1，5原始保留，373新运行修正。374→375→376全新物理/最终门/接口已准备，377准入待部署；旧369/370/371不作新源资格。R344继续route。M/S/T接收，V/R最终未齐，目标active/Issue121=in_progress/PR122=draft；登记pending、看板unverified/同步pending、审查待指定。

2026-10-29 19:04:26 CST：372轻量准入PID3047721已部署，代码1376465/配置2d51a8b，24个远端文件SHA与原归档核验、正反控制和两轮实际读回通过。仅替换366轻量控制并退休未分配365；364已有运行记录，保留正常收尾，不取消任何EDA。369等待367六行为/算术/映射与368七测量实际回执，370/371待后继；R344/345/346保留。V363/93294已自然COMPLETED/0但最终setup−0.13ns，不能接收。367六项通过、映射运行；M/S/T接收保持、V/R最终未齐，目标active、Issue121=in_progress/PR122=draft；登记pending、看板unverified/同步pending、审查待指定。

2026-10-29 19:00:49 CST：V363六原生阶段自然完成但最终RCX setup−0.13ns，cmd_valid→stats_sumsq[1][79]，未达300MHz。新源367命令/状态使能分离，93237现有allocation节点内五×16并发、六行为/算术项通过，映射运行；三初态各566999检查/414906拍、公共42/扩展36全部测量与361一致，47原始/308源核验。368已准备测量，369→370→371已准备全新物理及完整验收，等待真实依赖；372准入待部署，不声称已运行。R344继续route，原有EDA不取消。M/S/T接收保持、V/R最终未齐，目标active，Issue121=in_progress/PR122=draft；登记pending、看板unverified/同步pending、独立审查待指定。

2026-10-29 17:48:49 CST：V363 CTS内置LEC实际UNSAT/IDENTICAL（51142公共输入/51131公共输出、diff均0）；CTS setup/hold约−0.12/−0.08ns，rsp_ready→stats_sumsq[0][79]/rsp_valid；GRT setup−0.10/hold+0.02ns，rsp_ready→stats_sumsq[1][79]及cmd_data[117]→a[3][21]，仍详细布线。旧357六原生阶段自然COMPLETED/0，最终RCX setup−0.15ns、offset[2]→stat_block_max[16]，hold仅舍入0，不接收也不转移资格。三诊断目录共29原始文件SHA/字节与各308源绑定核验。R344仍全局布线拥塞修复；364/365及345/346按真实前置。M/S/T接收保持、V/R最终未齐，Issue121=in_progress/PR122=draft、目标active；登记pending、看板unverified/同步pending、独立审查待指定。

2026-10-29 16:28:31 CST：V361七项全部通过、445432映射单元（较355多2656，非物理面积），映射10原始/308源核验；362七项/135有限+78公共测量通过、80预算重绑且成本字段保持，原预算字节封存。366源423c006/配置4034242、PID2777187及两轮核验通过；只替换360轻量控制、未分配358/359退休，全部EDA正常收尾。366于16:23:02自动提交V363/93294/node17，全新原生继续，364/365待真实前置。R344 CTS内置LEC通过，setup仅舍入0/hold−0.24ns，9原始/307源绑定，已route；345/346待前置。M/S/T接收、V/R最终未齐，Issue121=in_progress/PR122=draft、目标active；登记pending/看板unverified与同步pending。

2026-10-29 15:11 CST：V355六数值/264bit算术项已过，47原始/35稳定/308源绑定核验，三初态各566999检查/414906拍，公共42/扩展36全部测量与348一致；映射继续。355复用R344/93237空闲80CPU，356复用R311/93125空闲80CPU执行七项新源占用/有限工作空间，均五个16CPU槽即时补位、无新allocation。选定未来357全新原生→358最终门/六文件/完整几何→359接口，仍待staging与真实前置；控制源RUNS已改，原354进程尚未替换。R344物理继续，M/S/T已接收、V/R最终未齐；Issue121=in_progress/PR122=draft、目标active，登记pending/看板unverified与同步pending。

2026-10-29 14:29 CST：R342映射实际通过，709124工艺单元/8个32×33乘法器，9原始小文件与307源核验；93189因保留两项旧引用采样失败自然FAILED/1:0，映射自身通过，修正后的343采样通过。354按逐项前置自动提交R344/93237/node21（14:24:55），已进入fresh floorplan，7启动原始文件/307源及R RTL绑定核验；345/346仍待真实前置。V350 CTS内置LEC已UNSAT/IDENTICAL，CTS setup−0.04/hold−0.23ns，11原始/308源绑定，继续原生route；351/352待真实前置。M/S/T已接收、V/R最终未齐，Issue121=in_progress/PR122=draft、目标active，登记pending、看板unverified/同步pending，管理员/独立审查待指定。

2026-10-29 14:24 CST：V350 CTS内置LEC已实际UNSAT/IDENTICAL（51126输入/51115输出、diff0/diff1均0），完成后最差setup−0.04ns、hold−0.23ns；分别定位cmd_valid→stats_sumsq[0][79]和reset→rsp_data[86]。11原始文件SHA、308源Git blobs及全部V RTL绑定核验，350/93210继续原生route/finish，351/352仍待真实前置。R342已进入ABC工艺映射，344/345/346待映射回执。M/S/T已接收，V/R最终未齐；Issue121=in_progress、PR122=draft、目标active，登记pending、看板unverified/同步pending，管理员/独立审查待指定。

2026-10-29 13:31 CST：V337实际CTS setup−0.41ns指向group_unit.sqrt_mode→余数（优化别名twice_remainder[29]），8原始文件/源网表映射保留，原337继续route。V348完整130bit分组减法同时产生无借位决策，不增寄存/迭代/周期；260bit无约束SAT及真实单bit负例、三初态/公共/扩展/组合/延迟/映射七项全过，447672单元、93204自然完成。349现有R311空闲80CPU七项占用/工作空间全过、53原始/39稳定/308源核验；135测量与340一致，80预算绑定349/R342且全部成本字段一致。350/351/352新链已stage/validate，354源5b659f1/配置8c45007及PID2486398两轮核验；只换347轻量控制，未分配338/339退休，350实际93210/node17于13:28:16提交并运行。初次10秒观察超时后按原PID恢复，未重启/重投。R342映射继续，344/345/346待真实前置；M/S/T接收保持、V/R最终未齐。Issue121=in_progress、PR122=draft，目标active；登记pending、看板unverified/同步pending，管理员/独立审查待指定。

2026-10-29 13:06 CST：仍为M/V/R/S/T各一个基础宏。R342三初态/24公共/9卷积通过，全部测量与309一致，映射93189仍运行；两旧引用采样失败保留，343两新源占用通过（现有93180空闲CPU，无新allocation）。80预算重新绑定342，全部候选成本字段保持；原预算字节封存。新R344原生→345独立最终门/六文件/完整几何→346接口已stage/validate，9原始文件/各307源Git blobs核验，暂无allocation。347源a237862/配置e31d915、PID2437030及两轮核验，只替换341轻量控制；未分配312/313退休，原311和全部运行EDA正常收尾。V337/93180已CTS完成、详细route运行，338/339待真实前置；M/S/T接收保持，V/R最终未齐，不能标五宏完成。Issue121=in_progress、PR122=draft，登记pending、看板unverified/同步pending，独立审查及管理员待指定。

2026-10-29 12:37 CST：340当前源有限预算已重算并核验80候选、全部输入SHA和生成器Git24143cb；333旧预算原字节保留，三初态与有限场景不转移为整模型资格。16M/4V4S/context2048下Phi/Qwen3.5/Falcon已计价101.19691/99.03555/94.945297ms，仍超假设90ms窗口。最新实际V337/93180及R311/93125均place运行，341控制进程存活；338/339和312/313待真实前置，M/S/T接收保持、V/R最终未齐。Issue121=in_progress、PR122=draft、目标active；登记pending、看板unverified/同步pending、独立审查及管理员待指定。

2026-10-29 12:35 CST：V336六项全部通过、440672单元映射，93173自然COMPLETED/0:0；340七项占用/工作空间全过、93177自然完成，135实际场景已比较，RMS/L2保持、3072连续Softmax16707→16719拍。分别9映射/47工作空间原始文件，307源Git blobs/receipt绑定核验；333预算原字节封存，新预算正在按340重算。341源3e3fc5f/配置389cec2已替换335轻量准入，PID2375026及两轮读回验证；原330与全部EDA不取消，331/332无allocation才退休。337已自动提交93180实际RUNNING/node21，7原始启动文件/307源核验；R311仍place，338/339及312/313最终门待真实前置。M/S/T已接收，V/R最终未齐，目标active；Issue121=in_progress、PR122=draft，登记pending、看板unverified/同步pending、管理员与独立审查待指定。

2026-10-29 12:24 CST：V336函数入口流水五行为项通过，三初态各566999检查/414906拍，公共42/扩展36案例、组合与延迟通过，八元素函数实测8拍；38原始文件/28稳定绑定/307源Git blobs核验。93173映射仍运行。未来选择337新原生→338最终四门/六文件/完整几何→339接口，340占用/有限工作空间与预算须按新源重测，均未授予资格。330原生正常收尾，R311仍place；M/S/T接收不变、V/R最终未齐。Issue121=in_progress、PR122=draft、目标active；登记pending、看板unverified/同步pending、管理员和独立审查待指定。

2026-10-29 10:16 CST：R309四项全部通过，映射773440单元/8个32×33乘法器，93066自然COMPLETED/0:0；9原始小文件、300源Git blobs/receipt绑定及大网表日志SHA核验。335自动在释放的槽位提交R311/93125，实际RUNNING/node18，16CPU原生任务已claim；7原始启动文件与302源Git blobs核验。R312最终门/六文件/完整几何和313接口待真实前置。本任务仍8allocation，V330仍待空位，旧322详细布线继续。M/S/T已接收，V/R最终未齐；Issue121=in_progress、PR122=draft、目标active，登记pending/看板unverified/同步pending，独立审查待指定。

2026-10-29 09:24 CST：329六项全部通过，443391单元映射，93097.4自然COMPLETED/0:0；源ddf2ed5/RTL4c0d3647…，五行为项三初态各565599检查/413506拍，公共42/扩展36案例、组合和延迟通过。333七项实际占用/有限S16KiB-V/模型长度全过，93097.5自然COMPLETED/0:0约49秒，无新allocation；53原始/39稳定绑定、305源Git blobs/receipt输入核验。135有限场景与327完全相同，当前全局统计Softmax入口周期不变；新增2拍仅本地组合Softmax。已按333新源重算80预算、成本字段完全相同。330全新原生ready，但8个本任务allocation满额，未分配；331最终四门/六文件/完整几何和332接口按真实前置。R309 ABC映射/311/312/313继续；原322/316/306/291/236不因慢取消。M/S/T接收保持，V/R最终未齐；Issue121=in_progress、PR122=draft、目标active；登记pending、看板unverified/同步pending、管理员及独立审查待指定。

历史记录（2026-10-29 08:33 CST）：M/S/T最终接收保持。V321分母流水五行为项通过、映射运行；322原生/323最终/324接口为未来选择，尚无新源最终结果。325拟重测有限S/V与占用，旧319预算不代表新RTL。R309映射继续，311/312/313待真实前置；五宏尚未齐。

# 五种基础宏：新版300MHz最终结果入口

每种仅一个基础实现。Nangate45 M1–M10在宏内固定，M11/M12接口验证单列。旧ad3c2b3的100MHz交付保留在原delivery目录，其资格不转移。

| 宏 | 新版原生最终接收 | 全信号接口P2几何 |
| --- | --- | --- |
| [M 矩阵乘加](M/README.md) | 255原生六阶段、258四门/最终文件/完整原生几何全部通过 | 262全部275位通过 |
| V 向量计算 | **尚未最终接收**。361七项/362测量预算通过；363/93294/node17详细布线，CTS内置LEC通过但GRT setup−0.10ns（rsp_ready→stats_sumsq[1][79]）、hold+0.02ns，最终RCX/364四门及六文件待前置。旧357自然完成，最终setup−0.15ns，不接收。 | 365待364实际完整几何 |
| R 递推计算 | **尚未最终接收**。342/343验证通过；344/93237已route，CTS内置LEC通过但setup仅舍入0/hold−0.24ns，345最终四门/六文件/完整几何待前置。原311正常收尾，不继承历史资格。 | 346待345实际完整几何 |
| [S 16KiB工作存储](S/README.md) | 280 fresh原生六阶段、独立四门、最终文件与完整原生几何全部通过；1610²µm、273接点，setup/hold +0.687419/+0.012282ns，原生及完整GDS DRC0 | 292全部273位P2、baseπRC通过；highπRC142输入cap违规。297逐端口base/high输出C通过 |
| [T 6KiB结果交接](T/README.md) | 246原生六阶段、249四门/256最终文件与完整原生几何全部通过 | 261全部386位通过 |

M/S/T全接口都是2µm宽/距、2µm切孔/2.2µm切孔间距和零额外包围的研究几何假设。全部原生mask保持，连接及规则已用真实DEF/ODB/joined GDS验证；完整跨宏系统时序与校准12层工艺均未验收。T线电容超原48fF线预算，M高变体也需另验。

本入口不宣称五宏整体或系统已完成。当前事实与恢复入口见[交接](../../../../docs/handoffs/2026-10-28-issue-121-300mhz-review.md)。

M/T新增[六点实际输出负载敏感性](../review-20261028/load-0200/README.md)全部通过，最高分别67.264218/89.640522fF；原生最终文件保持。新的[全部端口πRC试验](../review-20261028/boundary-rc-0448/README.md)补上输入/输出/clock串联R和分布C：M base/high及T base通过，**T high有9项输入电容违规，失败保留**（最差−20.721312fF）；T setup/hold虽正也不能覆盖电气失败。只授予声明base边界下的有限敏感性结论，新增层耦合、具体远端驱动/阵列和校准12层工艺资格未取得。旧286控制接收器失败保留，新287实际四控制已通过。

[V/R实际端口性能及长组补测](../review-20261028/vr-bench-0225/README.md)已通过，包含旧/新相同负载、两初态、气泡/背压和完整字节/相位计价；V/R新版最终物理资格仍未取得。

[M模型形状640执行](../review-20261028/model-m-0405/README.md)及[真实S/V模型长度216执行](../review-20261028/model-sv-0408/README.md)通过，RTL/独立参考保持；[阶段E资源预算](../review-20261028/RESOURCE-BUDGET.md)按实际有限端口重算八模型并列出具体剩余瓶颈，未宣称10token/s。M/T的[16位实际固定路径风险试验](../review-20261028/preconnect-0400/README.md)只在副本通过原生DRC0，生产宏不采用这些M9预连；首版适配继续依赖M11/M12。

[审阅要求的一页前后对照](../review-20261028/BEFORE-AFTER.md)：已填M/S/T真实原生面积、全部端口、上层halo/线长/via及最密方向组用轨；V/R最终项待真实验收后补齐，不以候选值占位为完成。
