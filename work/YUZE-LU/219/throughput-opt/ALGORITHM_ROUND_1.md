# 算法迭代1：当前搜索空间还有多少余量？

2026-11-09 CST，Issue219，准备外提作为共同后端基线，不计算法收益。

对每个任务t，取全部候选中乐观的全命中成本下界l(t)。
若无论选哪个候选都需要同一资源r，则这些任务在容量c(r)上的累计占用至少为：

```
LB_resource(r) = ceil(sum(l(t) for all t that must use r) / c(r))
LB_path = longest_dependency_path(sum l(t))
LB = max(LB_path, all LB_resource)
remaining_reduction <= 1 - LB/current_makespan
```

代码从候选的资源交集计算强制资源，不识别P/U或模型名；具有其他绑定的任务不能误算成必须使用某资源。
独立计划检查先核验当前计划。全命中假设故意乐观，只用于下界，不能据此产生实际命中。

| 当前候选族 | 已验证计划 | 乐观下界 | 在此候选族内的剩余降幅上限 |
| --- | ---: | ---: | ---: |
| 五组 | 1,220,294,552,058 | 1,220,290,609,986 | 0.000323043% |
| 九组 | 915,946,939,994 | 908,939,702,994 | 0.765027% |

五组主要被P0.M/上下文、S.IO、LC和memory.channel.0的整个内核占用锁住；九组被原子内核依赖链约束。
这证明继续用相同原子候选调beam、重排或增加缓存保留分支无法取得约20%的执行时间收益。
**它不是硬件性能下界**：更细阶段、数据分片、预取/计算交叠和不同驻留方案不受此候选族限制。
下界也不意味着当前搜索全局最优；具体可达最优仍介于下界和当前计划之间。

下一轮：让算法显式权衡S前缀驻留与预取缓冲，并用真实端口/银行/ACK和M上下文构造分阶段日历。
先核验原生M双输入bank、行/列/K段和实际局控/适配器能否发出所需重叠；不能在模型中凭空增加并发。
共同候选与代价必须同时交给强贪心/启发式和DP/局部搜索，区分候选扩充收益与搜索决策收益。

代码：project/experiments/block_synthesis/search_diagnostics.py；本地和Slurm100652均112项通过，作业COMPLETED0:0。
[五组下界](results/search-bound/five-groups-bound.json)、[九组下界](results/search-bound/nine-groups-count-experiment-bound.json)、
[输入/源/原件SHA](results/search-bound/receipt.json)。6份输出逐项回收核对，输入IR与前轮正式计划一致。

SystemC初查：本任务缓存的#198七宏模型有独立SC_THREAD/FIFO包装，但头文件明确无时钟和人为延迟；
不能继承时间/功耗资格。服务器host的pkg-config未找到SystemC，需要继续核查容器/工具环境，必要时安装官方实现。
后续必须补齐校准时间和能量参数，以及带KV decode；现S2 prefill不作decode token/s声明。

算法20%目标、后续多轮、SystemC/能耗及充分优化的ASIC/FPGA对照均继续进行。
