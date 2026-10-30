# 修正后V与原R的十队列准入

Refs #121 / PR #122。配置只监控404/405/406、旧508/509、新520/521/522/523/524；本Issue最多8 allocations，含旧/PENDING/UNKNOWN，c96默认6×16动态补位。只有真实前置或RAM限制减少并发，不以空任务占资源。

staging-verification.json核验10份实际远端manifest/queue与本地字节相同，dispatcher/队列执行器来自各自封存Git blob；source-chain.json核验新检查/原生源与独立最终源全部RTL/仿真源字节相同。当前仅准备，部署须使用已提交的canonical字节、运行正反例、实际生产配置预检，之后才能退休旧510轻量登录控制。任何EDA均不取消、不重启；部署回执生成前不称已接管。
