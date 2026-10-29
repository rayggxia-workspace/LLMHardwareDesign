# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

更新时间：2026-10-29T02:12:20.108872+00:00。以下覆盖历史状态，以封存索引及实际Slurm为准。

当前完整目标保持不变：阶段一 pass_with_inherited_issues；阶段二/三未验收、阶段四 NOTRUN；主要底座候选 **1/3，UNFROZEN**。同一资源并集冻结后必须保持实例、位置/朝向、内部实现、M1–M8、固定连接、M8接点、PG/clock和有源资源一致；只允许案例定制 **M9/M10及真实via8/via9**。M11/M12未启用。open=otpu_asic_top及全部33内部SRAM；LL=EPILOGUE_FUSION0 / DMA_MAX_OUTSTANDING16，外16 SRAM bank/DRAM/主机属功能环境，不计core面积。不缩规模、不加流水、不放宽3ns。

**本轮实际新结果**
- 93115 COMPLETED0/4：保留43862个原生AP，增加1642个明确标为软件几何候选的M7轨道/M8轨道交点，共45504个AP；完整13507端口/27014盒的输入检查、独立读回、实际禁用方向/删除AP负例闭合。没有移动引脚/器件、增加金属或删除原PIN/OBS/导体。**这是路由输入准备，不是完整native PA通过，也不是布线/DRC/功能通过。** wall46s / CPU44.562s，约0.969核；回执SHA ee54aa82c290770d6c9868d7b8adfbc02c642197680a79344e0be404e0cd6f68。
- 93116按4核实际运行完整546459实例、124目标网、62拆分、15489424保护矩形的详细布线。已进入原生迭代，运行中观察的短路数仍非零，**没有终态或物理通过结论**；日志全设计线长/通孔总数不能当新增目标成果。原3ns及全部保持性/连接/异网接触/fresh DRC/PG门槛保留；不停止或重复提交该作业。
- 93119 COMPLETED0/4：独立导出失败92548快照全部13张原生表，包括全部master PIN/OBS，逐表压缩字节完全一致。完整14059目标有737455个guides矩形、**目标实际wire仍为0**。只证明保存的原几何没有变化、可作为未布通输入；GRT-0116拥堵失败未变，不是固定线完成。wall785s / CPU792.767s，约1.010核；SHA afe22097d318c124ce06897b085d5626f2801c35d70ef0acd95563773c70a654。
- 93121 COMPLETED0/4：读取全部选中网络的真实引脚/guide，61个目标M8物理盒都没有同层重叠guide，M5/M6盒有覆盖；实际移除guide负例检出。这是搜索引导缺口，不是DRT不可行证明。
- **93123 FAILED**：小夹具的原生DRT退出0、DRC0，但没有实际导线，断线负例未检出。原因已定位：旧几何检查只要求每个逻辑端口有共同分量，不能保证同一BTerm的全部分离金属形状已连接。原文件保留，不采纳临时重复M8端口方案，不把旧PASS扩张成完整物理接口证明。
- **93124 COMPLETED0/4**：新增独立的公共端口物理岛门槛；新原生数据库中，用真实via5_0/6_0/7_0和导线连接原M5/M8盒，独立读回通过；实际删除整段导线后失败，两份旧零导线夹具也正确拒绝。wall5s / CPU1.963s。**只资格化检查器；正例导线是小夹具内显式构造，不是全设计DRT或DRC通过。** 93116封存源码不改，其后续结果必须补用该门槛，不能只读旧几何PASS。

**仍失败/未执行。** 92548固定预连线拥堵及862354溢出格未解；93101原生M8接入仍缺1642，软件候选不能抹掉该事实。93111坐标API、93114同进程载入第二DB等软件失败保留，修复只在新版本/目录。旧62BUF合法放置、65545状态/168074锥差异0、源PG预查及旧完整两案例回归只对各自版本有效；新124网布线、当前191父版完整功能、电气、固定/闲置/PGclock与最终共同底座尚未闭合。旧RC等child_launched=false仍为NOTRUN。旧AUX/VECTOR新增或恶化时序/电容不能归入继承问题；外clock rise/fall及open37常量输出负载仍null，不设0或epsilon。

**下一步最小行动。** 保留93116自然运行；用实际保存数据库及严格公共端口岛检查判断是否真实接到M8，并完成原保持性、短路、DRC、PG后才允许RC/新完整功能。若失败，按真实断点修复固定引出/局部接线方法，不靠AP标签或重复逻辑端口掩盖断线。复用93119封存的完整快照及guides评估后续实际固定线布线，不盲目重复6小时GRT。所有条件达到后才冻结同一底座、进行两完整案例定制。

