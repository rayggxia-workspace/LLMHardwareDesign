# Issue162 continuation checkpoint77

更新时间：2026-11-04T19:46:35+08:00。YUZE-LU；Issue [#162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162)、Draft PR [#163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)；承接[Checkpoint76](continuation-checkpoint-76.md)。

**完整组合仍未通过，任务继续、不合并。** 保留M/N/E/G/S/T六宏、R256、S1350块内驱动、23类型/138份单块六文件及345状态宿主；规范交付入口仍为[current363](block-delivery-r256-current363/index.json)。固定M1–M10内部与当前453接线/S5380位置不变，M11/M12仍只有被动互联；外部R及其他任务不动。所有新增芯片状态归属仍见[状态索引](state-ownership-current396.json)与[453绑定](state-ownership-candidate453-binding.json)。本轮搜索器的epoch数组仅是软件内存，不是新增硬件。

1236实核32次尝试切换前384对完整轮次非计时记录相同、三份实际第8轮完整路径SHA相同。1237读到12220首次完整dense轮的16次平均excess2032416.25，高于11400同轮956650.0625，不宣称提前切换有效。旧完整组合对照保留，不能从搜索慢或当前冲突推出物理不可能。

1242/1248在两份真实完整快照11400/11920第8轮各做64项有界探测；127条合法返回、一条原搜索90秒超时，候选64条全部返回且无重复展开。每帧已有192项独立合成Dijkstra路径检查和96条原函数路径逐字回放。原net2555/weight16在第一帧有45648715次展开、44733806次重复；候选1492065次展开、零重复，但路径代价改变。**代价是人为64倍当前占用，不能冒充实际累计history、全图速度或收敛收益。** 1252另用Python从原帧重建占用并去掉自己的原树，独立逐路径核端点、单位边、棋盘via、外来pin和精确人为代价，127条全部通过，超时原件保留。

source1250 `f2978da542dbc79b7a0330bbb6196f60b43f92dd`，1023文件，归档SHA256 `43f1cfd2acb82326e07ba2a2b81fbc8212e9b3a7cd826c3fff3ef524ad6d2dbe`。新增默认关闭的`--route-weighted-settle-once`：仅普通加权候选每侧每点最多展开一次，weight1仍调用原精确求解，native有限分支不变；不承诺候选最短。额外两个软件epoch数组在加权候选分支才分配，完整网格87984400字节/进程，约83.9MiB，16个约1.31GiB，包含在原每候选64GiB预测内。1251实核全部源/归档、1018未变项及三生产文件自有scratch精确回退；原weighted头、exact双向类、资源求解及全部物理门相同。

1252实际通过生产候选与独立验证过的scratch候选96条路径逐字、96次weight1精确回放、96次epoch重置及192项Dijkstra路径检查。默认旧完整小路线主/native/路径逐字一致及嵌套旧回归实际执行。新完整40×40合成例必须既跨8/16切换又实际使用settled分支，再逐边、via、树连通、预算及全图零冲突检查；结果为 `[{'cutoff': 8, 'seed': 972, 'final_round': 33, 'settled_branches': 130}, {'cutoff': 16, 'seed': 972, 'final_round': 28, 'settled_branches': 25}]`。切换前已结束或失败尝试保留，不充当覆盖。两非法上下文/重复拒绝和真实仅一轮有冲突无最终输出通过。小图不授予系统资格。

12560/12561进入原完整七阶段链，仅相对12220/12221增加新普通候选，保留相同stride16/cost8/拥塞1/加法history/seed4662/9060 trial0暖前缀与cutoff8/16。1257严格核14份规格、六键验收配置、当前453三初态八程序/事件及各自未来几何/PG/low-base-high/交付路径。1261实核32子进程、32对实际输入体/前缀、真实CLI/日程、node2和node4各四个16CPU掩码两两互斥、真实内存准入；不宣称32次都已跨切换或完整布通。必须继续全图零冲突、实际几何、PG与三档RC300MHz联合门。

source1270 `46c5820b42bf552d82e4e2d1a0446f7ff2925c6c`，1024源，归档SHA256 `e34fb39f43595d9f7000c8ba4f739c74c0754076a7f771b75f40b87855d229be`。1273实核1021未变项与两观察/分派文件自有scratch精确回退；RTL、模型、路由和最终门不变。1272只重新编译观察bench并链接同一不可变345实例/23类最终单元资产，3226位逐一绑定当前图同一物理网的实际root成员，没有跨网别名推断。实际捕获C接受的发射字、八队列cmd/组包后task/适配器complete/done返回及C接受返回，保留外部AXI和原数值/周期检查。

1272编译链接通过，三个初态正在并行执行；**捕获时尚未完整结束，未称全三态或全轨迹通过**。1278对不可变读取前缀内首个已完整结束矩阵程序做原审计，仅把最终期望案例/程序数改为1；所有包和载荷检查保留。5包、C40字、Q40字、5次Q_TASK及完成、10个完成返回字相同；C_WORD/Q_CMD/Q_TASK/Q_COMPLETE/Q_DONE/C_DONE六份实际破坏均拒绝。它不能替代尚在运行的全部14案例、18调用、三初态完整检查，也不是逐周期波形。472/473/480既有完整功能/外部事件证据不被替换。

资源保持8父节点36×16=576CPU，c64四个、c96六个独立16CPU任务动态补位。1243仅5550/source537/95341.86换有界探测，探测自然结束后1252再自然补12560；1259仅6140/source613/95391.95换12561；1274仅6560/source653/95341.89换内部观察。每次新核原规格SHA、UID10011/job/真实节点/PID/完整cmd/source/out/当前图、全部日志、无最终或赢家和实际内存。node4未来224GiB需284.8GiB可用；node2观察未来288GiB需361.6GiB，实际通过。旧源、规格、失败及部分输出保留；所有当前全图对照、父分配、CUGR3751、外部R和其他任务不动。

[远程索引](continuation-proof-77/index.json)绑定951项SHA，[原字节ZIP](continuation-proof-77/selected-originals.zip)含542项，全部entry SHA/CRC核验通过；大实际帧留授权服务器并绑定。运行路由与内部事件记录仅不可变读取前缀，绝非最终输出。[本地索引](continuation-proof-77/local-index.json)/[ZIP](continuation-proof-77/local-helpers.zip)保存97项实际编排/报告/首程序审计及六破坏原件；提交另核实际Git blob。继续全部声明组合最终布局布线、真实M11/M12、几何/PG/low-base-high分布RC300MHz setup/hold/电气、最终六文件/版图/源绑定，不在检查点结束任务。

规则rayggxia-project-collab1.0.0；project_id llm-hardware-design；本人YUZE-LU。管理检查PASS，业务物理未完成；登记management-hub PR5 pending；缺board.json，看板unverified/同步pending，管理员/审查人待指定；Issue in_progress、PR Draft/open/未合并。
