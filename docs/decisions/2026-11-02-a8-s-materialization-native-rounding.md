# A8：复用M量化读出与S物化完成有界Attention核心

状态：proposed，已具有有界RTL功能证据，外部设计/PR审查待完成。Issue151/PR152；2026-11-02。

本次采用M/N/S/T各1的本地固定序列，M的op4/op5完成QK缩放及两段RNE，N复用现有组服务。直接使用现有原生功能可以先验证宏间同步，不引入尚未实现的通用NUM或独立bridge硬宏。数据分别物化为score/EXP/prob/output，按实际存储ACK关闭阶段。

M A/B loader基址要求4word对齐，prob地址从最初讨论的462改为464，465..467实际清零并ACK后才启动PV。K按key×dimension、V按channel×key由host准备，未实现通用转置；这一限制必须保留在软件合同和测试中。CLEAR原生命令为op6，内部MC_CLEAR=0只表示阶段编号。

共同预制硬件在冻结前应包含所选FSM、MUX、holding、buffer和必要数值适配；M11/M12不能补造这些有源功能。此小FSM验证本地机制，不能作为已实现芯片母控、有限产品ROM或完整A_plain/A_gate的证据。

服务器复用现有Verilator5.042及shared Singularity入口，容器HOME/tmp/cache限定本人目录。环境/默认warning fatal的失败全部保留，最终功能执行保留所有warning；严格lint门未通过，不影响如实报告功能检查结果。后续先补模型实际Attention完整流程和尺度/layout合同，再扩真实shape与容量映射。
