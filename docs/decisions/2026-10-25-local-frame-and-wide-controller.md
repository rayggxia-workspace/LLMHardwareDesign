# 2026-10-25：优先固化宽运算局部反馈，继续保留跨模板物理映射

状态：有实际 RTL 证据的候选决策，待 Issue80/PR81 审查；不是制造宏定稿。依据 [Issue80 报告](../experiments/issue-80-block-circuit.md)，继承 PR77 的精度和有限库存约束。

Issue76 的完整 expert→merge 条件服务显示，近 M 驻留差仅约 0.00084%，共同 byte frame 开销更值得校准。本轮补上真实取指/寻址/宽控制器和有限 frame，避免继续依赖软件逐动作调度估计电路。

同 8 条 S8 lane、512B/单 1RW、单 ROM、相同程序/算术的 BUS-frame 与 LOCAL-frame，在 895×4 个命令中完整 frame 逐位相同。静默与同外部事务等待下分别少 44.029% /42.476% cycles；所有差值均为 7×实际 frame 事务数，未删除取指、RMW、scale 或调用者 IO。Nangate45 研究库逻辑面积 LOCAL 增约 0.157%，不含两侧共同 frame/ROM 整体 wrapper，非目标 PPA。

据此将“有限局部暂存＋宽算术读改写反馈＋明确完成/错误协议”提升为首选制造内连接候选。保留 128bit/1RW 旁路端点和真实容量/credit，不能进一步推导为免费多口 RF、无需 SRAM 宏时序或任意宽算术。

M 的同单位 INT32 fullK 局部累加、typed partial/complete、可绕过 RQ/宽对齐不变。M/V 合宏、独立 R 宏、A 的矩阵复用、动态 expert/bank/backing 端点和产品布线仍保留选择；没有新的证据支持冻结它们。六逻辑模板不等于六硬宏。

成本反例必须影响下一阶段：两个 norm8 平均 LOCAL 5787401 cycles，程序 1.93MB，说明纯 byte lowering 不适合作为最终高吞吐 norm/SFU。下一步只比较会改变电路选择的受限专用化：宽乘/进位、有限 RF、除法/开方/LUT 组织；每种都固定相同精度、舍入、容量和实际端口，并记录新增资源，不能把速度归给划分而漏算硬件。

冻结物理边界前还需实际 M partial 到完整消费者链、合法 SRAM/ROM 宏/Liberty/LEF/PVT/时钟、布局/布线/STA 和团队 Issue55/63 的同版本映射输入。当前不得报告 E2E 加速、同面积 PPA、全整数模型质量或完整状态原子发布已完成。
