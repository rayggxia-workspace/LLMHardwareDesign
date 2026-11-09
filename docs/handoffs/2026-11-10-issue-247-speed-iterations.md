# Issue247速度迭代接续

## 第四轮RTL已集成，服务器校准待启动（2026-11-10 Asia/Shanghai）

Issue247/PR243，Melodydt，in_progress；3/4轮PDF及证据已完整交付。R4从best R2增加op12可选四EXP lane，N/U两个生产源已集成，NEXP_DIRECT_LANES默认2，普通N不扩；router/adapter保持R2逐字相同，S仍16KiB。新显式状态34bit加两套EXP组合路径，不声称综合面积/300MHz通过。前态R2备份与R3大面积独立分支均保留。

21顺序build/63运行（三seed，含非法LANES3预期拒绝）已准备。原run18的21份真实日志与输出SHA派生1.16MB observed输入，run18-observed SHA cc5e13093dd5269e8fcd473e56a524e7a3b4e21d426e064b48ed0fab1f080296；新默认完整可观察事件须精确复现，另逐命令实数CALC次数。AST/纯生成/原回执解析/独立源码与测试审阅通过，未执行新RTL或填入周期。

下一步提交源并读回，创建扩通道独立备份，在本人服务器新run22经Slurm四核执行，随后用真实profile运行旧体系16case，出第四轮详细PDF；主达5或完整第四轮后停止。当前最高仍R2 ideal3.66958239533/shared3.37834376557，未到5。无活动作业/自动监测。目录project/experiments/rtl_iterations/round4；非Git本地快照work/Melodydt/242/r-load-bounds/repo仅根整合；远端task/242-r-load-bounds未合并main。登记pending、看板unverified/同步pending、正式审查人待指定，CI未声称通过。

## 第三轮RTL与旧体系评估通过，候选未超第二轮（2026-11-10，Asia/Shanghai）

Issue247/PR243，Melodydt，in_progress。run20/101872（源a3149d69a23f52efb808dbbb46b5558dffce4df7）41秒；run21/101878（源010ae8d0d8839967f96b94227d2224fade0edf37）6:06，均c64/node1/4核COMPLETED0:0。RTL六run×66场景、有限控制299064周期比对及实际S数值通过；模型24case/8精确回归/8fallback、192篡改及原测试通过。R3双buffer主ideal3.66041657326/shared2.75864978939，低于第二轮；当前最快仍3.66958239533/3.37834376557，未到5。

第三轮5页PDF、134内容单元及全部页面视觉QA通过，当前完整交付3/4轮。报告固定809f9820cc13157077e4399a789779aac52925db，PDF SHA00b0b6c2d6c44829808d316cb3e6658c378d8bf51e5cb7632320e790e969940d。大面积候选独立备份task/247-m-k16-area-initial@a3149d69a23f52efb808dbbb46b5558dffce4df7与前态备份均读回；S仍16KiB。run20结果SHA87842b59e42fb0773eedb82dce4981614432868fa12218c3aa15166b0b839eff，run21结果SHAbccd917afba10bb9c3f65f62b26b1eab588a85d73c364a4b4d54962b5197afb8。

服务器本人/public/home/yuzelu/Melodydt/issue247-area-speed/run20、run21持久保存source/、slurm-job.log与results/；62大raw另有retention SHA索引，不声称Git内含所有raw。追踪sacct -j 101872,101878 -X --format=JobID,State,ExitCode,Elapsed,NodeList。全部终态，无自动监测。第四轮在隔离目录实施R2基础op12四EXP lane；1KiB A缓存受DDR上限约束，仅保留方案。恢复第一步核对最新PR head/本轮报告，继续第四轮源审查、Slurm实测和旧体系复评。非Git本地快照work/Melodydt/242/r-load-bounds/repo仅根整合，R4子任务各隔离目录；远端task/242-r-load-bounds未合并main。

