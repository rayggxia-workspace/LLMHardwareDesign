# 每次前沿扩展的状态相关成本（Issue219 / PR220）

`full_plan.py --read-cache --state-cost` 或 `state-cost-plan.sbatch` 启用。
旧 `--read-cache` 保留为二元 cold/warm 对照；两种模式共享同一个搜索。

编译器仍生成宏实例、前缀长度和固定原生命令配方；`dot_cache.py`
为 v2 模板登记模型版本和实测/虚拟外存 LOAD 单位成本。冷/热端点
继续作为独立成本检查和乐观排序下界，实际转移不再二选一。

`transition.evaluate_transition(state,binding,hardware,data_ready,retention=...)`
是纯函数，统一求合法性、实际搬运、持续时间、资源和缓存新状态。
宽度1与宽度8都调用它，失败不会修改旧状态。独立检查器不导入该函数。

对于相同 SSA 输入、行布局、K 和数值分量的已有前缀 q，本次使用 t：

```
h = min(q,t)                         # 身份不匹配时 h=0
reads = R*a*(t-h) + R*N*a*b*(K-t) + R*N*K*b + 1
duration = cold_duration - R*a*h*LOAD_cost
start = max(input_ready, required_resource_available)
end = start + duration
delta_makespan = max(previous_makespan,end) - previous_makespan
```

只有 A 的实际省略 LOAD 被扣除；B、零包、原生命令、本地访问和所有
STORE/ACK 不变。不假设计算/通信重叠，时间仍是原模型代价，非芯片周期。
原全部写回配方单独保留，t=0 的 B/零包复用配方不是原基线。

每个当前状态实例化 preserve/discard；已有相同输入的更长前缀时还
可选 shrink。preserve 保留 max(q,t)，shrink 只保留 t，discard 在
本次消费后释放有效记录。t=0 且不覆盖缓存区时可保留另一个旧输入；
写新输入到相同缓存区则替换旧输入。只读丢弃不写回、不清零，不额外预取。
活跃 scratch 与保留区的峰值/地址以及空隙期间驻留均由独立检查器核对。

计划行增加 evaluation：版本、保留策略、reused/loaded/retained_prefix、
实际外存读写、scratch_by_site、duration 和 delta_makespan。cache_hit
仍表示完整命中，部分命中由 reused_prefix 明确表示。

有限 SRAM 回放从旧 packed 数组读取命中部分，只从输入补齐缺失部分，
并按保留策略保存或释放；不能只修改流量数字。全部K仍使用一个M上下文
并最终一次舍入。一般脏缓存、算子融合、DMA/RTL/物理覆盖不由此获得。

验证：原100项回归、部分命中的80组逐记录计数、纯函数不变性、身份、
容量、三种保留策略的独立调度检查与实际S数值回放。完整模型复验保持
Qwen2.5-3B、B1/S2无KV、三输入和原2%HF门槛，五组/九组/同10束对照。
实际结果和源/输入/输出绑定见 `work/YUZE-LU/219/STATE_COST_RESULTS.md`。
