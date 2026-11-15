# YUZE-LU 的进度

2026-11-15 CST。#219 / [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269)：正在接入 PR273 的尚未写回数据驻留、生产消费联合搜索和最后读者释放。新增原生范围主入口、实际 SRAM 安放与必要写回、重编码后的硬件准入，以及最终输出/持久 KV 比较器。远端十项生命周期检查通过；完整36层 prefill/decode 的联合搜索与同计划封装、TLM流水线正在执行，尚未数值验收。前一轮仅删除回载的范围8结果单独保留，不算本轮目标完成。

下一步：完成全图搜索与实际指令包执行，核对 DDR 流量、最终 logits 和72份持久KV；当前 MPR1 仍要求完整K和DDR输入，跨命令K续接缺口已定位到投影服务解码/流控，不能假借额外部分和bank。Issue保持in_progress，PR保持draft；待指定审查人，不自行合并。看板unverified/同步pending沿用现有配置缺项，未运行P512/D128。


2026-11-15 CST。#219 / [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269)：按 PR185 恢复控制归属与宏硬边界，显式绑定同计划指令和候选端点连线。完整 36 层 Qwen 两 token prefill + 一步自产 KV decode 的 141490/70457 次调用全部执行，651/723 个产出张量逐字节一致。剩余 20 张 benchmark 图均已尝试，全部停在尺寸解析或 operand lowering，尚未进入候选选择。时序未校准；不代表物理、广泛精度或稳态吞吐验收。源码及[结果](../../project/experiments/blockv2_mod/evidence/architecture-revision-185/RESULTS_ZH.md)提交本 PR 审查，Issue #219 更广泛优化目标保持 in_progress。

下一步：独立审查本次增量；后续前端尺寸与降级缺口另按证据推进。负责人 YUZE-LU；待指定独立审查人，不自行合并。仓库 config/board.json 在当前 head 不存在，看板 unverified/同步 pending；本次没有扩大到历史 Issue #219 的 20% 优化/物理评估目标。

