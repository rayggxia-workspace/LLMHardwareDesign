# 实际最终M与新S门及V失败证据

28份小文件，实际捕获01:24:57 CST；逐文件大小/SHA见[index.json](index.json)。M258独立四门及最终文件/完整原生几何全过，740µm/275信号位；其余M物理/功能/LEC见前序同一源证据。S246原生全流程完成，258物理setup+0.687419ns/hold+0.012282ns通过，功能/DRC仍运行，不能接收S。R236映射通过并进入原生物理。

V236 GRT原生失败，最终overflow3882、72.98%资源使用；native日志明确建议将上层调整25%降到20%。v-grt-failure-extract.json绑定原生回执及完整日志SHA，摘录错误末尾。263标量配置后来被证明无效并停止：当前ORFS不读取GRT_ADJUSTMENT、FASTROUTE只在floorplan初始化；264改在PRE_GLOBAL_ROUTE_TCL执行真实原生setter，其他规则/SDC及M1–M10上限保持。失败与无效配置不是通过结果。
