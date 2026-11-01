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


## PR144实现整合接续

- 时间：2026-10-31T19:47:17+08:00（Asia/Shanghai）；Issue151/PR152、负责人Melodydt；目标分支仍task/151-six-connection-study。
- 来源固定643c6012a11cbf461146ac40fbf61485223fe946，合前研究46b29c7664fefedf2de767ddcfb94a766cf341fb，共同祖先6a681d6632e7f7be537ff96eae1827df834bcfe8；最终merge commit/当前head见PR回执。
- PR152基线改task/143-seven-block-v2以隔离依赖差异；main、PR144分支和他人作业不修改。源后续提交须另行同步。
- 本地D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/merge-pr144-643c6012/integrated为独立API检查资料包，包含所需源码/管理文件而非完整clone；父目录保存base/ours/theirs、三方计划、冲突记录及新源payload，不上传临时草稿。
- 实现入口docs/SEVEN_BLOCK_RESEARCH_BASELINE.md；核心RTL不修改。旧验证保留历史身份，本轮静态源/合并结果见integration-verification.json。R未合格，PR133/146未自动引入。没有新服务器、RTL仿真或EDA。
- 恢复先读Issue151/PR152最新head与base，核两个父提交、src project tree和本轮回执；再从最小wrapper设计继续。主干合并、独立审查、登记和看板仍分别pending；处理人/审查人未定处保持待指定。

## 2026-10-31T20:30:44+08:00：RTL推导重写接续

- 仓库rayggxia-workspace/LLMHardwareDesign；Issue151/PR152；负责人Melodydt。分支task/151-six-connection-study，PR base task/143-seven-block-v2；输入commit faabeda68b3b098ba562d68517319e02725f5bc3（来源643c6012）。本轮输出commit/远端head见PR线上回执；未合main，不修改PR144分支。
- 工作目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/rtl-redesign-faabeda/integrated，为部分API检查包，非完整checkout；无Git HEAD/暂存区，本地候选改动为本轮白名单文档/合同/静态检查与自身进度，草稿留overall-drafts/rtl-replan不上传。旧包/根副本保持。
- 入口docs/SIX_CONNECTION_SYSTEM_DESIGN.md v0.2，原生审计docs/RTL_NATIVE_CONNECTION_AUDIT.md及rtl-contracts三附录；14份RTL字节保持原基线，7签名和命令示例在rtl-derived-contract.json。
- 实际检查/日志：rtl-redesign-checks.json与rtl-redesign-verification.json、system-verification.json、integration-verification.json；管理和静态源码/合同检查，不代表硬件或精度。RTL/SystemC/整数oracle/EDA/完整产品程序未执行，没有服务器作业。
- 未完成：独立评审/PR合并（审查人待指定）、最小组合wrapper、NUM/外存/状态版本实现、R资格与全模型编译/数值/物理验收。处理人Melodydt负责接续研究，实际实施任务/审查人待确定，不接管其他成员作业。
- 看板：本仓库无board.json，status-mapping存在；当前连接无Projects条目工具，组织候选看板1的条目/字段本轮仍无法读回，状态unverified、同步pending，管理员待指定。不能认定Melodydt权限不足或已同步；已有portfolio来源和浏览器超时记录保留。登记沿用management-hub PR5 pending，不跨仓库重复登记。
- 恢复第一步：用Melodydt连接读回Issue151、PR152最新head/base/评论/CI，比较本轮白名单与其他会话占用，再从v0.2及原生审计讨论实现子任务。先确认GDN/SSM全组和两遍、M单结果、T批界、ROM预编译及外存能力，不能从框图推断已存在硬件。

## 2026-10-31T21:15:42+08:00：全合法连接目标接续

- 仓库rayggxia-workspace/LLMHardwareDesign，Issue151/PR152，Melodydt；task/151-six-connection-study，PR base task/143-seven-block-v2；输入commit36f9c9dbb3cab8247008403ccb08ce26c0fdc99f。输出head/线上CI见PR最新回执，未合main/未改PR144源分支。
- 用户最新边界：有限大模型类型，全部允许连接，M11/M12永久绑定，无boot load。当前入口docs/ALL_LEGAL_CONNECTION_SPEC.md及总方案v0.3，六模板仅回归；保留合法但缺实现/资源/程序/路线gap，不能把49格目录当实际已通。
- 独立目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/all-legal-36f9c9d/integrated，部分API资料包，非Git clone，无本地HEAD/暂存；原交付/根参考副本不覆盖，草稿在overall-drafts/all-legal不上传。新增白名单文档/机器目录/检查及自身进度；不改RTL、服务器或ref-project。
- 实际检查见all-legal-checks.json与all-legal-verification.json；完整家族语法/参数范围和编译/ROM预算待落实，连接原语/宽转换/NUM/外存/状态服务与组合功能、活性及物理验证未完成。R最终资格仍单列，不接管他人作业。
- 看板无board.json、有status-mapping，当前GitHub工具无Projects条目读写；条目/字段unverified、同步pending，管理员待指定。登记沿用management-hub PR5 pending，不重复登记，不把本地目录当在线卡片。
- 恢复第一步用Melodydt读回Issue151/PR152 head/base/评论/CI与白名单，再审查家族目录/合法profile/阶段回访控制；分配实际RTL子任务前区分原语实现与整模型验收。负责人Melodydt，独立审查人待指定。