2026-11-14 16:39 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 增加外部指定的 SRAM 实例、容量和读写位宽。112358、112359 用同一底座分别读回 128-bit 和 512-bit 读配置，核对对齐事务换算和 Gather 单字写约束。远端 10 项测试通过，目标底座执行仍待接入。[参数及回执](../../work/YUZE-LU/219/native_ingress/request_retirement/REQUEST_SEQUENCE.md#sram-容量和端口位宽由外部配置)。

2026-11-14 16:25 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 增加 Algo1 指令包、同计划连线与独立底座的 TLM 准入检查。远端 112167 核对 184,927 页与 639 页 Gather 替换，定位 12 类派发缺口、2 类完成信号缺口，以及 7 类等待 TLM 实现的候选服务。PR #260 原短程作业按诊断记录。下一步用目标绑定的资源时序与单页 Gather 验证实际指令执行。[回执及复现](../../work/YUZE-LU/219/native_ingress/request_retirement/REQUEST_SEQUENCE.md#对同计划底座的-tlm-准入)。

2026-11-14 16:08 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 完成 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 两输入位置的短程 prefill。111805 用原版审计核对 578 页和 288 次 KV 写入，TLM 结果 5.5065 token/s。111806 已报告第一步 token 退休，第二步运行中。完整 P512/D128 仍取消。见[快评回执](../../work/YUZE-LU/219/native_ingress/request_retirement/REQUEST_SEQUENCE.md#pr-260-短程吞吐)。

2026-11-14 15:56 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 合并 C0 残差控制网和原整图接口。111993 独立读回 6,085 根网和 12,753 个端点。14 类整图服务仍缺派发或完成接口。本轮继续用两项 PR #260 短程作业，待其原版审计。见[合并布线入口](../../work/YUZE-LU/219/native_ingress/SAME_PLAN_NATIVE_REQUEST.md#同一底座的合并布线输入)。

2026-11-14 15:46 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 读回 C0 残差输出至下一层 RMSNorm 输入的 512 组写确认依赖及 1,024 个局控镜像，复用原 153 根候选线。111983 完成。C0 输入来源、母控页和可执行的 S32 RMSNorm 服务待闭合。两项 PR #260 短程评估仍运行。见[残差输出](../../work/YUZE-LU/219/native_ingress/SAME_PLAN_NATIVE_REQUEST.md#残差输出写入下一层的输入窗口)。

2026-11-14 15:36 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 将真实算子图中的一条 S32 残差映射到 C0，读回 32 个局控镜像及 Algo2 侧的 431 根控制网。111950 和三项否定对照通过。U 组通用数据输出缺 M10 接点，C0 输入供应、结果窗交接和母控调度待闭合。两项 PR #260 短程评估仍进行中。见[残差回执](../../work/YUZE-LU/219/native_ingress/SAME_PLAN_NATIVE_REQUEST.md#c0-的-s32-残差编译与搬运接口)。

2026-11-14 15:15 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 从独立 Block V2 候选底座读回 5,935 根网、12,330 个 M10 端点，保护项拒绝改坐标及换底座。20 根接入诊断来自试布占用。111873、111882 和项目结构检查通过。下一步补齐目标服务和退休路径，短程 PR #260 作业 111805、111806 仍运行。见[同图交接](../../work/YUZE-LU/219/native_ingress/SAME_PLAN_NATIVE_REQUEST.md#候选底座独立读回)。

2026-11-14 15:00 CST。#219 停止完整 P512/D128 作业 109409，使用 PR #260 的 TLM 短程方法对同图部署远程并行执行两个输入位置的 prefill 和两步 decode，作业 111805 与 111806 等待结果。111756 完成同页实时 QKV 的四条 KVR1 写回，111828 复核同一 Algo2 布线规范的接入诊断。见[复现与验收](../../work/YUZE-LU/219/native_ingress/request_retirement/REQUEST_SEQUENCE.md#pr-260-短程吞吐)。

2026-11-14 14:39 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 记录 U0 CALL、索引写确认、首读及读回，扩展 PR #260 的 RTL 审计，保持原有完成校验。用全图的 288 个原始 KVR1 描述符跑完真实 DDR 写回，两个阶段的实际回执驱动阶段控制器。KV 源和其余阶段结果仍来自各自测试端。下一步同一底座接实时 QKV、词表及 C0 索引发送。见[回执](../../work/YUZE-LU/219/native_ingress/request_retirement/REQUEST_SEQUENCE.md#实际索引与-kv-回执)。

2026-11-14 14:28 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 从同一份图部署生成 128 条阶段记录和 127 条退休到 Gather 的索引交接。现有请求控制器等页提交、KV 和词表 token，再启动 U0。远端协议和实际 U0 组件回归通过。用 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 当前接口读回 184,927 页，TLM 执行首四页。整机还需接实际 KV 和 P0/C0 物理链，并核对 CALL 与 U0 索引 ACK 的 RTL 审计顺序。见[阶段交接](../../work/YUZE-LU/219/native_ingress/request_retirement/REQUEST_SEQUENCE.md)。

2026-11-14 14:02 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 从同一 Block V2 候选底座和全图请求生成 184,927 页的原生指令索引与 5,935 根 Algo2 候选网。Algo2 接口通过读回，639 个 Gather 页换用主底座拓扑的母控镜像且 U0 正常／背压回归通过。下一步接通实时 token/KV 提交和其余 14 类服务，完成 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 整机验收。见[交接](../../work/YUZE-LU/219/native_ingress/SAME_PLAN_NATIVE_REQUEST.md)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 将 decode 的索引写确认编入 127 条原生 U0 Gather。正常和背压两种回归从封存 logits 现场选 token 并核对真实权重行。新 U0 网表重建了 Algo2 接口。全图词表退休源、母控与 U0 的写入路径仍需共同绑定。见[远端回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#decode-退休索引与新版-u0-接点)。
2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 从 639 个封存 Gather 生成索引来源和局控程序。U0 经 v45 DMA 从真实 prompt 记录取索引并按 512 笔 SRAM 提交回报。Decode 的 127 条入口均记录上一退休步的写确认依赖，目标底座上的退休输送和固定 #260 完整请求待接入。见[远端回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#u0-从-ddr-取-prompt-索引)。
2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 由同一 Gather 计划生成 U0 局控程序和 650 根数据网。真实局控经四拍入口执行首条 Gather，v45 DMA 交付 128 笔真实权重数据，目标 SRAM 512 笔提交后回报完成。Algo2 读回候选端点。详细布线停在 N32 接入，仍需接上母控索引供给并验收 #260 全请求。见[远端回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#u0-gather-的局控程序和两端布线交接)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 新增 v45 DMA 客户端 3 的 684 个 M10 接点。独立 DMA 的 5,028 个端口有详细布线，最终报告零违例。Algo2 在新端点目录上重新读回原三 P 计划的 4,981 根网。Gather 的真实权重行通过双拍记录的远端对照。U0 仍需运行时整行窗口与写确认服务，再接 #260 整图。见[远程回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#gather-的-v45-dma-接点与双拍请求)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 从已链接 Gather 生成 #260 的运行时索引记录。639 条记录与旧整包逐字节一致，首个 prompt 页用原后端执行并核对实际 8 KiB 行。候选底座的 v45 DMA 存在可用协议的逻辑客户，但该客户的 M10 接点和 U.S 确认路径待实现。见[输入索引回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#从已链接的查表指令生成运行时索引表)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 将 C/U 的 512 次存储字搬运编成两端局控 PM 片段并独立读回。DDR 端点审计定位到 C/U 尚缺运行时索引读入路径，固定 #260 仍需可常驻的局控服务及整图封包。见[局控与索引入口回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#cu-存储链路的局控编码与动态查表入口)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 为 C/U 已存储字搬运增加 16 B 合同。真实端点上的 512 条分片搬运生成同源控制 IR 和 Algo2 输入，后者独立读回。远端 413 项回归通过。运行时 DDR 行供数和整图 #260 仍待打通。见[远端回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#c0-到-u0-的逐字提交与试布回执)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 将原生 WAIT 表达能力加入 Algo1 搜索。独立 DMA 的 4,344 个数据端口详细布线报告零违例，同一三 P 计划用新物理凭据重新被 Algo2 和固定 #260 页读取器读回。新底座仍欠运行时索引到 DDR 行的 Gather 服务、完整数据/控制布线和真实 KV 与退休验收。见[远端回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#原生-wait-准入与-dma-接点实布)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 增加整图 lowering 缺项报告，并将 #260 整数请求的 21 项完成合同与 main P/U 的直接入口审计对账。远端复现 tile 交接及共享 DDR 下的宏选择反转，410 项回归通过。Algo2 实际试布仍有 4,973 根待解决。下一步验证新底座的可执行服务、真实数据路径和 KV/退休。详见[模型与整图缺项回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#七点模型复核与整图缺项)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 用 main P2545 真实叶端点与独立 DMA 的暂定 M10 接点完成同计划接口回放。Algo2 读入 4,981 根控制与数据网，固定 #260 读回 192 条 CALL 和 64 组 WAIT。原生层引出、Algo2 几何结果及整图原生执行仍待验收。见[三 P 同计划回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#含数据面的三-p-同计划接口试验)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 把原生命令所需的数据面通路纳入 Algo1 候选准入。109781 用实际端点清单复核三 P 首层方案并报告九个缺失需求，109758 的细网格试布布通 27/730 根控制网。完整数据通路、联合布线和原生整图执行待验证。详见[同计划准入回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#algo1-原生命令的数据面准入)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 增加同计划的原生编码与 #260 指令页交接。109741 在 main Block V2 加交换器的候选摆位上，用同一方案产出 730 根待布控制网，#260 读取器核对 192 条 CALL 和 64 组 WAIT，三 P 原生镜像与归档字节一致。109728 的 410 项回归通过。当前验证范围是控制端点与指令页，数据面和严格整图执行仍待接入。见[原生交接回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#同一计划交给-algo2-与-260-指令页读取器)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 接入现有 Algo2 的试布回执。Block V2 的 C0→U0 实际端点用例中，Algo1 将失败物理网追溯到对应逻辑需求并重搜；该用例无替代输入路径。另有替代搬运路径的回归验证重新生成同计划指令和线束。见[试布回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#algo2-试布回执与-algo1-重选)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 核对重编 #260 整包的 184,927 页及 8,273,243 次 CALL。已把 2,876,395 次原始描述符的 P/U 直接入口冲突接入 Algo1 搜索，并从真实 Gather 的命令行复现；409 项远端回归通过。匹配头部的调用仍需完整服务资格。下一步验证同底座的实际局控编码、数据面及 Algo2 布线。详见[准入证据](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#block-v2-直接描述符准入审计)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 把同一 #260 封存请求的包控制和三 P 描述符、权重、栅栏需求投影到已有联合摆位，Algo2 读入 5132 根网。OpenDB 验证 2310 个原生叶宏端点和 8414 个候选逃线端点。另核对 main P2545 实际接点，DMA v45 仍需在共同摆位引出 4344 个数据面逻辑端点。联合摆位与 main 的 P 版本不同。详见[联合摆位交接](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#联合摆位的-pdma-交接与-main-端点对照)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 新增 Block V2 的 C0→U0 数据链交接，Algo2 读回 153 根链路信号及相应控制网；U0、U1 反向各缺 128 个 M10 数据接点。已对照 #260 整包的 21 类调用与实际 P/U 描述符入口，给出需要另选服务或重新编码的调用。109409 继续执行旧拓扑的严格 TLM。详见[数据端点与调用入口核对](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md#数据端点交接与整包描述符入口核对)。

2026-11-14 CST。#219 的 [PR #269](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/269) 已在远端重编 #260 既有拓扑的 639 个位置，130 份程序与描述符二进制和归档一致。根据新编程序的目标掩码，在 Block V2 候选摆位上绑定 881 根控制网。U39 的实际本地控制器拒绝 #260 Gather 的描述符版本，数据面及产品服务编码仍待接入。初版封包缺少 FFN activation 地址表，已从新编阶段凭据重新封包并提交全请求 TLM。详见[远程回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md)。

2026-11-14 CST。#219 的框架分支已跑通 tile 交接、同池 DDR 排序反转及 Qwen2.5-3B B1/S2 无 KV 完整图编译。两种搜索宽度在三组真实输入上逐位核对 logits。当前算法 2 读取旧候选底座的整图交接和两 U 真实端点用例。#260 归档 linker 用新 Algo1 计划生成一段三 P SwiGLU 原生程序，192 次 CALL 的控制和描述符与参考逐字节一致。Block V2 九组加 MC06 准入、同计划完整请求和持续 KV 退休仍待验证。详见[远程回执](../../work/YUZE-LU/219/FRAMEWORK_INTEGRATION.md)。

2026-11-13 CST。#219 第 51 轮将 #251 SRAM feeder 的回传槽、宽窄口仲裁和 READY 纳入 DP 快照。8 组归档 RTL 的 43 个访问完成拍一致，900 组远程压力对照及 395 项回归通过。深度 8 的两层同池对照也保住早读选择。FFN 分段外存需求已提取，分支内 FFN 竞争计价及历史裁剪仍待接入。详见[芯片状态计价方案](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)。任务分支待汇入 [PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257)。

2026-11-13 CST。#219 第 49 轮把每客户端回传速率和后端信用周转纳入快照代价。旧 KV 写回上关键路径时，宽度 8 在四个模型对照中改选串行，宽度 1 仍选早读。预计旧写推迟量由 66 拍修正为 132 拍，逐事件参考为 136 拍。两层宽度 8 继续选早读，快照总长与参考分别相差 8 和 320 拍。392 项远程回归通过。

2026-11-13 CST。#219 第 47 轮从逐事件对照抽出窗口版本、资源区间、DDR 通道预约和客户端最早回传边，用于候选计价。两层同池测试在两种压力下保住早读选择，宽度 8 约 3.3 秒，绝对周期低估约 9–13%。391 项远程回归通过。下一轮用相同混合后端校准 DDR 及 FFN 时长，并在未参与拟合的压力场景复核。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)第 46 轮允许有限 SRAM 上按阶段原址更新并保留旧版本，复用 #234 层 1 的归一化程序形状及实际 gamma 地址。四组成对回放和 389 项远程回归通过。S32 整段硬件时序及数值接续仍待独立验证。任务分支待汇入 [PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257)。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)第 45 轮为不同操作数记录首次及末次读取。归档 S16 RMSNorm 的阶段长度用于驻留／非驻留对照，388 项远程回归通过。#234 层间 S32 归一化仍待独立接续及校准。任务分支待汇入 [PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257)。

2026-11-13 CST。#219 第 44 轮将两层 FFN 的独立 DDR 镜像、各自 KV 和共享内存状态接进同一事件图。387 项远程回归、24 个快照分岔及层 1 的六份整数分块对照通过。两段完整 FFN 在同流量下验证早读可推迟前层 KV 写回，同时提前两层完成。两种压力下的同池贪心均达到强制对照的最早完成拍，宽度 8 的 Slurm `106616` 也在两种压力下选到同一最早方案。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)推进至第 43 轮。相邻两步使用同一物理历史与共享 FFN/KV 外存仲裁，允许旧 K 预取和 FFN 重叠，下一 token 的 Q/K/V 仍等待 FFN 完成。六份 #234 归档 KV 的五种分块逐位验证及 386 项远程回归通过。Attention 端口和计算时序仍待原生校准，整模型跨层与退休仍待接续。任务分支待汇入 [PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257)。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)推进至第 42 轮。事件 DP 支持对有 DDR 副本的历史窗口提前一阶段试排，保留发布确认、旧读者和有限 SRAM 约束。#234 两条序列的前三步完整历史逐地址对账。旧写上关键路径的四个模型对照中，宽度 8 切回串行并达到同池最佳，严格贪心仍选预取。385 项远程回归通过。后续需校准原生 Attention 服务并接入同层 FFN、跨 token 追加和下一层。任务分支待汇入 [PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257)。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)推进至第 41 轮。完整 FFN 进入事件 DP，读写共享后端队列、bank 行状态和返回方向。旧 KV 等 STORE 确认后才允许读回，候选可从运行中的 FFN 和 DDR 快照试排。383 项远程回归和 288 次混合快照对照通过，旧写的位置能使同一权重副本候选的排序反转。下一步把 #234 的连续整数 KV 交接和更多 Attention 阶段接入同一事件时间线。任务分支的改动待汇入 [PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257)。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 29 轮。P 共同请求生成 K 窗口和 A 加载，五组完整 RTL 各对齐 1,444 个窗口。新跑的首片 COPY 候选使后续 1,443 个 header 及程序结果晚一拍。367 项测试通过，六个负例均拒绝。scope dispatch 与 CALL 仍来自波形，继续从 P 退休和终端回执…17318 tokens truncated…0 µm 已通过独立叶宏全部工程门，完整交付归档回收并核对。父层互连与组合时序另验收。

[Issue #208](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/208)补齐[图册与接点坐标](../../docs/experiments/assets/compact-ge/index.html)，已核对图源、接点数及本地图册链接。

## 2026-11-06 紧凑双型局部 SRAM S

[Issue #200](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/200)由 YUZE-LU 执行。两个 16 KiB 独立宏完成详细布线和 273/965 位同时逃逸测试，实际有效占地为 82.45% 和 82.11%。结果、原生独立验收范围和复跑入口见[实验说明](../../project/experiments/compact_local_s/README.md)。[PR #203](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/203) 已合并。两颗的完整 GDS DRC 均为 0，TT 300 MHz 独立审计、选定 ODB 的三初态回归和四 bank 等价均通过。看板缺项目配置，登记沿用待合并的管理中心 PR #5。

## 2026-11-05 局部 SRAM S 交付

[Issue #155](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/155)的后续整合，执行账号 YUZE-LU。P4/N4/N5 的 300 MHz 独立叶宏验收、版图、六文件索引和 RTL 回归入口见[局部 SRAM S](../../docs/BLOCK_LOCAL_S_SRAM.md)。系统级接入单独验收。看板配置和同步由项目管理员核验。

## 2026-11-01：Issue143 六块成果进入整合审查

按用户决定先提交 M/N/E/G/S/T 六块，不等待 R；六块全部适用最终门及源绑定本地实收通过，R 标为未完成且不在合格清单。Issue #143 保持开放，研究 PR #144 保留；当前 `task/143-six-block-main` 基于 main a103da35，面向 main 的成果整合待独立审查。规格和结果见 docs/BLOCK_V2.md、docs/BLOCK_V2_RESULTS.md；核验命令见 docs/ARCHITECTURE.md。登记 PR5 pending；缺 config/board.json，看板 unverified/同步 pending；审查人待指定。历史记录保留在下方。

## 2026-10-30 计算积木规划文档同步

- 更新时间：2026-10-30（Asia/Shanghai）。任务：[Issue #139](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/139)，负责人/实际身份 YUZE-LU；独立分支 `task/139-compute-block-docs`，基于 main `6a681d66`。
- 已完成：原本地 V/M 分析重命名为 MVR 讨论总结，加入 R 的结构、数值、状态容量/共享存储、四抽头限制及首版独立保留结论；仓库[同文正文](../../docs/COMPUTE_BLOCK_BOUNDARIES_2026-10-30.md)。
- 同步：[项目说明](../../预制计算底座项目说明_v1.0.md)和 README/导读/简介/架构/状态；[决策 0005](../../docs/decisions/0005-compute-block-v-split-r.md)记录 V 三宏、R 保留、每种一个实现、逐宏最终布局布线。M/V 缩位宽和部分和精简仍为候选，未转移原 V 的物理资格。
- 验证：[本次交付记录](../../work/YUZE-LU/139/README.md)及 validation.json；仅文档/管理检查，未重跑模型、RTL、EDA 或服务器作业，未修改现有实现工作树。
- PR/最终提交与 CI 以 Issue #139 回执为准；待独立审查，不自合并或标 done。登记沿用 PR5 pending；缺 board.json 与 Projects 条目工具，看板 unverified/同步 pending，管理员待指定。
- 续补：已有 M/V/R/S/T 的电路图、存储、控制与固定源码来源已直接加入总项目说明第 5.6 节；规划中的新 V 三宏不画图，本次不新建 Block 说明文件。
- 交付：[PR #142](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/142)。用户本轮明确要求同步 main，将在检查后正常合并并读回；不代替他人审查或绕过保护。具体最终合并回执以 Issue #139 为准；主线另行落实逐宏物理验收，本次不接管运行任务。

## 2026-10-26 模型分析与计算图归档

- 更新时间：2026-10-27 14:25 CST，用户已明确授权提交到 main。
- 任务：[Issue #116](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/116)，负责人及实际账号 YUZE-LU；分支 `task/116-model-analysis-docs`。
- 本地成果：[模型分析目录](../../docs/model-analysis/README.md)，集中提供精简字符算子图、完整图册和原 PR #115 的实验分析报告；旧报告路径保留跳转，README 与导读更新入口。
- 原始图册、图结构、配置和回执按 SHA 原样复制；新说明明确 Falcon 旧手工图的已知差异。没有重新运行模型/ONNX、修改历史 Issue #114 的证据或接触服务器作业。
- 验证与导入清单：[work116](../../work/YUZE-LU/116/README.md)。本轮重验183份导入文件、196处本地引用、40张SVG、10组成功回执及原报告正文迁移均通过；正在通过任务分支和PR交付，实际PR/CI/合并回执保存在Issue #116，未合并前不标done。未重跑模型或物理实验。
- 接入：无 `config/board.json`，连接器未提供 Projects 条目能力，条目未核实、同步 pending；管理员待指定。现有登记和项目里程碑不变。

## 2026-10-27 共同文档阶段边界澄清

- 任务：[Issue #123](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/123)，负责人及实际账号 YUZE-LU。
- 成果：[决策 0004](../../docs/decisions/0004-block-library-base-freeze.md)，同步 README、项目简介、项目说明和共同状态。
- 已确认：Nangate45 原生十层预制与新增两层定制；叶块、共同底座与任务定制分别验收。同类实例/裕量版本组合、排布和固定预连线在底座阶段确定；共同底座冻结后不得按任务改变固定资源。
- 边界：保留 Issue #121 / PR #122 的既有范围与验收状态；本次没有修改实现工作树、RTL、实验配置或服务器任务。
- 验证与集成：[PR #124](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/124) 交付本次澄清；管理结构、44 处本地链接、3 张表格及暂存差分检查通过，PR CI/最终合并以 Issue #123 的读回回执为准。用户明确授权经 PR 正常合入 main，不代替独立审查或绕过保护。
- 接入：本次读回既有登记 management-hub PR #5 仍 open/未合并（pending）；无 config/board.json，当前工具无 Projects 能力，条目/字段 unverified、同步 pending，管理员待指定。此缺项不改变文档业务验收。
- 下一步：完成文档检查、PR/CI 与 main 内容读回；后续物理实现继续由原任务跟踪。

## 2026-10-26 模型实验分析报告

- 任务：[Issue #114](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/114)，负责人及实际账号 YUZE-LU。
- 成果：[阶段性分析报告](../../docs/model-analysis/MODEL_EXPERIMENT_ANALYSIS.md)，补充 README 与研究资料导读入口；来源与检查见 [work114](../../work/YUZE-LU/114/README.md)。
- 已完成：读取九份固定版本报告及十个来源 PR 的状态，梳理八个模型的目的、范围、结果、失败和能力/接口约束；读取后续 #102/#106/#109/#110 的范围，避免将旧批次限制误写为当前无 RTL。
- 集成：用户明确要求合入 main；本次通过独立文档 PR 交付，最终 PR/commit/CI 以 Issue #114 的读回回执为准。不合并其他实验 PR，不冒充独立审查批准。
- 验证：文档检查与管理结构的实际结果见 validation.json；未重跑模型、原始数值接收、RTL 或物理。
- 接入：登记 management-hub PR5 仍 pending；无 board.json，实际 Projects 查询缺 read:project，看板 unverified、同步 pending，管理员待指定。
- 下一步：完成当前文档检查、PR/CI 及按本次授权入 main 的读回；原实验审查和后续实现另按原任务推进。

## 历史阶段：Issue #7（2026-10-21）

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- Issue：[候选 Block 边界及分层布线流程](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU，当前 `in_review`；审查人和优先级待指定。
- 已完成：读取两个项目的接口／RTL／报告和已有 ACT—MXU 实验；形成 [候选划分及对照矩阵](../../docs/experiments/openTPU-llaccel-block-plan.md)；核实用户授权的集群工程与工具可访问；在独立分支 `task/7-block-routing` 增加正式实验运行器，原参考包和原工作区改动保留。
- 实验：完整16-lane VECTOR的screening 89442通过；早期89443人工时限超时及89447恢复预检查失败保留。89448从checkpoint进入stage4、不重综合，仍在默认LEC、未得CTS完成产物，继续 `UNLIMITED`。89449因旧默认PDN已知不兼容，在确认PENDING后取消，非按求解耗时终止48。终态以[试验记录](../../docs/experiments/issue-7-vector-pilot.md)和[轻量索引](../../project/experiments/block_hierarchy/results/issue-7.json)为准。
- 运行约束：用户明确要求不设时限；后续作业取消人工有限时长，实读 c64/c96 `MaxTime=UNLIMITED`，每次提交后核验实际 `TimeLimit`。早期超时与恢复预检查失败保留，不通过删除历史制造成功。
- 新增验证：独立RTL回归89455通过，VECTOR 1203例／数学12000组／舍入16384组；测试副本唯一 `1u << 31` 兼容修正有diff/hash，原RTL与参考不改。89453及后续顶层是另开的 `LEC_CHECK=0` 物理路线，89448默认检查路线保持运行，不混用二者证明。
- 实际物理结果：89453完整Block和89472单宏顶层均完成最终布线，DRT错误0；89475最终只读审计通过，双网连通、唯一固定宏／2246位接口与逐位映射、M7–M9接入几何复算闭合。Block setup WS −4.16659 ns／287违例、最大电容59违例；父级setup WS −0.0429892 ns／3违例，质量仍未通过。父层新增2245个IO buffer，single-sink实际跳过CTS，无多宏时钟树验证。历史PG／hook失败均保留。
- 验证：`python scripts/check_project.py`、Python 脚本语法编译、远程 Bash 语法检查和 `git diff --check` 通过；镜像阶段门级 LEC 已调用、尚未得结论。完整 core 回归、原 RTL 到物理网表的完整形式比较、多计算图、受限定制和系统签核未执行。
- 下一步：审查本轮工程实现和失败证据，保留内部／父级时序、电容、异步复位抽象和缺少宏功耗模型的限制；再准备同资源F0/H1对照、多Block和H2冻结资源规则。89448继续无限时求解，其后续匹配模型必须来自其自身最终实现，不套用89453模型。
- PR：[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)供审查；89472／89475实际运行代码快照 `357dd98a7a07f370a1cc2c67b066c7ecccf3bf9a`，75启动时仅文档／结果dirty并如实记录。最终采集器精简及成果记录由PR当前HEAD回执绑定；每个attempt的SHA-256独立保存，未合并或验收前不标 `done`。
- 接入：管理中心 [登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 本轮读回仍 `OPEN`，登记 `pending`；Projects 缺 `read:project`，无 `config/board.json`，看板 `unverified`、同步 `pending`，由具备权限的管理员处理（待指定），见[持久交接](../../docs/handoffs/2026-10-21-issue-7-projects.md)。




## 2026-10-22 ACT/MXU 同资源物理对照

- 更新时间：2026-10-23 04:37 CST，中国标准时间UTC+08:00；负责人／实际GitHub账号YUZE-LU。
- [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)，分支`task/15-opentpu-compare`，[PR #17](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17)，依赖PR10基线2b76f69；独立工作树，未修改PR8／PR10工作树、VECTOR或89448。
- 已完成：三种块内实现与拆分两宏／合并一宏父层实际布局布线。保持169109初始映射单元、37023DFF、12个SRAM及相同计算／状态逻辑；统一1662bit外部引脚、die、2.5ns时钟及0.5ns IO预算，全部物理支持成本计入。拆分89829／34:01自然COMPLETED0，五个物理来源和六类证明共十一份记录全部通过compare；功能89831、覆盖89832、完整ODB89833通过。旧20的act_data[145] slew违例经单一驱动X4→X8并重新DRT／提取消除，没有放宽门槛。
- 实测：拆分／合并总叶面积484240.4／482252.4µm²，总信号线6647739／6204600µm，通孔1322289／1284106，完整setup WNS +0.102306／+0.065642ns、hold +0.036146／+0.013027ns。拆分块内线长−249953µm，被父层+693092µm抵消；总线长+7.142%，不能将父层IO／时钟全归为685bit边界成本。
- 成果：[中文HTML和三类图表](../../docs/experiments/issue-15-opentpu-results.html)，[过程及失败证据](../../docs/experiments/issue-15-opentpu-comparison.md)。生成代码8a646d8，冻结输入SHA f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d；report-manifest绑定9个产物。实际查看三PNG、浏览器核验页面／表格／三图／路径和完整ODB展开，临时页面服务已关闭。delivery-validation记录实际检查和两个成本证明负例，均拒绝且未改变合格输出。
- 补充已完成：全量清线重布21／89826自然COMPLETED0（1:02:26），匹配功能89827／RC89828／五ODB成本89835全通过；另存完整十一来源对照，快照72b9829d0df7ac7d30c5b7a6f8e602f11e317c2070cbacab4f55e466299cce0f。与主拆分叶面积相同，总线长多42µm、通孔少2、setup多0.000008ns；原主报告和9产物SHA不变，不能当作显著改善。两套合计15份唯一封存来源全部自然完成、UNLIMITED。Issue in_review、PR17待独立审查。
- 限制：H1允许新增有源缓冲和全父层路由，M10以下父层线长占比约99.39%／99.26%，不代表H2少量定制层冻结底座；单small／typical／固定布局与引脚，synthetic SRAM无GDS、上游RTL通用等价和制造签核未完成。
- 下一步：PR独立审查／合并及最终验收由人处理，审查人待指定。不自合并或标done；审查人／优先级待指定。H2预算及限定制层是后续独立实验。
- 接入：登记管理中心PR5本次核验仍OPEN未合并、pending；本仓库无board.json，连接器无Projects条目工具、CLI实际GraphQL查询返回INSUFFICIENT_SCOPES缺read:project，看板unverified、同步pending，管理员待指定。

## 历史记录：2026-10-21 资料与规则交付


- 更新时间：2026-10-21（中国标准时间，UTC+08:00）
- 当前任务：[Issue #3：同步两份布线报告并补入 llaccel 引擎分析](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3)。负责人 YUZE-LU，优先级待指定。
- 已完成：同步最新总报告、线长报告及其引用资源；总报告增加 llaccel 三个引擎的中文分析与 9 张图。保持图片直接展示、长表可展开；不创建备份或多余首页。更新来源边界和包说明。
- 验证：管理结构检查、报告依赖/锚点检查、包内清单哈希、正文/表格保留和差异检查；具体结果见本任务 PR 回执与 `work/YUZE-LU/3/validation.json`。没有重跑物理实现或 STA。
- 交付：[PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4)，分支 `task/3-update-routing-reports`，报告成果 commit `b041d53`；2026-10-21 按用户明确要求已合并到 main，合并提交 `1d80491`。
- 下一步：继续审查[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)。登记仍为 pending。
- 阻塞/接入缺项：报告上传可独立完成；本仓库没有看板配置，当前凭据缺少 `read:project`，无法核验或同步 Projects。由有相应权限的管理员处理，处理人待指定；详见[交接](../../docs/handoffs/2026-10-20-issue-3-report-board.md)。不自行扩大凭据权限。
- 历史：Issue #1 的初期资料由 PR #2 导入，后续参考资料提交 `695587d`、`5c86109` 已进入 main。`ref-project/` 仍不属于 Agent 主动或例行维护范围。

## 2026-10-21 补充交付

- 按用户要求补入 `ref-project/llm-routing/模块与接口报告.html`，保留原文，并复制其引用资源；README、研究资料导读及阅读说明补充入口。
- 本次仅检查新报告的本地引用是否存在及管理结构、文档差异；不执行哈希检查，不重算参考数据，不修改原有清单。原清单不覆盖此次新增文件。
- 沿用 Issue #3、任务分支及 PR #4 上传；2026-10-21 已按用户要求合并到 main。看板权限缺项沿用上述交接。

## 2026-10-21 远程服务器规则

- [Issue #9](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/9)：记录服务器节点、`/public/home/yuzelu` 下的目录权限和 sbatch 任务命名要求，README、AGENTS.md 提供规则入口。
- 任务名采用“本人姓名缩写-任务缩写”，如 `hpy-block`；脚本和提交时覆盖的任务名均应遵守，便于在 squeue 的 NAME 中辨认。
- 验证：管理结构检查及所改文档的差异检查通过；未登录或修改远程服务器。通过 PR #4 上传，2026-10-21 已按用户要求合并到 main；看板同步仍待具备权限的管理员处理。

## 2026-10-21 main 集成

- 按用户“最新状态都提交到 main”的明确要求，将报告、远程规则及此前未提交的工艺互连资料补充一并纳入 PR #4 并合并。合并提交 `1d804912927602900aa074339db33156a805c582`；本地已同步到 main。
- 管理结构及文档差异检查通过；未重算参考数据。其他成员的独立 PR 未合并。登记、看板的既有待办继续保留，不宣称已完成。

## 历史记录：2026-10-19

- 更新时间：2026-10-19（中国标准时间，UTC+08:00）
- 当前任务：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)
- 已完成：初期研究资料已进入 `main`；PR #2 已合并。本次按用户要求直接在 `main` 提交并推送更新后的研究资料导读与用户提供的 `ref-project/` 改动；成果提交为 `695587d`、`5c86109`。
- 下一步：完成[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 的审查；由具备 Projects 权限的管理员核验或配置项目看板。`ref-project/` 不纳入 Agent 的主动或例行维护，用户更新后可按要求提交；无需逐项审查或做哈希检查。
- 阻塞：物理实现原始代码、数据库与工具环境未包含在当前资料包；共享存储位置和实际可访问性待核实。
- 本次验证：`python scripts/check_project.py` 通过；导读的 6 个本地相对链接存在；变更文档的 `git diff --check` 通过。未检查参考包内部改动或哈希，未执行业务构建／仿真。本地未配置 `config/board.json`，看板仍待管理员处理。

## 2026-10-23 布局与接口报告本地归档

- 按用户要求，沿用 Issue #7 并发工作树 `issue-7-parallel-blocks` / 分支 `task/7-parallel-blocks`，将两份报告集中到 `ref-project/llm-routing/docs/`，并修正相对资源 URL 与 README、资料导读、阅读说明中的入口。详见[报告目录说明](../../ref-project/llm-routing/docs/README.md)。
- 已核验移动前 56 个不同本地资源 URL 均存在；移动只调整 URL，报告正文和标签结构保持不变。新 Block 报告从外部生成产物原样复制，保留源文件。项目管理结构检查通过；未重跑 EDA。
- 交付状态：仅本地文件整理，尚未 commit / 推送，现有 PR #10 尚不包含此修改；Issue 状态、项目里程碑及看板未变。登记/看板缺项沿用原任务交接。下一步可按用户后续提交要求并入现有 PR，不能把本地归档视为已合入 main。

## 2026-10-23 按用户授权整合实验与 HTML

- 用户明确授权完成 PR #8、#10、#17 及两份 HTML 的提交与合并；H2（Issue #31）继续独立运行。HTML 的来源和范围不变，先前“仅本地”的记录为归档时快照。
- 本次技术复核：H1 主/补充对照从现有封存记录重算，全部成本与质量字段一致；9 个报告产物 SHA 未改变。缺少成本审计、错源审计两负例均拒绝；并发电气门槛、Tcl 修复与配置覆盖回归通过。不是新跑 EDA 或上游 RTL 通用等价证明。
- 合并权限来自本次用户明确指令；不冒充独立 GitHub APPROVED 审查，不绕过保护规则。登记 PR5 仍 pending；看板实读缺 read:project，unverified / 同步 pending。

## 2026-10-23 用户授权整合

用户明确授权将主线PR #8、并发PR #10及H1 PR #17合入main，并将两份参考HTML归档到ref-project/llm-routing/docs/。以上旧记录中的待授权／不自合并描述是当时状态，本次按用户的新授权执行，不伪造独立审查批准。H2工作树及运行任务保持独立。本次验证与限制见[整合回执](../../docs/handoffs/2026-10-23-h1-html-integration.md)。

网络恢复续办：PR #8 已合并为 a30d598，PR #10 已按匹配 head 成功合并为 a77d288；完整 H1 整合树由 PR #17 交付，最新 CI 和合并状态以在线记录为准。本地 8 项检查、58 份 Python 语法、两份 HTML 资源／锚点及 9 产物不变检查通过。Issue #7 的 VECTOR 质量缺口保留；H1 交付与 H2／Issue #31 分开，项目登记及看板待办不变。
