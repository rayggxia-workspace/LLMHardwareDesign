## 2026-11-10 Asia/Shanghai：共享 A 32B 已验证，待审查

Issue247 / PR243；源码e7e8becca866e8257e026fddfc6e6215169e4015。run34/job102033在c64/node1/4核10:01 COMPLETED0:0，72run、12对430008周期事件、六项面积与全部回收SHA核验通过。原生同工作处理增益普通M2.0432%/8-context1.4344%，已计标准单元+0.033507222mm²、SRAM宏0。旧条件token/s单列，不作原生全模型测量。报告/证据见共享A32交接；下一步正式审查及连续负载瓶颈定位。in_review，未合并/not done；登记pending、看板unverified/pending、CI限制保留；无活动作业或自动监测。

# 当前：prefill扩宽评估完成待审（2026-11-10，Asia/Shanghai）

Issue247 / PR243，负责人Melodydt。生产RTL未改，实际条件模型源码ffa5410be225037c7f13c3092c2ee3487fa07ec0。run33/job102011/mdt-prefill-width，c64/node1/4核，10:33 COMPLETED0:0。24场景、8旧控制、7250+120数值、100生命周期负例、80事件负控、360主场景负控通过；99源/18输入/392输出索引核验及172回收输出SHA、独立复核通过。

原prefill2/W8条件最高4.429583 token/s，未达5；双组交错32→64B增益shared0.1450%/ideal0.6972%，64→128无整图增益；ideal服务已达到原M计算工作量，不能把旧5.0507外推当实测。报告[扩宽评估](../../docs/experiments/issue-247-prefill-width-evaluation.md)，[证据索引](../../work/Melodydt/247/shared-width/evidence-index.json)。

当前in_review，PR未合并/not done；没有活动作业或自动监测。下一步独立审查并依据结果决定后续M服务/输入ACK/非Dot优化，32B入口生产RTL仍待实施。登记PR5 pending，Projects无工具/board配置，看板unverified/同步pending；a2e8dd0上的GitHub结构CI仍failure且validate无steps/runner，原因待管理员核实；本地管理检查通过。

---

# Melodydt 进度

本阶段六页实施PDF已生成，全部237内容单元、8表/45行、两代码块、链接、嵌入字体及六页视觉QA通过。报告固定commit3e8dffdc9dce89cf7f04ff77b2b1cf711dae0039，64个新交付文件Git blob已读回；PDF SHA2630163765d8b0f6a0f97875ecd70749e18d83e4e925d3865da2456549984e32。PDF及QA由本次交付提交保留，原始报告来源保持冻结。本阶段转in_review；未合并、不done。

## 共享32KiB直供与本地1R1W实施（2026-11-10 Asia/Shanghai）

负责人/认证Melodydt，Issue247 / PR243 / task/242-r-load-bounds。两项可选RTL与真实双P包装层已完成本阶段验证，提交独立审查，未合并、不done。稳定测试源a7a36cbb76fa76f6162b666d1f5683cda2a8f7ec；修改前备份task/247-before-shared32-rtl@a8e793e4，候选备份task/247-shared32-native-a7a36cbb，均已读回。

run32/102006在c64/node1/4核1:16 COMPLETED0:0：单元3+4runs、双P四配置各三组、RELEASE/cold/lease、41472主数值+192重填数值及ECHO0生产面积通过。run29/10200340秒COMPLETED0:0：12组默认逐事件/周期精确比较+3组cold。run30/1020045:45 COMPLETED0:0：原评价体系32例端口宽度敏感性；16B共享A约束最高3.640199，prefill ideal3.496459，明确不是原生全图token/s。三路独立审计和完整本地SHA复核通过。

逻辑容量80KiB/物理112KiB/28宏；相对48KiB原配置新增64KiB物理SRAM。宏代理+1.4793928004mm²，池与两P后端标准单元净增0.07256081mm²（同ECHO0实际bank_rw基线），不含P外围和物理实现。完整DDR桥、母控/SoC接入、S32转换及真实模型生成仍未实现。

[实施报告](../../docs/experiments/issue-247-shared32-native.md)；证据work/Melodydt/247/shared32-native/evidence-index.json。服务器yuzelu@10.129.166.172，个人/public/home/yuzelu/Melodydt/issue247-area-speed/run26至run32；source/、slurm日志、results/、receipts.tar持久保存，全部终态，无活动作业，无自动监测。失败run26/28/31及修复经过保留。

