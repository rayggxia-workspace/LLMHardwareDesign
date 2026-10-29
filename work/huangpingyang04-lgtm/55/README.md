# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

当前检查点2026-10-29T01:03:14.503334+00:00，以本段及最新索引为准。完整目标不变，阶段一pass_with_inherited_issues；阶段二/三未验收、四NOTRUN；候选1/3 **UNFROZEN**。

**同一底座边界。** 两完整硬件案例采用计算/状态/存储/控制资源并集；冻结后资源、位置/朝向、内部实现、固定预连线、PG/clock和真实M8接点完全相同。M1–M8固定，只定制M9/M10及真实via8/via9；M11/M12未启用。open=otpu_asic_top及33内部SRAM；LL=EPILOGUE_FUSION0/DMA_MAX_OUTSTANDING16，外16SRAM bank/DRAM/主机参加完整功能、不计core面积。不缩硬件、不加流水、不放宽原3ns。

**固定预连线：实际失败，不是已完成导线。** 92548自然FAILED1:0/4，wall24335s/CPU24357s，约1.001核（四核利用率约25%）。原生先报GRT-0116全局拥堵，未进入详细布线；后续DRC计数查询再报DRT-0002，是次生记录错误。保存2,502,723,609字节ODB仅失败快照，SHA47e51b052c508d4988c89a20aade663892468cbd847bcd2fd9c124227076d793；回执SHA694354b64878322d74b67e6853a4374ef5401fcee6b8eab2c80ac66a3b93f4b8。93104新进程只读完整保存GCell、没有重跑6小时GRT：7层各5,040,025格，总35,280,175层格；M5/M6/M7/M8超容量格分别63,626/236,171/372,529/190,028，总862,354。wall120s/CPU119.319s≈0.994核；回执SHAf91ddbb7e49b87097b7ff191e152c8ba08d97317808b5bb12fbd03c768a22f40。

93107对全部862354行按真实六宏矩形作空间归属：633205格中心位于宏外（约73.43%），5595个宏外中心格仍与边界相交，热点在M7底边、M6左边的64×64网格区域。**完整14059目标中，14059有数据库guides，实际有wire的目标为0**。guides不是导线，统计不是完整物理连通。wall6s/CPU4.877s；回执SHAa729ea6d1ff978201c6a93589e11353db859d63556fdc3bfad8aa72ff0bf6b9d。该归属不等于逐PIN/OBS碰撞或排他根因，不能据此删几何；应反馈公共IO/通道与预连线策略。93103首次读回把DRT的15566信号/clock网数误作native全网数而失败；原生库存实际另含2PG共15568，修复为绑定真实191实例/15568全网后才运行93104，未去掉身份守卫，原失败保留。

**接入点：完整实测部分改善，仍未通过。** 93086完整native PA/GRT实际完成、两诊断DB已保存，但独立读回脚本缺need而Slurm FAILED；93093新目录逐SHA及真实独立读回恢复了完整观察证据，没有重跑PA。13507端口、27014盒、47262AP行一致；5066个M8盒无AP，其中53在选中网。93093回执SHAf9187747c0b938a88569d1a8e80a5a774e4c6c4f0b24728500627d9bf7ba5f65。所有端口有原低层AP不等于全部新M8接口可用。

93095小对照、93100原生helper资格后，**93101完整设计观察COMPLETED0/4**：只按真实pitch/offset补充相邻M9轨道元数据，原52模式保留；不增加M9导线或器件、不移动引脚/内部cell、不删PIN/OBS/导体、不软件补AP，实际布线上限仍M8。完整546459实例/124targets/62splits/15489424保护不减。缺M8 AP从5066降至**1642**，剩余在负X左侧，其中1口在选中网；43862个AP均在自有真实盒内。PA后/GRT后与实际新进程ODB读回一致。**这只是native接入机制部分改善，没有执行详细布线或完整接入/布线验收。** wall961s/CPU3404.059s≈3.542核（四核利用率约88.6%）；源码cedf97f7f1f65a5570da3d2c0cac080f315a0083；回执SHA85f5d98c466134abb8eb041a2e1f3e847419bba7f317446685b4266880940685。GRT后UNACCEPTED诊断DB1,484,948,574字节，SHA74b0b27c315c1d8a80041dcaa2a94a405737bf8bb6473c6140a7739024839e4e。旧93099 Rect对象误作列表在PA前失败保留；新代码按实际阶段闭合才标actual，不沿用旧预设布尔值。

