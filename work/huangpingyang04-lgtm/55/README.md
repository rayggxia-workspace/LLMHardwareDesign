# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

检查时间：2026-10-28T17:56:31.417898+00:00（UTC；北京时间UTC+8）。Issue55 / task/55-full-block-integration / 草稿PR58，负责人huangpingyang04-lgtm；整体in_progress。阶段一pass_with_inherited_issues，二/三未验收，四未执行；资源并集底座候选1/3，**未冻结**。

**目标与冻结边界。** 两完整硬件案例共享全部Block、有源/存储/控制资源、位置/朝向、内部实现、固定预连线、PG/clock及M8接点。M1–M8固定，仅M9/M10及实际M8↔M9、M9↔M10通孔定制；M11/M12独立后备未启用。当前必要低层修正仅在本人未冻结派生副本。openTPU保留otpu_asic_top全部33内部SRAM；llaccel保持EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外16SRAM bank/DRAM/主机参与功能测试而不计core面积。未缩规模、加流水或放宽3ns。

**新通过：共同父版整片原生几何及独立来源/时钟图。** 92538实际75985s（21h06m25s），4worker×native1，完成4096/4096区、256闭合批次，原生DRC记录0。完整源/PIN/OBS/PG/导体保留，各批前后DEF身份一致。92547独立核验相同源及完整覆盖、76个完整时钟网络/157必要端点，通过PASS_CURRENT_SOURCE_COMPLETE_TILED_NATIVE_DRC_AND_CLOCK_GRAPH_ONLY。源ODB SHA 5429f170d2da4e870e33da3efc8f528737ce3378cc1959b26e24610e96211508。10金属层边界与真实via8/via9负例及缺区/重复区/改源/改box/非零marker控制有记录。**只代表当前共同父版的原生几何和时钟图，不含RC/STA、clock质量、完整功能或制造签核。** 92793实际跳过恢复，没有重复扫描。

**预连线与实际布线。** 14059固定连接原为方案；92548当前 RUNNING，已进入真实详细布线/引脚访问，尚无完整闭合receipt，不能称14059条已布通。原父版DRC0不能继承给新布线结果。每案例841闲置扇出未完成；新固定父版需独立读回/完整连接、固定和非目标保持、PG/clock、fresh native、真实RC及质量检查。

**新通过：AUX单通孔修正。** 92934仅在net _280627_固定坐标(2437130,2084740)DBU将实际tech via1_4换成via1_3：cut和M1落脚不变，只把M2落脚在x两侧各扩70DBU。新完整独立native DRC0，放置/PG拓扑通过；16330527条非目标形状及九类完整资源/端点/工艺表保持，16条目标形状限定差异核对通过。1320s/CPU2249.452s，平均1.704核。新ODB：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/auxiliary-native-repair-single-via-shape-r01-4c-01/repaired.odb，708889986字节，SHA 8ce385e5f7a9cb68eaca80853d651f789091655e173dfd50681d12b422340387。**尚非全网连通、功能或时序通过；原92810仍FAILED。** 旧92797字节身份不能用于含resize/buffer的新源。

**失败和修正记录。** 92922两条M2补线的实际目标图2端点/1分量、无异网接触，非目标及11类表保持（92939独立补核）；但局部native仍1条Metal Spacing，拒绝，未执行其后全AUX DRC/RC/功能。1175s/CPU1176.493s，约1核。随后单通孔候选采用不同修复，不重跑全路由。92937/92938实际宿主COMPLETED0→容器准入→子程序启动，但--output误填文件路径导致父目录不存在，在实质状态/全网计算前失败；保留child日志/continuation，不写成状态或连接失败。r02已改用独立输出目录；92942实际65545状态/168074锥检查仍有5104严格结构差异，状态/端口相同且负例检出，尚未通过。92948随后以已独立验证的实际Lib真值/引脚对称和寄存器驱动族语义，在这份新物理网表上重新检查65545状态/168074锥，差异0，实际状态D反相/时钟模型破坏负例检出，COMPLETED0/4通过限定库语义证书。严格5104结构差异原记录保留；这不是上游RTL/四态/SDF或完整案例功能证明，不沿用旧字节身份。全网92945仍需实际闭合，见current_evidence。

**VECTOR仍质量拒绝。** M8候选真实52形状/41网/3边界、八表/非目标和独立来源通过；原27条native逐条保持/新增0，不是零DRC。原3ns实际RC/STA相对e238 setup恶化0、改善37，却4项既有cap恶化，拒绝；e238本身相对原始仍200setup/26cap恶化。92927只读扫描8896890行发现4个victim网的M4导体均在旧M7/新M8路径投影下方；安装版OpenRCX默认coupling_threshold=0.1fF、context_depth=5、cc_model=10。无直接耦合输出记录不等于无上下文影响；尚未证明排他原因。独立弱耦合诊断采用1e-9fF，仅写net83203、不跑STA，不改生产0.1fF或豁免4项退化。92941因SDC只读挂载缺失在提取前失败；r02/92946修正挂载后实际完成父版提取，但-net_id选网SPEF导出触发OpenROAD SIGSEGV11，新M8版未执行，诊断整体失败。保留原日志；先用小fixture验证替代导出接口，再决定是否另跑，不以安装版help支持等同实际可用。

