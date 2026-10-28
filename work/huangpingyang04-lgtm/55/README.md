# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

当前检查点：2026-10-28T06:10:57.638684+00:00。阶段一已交付（pass_with_inherited_issues）；阶段二、三未验收，阶段四未执行，底座候选1/3未冻结。主方案M1–M8固定，M9/M10及真实via8_0/via9_0允许定制，M11/M12仅后备。

已完成：92642筛查10个via位置候选，6个通过初筛；92643旧模式回归通过。92644在完整VECTOR的net157847上只把一个via3_2沿X移动35nm，独立原生读回确认仅3条via层形状变化，普通导线、全部8类资源表和非目标保持；全部40条目标连通、异网接触0、两处M8接口连通、M9/M10预留检查通过。matched原生DRC与真正迁线前设计逐条相同：27条原有标记保留，新增0；这不是零DRC或制造签核。92645独立物理来源资格检查通过（仅该宏，pass_with_inherited_issues）。

质量仍失败：92646实际提取新SPEF并按原3ns条件执行时序，setup WNS=-4.1730544645ns、TNS=-1057.7435049453ns、287个失败端点；对真正原始参考没有新增失败端点，但190个既有端点数值恶化，最大额外28.407ps，不能豁免。hold WNS=+0.02439915ns；slew0；fanout无有限约束，不能算覆盖通过。92647按引脚身份对照电容59→56，新增0/解决3，但27个既有超限点恶化。因此没有接纳该宏进入底座、没有最终功能或冻结结论。92652诊断FAILED：无法精确查到port vec_rd0_req[24]，不是功能失败；保留证据后修程序，在新目录复用现有寄生继续定位。自建AUX仍有53条M3标记，不属于已证明的原项目遗留豁免。

仍运行：92538整片4096区检查，当前已闭合1408区仅是部分覆盖，未停止或重复提交；92547/92548依赖等待。14,059条固定连接仍是方案，未完成实际布线；每案例841个闲置输入定制扇出也未完成。早前两个完整硬件结构有限active/idle功能回归通过，仅适用于当时版本，不等于最终冻结物理版本。外部时钟转换时间和37常量输出负载未确定/null。

资源：新作业均申请4核；92644 wall1444s/CPU2136.538s，平均1.48核（所分4核约37%）；92646 wall204s/CPU256.901s，平均1.26核。主要单线程步骤不声称4倍加速。完整目标、原始资料、封存结果和无关修改均保留。

服务器根目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z；源码：2b421ae6f17f91e697868b6f5116da4eef5445f3。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T061057Z/milestone.json；SHA-256=28352e959fe9ce8648c95ba9a9979b7187a0e1ddc0ff7cc65cc41056a74cb3e8。修复ODB SHA-256=d95ba8c4c1aedb25e3feb75fe12862999b3136b9cc90ec72adacf3cbac5a61b2。下一步先修精确端口查找并分析时序/电容恶化，再处理AUX、整片资格和实际固定布线；通过全部冻结条件后才运行两个完整定制案例。GitHub上传状态以独立交付回执为准；Issue55/PR58保持进行中/草稿。
