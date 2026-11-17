# Melodydt 的进度

## 2026-11-17（Asia/Shanghai）Qwen3 旧版 M 功耗估算

- 38809661／38809662／38809728／38809915 均 `COMPLETED 0:0`。旧版 116976 对应 TT 300 MHz setup −1.121800 ns、hold −0.053419 ns。单个 M 18 窗带载估算 263.415–272.194 mW，复位后开钟、无请求为 248.092 mW。
- Qwen3 短 Prefill／首 Decode token／稳态 Decode 的 M 参考分别为 31.95–32.07／104.19–104.31／104.29–104.41 mJ/token。另列 DDR 器件与 G32 活跃增量加 M 的小计。旧版估算沿用三路开钟与 C639 FFN 样本，使用复位后空载作等待期参照。
- Melodydt 继续归并写 DMA、U、PM 与局控；读 DMA 38769386／38769388／38795299／38795300 在 ABC，38795516–38795519 等待依赖。SRAM／母控 PM 原宏缺档。新版 M 38792357 止于 CTS hold 缓冲插入，后续从 3_place.odb 恢复物理验收。
- [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [回执与复现](../../docs/handoffs/2026-11-17-issue-280-bscc-t6-m-baseline-power.md)。任务进行中，项目登记待合并，看板待有权限维护者核验。

## Melodydt 的 Slurm 提交约定

后续在本项目提交的作业统一请求无限时限。新脚本写 `#SBATCH --time=0`，提交时显式加 `sbatch --time=0`，并读回 `TimeLimit=UNLIMITED`。后续本项目仿真迁至 BSCC-T6 的 `~/LLMHardware/zenanyan`，在支持无限时限的 `v6_384` 分区提交。运行中需要新装的开源包统一安装到 `~/LLMHardware/opt`。 [服务器交接](../../docs/handoffs/2026-11-16-issue-280-bscc-t6.md)

## 2026-11-14（Asia/Shanghai）七模型短程吞吐准备

- [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 进行中，任务分支自 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 的 `55620f17` 建立。六模型归档核验通过。Qwen3 功能复跑 114275 与归档逐字节一致。指令驱动 Gather 114290 两位置通过，DDR 读取与回调 144/144。
- [作业、验证和复跑记录](../../work/Melodydt/274/README.md)保留首次失败 114273 与修订重跑。两步 decode 和短 prefill 的整模型吞吐尚未测得。
- 下一步接 Qwen3 输入 RMS、Q/K Norm、16Q/8KV 及状态回读。Llama 需要可访问的真实整模型检查点。登记待合并，Projects 待核验和同步，审查人待指定。

## 2026-11-15（Asia/Shanghai）七模型数值参考完成

- 114294 和 114313 完成七套 FP32 数值参考与状态/输出散列。Llama 固定 ModelScope 版本及八文件上传核验完成。
- 114340 完成 Qwen3 28 层投影与全词表共 197 张量、582,016 个记录。详见 [草稿 PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 与上面的作业记录。
- 下一步生成 Qwen3 首层部署指令、运行 Q/K Norm 与写确认后跨步 KV，再扩至 28 层。两步 Decode／短 Prefill 整模型吞吐仍待测，Issue 保持进行中。

- 114376 的 1,024 维输入 RMS 和 128 维 Q/K Norm 使用真实 gamma 与独立向量，6/6 成功，214/214 DDR 回调对账。下一步串到真实 QKV 与跨步 KV，全部已提交作业均终态。

## 2026-11-15（Asia/Shanghai）七模型短程回放

- Qwen3 115055 正常结束，短 Prefill 13.481376 输入 token/s，Decode 3.585938 token/s，两个 token 均与零历史 FP32 一致。已保存日志、输出、审计和散列。
- Llama 已完成短 Prefill，六个模型的整模型 Decode 作业已提交。Gemma 的残差定点饱和、64 维头填充及混合递推服务记录在[结果与复跑索引](../../work/Melodydt/274/RESULTS.md)。
- [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 进行中，[PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 草稿。后续按模型核验实际退出码、两阶段回执、零历史数值及输入输出散列。登记 pending，Projects 看板待核验。

- Qwen3 逐周期和加速回放两个阶段时间、状态、logits 与 DDR 计数均一致。Llama 两阶段完成，短 Prefill 7.178705 输入 token/s，Decode 2.523063 token/s，FP32 两个 top-1 一致。Granite 两阶段完成，短 Prefill 8.055319 输入 token/s，Decode 2.376006 token/s，第二步 top-1 分歧已登记，另有路由诊断。Phi 的 Prefill 2.165252 输入 token/s，Decode 继续运行。

- 七个模型的两个全层回放阶段均已审计，统一使用 512-bit SRAM 端口和 512-bit 程序存储写宽。所有 Slurm 作业终态，日志和输出备查。包括阶段重跑在内的实际回执见[结果索引](../../work/Melodydt/274/RESULTS.md)。Qwen3、Llama、Phi 两步 top-1 均与 FP32 一致。Granite、Gemma、Qwen3.5 和 Falcon 有数值分歧，已补路由和同输入对照。PR 保持草稿，Issue 进行中，待数值资格、RTL／物理校准和独立审查。

## 2026-11-15（Asia/Shanghai）七模型第一轮优化

- 全部模型的权重窗口四层或首层 A/B 已结束，结果逐位和状态证据见[优化记录](../../work/Melodydt/274/OPTIMIZATION.md)。另完成 FFN Context 缓存及 64 维 KV 前缀 A/B。
- Qwen3 全层 Prefill 17.897215 输入 token/s，较基线提高 32.76%。Decode 115262 运行中，其余六模型的整层作业 115282–115287 已进入 RUNNING。待核验两步词表、状态、DDR 对账及整层增幅。
- [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 继续进行中，[PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 草稿。登记 pending，Projects 看板无项目配置，审查人待指定。

- 首轮优化整层 Slurm 115262、115282–115288 均正常退出。七模型用 512-bit SRAM 完成两阶段 A/B，候选和原基线最终残差、词表 logits 逐字节一致。短 Prefill 提升 33.89%–53.98%，两步 Decode 提升 20.82%–97.53%。输出清单已复验。另完成 Qwen3 独立 V 读取复用，Decode 达 4.948742 token/s。见[完整优化记录](../../work/Melodydt/274/OPTIMIZATION.md)。PR 保持草稿，Issue 进行中，基线数值资格与 RTL／物理校准待完成。

## 2026-11-15（Asia/Shanghai）PR #272 调度重测

- 代码 `209482b226456a7fdc328692470b26ef42ac05e6` 接入 ATT1 双窗口和四权重 bank。115340–115346 在 512-bit SRAM 下完成 14 个全层阶段，3,601 项输出清单和程序、残差、logits、反馈及状态事务均通过对账。6 个模型的 Decode 提速，七模型短 Prefill 降速。详见[重测和复跑记录](../../work/Melodydt/274/PR272_RETEST.md)。
- C380 原生 RTL 115329/115330 正常／背压周期减少 13.11%／0.91%。C639 原生 FFN 115347 正常／背压周期与 PR #272 归档一致，98 项散列通过。
- [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 进行中，[PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) 草稿。由 Melodydt 续办数值资格和整模型 RTL／物理校准，审查人待指定。登记 pending，Projects 缺看板配置，已留交接。

## 2026-11-15（Asia/Shanghai）七模型三 P 与非零历史

- 七模型全层短 Prefill 与代表性历史两步 Decode 已通过，两个阶段均无残差限幅。14 个 top-1 与同历史 FP32 一致。115618/115619/116000 全部正常退出，116181/116182 独立验收通过，6,699 项输出清单已验。见[完整记录](../../work/Melodydt/274/THREE_P_LIVE.md)。
- Gemma Q12 修正残差与后归一化写回的限幅，旧混合模型的 FP32 零历史清理已修正。范围为 512-bit TLM，整机 RTL／物理校准待续。Issue #274 进行中、PR #275 草稿，审查人待指定，登记 pending，Projects 无配置。

- 2026-11-15（Asia/Shanghai）发布[七模型速度评估交接](../../docs/handoffs/2026-11-15-issue-274-speed-evaluation.md)，集中记录最终速度、实际生效的模型专项路径和冻结复跑入口。项目结构检查通过，七组速率与最终回执逐项一致。下一步为增加分窗活动计数以接入能耗评估，整模型 RTL／物理校准仍待完成。

## 2026-11-15（Asia/Shanghai）七模型 DDR 能耗试点

- [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 以 #274 的已验收短窗为输入。已实现 [DDR 快照和分窗汇总](../../work/Melodydt/280/README.md)，本地混合读写开启前后 640 个回调及原生终态统计一致。
- 服务器指纹已核对，当前批量 SSH 身份认证待 Melodydt 恢复。下一步在同版本服务器库上做 Qwen3 全层 Prefill 与 Decode 分窗回归，随后做单 P／三 P 消融、门级标定与七模型扩测。 [恢复入口](../../docs/handoffs/2026-11-15-issue-280-ddr-energy-pilot.md)

- 已补齐 [Qwen3 DDR Slurm 入口](../../work/Melodydt/280/run_qwen3_ddr_pilot.py)，本地验证分窗参数、依赖散列失败时终止、原容器审计和结果输出路径。批量 SSH 认证重试仍失败，当前没有试点作业。 [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

- 2026-11-15（Asia/Shanghai）显式选择本地匹配身份后，SSH 公钥认证已恢复。服务器原 DDR 桥与配置 SHA-256 对齐。首作业 116477 的探针编译通过，留存因漏拷 `projection_math.cpp` 的启动失败。修订作业 116481 在 c96/node15 以 2×12 核进入模型回放。见 [作业追踪与验收命令](../../docs/handoffs/2026-11-15-issue-280-ddr-energy-pilot.md)。下一步核验两阶段和能耗结果，#280 已恢复进行中。

- 2026-11-15（Asia/Shanghai）Qwen3 双通道 DDR 试点通过。回放 116481 两模型步骤 `0:0`，原审计路径错误由 116496 补跑 `0:0`。短 Prefill 114.940 mJ/输入 token，Decode 两退休间 332.855 mJ/输出 token，FP32 top-1 两步通过。1,068 项回放输出及最终清单已验。下一步由 Melodydt 从同行 DDR 路由的单 P／三 P 对照继续。 [分窗结果与复现](../../work/Melodydt/280/QWEN3_DDR_PILOT.md)

- 2026-11-15（Asia/Shanghai）已提交同配置 P0 对照 116787。三 P 沿用 116481 验收结果，本地调度及 FFN DDR 写回／回读路径对账通过。c96,c64 两个单线程阶段各 1 核，排队中，待 Melodydt 核验 Slurm 终态、FP32 与逐窗能耗。 [提交与接续](../../docs/handoffs/2026-11-15-issue-280-p0-ab.md)

- 2026-11-15（Asia/Shanghai）S128 门级配对窗口 116809 复现原功耗，C380 正常和背压 116817 取得两份已验收 RTL FST，两个作业均 `COMPLETED 0:0`。C380 实际为 128-bit 普通端口；后续从门级关联、C639 和 512-bit 路径校准继续，P0 116787 仍排队。 [证据与恢复命令](../../work/Melodydt/280/GATE_ACTIVITY_01.md)

- 2026-11-15（Asia/Shanghai）Qwen3 同底座 P0／三 P 的 116787 终态 `COMPLETED 0:0`，两组 FP32 与层输出一致。三 P 短 Prefill／两退休 Decode 吞吐 +43.22%／+13.14%，DDR mJ/token −26.44%／−11.00%。C639 原生采样 116856 已运行，116858 等待前置终态对账。 [Qwen3 A/B](../../work/Melodydt/280/QWEN3_P0_AB.md) · [C639 接续](../../docs/handoffs/2026-11-15-issue-280-c639-activity.md)

- 2026-11-15（Asia/Shanghai）C639 四份波形由 116887 验收，两工况逐源同拍数据、时刻与完整 DDR／KV 对账通过。116893 在真实 FST 与 #200 布线 `local_s_base` 之间绑定 10 端口、273 位，C639 三路 RTL 层级已读回。下一步为匹配门级重放和 512-bit 路径标定。 [作业与结果](../../work/Melodydt/280/GATE_BINDING_02.md)

## 2026-11-15（Asia/Shanghai）C380 布线 SRAM 功耗

- 116908 在 c64/node9 用 8 核，65 秒 COMPLETED 0:0。布线 `local_s_base` 两种工况的全量读回、DDR 事务、周期和采样窗口与冻结基准一致。
- 116918 在 c64/node9 用 4 核，12 秒 COMPLETED 0:0。100 MHz 下，两个 20.48 µs 活动窗口的 128-bit SRAM 平均总功耗为 35.663966 和 34.209967 mW，标注 17,309 个引脚、143 个待核实。服务器日志、首次失败、结果 SHA-256 和接续命令已归档。 [C380 回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cdc1acdc83594a8240ace568a002af9fc41411fc/work/Melodydt/280/C380_ROUTED_POWER.md)
- 下一步补 C380 配对空闲并核实未标注引脚，随后绑定 C639 物理分块和标定真实 512-bit SRAM／PM。#280 进行中。PR #281 草稿，独立审查人待指定，登记待合并，Projects 缺配置待权责人核验。

## 2026-11-15（Asia/Shanghai）配对 SRAM 功耗与 C639 G32

- 116935、116939 均 COMPLETED 0:0。C380 普通 128-bit SRAM 同初态 20.48 µs 窗的正常／背压增量为 37.945404／8.170166 nJ。四窗相同的 143 个缺项均为输入天线二极管 A 引脚。
- 116938 COMPLETED 0:0。P SRAM 的 512-bit feeder 读以四 bank 同地址选通通过原生 RTL 和布线网表验证。母控及局控 PM 实际读写为 128-bit，上游 DDR 回包为 512-bit。真实宽写和控制链路物理标定待做。
- C639 G32 116937 在 c64/node9 以 12 核运行，正常工况 2,654,967 周期和两窗已读回。预检 116942 首窗标注覆盖 99.83%。四窗功耗 116943 以 `afterok:116937` 等待。M60 的当前快照等价及其他分块待验证。 [结果和 SHA-256](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/bc7ac38b5aaa8fa8d908ca6da999ed45ddbcbe76/work/Melodydt/280/PAIRED_SRAM_AND_C639.md) · [长作业接续](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/49ce662ad40155d02184ea731476aa29928755b6/docs/handoffs/2026-11-15-issue-280-c639-g32-power.md)
- #280 进行中，PR #281 草稿，独立审查人待指定。项目登记待合并，Projects 缺配置待维护者核验。

## 终态更新（Asia/Shanghai）

116937 和 116943 均 COMPLETED 0:0 并通过 SHA-256。四个 FFN 首 CALL 窗口的 G32 握手均为 0。补采 116950 从首次 G32 输入握手触发，两种工况各 64 次输入、64 次输出，功耗分别为 1.380787／1.377006 mW，DDR 前缀对账通过。作业 116950 在 c64/node12 用 2 核运行 4 分 59 秒并以 0:0 退出。后续从 M 与当前快照的等价证据、实际 512-bit SRAM／PM 写路径及控制链路功耗继续。 [终态、结果散列和复跑](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/524d0f1ae7e03a38114ae356bc4f4c8f81b0e253/work/Melodydt/280/C639_G32_POWER.md)

## 2026-11-15（Asia/Shanghai）C639 M 实际送布线源与同源实现

- 116953 完成 M60 与 C639 权重模块的合法事务对照，两版均接受 START，只有 M60 同拍接受 ALLOC。实际送布线的 M60 与 C639 均为单执行槽，已更新早期基于集成副本的比较。
- 116958 完成六个窗、三路 P 共 147,456 个周期的真实活动审计，3,472 次 ALLOC 和 3,423 次 START，未发现双 valid 同拍。116956 的 18 项 C639 同源叶块回归通过，Nangate45 映射 116956 已在 c64/node9 用 12 核、9 分 55 秒 COMPLETED 0:0，映射 406,959 个单元、723,919.532 µm²。首个布线参数指向错误目录，修订作业 116976 已在 c64/node9 12 核运行。 [回执与 SHA-256](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/8a58ca82721a50939f2e4e4e988d4a556b7a6e5a/work/Melodydt/280/C639_M_PHYSICAL.md) · [作业接续](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cfa5a4efba106992c47cf1ba537ec94e1268abe9/docs/handoffs/2026-11-15-issue-280-c639-m-physical.md)
- 后续需映射、布线、物理和门级验收、M 实际功耗，再补 512-bit 写与控制链路。#280 进行中，PR #281 草稿，独立审查人待指定。登记待合并，Projects 缺配置待维护者核验。

## 2026-11-16（Asia/Shanghai）C639 M 时序与功耗并行

- [#280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) / [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)。原 M 布线 116976 正常退出，300 MHz setup/hold 最差为 −1.122 ns/−53.4 ps。
- 117651 在 c64/node1 以 12 核重新布线并修复时序。117652 在 c64/node2 以 12 核运行 6 分 48 秒，COMPLETED 0:0，并核验全部结果散列。正常/背压的 Gate/Up、Down 共 12 窗，100 MHz 单路 101.523–102.765 mW，1,330 个边界引脚全标注，内部活动传播估算。
- Melodydt 读回 ECO 终态，验收 ECO 时序、DRC、电气与等价，再补门级活动、配对空闲和 512-bit SRAM／PM。源码、实际命令、日志和成功判据见 [并行作业交接](../../docs/handoffs/2026-11-16-issue-280-c639-m-eco-power.md)。登记待合并，Projects 待有权限维护者核验。

- 300 MHz 复测 117660 在 c64/node2、12 核、6 分 53 秒 `COMPLETED 0:0`。原 SDC 和 12 窗结果散列已复核。C639 原布线 M 单路 268.515–272.194 mW，每个 27.306667 µs 窗为 7.332–7.433 µJ，内部活动传播估算。ECO 117651 仍在执行。后续 M 标定沿用 300 MHz。 [300 MHz 回执](../../docs/handoffs/2026-11-16-issue-280-c639-m-eco-power.md#300-mhz-补测)

## 2026-11-16（Asia/Shanghai）推进三项 300 MHz 门级标定

- 117743 完成 512-bit 四 bank 读和 128-bit 单 bank 写的配对门级功耗，8.773／17.236 pJ/次。117749 完成 C380 和 G32 10 窗（含独立活跃窗），成果清单已验散列。
- 117729 在 c96/node15 编译 C639 三路布线 M 门级回放。117751 在 c96/node15 完成原始 LC PM RTL 综合并进入全局布线，后续回放 22 次写确认。M 时序 ECO 117651 因 hold 缓冲上限退出，尚无修复后网表。M 活跃／空闲和局控 PM 待验收。其余计算、母控、局控、DMA、互连和系统时钟继续绑定。
- 真实作业、复跑命令、回执和待办见 [三项标定接续](../../docs/handoffs/2026-11-16-issue-280-power-calibration-300.md)。 [#280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 进行中，[PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) 草稿。

- 局控 PM 配对功耗 117831（c64/node12、4 核、19 秒、COMPLETED 0:0）已核验。300 MHz 103 拍，活跃/空闲 30.888/30.803 mW，增量 1.339 pJ/写，直接标注 30.33%。接续 117729 和其余片上分项。 [PM 窗口与结果](../../docs/handoffs/2026-11-16-issue-280-power-calibration-300.md#局控-pm-配对功耗完成)

## 2026-11-16（Asia/Shanghai）并行续跑 M ECO 和四端点交换机

- 冻结 M 的提取路径复现 setup −1.122 ns、hold −53.4 ps，定位四个 hold 端点。117855 在 c64/node1 运行，已在四个 D 输入插入共 6 个缓冲并开始重新布线，GRT setup 仍约 −1.051 ns，117729 在 c96/node15 继续门级编译。
- 117841 验收四端点交换机 300 MHz 物理工件及空闲参考，117856 验收正常／背压实际活跃捕获，各 20 个握手周期、约 78.550 µW。空闲参考 78.328–78.398 µW。内部活动传播估算。
- 继续验收 M ECO 和门级回放，补其余片上活动。 [作业和接续](../../docs/handoffs/2026-11-16-issue-280-m-eco-switch-300.md)。

## 2026-11-16（Asia/Shanghai）归档 Qwen3 已覆盖功耗和 DMA 三窗补采

- [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 进行中，[PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) 草稿。已核验服务器清单。Qwen3 三窗已覆盖小计仅含双通道 DDR 芯片及 G32 活跃增量：短 Prefill 114.9417–114.9420 mJ/输入 token，首 token 332.7932–332.7934 mJ，两次退休间 332.8565–332.8567 mJ/输出 token。 [小计回执](../../docs/handoffs/2026-11-16-issue-280-qwen3-non-dma-subtotal.md)
- 117939（DMA 综合）和 117729（M 门级活动）已于 15:17:54 取消。117940（局控取指）在 hold 缓冲达上限处失败。117855（M ECO）在最终等价阶段异常退出，候选网表尚未验收。118132（三窗 DMA 事务）15:24 仍为 `PENDING (Priority)`，时限 `UNLIMITED`。封存包、归档 DDR 完成数与脚本散列通过；新回放等待调度。 [作业终态、追踪与验证](../../docs/handoffs/2026-11-16-issue-280-qwen3-dma-windows.md)
- Melodydt 后续核验 118132 三窗提交、接收、完成及边界积压，再补片上 DMA 功耗标定和 M 活动驻留。登记 PR #5 待合并，项目未配置专属看板，组织总览的 #280 条目待管理员核验。

## 2026-11-16（Asia/Shanghai）以无限时限重新提交 Qwen3 DMA 三窗

- [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) 进行中，[PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) 保持草稿。原提交封存包 SHA-256 和 Bash 语法通过，118207 已受理为 `PENDING (Priority)`，时限 `UNLIMITED`，节点待分配。118132 已于 15:34:35 取消。
- Melodydt 下一步读回 118207 的终态和结果，核验三窗 DMA 事务与冻结基线。登记 PR #5 待合并，组织 Projects 条目待具权限管理员核验。 [提交与追踪](../../docs/handoffs/2026-11-16-issue-280-qwen3-dma-windows.md)

## 2026-11-16（Asia/Shanghai）停止旧回放并切换仿真服务器

- 118207 于 15:57:00 在旧服务器取消。保留短 Prefill 与首 token 的局部核验，第二次退休及三窗总回执待补。
- BSCC-T6 登录和目标目录验证通过，`v6_384` 的 `--time=0` 提交预检通过。下一步由 Melodydt 迁移冻结工件并核验依赖，再提交新回放。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [迁移交接](../../docs/handoffs/2026-11-16-issue-280-bscc-t6.md)

## 2026-11-16（Asia/Shanghai）BSCC-T6 并行回放与 DMA 物理实现

- 38769328 完成新机 ORFS 运行环境。冻结 Qwen3 输入、原指令流和代表性 KV 镜像 SHA-256 已核验。
- 38769452 在 m3ca2408 并行回放 Prefill 和 Decode。38769386 与 38769388 已在计算节点进入共享读和阶段切换综合。38769390 完成 512-bit FFN 写回物理实现，300 MHz setup/hold 为 +368.527/+6.771 ps，详细布线 DRC 0。所有作业为 `UNLIMITED`。
- Melodydt 下一步读回三窗和两项读侧物理终态，再补齐 DMA 活动与功耗。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [作业和校验](../../docs/handoffs/2026-11-16-issue-280-bscc-t6-parallel.md)

## 2026-11-16（Asia/Shanghai）Qwen3 三窗验收及 DMA 标定准备

- 38769452 在 BSCC-T6 完成 Qwen3 三窗回放并通过对账。38770731 完成写回无握手参考，3.950–3.967 mW。38771074 完成残差写回网表与物理验收，300 MHz DRC 0，setup/hold 裕量 +989.615/+1.093 ps。
- 38772137 运行宽回包与活跃写回捕获，38772138 等待其通过后测活跃写回功耗。38769386、38769388 继续读侧综合。38771837 复现 M 的 300 MHz 原始时序违例，保留修复路径。三窗汇总脚本已对齐 DMA 事务、DDR＋G32 小计及 TLM 服务调用。
- Melodydt 继续验收波形、标定和读侧物理，再补整模型分项。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [作业与结果](../../docs/handoffs/2026-11-16-issue-280-bscc-t6-dma-power-prep.md)

## 2026-11-16（Asia/Shanghai）Qwen3 并行校准与写事务对账

- C639 宽波形补验收完成，6 份 FST 回包宽度为 6,144 bit。FFN 两个配对窗口各退休 128 笔写，估算 4.803/4.871 pJ/笔。38782602 选到未启用的残差 DDR 路径，依赖 38782604 取消。
- Qwen3 38782605 完成三窗 DDR／S128／M／PM 对账。每个 Decode 窗口的 8,960 笔 DDR 写分为 KV 3,584 与 FFN backing 5,376 笔。56 次残差由 U/SRAM 执行。完整 DMA 和片内总功耗仍待校准。
- M 缓冲器换档 setup 仅改善 4.754 ps。原路径 `word3[54] → a_ready` 已定位，EXEC 专用校验通过严格 lint 与组合 SAT 证明。Melodydt 后续进行功能回归和 300 MHz 重布线，读回 38769386／38769388 并做读侧校准，再测 KV／FFN backing 写侧与其余片内分项。
- [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [结果与恢复命令](../../docs/handoffs/2026-11-16-issue-280-bscc-t6-independent-calibration.md)。进行中，登记 PR #5 待合并，Projects 待具权限维护者核验。

## 2026-11-16（Asia/Shanghai）Qwen3 写侧与片内物理标定

- 38792114 的共享写侧完成 300 MHz 路由，38792400／38792563 验证 K、V 和 FFN 中间激活两工况各八笔写，配对估算 23.15–23.40 pJ/64 B。真实地址配确定性替代数据，待补负载敏感性。
- 38792815 通过 512-bit SRAM 四 bank、PM 拆拍、256-word U 残差。38793273 的 PM 桥 300 MHz 通过，1,664 字节真实页活跃增量 0.631–0.663 nJ/页。数组、互连与宽写尚待归属。
- M 候选 38792112 的两工况产品回归通过，物理作业 38792357 仍在映射。38793408 已为读 DMA 两种物理边界准备 12 份 VCD，Melodydt 等 38769386／38769388 交付网表与寄生后做最终读标定，再合并三窗。
- [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [本轮回执](../../docs/handoffs/2026-11-16-issue-280-bscc-t6-physical-calibration.md)。任务进行中，登记 PR #5 待合并，看板待管理员核验。

## 2026-11-16（Asia/Shanghai）真实写载荷与 PM／U 分项

- 38794389 真实写回通过三窗对账。38795264／38795265／38795266 使用真实载荷，配对范围 22.52–24.46 pJ/64 B，覆盖 K/V/FFN 三类及两种工况。
- 实际母控 1,616 字节页有 101 次 128-bit 写确认。局控阵列和 U 的字级控制、调度、算术已分别完成 300 MHz 标定。38795515 通过 SRAM 串行宽写和普通读对账，宏 TT 库和布线工件待从旧归档补齐。
- M 的 18 份波形及非 DMA 控制六窗活动已备齐。38792357 进入 CTS。两项原读综合和两项跳过 SHARE 的对照持续执行，五条功耗链按物理结果等待。Melodydt 后续核验映射、时序/DRC、门级功耗和重叠层级，再输出三窗整模型结果。
- [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [结果与恢复](../../docs/handoffs/2026-11-16-issue-280-bscc-t6-actual-payload-and-leaf-calibration.md)。任务进行中，项目登记待合并，看板待管理员核验。
