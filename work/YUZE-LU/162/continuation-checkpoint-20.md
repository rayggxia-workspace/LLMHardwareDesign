# Issue162 continuation checkpoint20

捕获：2026-11-03T01:18:38.216586+08:00；YUZE-LU；[Issue162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)，in_progress/Draft，不合并。

[354项源绑定远程记录、341项原文件及3项实际发射/资源辅助脚本](continuation-proof-20/index.json)逐字节SHA复核；大文件仅索引原路径/大小/SHA，运行中日志代表捕获字节。规则rayggxia-project-collab1.0.0；登记management-hub PR5 pending；缺board.json，看板unverified/同步pending，处理人待指定，审查人待指定。

## 用实际最终RC决定修复方向

按用户决定，在S内部补驱动并重新验收整块。source118的1180、1181、1182、1183四个原始候选均已完成全部原生P&R及普通原生LEC，原完整回执passed=true；实际最终ODB均保持788个BUF_X32输出驱动。它们只是原始流程完成，尚未获得全部独立原生/固定PG/系统资格。其他五宏、原S基线及R并行修改保留。

新追加的独立最终验收使用已经通过的紧凑RTL预检，旧128GiB预检及其已有依赖链不改写。1181实际最终原生物理门passed=true：全部端点setup/hold违例数0，cap/slew/fanout违例数0，RC覆盖、全部实际端点、固定输入接收器、M10接点、PG、放置和信号输入连接检查全部通过。timing.rpt实际setup WNS为+0.017822854ns、hold WNS为+0.005294543ns。**但独立完整native DRC失败**，dout[58]的M10存在四处同网间距违例，不能交付或宣布S合格。

1183实际最终原生物理门passed=false：20个setup端点违例，最差−0.061375797ns，hold/cap/slew/fanout违例0，其他物理检查通过。此前摘要引用−0.0133ns只是报告尾部一条路径，不能作真实WNS；以本次完整WNS为准。1180、1182的实际独立物理/DRC仍在运行或等待准入，不据文件存在或原始流程成功判合格。1182完整GDS DRC已经进入实际FreePDK45全deck，最终回执尚未关闭。

GRT复位延迟实验保留：source131的48/64级在第二个缓冲连接时触发dont_touch保护；source132将锁定动作移至所有支路接完后，实际继续执行，但原生repair_design在更新后的寄生状态报EST-0104 inconsistent parasitics state，两项仍失败。没有发射完整复位延迟P&R，不能把未完成的诊断当修复结果。更关键的是实际最终RC已证明1181/1183的hold均为0违例，所以不再把GRT放置估计的负裕量直接当最终hold失败；优先修复已通过实际时序的1181局部几何。

## S1181局部M10修复实际发射

source133精确commit12e714cc4b21f0b95f58a445a4f743e0901c8782，939文件，归档SHA3d1372f60fd08ae29c0d8e837e5e6498d58aee26ad614c2d29dca65d55c06bf1，已正常push。新增s_escape_repair.py严格绑定原1181成功回执、该实际四处dout[58]/M10间距失败和同源物理通过；复用未改的native_escape规划及DEF完整读回。元数据规划只把M10路径总长从12um缩为5.6um，原pin、via9落点及所有过孔、下层路径、全部单元/PG/非目标网和逻辑不变，实物还须验证。

已排12项新原生/固定PG链，原始修复输出s-escape-repair-01/candidate-1330，全部门s-escape-gates-01/1330，合格输出目标s-escape-qualified-01/1330。实际修复已经Slurm运行：先完整native DRC零违例才启动do-6_report的新RC/最终输出及普通LEC，再由独立封装、物理、完整GDS/DRC、最终单元三初态功能、严格状态边界LEC和固定PG/新鲜RC门逐项验收；不继承1181原物理门资格。修复仍未完成，尚无合格新S。

另已追加新1330实际组合六项及精确native SPEF地电容/上层必要界一项，使用其他20类精确合格PG叶；所有工作依赖新S全部原生及固定PG门。真实程序、实际拓扑与所有端点、完整M11/M12/PG/low-base-high分布RC/300MHz和联合六文件/版图/源绑定仍必须新鲜通过，不能借旧335组合结果。上层正式四候选及后继尚未发射，必须先过实际前置条件。

## 动态资源实际调整

实际完整S普通LEC峰值约145GiB，初始128GiB预测不足，source133新队列支持256GiB完整收尾/严格LEC预算，保护仍为sum(forecast)×1.2+16GiB。仅替换本任务自有node2旧父分配95097，事先逐项核实其全部活动项均是原external-S-Link8组合搜索；完整原记录保留。新自有Slurm95341运行dynamic-05/node2，c64四个16CPU动态槽。其他七个分配、四份原S结果和所有其他任务不动，总数仍八节点。因1330当前只有一个ready步骤，其他步骤确有依赖而未并行，未造虚假ready工作。

node26的1182最终64GiB物理门因保护准入拒绝，按实际available及forecast只停止一个精确自有旧搜索95119.37，释放32GiB预测后可满足保护；UID、任务名、进程命令、SHA和停止回执均存证。不修改pending/active/completed spec，不降低内存系数或16CPU配置，不把中断旧搜索称作物理失败。

实际本地检查：check_project PASS、相关Python py_compile PASS、git diff --check PASS；元数据规划支持实际该网且保留原via/低层结构。它们不替代物理门。继续执行全部验收，PR不合并、Issue不关闭。