登记pending、Projects unverified/同步pending（缺board.json及工具能力）、审查人/管理员待指定；GitHub CI此前失败原因未核实，未绕过。当前候选不具备完整P/DMA、原生整图生成或新物理资格。

## 第三轮RTL校准通过，旧体系整图评估待运行（2026-11-10，Asia/Shanghai）

Issue247/PR243，Melodydt，in_progress；已完整交付2/4轮。run20/101872/mdt-r3-finite-m，源码a3149d69a23f52efb808dbbb46b5558dffce4df7，c64/node1/4核，41秒COMPLETED0:0。六次各66场景7638检查20复位点，数值/S96前缀/生命周期/有限资源/真实S/源身份/单双缓冲公平性与299064周期控制比对通过。实际读写ACK均2拍。结果SHA87842b59e42fb0773eedb82dce4981614432868fa12218c3aa15166b0b839eff。完整raw在/public/home/yuzelu/Melodydt/issue247-area-speed/run20/results及本地run20/receipts；62大原始文件留服务器和本地归档，仓库retention索引明确，不冒充Git内含全部raw。

大型K16候选独立备份task/247-m-k16-area-initial@a3149d69a23f52efb808dbbb46b5558dffce4df7已创建读回；前态task/247-pre-m-area-r2-ed9f5ee6和本地初版归档保留。S仍16KiB四1RW。正式round03模型已独立审查及真实profile静态核验，待服务器24场景运行；不能由局部周期比预填token/s。最快仍R2条件ideal3.66958239533/shared3.37834376557，未到5。

源模型位于project/experiments/iterative_speed/round03，关闭优化须精确复现run19，所有DDR/缓存/原tile调度成本保留；当前R3尚无完整P/DMA联调或物理验收。无活动作业/自动监测。恢复第一步读最新PR head，提交/核验本模型源后创建新run21，仅Slurm节点运行。登记pending、看板unverified/同步pending、审查人待指定；CI旧失败未绕过。源码快照目录work/Melodydt/242/r-load-bounds/repo为非Git本地副本；远端任务分支未合并main。

## 第三轮候选已准备（2026-11-10，Asia/Shanghai）

Issue247 / PR243，负责人Melodydt，in_progress，已完成2/4轮。R3独立K16 S32/W8/S96有限供数、单/双buffer、8条完成预约、2条读metadata已实现，仍四1RW/16KiB；原生产P和R1/R2不变。基线额外备份task/247-pre-m-area-r2-ed9f5ee6@ed9f5ee63ceaeb260eb611f10d569ec8904a81c6已读回，初版七源归档SHA9150111291360ce468c336549a70c4a4b9b3eb901fa33a4fce302bd0ef1137e2另存。大面积128个32×9乘法器与寄存账本见docs/decisions/issue-247-r3-large-area.md；不是综合面积或完整P/DMA集成。

66个数值/边界/背压场景、完整K2048/11008和八ctx、20复位点测试及有限控制逐周期重放器准备完成；目前仅源/AST/生成输入/静态交叉审查通过，尚未执行R3服务器RTL。下一步提交源码、创建候选独立远端备份，随后在本人父目录新run20、Slurm4核校准。必须先真实数值/控制/ACK延迟通过再运行旧模型24case，不预填性能。当前最快仍R2 ideal3.66958239533/shared3.37834376557，未达5；无活动作业或自动监测。

R3正式实验目录project/experiments/rtl_iterations/round3；子代理的feed/rtl/model独立目录保留，只有根整合正式源。模型将在iterative_speed/round03独立实现，关闭新开关须完整复现run19；R2冻结目录不改。登记pending、Projects unverified/同步pending、审查人待指定；R2 GitHub CI无steps且日志404，未绕过。

## 第二轮RTL与评估通过（2026-11-10，Asia/Shanghai）

