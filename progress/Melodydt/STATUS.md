# Melodydt 的进度

## 2026-11-04 17:05（Asia/Shanghai，UTC+08:00）：限定母控／局控研究范围

- 用户明确本分支不负责完整 Block 实现，仅研究母控／局控。[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)继续复用。
- [综合方案第0、9节](../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)将 R3／R4 改为控制 RTL＋有限协议 peer、多局控协同；R5／R6 为控制 profile／程序生成；完整 Block、数值／模型质量及系统物理保留为外部依赖门，任务／负责人待指定，不能用 peer 通过替代。
- 当前可以研究：接口／原生 ABI、ISA／装载／取指、对象与上下文、任务／事件／错误、二进制模型及控制 RTL。完整 Block RTL 不是启动前提。
- 下一步 R1 控制接口与 profile、装载准入和有限资源模型，再 R2 二进制控制解释器；未在本轮实施控制 RTL、Block RTL、模型或服务器实验。
- 发布前基线614cdab41cfde66ee31c92fc3e44a9e1733a338a；独立部分 API 目录 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-scope-614cdab/delivery，无 .git／HEAD／index，旧目录保留；最终 commit／核验见在线回执。
- [本轮文档验证](../../work/Melodydt/179/control-scope-validation.json)记录范围与来源。研究 in_progress，PR Draft／未合并；登记 PR5 pending；缺 board.json／Projects 工具，看板 unverified／同步 pending，管理员／审查人待指定。

下方早期研究步骤按其轮次保留；完整 Block 实现目标已由本条和方案范围节修正。

## 2026-11-04 16:25（Asia/Shanghai，UTC+08:00）：综合方案与下一步

