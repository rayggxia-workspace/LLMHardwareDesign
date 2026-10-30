# Issue121 继续入口（2026-10-31 07:06 CST）

Refs #121 / PR #122；负责人YUZE-LU。两份审阅建议及五宏一个基础实现/完整300MHz最终布局布线目标保持。此前同源物理/功能/信号几何/严格LEC见[790](CHECKPOINT-790.md)，当前有限预算入口见[792](CHECKPOINT-792.md)。

2026-10-31 07:06 CST：767/94002完整DRC自然FAILED：原生全片0项，完整未改FreePDK45 GDS deck129类/1项METAL2.5，约(498,73)µm。788封存23原始/10实际服务器大文件SHA、358归档Git源及receipt输入/稳定输出，精确同源f06b8e14…；物理777/信号几何784/最终功能786/严格LEC787通过仍保留，但不抵消完整GDS失败。delivery/geometry已按真实前置BLOCKED，768未提交；当前V accepted=false。新增两项只读定位：实际GDS窗口/规则与全层全网ODB/PG/pin/OBS/DEF RECT，尚待调度实测，不重跑整套P&R。R404原进程继续、GRT extra47，M/S/T保持，五宏最终未齐。

完整GDS report SHA977d7c4a0918b024b4f1fa9bef2f7699d9a56e76e6fdd8678d69f5d4b0240014，最终GDS SHA6cace632632e570b799addd4fdf9ba83458cc957edf00bf7a307a8a9fde2eb06。实际边对：(497.91,72.87;498.1466,72.87)/(498.09,72.94;497.8534,72.94)。不得把native0或既有功能/LEC当作完整通过。

只读定位helper revision300_v_gds_localize.py显式绑定767失败receipt、同一最终源、unmodified deck SHA和唯一METAL2.5项；ODB侧输出完整6×6µm邻域及全部DEF RECT补集，GDS侧输出实际metal2映射、原规则和窗口原生多边形。拟793队列只运行这两个真实共享前置，各16CPU，32GiB预估；其余候选需定位后才有依据，不用复制任务补并发。不会改写767归档/失败数据库或取消R。

注意：94002已自然结束，停止使用sample767only.py对已过期allocation观察。R用sample661.py仍可核验实际PID1987219。634/769控制器保留，767 needs_attention，768真实前置未满足；不直接重启failed队列。下一步：完成793只读定位、按真实几何/规则形成局部候选，再验证全片native与完整未改GDS、fresh RCX/STA、信号几何、最终功能/LEC及六文件/全部接口同源。

目标active、PR122 draft、Issue121 in_progress。登记management-hub PR5待合并pending，无board配置看板unverified/同步pending，管理员/独立审查人待指定。本Issue最多8allocation含旧/PENDING/UNKNOWN，其他Issue不计；c96按6×16独立队列即完即补，当前只有两个定位前置就绪。
