# Issue162 continuation checkpoint16

2026-11-02 22:15:03 CST；YUZE-LU；Issue162 / PR163，in_progress / Draft，继续执行，不合并。规则rayggxia-project-collab1.0.0；登记management-hub PR5 pending；缺board.json，看板unverified/同步pending，处理人待指定。

[48项远程源绑定证据](continuation-proof-16/index.json)，40项原文件逐字节复制并复算SHA；其余8项较大、已完成的CTS日志和pin清单留获授权远程存储，路径/大小/SHA均有索引。另附source122精确Git Data发布回执，远程读回SHA与本地commit相同，force=false。运行中的native-flow/route日志/queue-state为捕获字节快照，不要求后来远程可变路径仍同SHA。独立CTS全部setup/hold报告及空电气报告均已收取；setup报告后补收时与最初索引SHA一致。

## S内部物理实现继续

四个source118候选1180–1183均已完成placement/CTS，进入do-route中的输入接收器/内部输出级插入、电气修复及global-route准备。四份实际插入日志各有788个不同输出端口、788个不同输出驱动实例，驱动归属S M1–M10；这只是插入证据，最后仍须由独立最终ODB驱动审计确认实际保留全部BUF_X32，并完成全部门。当前未生成6_final.odb，不宣布S或系统通过。

原六宏RTL对main4b1df2c7差异为空；S仅物理改变。其他五宏及原S合格基线保留，R保留并由并行任务修改。S独立公开端口oracle三初态通过见checkpoint15，实际最终单元仍须重跑，不能转授RTL通过。

## 真实CTS诊断定位

source122 (c7a7b751ef87144305e0cd6c8e4cbd4775bdb970)在自有Slurm分配的16核/16GiB槽运行只读检查，读取实际完成的4_cts.odb/4_cts.sdc并在前后核对所有输入SHA。执行完成，diagnostic_only=true、native_leaf_qualified=false；没有修改该检查点，原native route继续。

最差setup报告16条路径中最小+0.002187ns；最差hold报告8条路径中最小−0.628965ns，明确来自reset输入到寄存器slice666741：数据到达0.249359ns，所需0.878324ns，时钟插入0.774165ns及0.1ns不确定性。此前日志负裕量属于hold，不能误说成setup/频率失败，也不能把接近0的setup当最终通过。

这份CTS检查点早于PRE_GLOBAL_ROUTE_TCL中的固定输入接收器、S内部强输出级和之后的修复。该插入时间由原实现器config_suffix/实际config绑定；CTS路径报告中没有新输出级符合流程。最终仍须在全部改动之后用实际最终ODB/新鲜RC重新检查所有setup、hold、电气、PG、DRC、功能及LEC；不会通过修改SDC、加入假路径或放宽门来消除负裕量。

## 新S真实组合的后继准备

source121 (379963f9508a4c80c9991c4fceb6b68baad2f1f2)将可选弱输出优先搜索限制到剩余五宏的583条弱输出到Link8连接；新S全部实际输出仍正常参加全网搜索及全部RC/电气/300MHz验收，旧图1370条规则保持。源码已冻结/发布；没有通过这个搜索选择取消任何实际网络或负载。

为当前领先候选1182追加6个不可变后继：重新选择全部合格固定PG叶、实际端口拓扑、完整最终单元三程序、严格原生RC/300MHz及独立PG/电容必要界预检。它们全部依赖新S原生四门和固定PG完整验收，未满足不得发射；若候选失败，将按实际失败选择/迭代其他候选。重用其他20种精确已合格PG叶的delivery/receipt SHA，自己的索引目录仅建引用，不改旧文件。新S旁外置Link8被明确排除，其他来源需要的Link8保留；新图必须重新提取、收缩核对和确定状态归属。1182不是已合格的S选择，也不代表新组合通过。

实际完整M11/M12路由/DEF-ODB-GDS、独立全场景PG、low/base/high实际分布RC/300MHz和六文件/图联合交付，在新S与新图确定后继续。旧335实例的功能和原生RC结果保留为工程基线，不转授新组合；整机实际资格仍未完成。

资源继续八自有节点、c96 6×16/c64 4×16独立队列动态补位。128GiB预检因预测内存保护仍在等待；此次实际只读诊断和已通过的小RTL预检用有具体依据的16GiB独立规格，不改已有pending/active/completed。没有新增节点、停止新S任务、操作其他任务或合并PR。