本地完整快照python scripts/check_project.py通过，仅管理结构；GitHub validate在a7a36cbb仍failure且steps为空，原因未核实，未绕过。登记management-hub PR5 pending；缺board配置/Projects能力，看板unverified/同步pending；正式审查人和管理员待指定。下一步独立审查本阶段RTL/报告，确认A16B端口与实际DMA后续范围；管理员处理CI、登记和看板。此前run24/25研究报告证据包上传阻塞仍保留，本阶段不重传该包。

## 本地交付与上传阻塞（2026-11-10 Asia/Shanghai）

本次32/48/96KiB共享S条件研究及两路独立复核已完成；报告、run24/25结果证据及PDF留在本地，尚未上传GitHub。此前模型源码a8e793e4c6f97e9dca5b0cc203797dcd3b0e0e78已上传并用于run25，生产RTL未扩容。自动审批拒绝本次研究证据包上传rayggxia-workspace/LLMHardwareDesign，理由为内部路径及压缩实验资料的特定外传授权不足。没有通过拆包或其他通道规避；线上Issue/PR结果状态尚未同步。本地研究完成不等于在线交付或正式验收，以下in_review指拟提交状态。需用户确认这批资料上传到现有task/242-r-load-bounds / PR243；负责人Melodydt。

恢复第一步：读取本地work/Melodydt/247/shared-pool/README.md及此阻塞记录，确认授权后重新核对远端head和文件清单，按lease上传、逐blob读回，再同步Issue/PR。不要重复运行已成功的run25。登记PR5 pending，看板unverified/同步pending。

## 共享 S 直供研究已完成服务器评估（2026-11-10 Asia/Shanghai）
Issue247 / PR243，Melodydt，研究交付in_review，不done。保留各Block本地16KiB，共享32/48/96KiB经每P有限FIFO直供A；32main+10敏感例与8旧基线全字段回归、12数值地址case/725输出/107471事件/10生命周期负控/14非法CLI通过，两路独立后处理通过。prefill理想层4.398913/4.475230/4.668451，较R4+19.00%/+21.06%/+26.29%；shared层3.894197/3.977429/4.189147。三个decode的48/96完全同速，W8主ideal3.711253（+0.953%）。未达5；生产RTL未扩容，不计第五轮RTL迭代。
run25/101993/mdt-shared-pool，源a8e793e4c6f97e9dca5b0cc203797dcd3b0e0e78，c64/node1/4核，7:05 COMPLETED0:0；result SHAb56095b29aac658af899db495d5b44a07246c3ad04fa93a7b8945def87cfbd03。run24/101992 FAILED1:0的过时API编译失败已保留并修复，未弱化-Werror。244策展原件、两run各89源/15输入已SHA核验，3大输出由retention索引留在本人服务器和本地归档。
原服务器/public/home/yuzelu/Melodydt/issue247-area-speed/run24、run25持久保存source/、slurm日志、results/；本地work/Melodydt/242/r-load-bounds/repo为非Git快照，远端task/242-r-load-bounds未合并main。当前没有活动作业和自动监测。成果/复跑见docs/experiments/issue-247-shared-pool-study.md及work/Melodydt/247/shared-pool/README.md；原生RTL、物理面积/时序与真实生成仍未验收。独立审查人待指定，登记PR5 pending、看板unverified/同步pending；GitHub CI以最新PR回执为准。

[正式报告](../../docs/experiments/issue-247-shared-pool-study.md)。恢复第一步读取最新PR head与run25/index.json，再按verify.py核验；下一步正式审查并决定共享池RTL实施范围，负责人Melodydt。

## 顶层共享 S 直供研究（2026-11-10 Asia/Shanghai）
Issue247 / PR243，Melodydt，in_progress。用户选择共享 S→每 P 独立有限 FIFO→A feeder，比较共享32/48/96KiB；各Block本地16KiB保留。正式实验project/experiments/shared_pool_study，根独占当前非Git快照；子代理只在外层shared-pool-research独立目录开发。关闭新功能须精确复现run23八个R4场景，新增池计入填充/端口/延迟/背压；新性能尚未测量，不实装生产RTL，不属于第五轮迭代。
已核对Melodydt认证、远端head00a138bae558ccafa23514a7c1a8013dcc61b27f、Issue/PR与服务器本人目录；管理结构检查通过。下一步完成模型、独立审计、源上传后启动新Slurm run24；尚无本研究作业或自动监测。登记pending；缺board.json与Projects能力，看板unverified/同步pending，管理员与正式审查人待指定。[接续](../../docs/handoffs/2026-11-10-issue-247-shared-pool.md)。

## 大容量模型与面积预算补充（2026-11-10 Asia/Shanghai）

