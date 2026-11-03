# 固定 FFN8 与岛内 E/G 服务

- 日期：2026-11-01
- 状态：proposed
- 决策负责人：Melodydt
- 关联Issue / PR：[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151) / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)
- 替代记录：无；在既有静态共同底座与唯一S服务方案上增加有限RTL切片证据

## 背景

现有宏的payload、响应和生命周期不同。M.op5的四个S32载体并非紧凑S16包，G每拍只有两个S16 lane；S写有必须消费的真实应答。单M的merged结果不能在另一次CLEAR/EXEC后免费恢复。为验证实际跨宏连接，先选固定8维FFN核，锁定算法、数值、布局和存储范围，允许输入tensor/权重内容变化。

## 决策与原因

采用一个本地固定FSM，M/E/G/S/T各一个，普通S由唯一helper和LOCAL/E/G owner选择器驱动。E/G服务在输入采集、原生算子握手、结果收集与目的写ACK全部完成后返回response；top在response消费前不切换owner。M gate/up/down严格串行，结果保存ACK后再清空M；G门乘后补齐三个真实零padding字，供down A16 loader读取。保留直接S512 loader到M的原生路径，不增加通用49对互连。

数值采用本次明确的S8 Fin7→S16 Fin10合同，通过原生M.op5实现两次不同shift的RNE和裁剪，用E7对齐残差，再E0相加。用单独done_saturated记录定义内的clip，避免把允许的量化饱和混同协议/原生错误。本次只验证预制固定FFN8程序；跨产品永久选择和完整有限程序库仍未实现。不得把这个FSM当作所有产品的母控，也不能以每个产品重综合控制器替代未来共同底座要求。

## 考虑过的其他方案

完整decoder层或完整F一次实现，需要同时闭合N回放、真实大shape存储、数值质量及跨岛接口，超出本次可独立验收范围。gate/up/down各配一个M可增加并行机会，但会改变面积和调度问题，当前选择单M串行基线。仅把M结果引脚直连G会丢失slot提取、gate/up配对和存储生存期，不能替代实际适配；通用运行时类型/程序系统也不是本切片所需的最小控制。

## 影响与验证

代价是新增固定FSM、捕获/拼包寄存器、E/G适配器和真实S往返，尚无新增逻辑的综合/PPA结果。收益是将宏角色、payload和ACK/phase/DONE拆为可检查的有限执行步骤，证明输入数据变化能够经过真实M/E/G/S/T产生独立预期输出。正常帧使用S保留416B及T单字lease，不能把该保留量当成整个宏或完整模型的存储需求。

测试分别验证独立整数参考、E/G standalone和固定FFN8，保存所有源码/工具/命令/日志SHA；原P2/W1回归单独留存。局部FFN-r02有21检查真实通过，adapters-r01有46检查真实通过；有限测试范围详见验证报告。当前本地controller不代表整片母控、M11/M12实现、跨岛活性或模型编译完成。后续N主线补阶段控制与回放；MEM、R、MoE、真实样本尺寸及系统物理保留各自验收责任。

reset/abort采用协调清空本地和原生生命周期，RUN中止产生一份保持到take的error completion；已有DONE的error/saturation保持且可同拍消费。此方案不支持未协调的adapter单独cancel，也不回滚已接受的RAM写或外部已消费前缀。特别是目的写ACK报错发生在写已接受之后，只能报告失败，不能声称目的未变；当前真实S helper的error恒0。
