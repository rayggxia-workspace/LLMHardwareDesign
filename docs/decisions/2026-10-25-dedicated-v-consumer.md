# 专用V前处理作为有界消费者闭包（Issue97）

2026-10-25，Liangruizhi；[实验证据](../experiments/issue-97-v-consumer.md)。决定先实现专用SiLU/MID/完整512范围量化数据通路，接真实驻留M和93流式norm；80通用V ISA保留独立，不为本次复制8个byte乘法器、私有frame或ROM。理由是当前缺口在真实动态scale/A的生产消费与S生命周期，而通用取指/byte ALU是另一项工程义务。

此取舍没有免掉宽运算：signed compare、abs(INT_MIN)、RNE/变量shift、LUT地址、元数据、五行寄存与FSM全部实际映射计费；70,102.970µm²只是不含宏的参考逻辑面积。C0 LUT外置的所有128bit行请求/5beat桥计费，外部ROM和tag/fabric物理成本明确未含。不能声称它比通用ISA更优，因未做同功能同版本两实现对照。

冻结的语义是完整512范围确定δ，A与scale/owner/version/epoch一致发布，S复用前排空服务。接口新格式拒绝旧host δ，oracle从原始gate/up核对静态scale不变。元数据故障/终止epoch的验证后门仅用于RTL，不迁移成门级输出赋值证明。

有界V→实际M→norm的L2和selected raw gate已获接收；通用M/V、在线GQA A、完整原子R、宏/STA/产品后定制均未完成。98单独检查新93/97图的物理代价与固定预算，99独立推进R；若新物理失败保留原失败并改结构，不提高预算遮蔽问题。