- [Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人／认证 Melodydt，已核 write 权限；研究仍 in_progress，未审查未合并。
- 更新[综合方案 v0.2](../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)：五类 Block／28 宏示例、Block 间／宏间／母控到块／局控到宏的四类连接、24 指令及小端位编码、本地存储／配置装载／任务执行、已有进度及 R0–R7。ISA v0.1 和软件编码不变，宏级断电按用户要求暂缓。
- 明确固定控制归属、建议 M1–M10 控制预连但实际 pin／层未冻结；主要数据通路后制；推荐主机统一装载器，母控运行时发任务／参数，局控从本地 entry_pc 取指。以上是 proposed，不写成已完成 RTL。
- 发布前基线 d6429607d5e0f607c321ab6372e78d5f53ec96ba，tree f7a1826fee23c24ed8d939f2325961e059e44257；任务分支和 PR base 不变。本轮最终 commit／远端核验／CI 见在线回执。
- 新独立 API 目录 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-summary-d642960/delivery；无 .git／HEAD／index，是部分资料快照。旧 179／151 工作包保持；只上传本轮白名单。
- 依赖快照更新：PR178 b9dc77eb，N4／N5 四门通过，P4 完整后续尚未统一验收；PR163 64b7c85 仍无完整系统联合通过；PR167 c97353cf 与 PR152 55243d2c 的独立证据不转移资格。仅核在线／固定文档，没有重验服务器包或实时作业。
- 实际检查及产物 SHA 见[本轮验证](../../work/Melodydt/179/control-summary-validation.json)和[来源](../../work/Melodydt/179/control-summary-sources.json)。未新增 RTL／模型／服务器／EDA 作业或自动监测。
- 下一步：R1 原生 ABI／端口表、固定控制与实际数据端点、镜像／配置装载合同和真实 S 对象布局；R2 有限二进制模型；再 R3 真实 P 局控，同控制 RTL 不同程序。负责人 Melodydt，不接管其他任务。
- 登记 management-hub PR5 pending；缺 board.json／Projects 条目字段工具，看板 unverified／同步 pending，管理员／审查人待指定。[恢复交接](../../docs/handoffs/2026-11-04-issue-179-local-block-continuation.md)已更新。

## 2026-11-04（Asia/Shanghai，UTC+08:00）：母控/局控方案与ISA v0.1

- [Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人/认证Melodydt，write权限核验；研究主线按用户要求聚焦两级控制。
- 已形成[架构方案与R0–R7研究门](../../docs/local-blocks/TWO_LEVEL_CONTROL_PLAN.md)、[明确指令/编码](../../docs/local-blocks/CONTROL_ISA_V0_1.md)，24个操作码、9类记录、小端布局、描述符/端序和错误语义；规范JSON及标准库参考codec/独立向量进入本任务。
- 基线commit `1f3e916ed5c40fc54a0e7af90c675017c87317e4`、tree `0beb612ccc0dacc350e1ab5765b583efdf1fe324`；仍在task/179-local-block-continuation，PR base为task/175-local-block-design。最终发布SHA以PR/Issue在线回执读回。
- 新独立API目录D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-plan-1f3e916/delivery，无.git/HEAD/index；旧179和151资料包保持。只上传显式白名单，继承固定远端父树。
- 实际验证入口/结果见[本轮回执](../../work/Melodydt/179/control-plan-validation.json)；编码检查不等于完整镜像装配/语义编译或硬件执行。未启动新RTL/服务器/模型/EDA，无作业或自动监测。
- 下一步：R1固定真实端口与native参数字布局、能力/拓扑profile和部署检查器；R2二进制执行模型；再R3真实P局控及同控制硬件不同程序。私有S/新R/原控制物理继续由原任务负责，不接管。
- 方案proposed，整体研究in_progress、PR Draft/未审查未合并；登记PR5 pending；缺board.json/Projects条目字段工具，看板unverified、同步pending，管理员/审查人待指定。
- [交接](../../docs/handoffs/2026-11-04-issue-179-local-block-continuation.md)。此前容量/接入/原研究记录全部保留在下方。

## 2026-11-04 11:09（Asia/Shanghai，UTC+08:00）：PR176接续研究

- 当前任务：[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人/实际认证Melodydt，仓库write权限已核验；优先级和独立审查人待指定。
- 远端分支：`task/179-local-block-continuation`；设计父提交`08f2ea20a11dfdd09892a67599163e32b7237edb`；PR base=`task/175-local-block-design`。首交付commit `8513c23d70ac6156a9735f04da271cf6764a1f7c`；最终HEAD以PR180在线读回为准。
- 已完成：核对PR176/Issue175及评论、相关任务与交接；建立独立接续任务/分支；整理[已有进展和研究方案](../../docs/local-blocks/CONTINUATION_RESEARCH.md)，交付8项可重复payload容量分析。
- 关键发现：Qwen全gate/up/input共41KiB；32KiB驻留gate或Mid/input共23KiB；16KiB需不同分片/重放方案；F0两对象恰好满16KiB、Falcon J0余1KiB。仅payload下界，调度/RTL/物理未验。
- 本地：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/delivery`独立API资料目录，无.git/HEAD/index，不是完整clone；根参考副本、151既有工作包不改。远端以固定base tree继承未改内容，仅提交本任务白名单。
- 验证：管理结构检查通过；容量生成/重算及提交范围/来源核验以[任务回执](../../work/Melodydt/179/README.md)和验证索引为准。未执行新RTL/模型/服务器/EDA，无新增作业或自动监测。
- 下一步：先向用户介绍进度和方案，再在179中明确Qwen dense FFN对象/bank/真实打包/回放合同及16/32KiB两种有代价的候选轨迹；依赖PR178、PR167按其固定资格接收，保持其他任务范围。
- 状态：研究in_progress，Draft PR未审查/未合并，不标done；登记PR5 pending；无board.json/Projects item字段工具，看板unverified/同步pending，管理员待指定。
- [恢复交接](../../docs/handoffs/2026-11-04-issue-179-local-block-continuation.md)。

## 已有任务的记录入口

本分支设计基线没有Melodydt个人进度文件，新增此摘要，不覆盖其他未合并分支的实际记录。Issue151/PR152最新进度继续保留在[55243d2c固定版](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/55243d2c58626547d0d452bfb25fa79b7499b486/progress/Melodydt/STATUS.md)，G1切片已交付、整体未完成；接入/仿真记录由其引用的PR148/PR150维护。合并发生同路径冲突时保留两侧进展，不用本任务摘要覆盖历史。原PDF/服务器/作业/实施要求归各原任务，不在179中复制执行。
