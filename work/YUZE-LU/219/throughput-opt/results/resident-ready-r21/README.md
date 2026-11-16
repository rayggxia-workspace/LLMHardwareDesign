# 迭代21冻结证据

`evidence.tar.gz`：3,184,344字节，SHA-256
`d6def42f694dfc858813e1a66e887e2594dc2c3a61f2e687a284a2add342862f`。
245个成员全部逐项SHA核对，无去重别名；标准tar解包即可，成员索引见 `manifest.json`。

`batch-terminal/` 为101657终态：18个冷tile、72个固定顺序候选，原始冻结代码、输入/输出摘要、日志和Slurm回执。
`runtime/batch-terminal-audit.json` 及外置同名回执为新独立审计：288组边界/随机轨迹，原生解释器及原整数算子输出全部匹配。
审计命令见 [合同](../../../../../../project/experiments/block_synthesis/RESIDENT_READY.md)，IR使用迭代18冻结文件SHA：
`3fff3712f59ff04eedd491fe87fd913a7487fd34a01203eaf3afdd70e212165c`。

`runtime/` 包含309项Windows/Linux通过日志、首次Windows临时盘17项失败和修正后的完整通过日志、
本机长切片解包异常与冻结源，以及301/302提交回执。
`frozen/` 保留两个不可变服务器源包；301有窄束/贪心标签偏差，302是修正后的严格贪心对照。
两项搜索冻结时仍运行，不把阶段输出或提交回执记为新性能通过。

这是合成输入冷tile与算法测试证据，不是新批程序RTL、实际权重、整循环、全模型、DRAM或SystemC/能耗/token/s验收。
