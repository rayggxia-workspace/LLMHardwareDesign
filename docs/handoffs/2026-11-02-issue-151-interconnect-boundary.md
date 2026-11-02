# 三层互联边界安排交接

仓库https://github.com/rayggxia-workspace/LLMHardwareDesign；Issue151/PR152，负责人Melodydt。分支task/151-six-connection-study，base task/143-seven-block-v2，输入commit 714cab4fda64c8e5cdd74c57ae8bc704e4902981；本次交付commit读取PR最新回执，不伪填。

本地独立API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/control-boundary-714cab4/integrated，无.git/HEAD/暂存；旧A8包、根管理参考副本、他人文件和ref-project保留。新文件/修改白名单及实际检查见本任务上传回执与interconnect-boundary-checks.json。

成果：三层互联实施安排、proposed决策、工作包/八主线进度与机器索引、自身进度。本轮仅文档/计划，不改RTL，不新增仿真/服务器/EDA，不把任何接口或物理层冻结。当前仍L4，W5-IF具体接口合同待编，L5 RTL未开始。独立SSH+Slurm+Verilator及本人服务器目录政策保持，Moba不是依赖。

安排：L4先定端口/事件/ACK/资源/layer约束；L5/W2-C做固定母控任务/事件网、W2-D双岛目的stored ACK/源释放，W6扩一般拓扑；L6/7补状态/动态事件；L8/W10/W11真实MEM与共同M1–M10/PG/CTS及至少两产品M11/M12差分最终验收。物理pin/扇出/中继/资源需求从L4/L5前置，不到L8才补有源逻辑。

三类证据分别记录：计划已形成待审查；新接口合同未完成；RTL未开始；物理未冻结。原A8服务属于714cab4固定源/95116历史证据，本次不重跑或扩大其范围。

在线状态以PR/Issue最终读回为准；登记management-hub PR5本轮open/unmerged→pending，无board.json/Projects item工具→看板unverified、同步pending、处理人待指定，未证实权限拒绝。外部审查人待指定，不自合并或done。

恢复第一步：核最新Issue151/PR152头、此交接与interconnect-boundary-plan.json，再编制W5-IF有界端口/事件/资源表。主要负责人Melodydt；物理拓扑/具体位宽/规模待测算和审查。不得把本次计划提交视为已完成全局控制网或转入L5 RTL。
