# Issue247 实验入口

最新为[原生P前三项实现与服务器证据](native-p/README.md)及[详细实施文档](../../../docs/experiments/issue-247-p-native-optimizations.md)：run10/101756、run11/101758全部通过，已新增可选生产RTL，默认行为兼容，SRAM16KiB不扩容。完整P含释放：K59 2112→2032、K11 672→676；真实DMA/物理/整模型未验收。以下生产RTL不变的描述仅对应此前研究阶段。

新增[连续融合/流水研究证据](fusion/README.md)和[详细报告](../../../docs/experiments/issue-247-u-fusion.md)：run07/101720与run09/101728已完成，生产RTL保持不变；原生局部周期、实际条件SystemC与流水条件预测分别报告。

后续容量/读写并发两路线及调度交互比较已完成run04/101665和run05/101672，见[新增证据](compare/README.md)与[对比报告](../../../docs/experiments/issue-247-capacity-port-compare.md)。新增两轮87完整trace、6尾块、6非法CLI及230回收SHA；下文保留首三轮证据，不重复改写旧索引。

负责人 Melodydt；2026-11-09 Asia/Shanghai。[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。用户授权按顺序研究，允许增加一定面积；SRAM扩容保留但不实装。

正式研究工具位于 `project/experiments/area_speed_study/`。复用Issue245的完整冻结输入，保留全部原功能源。此目录只放轻量证据与索引；大原始输入/输出和生成二进制保留本人服务器目录。来源不是物理或真实模型生成验收。

三轮实际完成：101631（4:57）、101635（0:24）、101638（4:42），均c64/node1/4核/COMPLETED0:0。56次完整trace、32次小模型/非法CLI、独立oracle及隔离RTL/P程序对照通过；分别回收核验92/85/65份输出SHA。`index.json`记录三个源码commit、完整结果SHA、63份轻量文件SHA和服务器位置；各run的summary给全部主结果，selected results保留可复核原始case。完整结果/生成源码/二进制仅在本人服务器run01–03保存。

`python -B work/Melodydt/247/verify.py`核对轻量证据、最新已测功能源、摘要与原始case，不重跑仿真。正式结论见[报告](../../../docs/experiments/issue-247-area-speed.md)，恢复见[交接](../../../docs/handoffs/2026-11-09-issue-247-area-speed.md)。无活动作业、无自动监测。规则rayggxia-project-collab1.0.0，登记pending、看板unverified/同步pending；研究交付待独立审查/合并，不done。
