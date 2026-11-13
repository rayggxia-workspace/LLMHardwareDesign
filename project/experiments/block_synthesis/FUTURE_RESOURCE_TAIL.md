# 未就绪任务的资源释放下界

Issue219 / PR220，2026-11-09。搜索排序改进，不改变动作池、硬件、S、外存或原生命令成本。

此前 `net_resource_tail` 对当前 ready 节点估算实际资源等待，再加乐观后继路径。
它没有充分看到另一分支中尚未 ready 的节点：当前绑定占用的宏可能正是该节点以后唯一能用的宏。
新 `net_future_resource_tail` 把所有 pending 节点纳入这个必要条件。

设状态为 s，静态网并集为 E(s)，A(v,s) 为与该并集/连接预算相容的绑定。
`c(v,s)` 为忽略未来争用、采用允许全命中时长的条件关键尾长。
在现有已提交预约保持不变、把 v 输入到达时间放宽成0时，计算：

```
release_finish(v,s) = min[b in A(v,s)] optimistic_finish(b, committed_resources(s), data_ready=0)
future_bound(s) = max[pending v] (release_finish(v,s) + max[child u of v] c(u,s))
rank_bound(s) = max(makespan(s), existing_ready_bound(s), future_bound(s))
```

这里只把不可逆的已提交资源等待带到尚未就绪的后续节点。
没有把后继按当前空闲资源当作已经排好，没有删除搬运或创造缓存命中。
普通串行孩子按各自资源释放计算；明确的 FCFS phase 协议才使用其已有整资源并集启动屏障。
固定辅助窗口沿用真实 interval calendar；不能把窗口偏移不同的候选合成一个 profile。
全命中 endpoint 只用于下界；真实转移仍由同一个 `evaluate_transition` 计算。

## 可复查小例

| 节点 | 依赖 | 选项 |
| --- | --- | --- |
| A | 无 | M0 上80；或 M1 上81 |
| D | A | G 上30 |
| B | 无 | other 上1 |
| C | B | 只能 M0 上100 |

两种 width1 策略都用相同 `ready_limit=1`，先决策最长尾的 A。
旧 ready-only 排序选择 M0，C 被推迟，总长180。
新下界看到尚未就绪的 C 将等到 M0 释放，选择 A→M1，总长111。
这是机制验证，不是完整模型收益。

## 状态和开销

没有扩大硬件 DP 状态；额外结构只是编译器缓存。
按资源候选及窗口偏移 profile 分组；每组的后继尾长以实际 task bit 建小块索引。
查询时排除已经安排的任务，即便其完成值早已离开 dependency frontier。
静态网条件表 LRU8、pending suffix LRU1024、资源释放 finish LRU16384。
普通 append-only 日历可用安全的**上界**跳过必不加强当前下界的 profile；该上界绝不作为下界使用。
所有时间保持整数，包括大于2**53的模型时长。

同池比较：`tile_review.py --registered-ir ... --policies future-greedy future-dp`。
有限 beam / ready 截断仍不保证最优；更强下界也不保证有限 beam 的结果更好。
因此始终保留已独立检查的最强同池计划，并分别记录编译开销及负结果。

`test_future_resource_tail.py`：独立枚举70组小 DAG 的容量1/2、静态互斥/预算及合法部分前缀；
检查下界不超过完整解、无状态修改；另验复合、窗口、pending索引及整数边界。

## 一版金属的诊断

`topology_diagnostics.py` 从完整最小连接 cover 逐个扩展候选线束，枚举最大合法静态网并集。
对每个并集只留下真实可用绑定，重新计算关键路径和资源工作量下界；再对所有产品取最小。
每个实际产品的可执行绑定都被某个最大并集覆盖，所以这个最小值仍是通用下界。
它修正“不同算子各自借用互相冲突的最快拓扑”导致的过度乐观，但不证明这些网可实际布通。
达到4096枚举上限时显式报告未完成，只回退原无拓扑条件下界，不能使用部分枚举宣称全局上限。
3项测试包含60组小清单的所有合法产品子集穷举、固定/零成本网和截断负对照。

实际FFN：此前强计划与新贪心/DP/backbone-DP同为4,095,979,108 ticks，额外0。
该切片125个完整最大静态并集也未加强2,962,455,648的乐观下界；不能据此宣称可达27.674%。
完整模型实验及其独立数值证据见个人轮次记录；不能用本小图替代。
通用脏中间值驻留、KV decode、系统RTL/能耗/token/s继续未完成。
