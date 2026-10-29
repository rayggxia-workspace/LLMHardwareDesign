# huangpingyang04-lgtm 的进度

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。阶段一已交付；二/三未验收、四未执行；主要候选1/3，无冻结。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

- open原20例、三seed两次host任务、162 VPU/控制与120 MM/QACT有限回归及独立证据通过；LL180连续任务/540完整内存通过；不是全输入证明。
- 当前两辅助state-cone/M8/RC锚点/抽象PIN/OBS/model link资格通过；新辅助时序与VECTOR新增/恶化未解，不归继承。另一全规模LL候选布线92018继续，不重复/停止。
- 92044方向bug、92071 cut间距、92078旧图断开失败保留；92085新点集fixture/92087规划通过，没有放宽规则、移动Block或切换M11/M12。
- 新任务4核，线程匹配。92063用7:04/CPU8:31.805，均1.21核；92064用13:21/CPU13:30.398，均1.01核；92026用25:08/CPU25:11.394，均1.00核。未停止/在线切换旧作业，不称四倍提速。
- 恢复先读最新milestone与driver/submission/source_revision/spec，再核对sacct，避免重复。92026新源PG独立检查、92063全六资源held-reset、92064当前13局部接入已各自通过；核查92087完整5网原生读回和92018候选完整布线。继续active+idle任务/物理parking、时钟质量RC及新增时序问题，再冻结和两完整案例M9/M10定制。freeze/route仍未实现，无阶段二/三/四验收或新远端push。
- 远端仅阶段一，无新push；登记pending、看板unverified/同步pending、审查人待指定，不合并/关闭。

<!-- current-buffer-PG-status -->

更新时间：2026-10-29T04:13:47.859996+00:00（UTC；中国时间加8小时）。本段为当前结论；历史快照与上版六份记录完整归档在下面索引中。

**目标与冻结边界。** 两个完整案例使用同一资源并集。冻结后实例、位置/朝向、内部实现、M1–M8、固定预连线、M8接点、PG/clock和有源资源必须一致；只定制M9/M10及真实via8/via9。M11/M12未启用。open为otpu_asic_top及全部33内部SRAM；LL保持EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，16外部SRAM bank/DRAM/主机仅属功能环境。不缩规模、不加流水、不放宽原周期。当前主要候选1/3，**UNFROZEN**；阶段一pass_with_inherited_issues，二/三未验收，四NOTRUN。

**实际完成与失败：**

| 实验/作业 | 终态及严格证据边界 |
| --- | --- |
| 旧完整AUX详细布线93116 | FAILED1:0/4。完整546459实例、124目标、62拆分、15489424保护保持。独立新进程全片DRC **89**（44 M2 Short、45 M3 MetalSpacing）；目标对全量导体 **55个异网形状接触对**，不等于55个唯一短路位置。原实例/master/PIN/OBS/非目标导体、PG/clock保持；placement/PG拓扑通过，但信号物理失败。原DRT内部48标记不是最终89的替代。 |
| 公共端口复核93131 | FAILED1:0/4。独立读回完整源/13表，**61/61公共M8端口存在未连接物理岛**；旧逻辑端口连通检查漏项不能作放行依据。 |
| 接入感知位置规划93160 | COMPLETED0/4。2220个候选姿态，62个既有新buffer中58个位置需调整、4个保留。按真实行/轨道/PIN/OBS/过孔及完整原导体检查；规划自身不是native接入通过。 |
| 实际新放置93162 | COMPLETED0/4。新位置实际写入派生ODB并独立读回；原546397实例全部保持，仍为546459实例/62新buffer。原导体与PIN/OBS保持、实际DPL0、离开合法site的真实负例检出。**只通过放置，不是布线/RC/功能。** |
| 全部新buffer首过孔93165 | COMPLETED0/4。完整原设计背景下实际写入124个via1_4；全部62区域native DRC标记0，重新读回124个via身份/位置，真实异网短接负例检出。原新UNROUTED源placement/PG拓扑通过。诊断副本仅移除声明的124条可变普通信号线；非目标导体保留。**这是全部新buffer的局部首过孔接入，不是全片信号布通/最终DRC。** |
| 保留固定线方法93164 | COMPLETED0/4。小型真实N45夹具中，将原固定导线投影成临时障碍、实际布新线、精确合并回原几何；全部11原形状保留，公共物理岛连通，新进程DRC0，实际删线负例检出。**只证明工具方法，未完成全61引出/完整124网布线。** |
| 完整固定线93130 | **RUNNING/4**，已完成native track assignment、进入详细布线；没有最终结果。14059固定目标/6225真实公共PIN，未重跑PA/GRT；使用旧版AUX来源，后续新58位置版不能直接继承。 |

