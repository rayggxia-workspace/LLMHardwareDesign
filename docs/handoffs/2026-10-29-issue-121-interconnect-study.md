# Issue121侧线互联实验交接

## 全宽修复闭合（2026-10-29 23:57 CST）

当前结果以[全宽报告](../reports/2026-10-29-block-v1-full-bus-driver-repair.md)和[结果索引](../../work/YUZE-LU/121/interconnect-fix-20261029/repair-results.json)为准，下文代表子集阶段保留为历史。当前分支`task/121-interconnect-study`，现有[PR133](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/133)待独立审查；实际执行源940=`dc411ac466956ad23998b9dce1540f8121c547bd`，其余源/归档SHA见最终审计。

M928/T928及S940增强驱动实验副本的原生物理、原生整片DRC、完整未修改GDS规则、严格最终LEC和三初态最终网表功能全部通过。M→T完整275根、T→S完整281根，三种RC条件共6项全部无setup/hold/C/slew/fanout违规。原生产18文件保持，所有本侧线allocation已结束。实际峰值6×16，失败/中断/未执行尝试完整保存。

S928的3条M2违规通过两处精确同网RECT修补解决，其他DEF字节相同；940重新fill/finish/RCX并独立验收，再用新S寄生重测TS。修补后检查必须由全新进程读取已保存ODB，不能重用修改前路由器内部状态。完整信号视图仅在逐字节及库/bench/日志同一性核对后复用937功能仿真，几何与时序没有资格转移。

主线可审查这些副本及逐块六文件/实际接口LEF，采用后再冻结相应M1–M10；组合应读取`accepted_sdc`的精确批准SDC。此次角色是M→T、T→S及S ready返回，其他端口方向、共同CTS/顶层PG/完整控制器和制造校准继续按各自范围验证。接手第一步读取结果索引、最终源/资源审计及PR实际状态；不要重跑已关闭的41项、旧48项或本次6项来填槽。本侧线不修改主线工作树或Issue121整体状态。

18项本地测试、结构/差异/链接及证据包重开逐成员SHA检查通过。登记pending、看板unverified/同步pending、管理员及独立审查人待指定；在线CI以PR当前head实际检查为准。

## 补齐交接（2026-10-29）

当前结论以[补齐报告](../reports/2026-10-29-block-v1-representative-link-closure.md)为准，下文14:45记录是历史阶段。bridge/bank/booster三种预制接口实际M1–M10 P&R/全DRC/严格LEC通过，MT17/TS15根详细走线/独立研究几何通过。M/T/S RTL＋bridge最终门级混合15例×三初态通过；41项电气测量及31条端口C预算已闭合；当前guarded组合仍失败（MT9 cap；TS8 cap+1 slew）。全宽275/281根未收敛，不能用子集覆盖。

主线无需重跑这41项或旧48项。下一版决策应处理弱端口到第一中继的实际水平距离，靠近混合pad配置固定第一驱动/多侧中继；强中继在本次分支形态下可从≤1mm/≤4起步。若集成桥/缓冲到M/T/S，重验受影响原生宏，不能只在新金属上补有源器件。完整CTS/顶层PG/控制器及全宽布线仍未验收。

原生产18文件末次SHA保持，16轮job均终止，末轮93298/93301自然COMPLETED。捕获、失败回执、源归档与资源审计见工作目录closure-*.json及closure-evidence.tar.gz；源commit与API发布快照不同，按归档SHA恢复运行源。只在本侧线发布现有PR133，不修改主线工作树/PR122/Issue121状态，不向主线聊天发消息。登记pending、看板unverified/同步pending、审查待指定保持。

## 历史阶段交接（14:45 CST）

