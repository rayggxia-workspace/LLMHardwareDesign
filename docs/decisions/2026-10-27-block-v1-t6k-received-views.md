# T6K完整原生接收与同源宏视图入口

161/92264实际COMPLETED，49:10、TotalCPU3:36:58、MaxRSS72319928K，在node20分配32CPU，物理A/C与最终功能A/C四路各8CPU。不是宏冻结：后续flat/abstract边界、共同底座与十二层产品仍未验收。

两路18项完整物理门全部true，完整独立FreePDK45 deck零项（无排除/豁免），新最终全片原生DRC零项；全部49544时序端点setup/hold及严格cap/slew通过。A最小setup/hold为5.202862/0.005335ns，C为5.228821/0.016969ns；当前库没有有限fanout限值，报告明确has_limit=false，不宣称该类有限限值通过。PG、使用网驱动、RC覆盖、最终与映射LEC和固定M10 pin均通过。

最终真实网表使用实际映射存储cell，以all-ones、random-121、random-122三种初态分别执行242事务/264051cycles/3295817断言，A/C均通过；零延迟回归与STA分别记录，不宣称四态或延迟回装。源160网表、物理网表导出与三初态收据均有独立SHA。完整原始结果位于授权服务器run161，仓库保存group及四子终态索引。

新增native-escape-view-group，16CPU内两路各8CPU，仍使用保守的旧完整C8单路峰值180451804KiB加20%余量作为2/1并行内存门，不伪报尚未测量的view峰值。依赖161完整组与145安装版库pin/bus控制。native_views只为transaction6k接受native_pipeline_escape.json，既有完整物理门不变，并绑定同一160最终网表、161最终功能收据/三初态、实际driver与Lib/LEF接口控制；其他历史候选路径保持。

本提交时164尚未部署/运行；即使导出与读回成功，候选Lib/LEF也只具接口/来源资格，flat_abstract_boundary_qualified与qualified_hard_macro仍false。#127负责独立边界QA，主线负责正式来源与视图生产；先准备同源输入，实际接收按支线合同另行核验。支线小控制仅在统一8allocation总预算内安排，待独立固定命令就绪，不为等待预留闲置节点。

实际161总CPU/(wall×32)约13.8%，是四路混合负载观测，不是加速比。下一批继续节点内独立A/C并行，按实际阶段资源和内存安全调整；其他成员作业不操作，现有长作业不因耗时取消。