仅精选既有记录入库；大型ODB/DEF/SPEF/完整日志/trace/工艺留服务器。新作业4CPU、原生线程≤4、BLAS1，CPU时间与申请分别记录；本轮无在线换核、未停/重提活跃实验，不改原资料/封存结果/其他成员/受保护dirty文件。rayggxia-project-collab1.0.0；登记复用管理PR5 pending，board.json缺失/Projects unverified/同步pending，审查人待指定，Issue55继续in_progress。

服务器唯一根：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

最新完整索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-explicit-M8-input-and-physical-island-correction-20261029T021220Z/milestone.json
SHA-256：1b15b26cc1e7c8860063ad7b2f05da504212c907d88bdbe0d3f9bc6f91f370ff
复核源码：585a6a4e2c8afd8b4cc1a482d1497518fb92e330；各作业源码/spec/submission/输入与工具SHA见索引和封存execution。OpenROAD版本unknown，binary SHA0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。


### 实际DRT违规与接入反馈：2026-10-29T03:00:06.921596+00:00

本次更新后的实测补充（以本段最新记录覆盖上文运行中观察）：
- **93116 的详细布线阶段已正常返回，但原生 route.tsv 与 route.drc 均报48个M2 Short类型标记，不能验收为通过。** 44项带temporary-OBS来源，4项明确含两条网络；不能把48全部当作最终独立电气短路，也不能豁免这4项。原生报告SHA917ad6e27779439f908530597216c4bf6fa58ff5bde7efec6f5f408f79a36014；route.tsv SHA8ebe95f21466777b463a4571e3b33700b01c5656a4d7586c6107c0a99a67c5f1。真实候选ODB/DEF/v/SDC已保存在原run/route/，未冻结。作业仍RUNNING：新进程已完整导出623281网，保持性/连接/fresh DRC/PG后查尚未闭合；自然终态和最终SHA以后续execution为准，不停止、不重复。
- **93145 COMPLETED0/4**：流读全部546459实例，对全部48个实际marker按精确DBU定位，48/48都与新BUF_X2区域相交，0与原driver区域相交。是区域归属，**不是精确PIN/via/障碍所有权或排他根因证明**。wall4s/CPU3.367s，单线程；回执SHA6f709cf14f4f5797f263c727f034d93571ef121e82c4cdc252d24b5dbdf0e2ec，目录runs/auxiliary-closed-DRT-marker-cell-attribution-r01-4c-01/。
- **93130 RUNNING/4**：完整191父层、14059目标、6225真实公共PIN的保存native AP检查通过，实际track assignment已完成，详细布线0th迭代已开始。只复用资格化的原失败快照/完整拥堵guides，未重复PA/GRT；旧GRT失败不改为通过。源码f21c44e0b8800db66b6487ffaa22fda7feedf913；目录runs/complete-fixed-parent-saved-guides-fresh-DRT-r01-4c-01/。
- **93131 PENDING，申请4核**，等待93116自然终态后补严格公共BPin物理岛门槛，缺完整候选就NOTRUN。源码35712838705cef0b93865f0ecb0f2316825247a6。没有提前放行RC或功能。
- **93136 COMPLETED0/4**：完整流读16490071原始形状，61/61原M5/M6→M8端口已由原导体/过孔连通；原via7几何内存移除负例检出。wall92s/CPU89.477s≈0.973核。SHA3c3b400e5d724bdcf9b5a230a5eca3b42c69f86d9c7cc50817b844dd3483c183，目录runs/original-public-pin-retained-escape-components-r01-4c-01/。这是原线路诊断，不是新保留/投影算法已实际布通。

下一步按失败证据检查新增buffer的M1→M2接入与原固定导体，评估接入感知的位置选择；已有DPL通过只证明不重叠/在合法site，未证明第一层过孔可接入。并评估保留原61段已连通M5/M6→M8引出，只重布变动部分。**这些方法尚未实施或物理验证**；不得靠删原导体/OBS、缩硬件或只改AP元数据解决。旧作业继续后查、新版本只在本任务新目录，全部原有保持性/物理/电气/功能门槛不减。

候选仍1/3、UNFROZEN，二/三未验收、四NOTRUN。两个当前运行中作业均4核；新增诊断主要单线程，如实列CPU时间。source/配置/工具/输入SHA及不可变的前次记录归档见最新索引；大DB/完整日志/工艺仍只留服务器。

最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-actual-DRT48-marker-and-escape-feedback-20261029T030006Z/milestone.json
SHA-256：eea4a5f39f0f6355cd43fc4ad5bf78017f11d0dd998086d3eabafb950d24cb84
复核源码：9b937a2489570438013b05c378477cdfbaf25d27。
