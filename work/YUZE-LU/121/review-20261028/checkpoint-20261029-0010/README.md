# 五宏修订：M流水保护、T实际物理和端口吞吐证据

Refs #121 / PR #122。观测 2026-10-28T16:07:00.833910+00:00（北京时间2026-10-29 00:07）；目录0010只是标识。88份实物文件大小/SHA全部本地复核通过；[index.json](index.json)为原样报告清单，不能由本摘要推定通过。

M245六阶段P&R完成；248最终三初态/严格LEC通过，但fresh-RCX物理失败654项setup，最差−0.167512670ns；hold最小+0.012434ns（精确值以timing-summary.tsv为准）。完整未修改GDS deck为0，但原生全片DRC有两处metal2 spacing：net15612，(716.5200,658.5250)–(716.5900,658.5600)及(716.5500,658.5250)–(716.5900,658.5600)。因此时序与原生DRC均失败，不接收、不豁免。

7a9d861修复M符号溢出检查门控整组累加写入路径，保持完整S64、24符号FF+有效位/粘滞位，末尾检查后才发布；旧/驻留命令均+1拍，op4仍49拍，驻留II1。250/92893实际6个独立16CPU任务起跑：三初态数值、综合、保护正负例和三份端口bench全部通过，随后依赖补位P&R。保护三初态各4次注入/1196检查/766周期，关闭检查器的实际负例返回1并因漏拒绝被发现。新M尚未物理验收。

T246原生六阶段完成，249封存新源并独立物理通过：全部端点、电气、RC、PG、连接、真实2µm M10接点均通过；最小setup/hold +0.429092/+0.007988ns。50fF/批准10/3ns约束不变。251/92890恢复249原队列及共享claim，已通过约束/benchmark不重跑；T完整DRC与最终网表功能继续，严格LEC依功能补位。S246全局布线、V236全局布线、R236进入ABC映射，均未完成新五宏交付。

## M实际完整端口周期

相同K1024×N8、S8/S8：预装、执行、S64部分和读回、S32系数合并和最终RNE读回均收费。300MHz速率仅按实测周期换算，旧基线仍仅100MHz物理资格；不能称系统或模型实测速度。四格式、四形状（K1024/N8、K65/N7、K9/N1、K3072/N8）及四供数场景共64项/variant、两初态一致。有效字节/容器字节/排空、互斥周期归因与可重叠资源占用分别保留。

| 实现 | 场景 | 总周期 | 按300MHz换算GMAC/s |
| --- | --- | ---: | ---: |
| baseline | resident_reuse | 817 | 3.008078 |
| baseline | continuous_supply | 3103 | 0.792008 |
| baseline | producer_gaps | 4520 | 0.543717 |
| baseline | downstream_backpressure | 3554 | 0.691503 |
| legacy | resident_reuse | 842 | 2.918765 |
| legacy | continuous_supply | 1984 | 1.238710 |
| legacy | producer_gaps | 2759 | 0.890758 |
| legacy | downstream_backpressure | 2305 | 1.066204 |
| packed | resident_reuse | 373 | 6.588740 |
| packed | continuous_supply | 806 | 3.049132 |
| packed | producer_gaps | 1347 | 1.824499 |
| packed | downstream_backpressure | 953 | 2.578804 |

legacy修订驻留复用842拍，旧基线817拍；49拍数值处理及新保护有成本，不能只展示有利场景。packed连续供数806拍，旧3103拍，改善来自有限银行/紧凑装载/重叠执行，不是改变MAC数。

## S/T事务测量

252 revised S及baseline/revised T均通过两初态。384字连续完整往返：S revised770周期（写385/读385）；T baseline1155（写384/读768/控制3），T revised772（写384/读385含首拍同步读/控制3）。这不是双份6KiB并发。4批、17字与1字、生产气泡及下游背压也测量。S旧基线因漏带store82依赖首次编译失败，已固定同ad3源依赖SHA，253仅补该失败测量，不重跑通过项。完整T资格仍等待四门。

253/92899还编排T四门后最终文件/实际pin/版图接收，再导出完整wire/via/PG/pin/OBS、DEF RECT补全及源ODB不变核验；目前只是待执行的有依赖队列，不是已交付。

后续：所有五块新最终P&R/同源四门、完整实际接口引出和有限预连风险、V/R吞吐及全局统计实际S流量、8模型资源预算仍未完成。每种只保留一个基础实现，不增加裕量版/阵列/产品。c96默认6×16即完即补，本任务max8含pending/unknown，当前就绪任务受真实依赖约束；未取消慢EDA、未碰其他成员。

检查：check_project.py、Python编译和git diff --check通过；新版交付/几何尚未实际运行，只有显式零enclosure demo契约和旧默认拒绝的本地控制通过。登记pending（management-hub PR5），看板unverified/同步pending（无board配置/Projects条目能力），管理员与审查待指定；Issue in_progress、PR draft、目标active。
