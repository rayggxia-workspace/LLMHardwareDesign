> 主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

> 主线五首轮实施：共同表顺序器、真实SACK的edge DMA/TXRX、原生A/F执行器和固定top已上传。unit96170/node1/29秒通过DMA29+SEQ30；实际G1整合96183/node1编译通过、正在运行，未预报18CASE/10流通过。下一核真实G1终态，后续同RTL换表和一般拓扑；主线四trained质量仍并行。[实施合同](W5_CONTROL_FIRST_SLICE.md)、[unit报告](W5_EDGE_DMA_AND_SEQUENCER_REPORT.md)、[交接](handoffs/2026-11-03-issue-151-w5-first-rtl.md)。后续统一使用主线一至八汇报，H编号仅作子阶段。

> 2026-11-03 H1 v0.1：[三图/控制表/生存期](H1_GRAPH_CONTROL_SPEC.md)和[工作报告](H1_WORK_REPORT.md)已形成可审查规格。三图4路径、28正式拒绝及11独立审查通过；同12叶候选含新增edge S16KiB，实际共同RTL未实施，逻辑表1184/2016/1808B、共同5856B候选不等于物理ROM。L5前置设计输入已形成，下一H2端点/母顺序器切片；当前L4-QUALITY-AF、24GAP、R/NUM/X/MEM与物理门保持。本轮无RTL/服务器。交接见[H1](handoffs/2026-11-03-issue-151-h1.md)。 H1 v0.1只验收声明A/F切片，运行时LOOP/被跳分支及更广图仍待H3扩展；不把旧八主线改成全部完成。

> 2026-11-03 当前总方案：[混合控制v0.6](HYBRID_METAL_CONTROL_PLAN.md)。用户确认冻结后可用M11/M12永久编码此前未列出的有界合法新图；主候选为粗任务表＋固定母顺序器＋预制端点/真实ACK/局部令牌＋固定岛内程序。H0文档已形成，H1图/资源/控制存储规格前置；H2/H3对应L5实现仍未完成。L4-QUALITY-AF及所有原数值/状态/MEM/物理门保持；本次不新增RTL资格。

# 功能岛研究八主线：当前入口

2026-11-03，Issue151 / PR152，负责人Melodydt。main固定4b1df2c7已于上一轮同步；来源与退出门见[主线重整报告](MAIN_SYNC_AND_RESEARCH_ROADMAP.md)，本轮QUALITY后的机器状态见[roadmap-update.json](../work/Melodydt/151/quality/roadmap-update.json)。本文件替代此前按轮次叠加的“当前”提示；历史报告、source-lock及实跑receipt保留原日期/源码版本。

**当前推进主线五首轮RTL，主线四质量并行收口。** [本轮官方参考/W8](L4_QUALITY_REFERENCE_W8_REPORT.md)源b18e8a5f，95979/r02/node1/2:55：28官方FP32阶段、8真实F行×7CASE和8actualSHA通过，95978闭包失败保留。旧54runtime不改、AF1024仍原baseline。旧前缀回归非代表性未见holdout，trained整数AF/一般L5/物理均未接收。

| 主线/工作包 | 内容 | 实际进展 | 当前缺口 |
|---|---|---|---|
| L1 / W0 | 原生合同与来源 | 合同/角色与版本审计已有；本轮接收main六叶交付，12共同源相同 | 独立审查；完整底座能力并集/预算未冻结 |
| L2 / W1 | 输入/输出岛壳 | 固定DOT8可变输入、真实S写ACK、holding/DONE/错误已有有限RTL证据 | 通用hidden/参数端点、完整排空/复用与资源合同未实现 |
| L3 / W3 | E/G适配和FFN核 | E三输入收集、G拆拼配对及有限FFN8已有 | 六配置需要的全部op/尾字/宽数值能力未全验收 |
| L4 / W4/W5 | 完整A/F与真实样本纵向实现 | A16/F16/AF16有界RTL；N-long/F1024与4真实F行整数RTL，官方FP32参考及同Fin10 W8八行回归；AFULL完整固定Sq2整数A及AF1024真实尺寸固定纵向组合已测 | 正在推进；完整trained整数AF误差、新代表性质量门及全部样本变体未闭合 |
| L5 / W2/W6 | 母控与跨岛连接 | H1规格已形成；共同母顺序器/edge S DMA新增RTL，96170的59unit实测通过；最终96208的12终态+18真实G1及10SHA通过 | G1首切片已验证；同RTL换表G2/G3、RUN错误/prefix取消及更广拓扑未验收 |
| L6 / W7/W8 | NUM/R及D/H配置 | BOM/算法/角色合同为候选；无完整D/H岛RTL | R叶最终资格未完成；宽算术、state/history版本与多tile原子发布缺失 |
| L7 / W9 | MoE X配置 | router/TopK/专家/归并需求已分析；完整X RTL尚未开始 | ID与score映射、动态专家调度、宽加权合并/容量未闭合 |
| L8 / W10/W11 | 真实MEM/产品/共同底座物理 | 六叶已有上游典型角资格；系统MEM/产品/共同底座尚未实现 | 真实外存接入、完整程序/ROM预算、预连/定制层几何及系统时序缺失 |

并行质量切片是 **L4-QUALITY-AF：真实训练参数的完整Sq2整数A→两行F数值参考与误差分解**，并先冻结新代表性cal/holdout及产品阈值。L4未整体退出，L5仍为通用母控/端点实施门；每步继续覆盖同一本地交流PDF。

已有关键证据：[N/preNorm F8](W4_N_F8_IMPLEMENTATION.md)、[A8](W4_A8_IMPLEMENTATION.md)、[F16](W4_F16_IMPLEMENTATION.md)、[A16](W4_A16_IMPLEMENTATION.md)、[AF16](W4_AF16_IMPLEMENTATION.md)、[F1024](W4_F1024_IMPLEMENTATION.md)、[真实F行数值/RTL](QWEN_LAYER0_NUMERIC_RTL_REPORT.md)。95245 N38/F26、95248四真实F行×7项等只证明相应有限流程，不代表完整L4或模型质量。八样本×三旧target继续24GAP。

六配置A_plain/A_gate/F/D/H/X的[BOM](COARSE_BLOCK_MACRO_BOM.md)仍是串行条件方案，不是六类物理岛已制作。母控固定网/跨岛数据和stored ACK归L5；实际MEM和共同底座/M11-M12物理归L8，预算前置。外存保留，成品控制只靠M11/M12永久绑定预制能力，不依赖启动装载。

原[七阶段索引](../work/Melodydt/151/seven-stage-roadmap.json)和[八线初始计划](../work/Melodydt/151/island-sync-plan.json)作为历史快照保留，不机械读取其中旧status当当前进度。旧进度正文可追溯[ad407ef6固定版本](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ad407ef6d051dbe3f43285b7d3ff8368ff112b2e/docs/COARSE_BLOCK_RESEARCH_PROGRESS.md)。

审查人待指定，PR152未合并/非done；登记pending，看板unverified、同步pending。接续见[本轮交接](handoffs/2026-11-03-issue-151-quality.md)。
