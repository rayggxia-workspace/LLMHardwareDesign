# 2026-10-30 23:05 接续入口

Refs #121 / PR #122。目标仍未完成，不能标complete。M/V/R/S/T各一基础宏、300MHz、固定M1–M10及未来M11/M12的真实M10接口。M/S/T已接收，不重复跑。V/R待全部最终物理门、六文件、实际完整几何和逐端口/有限RC。无整数整模型质量/速度/制造资格结论。

## 唯一当前V

- 生产RTL源dea3c22b4f3a63641fceacfbc9fedafbd3bf3388；archive576 SHA5e45946f8e71e7339869e281ef0555e3fb1e53b94772ba4f3c822be3f3855149。S_WRITE两上下文常数索引本地反馈、S64/U80精确prefix累加，周期未改；完整128位点运算、8共享乘法器保持。
- 576八项实际全PASS，583保存61原始/47稳定输出/315归档Git与receipt绑定；公共42/扩展36例。统计模64/80、128位RNE及两项故障负对照已证明。
- 577五项有限S/V PASS，两项occupancy因helper遗留generation550与policy576不符在测量前失败。584完整保留41原始/25稳定/315源。不得重试577或改写失败。
- 仅helper修复80f004e0764bde2125a70a125ad567a16151676f；archive587 SHAf26714b403780fbfeb43f9a2c91cf474826b16476e616c2ac9ac0abec1bbca3a。587/93779两项occupancy实际PASS（592，19原始/10稳定/315源）。51 RTL/C++与576逐字节一致，既有通过的五项有限SV不重跑。
- **588/93781/node16已实际启动**，全16真实前置为576八项+348 group证明+577五项+587两项。当前综合完成、floorplan进行；不是最终通过。归档587，从六阶段全新执行，不复用552 CTS/route。
- 589最终所有门/六文件/实际完整几何、590逐端口/有限RC已stage。helper84045638ae0621dbaa8fcc14119a9e07489a632f/archive589 SHA088cfe2657ef6eaf562b1b331091b01cd222139632c1ebad83d39e02927fdae4，与576/587三方51 RTL/C++精确一致。源码选择与BEFORE-AFTER指向588/589/590，accepted=false。
- 589 stage末尾dry-run遇Issue级非阻塞锁，仅准备日志失败；identity-proof、manifest、queue、源码均已核验。没有sbatch，不需要重做stage；控制器按原锁接续。

## 仍在运行与自动接续

- **591登录控制器PID1087781**，配置SHA9462704bd644ffcc91bcc06a70be38d2c6cf5d8b760d8886baf23d15eddda7df，代码来自当前84045638的revision300_admission.py。十六固定队列，原dispatcher仍是唯一提交者，Issue级锁/reservation及≤8 allocations保持。启动和第二轮进程/UID/启动tick/命令/代码配置SHA、实际账目都已封存。
- 仅退役581登录控制器，未触碰EDA/Slurm。更旧555/540已退役。不要再运行peek555live/peek581live。
- R404/93555/node21原GRT **extra40/100**。无时限；不要因慢或日志安静取消/重启。405/406由591按真实前置接续。
- 553/93764/node13旧552独立验收：physical FAILED（582，13项setup）；DRC与三初态功能仍RUNNING；formal待依赖。自然收尾，交付/几何被物理失败阻止。不转移资格。
- 两旧92045/node14、92046/node15继续自然收尾。当前五个本Issue节点，其他hpy任务不是本任务，不操作。依赖限制减少并发，不用假任务占位；有独立任务用6×16即完即补。

## 已封存的失败与诊断

- 552/93734自然完成全部六阶段；574最终WS−.0644667ns/TNS−.462257ns/13 setup，真实cmd_index[2]→stats_sum[0][62]。hold+.040569ns/0、cap/slew0，内部LEC零差异。582独立fresh RCX/coverage、PG/连通/M10等通过但setup拒收。不要再sample552current。
- 历史538/93729已自然FAILED：575 native465，完整未改GDS deck129类0；整体失败。558/559功能/LEC PASS不抵消物理/DRC。不要再轮询538终态。
- 旧523局部诊断：566填角445→213但22新增拒收；568过滤20候选、保留232填角，445→211/0新增，方法证据不接收。571 M1单via-pair445→444/0新增；**573 M3单via-pair也445→444/0新增**（586）。三者独立，不相加、不转移当前V资格。
- 573使用归档576，helper的m3 case来自此前50d208f4；实际marker249、via2_5两中心(60610,640500)/(60990,640500)，保留整个M3长线与第二via，去第一via、加M2桥。其他557411 NETS原始记录一致，目标恰一via换一M2线。仅诊断，无fresh连接/RCX/STA/完整GDS资格。
- 下一步若有必要，可把已验证两单例方法扩展为受约束的M3 via-pair候选，再做完整native0新增、精确NETS/DEF/几何连通补证。**尚未实现或运行批量方法**，不要说M3已解决。所有数据仅旧523方法验证，新588必须用自己真实坐标/源和全部最终门。

## 本地续跑与提交

工作树`D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-121-block-v1`，branch task/121-block-v1-twelve-layer。规则AGENTS/协作Skill/REMOTE_RULES已读，账号YUZE-LU；无新subagent授权。Windows嵌套引号失败多次：复杂Python逻辑写入.local的.py，不拼复杂python -c。

- `.local/issue121/peek588active.py`：只读V588/R404阶段与squeue；`peek591live.py`验证实际591；`peek587.py`可读当前588队列，587终态已封存，不重复收取。
- `.local/issue121/audit592.py`曾核验364原始Git字节/184证据SHA。593追加后应把期望改189并纳入593与591 capture/accounting，执行一次。
- 583/584/586/592/593以及581/591 capture/accounting已经收取；collector不可重复运行（带禁止覆盖断言）。record591/record593已执行，不能再次prepend或copytree。
- 有限资源预算仍是旧551的规范Git证据。577新五项已测，但**当前预算助手还硬编码v-workspace-551，尚未切换到577并按规范Git重新计算**；后续若更新，保留旧预算，不将旧输入说成新源测量。
- 所有sourceNNN.tar在.local/issue121，315源文件/316成员，新归档2,406,400B。正式大数据库保留服务器，仅小报告与原始字节索引入Git。
- `publish_exact_parallel.py BASE`只上传Git对象，不移动ref；执行时HEAD必须固定到终态，再用connector expected_sha CAS。raw `.gitattributes -text -whitespace`必须先于stage，验证真实Git字节。

PR122 OPEN/DRAFT、Issue121 OPEN/status:in_progress；管理中心PR5仍pending，看板unverified/同步pending、管理员与审查待指定；不自审、不合并、不关闭。线上body和实际ref/CI要在本次发布后读回，保留PR与Issue各自不同的封存ad3c2b3历史后缀，不能相互覆盖。完整原GDS deck/原生DRC/最终功能/严格LEC/RCX/接口等门未齐，目标保持active。
