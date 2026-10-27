# T6K候选模型的电源类型与完整flat时序源

164原生write_timing_model将实际POWER/GROUND边界VDD/VSS写成普通input pin，0电容及max_transition=.199。原界面接收只核LEF PG，忽略Liberty供电语义；#127独立合同拒绝保持，164不改写。168新版本保留原candidate-raw.lib，只将严格核明无逻辑/时序语义的这两个零电容伪输入组替换为pg_pin，分别primary_power/primary_ground及对应voltage_name。逐项逆变换必须恢复原模型全部字节；其他所有信号、表格、约束和时序弧不动。

类型以[固定OpenSTA读取器](https://github.com/The-OpenROAD-Project/OpenSTA/blob/bc7af6f02679074eaf43657488ca117c05f98eed/liberty/LibertyReader.cc#L1149)的pg_pin语义为依据；供电类型与普通inout方向不同。实际安装工具还需独立read_liberty后按明确library/cell find_liberty_port，要求is_pwr_gnd为真、direction分别power/ground，并与同源LEF POWER/GROUND保持。没有通过原生读回前不宣称修复通过。保留原145已资格的信号/typed bus读取脚本SHA，新增供电检查使用独立native_pg_pins.tcl。

另一个独立问题是ORFS 6_final.v过滤了ANTENNA_X1，不能用来接收包含真实保护负载的全部SPEF。161完整物理接收已经从实际ODB导出physical-functional.v，保留全部信号单元及189个保护单元，并逐cell/pin-bit证明仅审计过的输入型无状态ANTENNA_X1与原过滤源不同。168正式交付candidate-timing.v为该已接收文件的SHA严格副本，同时绑定physical-functional-proof.json、161收据和160 ODB/原过滤V来源；不重新推导/假造缺失RC，也不改变原生STA物理接收。#127此前缺189实例/部分net的flat对照保留为context拒绝，不能据此将全部偏差归因于宏模型。

本地控制绑定两份实际164 Liberty SHA及161完整物理proof：两路精确逆变换与189负载选择通过，22个错误供电属性/类型/缺供电/重复转换/失败来源/漏负载/错误网表hash等反例均拒绝。仍待168实际原生导出/读回，边界误差、窗口寄生和宏冻结均未通过。新worker native-typed-view-group在一个c96 allocation双8CPU工作，完整物理源仍为160/161，不重跑P&R。


## 2026-10-27 17:44 CST 实际执行

168/92335实际T6K两路typed PG与完整flat timing网表交付通过，0:58、TotalCPU2:54.816、MaxRSS3193048K，node21双8CPU。原始模型保留，VDD/VSS仅转换pg_pin，精确逆变换证明全部其他模型字节不变；实际原生读回power/ground及is_pwr_gnd全部通过。candidate-timing.v严格复制161实际ODB完整信号导出，两路各保留189保护单元并绑定完整proof，旧6_final.v继续保留但不能充当full-SPEF flat源。169/92336用PR128固定5eda23a源只读导出实际ODB占用，node22双1CPU，2:47、CPU4:07.617、MaxRSS3592768K；A453227实例/2229968个master OBS、C451330/2232347；完整占用666023293/664926056字节保留服务器并封存SHA。仅导出通过，独立覆盖/边界资格仍待#127。167/92333仍RUNNING，node20双8CPU，不能先称C8新RC/全片DRC通过。新170准备补查严格C8前后完整图的无驱动使用bit及未使用输出，不改图/日志/严格门，本次提交尚未运行。完整P0–P6及宏冻结/两个新增层产品未完成；登记pending、看板unverified/同步pending、待独立审查。

168/169 group与全部peer终态索引均位于work/YUZE-LU/121/results/run168-*及run169-*；同源交接inventory为t6k-qa127-handoff-168.json，每路30角色，仅索引，独立pack仍需前后hash。
