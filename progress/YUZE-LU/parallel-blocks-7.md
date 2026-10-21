# Issue #7 并发实验进度补充

## 最新：2026-10-21 20:52（UTC+08:00）

- 用户授权修复ACT10并跟进其余并发工作。第二轮七路、89499产物审计和89510／89511严格审计均已完成；冻结终态与SHA已取回。严格工具门槛通过ACT20／GEMM20／MXU20；GEMM10仍8处电容违例，合并20仍4处。完整数字见[修复与完整终态记录](../../docs/experiments/issue-7-parallel-blocks-repair.md)。
- ACT10失败原因查实：约1fF零值容差忽略了−0.776fF负余量。实际网 `_5406_/Z` 驱动3个SRAM地址输入，最终负载61.2773fF、限制60.5011fF。89513／1CPU独立核对实际镜像二进制常量、SPEF／Liberty和候选视图，诊断SHA已核对。
- **ACT已定向修复**：根12／89512.0／node7／16CPU／UNLIMITED，4:07，CTS检查点续跑，仅MUX2_X1→MUX2_X2；最终最差电容余量+1.218952fF、DRC／天线／电气计数0、setup/hold正、总面积35,899.6µm²。89514核对825源＋89输出全过、严格门槛true，仍非完整宏资格或签核。原ACT10失败保留，ACT20仍为余量更充足候选。
- 合并块接续根15／89519／node8／16CPU已完成20:13，89520审计10秒完成，实际runner `bb0994d`；4项驱动升级已在实际ODB确认，但仍4处电容违例，最差−5.886479fF，严格门槛false。DRC／天线0、setup0.498073ns、hold0.0112005ns；825源＋104输出校验通过，冻结SHA已核对。根12.1／13的名称校验失败及根14的本次生成器格式化错误均非零退出保存，不以产物哈希通过掩盖。生成器Tcl回归覆盖普通名、转义总线名及缺目标／错类型拒绝。
- 根16／89521／node9／1CPU及89522均已完成，三个X1/X2替换对的Liberty逻辑／状态方程相同，诊断和冻结终态SHA已核对；ACT修复前后最终网表逐字比较仅一个MUX型号变化。不重跑已通过的三个大块。宏视图仍缺minimum_period，arc、边界驱动负载、PG几何及源到物理等价待完成，正式顶层尚未启动。
- 仅改专有目录、[草稿PR10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)及[固定Issue回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7#issuecomment-6312241685)；主线PR8、状态页和89448作业未修改。当前整体Issue仍status:in_review，不自合并。登记PR5 pending，看板unverified／同步pending，管理员／审查人／优先级待指定。
- 本并行线所有作业和一次性审计已结束。下一步可对合并块全块路由裕量30／40做同节点2×16核检查点对照（待执行），补齐已通过候选的宏资格，再安排同die顶层。20:52只读查看主线89448仍运行，未干预。临时侧聊无定时助手唤醒；所有作业无墙钟截止。

## 最新：2026-10-21 19:25（UTC+08:00）

- 用户同意三个节点方案，已实际执行。物理接续 **89497／node7／48 CPU（三路ACT 0/10/20，各16）已COMPLETED0:0／6:00**；**89498／node8／64 CPU（GEMM10/20、MXU20、合并20，各16）仍运行**，根 `parallel-blocks-wave2-06`、实际runner `05074e2`，均实读UNLIMITED；89499为一次性afterany审计。
- ACT严格审计89508／node9／1CPU完成，三路各825项源和154项输出校验通过。电容计数为2／0／0，但最差余量为−2.65367／−0.77620／+2.44166，因此**仅20通过本次严格工具门槛**，面积比0增加0.321716%；只是进一步视图检查候选。根10冻结SHA已核对；根11的89510 afterany89499及89511将对七路同样核对最差余量，不能只信06原计数门槛。根08的容器缺Slurm采集失败和未开始的09取消另存，不掩盖为成功。
- C／node9最初8 CPU的89482已完成三个基线宏的详细LEF／时序模型导出与pin核对；仍保留电容失败。89487／1 CPU完成两个黑盒宏逐bit接线检查：40外部端口、1662 signal bit、684 bit地址／数据＋1 bit computing反馈，共享clk，无新增状态；横排／竖排提出同一1670×1670µm边界，**正式顶层PNR未执行**。时序模型缺minimum_period，arc／边界模型／PG审计待完成。
- 功能：原openTPU RAM generic／ASIC12组周期对照、实际包装连接与RAM资源核对通过（89480.3）。原GEMM fusion0／1各500例实际通过，但首试摘要采集格式有误，89480.4保留FAILED1；89484在新目录核对原日志SHA与1000例summary通过，没有重跑模拟。不是完整MXU数值回归或物理网表等价。
- 故障：首试7路ABC映射输出已生成，持久进程仍等待回执；长TMPDIR最小复现，恢复首轮默认临时目录后校正探针89493通过，真实ACT已继续。仅终止明确的7个停滞物理step和长路径探针，非耗时限额；原89480／89481及89491保留失败／取消。89483／89492审计因取消缺输出manifest分别失败7／1项；89501／89502只封存失败记录原字节，未将失败改成通过。
- 同步成果：[第二轮实验记录](../../docs/experiments/issue-7-parallel-blocks-wave2.md)、[07封存回执](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-07-completion.json)、[06最新阶段](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-06-latest.json)。仍用[草稿PR10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)和[固定Issue回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7#issuecomment-6312241685)，主线PR8文件／作业不改。
- 下一步：运行wave2监视器读06与11；分别核对最终电容计数和最差余量、时序、电气、DRC／天线及PG，ACT结果不自动授予其它块。选择合格新块后补齐视图／边界及PG检查，再做同die两宏顶层／flat。无H2／签核结论。临时侧聊无定时助手监视，afterany审计会独立落盘。
- 检查：结构、Python／Bash语法、Git whitespace、实际RAM／GEMM回执／顶层接线／ACT严格审计及冻结SHA核对通过；本次结构CI见PR最新head。登记PR5再次读回OPEN未合并、pending；无board.json／缺read:project，看板unverified／同步pending，管理员、审查人和优先级待指定。整体Issue本轮读回 **status:in_review**，由主线维护，不改回；本并发实验仍运行，不自行合并。

## 首轮历史（18:05诊断时点）

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- 任务：[Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU；本补充由用户新授权的并行会话维护。主线的 `STATUS.md` 由原会话维护，此处使用独立文件避免冲突。
- 已完成：独立工作树及 branch `task/7-parallel-blocks`；作业 89458 在 node7 同时跑四个 16 CPU step，总计 64 CPU，实际 `UNLIMITED`；GEMM 与 openTPU ACT／MXU／合并版均通过 elaboration，后三路 SRAM 模型类型与实例数一致。
- 终态：四路及批次 89458 均 `COMPLETED 0:0`，批次 41:33；各路 DRC／天线 0，setup／hold WS 均正、TNS 均0，最大电容违例仍为 GEMM 49、ACT 2、MXU 12、合并41，四路均未通过完整电气验收。
- 审计：89460 一次性依赖审计已 `COMPLETED 0:0`／21秒；438个产物条目校验全部通过。已取回[冻结终态](../../project/experiments/parallel_blocks/results/parallel-blocks-01-completion.json)，字节 SHA 与计算节点记录一致 `4e6d7c24518f8ef55d45b57eb5325d0e7329dfc773273f8c339c4496fd885903`。
- 诊断：新增89478／node7／1CPU／UNLIMITED，已完成，仅在计算节点读取同一镜像的 ORFS 源码。放置优化时四路电容违例均0，最终提取后出现违例；本轮 repair_design 未设置 CAP_MARGIN，流程确认支持该裕量。只形成候选解释和下一轮对照方案，未发起新PNR、未宣称修复。
- 监视改进：明确打印校验与失败门槛，保存逐阶段电容数量、最终违例原文和 Slurm 资源账单。实际重新采集、核对行数49／2／12／41与metrics一致；[轻量索引](../../project/experiments/parallel_blocks/results/parallel-blocks-01-latest.json)。临时侧聊不支持后台助手唤醒，未创建定时通知。
- 限制：synthetic SRAM 研究模型、`LEC_CHECK=0`、未做源到物理网表完整等价和独立系统签核；分开两宏尚未重连顶层，无 H2 结论。
- 交付：[草稿 PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)，补充主线 PR #8，Refs #7；执行 runner `2568623f91f871e139c4b7544d00d0181ce4cb01`，监视／审计代码快照 `017a0a7e16c40e47a837e75101789c57b34625e6`。每次实际执行以计算节点输入 SHA 为准，后续 commit 不覆盖运行历史。
- 验证：结构／Python／Bash／Git whitespace 检查通过，增强监视器实际运行及SHA／行数核对通过；前一交付`7908208`的 Project structure CI success，当前提交CI以PR回执为准，非物理签核。
- 下一步：ACT固定16线程先对照电容裕量10／20与原0基线，再决定其它三块是否重跑；补齐包装回归／等价及边界驱动负载，再推进ACT＋MXU分开硬块的实际顶层。尚无新参数执行结果。账单CPU使用／分配约22.1%，短ACT占槽结束后长期空闲，可另行测试线程数与动态补位，不把未测配置称最优。详见[实验记录](../../docs/experiments/issue-7-parallel-blocks.md)。更新同一条[固定 Issue 回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7#issuecomment-6312241685)，由主线决定合入顺序。审查人／优先级待指定，整体 Issue 仍以主线实际状态为准，不自标 done／合并。
- 接入：管理中心 PR #5 OPEN，登记 pending；无 board.json／缺 read:project，看板 unverified、同步 pending，管理员待指定。详见[恢复交接](../../docs/handoffs/2026-10-21-issue-7-parallel-blocks.md)。
