# 五种基础宏交付入口

补充验证：[230 原样 RTL 命令组合回执](../results/v-composition-044706/index.json)已通过320个成对RoPE tile、65535元素跨命令统计与三项错误保持检查，共93091检查/68868周期。使用既有92523节点永久空余的80–95 CPU、约25秒，无新allocation；生产队列Store记录v-composition=PASSED。R196最终回执已通过，230/92545已接续三项独立验收并跳过这项已通过补测，224仍不提交。补测不是最终网表实测或模型质量结论；V228之后已完成独立同源验收，见下方最终包。

更新时间：2026-10-28 07:00 CST。Refs [Issue #121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)、[PR #122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。**M、V、S、T 已有通过独立接收的单块结果；四块完整原生几何已齐，R剩余验收继续，五宏整体尚未交付完成。** 每种仅一个基础实现；当前修复只处理实测缺陷，没有另设裕量版本。

| 宏 | 基础资源与功能 | 外框 µm | 当前有效结果及剩余项 |
| --- | --- | --- | --- |
| M | 64个S8基础乘法器；8路局部归约/S64累加；S16分解、S128跨组合并；操作数缓冲与RNE/饱和 | 560×560 | [最终文件、接点及版图](M/README.md)：同源四门通过，待项目审查 |
| V | 8路逐元素/统计；2路独立函数流水线；U128组级单元；2KiB回放；有限TopK | 1210×1210 | [最终文件、接点及版图](V/README.md)：228同源四门、最终交付及完整原生几何均通过；相同RTL/外框/接口，仅修实测7BUF及1DFF驱动和PG连接次序，未沿用旧源资格 |
| R | 8路共享GDN/SSM通路；8KiB活动+8KiB影子状态；四抽头卷积与历史 | 1870×1870 | 196原生最终全流程通过；230/92545在node26已通过三初态最终网表功能，208独立物理已通过；严格LEC自动补位并与完整DRC并行，交付仍依真实四门回执；尚未最终接收 |
| S | 16KiB、1024×128bit、单1RW标准单元工作存储 | 1610×1610 | [最终文件、接点及版图](S/README.md)：225同源四门、最终交付及完整原生占用/OBS均通过，待项目审查 |
| T | 6KiB、384×128bit标准单元结果交接；所有权/背压/提交/撤销/消费释放 | 1120×1120 | [既有C叶块最终文件、接点及版图](T/README.md)：沿用选定单块接收，完整原生几何已齐 |

五块均已生成原生最终布局布线产物，并通过各自独立物理门；R尚待剩余同源接收及最终交付包；M/V/S/T的四门与最终包已通过。下表为同一10ns时钟、0.1ns不确定度、I/O max2ns/min0.2ns、BUF_X2输入驱动、2fF输出负载、Nangate45 typical条件下的实际结果，面积包括全部信号单元及另列的物理专用单元；最终宏占地仍以上表外框计。

| 宏 | 有源单元面积 µm² | 物理专用单元面积 µm² | 最小setup ns | 最小hold ns | 物理证据 |
| --- | ---: | ---: | ---: | ---: | --- |
| M | 115631.264 | 153645.856 | 1.737254 | 0.014780 | [M最终接收](M/README.md) |
| V | 626334.506 | 741196.764 | 1.798553 | 0.016960 | [V228物理](../results/v-physical-051104/index.json) |
| R | 1542765.420 | 1802658.060 | 2.155765 | 0.015269 | [R208物理](../results/r-physical-050943/index.json) |
| S | 1071968.030 | 1389447.010 | 5.995658 | 0.008125 | [S225物理](../results/run225-five-macro-045746/index.json) |
| T | 415495.990 | 748496.070 | 5.228821 | 0.016969 | [T最终接收](T/README.md) |

独立物理通过不代替完整DRC、最终网表功能或严格LEC。V228的[新源最终网表功能](../results/v-final-function-053914/index.json)已通过，三初态各416344检查/310231周期；[新源严格LEC](../results/v-formal-054725/index.json)也已通过（43776输入/43765输出全匹配，UNSAT/IDENTICAL），V完整DRC现已通过，见[V最终包](V/README.md)。S225的[新源严格LEC](../results/s-formal-053020/index.json)现已通过（262545输入/262532输出全匹配，UNSAT/IDENTICAL），S的完整DRC现已通过，见[S最终包](S/README.md)；未沿用旧207资格。V新最终源见[228回执](../results/run228-five-macro-050719/index.json)，R见[196回执](../results/run196-five-macro-050016/index.json)；[新阶段并发实测](../results/all-live-progress-050754/index.json)证明实际任务和全部线程硬绑16CPU且CPU增长，未以父调度器状态或文件更新时间代替检查结论。

R的[三初态最终网表功能](../results/r-final-function-065951/index.json)已通过，每次397971检查/197111周期，包含240组递推和100组卷积；回执4c1a6b52a6d0ed93dccaf231eca00ab60f4d4b0141dc8d7061925476eeaf7a28，绑定同一R196最终ODB/Verilog及native回执，未改RTL或数值边界。严格LEC已自动补位，与完整DRC并行；这不是R全部验收完成。

功能、格式、并行度、局部缓冲、端口见[五宏规格](../../../../docs/BLOCK_LIBRARY_V1.md)，命令与实测逻辑周期见[接口合同](../../../../docs/BLOCK_V1_COMMANDS.md)。S/T均为标准单元存储，不能称SRAM宏；R的16KiB状态和外部S是不同存储实体。

每块最终接收必须绑定同一份最终文件：全部真实端点时序/电气/寄生、PG与连接、精确M10接点；全片原生DRC及完整FreePDK45 GDS deck；三初态最终网表功能；严格LEC。通过后提供最终Verilog/SDC/DEF/ODB/GDS/SPEF的服务器位置、大小和SHA-256，仓库保存实际接点及版图图。大体积数据库保存在授权服务器目录，不将中间布局当作最终交付。

M/V/S/T完整原生wire/via/PG/pin/OBS与M10底部几何合同见[M](M/native-geometry/README.md)、[V](V/native-geometry/README.md)、[S](S/native-geometry/README.md)、[T](T/native-geometry/README.md)。普通网络RECT已据封存DEF补核；原geometry目录仅保留迭代器历史。候选LEF的抽象覆盖、通用层次Lib和M11/M12系统资格仍为false。V完整几何已由228在本块验收后生成并通过；R由225原队列对应依赖生成。225已完成S且等待真实R交付而自然释放，后续仅在依赖ready时以共享state/claim接续未领取R几何；旧V222几何已过时，不作最终V入口。

R交付接续：旧222控制allocation已自然释放，R物理208通过，交付尚未领取；[231暂存证据](../results/r-delivery-resume-staged-052218/index.json)复用原222不可变队列和claim锁，仅等207三门真实通过后提交，目前零新allocation。它不改变任何宏实现，也不把旧V失败转移为R失败。

R几何接续：[232实际暂存证据](../results/r-geometry-resume-staged-063043/index.json)确认92526自然COMPLETED/0:0，复用225原样队列、源归档和state/claim锁；S几何已通过，R几何尚未领取。232当前未提交、零新allocation，只在208最终交付真实通过后接续；231/232各有幂等依赖观察器，不能因等待重启旧任务。

当前恢复入口及历史失败证据见[接续记录](../../../../docs/handoffs/2026-10-28-issue-121-five-macro.md)。原V203/222和S190的失败不能由新结果反向抹去，也不能将旧功能/LEC资格转移给新最终文件。阵列、多实例系统与上层M11/M12布线留下一轮。