仓库：rayggxia-workspace/LLMHardwareDesign；Issue：[121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)；主线PR：[122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。账号YUZE-LU；2026-10-29 14:45 CST。

独立工作树`D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-121-interconnect-study`，分支`task/121-interconnect-study`，起点b451039b3d6083a9dcc8e4db7b46fa4440ed87ac。闭合实验代码/证据基准e3b129e2b8a55c70b5be9e5843ad9c5b172b0cb5；其后补交接/进度与发布回执，并在本侧线同步主线94d5579入口，自动三方合并通过。主线工作树未修改。原运行源分别为7383a79/run907及b591fd8/run908，不转移新源码的物理资格。

## 已完成

- [报告](../reports/2026-10-29-block-v1-interconnect-study.md)：两组完整真实宏、每组130根线，36个长度/RC案例及12个实际接点距离/强缓冲案例。48项测量完整性门均通过，MT为0/24项、TS为19/24项在声明条件通过。
- T→S实际最长1688µm，8→8→2候选在high和section均通过，section最小链路setup+0.308616ns。M→T长线的电气负载可分段处理，但ready组合时序未闭合；568µm/base直连最差−0.159452ns，实际距离section加中继仍−0.313493ns。
- 原生连接、ground/coupling C和R逐条指纹反查；恢复原清单的M142/T190/S143个保护器件到实验副本，无警告豁免。原生产Verilog/SPEF/SDC九文件和三个physical回执末次SHA保持。
- 93222/93236在node26自然COMPLETED/0:0；6×16互斥CPU队列、即时补位、Issue121共享最多8allocation保持。仅停止经身份核验且模型已确认无效的本侧线93214；其他作业未取消。
- 七项本地控制、项目结构检查、48项源SHA/原生图/原始全局与逐线时序一致性核验通过。数值截面三档网格、域、能量/电荷、解析控制及错误面距反例通过。

## 主线恢复入口

先读报告与`work/YUZE-LU/121/interconnect-study-20261029/README.md`。当前不需重投这48项或重新运行已验收M/S/T生产P&R。

主线下一项应明确M→T的控制路径预算：用真实控制器的输入到达、外部输出延迟和寄存器时序检查`write_index→write_ready→rsp_ready→cmd_ready/busy`；若预算不足，再比较正确处理在途数据的弹性缓冲/信用或局部寄存控制。不要直接插ready寄存器、加false path或无依据改I/O约束。

驱动候选应预先放置在固定M1–M10底座内或固定中继小宏中，随后重做所影响宏的完整同源验收；需要验证8µm局部线假设、合法位置/供电/M10接入、全局setup/hold。M11/M12只定制连线，不能临时增加有源器件。尚未完成这些P&R，不将候选写成最终积木。

完整共同CTS、130线同时布通、新层真实三维提取/串扰、制造、广播/多跳、全协议控制器及整模型吞吐未验收。原有单宏验收对应其原边界条件，本实验不自动授予组合资格。保持一套基础宏，不增加阵列/产品/裕量版任务。

## 源码与发布恢复

本地Git HTTPS两次连接重置；采用YUZE-LU GitHub连接器发布与最终本地提交**相同Git树**的独立快照供审查。线上快照和本地分支的commit身份不同，不强推也不盲目覆盖。线上PR提交回执给出最终snapshot SHA和tree等值读回；侧线PR目标应为主线feature分支，不能关闭Issue121或替换PR122。

原实验历史Git bundle：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/interconnect-study-history-20261029-e3b129e/source-history.bundle`，287918字节，SHA256 `dc8acf4aaa17ffca4901748c1e6cd4f1972a3a595a08dfc0afeb9e5ef2fe2e69`。它要求已有b451039b3d6083a9dcc8e4db7b46fa4440ed87ac，恢复出e3b129e及所有原运行源commit；`source-history.json`保存同份索引。恢复应另建分支，不在主线工作树reset。

大数据库/原始回执仍在获授权服务器run901–908目录；仓库保留原SHA索引及代表原始小报告，完整捕获可用报告中的`interconnect_collect.py`命令重新获得。已保留901–906的失败及拒收原因，不视为硬件失败或删除失败记录。

协作：规则rayggxia-project-collab1.0.0；project_id=llm-hardware-design。Issue121仍是主线in_progress、PR122为其原状态；本侧线只交有限实验审查，不代替独立审查/合并。审查人待指定；登记pending（已有management-hub PR5待合并），缺config/board.json，看板unverified/同步pending，管理员待指定。未向主线聊天发送消息。
