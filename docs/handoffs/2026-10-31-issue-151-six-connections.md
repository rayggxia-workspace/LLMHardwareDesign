# Issue151六类连接方案研究交接

- 时间：2026-10-31T16:22:44+08:00（Asia/Shanghai）；负责人Melodydt。
- 仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign；Issue：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；任务分支：`task/151-six-connection-study`；基线commit：`a103da352b7e431cedc69f54b9f71c05371be1b3`。研究成果commit和PR链接以Issue151线上回执为准，不把基线当成果提交。
- 本地工作目录：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/`，delivery为独立API提交包，非Git checkout；根目录仍为管理参考副本。没有本地Git HEAD、暂存区或与远端同步的完整工作树；准备文件清单见本任务README与verification.json。
- 正式成果：docs/SIX_CONNECTION_SCHEMES_STUDY.md、SIX_CONNECTION_BRIDGE_AUDIT.md、SIX_CONNECTION_COORDINATION_CANDIDATE.md；辅助索引/核验在work/Melodydt/151。
- 已完成：研究六项、逐项归属及旧bridge源码核对；仅选定相关文本来源的Git blob与SHA-256检查。未改叶宏RTL/物理副本；未运行服务器、模型或EDA；ref-project未纳入维护。
- 实际检查：管理结构及本任务verify_study.py的结果见verification.json；未执行RTL/SystemC、综合/P&R、共同CTS/PG或动态SI。
- 未完成：独立设计审查；系数/宽归并服务边界决策；候选wrapper的RTL、硬化及六项整链验证。处理人Melodydt，独立审查人与所需项目管理员待指定。
- 登记：management-hub PR5读回open/unmerged，pending。看板：main配置仅labels/status-mapping，无board.json；当前工具无Projects条目读写能力，unverified/同步pending，管理员待指定。恢复后先核验候选组织看板1的受众、字段和本Issue条目，复用/加卡并读回。
- 恢复第一步：用Melodydt连接读回Issue151、PR与任务分支最新head，确认来源版本和其他会话文件占用；从本任务包核验实际改动清单，再决定后续实现范围。不要把其他成员#121/#130/#143的工作树、作业或旧资格接管过来。
- 状态区分：本地研究包、远端任务分支、待审查PR、已合并main和服务器真实状态分别核验；本任务没有服务器作业或新仿真结果。
