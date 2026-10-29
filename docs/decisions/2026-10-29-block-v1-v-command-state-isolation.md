# V 命令接受与运行状态使能分离

Refs #121 / PR #122。一个基础 V，不增加版本或放宽 300 MHz。

V363 最终 RCX setup −0.13 ns/TNS −12.04 ns，cmd_valid→stats_sumsq[1][79]；原始报告及映射见 work/YUZE-LU/121/review-20261028/v-363-finish-diagnosis。hold 只有报告舍入 0.00，独立门未通过。

旧结构在 if(cmd_valid&&cmd_ready) 的 else 中执行 case(phase)，把外部 cmd_valid/rsp_ready 的优先选择引入运行状态的数据写入使能。cmd_ready 明确要求 phase==IDLE；case 的 IDLE/default 不写任何寄存器，所以接受命令与非 IDLE 状态动作始终互斥。

选定修改仅将该 else case 改为独立 case(phase)，仍在同一个同步 reset 的 else 中。非阻塞赋值按旧 phase 判断：IDLE 接受命令时 case 为空，非 IDLE 的 cmd_ready 为 0、命令分支不执行。响应消费的先后顺序不变；不增加周期、存储、端口或算术单元，不改数值格式、异常/饱和、RNE、回放、统计上下文、带索引选择或操作延迟。

后续使用新不可变源 367，执行三初态功能、公共/扩展、组合、逐命令延迟、映射及算术证明；重做占用/有限预算绑定与六阶段物理、所有独立最终门/六文件/完整几何/接口。不能把 363 的物理资格转给新源。现有全部 EDA 正常收尾。

实际367：六行为/算术项通过，三初态各566999检查/414906拍、公共42/扩展36测量全同361；映射仍运行。原363六阶段自然完成但setup未过，不转移资格。

实际续进：367七项全部通过，映射415764（较361少29668、非物理面积）；373纠正368父类型错误后七测量通过，135有限+78公共字段保持，80预算重绑。374全新物理已93372/node17运行，375/376仍待前置，377实际准入。

2026-10-29 19:53:30 CST：V374 已完成 CTS 并进入 route 阶段；最新日志为全局布线修复。CTS setup/TNS −0.01/−0.02 ns、hold −0.04 ns，尚未通过；最大 norm_square[1]→group_unit.denominator[127]，最小 cmd_data[22]→input_mem[220][22]。修复内置 LEC 实际 UNSAT/IDENTICAL（51206 输入/51195 输出，差异均0），11原始文件及308源/Git/远端SHA核验；此为阶段诊断，最终RCX和375/376独立验收仍待实际结果。R344 全局布线额外迭代13/30，继续原任务，不增加版本或中断EDA。M/S/T接收保持，V/R最终未齐，目标active、Issue121=in_progress/PR122=draft；登记pending、看板unverified/同步pending、审查待指定。
