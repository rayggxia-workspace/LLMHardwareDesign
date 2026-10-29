# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

当前检查点：2026-10-29T00:22:14.585912+00:00，取代旧的“93067运行中”。阶段一pass_with_inherited_issues；阶段二/三未验收、四NOTRUN，主要候选1/3 **UNFROZEN**。同一Issue55/task/55-full-block-integration/草稿PR58，不新建、合并或关闭。

**完整目标不变。** 两完整硬件案例使用资源并集；冻结后计算/状态/存储/控制、预置有源资源、位置/朝向、内部实现、固定预连线、PG/clock和M8接点相同。M1–M8固定，M9/M10及真实via8/via9定制；M11/M12为未启用独立后备。open=otpu_asic_top全部33内部SRAM；LL=EPILOGUE_FUSION0/DMA_MAX_OUTSTANDING16，16外SRAM bank/DRAM/主机参加功能测试、不计core面积。不缩硬件、不加流水、不放宽3ns，不动原四核心。

**保留的限定通过。** 93016新增62BUF_X2合法放置、原546397实例/全部导体阻挡保持与实际off-site负例通过。93022新旧实际网表65545状态/168074状态输入输出锥一致，真实状态输入破坏检出；是声明模型/BUF-drive-inverter归一化下的命名锥证明，不是新完整整机/四态/SDF/所有输入证明。93058完整新driver源UNROUTED PG/放置预查placement0/VDD1/VSS1通过，不代替最终route PG/全DRC/IR/EM。93056完整准备来源核查和15来源帧破坏拒绝通过，失败route本身不接受。

**93067新实际失败，未启动详细布线。** Slurm FAILED1:0/4，wall958s/CPU3409.502s≈3.559核。复用原完整prepare、124targets/62splits与全保护的native PA完成，标准单元NoAp0；但逐真实BPin矩形守卫在第401行遇到 **bit_118的M8矩形AP=0**。原坐标[2018990,-6660,2019790,-5860]DBU。严格失败发生在route__global_handoff，**没有handoff.odb，也没有fresh-detail进程/最终migrated.odb**。保存的selected.guide只是guide，不是实际线路。回执/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-fixed-position-driver-stages-route-r03-saved-PA-4c-01/execution.json，SHA 8a5b1c6e1481d821d81ea0dab8289f9050ebf2082c8426b243957d7c0fd110e7。原始输入哈希不变，失败记录不覆盖。

此前93053两个完整native PA实际完成但记录器独占写文件冲突FAILED；93065只读封存输出复核完成、未重跑PA，49报错口都有M8 AP且保存坐标相同。“重复OBS令这49个保存M8点消失”不受实测支持；不能推广成全部13507口已覆盖或方向标志/worker可达性相同。93067更完整的守卫发现了49口之外的问题。93018原DRT1231失败、93024/26/29/34/36 child_launched=false/实际五项业务NOTRUN均保留。

**完整上下文与工具对照已实际执行。** 93071只读prepared源（不是失败后未保存的PA运行时）：13507个M8盒；3283个含负X、3424个含负Y；全部都有实际X/Y轨道，bit118也有。不能简单归因于“无轨道”或“负坐标必然失败”。回执SHA f3c58dd08403c74e8601bc7202296270e95d13d8b465b69117ff4b43a3bae78b。
93078七个独立工具夹具：同一负坐标M8盒单独作为PORT时原生PA有AP；和原M6盒合进同一PORT时M8缺AP；保持全部track相位的正Y平移对照恢复M8 AP；合并轨道记录不恢复原双盒案例。只改变夹具输入，不移动或修改原始完整硬件；不是完整Block通过，也未证明排他根因。回执SHA 19633c3d2c42cd4f71760d7f1238764bf1b3cf4883add11a0c1f2ba67f658e2a。
93081只新增两项独立PORT分组对照（未重跑七项）：**两项原生PA都报DRT-0302 Unsupported multiple pins on bterm**，即使正坐标也失败。Slurm COMPLETED仅表示观察脚本记录完原生失败；不称PA通过。不采用该方案，未对完整源拆PORT。回执SHA 09fef4f4989d9dad26d57f639bba36f0c6117beaf846247c5991a67b9a8c5feb。
93087只读实际AP方向API：单M8夹具原生点有四个平面方向、UP/DOWN=false；旧getAccesses无输出vector调用不支持，不伪称读到方向等价。没有创建/补写AP或生成新硬件接线。

