# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

当前检查点：2026-10-28T12:20:34.660325+00:00。Issue55/PR58、task/55-full-block-integration；负责人huangpingyang04-lgtm，整体in_progress。目标仍为两个完整硬件案例共用同一冻结底座，阶段一含遗留输入问题已交付，二/三未验收，四未执行；底座主要候选1/3未冻结。按本任务现行Issue55边界：冻结后M1–M8、全部资源/位置/朝向/内部线路/PG/clock/接入点一致，仅M9/M10及实际via8_0/via9_0可定制；M11/M12后备未启用。当前修复只发生在本人冻结前派生副本。openTPU保留全部33个内部SRAM；llaccel外部16个SRAM bank不计核心物理面积。

**已经实际完成：新版AUX CTS及限定状态逻辑检查。** 92746 CTS已COMPLETED0，原3ns，native放置/PG/接口/资源及预留层检查通过，inputs_unchanged=true。该llaccel辅助区本来无SRAM宏，保持0，不能推广至openTPU。新实际ODB为/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-cts-repaired-place-llaccel-r01-4c-01/flow/results/nangate45/hpy_llaccel_aux/base/4_cts_connected.odb，277169676字节，SHA-256=303de55dd4ecfd6a4463d16587e60c99dd5555f7cb81374511c50d094f4b8d52。对应实际网表SHA-256=582d57face74a5e90b18d8fe4544285b973b14a1173e22283bb8de131ab77832。

92769严格结构图检查失败，168074锥中3696不一致，完整证据保留；不据此直接认定功能错误。92771复用同一实际库已经资格的布尔真值/合法引脚对称与状态模型，全部65545状态、168074状态输入及公共输出锥规范化匹配，差异0，状态/端口清单一致；真实状态D输入反相负例被检出。图SHA-256=e2d4ff2471856222fb9e066f0fbff7e3be35420439f8ec8b93548b81ae83c635。只证明相同命名状态/初值及原存储模型假设下映射网表到本版CTS的限定一致性；**不是完整源RTL等价、四态启动/闲置合法性、SDF、实际信号布线或时序通过**。本支线没有运行SAT；92771封存limits的通用模板提及“earlier timed-out SAT”不构成本支线SAT证据，源码3c4de2d仅纠正说明而未重跑已合格证书。

**仍在运行：AUX92750完整详细布线。** RUNNING，4CPU，6小时调度时限，完整原硬件、原3ns、M8上限；在显式核对新placement→CTS与原floorplan链后提交。当前新路径采用baseline route repair=off；旧路径place off/route on与新路径place on/route off不构成单一变量A/B，不作因果性能结论。GRT阶段完整555400网/4643515guide，工具拥塞表0和估算slack−1.895ns均不是最终合法/时序通过。实际4_cts.sdc及详细布线读取的5_1_grt.sdc为3.0000ns；updated_clks.sdc中的4.6506仅诊断文件，未作为实际DRT约束使用。最终独立native检查、全网连通、新寄生、功能回归及电气检查尚待实际结果。

**新的VECTOR输出接入：真实物理范围通过，但质量失败，未接纳。** 92754实际输入/4项破坏负例通过；92755/56确认内部网旧资格路径仍通过。92760随后实际写出ODB、在新进程原生读回：vec_rd0_req[24]为28条route+2处不变BPIN，共30形状；完整41相关网络连通、全部3处边界端口形状可达、异网接触0。原内部15形状、固定M8导体区域及两BPIN、全部八类资源表和非目标线路保持，M9/M10预留为空。原始27条native DRC记录逐条保持，新增0/遗漏0；**不是零DRC或制造签核**。92763独立来源资格通过，15项真实报告破坏负例检出。只接受这份候选的限定物理来源，不代表共同底座或质量验收。

候选ODB SHA-256=d32a0064a89efa04f6b5f97053635be94e53426ba485f86c095bbf5f5a9948c0。92764在相同3ns/库/RC/SDC/提取框下实际提取，SPEF426150575字节，SHA-256=6b6b3331d982c943b15a4585dbb7b66e3674ca36cadad2240f33cb8622dcb094。setup WNS−4.173063790419197ns、native TNS−1057.7103083877685ns，287负端点；hold WNS+0.02439915005763723ns/负端点0；cap56、slew0，fanout无有限约束不算覆盖通过。与真正原始相比200setup及26cap项恶化，最差额外4.124922742ps。92766与紧邻2bf版完整端点对照，恰1个setup端点进一步恶化0.5175859887ps，即vec_rd0_req[24]；cap列表与紧邻版一致，未新增/消除/打印精度恶化。**候选未改善目标，质量失败，不采用d32替换原合格2bf物理源**。全局WNS不变不表示每端点不恶化，不忽略微小负数；完整端点差异是验收依据，聚合TNS差值不直接充当单端点差值。

**主线未完成项。** 92538为RUNNING，当前2448/4096区闭合，仅部分覆盖；92547/48依赖等待，不终止或重复活跃作业。14059条固定连接仍是预连线方案，尚未完成实际导线；每案例841闲置输入扇出未完成。既有共同布局/局部PG/控制路线通过的限定证据不等于全部固定连接完成。旧92508 open20例/87160行/2317514字段、92505 llaccel六组180次/243883行/17769493字段等有限完整结构active/idle回归仅对应当时版本；不能替代新CTS、最终物理网表和两完整案例最终回归。旧AUX92710/11仍5635setup/30hold/1087cap失败，跨原core边界未完全归一化，不全归输入继承。新AUX尚无实际RC质量结论。共同PG/clock/固定连线/全局检查/最终功能电气尚未闭合，**底座未冻结，尚未完成同一冻结底座上两个完整案例**。外部clock rise/fall、open37常量输出负载用户确认未确定，保持null而非0。

**4核实际执行。** 本次全部列出作业申请4CPU，native≤4、Python单线程步骤如实记录，无停止/重提活跃任务。92746 wall719s/CPU1007.965s，平均1.402核；92760 wall1748s/CPU2438.444s，平均1.395核，MaxRSS29385804KiB；92764 wall206s/CPU257.391s，平均1.249核；92769 wall134s/CPU133.325s，92771 wall39s/CPU38.282s，实际约1核，不能声称4倍加速。92750运行中，不用未结算CPU账目声称利用率。

成果全部留服务器/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z。本次归档源码3c4de2d31ad3b6d289fecd7d67e2dce5cbade934；各作业源码、配置、工具、输入版本和结果SHA见最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T122034Z/milestone.json，SHA-256=38922cf2b5f8fb13a93ed935d3fab675a8383936f6b43a3a63ff1d0dc296554e。上一已核实GitHub提交9d7f9c1f773f33b65fdb2137059b83ce3c6e996e、PR58/Issue55评论6467367575/结构CI40677140365 success；本轮交付以新回执为准。仅增量六份既有文档/小索引，代码运行快照、大DB/完整日志/工艺继续在服务器，**本轮不是所有算法源代码的远端交付**。项目结构检查不等于业务验收。登记沿用管理中心PR5 pending（未重核），看板unverified/同步pending（缺board配置及已验证Projects接入），审查人待指定。不合并、不关闭Issue、不标done。

下一步最小动作：保持92750完整DRT及92538整片检查；拒绝d32质量失败方案，基于保留的2bf源，从原实际M3导线推导有限接入替代方案，先做完整几何预筛/边界准入，再实际布线及独立来源/RC对照。新AUX路线闭合后补新寄生、全网与对应最终功能回归；最终条件齐备后才能冻结并执行两个完整案例定制。
