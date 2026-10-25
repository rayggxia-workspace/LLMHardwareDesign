# 决策：耗尽tag必须终止并排空，reset撤销接口发布

关联Issue92/85。维持32位代际计数，不允许wrap。最后合法命令可以运行在max；max空闲或abort时所有响应排空，不进入已撤销消费者。重新开始必须核心与fabric协调硬复位，保留SRAM而重载被中止的输入由调用者负责。

reset/soft_abort优先于cfg request、cfg response及done/ack。调用者发出reset时同时取消已接受但未响应的cfg，复位后按需要重试。已接受写入不回滚。选组合过滤/mask以避免额外状态/队列；同版实际边界、10条原门锥安全性质和完整消费者接收通过。

成本不省略：同16KiB1RW、8S8+1S32、4309generic寄存器bit；核心映射cell变化计入，外部两槽320bit数据/tag加控制和32bit互联另列。该决定关闭协议安全缺口，不冻结物理宏边界、不授予STA/整机通过。证据见issue-92-epoch-boundary报告。
