# Issue121 继续入口（2026-10-31 06:18 CST）

Refs #121 / PR #122；负责人YUZE-LU。五宏各一个基础实现及两份审阅建议的完整300MHz布局布线/全部端口引出目标保持。最终物理/功能证据和剩余执行入口见[790](CHECKPOINT-790.md)。

本轮核对预算总入口，发现RESOURCE-BUDGET.md仍以历史422表为开头，当前576数值/周期源的实际预算595已另行封存。现增加明确当前入口、当前2048上下文对照表，历史正文和旧JSON保持。791从当前f1c60148的43个规范Git字节输入重算，JSON规范化后与封存595完整对象精确一致；14个报告SHA、8模型/80个有限分析候选、各阶段周期和ms换算复核。原辅助核验首次因Python tuple与JSON list直接对象比较而断言，随后改为JSON规范化；再纠正核验器假定8M为实际1M，不改任何预算输入、计算器或数值，最终全部通过。见[verification-791](verification-791.json)。

该表仍只计已测矩阵/状态/卷积/统计子集，未覆盖阶段不记零，不宣称整模型10token/s或整数质量，不新增阵列实现。当前V物理/信号几何/最终三初态功能/严格LEC已PASS，完整未改GDS仍运行；六文件/完整已查看几何/768接口按真实前置，V总accepted=false。R404原任务继续，M/S/T保持。

06:14实际进程验证：767/94002 KLayout PID3551157和R404/93555 OpenROAD PID1987219 CPU各增长100ticks/秒，原任务保持。634/769控制器最近实际PID/同UID/命令行及固定配置SHA读回有效，不因耗时或静默重启EDA。下一步等767 DRC真实终态后collect788封存，再按790执行交付/全部端口。

本任务最多8allocation（含旧/PENDING/UNKNOWN，其他Issue不计）；c96以6×16独立队列即完即补，当前并发受真实前置限制，不复制EDA占位。原immutable归档不改写，新V接收额外绑定782全信号几何及8a347ce6强制门。

目标active；Issue121 OPEN/in_progress、PR122 OPEN/draft；登记management-hub PR5前次核验未合并pending；无board配置，看板unverified/同步pending，管理员/独立审查人待指定。