Issue247 / PR243，负责人 Melodydt。汇总 PDF 已修订为10页，包含48/64KiB四场景、端口敏感性、负结果和面积预算；404内容单元、16表/85行、2代码块、全部链接/字体及10页逐页视觉核验通过。固定报告源 commit 9d987151ee687322c0ce52d69a0a14f2275bd52b；PDF SHA-256 3e70437bac53997fc7f4471dc00bd261268b34dedd27661188d001239b2ec9d1。本次未修改 RTL、未启动服务器仿真或 EDA，不计第五轮。

历史policy16/理想1R1W模型：A48/A64 prefill2为4.467001/4.547434 token/s，较B16＋ctx8为+20.84%/+23.01%；三个decode场景增幅约1.30%至1.66%。同现有1RW bank复制，2P＋U的bank外框之和B16/A48/A64为1.109545/2.588937/3.328634mm²，A路线增量1.479393/2.219089mm²（+133.33%/+200%）。这是容量复制代理，不是目标1R1W、新布局、整个P/U或系统面积。q端口溢价与f系统占比均未测；新外围/布线/时序和实际面积待后续实现与EDA。

新增两份派生JSON均由独立计算与主代理重算逐字节一致；冻结原结果SHA、工作守恒、配置匹配和面积来源检查通过，独立性能/面积复核无阻断。本地管理结构检查通过。PDF保留旧版本已实施RTL的最新八场景；当前最高16KiB prefill仍3.69669737899，历史大容量/融合不得与R4叠加。

任务仍 in_review、PR243 open/unmerged，审查人待指定。登记management-hub PR5 pending；config/board.json缺失且无Projects工具，看板unverified、同步pending，管理员待指定。GitHub CI的最终head状态见PR本次回执，不宣称已通过。下一步独立审查报告及证据，管理员核实CI、登记和看板；不自动开始第五轮或实装扩容。

[最新报告](../../docs/experiments/issue-247-implemented-optimizations-summary.md)；[固定来源](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9d987151ee687322c0ce52d69a0a14f2275bd52b/docs/experiments/issue-247-implemented-optimizations-summary.md)。

## 优化总览与全场景性能PDF（2026-11-10 Asia/Shanghai）

Issue247/PR243：已汇总6类生产可选RTL、继承直连与独立实验候选；最新run23八场景和原run15矩阵/容量参考分列。7页PDF已完成244内容单元、9表/52行与全部页面视觉QA，报告固定c60106201c232742c701da6b3861df575208f8e3；PDF SHA 4625c72b6b472a048fdc6f0fc7e29d38309b82b0f05b085654f376c34ec23ef1。主W8 decode512共享3.38396291561/理想3.67621308212，最新16KiB最高prefill3.69669737899；历史大容量/融合不混入最新值。93条完整结果SHA复核与派生重现通过，无新仿真/第五轮。

[总览报告](../../docs/experiments/issue-247-implemented-optimizations-summary.md)。仍in_review、PR未合并；登记pending、Projects unverified/同步pending，CI以最终PR回执为准。审查人/管理员待指定。恢复第一步核对最新PR与总览/QA，再进行独立审查。

## 停止场景澄清（2026-11-10 Asia/Shanghai）

Issue247/PR243：用户确认任一原评估场景（包括prefill）达5 token/s或完成4轮即停止。已复核72条本轮及21条历史完整场景，本次16KiB最高3.69669737899；原64KiB未实装参考4.54743400007，均未达5，仍按4轮停止。[口径补充](../../docs/experiments/issue-247-speed-iterations.md)覆盖冻结PDF中的临时decode-only停止假设。本次无新仿真；管理结构检查通过。下一步独立审查，状态in_review、未合并；登记pending、看板unverified/同步pending、CI限制见PR，处理人待指定。

## 四轮迭代交付完成，进入独立审查（2026-11-10 Asia/Shanghai）

Issue247/PR243，Melodydt，in_review（待正式审查/合并，不done）。四轮研究、方案、RTL和旧体系评估已完成；四份PDF均已完成内容和逐页视觉QA，4/4轮完整交付，按轮数上限停止。第四份5页/141内容单元，报告固定f4be5c50507fec202551e45e39fb2215fc18876c，PDF SHA85ae41e4c79712710e078af3f1bcf033d17a8fd35e7896cb90a705b46dc5a741。最终主W8 decode512 ideal 3.67621308212/shared 3.38396291561 token/s，未达5；本次不再增加第五轮。R4采用best R2基础仅op12四EXP lane，默认2，普通N保留；生产启用需BATCH1/DIRECT1/LANES4。R3双buffer退化独立保留，SRAM没有扩容，物理时钟/完整原生生成未验收。