Issue247 / PR243，负责人Melodydt，in_progress。R2源码863492081f0f512fc64fb73c787fcdcaf145a6b4，31文件blob读回通过。run18/101852/mdt-r2-nexp-rtl，2:37；run19/101854/mdt-iter2-nexp，2:53；均c64/node1/4核COMPLETED0:0。R2实际费用[7,7,9,9,16,16,18,18]，默认/DIRECT0兼容、数值、持久状态及完整U通过。16旧体系case/8默认精确回归、2prefill fallback、128篡改及profile/CLI负例通过；独立复核完成。

主W8 decode512 ideal3.66958239533（比R1+0.90184%）、shared3.37834376557（+0.83026%）；Dot224.101536667ms占82.2359%，未达5。run18结果SHAfb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78，run19结果SHAb16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098。两run在/public/home/yuzelu/Melodydt/issue247-area-speed/，源码、日志和结果持久保存；追踪`sacct -j 101852,101854 -X --format=JobID,State,ExitCode,Elapsed,NodeList`，查看各目录results/result.json。所有作业终态，无自动监测。

第二轮4页PDF及110内容单元、全部页面视觉QA完成，当前2/4轮完整交付。PDF源文档固定e531a9944ff1ae4bc55e3b6e204be48f425af1a3，PDF SHA1c28b2f2ee7a736b92d4e84308e6a067a6ec761976e78d547310248ac9850a66。第三轮在隔离目录研究/实施S32/S96 M有限供数；正式生产未改R3。恢复第一步核对PR最新head，审查R3真实buffer/nextK/commit/ACK与旧模型收费边界，并在新增大面积候选前创建独立备份。SRAM不扩容；大面积候选另备份。登记pending、看板unverified/同步pending、审查人待指定，未合并main。

以下为历史阶段回执；当前以最上方记录为准。

## 最新阶段：R1已通过，R2隔离实施中

R1源e6d72113a14c5a0772f01ff5851d630d5d6687fa；run16/101835已COMPLETED0:0、40秒，结果SHA78c57febe43f2a114a8a21ca9b5992b465d7b7589f05c83eb68e5f97923d4ef7。run17/101838已COMPLETED0:0、2:52，结果SHAbc27f6b66c63b7356a4ead76e800c539efb1499322f91c45114e6df79595d076。均c64/node1/4核，源码/日志/结果在上述本人父目录run16、run17。133策展原件和完整源/输入SHA已核验，见work/Melodydt/247/speed-iterations/index.json；主条件3.63678454238、shared3.35052563236，未到5。无活动作业、无自动监测。

R1 PDF已完成5页/125内容单元/全部页面视觉QA，源码文档固定1b3bdd623b7a85e2d7a4daac158b281e0b12dd92。PDF SHA f4618d877fee2072744aa9af8f7cefba86c4bd859d9a512d21b7996276fbf7b6，当前1/4轮完成。R2新方向是复用原N两lane的stateless relative-exp保留op12，把四命令收敛单命令，新增参数默认0；这是小幅增量，不承诺到5。子代理在外层iterations-research/{feed,rtl,model}/round2独立实现，根尚未集成R2生产源。恢复第一步：先读最新远程head，再完成R1 PDF/证据提交和R2候选审查；不能跳过真实RTL周期而使用预估9拍。

以下运行启动块为历史回执，当前状态以上述终态为准。

## 最新运行回执：R1 RTL

2026-11-10，Asia/Shanghai，源码e6d72113a14c5a0772f01ff5851d630d5d6687fa已上传并读回27文件Git blob一致。run16 / 101835 / mdt-r1-nexp-rtl，c64 / node1 / 4核，已读回RUNNING。服务器yuzelu@10.129.166.172，本人目录/public/home/yuzelu/Melodydt/issue247-area-speed/run16，源码source/、日志slurm-101835.log、结果results/result.json。payload SHA256 37f16a1a9c833b52459a242e5fbe50c94d1febe6da17740c160c94b51e4402ca；25源文件和1份上游版本索引随清单绑定。

