# V 命令接受与运行状态使能分离

Refs #121 / PR #122。一个基础 V，不增加版本或放宽 300 MHz。

V363 最终 RCX setup −0.13 ns/TNS −12.04 ns，cmd_valid→stats_sumsq[1][79]；原始报告及映射见 work/YUZE-LU/121/review-20261028/v-363-finish-diagnosis。hold 只有报告舍入 0.00，独立门未通过。

旧结构在 if(cmd_valid&&cmd_ready) 的 else 中执行 case(phase)，把外部 cmd_valid/rsp_ready 的优先选择引入运行状态的数据写入使能。cmd_ready 明确要求 phase==IDLE；case 的 IDLE/default 不写任何寄存器，所以接受命令与非 IDLE 状态动作始终互斥。

选定修改仅将该 else case 改为独立 case(phase)，仍在同一个同步 reset 的 else 中。非阻塞赋值按旧 phase 判断：IDLE 接受命令时 case 为空，非 IDLE 的 cmd_ready 为 0、命令分支不执行。响应消费的先后顺序不变；不增加周期、存储、端口或算术单元，不改数值格式、异常/饱和、RNE、回放、统计上下文、带索引选择或操作延迟。

后续使用新不可变源 367，执行三初态功能、公共/扩展、组合、逐命令延迟、映射及算术证明；重做占用/有限预算绑定与六阶段物理、所有独立最终门/六文件/完整几何/接口。不能把 363 的物理资格转给新源。现有全部 EDA 正常收尾。