run22/101884源7048c35ed2912e80e62bd7827deaec480d4a7e1a，5:45；run23/101888源e6209544086f2460662bf7edfc91cbfb2c63cd9b，00:02:55；均c64/node1/4核COMPLETED0:0。21build/63run（3预期非法lane拒绝）及11门通过，fee[7,7,7,7,14,14,14,14]；旧模型16case、8精确回归/2fallback、128篡改及原测试通过，独立审计完成。run22结果SHA5abb31227f0c7b2c7ac9ff7eb8f80687569fab0b64bf74eb1a9ea6ccb54b518d，run23结果SHA52c5faaad4d67a30577a5b4bc6d564866627105d492ea37aabc31d5b5b5372ff。

所有源码、日志、结果持久保存在yuzelu@10.129.166.172本人/public/home/yuzelu/Melodydt/issue247-area-speed/run16至run23；全部作业终态，无自动监测。R3/R4共92大raw由retention索引明确服务器/本地归档保存，仓库核验内容和远端索引不混称。扩通道备份task/247-nexp4-area-r4@7048c35ed2912e80e62bd7827deaec480d4a7e1a及R2/R3备份均读回。追踪sacct -j 101884,101888 -X --format=JobID,State,ExitCode,Elapsed,NodeList。

非Git本地快照work/Melodydt/242/r-load-bounds/repo，远端task/242-r-load-bounds供PR243审查，未合并main。恢复第一步核对最新PR head、四轮报告/PDF及正式审查意见；已达到四轮停止条件，不自动增加第五轮。登记management-hub PR5 pending；缺board.json/Projects能力，看板unverified、同步pending，处理管理员/正式审查人待指定；GitHub CI以最终PR回执为准，不冒称通过。

## 第四轮RTL通过，实测费用接入旧体系（2026-11-10 Asia/Shanghai）

Issue247/PR243，Melodydt，in_progress；3/4轮完整交付。run22/101884/mdt-r4-nexp-rtl，源7048c35ed2912e80e62bd7827deaec480d4a7e1a，c64/node1/4核，5:45 COMPLETED0:0。21编译/63运行完成，85命令中82成功、3个LANES3定向拒绝；11门全通过，实测费用[7,7,7,7,14,14,14,14]。NX32四元素间隔9→7，完整U18→16，S仍5+5拍；n8仍两个真实n4。main SHA5abb31227f0c7b2c7ac9ff7eb8f80687569fab0b64bf74eb1a9ea6ccb54b518d，1122输出全哈希，106选中结果本地验。原日志和source在/public/home/yuzelu/Melodydt/issue247-area-speed/run22，30大raw由retention SHA索引另存；无活动作业/自动监测。

默认两lane完整事件、DIRECT0四lane与普通N兼容，外层全部65536 S16输入及状态/reset通过；实际native经clamp唯一32769值（全部负值+0），不冒称native65536唯一。扩通道备份task/247-nexp4-area-r4@7048c35ed2912e80e62bd7827deaec480d4a7e1a已读回；R2前态/R3大面积备份保留，SRAM未扩容。

round04模型六源已用真实profile审计、85日志SHA及9个篡改拒绝通过，冻结R2九生成源精确复现；正式SystemC尚未运行，不预填token/s。下一步提交/读回本模型源，在新run23进行16场景旧体系复评；第四轮PDF完整交付后按四轮上限停止。最高仍R2 ideal3.66958239533/shared3.37834376557，未到5。非Git快照work/Melodydt/242/r-load-bounds/repo仅根整合，远端task/242-r-load-bounds未合并main；登记pending、看板unverified/同步pending、正式审查人待指定，新物理资格/原生生成未验收。

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

## 新一轮提速迭代（2026-11-10，Asia/Shanghai）

Issue247/PR243，in_progress。R1正式U共享单N批处理已服务器通过，源e6d72113a14c5a0772f01ff5851d630d5d6687fa已上传/27文件Git blob一致。run16/101835 40秒、run17/101838 2:52，均c64/node1/4核COMPLETED0:0。16场景：主ideal3.63678454238(+4.0220%)、shared3.35052563236(+3.7054%)；prefill保留。133原件、89源成员、11输入、96回收输出SHA核验通过。首轮5页PDF及125内容单元/逐页视觉QA通过，1/4轮完成，第二轮复用N的单命令stateless relative-exp路径已选定，隔离实施中；正式R2代码尚未集成/运行。

目标仍主decode旧体系理想端口5 token/s或满四轮，SRAM不扩容；巨大面积另备份。原物理/完整模型资格不转移。当前无活动作业、无聊天结束后自动监测。下一步完成R2 RTL校准与旧模型配对，按目标继续迭代。[R1报告](../../docs/experiments/issue-247-speed-round1.md) / [机器证据](../../work/Melodydt/247/speed-iterations/README.md) / [接续](../../docs/handoffs/2026-11-10-issue-247-speed-iterations.md)。登记pending、Projects unverified/同步pending，审查人待指定，不done。

