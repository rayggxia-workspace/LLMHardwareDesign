# 决策：L4先闭合真实尺寸整数行，单独保留模型质量门

状态：实现候选，待外部审查；Issue151/PR152。输入75d99a5，服务器源6a7de2c8，95245已通过N38/F26。

新增独立N-long与H1024/I3072顶层，保留旧模块；单M按K32流式供参、全K raw累加后统一量化，S保留原X/完整Norm/mid/output、宽容器单列，避免缩形和隐式spill。供参固定顺序并以job/seq/version及真实写ACK门控，不通过provider装载控制程序。

真实维度和整数执行资格与trained-checkpoint质量分开：epsilon2^-20及S8/S16固定尺度未获源模型接受；dense合成fixture饱和显著。原准入账本不放宽；后续由资料拥有者向获授权存储交付tensor/输入/FP32参考及误差门，再决定重定标资源。真实MEM、完整A/L5和M11/M12物理差分不在本候选资格内。

取舍：串行一个M/N/E/G/S/T节省并行实例、降低存储上下文复杂度，但每行9MiB参数及36864EXEC可能形成性能/带宽瓶颈；当前只证明功能，未做吞吐/PPA选择。hardreset需provider协调、已take前缀不能回滚。来源及证据见[实施报告](../W4_F1024_IMPLEMENTATION.md)。
