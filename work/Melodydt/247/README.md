# Issue247 实验入口

## 第三轮RTL与旧体系评估通过，候选未超第二轮（2026-11-10，Asia/Shanghai）

Issue247/PR243，Melodydt，in_progress。run20/101872（源a3149d69a23f52efb808dbbb46b5558dffce4df7）41秒；run21/101878（源010ae8d0d8839967f96b94227d2224fade0edf37）6:06，均c64/node1/4核COMPLETED0:0。RTL六run×66场景、有限控制299064周期比对及实际S数值通过；模型24case/8精确回归/8fallback、192篡改及原测试通过。R3双buffer主ideal3.66041657326/shared2.75864978939，低于第二轮；当前最快仍3.66958239533/3.37834376557，未到5。

第三轮5页PDF、134内容单元及全部页面视觉QA通过，当前完整交付3/4轮。报告固定809f9820cc13157077e4399a789779aac52925db，PDF SHA00b0b6c2d6c44829808d316cb3e6658c378d8bf51e5cb7632320e790e969940d。大面积候选独立备份task/247-m-k16-area-initial@a3149d69a23f52efb808dbbb46b5558dffce4df7与前态备份均读回；S仍16KiB。run20结果SHA87842b59e42fb0773eedb82dce4981614432868fa12218c3aa15166b0b839eff，run21结果SHAbccd917afba10bb9c3f65f62b26b1eab588a85d73c364a4b4d54962b5197afb8。

服务器本人/public/home/yuzelu/Melodydt/issue247-area-speed/run20、run21持久保存source/、slurm-job.log与results/；62大raw另有retention SHA索引，不声称Git内含所有raw。追踪sacct -j 101872,101878 -X --format=JobID,State,ExitCode,Elapsed,NodeList。全部终态，无自动监测。第四轮在隔离目录实施R2基础op12四EXP lane；1KiB A缓存受DDR上限约束，仅保留方案。恢复第一步核对最新PR head/本轮报告，继续第四轮源审查、Slurm实测和旧体系复评。非Git本地快照work/Melodydt/242/r-load-bounds/repo仅根整合，R4子任务各隔离目录；远端task/242-r-load-bounds未合并main。

登记pending、Projects unverified/同步pending（缺board.json及工具能力）、审查人/管理员待指定；GitHub CI此前失败原因未核实，未绕过。当前候选不具备完整P/DMA、原生整图生成或新物理资格。

当前进入[最多四轮提速迭代](../../../docs/experiments/issue-247-speed-iterations.md)，2/4轮完成、in_progress；每轮研究/RTL/旧体系评估/PDF。主目标W8 decode512 5 token/s，保留SRAM不扩容和所有历史研究边界。[恢复入口](../../../docs/handoffs/2026-11-10-issue-247-speed-iterations.md)。

新增[旧评价体系21场景复评](legacy-metric-eval/README.md)及[正式报告](../../../docs/experiments/issue-247-legacy-metric-evaluation.md)。run15/101800全部历史字段复现；主W8 decode512 3.063655→共享口ctx8 3.230811 /理想端口ctx8 3.496169。48/64KiB prefill2 4.467001/4.547434保留为未实装参考。

新增[实施PDF和新版吞吐证据](token-throughput/README.md)、[详细核验报告](../../../docs/experiments/issue-247-native-token-throughput.md)。原生准入、历史重现、实际P周期和候选整图token/s分别说明；本轮未再修改生产RTL或扩容S。

最新为[原生P前三项实现与服务器证据](native-p/README.md)及[详细实施文档](../../../docs/experiments/issue-247-p-native-optimizations.md)：run10/101756、run11/101758全部通过，已新增可选生产RTL，默认行为兼容，SRAM16KiB不扩容。完整P含释放：K59 2112→2032、K11 672→676；真实DMA/物理/整模型未验收。以下生产RTL不变的描述仅对应此前研究阶段。

新增[连续融合/流水研究证据](fusion/README.md)和[详细报告](../../../docs/experiments/issue-247-u-fusion.md)：run07/101720与run09/101728已完成，生产RTL保持不变；原生局部周期、实际条件SystemC与流水条件预测分别报告。

后续容量/读写并发两路线及调度交互比较已完成run04/101665和run05/101672，见[新增证据](compare/README.md)与[对比报告](../../../docs/experiments/issue-247-capacity-port-compare.md)。新增两轮87完整trace、6尾块、6非法CLI及230回收SHA；下文保留首三轮证据，不重复改写旧索引。

负责人 Melodydt；2026-11-09 Asia/Shanghai。[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。用户授权按顺序研究，允许增加一定面积；SRAM扩容保留但不实装。

正式研究工具位于 `project/experiments/area_speed_study/`。复用Issue245的完整冻结输入，保留全部原功能源。此目录只放轻量证据与索引；大原始输入/输出和生成二进制保留本人服务器目录。来源不是物理或真实模型生成验收。

三轮实际完成：101631（4:57）、101635（0:24）、101638（4:42），均c64/node1/4核/COMPLETED0:0。56次完整trace、32次小模型/非法CLI、独立oracle及隔离RTL/P程序对照通过；分别回收核验92/85/65份输出SHA。`index.json`记录三个源码commit、完整结果SHA、63份轻量文件SHA和服务器位置；各run的summary给全部主结果，selected results保留可复核原始case。完整结果/生成源码/二进制仅在本人服务器run01–03保存。

`python -B work/Melodydt/247/verify.py`核对轻量证据、最新已测功能源、摘要与原始case，不重跑仿真。正式结论见[报告](../../../docs/experiments/issue-247-area-speed.md)，恢复见[交接](../../../docs/handoffs/2026-11-09-issue-247-area-speed.md)。无活动作业、无自动监测。规则rayggxia-project-collab1.0.0，登记pending、看板unverified/同步pending；研究交付待独立审查/合并，不done。
