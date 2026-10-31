# V316 placement只读诊断：暂存回执

Issue #121 / PR #122。源db4905bd3534e4f89e82469980fa12efd3092727，archive38af4ca2c3bc7d56ee2537c2e597ae56dfac0371e6811a3c694bddd7e68247bb，与316同源。归档303个Git blobs逐一核验，内部selector真实选中316；不修改已提交归档、queue或原数据库。

320仅做`revision300-checkpoint-timing-v`。执行前必须看到316完整`do-place`阶段记录，随后读取3_5_place_dp.odb/3_place.sdc、原网表、配置、库/setRC，核对前后SHA，输出真实最坏路径；使用placement估计RC和理想时钟，不授予最终STA或原生/上层验收资格。它用于检查315新增操作数和逐元素分级后的路径，不是重做一套P&R。

`index.json`实际捕获UTC00:13:12.328524：316只完成综合/floorplan，320 dispatch.tasks为空，无allocation。后继控制按真实stage检查及本任务8 allocation上限提交；不能把此暂存回执当成诊断已执行或时序通过。复用既有函数数学证明和M/S/T通过项，不以填槽为由重跑。