**消费者程序边界。** 新driver_saved_PA_handoff_review把后续RC/回归绑定实际handoff与独立reload、全BPin盒/原OBS/保护和完整源；整体新路径尚无成功producer可验证。93069仅用真实完整13507端口/13507原生单box记录检验读取器，八类真实数据破坏（缺口、错net、零AP、重复盒、退化尺寸、错误BPin索引、假inside、错误总数）均拒绝，输入未改；wall1s/CPU0.522s。不是新handoff/路由/RC/功能通过。回执SHA e16bc2f178a3284d57e7e43b2e2177c793574173b66683a6b23a7fab6dddedfd。

**当前实际动作93086：RUNNING，4核。** 目录/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-driver-complete-native-PA-state-capture-r01-4c-01，源码22d307b170d2b6ba22545cf5fb53cd9e4cc93bbb。93067仅留首个失败前401行、没有可恢复运行时DB，本次新增完整BEFORE_PA/AFTER_PA/AFTER_GRT观察、明确UNACCEPTED诊断DB及独立读回，不是重复提交同一布线。完整原硬件/124网/全15,489,424重复保护保留；只在原生PA/GRT观察后停止，**不执行详细布线、不接受失败端口、不把诊断DB当candidate**。当前闭合与否以receipt为准，保存脚本完成不算实际保存完成。后续先依据完整证据选接入处理；原PIN/导体/OBS不删、不隐藏，不把接点元数据当真实布线证明。

**其余主线仍待。** 92548现RUNNING4核，继续不停止/重提。14059固定预连线有规划和未闭合实际布线，无最终独立实际导线验收；每case841模式相关闲置扇出、当前191父版PG/clock/固定线/完整功能未统一。旧未加62buffer的M8 AUX原3ns setup5691/WNS−1.5718422563995755ns、hold36/WNS−0.24845087801435276ns、cap1104/slew0质量拒绝；不是新driver测量。VECTOR新增4cap恶化及e238对原版200setup/26cap退化未解，不用epsilon或时钟/复位豁免。外clock rise/fall、open37常量输出负载仍用户未确定/null，不填0。

旧完整原父层LL六组180任务/243883行/17769493字段/540份1MiB镜像、旧open20例及active+idle只绑定各自版本，不能转移为新driver/当前191/最终共同底座通过。下一步读93086完整诊断、核实可行接入处理并实际完成124网原位约束下的线路，再做全连接/接触/fresh DRC/PG、RC/全部端点电气与新完整回归；统一全部资源后才freeze并验证两个完整案例M9/M10定制。

唯一根/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z；review源码1b8f149691558d399c64157de46904b00e54e38e；最新索引/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-complete-BPin-gate-failure-and-tool-controls-20261029T002214Z/milestone.json，SHA e0c18451d44b8f6026ab86e6dc05a3f0b38df860006c2eb1fe8aa4ac3245270b。所有driver保留source_revision/spec/submission、输入/工具/成果SHA；OpenROAD版本unknown，binary SHA0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。新任务4CPU/native≤4/BLAS1、阶段串行；微型检查/PG常约1核，不称4倍提速。大ODB/DEF/SPEF/日志/trace/工艺留服务器；旧六文档全文在索引previous_documents。结果summary收紧为小型事实索引，旧完整JSON仍封存服务器，通过父索引和SHA追溯。六份记录发布另存独立delivery receipt；当前远端1c1daea核实open/draft，服务器后阶段源码不等于已完整远端交付。登记复用管理PR5 pending未重核，board.json缺失/Projects unverified/同步pending，审查人待指定，Issue仍in_progress；不动四个保护dirty文件。
