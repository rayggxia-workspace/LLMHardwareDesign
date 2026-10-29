# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

更新时间：2026-10-29T12:30:15.564869+00:00（UTC），Refs #55 / PR58。候选1/3 **UNFROZEN**；阶段一pass_with_inherited_issues，二/三未验收，四NOTRUN。完整openTPU otpu_asic_top及33内部SRAM保留；LL配置EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外16SRAM/DRAM/host在功能环境。冻结后M1–M8固定，M9/M10及真实via8_0/via9_0定制，M11/M12未启用。

**已实际完成的有限验证：** 获批26具名CORE_SPACER在新副本替换为26BUF_X4+53填充，3处6个原PG矩形保留；733520受保护原实例及原导体/OBS保持，完整733599实例放置与PG拓扑通过（非IR/EM）。93344的52首通孔/有界M1引出实际写入、26区域native DRC0、独立路径读回/真实短接负例/完整非目标保持闭合。93364投影/还原全部8类native资源与逐网几何精确保持，但同进程网表残留52临时端口，整体FAIL保留；93376新进程重载同一ODB导出与原placement逐字节相同，SHA6884f81cc974d0c7d8aa48d5c64a545e2bb76d0d0e8f10c7ea0fd83a310c5702。新93379只闭合临时路由输入资格，不是完整布线/功能。93383已COMPLETED0:0/4核：完整源仅将普通路径状态ROUTED改FIXED，全733599实例/端点/所有导体几何精确保持，输入未变。

**新失败及实际定位：** 93385的52个实际M2 BPin均通过native PA，但GRT只有49网导引；三条遗漏正好是y2_r带反斜杠/方括号的[111]、[51]、[58]网，原生STA name lookup对这三条报not found。严格全部52导引关卡拒绝，**未执行DRT**。93391后继guard拒绝/nochild，端点还原未运行。旧失败没有改写，没有减少目标或跳过检查。

**新实际进展，仍非布线完成：** 93395采用真实dbNet对象直接选择52网，真实重复/未知网络负例被拒；完整native PA再次闭合52/52真实M2落点，GRT实际52/52网有导引。保存全733599源及8,589,150个保护外网导体的duplicate OBS，独立新进程已读回全部52 AP与guide集合。完整native资源/逐网几何保持比较已通过，8表完全一致、改变网0/禁止改变0；fresh详细布线已实际启动，目前未结束。导引线、AP、保存handoff都不是已经布好的电线。93395仍运行，尚无完整路线或后验物理结果。

**后继实际已排队：** 93396（4核）只在93395成功且收据合格后，接回52真实BUF A/Z端点、导入仅替换端口tuple而不改路线字节的实际52网DEF、补回精确首通孔、按ID移除临时shadow；再做新进程完整网表字节一致、全源保持、原接入/实际DRT导体多重集保留、全52连通/短路及placement/PG。10项格式正负例通过，**真实还原尚未运行**。93397（4核）再等待其成功，进行fresh完整native DRC，要求原参照GCell网格精确相同、检查前后DEF字节不变、原27报错记录多重集逐条完全保持；新增/遗漏/改变记录均拒绝。原27报告破坏与网格格式控制通过，**真实完整DRC尚未运行**。即使通过也非零DRC、制造签核或RC/功能验收。


**新增闭合证据（2026-10-29T12:30:15.564869+00:00 UTC）：** 93395保存handoff的独立完整比较已通过，8类native资源/端点表完全一致、全部原导体几何保持，changed_nets=0、forbidden_changes=0；fresh详细布线已实际启动，仍在优化，尚无最终路线验收。93412独立逻辑检查已COMPLETED0:0/4CPU：完整VECTOR插buffer前后4117状态单元、10973寄存器输入/输出逻辑锥一致，差异0；真实状态输入破坏负例检出，实际同Lib BUF_X4真值为恒等。源placement网表SHA6884f81cc974d0c7d8aa48d5c64a545e2bb76d0d0e8f10c7ea0fd83a310c5702。仅同名/同初态条件下的已知库图比较，不是SAT、上游RTL/四态/SDF或完整LL任务仿真。未来只在最终保存网表字节完全一致及完整端点/master保持后复用；不能直接当最终物理/功能通过。
逻辑回执：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/vector-declared-driver-state-cones-r01-4c-01/execution.json，SHA-256 50615c7445d973a0316b0116585e4bb7f3c341132e58b50ab777f073e56d3238。
93412 wall96s/CPU95.376s≈0.994核，申请4核、前端/图比较主要1核。实际源码fb3a1998a3d0db1d199d7be0b0b2736d0b99a142。

AUX93191仍FAIL45项M3，93336只改路径状态后45记录完全一样；93351全546459源/全导体的覆盖整片coarse上下文诊断仍运行，不能用它豁免原45或放行RC/LL回归。93130全191父层/14059固定网详细布线仍运行；第0轮中途40%/3053444违例不是最终结果，不重复/停止。

下一步：继续93395实际DRT→93396真实端点还原/独立连通与供电→93397同原网格/原27记录完整DRC依次闭合；失败则保留证据定位。随后执行实际RC/原3ns质量与当前版完整功能。共同PG/clock、每case841闲置sink、AUX45、新增或恶化问题、同最终底座两完整案例仍未全部验证，满足条件才冻结。外clock rise/fall及open37常量输出load用户未确定，保持null。

服务器根：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z
工程最新：fb3a1998a3d0db1d199d7be0b0b2736d0b99a142（实际93395源码18cfba90b2e9eb4aab98d77fc04cd03ed02f37e9；93396源码787297d64f727aea685253fb102a631309e1ed73；93397源码4b8756bbff7ed65498adeec997bf1a8c85a00b95）
最新证据索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-handoff-and-VECTOR-logic-closed-20261029T123015Z/milestone.json
SHA-256：ddff8a682ce24f63e8398f192693199e6116050232bcaf90d77e23b4b9bcf376
资源：所有新作业4CPU/native≤4/BLAS1/实际cpuset；93383 wall786s/CPU785.873s≈1核，93385 wall454s/CPU1501.015s≈3.31核（4核容量82.7%）。申请4核不等于每步四倍加速；Python完整比较主要1核。无原始/封存/其他成员文件修改，无停止/重复活跃实验。大DB/工艺/完整日志留服务器；后阶段源码仍未全部上传。登记PR5 pending、Projects unverified/sync pending、审查人待指定，Issue55 in_progress，PR58草稿未合并。
