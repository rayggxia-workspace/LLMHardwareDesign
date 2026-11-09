# Issue247 容量/端口两路线证据

负责人Melodydt；2026-11-09 Asia/Shanghai；[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)/[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。[正式报告](../../../../docs/experiments/issue-247-capacity-port-compare.md)与[恢复入口](../../../../docs/handoffs/2026-11-09-issue-247-capacity-port-compare.md)。

run04源c597a7d0f7e5ee03100cea5d4ac65dd22cb93a11，作业101665/mdt-sram-rw，c64/node1/4核，8:02 COMPLETED0:0；57完整trace、6尾块、4非法CLI，先20历史完整回归通过。149回收输出SHA、22轻量证据、44功能源一致性通过。[索引](index.json)/[摘要](summary.json)。

run05源49b3938ce8b55734520c56a79a7d5d7933af9cdc，作业101672/mdt-sram-policy，c64/node1/4核，3:58 COMPLETED0:0；30完整trace、先12默认完整回放、2非法CLI、纯调度不变量及每case6负例通过。81回收输出SHA、23轻量证据、49功能源一致性通过。[索引](policy/index.json)/[摘要](policy/summary.json)。

两轮87完整trace＋6小trace＋6非法CLI，含重复基线/控制回放；共230回收SHA。完整结果SHA分别966729e962ecde76f755a9da873f3fb7ac566e4dd454f45e7d4b6f8f76c73cce和4dcb0f01357e2f71fcf9f90deeab1d1dd50101b3d928b3e9866473c91c133777。大原始结果、输入、生成源/二进制在本人服务器/public/home/yuzelu/Melodydt/issue247-area-speed/run04与run05及外层本地回收目录；仓库仅轻量摘要/选定原始case/日志/版本与SHA。

本地执行python -B work/Melodydt/247/compare/verify.py及python -B work/Melodydt/247/compare/policy/verify.py，只核验源与回执，不重跑仿真。源码入口project/experiments/sram_port_compare；旧246/247功能文件保持。所有结果是条件模型，未实装SRAM扩容、未改生产RTL，真实宏/面积/频率/生成未验收。

无活动作业、无自动监测。规则rayggxia-project-collab1.0.0；待独立审查/合并，不done；登记pending，看板unverified/同步pending，CI以最终PR真实回执为准。