**检查器与后续实际动作。** 93105只在独立小夹具验证所需M8接口守卫：真实native正例、禁用实际AP方向负例、恢复正例、删除实际M8 AP负例均检出；回执SHA6b0ca82e34402cb23884eb2ae523d573e4d32ab1c727fefa8a8e96d72716f8c4。旧“每个金属盒都有AP”守卫不修改/不放行；新M8接口检查器尚未接入成功全设计源，完整检查程序已写但未执行，因1642真实缺口未解。它不代替原低层物理连接、全DRC/PG、RC或功能。93109实际在native PA启动前失败：旧夹具适配器只接受M6/M8双形状，而剩余左侧实际为M5/M8。故min_access_points=1/2/4三项原生调用均NOTRUN，不能把配置编写当实测。错误回执SHA094c4986134c93dc2f3226e187eea38057f73eb580db95bf9892790f6f4ec098。下一步先按实际低层形状参数修复此案例适配，再测native设置；不据此重复完整PA。

**仍有效的限定通过。** 93016新增62BUF_X2真实合法放置、原546397实例/原导体阻挡保持及off-site负例；93022实际新旧65545状态/168074状态输入输出锥一致及真实状态破坏检出；93058新UNROUTED源placement0/VDD1/VSS1；93056闭合prepare+15来源破坏拒绝；93069完整13507口读取器+8数据破坏拒绝。均不能当新完整整机、四态/SDF/所有输入形式等价、实际线路或电气验收。旧LL六组180任务/243883行/17769493字段/540份1MiB镜像、旧open20例及active+idle只适用各自源版，不能转移为新增driver/当前191/最终底座通过。

**失败、未执行与缺项。** 93067在bit118真实M8盒无AP失败，没handoff/没fresh-detail；93018原DRT1231失败保留。93024/26/29/34/36 child_launched=false，五项实际RC/覆盖/完整LL准备/编译/回归NOTRUN。93053记录器失败与93065只读复核不变更原终态；49旧口AP点相同不覆盖全部13507口或方向/worker可达性。93081拆PORT两项真实DRT0302失败未采用。旧未加62buffer M8 AUX原3ns setup5691/WNS−1.5718422563995755ns、hold36/WNS−0.24845087801435276ns、cap1104/slew0质量拒绝；不是新driver测量。VECTOR新增4cap及e238相对原版200setup/26cap恶化未解，不设epsilon/复位例外/放宽时钟。外clock rise/fall、open37常量输出负载用户未确定/null，不填0。每例841模式相关闲置扇出、当前191统一PG/clock/固定线/完整功能仍未闭合。

下一步最小动作：依据93109及1642端口的真实轨道/层/坐标选择可验证接入处理；依据93104/93107的保存拥堵反馈公共IO/通道/固定连接安排，不缩设计、不把guides当wire。实际线路完成后独立全连接/接触/fresh DRC/PG、同frame RC/完整负端点与电气、新完整功能；统一同源全部条件通过再冻结，再做两完整case最终M9/M10定制。

唯一根：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/；93101在runs/auxiliary-driver-adjacent-track-complete-PA-capture-r01-4c-02/；93104在runs/closed-fixed-parent-route-native-grid-r01-4c-02/；93107在runs/closed-fixed-parent-grid-macro-attribution-r01-4c-01/。
最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-native-access-partial-improvement-and-actual-congestion-20261029T010314Z/milestone.json
SHA-256：**b8962b17db48829974621da22f9ba70c1fb5c6b8f7ba0ecfcc4ae3f02a448f02**。
review源码481d2af73c43c06f756ece9740d2eb552051c93b；所有job spec/source_revision/submission及关键输入/工具/输出SHA按源绑定。OpenROAD版本unknown、binary SHA0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。父索引和上一版六记录完整先封存，不改失败/封存结果。

同一Issue55/task/55-full-block-integration/草稿PR58；前次精选远端b6be911b647331ea24dbf60d7b2864b04391166e已核验，本次发布另有独立delivery receipt。大ODB/DEF/SPEF/完整日志/trace/工艺留服务器，远端仅精选小记录，不冒称完整后阶段源码已交付。所有新job4CPU/native≤4/BLAS1，单线程明确单列，无独占，不超分配，不停/重复活跃作业，不改四个受保护dirty路径、原资料或其他任务。rayggxia-project-collab1.0.0；登记PR5 pending复用未重核，board.json缺失/Projects unverified/同步pending，审查人待指定，Issue继续in_progress。
