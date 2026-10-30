# Issue121 继续入口（2026-10-31 06:04 CST）

Refs #121 / PR #122；负责人YUZE-LU。完整范围见[执行计划](../../../../docs/plans/block-v1-review-300mhz.md)；原生0/fresh RCX见[775](CHECKPOINT-775.md)，全宏信号几何与新接收门见[785](CHECKPOINT-785.md)。五宏各一个实现，目标与门不收窄。

本轮新增767最终网表all-ones/random121/random122三初态功能PASS，`v-767-final-function-786/index.json`封存27原始/8实际服务器大文件SHA、358归档Git blob及receipt输入/稳定输出。每种574942检查/425971拍，RTL数值/事务独立参考；不是仅RTL测试，也不是复用630资格。源receipt f06b8e147dfb8bde4e5cdd662bfbbad97b873e661b3b47c9667a6386a6d06005，与777物理/784全信号几何完全相同。

767/94002的严格LEC已自动补位，与完整未改GDS DRC并行；最近06:01实际Yosys/KLayout CPU增长。三初态测试结束后释放的16CPU槽已由formal占用，不等整批最慢任务。原R404/93555最近05:56原PID1987219实际CPU增长，GRT extra46。原634/R、769/V控制器保持，所有EDA正常收尾，不因耗时或静默重启。

当前V1260²µm、277信号位，fresh物理777 setup+.012848834/hold+.029884208ns；只代表该子门通过。**完整GDS/严格LEC、六文件/完整已查看几何、768全部接口与有限RC尚待完成，V总accepted=false，R最终未齐。** 旧自动四门delivery归档不包含新增全宏信号证明；总接收必须绑定782实际证明及8a347ce6新接收门。

`delivery-300mhz/README.md`已补清楚当前交付入口，原旧快照保留为历史；BEFORE-AFTER当前V行已从“信号几何待补”更新为真实通过，未把现有子门写成五宏最终完成。M/S/T保持。

恢复第一步：先核实94002的sacct、实际进程和各task receipt。`.local/issue121/collect787.py`已准备，仅在formal终态PASS后封存严格LEC并绑定786；`.local/issue121/collect788.py`仅在DRC终态后封存实际native/完整未改GDS门，无论成败均保留。若新最终门失败，保留原task/源，再修当前唯一实现，不修改原失败或放宽检查。782已终态封存，不重新采样或重跑。

服务器base `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121`。c96按6×16独立任务、即完即补；本任务最多8allocation含旧/PENDING/UNKNOWN，其他Issue不计入。真实前置不足不复制EDA占位。

PR122 OPEN/draft、Issue121 in_progress、目标active；登记management-hub PR5 pending，看板无配置unverified/同步pending、管理员待指定；独立审查人待指定。完整技术交付之前不转done。