**阻塞及最小下一步。** 继续92548实际固定布线和独立验证；完成新AUX严格状态锥差异的库语义检查/全网，再以原3ns提取RC、做逐端点质量与最终功能；VECTOR先定位实际CAP差异再做有限修正。各合格物理源合入同一父版仍需统一验证，不能拼不同版本的通过。外部clock rise/fall、open37常量输出负载仍null（用户未确定），不阻止其他独立工作。正式Block/任意LLM未证明；route入口目前固定父层范围、replay目前native清单范围，冻结及最终两case定制未完成。

**追溯与协作。** 唯一任务根 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z；本轮review源码 b2991d5cadc340172a9ca312b0fe2d7b2f5045f5，各作业原始commit/配置/工具/输入SHA/日志/CPU在索引。OpenROAD版本字符串unknown，binary SHA 0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53。整片检查CPU294872s/墙钟75985s，平均3.881核，约占4核97.0%；新作业均4CPU/native≤4/BLAS1，不停/重复活跃作业、不超额。索引 /public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-state-closure-20261028T175958Z/milestone.json；SHA 2ba969769ad2fe7fb120671f193ec6463daac922b9a7b58b44f03f1555fee7e7。保留历史/封存结果，只更新原六份任务记录；大ODB/DEF/SPEF/全日志/工艺留服务器。

沿用本人账号/Issue55/现有PR58，不新建、合并、关闭。上次核实远端afe2654e254059910a01799b2840021b85413d84；本次发布以独立交付receipt为准。规则rayggxia-project-collab1.0.0；登记复用管理中心PR5 pending（未重核），board unverified/同步pending（board.json缺失），reviewer待指定，保持in_progress。原232939字节方法全文在155133Z归档previous_methods.md及Git历史，本次previous_methods仅保存更新前17KB稿。

<!-- actual-AUX-complete-RC-checkpoint -->

新增实际检查点：2026-10-28T18:13:55.121251+00:00（UTC，CST=UTC+8）。
AUX全网92945实际COMPLETED0/4：623217条信号网、1837063个必要端点全部连通，失败网0、未连信号输入0。454s/CPU452.664s，约1核；底层实际电气图23207497节点，不是仅端口/画线方案。
92949实际COMPLETED0/4，原3ns真实OpenRCX/精确STA完成，但**质量失败**：setup WNS−1.5643455862360762ns、TNS−6788.803340083859ns、5658负端点；hold WNS−0.2471712904311318ns、TNS−4.276947361771401ns、35负端点；cap1039、slew0，fanout无有限约束不算覆盖通过。292s/CPU340.770s，平均1.167核。状态证书、完整连接、真实提取和质量分别判断；不能把measurement PASS写成时序/功能/冻结通过。与旧版计数不同不代替逐端点/逐PIN比较，尚未宣称消除新增退化。
92952只在精确92949实际完成后启动全active SPEF端点覆盖，当前RUNNING；覆盖通过也不能豁免上述违例。
92951小型两线API探针已闭合：全网SPEF导出和按-net名称导出实际通过，按net_id导出复现SIGSEGV11。仅工具接口诊断，不是硬件/工艺验证。5e36d063fd855e606ee29cd9c32c05cf1974d56a在自己的新源码版本改为已探测的-nets接口、保留所有原失败；92953新r03已实际串行完成父/新M8两份低阈值提取、各仅一条net83203的SPEF且完整端点/单位匹配；两版仍未导出这四victim网的直接耦合，不能把旧无记录简单归因于0.1fF阈值，也未证明变化原因。159s/CPU171.147s；仅诊断通过，不改生产0.1fF或豁免4cap退化。
92548完整固定布线当前RUNNING；14059仍未有完整真实布通/独立验证，841闲置扇出/案例未完成。底座候选1/3未冻结，阶段二/三未验收，四未执行。继续修复/验证质量、统一共同父版，再重验两完整案例。
最新索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-AUX-RC-closure-20261028T181355Z/milestone.json；SHA-256 3576bbe8a1632d09ae3cdf41a9a37bbfdac40fe39cdb8770b54391682459de30。本轮review代码5e36d063fd855e606ee29cd9c32c05cf1974d56a；每作业精确source_commit/config/tool/input/outputs/CPU与旧历史索引均保留。上一已核实远端2d08aea475c6ba1ad67fca392d963898cf5dc3be/结构CI40741313336 success；本次后续发布看独立receipt。不修改历史结果、不上传大数据库/日志/工艺，不停止/重复活跃作业，仍4CPU/native≤4/BLAS1。
