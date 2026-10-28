# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

检查时间：2026-10-28T21:13:45.434140+00:00（UTC，北京时间+8）。Issue55 / task/55-full-block-integration / 草稿PR58；负责人huangpingyang04-lgtm。**阶段一pass_with_inherited_issues；二/三未验收；四未执行；资源并集候选1/3未冻结。** 此段及索引为当前状态，历史原文已归档。

**目标和冻结边界。** 两完整硬件案例共用全部计算/状态/存储/控制及适配资源、内部实现、位置/朝向、固定接线、PG/clock和M8接点。主方案M1–M8固定，只定制M9/M10及真实M8↔M9、M9↔M10通孔；M11/M12独立后备未启用。openTPU保持otpu_asic_top全部33内部SRAM；llaccel保持EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外16SRAM bank/DRAM/主机参与功能、不计core面积。无减规模、加流水或放宽原3ns。

**已通过的实际检查。** 新raw AUX经92934局部通孔修复fresh DRC0/PG/放置及非目标保持；92945全部623217信号网/1837063端点连通；92948库语义65545状态/168074锥通过，严格5104结构差异保留。92956/58/59实际导出三资源1851723单元、回装完整原LL父层并新编译：六组种子/背压180任务、243883行/17769493字段/540份完整1MiB镜像对照通过；92971四类真实trace破坏检出。这是有限二态零延迟原父层测试，不是所有输入、SDF或最终current191/闲置六资源证明。旧open20例及共同六资源证据仅对原绑定版本有效。

92966已把13507信号口+2PG桥真实引出到M8：159528新增形状、异网接触0，9类原表/原导体保持、fresh native全DRC0、32新track和13509 BPin实际读回。92992新进程PG/放置及资源Verilog字节SHA94116af9aa49f88fb4e5e68ac9a3ac081bc2a3fda6218962b3aa275da4597afa、旧回归输入闭合通过；**没有重新仿真**，仅精确复用旧六组证据。92980/82实际RC覆盖557955 active网/1771801端点及全部13507真实M8锚点。几何/PG/覆盖不是质量或制造签核。

**仍失败。** 原3ns后M8有5691 setup/36 hold/1104cap；setup WNS−1.5718422563995755ns、hold−0.24845087801435276ns；slew0，fanout无有限限制不算通过。92994/99只改die/track建立同范围控制、12类原表/轨道保持并完整覆盖；93002/01逐身份确认新增12setup/1hold/7cap，既有3836setup/35hold/55cap恶化，**当前M8候选拒绝采用**。raw AUX5658/35/1039另列，不把自建AUX问题当作原始core继承。93005定位62个cap退化全为BUF_X1：61直接M8口网+1内部place202727/Z。VECTOR候选4cap恶化仍拒绝，e238相对原始200setup/26cap退化未解决；低阈值诊断未排他解释。

**本次真实新增进展。** 93006实际库/LEF/native目录：BUF_X1 max60.6537fF，BUF_X2 max121.155fF、输入负载更高、宽1140→1520DBU。93007对全部546397原实例和62个同时替换bbox检查：19重叠，43仅bbox未阻挡，不是43合法放置；未替换或移动原单元。93008实测同尺寸CLKBUF_X1 max60.73fF仍不足，未采用。
93013因native命名接口不符失败，未生成ODB；93014只读确认真实实现。改用明确native实例/分支身份的93016现已COMPLETED0/4：**62个新BUF_X2真实合法放置，原546397单元位置/朝向/master/状态保持，全部原导体/阻挡保持，声明拓扑逐端点读回，实际off-site负例检出。** 这是冻结前有界新增基础设施，四个原核心不改，不增加主要布局候选轮次。

该成果仍命名driver_stages_placed_UNROUTED.odb：62个split网没有导线，旧目标导体须实际重新接线，新PG本阶段只是逻辑连接。**不能称已完成供电/信号布线、RC/时序或新功能验证。** 新缓冲器改变实际资源字节，92992旧字节身份不能用作新回归通过证明。

**布线准备失败与恢复。** 93017的13项有限元数据对照、原生真实split集正例/遗漏与非目标声明负例已通过；host实际COMPLETED0/4及来源守卫也通过。但import_fixed检查发现bit_1391676实际路径仍标FIXED，严格失败，尚未调用router，原结果保留。93018现RUNNING，4核，复用该封存marked/NETS-only DEF，使用已有scan/normalize算法只改声明目标FIXED→ROUTED状态词，其余字节必须相同；完整native往返资源/导体比较通过后才允许真实124网重布。缺线仅允许62个明确声明、双cell一入一出的split；has_wire仅允许这些网0→1，连接数/类型/其他字段和所有单元不变。新脚本/作业状态不算布线成功；最终仍须真实保存ODB、连接/短接、全fresh DRC、PG、实际RC/全端点质量及新功能验证。

**原主作业保留。** 92548现RUNNING，原4核继续，未停止或重复。源92538完整4096区native0与92547时钟76网/157端点只绑定5429f170，不能继承给新导线。**14059固定线有规划和正在执行的真实布线，尚无闭合布通/独立验收；841闲置扇出/案例未完成。** 新AUX尚未统一到最终父版，不能拼接不同来源局部通过来freeze。

**资源/版本/下一步。** 本次新作业均4CPU、native≤4/BLAS1，阶段串行、不改其他成员作业。93016 wall958s/CPU960.893s，平均约1.003核，4核利用率约25.1%；93017失败wall47s/CPU42.702s。主要核对为串行，未声称4倍提速。原clock rise/fall及open37常量输出负载仍null（用户未确定），不按0。先闭合93018完整准备/实际route，再提取RC并做全部负端点/电气与新功能检查；统一PG/clock/固定线/闲置后重验两个完整案例，全部条件满足才冻结及做M9/M10定制。

唯一根：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z；review源码c55c29a519f29662c3d46667591f04852cb25bb3。新放置ODB710445317字节，SHA f0ceaf6ef228f6ddf42871c4efdba3d35ca923e6a006c97c71a8835d4626bf32。最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-bounded-driver-progress-20261028T211345Z/milestone.json；SHA-256 151781538e6bd9ddf6d533faabf653b38da0fa7ad38f6eacd9b1c78e8fffde17。每个driver保留spec/source_revision/submission、输入/工具/成果SHA；OpenROAD版本unknown，binary SHA0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。大ODB/DEF/SPEF/日志/PDK留服务器；旧六份文档全文在索引previous_documents。只维护本人获授权文件，四个原dirty路径不动。

已核实远端PR58 open/draft、head7f49cc64ca7e66837e86afcbb354616aa90dacc6；本次以独立delivery receipt读回为准，精选六份记录，不把服务器源码快照称完整代码已交付。rayggxia-project-collab1.0.0；登记复用管理PR5 pending（未重核），board.json缺失、board unverified/同步pending；审查人待指定，Issue保持in_progress。
