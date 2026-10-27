# Issue126 持续执行入口与阶段证据

仓库：rayggxia-workspace/LLMHardwareDesign；[Issue126](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/126)，负责人huangpingyang04-lgtm，in_progress。
分支 `task/126-full-block-pin-xy`，在PR120 head4f91e098之上，不擅自合并PR120；当前物理驱动commit在每次execution.json里精确记录。

成果入口：[中文报告](../experiments/issue-126-full-pin/report.html)；[脚本](../../project/experiments/full_pin_xy/README.md)。
六块24,767个原始信号pin、74,301候选行；18项功能归属，外部设备/存储范围明确，原参考包不修改。
候选覆盖不代表物理实现：各块的实际接入、DRC/连通、RC/STA/电气状态分别见 `data/physical_summary.json`。

远程独立目录 `/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027`，所有原Issue7/55数据库只读bind。
驱动按commit封存至 `drivers/<commit>/code`，结果在 `trials/<revision>/<case>-<plan>`；大体积ODB/DEF/SPEF与完整路径报告保持远程，以execution.json的SHA索引定位。
ACT8pin试验r02、原XY重布线控制r03；GEMM r01及重布线控制r04；MXU/两个SYSTEM r03；VECTOR首个驱动配置发现失败r03保留，正确vec-config.mk后r04。
ACT完整740-pin C对照fullC-r01采用相同C可移动cohort，B也是该740-pin子集，不能称为完整B859-pin方案。

恢复第一步：读取AGENTS/Skill/远程规则和Issue/PR最新head，核对squeue/sacct，仅收集本任务作业，不碰Issue55/121或他人任务。
用 `collect_trial_snapshot.py` 创建全新snapshot名、下载后 `make_physical_summary.py` 汇总；先确认所用whole-connectivity的source ODB SHA与提取前routed.odb（A为原始ODB）一致，不能使用RCX后checked.odb。
全块几何连通可用 `full_connect_job.sh <case> <revision> A C` 对实际终态独立检查，必须使用新输出目录；旧API失败不是通过证据。
完整原父层handoff/实际层序还未知；逻辑对端和对端原pin层已补齐但不能替代该证据。完整工艺规则/GDS/LVS及系统边界RC/STA/电气仍待验证。

登记：管理中心PR5 pending；Projects未配置board.json且无工具，unverified/同步pending；处理人待指定。不得把文件上传写成在线协作接入完成。
本记录用于持续执行与审查，不表示任务完成、暂停或已验收。新的结果在同一Issue/PR增量更新，所有失败与基线未通过项保留。

在线交付：[Draft PR129](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/129)，首次发布fbac83836ecc7767a929639265b67b31d74902db；图表已上传。ACT740完整C的独立clean DRC/全块几何连通通过；新增四块制造网格r02已修订、8pin重试grid-r05。旧RCX后ODB重读失败保留，物理母本统一从提取前routed ODB生成。当前运行/后续独立检查按最新execution与Slurm读回，不根据旧snapshot猜终态。

本轮C局部验证现已六块全部完成：ACT740完整C、其余5块各8pin；独立clean native DRC均0，全块多端OpenDB几何连通均通过。RC/STA当前模型：ACT/GEMM/MXU预算满足；VECTOR及两个SYSTEM失败，不能资格化。最终收集snapshot milestone-r05，独立检查92344–92347均COMPLETED 0:0 / UNLIMITED。仍需逐项完成真实父层目标/可达、GDS/LVS/完整规则、完整系统模型及其余全C实现，不能关闭Issue。旧LL辅助边界试验若仍在运行让其自然完成，不取消/覆盖。

增量持续验证（不停止活动作业）：

- 完整C路由：92365 GEMM3039、92366 MXU1964、92367 VECTOR1022、92368 openSYS1768、92369 llSYS13184；顺序afterany，驱动f08e026，full-other-r01。独立clean92370–92374分别依赖对应路由。结束状态必须重新读回，不能把提交当通过。
- 完整cohort边界控制：92388 ACT Aopt740集合（698实际换槽）；其余92389 GEMM /92390 MXU /92391 VECTOR /92392 openSYS /92393 llSYS，均A_replay/Aopt/B。驱动bbc859d，inputs/trial-inputs-full-controls-r04，实际Aopt在既有分束/边/层槽位中优化C中心代理，非全局最优。独立clean92394–92399依赖各自路由；失败仍会释放下一块。
- 严格GDS：92375 ACT已完成，未豁免两个fakeram缺失，A/C合并返回2；不完整诊断GDS上的原样FreePDK45 deck为678/770项天线错误。其余92376 GEMM、92377 MXU、92378 VECTOR、92380 openSYS、92381 llSYS按afterany继续，来源是已完成的原始A/8pin C，不能与后续全C混同。
- 电气观察：92383已完成14组原生JSON路径汇总，F/s单位，完整ACT C与标准JSON解析交叉核对通过。只为已报告路径点最大负载/slew观察，不是全部net覆盖。92382旧回执字段缺失的驱动失败保留，新版从原冻结Tcl恢复cohort。
- validation_extensions/milestone-r01 为新增严格GDS失败和真实电气观察快照；raw GDS/大型lyrdb留远程。ACT原始/完整C导出LEF同层PIN/OBS相交782/777（含PG）只作矩形诊断，包含可能的同网形状，不直接判不可接入。
- 原始匹配父层handoff/层序及缺失宏GDS已向用户询问位置；现有资料中继续保持未知，不指派目标层。根因未完全定位的RCX后ODB问题仍在，隔离流程不等于已修复工具或证明绝对RC正确性。
