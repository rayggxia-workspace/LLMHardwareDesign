# 当前统计前缀源的有限资源预算

Refs #121 / PR #122。resource-budget-after-statistic-prefix-595.json使用577五项实际S/V测量，43个规范Git字节输入；输入清单与对比报告分别为同前缀-inputs.json和-comparison.json。14个报告引用源SHA重验，8个模型各10个有限分析候选，与旧551的80个成本字典完全相同。这里的候选只用于已测统计/归一化子集的分析，不产生第二种物理宏，不启动阵列/系统实现。

统计前缀修复保持逻辑周期，故新测成本一致；逐元素当前7拍、统计5拍、8元素函数9拍、TopK40选8为328拍，N256本地RMS/L2=551/Softmax618。局部操作周期不代表整模型吞吐。full_model_10tps_qualified、integer_quality_qualified与prefill_latency_measured均为false；当前V/R尚未物理验收。旧551证据保留。
