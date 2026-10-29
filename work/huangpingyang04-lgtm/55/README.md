# 完整案例共同底座集成

[Issue55](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/55)，[草稿PR58](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/58)。正式[入口](../../../project/experiments/block_full_integration/README.md)、[阶段](../../../docs/experiments/issue-55-full-block-integration.md)、[方法](../../../docs/experiments/issue-55-block-integration-methods.md)。

唯一服务器目录：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z

历史检查点：2026-10-27 11:13 CST；当前结果及唯一最新索引见文末 current-buffer-PG-status。

此前检查点（历史，非当前结论）：原wire-only共同钟线6/6入口slew失败。新75个无状态正向buffer的共同CTS/合法放置/独立读回通过，76逻辑clock网通达6入口，原6宏PIN/OBS与PG/reset严格保持；150个真实电源PIN及坐标变换已核对，但新缓冲器只有逻辑供电，真实PG和钟线布线/RC未完成。LL新ABC候选全布线/DRC0/全网/65545状态168074锥通过，但3ns实测setup−2.151527ns/hold−0.547693ns、slew98/cap2548失败，不替换当前主线。无冻结或最终定制。

此前执行说明（历史；恢复以文末最新milestone为准）：92018/92107/92108/92109/92112/92116/92119已闭合。下一步依据75buffer/150真实PG PIN构造M1–M8实际供电接入/增量PG，再完成76clock网真实布线与两原周期RC/slew/时序复测；保留原6宏/内部几何、现有PG/reset及全部原始文件。LL ABC raw源3ns失败，不是当前底座源；92121已在725253网/2325528端点RC覆盖及同CTS精确通过后启动现有电气/setup/hold修复，尚无结果。继续active+idle完整任务与新增时序问题；无冻结，远端仅阶段一。

新源码/配置用新commit与独立driver/output；原始文件/封存结果只读，大数据库/trace/编译产物/缓存全留服务器，无安装或大文件下载。GitHub仅阶段一PR58草稿未合并，登记/看板缺项不伪称完成。

<!-- current-buffer-PG-status -->

更新时间：2026-10-29T09:59:07.652522+00:00（UTC），Refs #55 / PR58。候选1/3 UNFROZEN；阶段一pass_with_inherited_issues，二/三未验收，四NOTRUN。完整openTPU otpu_asic_top保留33内部SRAM；LL为EPILOGUE_FUSION=0、DMA_MAX_OUTSTANDING=16，外16SRAM/DRAM/host在功能环境。冻结后M1–M8固定，M9/M10与真实via8_0/via9_0允许定制；M11/M12未启用。

已实际完成：获批26个具名CORE_SPACER在新副本替换为26个BUF_X4及53个填充单元，3处6个旧PG矩形显式保留；733520受保护原实例及全部原导体/阻挡保持。完整733599实例的放置和VDD/VSS拓扑检查通过（非IR/EM），全源native PA工具完成；独立读回52个preferred AP，并核实其实际坐标帧和UP标志。79个新单元的实际PIN/OBS对全部固定源几何筛查未发现冲突。仍非完整信号布线、全芯片DRC、时序或功能通过。

新增接入证据：52个首选点各评估9种真实via，34个有几何候选、18个在首选点受阻，不等于18个PIN不可布。制造网格Y搜索仍6输入失败；短水平M1引出后4输入失败；保持同一26个获批位置、使用最多一拐弯M1引出后26/26找到候选，最长660DBU=0.33μm。93342独立扫描全部733599实例和8896902源形状，52个所选via/短线候选对全部保留导体/cut、真实邻近PIN/OBS及彼此检查均无冲突。**只是几何预筛；93344已4核启动实际数据库写入、26区域native DRC、独立52路径读回、真实短接负例及完整非目标保持性核查，尚未有闭合验收。** 旧失败均保留，没有改成通过；这是同一底座候选的接入诊断，不是增加主要底座轮次。

AUX仍FAIL：93191的124目标网连通、61公共物理岛/579原引出保持及目标异网接触0只属已完成子检查；fresh整片45项M3间距未解决。93315独立全原生资源/引脚/导线/通孔及virtual图比较证明验证clone与源几何一致（文本差异失败仍保留）。以该独立证据运行93336完整源路径状态对照，仍报45项M3，原始45条报错记录集合完全一致；因此仅改变FIXED/ROUTED状态未解决问题。不是假报或继承豁免。五个后继guard未放行，当前新源RC与完整LL回归未执行。

93130完整191父层/14059网的固定预连线DRT仍运行，没有最终结果。预连线清单和guide不能写成完成的导线。当前统一PG/clock、每案例841闲置sink、新增或恶化问题、当前版本完整回归、冻结与最终两完整案例定制均未全部完成。外clock rise/fall与open37常量输出load用户未定，保持null。

下一步先核查93344实际原生结果并修复接入/真实信号路线，再做RC/质量及完整功能；AUX继续完整检查上下文/几何定位，不选择有利网格或删除保持检查。之后汇入同一版底座并重验两完整案例，满足条件后才冻结。

服务器根：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z
工程源码：9033dbdc5bf460c17393997bc3c67b86511b269f
最新证据索引：/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs/full-case-VECTOR-selected-access-and-AUX-type-control-20261029T095906Z/milestone.json
SHA-256：42616339af787d87227ffbfbe45c5121c5823e4d94baa9f8c613437174291b9f
4CPU/native≤4/BLAS1/实际cpuset；Python规划和对比主要单线程。93341 wall183s/CPU182.173s≈1核；93336 wall353s/CPU1261.403s≈3.57核。未停止/重复活跃作业，没有原始/封存/其他成员文件改动或安装。大型数据库/工艺/完整日志仅服务器；后阶段完整源码尚未全部上传。登记PR5 pending、Projects unverified/sync pending、审查人待指定；Issue55 in_progress，原PR草稿不合并、不另开。
