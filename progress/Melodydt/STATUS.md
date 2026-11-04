# Melodydt 的进度

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
