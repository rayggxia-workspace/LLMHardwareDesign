# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

当前检查点：2026-10-28T13:14:49.821883+00:00。Issue55/PR58、task/55-full-block-integration；负责人huangpingyang04-lgtm。完整目标保持：openTPU small（全部33个内部SRAM）和llaccel_core（EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外部16个SRAM bank/DRAM/主机在测试环境）共用同一冻结底座。阶段一含遗留输入问题已交付，二/三未验收，四未执行；主要候选1/3未冻结。按现行Issue55，冻结后M1–M8、资源/位置/朝向/内部连接/PG/clock/接入点相同，仅M9/M10及真实via8_0/via9_0定制；M11/M12后备未启用。当前修改仅本人冻结前派生副本。

**新实际结果：VECTOR原M3引出方案物理范围通过，并改善一个端点；整体质量仍未通过。** 先前M7输出支线92760/63物理检查通过，但92764/66实际测量使目标再恶化0.517586ps，d32版本已拒绝。新方案从原实际M3导线选有限接点，保留全部原15条内部route、两处BPIN、完整M6/via5/via6/via7/M8上层接入，仅把本任务新增一条长M5wire替换为M3wire及真实via3_2/via4_0。坐标由原生记录生成，非程序内手填；此为案例输入适配，不是任意Block通用成功。

92784因过严保持规则误拒绝必需的via4 M5落点，在全导体扫描前失败；原记录保留，不作为物理不可行结论。d498修正为保留全部原线和现有上层via，允许明确声明的新通孔落点。92785真实源DEF/native与原501内部形状回归、完整导体/cut标量预筛1/1及4破坏负例通过，仍仅提案。92786完整41目标/原线/BPIN/M8保持准入和4实际破坏负例通过。

92787随后实际生成并在新进程读回ODB：精确33route+2BPIN=35形状，全部41相关网、3处真实边界端口形状连通，异网接触0；八类资源表和全部非目标保持；M9/M10预留为空；原始27条native DRC逐条保持、新增0/遗漏0。92788独立来源资格与15实际报告破坏负例通过。**这些只接受限定物理来源，不是零DRC、制造签核、共同底座或功能/时序验收。**

92789原3ns/同库/同RC/SDC/提取范围实际提取：setup WNS−4.173063790419197ns、native TNS−1057.7092852062ns，287负端点；hold WNS+0.02439915005763723ns/负端点0；cap56、slew0，fanout无有限约束不算覆盖通过。92790复用同一比较器分别做原始/历史postM8及紧邻2bf完整端点与逐pin ERC对照：相对2bf无新增/消除/进一步恶化的负端点，只有vec_rd0_req[24]改善0.489164278ps；cap清单与打印精度也未恶化。相对真正原始仍200setup/26cap项恶化；该输出额外恶化仍3.118172475ps，当前最差额外恶化转为wr_data_r[95]/D的3.131717196ps。**有实际改善，但不能将当前宏或整机质量写成通过，也未并入共同底座。** 旧全局WNS相同不代表端点相同，保留所有严格数值差异，不用容差豁免。

新ODB：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/vector-output-original-tap-physical-r01-4c-01/patch/patched.odb，SHA-256=e23827eea06a8f74bbab2f49ed87d75d2bb83741a829b5735de0a28454f94102。实际SPEF426150353字节，/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/vector-output-original-tap-RC-r01-4c-01/extraction/extracted_coordinates.spef，SHA-256=94bfcbb5b7e41942e98fe4093959b9f248ad8489a213af943359f5f652a3f56a。92801按全清单选新最差wr95，精确复用原始/历史两份封存路径，实际只测当前e238，已闭合；新的路径组成分析状态见索引，不预先宣称因果或修复。