## 旧评价体系复评（2026-11-10）

更新时间2026-11-10T00:50+08:00，Asia/Shanghai；Issue247/PR243，in_review，待独立审查，不done。run15/101800，源3e62b85c8da19caca31784cb380c40d323295157，c64/node1/4核、00:03:22、COMPLETED0:0。固定旧S32/S96/K256模型、输入与资源，21完整场景历史字段、5生成文件SHA精确复现；225kernel/4validation/5smoke、7回执篡改/2非法CLI/源与历史SHA漂移拒绝通过。63回收结果SHA、63当前源和16输入绑定通过。

W8 decode512 3.063655→共享ctx8 3.230811（+5.46%），理想端口ctx8 3.496169（+14.12%）；W16共享ctx8略慢；48/64KiB prefill2 4.467001/4.547434。原生4×1RW不冒领理想端口结果，生产RTL未变、S不扩容。[报告](../../docs/experiments/issue-247-legacy-metric-evaluation.md)/[接续](../../docs/handoffs/2026-11-10-issue-247-legacy-metric.md)。本地非Git快照经本人租约上传，最终head/CI以PR为准；无活动作业/自动监测。下一步独立审查（待指定）；登记PR5 pending、看板unverified/同步pending，由管理员处理。

更新时间：2026-11-09（Asia/Shanghai）。Issue 是状态与验收的事实来源；本文件为当前任务分支摘要，不表示其他未合并分支已进入 main。

## 实施PDF与新版吞吐复核（2026-11-09 23:57，Asia/Shanghai）

本轮交付沿Issue247/PR243待独立审查（in_review），不done。完整7页[PDF](../../docs/experiments/pdf/issue-247-p-native-optimizations.pdf)固定源cf570ea69ff05b009c076b79414629b44a86d346，171内容单元和逐页视觉QA通过。源码、模型及证据已/待随最终提交读回，最终head以PR为准；未合并main。

三轮服务器测试均COMPLETED0:0，c64/node1/4核：run12/101767源e2b8c9f9，1:03，旧4场景全RESULT精确重现；run13/101769源eb8a40bc，0:14，实际P校准2后端×3初态共9336事件；run14/101777源b5ff1f708b1b1809bb78d5849d1f025dc5f3b6d1，10:34，9完整图case/4配对/4原生准入拒绝、168数值组/40884源乘积、6数值负例/6回执篡改拒绝全部通过。88策展原件、55回收输出SHA、164当前冻结功能源核验通过。全部作业终态，无活动作业、无自动监测。

固定300MHz/2P/1U/17.1GB/s的新条件模型：W8 decode512 0.06758220→0.08174053 token/s（+20.95%），W16 0.04491781→0.05052530（+12.48%），W8 decode2048 0.04826512→0.05507842（+14.12%），prefill2 0.07723904→同值。相同新接口ctx1→8增26.60%；ctx1比legacy退化4.46%。当前串行程序的仲裁/bank并发收益为0，不能把未实施调度收益叠加。

这些是条件时序仿真，不是完整原生RTL生成。原始trace仍需未实装的S32/S96适配器、图编译/DDR控制及候选U；每P额外2712B候选寄存器明确列账，S仍16KiB。原生整网token/s未取得。[报告](../../docs/experiments/issue-247-native-token-throughput.md)、[证据](../../work/Melodydt/247/token-throughput/README.md)、[恢复](../../docs/handoffs/2026-11-09-issue-247-token-native.md)。下一步独立审查与决定完整原生路径实施范围；负责人Melodydt，审查人待指定，登记PR5已读回open/unmerged为pending，看板无配置/能力为unverified/同步pending。CI以最终head实际回执为准，未改workflow绕过。

## 原生P前三项实施（2026-11-09，Asia/Shanghai）

Issue247本轮RTL与详细文档已通过验证，交付PR243待独立审查（in_review），不done。仲裁、固定16KiB bank并发、八组S64上下文+B-only已接入可选P参数，默认0；扩容未实装。run10/101756源码c2359bde、1:21，run11/101758源码24f720a7、1:05，均c64/node1/4核/COMPLETED0:0。15份生产RTL两轮相同；185轻量原件、163策展结果SHA与29当前功能源核验通过。管理结构/Python/JSON/链接检查通过仅在各自范围。