## 2026-10-31T22:10:32+08:00：前三步片上阶段接续

- 仓库rayggxia-workspace/LLMHardwareDesign，Issue151/PR152，Melodydt；task/151-six-connection-study，PR base task/143-seven-block-v2；输入commit39bd7bf66c47e17c18aa39483c1d974a1e079aa2，输出head/当前CI见PR回执，未合main/未改PR144分支。
- 当前用户范围覆盖旧摘要：仅仓库八样本、未知规模有据保守估计、暂不考虑外存；M11/M12永久绑定无bootload。当前准入onchip-contract.json，无EXT/DMA/spill；旧system-design-contract.json的外存候选仅历史参考。
- 工作目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/steps123-39bd7bf/integrated，部分API资料包，非完整clone，无HEAD/暂存；所有候选文件在本次白名单，旧包/根副本不覆盖。源原文overall-drafts/steps123/family-sources只本地，源索引及脚本/输出SHA上传。未运行服务器，无作业交接。
- 成果入口docs/STEPS_1_3_WORK_REPORT.md和三个步骤规格；family/edge/onchip合同、sample-memory-demand、96 obligations及验证在work/Melodydt/151。实际执行见steps123-checks/verification；未做RTL/SystemC/推理、完整程序/定点接受、活性或EDA。
- 未完成：独立审查、完整字段/尺度/图实例接受、资源扩容取舍、实际适配/NUM/局部控/存储与ROM实现、R资格和物理接收；容量不足不是语义非法，不得缩模型或隐含外存。负责人Melodydt，实施子任务/审查人待指定。
- 看板本仓库无board.json、有status-mapping；无Projects条目工具，条目/字段unverified，在线同步pending，管理员待指定。登记沿用management-hub PR5 pending/以本轮读回为准，不跨库重复登记。
- 恢复第一步：用Melodydt连接读Issue151/PR152最新head/base/评论/CI，确认用户最新内存范围及白名单，检查来源索引，再从工作报告和片上合同继续；不要接管其他#143/#153工作树或作业。区分本地候选、远端分支、未合并PR和服务器真实状态。

## 2026-11-01T11:06:48+08:00：外存边界纠正与N接口澄清

- Issue151 / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，负责人Melodydt；输入86d5648，分支task/151-six-connection-study、base task/143-seven-block-v2。
- 用户明确系统有外存，当前暂不研究，保留接入；P0片上验证credit0/无自动spill仅是评估范围，不能推广为永久无外存架构。JSON显式区分architecture_memory与memory_policy，保留地址/服务/完成语义扩展边界。
- 核对固定643c6012：N是一个顶层module、内部共享group及独立TopK表；同一128bit应答口由op决定payload格式。七宏RTL未改，无服务器作业。
- 目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/memory-scope-86d5648/integrated，为隔离API资料包、非Git clone，无HEAD/暂存；旧包和根参考副本保留。成果入口docs/MEMORY_SCOPE_AND_N_INTERFACE_CLARIFICATION.md；本轮实际验证见work/Melodydt/151/memory-scope-checks.json。
- 未完成：外存接口/带宽/驻留/一致性与有源预制范围、实际wrapper/NUM/控制RTL及精度/活性/物理验收。恢复第一步读回Issue151/PR152最新head及本澄清，再按P0与系统范围分别判断；不接管其他成员目录/作业。
- PR待独立审查、未合并，Issue保持in_review、不done；审查人待指定。登记management-hub PR5本轮已读open/unmerged→pending；无board.json且当前工具无Projects条目能力，卡片unverified/同步pending，管理员待指定。输出commit、远端读回和当前CI以PR回执为准。

## 2026-11-01T11:57:42+08:00：按静态编译和共同底座重做前三步

- Issue151 / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，Melodydt；输入e44c4f5，task/151-six-connection-study，base task/143-seven-block-v2；输出commit/CI见PR最新回执。
- 当前入口docs/STEPS_1_3_WORK_REPORT.md、三个步骤规格及work/Melodydt/151/static-rework-index.json；新增family-binding/compile-lowering/static-execution三合同，保留旧角色/模型输入与历史回执。role主要编译期，固定硬件执行共享动作，不能逐产品重新综合。
- 目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/static-rework-e44c4f5/integrated为隔离API资料包，无本地Git HEAD/暂存，不覆盖旧包/根参考副本。无服务器作业；RTL/ref-project未改。
- 验证命令/输入与输出SHA见static-rework-checks/verification；只是研究一致性/有限整数与协议规则，不是模型编译或RTL/PPA。完整八产品程序、精度、MEM/NUM与适配/控制RTL、活性和共同底座物理未完成。
- 恢复第一步：本人连接读回Issue151/PR152最新head/base/评论/CI，再读本工作报告与index；核对真实绑定和缺口后才建立RTL子任务，不接管#143/#153目录或作业。
- PR待独立审查不自合并，交付后Issue回in_review，不done；审查人待指定。登记PR5本轮读回open/unmerged→pending；当前无board.json/Projects条目工具，卡片unverified、同步pending，管理员待指定。

