# 异构链保留真实源所有权与目的提交资格

Issue179 / PR180；Melodydt；2026-11-07 Asia/Shanghai。

新增U/F/C/J→P四个定向RAW128变体，每任务双端各CALL一次，序号历史配对。固定物理端点隐含路由；job/epoch/task_sequence/service_sequence以128 bit显式同行。目的预约地址及身份必须匹配才发写请求，真实P存储响应产生commit。源另存commit_seen并核对完整ACK身份后才消费S响应或J输出；正确身份的过早ACK也不生效。

SEND/RESERVE/RECEIVE是现有L_EXEC的原生服务，执行ISA保持64 bit，ABI0x01930001，以新topology隔离合同。无隐式格式转换，J为T提交输出而非普通S读。共同复位/重装可恢复，完整取消/故障及适用CDC留第6步。

168/168功能、4/4控制结构分别验证；源数据与完整目的S读回独立对照。结构使用明示宏黑盒，新增组合STA/CTS/物理未执行；周期目标3.333333333 ns不变。详细合同和结果见project/control_hetero_boot_v1/README.md及work/Melodydt/179/control-hetero-validation.json。