无背压local95→71拍；完整P含32拍释放，K59 2112→2032，K11 672→676退化。仲裁516→516、backend99→99总周期不变。run10的644拍仅输出前缀，不再冒领完整任务加速。[详细方案](../../docs/experiments/issue-247-p-native-optimizations.md)、[证据](../../work/Melodydt/247/native-p/README.md)、[恢复与作业命令](../../docs/handoffs/2026-11-09-issue-247-p-native.md)。真实DMA预取、控制镜像、整模型、面积/STA/P&R未完成。全部作业已终态，无活动仿真，未配置自动监测。

负责人Melodydt，独立审查人/优先级待指定；登记PR5已读回open/unmerged，pending；缺board.json/Projects能力，看板unverified/同步pending。源码head24f720a7的CI42636841207失败、无可用step结果，原因待管理员核实；最终head状态以PR实时回执为准。本地非Git快照，经本人tree/commit/ref租约上传，未自合并。

## 当前研究：结合 PR220/241 提高 token/s

- Issue247本轮融合/流水研究已交付PR243待审（in_review），负责人Melodydt。run09/101728源af9e43282c82ed8bc43cdaf3c2ec3c1ce8fc53b2，9:56 COMPLETED0:0，22完整trace/9默认全字段回归/12小trace/3非法CLI及原生24测量通过；run07/101720源1e6e10a7，21秒COMPLETED0:0，108项FIFO测量通过。B路线decode512融合+0.0214%、prefill2+2.2776%；原生32tile直连串行1440→FIFO1071拍。有限流水整图仅条件预测，生产RTL不改、SRAM不实装。run06/08失败保留。下一步独立审查与决定最小生产接入范围；异常取消/完整并发DDR模型/面积时序尚未验收，处理人待指定。登记pending、看板unverified/同步pending、CI见PR真实回执。无活动作业/自动监测。[报告](../../docs/experiments/issue-247-u-fusion.md) / [接续](../../docs/handoffs/2026-11-09-issue-247-u-fusion.md)。

- Issue247两路线比较已完成，沿PR243提交待审查，在线状态以Issue回执为准。run04源c597a7d0、101665/mdt-sram-rw、c64/node1/4核、8:02 COMPLETED0:0；57完整/6尾块/4非法CLI、先20历史回归通过，149回收SHA。run05源49b3938c、101672/mdt-sram-policy、同节点4核、3:58 COMPLETED0:0；30完整/先12默认回放/2非法CLI/每case6负例通过，81回收SHA。两轮45轻量证据、run04/05各44/49功能源一致性通过。没有活动作业、没有自动监测。
- 容量联动的默认预取使A48/64 decode慢于B；只固定预取判定后W8/context512 A48/A64=3.541567/3.543921，B=3.496169，增量1.30%/1.37%；W16/长context约1%至2%，prefill2 A48/A64=4.467001/4.547434，对B+20.84/+23.01%。若只有大容量端口升至1.25拍，A64=3.490348低于B1拍；真实端口/面积/频率待验。decode且保持S预算优先16KiB路线，prefill保留48/64KiB候选。SRAM扩容不实装，生产RTL不变。[报告](../../docs/experiments/issue-247-capacity-port-compare.md)/[接续](../../docs/handoffs/2026-11-09-issue-247-capacity-port-compare.md)。
- [Issue247：固定SRAM的面积换速度研究](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) 已按顺序完成五方向首轮研究，沿task/242-r-load-bounds / PR243交付待审查；在线实际状态以Issue回执为准。仅隔离模型/实验RTL；生产RTL未改，SRAM扩容保持不实装。每P16KiB；第三P额外活跃私有S预算明确单列。[正式报告](../../docs/experiments/issue-247-area-speed.md)。
- 第一阶段源码9015effa13879bf8b5779905a4c83f53af8f2085，Slurm101631/mdt-area-speed、c64/node1/4核，4分57秒COMPLETED0:0；35完整trace、480数值配置/120生命周期/20错误注入、原225kernels/4validation/5smoke通过，92回收输出SHA一致。W8旧组合ctx8/16分别3.230811/3.243464（增量+5.46/+5.87%），原调度和W16退化；switch3/8退化，prefill不触发。结果/public/home/yuzelu/Melodydt/issue247-area-speed/run01/results/result.json，SHA62c787396bd331cb2c6d8a0a4352a4ebb83456616eb141bc50c33655d84f3fc3。
- 第二阶段源be603f4d7661dfc3a42c17d797e1ce74772284c3，Slurm101635/mdt-area-feed、c64/node1/4核、24秒COMPLETED0:0。空P审计修正后，实际C++21候选/6基线/5非法参数通过；阶段1生成C++逐文件SHA保持。独立link三种随机初始化各四例和提前完成负例通过，256拍128→256beat；原P程序两版本各三例均288拍，没有程序级改善。Nangate配对link映射面积4178.328→9085.762（2.1745倍，仅link综合，无P&R/STA）。85回收SHA通过，结果SHA cc7a4aceeef4b1d53c19229c686a8beb909f22b4ce66390ce8db6a5f3cddfba0。
- 第三轮源45e45bf75f35ebf35111f525de655076f7e122be，101638/mdt-area-hw、c64/node1/4核、4:42 COMPLETED0:0；21完整case按端口→第三P→向量顺序通过，默认结果完全回归、读写端口工作守恒/负例通过，65回收输出SHA一致。W8同容量1R1W+7.75%，组合8contexts为3.496169（对前轮最佳+14.12%）；W16单双端口+8.33%，context2048+6.09%、prefill2+18.97%。三P原均分W8−14.46%，vector8/16单独+2.41/+3.66%；不叠加未测组合。
- 56完整trace（含基线）+32边界调用及RTL研究交付，63轻量证据/50最新功能源SHA核验，三轮242回收SHA一致；[索引](../../work/Melodydt/247/index.json)/[交接](../../docs/handoffs/2026-11-09-issue-247-area-speed.md)。无活动作业、无自动监测。下一步独立审查研究并评估实际P同容量读写并发合同/面积/时序，负责人待指定；新S32、真实权重/KV/DDR/物理/能耗未验收。登记pending，看板unverified/同步pending，管理员和独立审查人待指定；CI以PR实际失败/待核实回执为准。
- 用户当前决定：**SRAM扩容研究保留，暂不实装**；Issue246既有结论与证据保持。Issue247首轮研究已交付，后续优先验证同容量P读写并发，不启动48/64KiB生产S实现。