## 2026-11-01T14:16:49+08:00：七阶段路线P1交付

- Issue151 / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，Melodydt；输入343f4d4，task/151-six-connection-study，base task/143-seven-block-v2，输出commit/CI与线上核对见PR回执。
- 用户采纳七阶段路线，本轮仅P1版本/接口合同与P2测试输入准备；入口docs/SEVEN_MACRO_INTERFACE_ROADMAP.md、docs/PHASE1_INTERFACE_BASELINE.md及work/Melodydt/151/phase1-index.json。七宏原生合同/149端口、源锁/升级记录、MST有界整数参考/向量与未来验证矩阵形成待评审材料。
- 固定643c6012；开始时PR144观察点adb819，14路径13相同、仅R内部变化、7顶层声明相同。旧源与新物理不混用，不自动升级；没有改叶宏/他人目录/ref-project，不运行服务器/RTL/SystemC/EDA。
- 本地目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/phase1-343f4d4/integrated为隔离API资料包，无Git HEAD/暂存，旧包与根参考副本保留。实际命令、工具与SHA见phase1-checks/verification；Python参考不是MST RTL通过。
- 未完成：独立审查和P1正式接收、P2真实MST顶层及后续阶段；审查人/实施子任务负责人待指定。P2-P7未开始，不将Issue标done；交付后保持in_review。
- 登记management-hub PR5本轮读回open/unmerged→pending；本仓库无board.json且当前工具无Projects条目读写，卡片unverified/同步pending，管理员待指定。无服务器作业或自动监测。
- 恢复第一步：用Melodydt读回Issue151/PR152最新head/base/评论/CI，再核对P1源锁和测试矩阵；源一致且P1接收后，才进入P2实现S_CTRL+M/T控制与最小top，母控/ROM骨架并行。


## 2026-11-01T14:40:15+08:00：P2交付与恢复

- Issue151 / [PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，Melodydt；输入be10e69bb9ad625079f68361fb47b4747d6ce040，分支task/151-six-connection-study，base task/143-seven-block-v2；输出commit/当前CI与线上读回见PR回执。
- 用户明确要求获取最新RTL并进入P2；14核心源固定707878621b2add4ed218b8c43df2e95c9a56e2ba，仅R更新，七顶层149端口相同。源码同步不授予R新资格，不接管Issue143或153。
- 新增S单在途普通端口helper、MST小顶层与固定ROM母控骨架，正式路径project/rtl/block_connection_p2/，测试project/tb/block_connection_p2/；报告docs/PHASE2_MST_IMPLEMENTATION.md。使用真实S/loader/M/T，写ACK、M状态/结果过滤、T提交/释放与协调reset分开。
- 实际命令/工具/输入输出SHA见phase2-checks/verification-status及RTL回执；只报告实际运行的有限切片，不以编译或Python代替RTL。完整模型、全部错误/形状/活性、系统物理和MEM集成未验收，P3–P7未开始。
- 本地隔离API包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/phase2-be10e69/integrated，无Git HEAD/暂存；旧包、根参考副本及其他成员目录保留。ModelSim实际运行不使用服务器，不修改系统/读取凭据。
- 当前PR待独立审查/未合并，不标done；审查人待指定，P1独立接收也未凭授权冒称完成。登记PR5 pending待最终读回；无board.json与Projects条目能力，看板unverified/同步pending，管理员待指定。
- 下一步先读回PR头/本轮锁与实测，再补P2验证矩阵缺项、扩展母控与资源反馈；P3–P7按原路线推进，不提前冻结共同底座。

- 恢复执行第一步：本人连接读取Issue151/PR152最新head/base/评论/CI，再用phase2-source-lock核对14核心源，按ARCHITECTURE复现本地RTL测试。所有新编译work库/二进制留任务目录，不上传；原始失败、修复和最终日志区分保存。无服务器作业或自动监测。

本轮正式路径实测：ModelSim六项工具命令exit0，helper6/MST13共19 CASE_PASS；源码/TB/工具/日志SHA见phase2-rtl-evidence/run-receipt.json。Sreq113/Sack112差1为协调abort；五个成功任务逐批守恒。P2仍有矩阵缺项，按phase2-verification-status继续，不能报告整体P2或硬件冻结完成。
