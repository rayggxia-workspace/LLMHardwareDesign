# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

当前检查点：2026-10-28T13:42:48.809805+00:00。Issue55/PR58、task/55-full-block-integration；负责人huangpingyang04-lgtm。完整目标保持：openTPU small（全部33个内部SRAM）和llaccel_core（EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外部16个SRAM bank/DRAM/主机在测试环境）共用同一冻结底座。阶段一含遗留输入问题已交付，二/三未验收，四未执行；主要候选1/3未冻结。按现行Issue55，冻结后M1–M8、资源/位置/朝向/内部连接/PG/clock/接入点相同，仅M9/M10及真实via8_0/via9_0定制；M11/M12后备未启用。当前修改仅本人冻结前派生副本。

**新实际结果：VECTOR原M3引出方案物理范围通过，并改善一个端点；整体质量仍未通过。** 先前M7输出支线92760/63物理检查通过，但92764/66实际测量使目标再恶化0.517586ps，d32版本已拒绝。新方案从原实际M3导线选有限接点，保留全部原15条内部route、两处BPIN、完整M6/via5/via6/via7/M8上层接入，仅把本任务新增一条长M5wire替换为M3wire及真实via3_2/via4_0。坐标由原生记录生成，非程序内手填；此为案例输入适配，不是任意Block通用成功。

92784因过严保持规则误拒绝必需的via4 M5落点，在全导体扫描前失败；原记录保留，不作为物理不可行结论。d498修正为保留全部原线和现有上层via，允许明确声明的新通孔落点。92785真实源DEF/native与原501内部形状回归、完整导体/cut标量预筛1/1及4破坏负例通过，仍仅提案。92786完整41目标/原线/BPIN/M8保持准入和4实际破坏负例通过。

92787随后实际生成并在新进程读回ODB：精确33route+2BPIN=35形状，全部41相关网、3处真实边界端口形状连通，异网接触0；八类资源表和全部非目标保持；M9/M10预留为空；原始27条native DRC逐条保持、新增0/遗漏0。92788独立来源资格与15实际报告破坏负例通过。**这些只接受限定物理来源，不是零DRC、制造签核、共同底座或功能/时序验收。**

92789原3ns/同库/同RC/SDC/提取范围实际提取：setup WNS−4.173063790419197ns、native TNS−1057.7092852062ns，287负端点；hold WNS+0.02439915005763723ns/负端点0；cap56、slew0，fanout无有限约束不算覆盖通过。92790复用同一比较器分别做原始/历史postM8及紧邻2bf完整端点与逐pin ERC对照：相对2bf无新增/消除/进一步恶化的负端点，只有vec_rd0_req[24]改善0.489164278ps；cap清单与打印精度也未恶化。相对真正原始仍200setup/26cap项恶化；该输出额外恶化仍3.118172475ps，当前最差额外恶化转为wr_data_r[95]/D的3.131717196ps。**有实际改善，但不能将当前宏或整机质量写成通过，也未并入共同底座。** 旧全局WNS相同不代表端点相同，保留所有严格数值差异，不用容差豁免。

新ODB：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/vector-output-original-tap-physical-r01-4c-01/patch/patched.odb，SHA-256=e23827eea06a8f74bbab2f49ed87d75d2bb83741a829b5735de0a28454f94102。实际SPEF426150353字节，/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/vector-output-original-tap-RC-r01-4c-01/extraction/extracted_coordinates.spef，SHA-256=94bfcbb5b7e41942e98fe4093959b9f248ad8489a213af943359f5f652a3f56a。92801按全清单选新最差wr95，精确复用原始/历史两份封存路径，实际只测当前e238，已闭合；新的路径组成分析状态见索引，不预先宣称因果或修复。

**新版AUX完整路线、全网与限定状态身份已经闭合，实际质量失败。** 92750已COMPLETED0，实际完整DRT、独立fresh native DRC0、放置0、VDD/VSS连通与接口/资源/预留层检查通过，inputs_unchanged=true；实际ODB705196924字节，SHA-256=72c80e4141365bbc40d6438c31a01586d925ebfec85a24f41f2ca315d7a4c8f2。92796独立检查全部620686信号网及1832001个必要端点，失败网0，不是只查少数网。92797最终61MB .v字节及完整8类native表与CTS92746完全相同，同native工具/flow/库/CTSpred证明通过，5项真实身份破坏负例检出；因此精确复用92771的65545状态/168074锥限定证书，没有重跑同一逻辑图或SAT。92805实际准入已消费该新身份类型，且在当前源码下重跑18来源守卫通过；不再仅为脚本完成。

