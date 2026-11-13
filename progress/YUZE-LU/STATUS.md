# YUZE-LU 的进度

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

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 29 轮。P 共同请求生成 K 窗口和 A 加载，五组完整 RTL 各对齐 1,444 个窗口。新跑的首片 COPY 候选使后续 1,443 个 header 及程序结果晚一拍。367 项测试通过，六个负例均拒绝。scope dispatch 与 CALL 仍来自波形，继续从 P 退休和终端回执生成 CALL。[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 沿用远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 28 轮。P 记录队列和回包直接驱动侧带与 EXEC。四组完整 RTL 各逐拍对齐 72,064 条侧带命令，COPY 候选改变 564 条命令的时刻，关闭 W 前瞻增加 340,018 拍。366 项测试通过，六个负例均拒绝。继续由 P 的请求生成 K header，再接入 scope dispatch 和 CALL。[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 沿用远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 27 轮。A 证明、M 回包和 P 退休直接生成 W/A 绑定。三组完整轨迹各逐拍对齐 66,048 次绑定及退休。第 21 个 K tile 的 COPY 晚一拍后，首个绑定早四拍，共 576 次绑定及 EXEC 接纳改变，程序完成拍相同。365 项测试通过，六个篡改负例均拒绝。侧带命令、K header 和 CALL 仍由波形提供。[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 沿用远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 26 轮。M 分配直接驱动共享 DDR，再由读回驱动 FILL。三组完整轨迹各重算 66,048 次 bank 安装和确认。小例改变新 ALLOC 后，已有 W 的确认提前 4、2 拍，DMA 回执与独立 RTL 一致。364 项测试通过，六个篡改负例均拒绝。侧带意图、W/A 绑定、K header 和 CALL 仍从波形提供。[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 沿用远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 25 轮。三组完整 RTL 各从 W bank 安装和 CALL 重算 1,123,200 次物理 DDR 请求及等量返回。小例从同一在途状态重算候选，旧 W 与描述符均提前 3 拍，逐 beat 对齐独立 RTL。363 项测试通过，六个篡改负例均拒绝。W bank 安装仍采样，继续与 M 分配和返回链路双向连接。[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 沿用远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 24 轮。基线及 COPY 候选各从 1,122,816 个 W beat 推出 66,048 次 FILL，完整回包和绑定逐拍一致。基线 5,563 次等待 FILL 确认槽，候选 5,555 次。362 项测试通过，五个篡改负例均拒绝。DMA 客户端握手仍来自波形，继续接入 W 源端与共享 DDR 仲裁。[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 沿用远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 23 轮。九组完整 RTL 各重算 66,048 次 W/A 绑定并逐拍对齐，覆盖前瞻、关闭前瞻和 COPY 候选。360 项测试通过，六个篡改负例均拒绝。完整检查以采样绑定启动 M 重放，再按回包、退休和 A 证明反查绑定。源文件清单确认逐拍对照使用 #251 基础及 #250 的三个替换文件。恢复 #251 原始文件的两组运行通过数值及字节断言，阶段周期另行记录。继续接入 W 的 DDR 请求和填充就绪。[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 沿用远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 22 轮。四组固定和三组候选 RTL 各逐拍对齐 1,444 个 K tile、69,312 次 A 读及 4,332 次共同证明接纳。两组带背压候选把 COPY 晚启动一拍，A 证明早四拍，全程序结果持平。无外加背压对照的 A 证明及程序结果均早一拍。358 项测试通过，九个篡改负例均拒绝。K header、W/A 绑定、侧带命令及 FILL 首次就绪仍采样。[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 沿用远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 21 轮。四组 #251 完整 RTL 各逐拍对齐 138,112 个命令及 66,048 次 W 分配。快照内保留已发 FILL、W bank 代次和待分配请求，候选修改会重算旧请求接纳。实际关闭前瞻的两组对照增加 322,410 和 340,018 拍，模型在各自采样入口下逐拍复现。355 项测试通过，八个篡改负例均拒绝。A 捕获、W/A 绑定、侧带命令和 FILL 首次就绪仍用采样，继续接入 COPY/SRAM/DDR。[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 沿用远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 20 轮。四组 #251 RTL 逐拍核对 264,192 条 M EXEC 和 1,080,832 个回包，P 首字写回从 M 执行与 guard 所有权重算。受控候选图中，加入两个控制回包后，宽度 8 的 DP 为 39 拍，严格贪心为 42 拍。353 项测试和七个负例通过。M 接纳与控制回包就绪仍来自 RTL 采样，继续接入 A/W 准备及命令仲裁。[PR #257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 待本地后续提交，#219 仍在执行，看板交接沿用现有记录。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 19 轮。四组 #251 完整 FFN 按物理 SRAM 的写确认重建 768 次 P DONE、24 次 Down 组完成，并重放 7,552 字读回和程序接受。352 项测试通过，七个篡改负例均拒绝。P 首字写发起仍来自 RTL 采样，下一步接入 K／权重／M 执行。PR #257 和看板沿用现有远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 18 轮。接入 G 流水、Mid SRAM 所有权及目录发布。四组 #251 完整 FFN 的 344 个 Mid tile、145,168 个事件逐拍对账。受控 RTL 中首条 G 晚一拍放行，首块 Mid 早十拍发布，完整 FFN 周期持平。351 项通过。下一步接入 P 计算与跨 scope 完整重排。PR #257 和看板沿用现有远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 17 轮。接入阶段 READY 门和逐 16 B 字的 scatter。#251 四组完整 FFN 对账 22,016 字及 232 次条带提交，提交拍由写 ACK 重算。350 项通过。后续沿已采样的 P DONE 向前接 P 计算，向后接 G 和 Mid 提交。PR #257 和看板沿用现有远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 16 轮。DP 支持跨任务阶段完成依赖和提前描述符准备。四组 #251 完整 FFN 重新编译，用实际生产者握手和描述符重放重建控制放行，256 组隔离回放逐拍对账。受控争用下宽度 8 的 DP 用 9 拍，严格贪心用 11 拍。349 项通过。继续把 P、scatter、Mid 的完成接入同一动态计划。PR #257 和看板沿用现有远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 15 轮。#251 完整 FFN 四组 RTL 的 768 次 P 接纳逐拍对账。最长控制器等待为 Gate/Up 1,578 拍、Down 6,759 拍，Down 同组描述符额外等待最长 33 拍。候选描述符准备可与输入搬运重叠，独立检查仍要求读取前有真实 ACK。348 项通过。继续实现由候选计划动态生成跨 scope 放行和 P 服务完成。PR #257 和看板沿用现有远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 14 轮。重编译 #251 完整 FFN，4 组原生周期和计数与归档相同，重放逐拍核对 768 个 CALL／终端和 1,536 个描述符 beat。服务 VALID 到接纳最长 6,759 拍。下一步将外层 Gate/Up 或 Down 放行、P 就绪和服务完成纳入候选重放，现有对照以真实 CALL 和 DONE 驱动。PR #257 和看板沿用现有远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 13 轮。#251 FFN 的有限 DDR 队列与物理权重副本选择已接入 DP，9 个 RTL 对照核对 2,728 个 beat 和每条 lane 的满载时间。旧请求更换通道后，两副本的最优选择随之翻转。347 项通过。继续联调真实 MC／LC 及完整 FFN，PR #257 和看板沿用现有远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 12 轮。普通读 DMA 的物理 beat、预留、寄存发放和回传槽接入 DP；7 个 #251 RTL 对照核对 267 个 beat 的五个事件拍，客户端反压使同 128 B 的路径排序翻转。346 项测试和实际 `run.py --event-ir` 入口通过。下一步接入 FFN 的有限 DDR 后端和真实局控。PR #257 和看板沿用现有远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)完成本地第 11 轮，18 次 #251 原 DMA RTL 对照逐拍核对 117,150 个通道采样和 99,720 次 DDR 握手。原生 offer 子模型解释了 897 个因保持 VALID 而少补发的通道拍，下一步把编译候选的物理 beat、预留和回传接入重放分支。PR #257 和看板沿用现有远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)在本地 `task/219-chip-state-replay` 完成第 9–10 轮。从 [#257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 继续把 SRAM 捕获、覆盖、发布和退休拆开，保留延迟写回期间的结果槽。重跑 #251 原生 SRAM RTL，8 个条件 86 次握手逐拍一致，反压使宽读与四次窄读的选择反转。待把探针合同接入原生候选，校准 DMA offer、局控、跨层和跨 token，沿用现有远端交接。

2026-11-13 CST。#219 的[芯片状态重放](../../project/experiments/block_synthesis/STATE_DEPENDENT_COST_PLAN.md)从 [#257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 固定提交继续，在本地分支 `task/219-chip-state-replay` 完成第 1–8 轮检查点，远端待提交。搬运分支按新旧请求共同仲裁后的整份计划比较，加入 #251 DMA 通道滑动发放上限。339 项测试通过，#251 12 个冻结条件的 69,312 字／例物理 COPY 写入逐项核对。待实现按阶段的真实窗口所有权、原生 DMA 可变请求及局控对照、跨层和跨 token 验收。登记和看板沿用既有交接。

2026-11-11 CST：#219 的[事件前沿](../../project/experiments/block_synthesis/EVENT_FRONTIER.md)在 [#257](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/257) 独立叠加到 #220，使用 #251 三 P FFN 的 12 组冻结 RTL 日志核对事件、容量、ACK、周期和流量。
固定 scope 回放的 DP 与贪心持平。可重排原生候选、整模型和系统性能留待后续独立验收。

2026-11-09 CST：#219/PR220[迭代23/24](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_24.md)继续in_progress。
逐行地址选择及来源可查的动态high16原生覆盖，保持16KiB/原宏/数值格式；双平台319测试。
84合成完整程序及36此前真实模型边界程序四初态RTL通过，实际错行/错K均失败；初版漏检与外部预算工具修正保留。
两行相对强旧贪心少7.421%模型时间，新DP仍比新强贪心慢0.0441%；四行仅有限S调查少8.574%，不冒充整网20%。
整模型流量分类首版缺覆盖投影已修，308终态独立319测试及守恒通过，80.19亿逻辑请求，B/A tile加载占38.48%/28.86%。
下一步联合表示/分片/驻留，避免重复计算已获tile复用；原长搜索保持运行，101683终态待回收，不因耗时重启。
新覆盖整模型/控制DMA/SystemC/KV/能耗/token/s和充分适配3–4B对照仍未完成。PR待独立审查、不自合并；登记pending/看板unverified，同步交接继续有效。

2026-11-09 CST：#219/PR220[迭代22](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_22.md)继续in_progress。
未修改M/P/feeder/S的四态各288案例、三策略四输入四初态共48完整冷程序及实际错行负对照通过；Windows/Linux/服务器各312测试。
两行width8模型时间较旧约束少10.50729%，同合同DP额外仅0.57703%；宽8完整程序RTL、实际权重与共同图注册待补。
ISSUE请求位点1.745%，逻辑流量审计定位跨S中转和同S地址排列重读；不外推整芯片利用率/DRAM性能。
下一步显式逐字匹配/布局与合法跨S路径，继续回收101683/101673/101669/101626/101525及依赖作业；20%、KV/SystemC/能耗/token/s/充分适配对照未完成。
按[协作规则](../../.agents/skills/rayggxia-project-collab/SKILL.md)提交PR220待独立审查，不自合并；登记pending、看板unverified/同步pending，已有交接继续有效。

2026-11-09 CST：#219/PR220迭代21继续in_progress；同一前沿已实现就绪节点、兼容多行与有限S布局选择。
严格贪心控制已纠正，Windows/Linux/独立服务器各309项通过；首版窄束标签问题、本机解包异常和临时盘失败均保留。
101657已终态回收：18tile/72计划/288独立数值重验通过，DP额外最好1.26044%，仍有退化。
101673严格就绪与101669窄束调查运行中；下一步核对同句柄结果、分析消费后仍保活的多余spill，补完整程序RTL/权重/热循环及全图资格。
PR220迭代19/20在线02a52244；本轮代码提交回执另记。登记pending、看板unverified/同步pending；20%及KV/SystemC/能耗/token/s/充分适配对照未完成。

2026-11-09 CST：#219/PR220迭代19/20继续in_progress。完整FFN事件重叠少4.43044%模型时间、记录不变，同池DP额外0，独立服务器与三初态64程序/216证书通过。
新增有限S多行分组/实际布局/付费重排，每次前沿更新成本；三初态各288行服务和Windows/Linux各305项通过。
2/4行真实S32冷tile DP仍分别慢9.41%/4.71%，不凑20%；更紧布局界的贪心负例保留。
下一步回收101657/101660，联合就绪DAG、分组和驻留；补完整批程序RTL及真实权重全部选中元素。
101626/101525仍运行，101654/101655等待101626；独立纯轨迹101659终态通过，本机异常根因未定。
算法20%/KV/SystemC能耗/token/s/充分适配比较未完成；不自合并，登记pending、看板unverified/同步pending。


2026-11-09 CST：#219/PR220[迭代18](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_18.md)保留原生逻辑位置/输出提交，前沿选择实际S复用、付费外部重读或原位重算。
同硬件FFN共同后端时间少5.34688%、记录少1.54219%；同池DP额外0，不计算法20%。
Windows/Linux最终各289项，54真实边界/324程序、三初态各48个真实RTL与陈旧字/漏输出负对照，独立保存证据重验通过。
旧全图101616 COMPLETED0:0，三输入实际各73循环全部元素有限S回放逐位相同；尾部错误以冻结源复现修正后，取消受影响101625、提交101626，101525保持运行。
下一步回收新全图及实际权重全部元素，再优化一般分片、跨S和资源长期占用。算法20%/KV/SystemC能耗/token/s/适配对照未完成；Issue in_progress，不自合并，登记pending/看板unverified。

2026-11-09 CST：#219/PR220[迭代17](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_17.md)新增候选路径约束的跨S复制/副本/静态并集状态，默认注册不启用未合格硬件。
两区域候选条件模型时间少16.30%/15.28%，不是现有产品或DP额外收益；加强静态路径选择后的强贪心仍优于部分DP。
两环境各277项，三初态各64次真实SRAM传输边界/提前ACK负对照、54实际边界/162程序及独立126序列重验通过。
v1 Windows异常退出保留，失败策略以同冻结源Linux补验；旧全图101591终态已回收，101616新选中实际权重作业RUNNING、101525继续RUNNING。
下一轮优先共同原生表达式的有限S驻留/重算与分片。算法20%/KV/SystemC能耗/token/s/对照仍未完成；Issue in_progress，不自合并，登记pending/看板unverified。

2026-11-09 CST：#219/PR220[迭代16](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_16.md)新增显式前序SRAM/银行与完整周期成本。
FFN同资源新池3030136180 ticks，较旧池少3.47246%；同池DP额外0，非算法20%。两环境各269项，三初态各48条8元素RTL连续链与两类负对照通过。
101593旧四循环及101604新12段连续循环全部元素接完整36层整数图，三输入逐位通过；101590失败已修，101605的54个真实边界案例补验通过。
继续核对跨S传递的真实端口/控制，再优化搬运、有限S与映射；KV/SystemC/能耗/token/s/对照未完成。Issue219 in_progress，不自合并；登记pending/看板unverified。

2026-11-09 CST：#219/PR220迭代15本地阶段：驻留候选已接通图覆盖搜索，真实FFN同池排序改进5.39681367%，新DP对新强贪心额外0，尚非整模型20%。
两环境各261项通过；真实权重边界/全部元素接回整图和完整搜索作业已排队，未预记通过。
101548旧完整计划三输入终态逐位通过。下一步回收新作业，优化跨元素S/常量/保护字/B银行状态，保持硬件不变及强同池基线。
本轮在线发布待处理，Issue219继续in_progress；PR待独立审查、不自合并；登记pending、看板unverified/同步pending。

2026-11-09 CST：#219/PR220[迭代14](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_14.md)部分交付。
来源闭合修复后完整图独立重验通过；原生SSA/有限S复制DP、216组合成边界数值、三初态各168个实际M/E/S RTL程序及负对照通过。
Windows/Linux各248项。尚未注册完整候选或实际权重整网驻留，无校准时间/能耗/token/s资格；算法20%未完成。
101516同池终态额外0.00010276037%，101548新选中数值与101525拓扑归档时运行。下一步接入完整候选并回放真实边界/整图。
Issue219 in_progress、PR220待独立审查，不自合并/关闭；登记pending，看板unverified/同步pending，继续本任务。

2026-11-09 CST：#219/PR220[迭代13](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_13.md)部分交付。
未修改P/M/S/feeder多行S32 Add/Sub聚合三初态各384例、实际负对照、两环境各234项通过。
23个真实FFN Add含相同准备的串行成本机会少29.8194%、记录少29.4998%，未注册动作池/生成新计划，不能算算法或整网收益。
101500历史池终态189,861,695,398 ticks，慢于当前167,410,840,866；101501/101513/101516/101525归档时仍运行。
一般脏驻留、算法20%及后续多轮/KV/校准SystemC能耗/token/s/最优适配对照未完成。
Issue in_progress；PR待独立审查、不自合并；登记pending，看板unverified/同步pending。

2026-11-09 CST：#219/PR220[迭代12](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_12.md)部分交付。
新增未就绪长链资源下界/单金属诊断，独立DAG和合法拓扑穷举；Windows/Linux各231项通过。
真实FFN额外0，125个最大并集未加强切片下界；完整新greedy更差，强计划保留，不替换默认策略。
101509完整phase池终态，最强条件DP仅额外0.0000192676%；101526其自身三输入数值终态逐位通过。
101516完整同池搜索、101525拓扑诊断继续核验，4核/UNLIMITED。
外存频繁往返仅部分解决；一般驻留/算法20%及后续多轮/KV/SystemC能耗/token/s/最优适配对照未完成。
Issue219 in_progress，待独立审查不自合并；登记pending，看板unverified/同步pending。

2026-11-09 CST：#219/PR220[迭代11](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_11.md)部分交付。
原生tile描述符阶段协作及独立工作/等待/有限S/全资源预约检查，Windows/Linux各221项、4个literal/native双回放通过。
真实FFN101508终态，共同后端少3.07596%但同池搜索额外0，流量多48；普通分片全图101506终态仍额外0。
新整网贪心167,410,873,122 ticks，少17.39470%属于共同后端、流量多4048，不能充当算法20%。
101511新贪心三输入逐位数值终态通过，HF/argmax/SHA保持；101509策略/101513同池好前缀及101500/101501仍运行，4核/UNLIMITED。
后续回收终态、按新池关键链/至多25.0392%机会及精确驻留/搬运合同继续算法迭代。
完整KV/校准SystemC能耗/token/s/最优适配对照未完成。Issue219 in_progress，待独立审查不自合并；登记pending，看板unverified/同步pending。

2026-11-09 CST：#219/PR220[迭代10](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_10.md)部分交付。
完整已验计划关键链/动作族下界诊断101504完成：分片前动作族最多余8.6111%，仅调排序不足20%。
多M原生tile共同候选、独立地址/临时区/资源审计，Windows/Linux各214项、4个literal/native有限S双回放及负对照通过。
真实FFN101505完成，新池仍选4,225,968,320 ticks旧强计划、额外0；PU资格E共用通道1阻止整段并行，下一轮做真实阶段交接与有限S。
101500/101501/101506归档时RUNNING，独立冻结、4核/UNLIMITED；新整网计划数值及20%/完整KV/校准SystemC能耗/token/s/最优适配对照待完成。
Issue219 in_progress，待独立审查不自合并；登记pending，看板unverified/同步pending。

2026-11-09 CST：#219/PR220[迭代9](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_9.md)部分交付。
实际阶段窗口/独立检查、额外外存成本及同宽度好前缀消融；Windows/Linux各204项，原生重排三组SRAM初态各347例及负对照通过。
有限S数值68例，其中60例新顺序；真实FFN仍不胜此前强计划，额外0，保存负结果与作废分母。修正N后完整DP三输入数值已逐位通过。
101500/101501为两份独立冻结的完整图消融，4核/UNLIMITED继续运行。下一步终态、有效新计划数值和一般有限S驻留；
20%、完整KV/校准系统能耗/token/s及最优适配对照仍未完成。Issue219 in_progress，待独立审查不自合并；登记pending，看板unverified/同步pending。

2026-11-09 CST：#219/PR220[迭代8](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_8.md)部分交付。
tile贪心/DP各三次完整3B整数数值逐位通过；NExp历史原生模板缺零Stats，已修并通过三初态各653例真实N及负对照。
旧向量数值不证明旧原生命令。187项Windows/Linux通过，重编译整图贪心三输入数值逐位通过；完整旧DP/条件DP持平、额外0，选中DP数值补验中。修正FFN额外3.890449%，价格下界无新增收益。
发现整tile锁E远长于实际E段，下一轮按真实数据/S/上下文/ACK边界研究释放，不直接扣时间；强基线共享新能力。
20%、一般驻留、完整KV/SystemC能耗/token/s和最优适配对照继续未完成。Issue219 in_progress，待独立审查不自合并；登记pending，看板unverified/同步pending。

2026-11-09 CST：#219/PR220[迭代7](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_7.md)部分交付。
受限tile共同候选/缓存失效/独立审计与有限S小例子数值通过，Windows/Linux各178项；真实FFN规划搬运减67.0961%。
该计划/新整网数值仍待验，条件策略相对同池旧DP额外0，不计后端扩展为20%。外围服务显式实例资格，首次C/F/J试验作废留证。
下一步有效FFN/整网数值、占用分析和真实驻留/调度优化；完整KV/SystemC能耗/token/s/最优适配对照继续未完成。
Issue219 in_progress、PR待独立审查，不自合并；登记pending、看板unverified/同步pending，沿用交接。

2026-11-09 CST：#219/PR220[迭代6](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_6.md)部分交付。
347例不变RTL的多列+真实E/M标量转换、184例多行、Windows/Linux各169项通过；包含实际转换/外存复制的共同成本配方已建，
尚未接入完整候选和新数值，不计算法20%。前轮完整3B阶段计划101213三输入逐位通过、HF保持；100972仍运行/UNLIMITED。
继续做合法缓存失效、候选/独立检查/有限S回放及同池对照，随后KV/能耗/token/s/最优适配ASIC-FPGA；目标未完成。
Issue in_progress，待独立审查不自合并；登记pending，看板unverified/同步pending沿用既有交接。

2026-11-09 CST：#219/PR220[迭代5](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_5.md)部分交付。
同池条件尾部DP完整3B额外0.0716468%、真实FFN0.0871689%，资源尾部消融无收益；Windows/Linux各157项通过。
84个原生多行RTL场景（含R2/K2048）通过，B staging4096→2048、A不变；新旧S布局尚需合法化后接入全图，
不计为算法20%。完整Linux调度/成本已过，新选中计划数值101213待验；SystemC阶段100970和搬运100971通过，
早期源全图100972仍运行，首次工具/依赖/运行时失败均保留。微实验不称整机时间或能耗。
完整数值/校准SystemC/能耗/KV token/s和充分优化ASIC/FPGA对照继续，Issue in_progress，待独立审查不自合并/关闭。
登记pending，看板unverified/同步pending，沿用Issue7交接。

2026-11-09 CST：#219/PR220 [迭代4](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_4.md)部分交付，145项通过。
选中全图逻辑搬运中A重复读65.8%、静态权重23.4%；一般tile/跨算子驻留尚未解决，后续合同已补齐。
精确长循环/常量阶段基础和孤立候选成本守恒通过，新增SystemC作业待终态，不归因新DP收益。
确认的M容量必要差距由独立[Issue236/草稿PR237](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/237)处理；
#234/#235校准工作树/作业独立。算法20%、更多轮、KV/能耗/token/s/对照仍未完成，持续in_progress。
登记PR5 pending，缺board配置，看板unverified/同步pending，独立审查人待指定，不自合并/关闭。

2026-11-09 CST：Issue219/PR220算法迭代3加入完整K列分片与每前沿整数分配，134项、本轮六次完整Qwen2.5-3B B1/S2无KV数值逐位一致；独立审计及原件SHA核验通过。同池较强基线下整网九组18束0.706898%、真实FFN切片3.800989%，未达20%。官方SystemC原生命令阶段微实验及负对照通过；整服务锁通道掩盖重叠，下一轮做经校准的事件前沿，不能以微实验当算法/整网性能。见[证据及后续](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_3.md)。时间/能耗/KV token/s与充分优化3–4B对照仍未完成，持续in_progress；待独立审查，登记pending、看板unverified/同步pending。

2026-11-09 CST：Issue219/PR220算法迭代2完成原语阶段化、静态线束未来可行性与已知好解保留；122项/完整5、9组工作量与预算审计通过。修复九组10束有解却被窄beam丢失的问题；同候选/同预算DP执行收益仍0，新动作族九组仅剩约2.79%重排空间，20%目标继续。SystemC3.0.2安装/FIFO环境检查通过，未有校准性能结论。[本轮证据及后续](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_2.md)。待独立审查、Issue in_progress；登记PR5 pending、看板unverified/同步pending。

2026-11-09 CST：算法迭代1为当前候选族建立强制资源/依赖链乐观下界，五组/九组现计划剩余改善上限仅0.000323%/0.765027%；112项及Slurm100652通过，6份原件SHA核验。[诊断及下一轮](../../work/YUZE-LU/219/throughput-opt/ALGORITHM_ROUND_1.md)。需改进合法分阶段/分片/驻留决策，不能只调beam；不是硬件性能上限。算法20%及SystemC/能耗/token/s/ASIC-FPGA目标持续in_progress。

2026-11-08 CST用户追加：准备外提只作共享后端基线，不计入算法本身约20%目标；继续多轮。后续须有SystemC（若支持）的校准时间/能耗、prefill及带KV decode token/s，并与充分优化的3–4B ASIC/FPGA比较；若硬件瓶颈需关联独立PR。[验收合同](../../work/YUZE-LU/219/throughput-opt/OPTIMIZATION_CONTRACT.md)。当前持续in_progress，算法目标及系统比较未完成，不以约60%后端下降结束。

2026-11-08 CST：Issue219/PR220准备复用已完成完整3B复验，五组同10束降60.5851%、九组同18束降59.9470%，搬运约降72.058%。110项和六次完整数值逐位一致，30份原件SHA核验。显式外存增加83.824MiB，实际容量未资格化；非DP单独收益、未新增RTL/物理资格。[结果与源回执](../../work/YUZE-LU/219/throughput-opt/RESULTS.md)。成果进入待独立审查，不自合并/关闭；登记pending、看板unverified/同步pending。

2026-11-08 CST：Issue219/PR220继续优化，隔离分支 task/219-throughput-opt。原生工作剖析发现Dot重复准备A分量；已实现通用循环外提、显式外存地址、独立成本检查与数值接入，本地110项通过。完整3B相同范围/预算复验待运行，不宣称收益。入口[迭代记录](../../work/YUZE-LU/219/throughput-opt/README.md)；远端PR仍1d284bdc、待审，登记pending，看板unverified/同步pending。

2026-11-08：PR220新增每次转移的状态求值与部分前缀命中，完整Qwen2.5-3B五组/九组各三输入及105项检查通过。五组/同10束预算结果不变，九组模型完成时间增加约0.00007686%；未取得新增性能收益。见[结果](../../work/YUZE-LU/219/STATE_COST_RESULTS.md)。成果待独立审查；登记pending、看板unverified/同步pending。

## 2026-11-08 CST：综合只读分片复用

[Issue219/PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)：新增真实Dot分片、相同SSA输入驻留和缓存感知DP状态。完整3B五组/九组各三输入逐位一致、100项服务器测试通过；搬运减25.40%，同10束无DP额外收益。见[回执与图册](../../work/YUZE-LU/219/READ_CACHE_RESULTS.md)。待独立审查，不自合并或标done；一般脏缓存、整网控制编码、实际布线另验。登记pending，看板unverified/同步pending，待有权限维护者处理。

## 2026-11-08 CST：#220 静态互斥修复与当前母控回放

[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。修复 loop DP 和独立检查器遗漏 incompatible_nets，固定／已选连接跨时间保留约束；100341 的 90 项测试含 150 个互斥小 DAG 穷举，100338 完整 3B 计划重验通过。100343 的当前独立母控含真实程序 SRAM，配两组 #221 修复后的 U_64 局控执行自动生成 Add/Mul 小图，9 次回放核对实际数值／写 ACK／源释放／连接，正常352拍、背压491拍、复位后486拍；这是固定放置控制子集，不是整网／九目标／物理覆盖。完整数值、零预连虚拟外存和同预算无整网收益结论不变。23 个最终控制输入 Git blob 对上，v1/v2 的 66/24 份输出 SHA 核对；失败环境作业100340保留后改用已有 CP 环境重提通过。见[本轮证据](../../work/YUZE-LU/219/MUTEX_CONTROL_RESULTS.md)。成果待独立审查，不自审、合并或关闭Issue；登记pending，看板unverified/同步pending。后续：任意整网计划控制编码、tile/cache及真实物理反馈。

## 2026-11-08 CST：完整3B生成程序与整网有限调度

[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。本轮属于#220的软件缺口已修复：Gather、真实量化/布局、完整S32原语、数值回放与同源成本。最终100224/100233/100234/100235均COMPLETED0:0，75项测试、完整Qwen2.5-3B B1/S2三输入数值和五组/九组16KiB独立计划检查通过。同连接预算无整网收益，九组多束需求时模型代价降低2.68%，不称系统性能；全部spill后端的tile/cache优化、更多完整模型和物理反馈仍待后续研究。见[完整结果](../../work/YUZE-LU/219/FULL_RESULTS.md)及离线图册。成果待独立审查，未自审/合并/关闭Issue；审查人待指定，登记pending，看板unverified/同步pending。下方11-07的Gather阻塞为已修复历史。

## 2026-11-07 CST：原生叶宏转换和五类混合计划

[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219)/[Draft PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。补入G/R/T、M跨K累加、流式N、实际E宽度/尺度转换和状态租约；服务器46检查、38任务三初态原生回放、两类S四银行验证通过。各S16KiB、数据预连0，搬运使用既有虚拟接口。完整3B重检首个未覆盖为Gather，后续仍需量化、动态矩阵布局及其余整网转换；不归因于控制/预连/物理。见[证据](../../work/YUZE-LU/219/LEAF_RESULTS.md)。Issue in_progress、PR Draft；审查人待指定；登记pending，看板unverified/同步pending。

## 2026-11-07 CST：算法范围修正、零预连与虚拟外存

[Issue219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) / [Draft PR220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。撤回未经证实的硬件缺失判断；控制镜像、真实DMA和最终物理不作为算法前置条件。接入#182来源的虚拟外存，服务内连线纳入静态并集，增加独立流并行构造和真实N/E整行规则。服务器34项检查、三初态2048 RMS→残差与16 Softmax的17,792周期回放通过；5组16KiB对照完成。完整3B的矩阵/G/R/T、尺度/布局等软件lowering仍未全部完成，不称整网成功。证据、失败与入口见[修订结果](../../work/YUZE-LU/219/FIX_RESULTS.md)。状态in_progress/Draft；审查人待指定，登记pending，看板unverified/同步pending。

## 2026-11-07 18:50 CST：有约束规划器与真实 U 服务回放

[Issue #219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) / [Draft PR #220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)，分支 `task/219-general-block-search`。新增链覆盖 DP、逐元素分片、流式初解、STORE/LOAD/spill、S 时间/地址联合约束、共享副本、跨层静态网任务组改进和独立回放。最终服务器25项测试通过；生成的4项真实 U/E/S 程序三初态均与80周期预测一致。完整 Qwen2.5-3B（30.86亿参数）HF/ORT前端验证通过，整网 lowering 明确未覆盖，未生成 MC/LC 镜像或物理验收。历史0.6B和假设架构结果撤出正式证据。图册、作业、哈希、失败和下一步见[本轮结果](../../work/YUZE-LU/219/JOINT_RESULTS.md)。后续接 M/N/G/R 数值 lowering、原生 DMA 和共同控制子集；状态保持in_progress、PR Draft、审查人待指定。登记pending，看板缺配置/权限，unverified/同步pending。

## 2026-11-07（CST）通用Block前沿搜索原型

[Issue #219](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/219) · [草稿PR #220](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/220)。服务器99698完成64组分析对照；完整Qwen3-0.6B浮点前端验证通过；23组分析计划独立重放通过，41组保留失败。输入与结果图册及哈希见[结果记录](../../work/YUZE-LU/219/README.md)。当前16 KiB场景均未完成，仍需多算子覆盖、分片/spill、原生控制镜像和pin/电气合同，不能称完整综合器或硬件通过。状态保持in_progress，PR为草稿，审查人待指定；登记pending，看板缺配置待核验。

## 2026-11-08（CST）U 原生入口和双向发送修复

[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) → `in_review`；[PR #221](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/221) 待独立审查。独立 TX 槽和普通三源入口修复后，两版重新综合并通过完整原版 GDS DRC 0、TT 300 MHz、电气/PG及三档代表上层 RC。U_128 setup/hold +255.014/+14.595 ps，U_64 +73.082/+0.212 ps；最终网表 48/48、78/78 全部通过。两包及全部 1,389/2,101 文件回收核验成功，31 硬件源文件与审查代码一致。[最终回执](../../work/YUZE-LU/212/u-native-fix.md)。P 不变。用户已授权将 #221 合入 main；五类图册 U 两版已绑定新验收包，P/C/F/J 图源不变。实际合并状态以 PR 在线回执为准，Issue 在线 assignee 未指定。登记 PR5 pending，缺 board 配置，Projects unverified/同步 pending，复用接入交接 Issue7。

2026-11-08 CST：用户已授权将 #223 / PR #224 母控双格式交付合入 main。新增五类 Block 与母控的[统一索引](../../docs/experiments/assets/five-leaf-bases/README.md)，原目录及交付散列保持不变。合并状态以 PR 回执为准；独立审查未代批，登记/看板缺项继续由 Issue #7 交接。

## 2026-11-08（CST）母控物理实现

更新时间：2026-11-08 CST。[Issue #223](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/223) / [PR #224](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/224) 已完成先64后128的工程验收，待独立审查。两格式各54项RTL、54项母控最终网表、69项实际Block/局控RTL回归；共用未改物理六文件，TT300MHz setup/hold +374.917/+7.629ps、完整原版GDS DRC0，电气/RC/PG/SRAM时钟通过。U绑定#221已验收31文件源。两包及3860/3148内部文件本地全部核验，见[报告](../../docs/experiments/mother-control-dual-format.md)与[执行记录](../../work/YUZE-LU/223/README.md)。下一步：指定独立审查人、审查PR；九目标扩展和联合布局布线另验。本任务未自行合并或标done；登记PR5 pending，缺board配置，Projects unverified/同步pending，待管理员核验。


## 2026-11-07（CST）C/F/J 独立叶宏组

更新时间：2026-11-07 21:40 +0800。

[Issue #211](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/211) · [PR #213](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/213) · [验收与回收索引](../../work/YUZE-LU/211/control64-acceptance.json)。C/F/J 独立紧凑叶宏、16 KiB 私有 S、局控与适配已交付；C/F 并发发送死锁修复并通过真实 SRAM 与双局控程序。原 `_128` 包保留，新增 `_64` 三类全部通过原版完整 GDS DRC 0、PG、电气、LEC、TT 300 MHz 及最终网表回放，本地包与316/273/548个内部文件全部核验。五类 _128/_64 摆放图及图源绑定已保存，用户已授权通过 #213/#214 主线整合，合并回执以 PR 在线状态为准；联合顶层重新绑定局控 ID、控制 profile 和实际布局并独立验收。审查人待指定；登记 PR5 pending，缺 board 配置，Projects unverified/同步 pending，待管理员处理。

## 2026-11-07 17:10（CST）P/U 紧凑指令物理版本

[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) · [PR #214](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/214)。已有合格交付保留为 P_128/U_128。P_64/U_64 均完成独立物理验收：完整原版 GDS DRC 0，原生 TT 300 MHz setup/hold 分别 +86.461/+7.498 ps、+100.376/+8.670 ps，电气/PG、信号路由、代表上层三档 RC、最终网表 9/60 次程序回归通过。两包已回收到本地，1122/1480 个清单文件和程序镜像逐项校验一致。[最终版本回执](../../work/YUZE-LU/212/compact64-physical.md)。64 指紧凑取指，PM/数据接口仍 128 位，控制仍是记录的原生服务子集。下一步独立审查和合并；Issue in_review，不自合并。登记 PR #5 pending；看板缺配置，字段 unverified、同步 pending。

## 2026-11-07 13:03（CST）P/U 独立叶宏底座

[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212) · [PR #214](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/214) · [工程回执](../../work/YUZE-LU/212/README.md)。E 操作数个数 P1 已修复，[新 U 物理重验收](../../work/YUZE-LU/212/u-e-count-physical.md)通过：完整原版 GDS DRC 0，TT 300 MHz setup/hold +334.870/+3.787 ps，电气、信号和 PG 通过；130 根代表上层接入三档 RC 通过。正常/FMA 两套最终网表测试共 30 次通过。新包及 82 个清单文件已回收校验，取代旧 U 交付包。P 原包保留，新回放入口对原 P 网表三初态通过。下一步独立审查和合并；登记待合并，看板缺配置。

## 2026-11-06（CST）紧凑 SRAM S 版图图册

[Issue #207](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/207)由 YUZE-LU 执行。从 #203 最终验收产物补齐两颗 SRAM 的[版图、摆放和 M10 引脚图册](../../docs/experiments/assets/compact-local-s/index.html)，逐个比对 273／965 根引脚坐标。由 [PR #209](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/209) 交付。看板配置仍待管理员核验。

## 2026-11-06 G/E 独立宏紧凑化

[Issue #201](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/201) · [PR #205](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/205) · [源提交与作业回执](../../work/YUZE-LU/201/README.md)。G 220 µm 和单输入 E 340 µm 已通过独立叶宏全部工程门，完整交付归档回收并核对。父层互连与组合时序另验收。

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
