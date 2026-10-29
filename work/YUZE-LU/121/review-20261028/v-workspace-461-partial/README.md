# 461：五项有限S/V测量通过，两项占用入口拒收

Refs #121 / PR #122。源074923df/归档2919ca01，93607/node16。实际源/目录/argv三文件身份读回已通过，五个有限S/V测量的独立回执通过。两个occupancy任务被旧421 public-provider断言拒绝，尚未建立其instrumented build，父队列FAILED。不能说七项全通过；五项成功结果保留，不重跑。

462只重试这两个occupancy模式：绑定真实459公共/扩展结果，补采function_fetch valid槽与实际mask有效元素，所有公共结果仍必须完全复现。模型/系统质量、功耗、10token/s不由这些测量证明。后续预算实际读取本目录的五份S/V报告，不能再使用422旧周期。
