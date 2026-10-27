2026-10-28 03:31 CST：222/92523已实际在node17接续V收尾（原生fillcell、route别名及SDC完成，最终LEC/RCX进行中），S只读定位已通过。S实际三个M10 U形接入addr[7]/din[43]/din[55]准备缩为1/1/2条直连，BPin与全部via/其他层/逻辑保持；真实190 DEF正例roundtrip通过，坐标改2DBU的源被拒。223准备从原190最终库内修三网并原生全片DRC/几何连通检查，再fresh final/RCX及全部四门重验；不是已修复通过。新几何队列同属223，依S223、V222、R208真实最终delivery，替代未提交的221。当前七allocation，223若提交仍受总上限8；六槽16CPU即完即补，S原生收尾含LEC按实际140.3GiB组峰值预留192GiB及1.2裕量/16GiBguard。

2026-10-28 03:25 CST：新终态已读回：S207完整GDS deck实际10项METAL10.2，原生7标记（addr[6]/addr[7]、din[31]/din[43]间距及din[55] NS Metal），不再记DRC运行。V215详细布线自然完成且router报告0，但随后do-finish缺5_route.odb失败；查安装原生Makefile确认漏do-5_3_fillcell/do-5_route/do-5_route.sdc，保留失败，222从封存5_2_route.odb接续这三步及完整final/RCX，全部独立门重验。222仅准备未提交，同时只读定位S及接续从未领取的208 R物理/交付；R交付只依实际207子回执，不依已排空FAILED父。03:18本任务六allocation，R196详细布线与209旧V DRC仍继续、其他成员未动。M/T已交付，五宏整体仍未完成。221几何队列未提交，V依赖旧215交付路径已过时；后继必须另建匹配新最终交付的几何队列，不覆盖221历史。

# 五种基础宏交付入口

2026-10-28 03:11 CST，Refs [Issue121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)，[PR122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)仍为草稿。每种只有一个基础实现；本轮必须交付全部五块的原生Nangate45 M1–M10最终布局布线。**目前两块已有单块接收结果，另外三块尚在执行；整套任务未完成。**

| 宏 | 已确定的基础实现 | 当前外框 µm | 实际交付状态 |
| --- | --- | --- | --- |
| M | 64个S8基础乘法器、8路局部归约/S64累加、S16分解与S128组间合并、操作数缓冲与RNE/饱和 | 560×560 | [最终文件、接点及版图](M/README.md)；完整独立接收通过，待项目审查 |
| V | 8路逐元素/统计、2路独立函数流水线、U128组级单元、2KiB回放、有限TopK | 1210×1210 | 203原生完成但7处cap/1处slew不合格；215已实际增强7BUF、合法化后进入详细布线，四门必须重验；无最终交付 |
| R | 8路共享GDN/SSM数据通路、8KiB活动+8KiB影子状态、四抽头卷积与历史 | 1870×1870 | RTL/映射通过，196已进入详细布线；无最终交付 |
| S | 16KiB、1024×128bit、单1RW标准单元工作存储 | 1610×1610 | 190原生全流程完成；208完整物理门通过（setup/hold最小5.995658/0.008125ns）；207三初态最终功能及严格LEC已通过；完整GDS DRC仍运行，未最终验收 |
| T | 6KiB、384×128bit标准单元结果交接，所有权/背压/提交/撤销/消费释放 | 1120×1120 | [既有C叶块最终文件、接点及版图](T/README.md)；沿用原接收结果，补齐只读原生几何交付 |

功能与数值/缓冲/端口定义见[五宏规格](../../../../docs/BLOCK_LIBRARY_V1.md)，实际命令及周期见[接口合同](../../../../docs/BLOCK_V1_COMMANDS.md)。M/V/R外框来自同一基础面积规则；这里没有另设裕量版本。S与R的局部状态是独立实体，不能将容量混算；S/T均不称SRAM。

M/T单块接收不等于通用层次Lib或M11/M12系统资格。阵列、多实例系统和通用十二层提取留下一轮。V/R/S必须完成同源的原生与完整GDS DRC、全部实际端点时序/电气/寄生、PG及连接、精确最终网表三初态功能和严格LEC，之后才生成最终V/SDC/DEF/ODB/GDS/SPEF索引、实际接点和版图图。

当前S原生终态见[190](../results/run190-five-macro-010130/index.json)，完整物理门通过见[208](../results/run208-five-macro-013337/index.json)，其余独立门执行见[207](../results/run207-five-macro-015115/index.json)，恢复与协作未完成项见[接续记录](../../../../docs/handoffs/2026-10-28-issue-121-five-macro.md)。时间点快照不是终态资格；后续以各块的同源最终交付索引为准。

M/T的完整原生占用、OBS和M10底部几何合同现分别见[M](M/native-geometry/README.md)、[T](T/native-geometry/README.md)。原迭代器文件不作完整性依据，已补核封存DEF全部普通网络RECT；候选LEF抽象覆盖资格仍false。S/R/V待同源最终验收后由已暂存221队列生成这些数据，尚未运行该队列。
