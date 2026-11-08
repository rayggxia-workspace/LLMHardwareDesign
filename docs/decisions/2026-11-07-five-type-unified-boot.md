# 五类统一装载保留原生数据语义

Issue179 / PR180，Melodydt，2026-11-07 Asia/Shanghai。

复用原有MC/LC、control_pm和control_boot_manager，新增编译期KIND的两目标控制封装，公共装载命令及64 bit执行ISA不变。普通U/F/C/P沿实际私有S端口读写；J保留片段tag/slot/last和T输出释放语义，以管理命令13/14明确适配，不伪造任意SRAM读回。

J使用4项提交结果FIFO，每任务一次JOIN、1-4字，完整任务身份随真实输出捕获；主机接收回复才归还槽位。运行、未消费RESULT/输出期间互锁写入和新START。J原生8 bit epoch限制为1-255。未接线的发送/直连边返回不支持。

当前是五个同类双目标变体，后续第5步再按声明拓扑连接异构数据和身份ACK。功能210/210、结构5/5和上游相关66/66分别验收，场景通过率不等同覆盖率；完整新组合STA及物理未执行，周期3.333333333 ns不变。复现与证据见project/control_five_boot_v1/README.md及work/Melodydt/179/control-five-boot-validation.json。