**新版AUX完整路线与后续检查。** 92750为RUNNING。实际完整DRT子步骤运行结束，已观察到独立fresh DRC0、放置0及VDD/VSS各自原生连通通过；仍须等完整native库存和输入闭合收据，不能以子步骤或日志替代生产者终态验收。原完整规模、3ns、M8上限保持；updated_clks.sdc4.6506仅诊断文件，DRT实际读取5_1_grt.sdc为3.0000。旧place off/route on与新place on/route off不是单变量A/B。92796全信号网独立连通为PENDING；92797真实最终.v字节+完整8类native表与已资格CTS身份比较为PENDING，仅完全一致才复用92771限定状态证书，否则须新证明。新身份适配器已实现，18项原来源守卫在e771快照通过；e1d只纠正不同封存源码路径的SHA匹配并要求准确5种破坏角色，实际新分支消费仍待真实输入验证，不把写好脚本当通过。

CTS92746放置/PG/资源检查与92771全部65545状态/168074锥规范化匹配0差异继续有效；严格图92769的3696差异失败保留。该证书只适用映射网表→本CTS、相同命名初态与原存储模型；没有本支线SAT、上游RTL全等价、四态/SDF或最终完整case验收。新路线尚无实际RC/STA结论，不能借旧AUX结果接纳。旧AUX5635setup/30hold/1087cap失败、原完整core比较边界未归一化也继续保留。

**整片检查和无损续接。** 92538为RUNNING，本次2592/4096区闭合，仍仅部分覆盖，92547/48依赖保留。92791用真实历史92363的16区干净检查点、12个原生线程对照报告、全部实际tile/前后DEF哈希，检出8种破坏；仅为检查点资格，不是当前5429源或4096全片通过。92793为PENDING，只在92538自然结束后决策：已完整则跳过全部native查询，干净partial才核对当前源/引擎/helper/box合同并让原扫描器重新验证源/clock/control/12夹具/canonical DEF后仅续查剩余区域；非零marker、坏检查点或来源变化拒绝。没有停止现有作业、没有重复已闭合区域，当前尚未执行真实续查。

14059固定连接仍是方案，尚未完成实际低层导线；每案例841闲置扇出未完成。旧92508 open20例/87160行/2317514字段、92505 llaccel六组180任务/243883行/17769493字段的有限完整active+idle回归仅对应当时版本，不能替代新AUX、最终物理网表和两个最终案例。共同PG/clock/固定连线/全局检查/最终功能电气、冻结与两个完整案例定制仍未完成。外部clock rise/fall及open37常量输出负载用户确认未确定，保持null而非0。

**资源与证据。** 全部新作业4CPU、native≤4、BLAS1；单线程步骤如实记录，不声称4倍提速。92787 wall1749s/CPU2441.397s（均值1.396核）；92789 wall201s/CPU252.113s（1.254核）；92785 wall78s/CPU76.182s；92791 wall2s/CPU0.312s，主要读既有文件；92790两项报告检查在同一4CPU作业内串行完成。运行中账目未结算，不拿0CPU字段当真实利用率。

服务器根目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z。归档源码dc8d4e9090ffd8a78795eeed1f2e487de4a31597；每作业各自source/config/tool/输入和成果SHA均在索引。最新索引/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-milestone-20261028T131449Z/milestone.json，SHA-256=4bce46faf11f25e8834b16ec20b0227fd93d3f2c523e5e62bf9b0bc868d9008d。上一已读回GitHub提交c1d97b05f723ab21a78d1f68a8835da9d2aded7b、PR58/Issue55评论6468891719、结构CI40687269155 success，本次上传以新交付回执为准。仍仅上传六份既有文档和小索引，运行代码快照/大DB/完整日志/工艺留服务器，非全部算法源码交付。登记沿用管理中心PR5 pending（未重核），看板unverified/同步pending（无board配置/已验证Projects接入），审查人待指定。整体in_progress，不合并/关闭/标done。

下一步最小动作：从新wr95真实组成证据选择有依据的有限修复；读回92750实际闭合，完成独立全网与限定状态资格后做新RC/电气及对应完整功能；保留整片检查/条件续查和实际固定布线主线。仅有单端点改善不能缩小两完整案例目标。
