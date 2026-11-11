# run22 独立只读审计

结论：PASS。源码 `7048c35ed2912e80e62bd7827deaec480d4a7e1a`，结果 SHA `5abb31227f0c7b2c7ac9ff7eb8f80687569fab0b64bf74eb1a9ea6ccb54b518d`，作业 101884 实际 COMPLETED 0:0，c64/node1/4 核。

核对全部 106 份已回收原输出 SHA、36 项实际 payload 源及两项输入。63 次运行中 60 次成功，3 次 LANES3 以固定错误文本实际非零退出；其余 82 条 build/lint/run 命令必须成功。未运行 EDA，未复制原始日志。

默认两 lane 四类及 DIRECT0 四 lane 与 fresh exact-R2 数据/周期握手 trace 精确相等；全部原可观察事件接回实际 run18 投影及原 log SHA。普通 N 接受至完成、元数据、结果保持。

逐个完成的原生 op12 由独立整数 LUT oracle 重算，共 601560 个元素。冻结 adapter 会把所有非负 S16 钳到0，因此每个 active compute raw trace 独立覆盖的是全部32768个负值及0（32769唯一输入）；外层完整65536输入逐值比较由冻结 bench 循环与实际 PASS 支撑，不能把 raw native trace 冒称65536唯一值。逐 count CALC 直方图与实际完成响应数/ceil(n/4) 一致。NX32 n1..4 实际费用 [7, 7, 7, 7]，模型 n1..8 费用 [7, 7, 7, 7, 14, 14, 14, 14]；n5..8 仍付两次有限 S32 帧费用，未借用 packedS16 n8 单次费用。

full U 原始物理 SRAM 读回核对最近写入，每条测量一读一写、分项 wall 守恒；stateless 12 场景/102 断言/12 reset 点绑定固定 bench 与实际 PASS。R4_TRACE 没有 reset 边标记，因此数值重算对取消请求仅按固定 reset 程序限定，不宣称从日志重建 reset 波形或所有持久状态。held ACK、非法尾 lane、外层 NX32 格式由已冻结 bench 断言与实际 PASS 支撑。

未获得 STA、物理面积或 300MHz 资格；没有 SRAM 扩容或端到端大模型 RTL 证明。实际逐文件审核范围与 SHA 见 audit.json 的 raw_files_parsed；其它已回收文件只做 SHA 核对，未声称逐文件语义审核。

完整输出清单 1122 项，其中本地回收并验 SHA 为 106 项；其余 1016 项对象/二进制留在服务器，本审计未读取其内容，不把清单中的 SHA 当成本地重新计算。回收目录实际 117 个文件，63 份运行原 log 逐行语义解析；6 份关键 metadata 与 payload 内 LUT/两个 run18 输入另行列 SHA。63,447,040B 回收归档 SHA 已实算为 `5105067aeabe69441592d24f491a43f3d3ec7602ba8870678830b40a7b8a3221`。

审计修正记录：初稿曾误要求原生端 65536 唯一输入，读回冻结 adapter 的 clamp 合同后改为32768负值加0；外层完整65536输入测试仍不变。仅修正独立审计断言/说明，没有修改生产或已测 bench 源。