实际启动：目录内 `sbatch --parsable job.sh`。追踪：`squeue -j 101835`；`sacct -j 101835 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList`；`tail -n 60 /public/home/yuzelu/Melodydt/issue247-area-speed/run16/slurm-101835.log`；`cat /public/home/yuzelu/Melodydt/issue247-area-speed/run16/results/result.json`。

成功判据：终态COMPLETED0:0、完整RTL result.passed、所有数值/生命周期/兼容性gate、实际count1..4服务校准及源/输出SHA通过。当前尚未通过，0/4轮完成。下一步根会话回收并核验，随后运行旧模型16case；未配置聊天结束后的自动监测，恢复由Melodydt唤起此交接。以下为开始时背景记录，当前运行以上述最新块为准。

2026-11-10，Asia/Shanghai；负责人Melodydt；状态in_progress。

- 仓库：rayggxia-workspace/LLMHardwareDesign；[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，现有分支 `task/242-r-load-bounds`。PR未合并，不宣称已进入main。
- 起点源码：`a22e199c1dce7d1037995a26f71f8b1358d038e0`；已创建并读回完整备份分支 `task/247-speed-base-a22e199c`。
- 本地主目录：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`，非Git快照，通过Melodydt本人GitHub连接、精确文件清单和租约更新远程分支；不要在外层管理快照假称git提交。
- 独立研究目录：外层 `work/Melodydt/247/iterations-research/{feed,model,rtl,upstream241}`。子代理仅改各自研究目录，正式目录由根会话集成。upstream241冻结PR241@189e43c77a6277955c1be54281b0d6b0b0d55c1f，13文件Git blobSHA已校验。
- 当前本地变更：迭代总入口、此交接、本人进度/项目阶段摘要；R1模块/测试在独立目录形成，尚无本轮已通过仿真。管理结构检查PASS，只是结构检查。
- 目标：最多四轮，每轮研究→方案→RTL→旧评价体系服务器评估→详细PDF，主W8 decode512达5 token/s或满四轮时停止。当前0/4轮完成。SRAM扩容仍不实装，巨大面积方案独立备份。
- 评价：固定run15原trace、S32/S96条件模型、2P/1U、300MHz、17.1GB/s，16KiB、八上下文，共享口/理想1R1W分列。起点3.23081074122/3.49616888299 token/s。仅在实际RTL证据支持下替换局部成本，禁止把原生S64/四1RW资格等同旧S96/理想端口。
- 首轮：正式U新增默认关闭NExp批处理，共享唯一原N。S32容器低16有符号映射和输出U16零扩为S32保持旧候选合同；op15显式破坏原N统计会话，普通统计需重新op0。prefill实际S16输入不适配NX32，保持完整旧路径费用。
- 下一步第一动作：核对远程分支仍是已知head及其他会话改动，再审查独立候选、集成正式RTL和运行器，提交代码后才打包仿真。先RTL功能/数值/握手/U实际S读写ACK，再把实际profile绑定旧SystemC评估；每轮PDF完成视觉QA和证据上传后计入已完成轮次。
- 服务器：`yuzelu@10.129.166.172`，本人目录 `/public/home/yuzelu/Melodydt/issue247-area-speed`。既有run01–15保留；本轮尚未提交，拟从run16开始。所有EDA/SystemC用Slurm c64/c96、4核、mdt前缀、time=0及既有容器，禁止本机/登录节点执行。每次提交立即补充实际job/node/日志/结果/追踪命令；现在无新作业，未配置自动监测。
- 工具辅助：外层 `work/Melodydt/247/iterations-tools/` 为显式清单打包、Git tree准备、不可变证据策展和PDF转换。首次新PDF操作marker已成功执行一次（05153f），无需重复；期望最多4份。每份最终PDF均需逐页渲染和目视核验。
- 审查/登记/看板：独立审查人待指定；登记management-hub PR5 pending；缺config/board.json及Projects工具，看板unverified、同步pending，管理员待处理。未标done，不自行合并。