旧93157（guide单位DBU误用导致分配失败）、93159（直接保留FIXED线未补通）、93163（增加ROUTED端点seed仍未补通）全部原样保留；未采用这些失败方案。新方法93164实际使用DBU和精确固定几何合并。旧93123临时重复M8端口漏检方案未采用。软件AP候选/路径规划/guide均不等于实际完成布线。

**资源与耗时。** 所有新任务申请4核、原生线程≤4、BLAS1，总进程受实际cpuset约束；未停止、在线变更或重复提交任何运行中实验。93116 wall6718s/CPU18413s，平均2.741核；93160 128s/127.450s≈0.996核；93162 951s/952.567s≈1.002核；93164 7s/3.721s≈0.532核；93165 640s/638.029s≈0.997核。这些规划、放置及局部检查主要单线程，**申请4核没有被写成4倍加速**。93130运行中CPU快照见索引，不将未结算TotalCPU=0当作无运行。

**未完成/阻塞。** 新124网完整布线、完整61固定引出保留/回装、全片连接/DRC、实际RC/时序/新版本完整功能均未完成；旧AUX/VECTOR新增或恶化的电气/时序未解决。14059项固定预连线仍未取得实际布通验收，841闲置sink/每case、当前191父版统一PG/clock与active+idle尚未闭合。外时钟rise/fall和open37常量输出负载由用户确认未确定，保持null而非0。旧功能/状态锥证书只对绑定版本有效，移动/布新线后不得自动继承寄生和功能验收。

**下一步最小行动。** 保留93130自然运行；以93162新源和93165接入证据，适配93164已资格化方法，保留原61条M5/M6→M8引出，在新独立目录实际重布完整124目标。所有原保持性/严格公共物理岛/异网接触/全片fresh DRC/PG门槛仍必须通过，之后才做当前版本RC/电气及完整功能；仍不冻结或进入阶段四。

服务器根：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z
当前实现源码：aafb7a5593c6bb74d2dba12dfda72ea6b4abda7d。各作业source/spec/submission、输入/工具/输出版本、大小和SHA见不可变索引。
最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-closed-failure-and-qualified-first-via-20261029T041347Z/milestone.json
索引SHA-256：938cb2b23fca5489ad697ba85205a1273c198e2136bc2631fef3a27e7050d7f3
关键回执：旧AUX FAIL 1ba9fba9ccfb8c3da7e1b48009026b5a58e11a6faaaa7d680eb61364c81a7f9b；新放置 6eafb75bfafdbd863d7b57da81d2618a3458832a8791c875f1ba5668778c5c52；全部62首过孔 c638f76850c9cc5addfd2f2cfbeabe567aa918860caf1e4b638b3419108d4fc4；固定线工具方法 7157b67d8b733b3ce5516a72717c5fe9f01437ca366eaaefc64a7e3950daaf72。
旧失败实际ODB：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-fixed-position-driver-route-r04-explicit-M8-4c-01/route/migrated.odb（872526222bytes），SHA 001b06bc9d0ed2578c8f3f3c884428c02e77bf043ae47b4c72f8f83e85d3ecc1。
新UNROUTED放置ODB：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-access-aware-driver-stages-placement-r01-4c-01/driver_stages_placed_UNROUTED.odb（710445317bytes），SHA e6e350524915f2d64866ffffa1cad40218d376df7f7d372e12e7c775e17acbc2。

仅六份精选既有记录入库；大型数据库/完整日志/工艺继续只在服务器。rayggxia-project-collab1.0.0；登记复用管理中心PR5 pending；board.json缺失/Projects unverified、同步pending；审查人待指定，Issue55继续in_progress。本次结构检查通过，不代替以上业务验证。
