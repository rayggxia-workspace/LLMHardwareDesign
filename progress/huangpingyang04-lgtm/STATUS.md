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

当前检查点：2026-10-28T11:03:07.670498+00:00。目标仍为两个完整案例在同一冻结底座上定制。阶段一已交付（含输入遗留问题），阶段二/三未验收，四未执行；共同底座候选1/3未冻结。主方案冻结后M1–M8、资源/位置/内部连接/PG/clock/接入点保持一致，只允许M9/M10和真实via8_0/via9_0定制；M11/M12后备未启用。所有当前内部修复均在本人冻结前派生副本。

**新里程碑：AUX92736实际放置检查通过。** 4核作业COMPLETED0，42项策略单测通过；同原floorplan、配置密度0.35、3ns与完整功能/规模，启用既有placement timing repair，实际resize调用已核实。独立native放置违例0、VDD/VSS连通，接口/资源/上层预留检查通过，inputs_unchanged=true。这个llaccel辅助分区本来没有SRAM宏，计数0得到保持；不能推广为所有设计没有SRAM，openTPU的33个内部SRAM仍在整体范围。缓冲/尺寸/位置改变只限未冻结自建辅助区，仍需完整状态/功能重验。工具拥塞优化会内部调整软密度，0.35是配置值，并非已证明最终布局密度固定。

该结果仅为placement/PG/结构通过。工具placement估算仍警告未修复全部setup，**尚未提取本版实际寄生，未证明功能、实际布线或时序通过**。新CTS92746为RUNNING，4核；配置关闭placement开关，CTS不放宽时钟，保持原约束。后续实际详细布线/RC/状态认证/完整功能仍需执行；旧route修复门槛要求旧CTS，不能把新CTS冒充同一来源，需显式验证新placement同floorplan继承链。

**VECTOR最差输出已得到实际诊断，不是修复通过。** 92737只重新运行当前候选native路径，原始/修复前报告按封存selection精确复用（旧索引1→新0），5项复用检查通过；92738三视图真实路径分析及4项实际报告破坏负例通过。最差vec_rd0_req[24]相对原始额外slack恶化3.607337ps，其中launch clock约多1.050919ps、数据约多2.556592ps；末级output1101/Z延迟约多2.584696ps，观察负载0.336149782→1.518016934fF。分解是观测证据，不自动证明排他的单网因果。

92740把实际native端口/驱动身份与三版真实SPEF和几何对应：该输出总电容相对原版多1.181871fF，ground多0.665528fF、coupling多0.51633926fF；修复前和当前该网几何/电容相同。原普通低层线路保持，新增M8引出支线存在约11.3um的M5段。矩形长度统计不是精确电气性能或连通证明，未更改负载约束。

92745将有限候选只作用于本任务新增输出接入支线：保留全部原始route、原/M8两处BPIN及固定M8导线；使用实际M6/M7分段轨道，最终via落在同一M8导体区域。3个X×3个Y共9项，6项通过完整当前导体的标量预筛；另外3项与vec_rd0_req[18]冲突。每项28条route形状，另有2处不变BPIN，**均未写ODB，不是实际布线/DRC/RC成功**。现有物理控制器只允许内部网，下一步必须显式增加单个边界网的合法范围与全部41目标/原线路/BPIN/M8保持检查，不能直接跳过内部网限制。

工具输入问题均保留：92739字段合并错误在扫描前失败，92740修复并3项选择测试/6项SPEF解析负例通过；92741不支持原生端点延伸和压缩多via格式，92742只读检查缺可选环境变量而失败，92743用明确根目录读出实际记录；92744已通过实际port27与既有internal501形状roundtrip，但拒绝三段track输入；cb4b1b4/92745补齐真实分段轨道，3项格式/延伸与3项真实轨道测试及4项实际候选破坏负例通过。这些是输入适配问题，不是目标路线不可行的证据。

原限定物理结果继续有效：VECTOR92727/28有实际501形状、40目标/两M8、八表/非目标保持、原27条native逐条保持且新增0；AUX92704/09有实际29形状、61目标/原生0。它们只接受宏来源，未并入共同底座。对应实际质量仍失败：VECTOR92729/30相对真正原始200setup/26cap数值恶化，287setup负端点、56cap超限，最大额外3.607337ps；92731相邻检查点92setup/4cap恶化。旧AUX92710/11有5635setup/30hold/1087cap失败，相对旧自建f739仍439setup/3hold/31cap恶化；跨原core四路径92733/34边界/状态未归一化，不能给这些问题继承豁免。新placement不复用旧版质量接受证明。

92538为RUNNING，当前2256/4096区闭合，仅部分覆盖；92547/48依赖等待。14,059条固定连接仍是预连线方案，尚未完成实际导线；每案例841闲置扇出也未完成。旧92508 open20例/87160行/2317514字段、92505 llaccel六组180次/243883行/17769493字段的有限active/idle回归，仅证明当时资源/连接版本，不能替代新placement、当前宏或最终物理版本。连贯共同PG/clock/实际固定布线/全局检查/最终功能、最终冻结与两个完整案例定制均未完成。外部clock rise/fall、open37个常量输出负载用户确认未确定，保持null而非0。

所有新作业4核、native≤4、BLAS1，无停止/重复活跃任务。92736 wall2650s/CPU3849s，平均1.452核（4核容量36.31%），MaxRSS7406056KiB；92737 wall61s/CPU75.924s，约1.245核；92738 wall19s/CPU18.692s，约0.984核；92740 wall134s/CPU132.868s，约0.992核。主要Python步骤实际约1核，不声称4倍提速。

服务器根目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z；归档源码cb4b1b45bd4a89397348503b45eaa391258317de。新AUX placement DB：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-place-timing-repair-r02-4c-01/flow/results/nangate45/hpy_llaccel_aux/base/3_place_connected.odb；269610433字节，SHA-256=fc195c4cb0057c59a4ff546b78590d7bbebd92120e9bd5a8bc9ad52c2f7177cb。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T110307Z/milestone.json；SHA-256=1533db6062ec9f89246dc9802be76683baa1ad32c1c48f94e733dc60962356f0。各实验source/config/tool/关键产物绑定在索引。上一GitHub精选提交7b0743396ce525a4d8708f6b2e38df12faf6bab0已精确读回，PR58/Issue55评论6466519731与结构CI40671711408 success核实；本次新上传以独立交付回执为准。仍只增量六份既有文档/小索引，源码快照/大数据库/日志/工艺留服务器。登记沿用管理中心PR5 pending（未重核）；看板unverified/同步pending（缺board配置/已验证Projects接入）；审查人待指定。Issue55继续in_progress，PR58草稿，不合并/关闭。

下一步最小动作：读回92746实际CTS终态；补齐输出接入边界网的显式物理准入与完整保持检查后，仅选择已预筛合格的一项做真实试改/独立资格/新RC；继续整片检查及固定布线主线。没有实质结果不重复远端发布。
