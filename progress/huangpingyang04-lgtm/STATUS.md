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
