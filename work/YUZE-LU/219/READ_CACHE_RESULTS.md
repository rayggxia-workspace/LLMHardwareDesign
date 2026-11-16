# 完整3B：有限S复用进入前沿搜索

2026-11-08，Asia/Shanghai。[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)、[PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)，负责人YUZE-LU。

本轮补充综合：真实Dot的只读分片、实例绑定、执行安排及跨任务相同SSA输入保留。DP状态增加每个M.S中的输入身份、索引范围和长度；独立检查器重建驻留区间、地址、容量和冷/热搬运。保留原有算术、准备命令、STORE及ACK，减少重复LOAD；不增加M累加上下文。实现及公式见[DOT_CACHE.md](../../../project/experiments/block_synthesis/DOT_CACHE.md)。作者输入仍是模型产物、硬件清单、调用参数；其余IR、校准和证据是生成物，无须新增手工JSON。

实际Qwen2.5-3B，3,085,938,688参数；完整embedding、36层、LM head，B1/S2 prefill、无KV。8850条已验收整数指令、1083个内核、325个Dot；每S16KiB、数据预连0、#182有限信用/队列虚拟外存，原生命令时间沿用三初态测量，不新增浮点服务或任意时延。

| 配置 | 原全部写回基线 | 有复用贪心 | 有复用DP | 逻辑束：贪心→DP |
| --- | ---: | ---: | ---: | ---: |
| 五类各一组 | 3,737,404,896,734 | 3,096,020,974,074 | 3,096,020,974,074 | 10→10 |
| 九组数量实验 | 3,737,404,896,734 | 3,096,020,974,074 | 2,286,834,164,826 | 10→18 |
| 九组且最多10束 | 3,737,404,896,734 | 3,096,020,974,074 | 3,096,020,974,074 | 10→10 |

时间为原生命令加虚拟外存的模型代价，不是芯片实测周期。贪心与DP共享同一候选池，宽度1/8、就绪上限4；不保证全局最优。复用贪心较原基线下降17.1612%；五组外存搬运126,259,111,012→94,189,914,879个128位字，减少25.3995%。九组DP搬运94,189,987,887字，跨任务命中36次；五组108次。九组DP较同候选贪心下降26.1363%，伴随10→18束；**同为10束仍无DP额外收益**。不能把复用或多连接并行收益都归给搜索。

S峰值从8字/128B提高到1023字/16,368B。实际K投影保留每行169个K位置，共1014个分量记录，不要求2048长输入整行进入S。完整清单互斥对为0，不代表真实物理无冲突；搜索/检查器仍执行全产品静态连接并集与incompatible_nets约束，错峰不能豁免。

五组和九组各三输入 `[[1,2]]`、`[[3,4]]`、`[[42,43]]`，六次完整缓存回放均与原整数程序逐位一致。相对HF L2保持0.5265%/0.7251%/0.5592%，所有位置argmax一致，原2%门槛不变。`dot_cache_replay.py`实际写入并使用有限S分量数组，检查陈旧值和容量；整张量模拟数组代表外存。这是编译器数值/存储模拟，未声称RTL或DMA协议仿真。

最终100项测试通过，包含原150个互斥小DAG、80个缓存/静态互斥穷举对照、80组逐条记录访问、错误缓存命中/地址/容量拒绝。即使容量总量装得下，活跃scratch覆盖驻留S地址也被独立拒绝。当前生成后端其他任务只使用前8字。独立成本检查重推原生工作、冷/热流量与时间，独立调度检查重建资源、驻留和静态网。

Ready集合按完成掩码缓存，检查器预索引Dot，减少重复整图扫描。优化前后两组IR及全部计划结构化比较完全相同；部分原始JSON SHA仅因对象键顺序变化，保留原始字节和各自SHA，未重排回执冒充原文件。

可查看：

- [复用、输入/输出及S地址图册](results/read-cache-v1/plan/generated/reuse.html)、[完整输入DAG/硬件/执行图](results/read-cache-v1/plan/generated/report.html)。浏览器安全策略拒绝本地file URL，本轮未目视验收；内嵌脚本和数据另做静态检查。
- [完整摘要](results/read-cache-v1/plan/generated/summary.json)、[当前独立检查器重验](results/read-cache-v1/tests/whole-plan-audit.json)、[100项测试](results/read-cache-v1/tests/tests.log)。
- [五组数值](results/read-cache-v1/five-numeric/generated/report.json)、[九组数值](results/read-cache-v1/nine-numeric/generated/report.json)。
- [Slurm终态](results/read-cache-v1/slurm.psv)、[输入/源码/输出SHA及服务器路径](results/read-cache-v1/receipt.json)、[回收核验](results/read-cache-v1/local-verification.json)、[语义等价](results/read-cache-v1/equivalence/equivalence.json)。

最终100357计划、100353五组数值、100359九组数值、100360全部测试/重验、100361等价，均c64、4CPU、yzl-*、UNLIMITED、COMPLETED0:0。回收39份文件SHA通过、466份源码快照登记，大IR和tar留授权服务器。100350负向测试把零长度字段改成已有零而失败，已改为真正修改非零候选，失败日志保留且未削弱检查。首次采集因要求JSON字节相同失败；后用Slurm独立语义比较并保留原字节。

复现：经本任务launch_fix.py冻结，向新attempt提交下列脚本；绝对路径和SHA见回执。

```text
reuse-plan.sbatch ROOT MODEL HARDWARE NUMERIC_TRACE QUALIFICATION PROGRAM
reuse-replay.sbatch ROOT IR PLAN WEIGHTS CALIBRATION HF_LOGITS NATIVE_HEADERS
reuse-audit.sbatch ROOT PLAN_DIRECTORY
reuse-compare.sbatch ROOT BEFORE AFTER
```

边界：本版仅有只读Dot分量、B/零包复用，不搜索任意跨层脏结果、算子链片上融合、重算或搬运/计算重叠；其他中间结果仍写外存。外存预留50,514,910,656B未压缩，实际容量资格未给出。完整MC/LC编码、实际DMA、九实例RTL及物理属于后续阶段，不是当前综合验收前提。其他bench没有新增完整整网资格。硬件清单变动可重跑；不支持的算子仍显式拒绝。

借鉴[Timeloop（ISPASS2019）](https://people.csail.mit.edu/anurag_m/papers/2019.timeloop.ispass.pdf)循环/数据复用表达，未移植其搜索器、代价或最优性。一般跨层缓存可进一步参考Stream，本版尚未实现。

回执：rayggxia-project-collab1.0.0，project_id=llm-hardware-design；PR220待独立审查，不自合并/关闭。登记pending（management-hub PR5）；缺board配置且Projects读取权限不足，看板unverified/同步pending，待有权限维护者处理。后续入口为本说明、DOT_CACHE.md及当前PR远端HEAD。
