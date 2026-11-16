# Dot 操作数准备复用

输入仍是现有模型图、硬件清单、已资格化原生命令时间与整数程序；启用 `--prepare-reuse`。
它是通用的循环不变量外提，不根据模型名、层数、P/U 实例数设置规则。

对输出形状 `[..., R, N]`、归约长度 K 的 Dot，把 batch 展开进 R：

```
旧：for r,n: prepare A[r,:]; prepare B[:,n]; accumulate whole K; final round
新：for r:   prepare A[r,:] -> explicit external region
    for r,n: prepare B[:,n]; read prepared A; accumulate whole K; final round
```

只有实际 S32（三个 S16 分量）的 A、N>1、且外存地址空间/声明容量能容纳新区域时适用。
S16 A 或容量不足保留原实现。广播时每个输出行仍独立准备，不假装跨 batch 免费复用。
`B` 的准备、全部 partial、唯一活跃 M 累加上下文和最终舍入原封保留。

每个 A 元素调用已有 split32 一次，三个有符号 S16 标量记录顺序为
`low16, signed_high16, low_negative_flag`，满足 `raw = low + 65536*(high+flag)`。
每个分量仍占完整 128 位字，没有免费压缩或新算术。
地址为 `base + ((row*K+k)*3+component)`；源地址从原 Dot 的 `(row*N,k)` 访问解析，
同一行各列共享这些只读分量。准备阶段在第一个消费者前完成所有 STORE/ACK；区域一直保留到最后一个输出写确认。
所有区域静态分配互不重叠，当前实现不做外存生命期压缩。

若一次原生 split32 在 binding b 上的完整代价为 P(b)，则：

```
removed_calls = R*K*(N-1)
T_new(state,b) = T_old(state,b) - removed_calls*P(b)
reads_new  = reads_old  - removed_calls*split32_reads
writes_new = writes_old - removed_calls*split32_writes
```

P 包括实际宏命令、S 读写、#182 模型 LOAD/STORE；不是只删计算时间。新区域的 STORE 已包含在剩余 R*K 次调用里。
原有只读 S 前缀仍在每次 DP/贪心扩展时按当前状态计算命中，准备复用与此前的 LOAD 复用分开记账。
新配方没有增加线束或 S 空间。它改变原生命令循环的工作量，不是 DP 搜索本身的收益。

独立检查器不调用外提函数：自行从算子形状和分量数推导命令量、核对绑定成本、区域/容量/地址位宽。
数值回放生成实际一维外存分量，从它们读取并恢复 A，再进入选定的有限 S Dot 路径。
这不是逐条 MC/LC 指令或系统 RTL 执行；全模型范围仍以输入的数值资格为准。

`prepare-reuse-plan.sbatch` 生成完整五组、九组和同连接预算计划；`reuse-replay.sbatch` 做三输入回放。
保留未启用开关的旧后端与原结果，实验应同时报告贪心/DP、线束预算、外存占用和编译开销。
旧全写回计划用 `all_spill_reference_tasks` 单独核验，不能拿新时长去核验旧计划。

当前没有搜索跨 Dot 的准备共享、脏中间结果驻留、任意融合、S64 累加器 spill 或计算/搬运重叠。
