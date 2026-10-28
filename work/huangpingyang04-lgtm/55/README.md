# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

当前检查点：2026-10-28T08:11:16.127687+00:00。阶段一已交付；阶段二/三未验收、四未执行；主要候选1/3未冻结。固定M1–M8、M9/M10及via8_0/via9_0定制，M11/M12后备未启用。

本轮完整宏级物理检查已实际通过：AUX92664完成53个via移动、精确159条via层形状变化；普通WIRE不变、全部八表/非目标保持、61条相关网络（含9条CLOCK）连通/异网接触0、M9/M10预留通过；全层原生DRC0。92669独立来源资格通过，11个破坏负例检出。VECTOR92668仅替换net83203完整线路，保存后独立native读回/全量八表与非目标保持/精确58条候选形状/40目标与两处M8接入通过，原始27条标记逐条保留、新增0；92670独立资格及11负例通过。这些是各自完整宏的限定物理来源通过，尚非共同冻结底座或两整机最终验证。

完整新寄生/时序/电气已跑完：VECTOR92674/92676在原3ns下setup WNS=-4.1730620141ns、TNS=-1057.7196307087ns，287个负端点；最大额外恶化由28.407ps降到3.607ps，wr95由28.407ps降到3.180ps，但仍191个既有端点变差。hold WNS=+0.02439915ns、无负端点；电容59→56，无新增、解决3，仍26个原超限点严格数值恶化；slew0。AUX92673/92675 setup WNS=-1.5128707604ns/TNS=-6735.5474215680ns、5635个负端点；hold WNS=-0.2393047495ns/TNS=-4.0300990352ns、30个负端点；电容1087、slew0。无新增失败身份，但305个setup、1个hold、31个电容原有失败项变差。两宏质量均未接受；AUX为本任务自建实现，其未解质量问题不能一概归原项目输入遗留。fanout无有限限制，不算覆盖通过。未知外部时钟rise/fall及37个常量输出负载继续null，未按0处理。

下一项有限修复：92678根据受害网_173404_对net157645耦合增加的真实证据，复用同一框架尝试恢复该网保存路线。实际筛查检出与固定net151699的6处M3接触，未写ODB、未接受候选。92679和92681分别完成±4/±8轨道范围的8/16个候选筛查，均0个合格；实际475条native形状与未改动DEF重构一致，M1/pin接入保持，冲突检查拒绝候选，未启动ODB试改。这是限定候选失败，不能泛化为物理路线不可行。AUX92692两版路径报告在EDA前因缺少reference_openroad配置字段失败；4a000696已改为从实际封存RC模型绑定同一工具及SHA，92694以4核在新目录重跑，不重复提取或布线，其结果以实际execution和调度终态为准。完整硬件、位宽、状态、存储和流水均未缩减或改写。

92538仍运行，当前1872/4096区闭合仅部分覆盖；92547/92548仍依赖。14,059条固定连接尚未实际完成，每案例841个闲置输入扇出也未完成。新宏物理资格不等于已并入连贯底座，后续仍须共同布局/PGclock/完整功能与两整机定制验收。新作业全4核；AUX92664 wall2962s/CPU3875s约1.31核（所分4核约32.7%），VECTOR92668 wall1405s/CPU2117.083s约1.51核（约37.7%）；Python单线程步骤仍约1核，不声称4倍提速。

服务器根目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z；归档源码：4a00069633e00d55b2fd4b66a29cc86496628b2c。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T081116Z/milestone.json；SHA-256=1e4a600a2cbf66bf2383733c519296e2b36e13ef6b343364d52551d5651e377b。AUX DB SHA=e2b6ca01287ea1bf9e5fa22c5166421db45b875ac3fa87d8eae338221ffda9a6；VECTOR DB SHA=271069ea0e90210174839c3873c87de6f8bf20158d8754b099c692ce3d143eaf。上次精选GitHub提交db4e8e0630b4149a40c916830423d7a31517a2b3已读回；本次新索引的在线状态以独立交付回执为准。PR58保持草稿/Issue55进行中，不合并、不关闭。
