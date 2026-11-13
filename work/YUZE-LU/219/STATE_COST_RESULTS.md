# 状态相关成本 v2：实现、同模型复验与效果

2026-11-08 CST，Issue #219 / PR #220，YUZE-LU。基线远端 f23a6d9，本地隔离实现基于同算法源码 ec6fc7734。

## 实现

贪心和DP每次前沿扩展均调用纯函数 evaluate_transition；编译阶段仍生成执行模板。
实际LOAD量由当前有效前缀计算，允许部分命中；显式选择preserve/shrink/discard。
使用短前缀可继续保留已有长前缀，容量按真实峰值计；只读丢弃不写回。
实际时长、读写量、复用/补齐/保留前缀、S占用和完成时间增量写入evaluation。
独立检查器不调用生产求值器；有限S回放实际拼接旧分量与新加载部分。
原生算术、本地访问、B/零包、STORE/ACK保持。算法说明见
[STATE_COST_V2.md](../../../project/experiments/block_synthesis/STATE_COST_V2.md)。

## 相同测试

实际Qwen2.5-3B，3,085,938,688参数；完整embedding、36层和LM head；B1/S2 prefill、无KV。
仍为每S16KiB、数据预连0、原生叶命令测量与#182虚拟外存模型；相同模型、权重、校准、HF logits与整数IR，原2%门槛不变。

| 配置 | f23a6d9模型完成时间 | v2模型完成时间 | 变化 |
| --- | ---: | ---: | --- |
| 五组DP | 3,096,020,974,074 | 3,096,020,974,074 | 不变 |
| 九组DP | 2,286,834,164,826 | 2,286,835,922,522 | 增1,757,696，约0.00007686% |
| 九组且最多10束 | 3,096,020,974,074 | 3,096,020,974,074 | 不变 |

两配置搬运量分别仍为94,189,914,879和94,189,987,887个128位字，线束仍10/18，S峰值16,368B。
五组/九组各三个输入[[1,2]]、[[3,4]]、[[42,43]]均逐位等于原整数程序；HF L2分别
0.5265177%、0.7250722%、0.5591736%，所有位置argmax相同。

**本轮证明成本/状态机制更完整，没有取得完整3B性能提升。** 两个所选整网计划的325个Dot均选择preserve，未出现部分前缀命中；部分命中能力由独立小例、逐记录计数及有限S数值回放验证。新增动作扩大了有界搜索空间，九组结果略退化，不能宣称最优或隐藏此结果。
历史五组/九组编译用时22.99/98.39秒，本轮48.89/207.55秒；是不同作业的端到端观测，约翻倍，未做受控运行时基准。后续优化应在相同候选和求值语义下减少开销，不以改变语义抹去成本。

## 验证与回收

Slurm100563计划、100569五组数值、100570九组数值、100571最终审计，全部COMPLETED 0:0，c64、4CPU、yzl-*、UNLIMITED。
本地及最终服务器105项测试全部通过，包括原100项、80组新增部分前缀逐记录访问、纯函数不变性、容量/身份拒绝、三种保留策略实际数值回放和伪造evaluation拒绝。
100563/100569使用104项测试快照；之后仅补一个测试，100570/100571绑定最终105项源码。全部生产源码一致，源比对逐项记录。

25份原始输出已回收并逐文件SHA-256对照服务器；完整IR、计划和数值原件保留原服务器新attempt。
[回执及原件SHA](results/state-cost-v2/receipt.json)、[六次数值摘要](results/state-cost-v2/five-numeric-summary.json)、[九组数值摘要](results/state-cost-v2/nine-numeric-summary.json)、[105项测试](results/state-cost-v2/tests.log)、[完整计划独立审计](results/state-cost-v2/whole-plan-audit.json)、[源与实际动作](results/state-cost-v2/source-and-action-checks.json)、[对比数据](results/state-cost-v2/comparison.json)、[Slurm终态](results/state-cost-v2/slurm.psv)。数值摘要移除了大体积逐Dot事件；完整原件位置和SHA见回执，不把摘要SHA冒充原件SHA。

复跑：launch_fix.py冻结到新的algorithm-fix-*目录；state-cost-plan.sbatch参数与reuse-plan.sbatch相同，另用原reuse-replay.sbatch、reuse-audit.sbatch。所有绝对路径及输入哈希随回执保留。
图册由原程序生成但本轮未目视验收。初次本地源比对因Windows默认GBK解码UTF-8失败，显式指定UTF-8后通过，未削弱检查。

范围为综合和整数/有限S模拟；不增加系统RTL、DMA、MC/LC或物理资格。登记management-hub PR5 pending、Projects缺配置/权限仍unverified与同步pending；待有权限维护者处理。成果待独立审查，不自批准、合并或关闭任务。
