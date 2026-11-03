# 功能岛研究八主线：当前入口

2026-11-03，Issue151 / PR152，负责人Melodydt。main固定4b1df2c7已于上一轮同步；来源与退出门见[主线重整报告](MAIN_SYNC_AND_RESEARCH_ROADMAP.md)，本轮AF1024后的机器状态见[roadmap-update.json](../work/Melodydt/151/af1024/roadmap-update.json)。本文件替代此前按轮次叠加的“当前”提示；历史报告、source-lock及实跑receipt保留原日期/源码版本。

**当前主攻L4。** [本轮AF1024](W4_AF1024_IMPLEMENTATION.md)源b3e14e27，95849/node1r03通过（r01/r02失败保留）/34CASE/12dumpSHA通过：完整A两行Y经真实F目的写ACK交给同一F1024逐行执行。总M2/N2/E2/G1/S2/T2、父2KiB gamma，无4KiB Y数组，旧52源保持；synthetic整数，非trained质量/通用L5/物理。

| 主线/工作包 | 内容 | 实际进展 | 当前缺口 |
|---|---|---|---|
| L1 / W0 | 原生合同与来源 | 合同/角色与版本审计已有；本轮接收main六叶交付，12共同源相同 | 独立审查；完整底座能力并集/预算未冻结 |
| L2 / W1 | 输入/输出岛壳 | 固定DOT8可变输入、真实S写ACK、holding/DONE/错误已有有限RTL证据 | 通用hidden/参数端点、完整排空/复用与资源合同未实现 |
| L3 / W3 | E/G适配和FFN核 | E三输入收集、G拆拼配对及有限FFN8已有 | 六配置需要的全部op/尾字/宽数值能力未全验收 |
| L4 / W4/W5 | 完整A/F与真实样本纵向实现 | A16/F16/AF16有界RTL；N-long/F1024与4真实F行整数RTL；AFULL完整固定Sq2整数A及AF1024真实尺寸固定纵向组合已测 | 正在推进；代表性trained质量/框架/W8及全部样本变体未闭合 |
| L5 / W2/W6 | 母控与跨岛连接 | W5-IF逻辑合同和三层互联安排已有；通用端点RTL尚未开始 | 固定控制网/双岛stored ACK、fork/join/反馈与安全回收未实现 |
| L6 / W7/W8 | NUM/R及D/H配置 | BOM/算法/角色合同为候选；无完整D/H岛RTL | R叶最终资格未完成；宽算术、state/history版本与多tile原子发布缺失 |
| L7 / W9 | MoE X配置 | router/TopK/专家/归并需求已分析；完整X RTL尚未开始 | ID与score映射、动态专家调度、宽加权合并/容量未闭合 |
| L8 / W10/W11 | 真实MEM/产品/共同底座物理 | 六叶已有上游典型角资格；系统MEM/产品/共同底座尚未实现 | 真实外存接入、完整程序/ROM预算、预连/定制层几何及系统时序缺失 |

下一切片是 **L4-QUALITY：代表性数值质量/官方框架对照、W8复核及有限模型变体准入**。L4未整体退出；L5仍为通用母控/端点实施门。每步完成后覆盖更新同一现有本地交流PDF，不新建版本。

已有关键证据：[N/preNorm F8](W4_N_F8_IMPLEMENTATION.md)、[A8](W4_A8_IMPLEMENTATION.md)、[F16](W4_F16_IMPLEMENTATION.md)、[A16](W4_A16_IMPLEMENTATION.md)、[AF16](W4_AF16_IMPLEMENTATION.md)、[F1024](W4_F1024_IMPLEMENTATION.md)、[真实F行数值/RTL](QWEN_LAYER0_NUMERIC_RTL_REPORT.md)。95245 N38/F26、95248四真实F行×7项等只证明相应有限流程，不代表完整L4或模型质量。八样本×三旧target继续24GAP。

六配置A_plain/A_gate/F/D/H/X的[BOM](COARSE_BLOCK_MACRO_BOM.md)仍是串行条件方案，不是六类物理岛已制作。母控固定网/跨岛数据和stored ACK归L5；实际MEM和共同底座/M11-M12物理归L8，预算前置。外存保留，成品控制只靠M11/M12永久绑定预制能力，不依赖启动装载。

原[七阶段索引](../work/Melodydt/151/seven-stage-roadmap.json)和[八线初始计划](../work/Melodydt/151/island-sync-plan.json)作为历史快照保留，不机械读取其中旧status当当前进度。旧进度正文可追溯[ad407ef6固定版本](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ad407ef6d051dbe3f43285b7d3ff8368ff112b2e/docs/COARSE_BLOCK_RESEARCH_PROGRESS.md)。

审查人待指定，PR152未合并/非done；登记pending，看板unverified、同步pending。接续见[本轮交接](handoffs/2026-11-03-issue-151-af1024.md)。
