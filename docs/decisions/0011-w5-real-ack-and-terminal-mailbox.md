# 0011：主线五G1以真实边存储ACK和独立终态mailbox闭环

2026-11-03，Issue151/PR152，候选实现待外部审查，不是物理冻结。
同一母表顺序器、固定A/F程序与独立edge S解释G1；源T在真实edgeSACK后退休，host出口用独立index/generation确认。增加S16KiB、控制/holding/字有效位/对象及引用metadata，均单独计价。
完整终态采用45bit mailbox一次锁存，隔离SEQ错误与executor poison收敛时序；消费前挡新job。原n01正常回归未覆盖的late-ROM窗口已修复，n02测试误读valid外旧tuple失败保留，n03改成liveACK计数和valid门验证，最终12组件+18G1通过。
没有每产品父FSM重综合或启动装载程序；ROM/metadata读口只是仿真永久内容模型。未来真实金属位单元、ROM/驱动/landing与共同几何另验；当前单profile/G1，参数cohort限制、更多图及系统故障不豁免。详见[完整报告](../W5_G1_NATIVE_AF_REPORT.md)和[实现限制](../W5_AF_IMPLEMENTATION_LIMITS.md)。