- [Issue246：P私有S容量](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/246) 沿PR243待审交付。[报告](../../docs/experiments/issue-246-sram-capacity.md)：W8/context512两P从16→64KiB，原调度+7.13%，前轮组合上容量增量+11.05%；48KiB已近64，128KiB该decode无新增收益。prefill2+21–23%，端口吞吐成本可能抵消容量收益。43KiB只是A，保K256至少W8 48.09375KiB/W16 52.09375KiB；真实S地址/描述符/1RW仲裁及新物理资格待实现，不改生产RTL。
- 246已测源8b18e0cb3efd3e8558d9930132282fbe551caf4e，Slurm101620/mdt-sram-cap、c64/node1/4核/UNLIMITED、4分02秒COMPLETED0:0，28case/16KiB完整结果回归/225kernels/4validation/5smoke/负例通过；35回收输出SHA匹配，四源码/15依赖保持。负责人Melodydt；待独立审查合并、不done，CI以PR回执为准，登记pending/看板unverified与同步pending。48/64KiB真实S_P实装按用户决定暂缓，保留研究候选；[恢复入口](../../docs/handoffs/2026-11-09-issue-246-sram-capacity.md)，无活动作业、无自动监测。

- 详细P/DMA专项 [Issue #245](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/245) 沿本PR243交付待审查，负责人Melodydt；原#242/#244独立待审范围保留。来源241@e7aeed20、220最新只读3a9f98a9；[详细报告](../../docs/experiments/issue-245-p-dma-study.md)。
- 已完成服务器26+18+18次完整trace执行（含重复基线），101612/101614/101615均c64/node1/4核/UNLIMITED/COMPLETED0:0。原版与仪表所有原指标、上游W8/W16基线精确一致；每轮225 kernels、4 validation、5 smoke、软件oracle及独立守恒审计通过，后两轮7个篡改拒绝通过。91份回收输出SHA通过，15份最终功能源与已测727f297cd0ec3436e108e351aad5799c013c0338一致；101611编译失败保留，-Werror未弱化。
- 发现W8权重占总线85.60%，A占11.90%，A的94.63%来自FFN下投影；原有驻留不重复记收益。有限前缀+1.10%；真正主要改善是按完整A驻留容量选择预取策略，单独+10.74%，叠加前缀/列组/512B写合并到3.063655条件token/s（+12.86%）。同组合context128/2048为+13.96%/+10.08%，prefill2吞吐+8.27%。W16仅容量策略1.871684、+11.27%，优于组合。全局关排队/减信用/单缓冲/小K负结果保留。
- 边界：同组合总线只减2.15%，17.1GB/s下必要上限4.84811仍不足5；容量策略切换/指令成本尚未实装。没有生产RTL变更、真实模型生成/新量化KV、DDR/物理/能耗资格。下一步优先验证有限预取与S消费者仲裁合同，再决定前缀/写合并硬件；实现负责人及审查人待指定。研究交付in_review，待独立审查/合并，不done；CI、登记pending、看板unverified/同步pending见PR回执。
- [本轮证据](../../work/Melodydt/245/README.md) · [恢复交接/作业命令](../../docs/handoffs/2026-11-09-issue-245-p-dma-study.md)。本专项无活动作业、未配置自动监测。

- [Issue #244](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/244)，负责人Melodydt，研究交付进入in_review；用户指定复用 `task/242-r-load-bounds` / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，待独立审查与合并，不done。
- 已读取最新PR220 `bf31827f7e039038ca2547046a13d29c4bf46901` 与PR241 `e7aeed2097f57a5f910cae70eb51a220c49a8a14`。形成[提速研究](../../docs/experiments/issue-244-token-throughput-study.md)：既有硬件改配方/有限S跨元素状态；新候选优先P/DMA流量、通道计数、2P/3P同带宽消融，后端/硬件/算法收益分账。
- 实际验证：900个图情景与独立路径穷举一致、关键链切换、五个非法/篡改输入拒绝；34组上游结果的算术/容量/阶段核验通过。本轮没有重跑这34组SystemC，没有修改生产RTL，也不转移物理/量化资格。
- 核心条件：241候选W8/context512约2.7146条件token/s；现流量/17.1GB/s下上限4.7438。达到5至少需减184.728MB/token，且其他阶段不变时Dot服务至少提速2.2195倍；不是已实现收益。
- 服务器 **101608 / mdt-tps-study**，代码 `81dfbd0e6e6d1432447750d5b2d4a106e2d786b7`，c96/node13、4核、22秒、UNLIMITED，**COMPLETED0:0**；`/public/home/yuzelu/Melodydt/issue244-token-throughput/run03`。复现旧attempt277图、完整图逐字节匹配，六源码/六回收输出SHA通过；服务器900情景/拒绝检查通过。101601因CRLF清单在读取源码前失败，LF重跑保持源码/校验不变，原件保留。
- 下一步：独立审查报告与研究工具，按报告验证可执行候选及真实KV质量；审查人/跨任务实现负责人待指定。本轮研究未取得新执行配方、RTL/物理/能量或实际生成速度资格。登记pending、看板unverified/同步pending，CI以PR实时失败/待核实记录为准。
- [交接与结果位置/追踪命令](../../docs/handoffs/2026-11-09-issue-244-token-throughput-study.md)。本任务无活动作业，未配置自动监测。

## R 原始 LOAD 边界修复（独立验收）

- [Issue #242](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/242) / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)；主要负责人 Melodydt；当前 in_review，待独立审查及合并。
- 分支 `task/242-r-load-bounds`，基线 main `c4d7b960599b9d292f27eb4429d5f226a7156c95`；已测源码 commit `f034be2b7c87137b92f7bfce274a5485647e512d`。
- 已完成：R 原始端口按目标/容量检查完整索引，阻断地址截位别名及非法操作数更新；保留已有 C 地址错误合同。c64/4 核数组 101572 全部 COMPLETED 0:0；两容量及 C 适配器 9/9 正向通过、旧源码 3/3 检出缺陷，源码及 12 日志 SHA 核验通过；管理结构/运行器语法检查通过。
- 本地独立源快照：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`（非 Git checkout）；服务器：`/public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01`，节点 node1，无活动作业。
- 交付：文档/证据提交 `ea9fcefbc166c649a36e17878823fdd1de29f766`，链接回执提交不改已测源码，最终 head 与 CI 以 PR 记录为准。下一步为独立审查与合并，审查人待指定。新 RTL 的原 192 项最终网表回归、综合与物理重新验收未执行，后续如开展须另定负责人及范围。原物理结果不转移资格。
- 协作接入：登记管理中心 PR #5 pending；看板 unverified / 同步 pending（无 board.json 与 Projects 条目工具），管理员待指定。
- [实验与证据](../../docs/experiments/issue-242-r-load-bounds.md) · [可恢复交接](../../docs/handoffs/2026-11-09-issue-242-r-load-bounds.md)。

## 其他本人任务入口

- [#232](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/232) / [PR #233](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/233)：main 完整性与 RTL 审查；本任务承接其中 LOAD 缺陷，另一处母控超时仍按原任务记录。其完整审查资料在对应分支，不据本文件推断审查/合并结果。
- [#179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [PR #180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)：独立任务及仿真/规则进度保留在其分支，本轮未修改该目录和任务状态。[已读取的个人进度快照](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5a691e182466fb4a2d48da7ca31a1ae6ed9156ba/progress/Melodydt/STATUS.md)，最新状态以其 PR 为准。

本文件新增于 #242 分支。合并多个待审 PR 时保留各任务最新记录；不以新分支中的简短交叉索引覆盖既有详细实验与交接。
