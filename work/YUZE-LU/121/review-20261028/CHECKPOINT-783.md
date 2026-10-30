# Issue121 继续入口（2026-10-31 05:46 CST）

Refs #121 / PR #122，负责人YUZE-LU。完整范围及物理新门说明见[779](CHECKPOINT-779.md)；原生0及fresh RCX见[775](CHECKPOINT-775.md)。目标仍是两份审阅建议下M/V/R/S/T各一个基础实现的最终300MHz布局布线与全部接口，五份结果尚未齐。

776/94006已自然FAILED/1:0：实际OpenROAD返回0，完整几何已导出，562492非PG网络、1875509引脚电极，文件1691623293字节，SHA c64c6a62bb54c79933c809b52d59b713890abf56760a6307c2fc3fcbc834b0a1。之后名称覆盖断言失败，没有进入实际连通判断。`v-signal-776-failed-781/index.json`封存5份原始、1份实际服务器大文件SHA及361归档Git源；原失败receipt SHA2eb7f5cfe093e4752ef5a3f51bee12142b242beae76b3ec25a85bd97ae2bbfd3。

在767allocation内只读诊断，DEF/ODB两侧49359对名称差异来自过早去掉转义；完整原始诊断见coverage-780.json。并非已证明的物理缺线。新解析器与既有native_rect_completion一致，精确原生名称优先，只有不存在精确名称才允许一次DEF解码，并强制完整集合、一一映射与全部端口/形状连通。未放宽空间接触或删除任何网络。9个几何、4个名称确定性对照、100随机与朴素图对照、本地实际解析/进程池RECT桥正负对照通过。

新源915f505b305ea963368b4e86769ca3630d07206c，782归档SHA a97e95e218f54ad186c43915128356b98d0691cb8c2bb12ae270dca74eb5ad79，362成员。782/94010已通过唯一dispatcher提交；只读绑定776失败receipt、原实际OpenROAD命令return0、相同Tcl导出helper SHA、原几何实际SHA及同一767最终源。**不重跑EDA，不覆盖776，不把解析修复称为实际连通PASS。**

恢复先核实94010/94002和allocation实际进程，再读782/767 task receipt。782若有实际断开，保留所有失败component witnesses并修复当前唯一实现，不能降低规则。767物理PASS已777封存，完整未改GDS/最终功能、严格LEC/六文件/完整已查看几何继续；768按真实前置。原R404/93555保持，最近05:36原PID1987219实际CPU增长，GRT extra46。M/S/T保持。

V accepted=false。旧自动四门delivery不包含新增全宏信号几何证明；即使其native_leaf_accepted为true，也不能单独授予本轮总接收。必须绑定782或后续同源真实通过证明。全部原始ODB/DEF/几何均未修改。

本任务最多8allocation含旧/PENDING/UNKNOWN；其他Issue不计入。c96按6×16独立队列即完即补，当前真实依赖不复制EDA。原634/R与769/V控制器不重部署。登记management-hub PR5 pending；无board配置，看板unverified/同步pending、管理员待指定；PR122 OPEN/draft、Issue121 in_progress，独立审查人待指定。
