# MC/LC/P/M 与真实全局 DMA 的局部验收

Refs #250。只覆盖 `LOCAL_CONTIG_RANGE`：K128/256、静态 W8A16、显式已提交 shift8、零 bias、K0 起完整 A16 输入预置在既有私有 S。真实 MC/LC PM 取指、128B 参数 DDR 读取及 CRC、M 串行指令、四银行 S、A 租约、RF 和实际结果 S ACK 均参与。不能外推为整模型或性能资格。

| Slurm | 实际覆盖 | 结果 / 分配和实耗 |
|---|---|---|
| 102312 | MC→LC→P→M→S，DMA `0b60b134e`、M `00082574a` | 18 PASS；60 CPU 分配，19s elapsed，58.619 CPU-s |
| 102322 | 同链路，M 改真实 request 寄存级 `f08aefb93` | 18 PASS；19s，58.220 CPU-s |
| 102324 | 原生形状拒绝、真实 M/S 取消后同上下文复用、namespace FENCE；DDR 为有限测试端 | 各18 PASS；24s，61.490 CPU-s |
| 102331 | MC/LC 数值程序中真实 M FENCE→全局 drain→backend purge；故意返回一次错误 purge generation | 18 PASS；18s，58.569 CPU-s |
| 102334 | A beat3 时注入错误来源完整返回帧→真实 MC fault17→LC CANCEL→当前 M/RF/源和目标 ACK 排空 | 18 PASS；18s，57.428 CPU-s |

每次正常数值 trial 执行八个真实 CALL、18 个 M record。315 次权重64B读取与16次参数64B读取共331次 backend 请求和返回；MC 实际确认21184B读取、384B写入私有 S，24个真实结果 S128 ACK。全局 fabric 是唯一 global credit owner，每通道32 beat、32 descriptor，返回 payload 仅六个64B槽（384B）；没有叠加旧独立 credit pool。外部 DDR 测试端有64项有限待返回事务和四个保持返回 lane，和片上缓冲分开计账。

102334 每 trial 有三个 CALL、一个真实 CANCEL、三个真实 LC RETURN。前两范围结果逐位正确；第三范围的当前 K128 record 完成真实八次 A 消费后清理仍存活 RF，上游已 offer 的下个 range record 诚实以 error/未前进 K 退役。权重68请求=68返回，参数6请求=6返回，6个结果 S ACK，48次 A S128 读。MC 返回 status17 前 A/RF/guard/全局 credit 全排空；`aborting` 在错误结果保持期间为1，只在真实结果 ACK 后清零并回 READY。没有假消费或回滚前缀。

所有失败原样保留：102301 的严格 UNOPTFLAT 暴露实际组合依赖；修复为注册 owner 分块，没有 waiver/新增缓冲。102323 的上传目录布局错误、102329 的测试端未使用 diagnostic 字段、102332 的测试端对错误结果保持和 A 读取数断言错误也保留。run56 因 D 盘满导致上传包截断，未提交 Slurm；原911360B截断上传、原 SHA 和回执保留。

完整原始源、向量、日志、CSV 和银行模型存于各 `runs/*.manifest.json` 及不超过1MiB的 byte-exact parts；原 archive SHA 保留，`followup-*.json` 保存具体路径、实际CPU和时序摘要，`sacct-51-60.txt` 保存完整 accounting。功能时钟10ns用于 SRAM 行为模型，**不是300MHz STA**。

尚未覆盖：service2 streamed input、whole projection/FFN 外层、三P并发性能、完整五类 provider、非零 bias、snapshot RESTORE/SPILL、动态 S32×S32 Attention、紧急 raw ABORT 的生产 executor 恢复、能耗/token/s、最终布局布线。正常取消采用完成当前 record 再 ABANDON 的排空方式；无法匹配归属的硬错误保持 quarantine，不能把它描述为自动恢复。
