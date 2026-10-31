# Issue151六类连接方案研究交接

- 时间：2026-10-31T16:22:44+08:00（Asia/Shanghai）；负责人Melodydt。
- 仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign；Issue：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151；任务分支：`task/151-six-connection-study`；基线commit：`a103da352b7e431cedc69f54b9f71c05371be1b3`。研究成果commit和PR链接以Issue151线上回执为准，不把基线当成果提交。
- 本地工作目录：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/`，delivery为独立API提交包，非Git checkout；根目录仍为管理参考副本。没有本地Git HEAD、暂存区或与远端同步的完整工作树；准备文件清单见本任务README与verification.json。
- 正式成果：[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，首份研究commit为796d413458fd267200ab9dbff6d8e1b0b6468cdd；当前head以PR读回为准。文件为docs/SIX_CONNECTION_SCHEMES_STUDY.md、SIX_CONNECTION_BRIDGE_AUDIT.md、SIX_CONNECTION_COORDINATION_CANDIDATE.md；辅助索引/核验在work/Melodydt/151。PR未合并，待独立审查。
- 已完成：研究六项、逐项归属及旧bridge源码核对；仅选定相关文本来源的Git blob与SHA-256检查。未改叶宏RTL/物理副本；未运行服务器、模型或EDA；ref-project未纳入维护。
- 实际检查：管理结构及本任务verify_study.py的结果见verification.json；未执行RTL/SystemC、综合/P&R、共同CTS/PG或动态SI。
- 未完成：独立设计审查；系数/宽归并服务边界决策；候选wrapper的RTL、硬化及六项整链验证。处理人Melodydt，独立审查人与所需项目管理员待指定。
- 登记：management-hub PR5读回open/unmerged，pending。看板：main配置仅labels/status-mapping，无board.json；当前工具无Projects条目读写能力，unverified/同步pending，管理员待指定。恢复后先核验候选组织看板1的受众、字段和本Issue条目，复用/加卡并读回。
- 恢复第一步：用Melodydt连接读回Issue151、PR与任务分支最新head，确认来源版本和其他会话文件占用；从本任务包核验实际改动清单，再决定后续实现范围。不要把其他成员#121/#130/#143的工作树、作业或旧资格接管过来。
- 状态区分：本地研究包、远端任务分支、待审查PR、已合并main和服务器真实状态分别核验；本任务没有服务器作业或新仿真结果。


## 第二阶段固定产品总方案接续

- 更新时间：2026-10-31T18:31:13+08:00（Asia/Shanghai）；仍为Issue151 / PR152 / task/151-six-connection-study，负责人Melodydt。
- 起始研究head：49a34e75657025244fd33af56111029868008db8；新增成果head以PR152最终回执为准。第二阶段基于该head增量保留第一阶段和main全部树，不与其他任务分支混合。
- 独立资料包：D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/system-delivery；草稿overall-drafts、新来源system-sources仅本地；无本地Git HEAD/暂存区/服务器作业。准备包不是完整clone，不能将缺少的文件视为远端删除。
- 正式成果：三份SYSTEM_DESIGN/CONTROL_SPEC/TEMPLATE_SPEC、proposed决策、system-design-contract.json、静态校验器/来源索引/实际回执；原研究文档新增入口，个人进度和架构运行命令按范围补记。
- 关键限制：八个完整模型程序尚未编译；ROM容量、NUM_COEFF、状态版本/历史和发布恢复、外存/局部硬化尚待接收；R仍未合格。静态依赖DAG/类型/容量正负例不是硬件仿真或无死锁证明。
- 验证：python scripts/check_project.py；verify_study.py带sources；verify_system_design.py带system-sources/原sources；实际结果和SHA见system-verification.json。RTL/SystemC/综合/P&R/整模型质量未执行。
- 协作限制：已读管理中心portfolio候选看板1（配置验证时间仍为2026-10-15，不能当当前生效证明）；当前GitHub连接没有Projects条目能力。先前浏览器访问虽能显示字段，但身份/条目读取操作连续超时，未完成实际同步。无board.json，条目unverified、同步pending，处理人待指定；未改权限/登录身份或另建看板。
- 恢复第一步：用Melodydt读回Issue151及PR152最新head/评论/CI，检查本包清单与最新源版本，然后审查proposed决策和多R tile版本服务；先处理所需设计范围，再创建明确RTL/实验子任务。不接管他人#143作业。
