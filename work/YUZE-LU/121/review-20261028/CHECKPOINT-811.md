# Issue121 继续入口（2026-10-31 07:47 CST）

2026-10-31 08:33 CST：805严格LEC实际UNSAT/IDENTICAL，diff0/1输入输出全0；815封存16原始/8实际服务器大文件SHA、364归档Git源及receipt输入/稳定输出，绑定814三初态最终功能与812物理/fresh全信号几何的同一9ef42c0f…源。actual receipt时间证明formal在function结束1.972308秒后补位，未等完整GDS。当前仅完整未改GDS仍运行（817实际进程/队列）；六文件/完整实际查看/806全端口与有限RC仍待真实前置，V accepted=false。原767失败/资格保留为历史。M/S/T保持，R原404继续，五宏最终未齐。

815 collector已自然完成并验证16原始本地SHA/大小，814也已完成；不要重跑已有目录。接下来只在完整GDS真实终态后执行collect813.py（失败也保留），再按真实前置完成六文件/完整原生几何实际查看/806全部接口。当前首选源804/805/806已修正到BEFORE-AFTER-SOURCES.current_selection.V，原767完整对象在historical_v_selection_767。

2026-10-31 08:25 CST：805/94063最终网表三初态功能全部PASS，all-ones/random121/random122各574942检查/425971拍；814封存27原始/8实际服务器大文件SHA、364归档Git源及receipt输入/稳定输出，绑定与812物理/fresh完整信号几何相同的9ef42c0f…最终源。严格LEC已自动补位并与完整未改GDS并行（816实际队列/进程快照）；尚未宣称LEC或完整GDS通过。804/809与812保持，六文件/完整查看及806全端口/有限RC待真实前置，V accepted=false。R原404继续（08:20 CPU实测+100ticks），M/S/T保持，五宏最终未齐。

814 collector已完成，27原始本地SHA/大小核验；不要对已有目录重跑。下一步只在真实终态后执行collect815.py（严格LEC）及collect813.py（完整GDS；失败也保留），之后交付/完整实际查看/806接口。wait805.py每次最多50秒观察已确认RUNNING的94063，若allocation终态则先读回sacct与receipt，不因观察失败重启EDA。

2026-10-31 07:53 CST：805/94063新最终源的物理检查与fresh完整信号几何均PASS；812封存38原始/9实际服务器大文件SHA、364源Git及receipt输入/稳定输出，绑定实际最终源receipt 9ef42c0f…。全部562492非PG网/22107288形状/1875509端子/400 DEF RECT连通、失败与缺失0；27066实际timed endpoints的setup/hold最小+0.012849/+0.029884ns，电容/slew违规0、PG/RC覆盖通过。完整未改GDS与三初态功能继续，严格LEC按功能前置补位；六文件/完整查看/806接口仍待，V accepted=false。804自然完成与809证据保持；R原404继续，M/S/T保持，五宏未齐。

812 collector已自然完成。38原始文件本地SHA/大小已核验，下一次核对其提交Git字节。采集入口collect812.py不可对已有目录盲目重跑；read805.py只读实际终态，sample805.py只在94063有效时取进程证据。

Refs #121 / PR122；负责人YUZE-LU。

2026-10-31 07:47 CST：804/94056自然COMPLETED/0:0，所选801case1的fresh RCX/finalreport、完整DEF几何精确不变及最终native0复查全部PASS。809封存41原始/10实际服务器大文件SHA、43实际receipt输出、364归档Git源及receipt输入核验。绑定原801case1 receipt，原767失败/旧资格不转移。807已按真实前置自动提交805/94063，实际进程正创建新最终源，之后并行物理/完整未改GDS/三初态功能/完整信号几何，formal与交付/完整查看按前置；806仍等待。当前V总accepted=false，R原404继续，M/S/T保持，五宏最终未齐。

原修复定位/单RECT选择及实际归档/队列/控制器见[807](CHECKPOINT-807.md)与[808](verification-808.json)，当前源入口修正见[810](CHECKPOINT-810.md)。809 collector已完成，不再盲目重跑，其实际源与全部43稳定输出已经核验，局部raw41本地SHA/大小精确匹配。完整GDS尚未对805出结果，不能用原767结果或native0代替。

停止使用sample804.py观察已自然结束94056；改用sample805.py（805/94063）实际PID/CPU/亲和性。R仍用sample661.py，不因静默或耗时取消。807只监视804/805/806；634/769保持不变。805新完整信号几何为交付强制前置，旧782只属于767。

下一步：核对805实际final-source receipt→物理、完整GDS、三初态功能、完整信号几何分别采集→严格LEC→六文件/完整原生几何实际查看→806全部端口/有限RC。每类一个基础实现，不制造裕量版本/复制占位任务。最多8allocation含旧/PENDING/UNKNOWN，本Issue限制不是账号总限制；c96按6×16即完即补，805初始多个子门依赖最终源完成。

PR122draft、Issue121in_progress；登记PR5 pending，board未配置unverified/同步pending，管理员/独立审查人待指定。目标active、最终五宏未齐。
