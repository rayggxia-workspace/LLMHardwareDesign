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
用 `collect_trial_snapshot.py` 创建全新snapshot名、下载后 `make_physical_summary.py` 汇总；先确认所用whole-connectivity的source ODB SHA与试验checked.odb一致。
全块几何连通可用 `full_connect_job.sh <case> <revision> A C` 对实际终态独立检查，必须使用新输出目录；旧API失败不是通过证据。
完整原父层handoff/实际层序还未知；逻辑对端和对端原pin层已补齐但不能替代该证据。完整工艺规则/GDS/LVS及系统边界RC/STA/电气仍待验证。

登记：管理中心PR5 pending；Projects未配置board.json且无工具，unverified/同步pending；处理人待指定。不得把文件上传写成在线协作接入完成。
本记录用于持续执行与审查，不表示任务完成、暂停或已验收。新的结果在同一Issue/PR增量更新，所有失败与基线未通过项保留。