92805在原3ns/真实新route上实际提取：setup WNS−1.9822344327021086ns、TNS−8618.500276501052ns、6100负端点；hold WNS−0.317598900612721ns、TNS−770.6699638811133ns、8673负端点；cap1317、slew0，fanout无有限限制不算覆盖通过。SPEF828437850字节，SHA-256=468246119ff143d2a957df03b4e7ebcfa07e6bb5f0827c4da83b6cbd30eba0e4。92809独立核实555400个active网/1766715端点精确SPEF覆盖；65286孤立单端点、9209原未连接输出逐项分类，共74495个未标注driver，不当作缺失active寄生，也不是时序通过。**接线和限定逻辑通过不等于速度和电气满足；本版质量失败，未采用为最终底座源。** 不将这些自建辅助问题全归原设计继承。

92810为RUNNING，4CPU，单次已有native setup/hold/electrical修复试验：仅在实际92809完整覆盖闭合后、绑定92750/92805失败与完全相同的新CTS92746才启动；与本版baseline唯一policy变化为SKIP_INCREMENTAL_REPAIR 1→0。保留原3ns/完整RTL/硬件容量/状态/流水/同floorplan，不重做placement，允许的标准单元buffer/尺寸调整仅在本人未冻结辅助内部；新增有源资源必须进入将来共同清单，并重新做受影响的state/fullcase/几何/RC。它仍是实验，尚无修复成功结论。旧place off/route on与新place on/route off不是单变量A/B，不作跨两旧分支的因果结论。updated_clks.sdc4.6506仍仅诊断，实际DRT约束3.0000；用户未确定波形/负载不按0处理。

CTS/最终身份沿用的状态证书依赖同名初态与原存储模型，不是上游RTL全等价、四态/SDF或完整最终case验收。严格图92769的3696差异及旧AUX5635setup/30hold/1087cap失败均保留。旧原完整core与辅助边界未完全归一化，不能给本版违例全部继承豁免；新修复若改变逻辑网表，不得再次借用本次字节身份。

**整片检查和无损续接。** 92538为RUNNING，本次2768/4096区闭合，仍仅部分覆盖，92547/48依赖保留。92791用真实历史92363的16区干净检查点、12个原生线程对照报告、全部实际tile/前后DEF哈希，检出8种破坏；仅为检查点资格，不是当前5429源或4096全片通过。92793为PENDING，只在92538自然结束后决策：已完整则跳过全部native查询，干净partial才核对当前源/引擎/helper/box合同并让原扫描器重新验证源/clock/control/12夹具/canonical DEF后仅续查剩余区域；非零marker、坏检查点或来源变化拒绝。没有停止现有作业、没有重复已闭合区域，当前尚未执行真实续查。

14059固定连接仍是方案，尚未完成实际低层导线；每案例841闲置扇出未完成。旧92508 open20例/87160行/2317514字段、92505 llaccel六组180任务/243883行/17769493字段的有限完整active+idle回归仅对应当时版本，不能替代新AUX、最终物理网表和两个最终案例。共同PG/clock/固定连线/全局检查/最终功能电气、冻结与两个完整案例定制仍未完成。外部clock rise/fall及open37常量输出负载用户确认未确定，保持null而非0。

**资源与证据。** 全部新作业4CPU、native≤4、BLAS1；单线程步骤如实记录，不声称4倍提速。92787 wall1749s/CPU2441.397s（均值1.396核）；92789 wall201s/CPU252.113s（1.254核）；92785 wall78s/CPU76.182s；92791 wall2s/CPU0.312s，主要读既有文件；92790两项报告检查在同一4CPU作业内串行完成。92750 wall7409s/CPU24561s，均值3.315核；92796 wall456s/CPU455.204s，约0.998核；92805 wall292s/CPU338.371s，约1.159核；92809 wall286s/CPU284.354s，约0.994核。运行中账目未结算，不拿0CPU字段当真实利用率。

服务器根目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z。归档源码26a7af32a1638e6376fd3847103c34570ea52ca7；每作业各自source/config/tool/输入和成果SHA均在索引。最新索引/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T134248Z/milestone.json，SHA-256=73036ec028585bc4d255286a9f8e93b29cfb4e40f68753a59ebf8370718fee0d。上一已读回GitHub提交8f879083d3de60f20613820ba4855d9081870496、PR58/Issue55评论6470050111、结构CI40694947684 success，本次上传以新交付回执为准。仍仅上传六份既有文档和小索引，运行代码快照/大DB/完整日志/工艺留服务器，非全部算法源码交付。登记沿用管理中心PR5 pending（未重核），看板unverified/同步pending（无board配置/已验证Projects接入），审查人待指定。整体in_progress，不合并/关闭/标done。

下一步最小动作：保留正在运行的同新CTS原3ns native修复并核查实际调用，终态后重做受影响native/状态/完整功能/实际RC；依据wr95真实net83203的额外ground电容与延迟设计有限候选，保持已改善输出及全41目标。保留整片检查/条件续查和实际固定布线主线。仅有单端点改善不能缩小两完整案例目标。
