# Melodydt 的进度

## 2026-11-13（Asia/Shanghai）Qwen2.5-3B 整机评估

- [Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 由 Melodydt 负责，为 #234 提供独立评估证据。评估分支 `task/265-qwen3b-system-evaluation` 继承 PR #260 的 `05225f51ee5367f8ca19793c45485dc5a90cc81c`。
- 已锁定六份历史输入、对应参考回执、9 个模型和 tokenizer 文件、旧 S16 校准与 434 项权重索引。评估清单把旧九组资源与 #250 的 W8A16 候选分别绑定。已准备只读提交前检查。
- 本地管理结构通过。两套真实清单均因缺服务器与部署证据返回 2。合成工件检查验证了有效散列和镜像，并拒绝占位散列、错误散列、越界路径、重复索引和缺失镜像。
- 下一步从可信渠道核对 SSH 主机密钥，验明获授权的共享 checkpoint、Python、SIF 和图文件，补实际编译器／RTL、控制镜像与硬件参数，再运行服务器预检。本阶段无新 Slurm 作业。完整步骤见[运行交接](../../docs/handoffs/2026-11-13-issue-265-input-freeze.md)。
- 项目登记 PR #5 待合并。Projects 配置缺失，条目和同步待具权限维护者处理。独立审查人待指定。
### 服务器只读核验

- ED25519 主机指纹匹配，已登录 `mgt01`。三个历史作业终态及两份组件回执与 #260 一致。
- 实物核验通过 12 份参考文件、434 份旧权重、校准清单、九组资源、四份 ONNX 与历史共享 SIF。四份 ONNX 均无外部数据引用。
- 继续落实获授权的共享 checkpoint、完整 Python 环境和实际整机部署。本地预检仍返回 2，服务器完整预检待执行，未提交新作业。详见[运行交接](../../docs/handoffs/2026-11-13-issue-265-input-freeze.md#2026-11-13-服务器只读核验)。

### 两个 P512 样本的 FP32 参考验证

- 2026-11-13（Asia/Shanghai），[PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266)。从官方固定 revision 在本人任务目录落地 checkpoint，9 个模型工件的 SHA-256 均匹配。任务专用 Python 3.10.12 已对齐历史核心包，`pip check` 通过。
- Slurm 107396 `zny-qwenref` 以 `e6e01fa46663101179a8679afc6deb45a638c93d` 在 c64/node2 上运行，8 核，74 秒，`COMPLETED 0:0`。两条 P512 的首两 token 与冻结参考相符，实际 P512 ONNX 输出已执行。参考回执和依赖清单已验散列。
- 已修复冻结字段可被覆盖、重复键和控制镜像缺实际来源及容量验证。下一步继续复现原整数偏差并完成整机平台绑定。整机 D128 和吞吐待验证。恢复及追踪入口见[交接](../../docs/handoffs/2026-11-13-issue-265-input-freeze.md#2026-11-13-参考环境验证)。

## 2026-11-13 15:29（Asia/Shanghai，UTC+08:00）快速周期评估

- [Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 和[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) 由 Melodydt 继续推进，沿用 `task/265-qwen3b-system-evaluation`。当前范围为已部署指令与拓扑驱动的快速周期和 DDR 吞吐估算；并行分支负责全程 decode 吞吐仿真。
- 已完成[方案](../../docs/decisions/0265-instruction-driven-cycle-estimation.md)与[首轮控制输入审计](../../work/Melodydt/265/README.md#快速周期评估)。两份历史归档的 MC/LC 镜像及描述符一致，恢复 192 次调用及 64 个 WAIT。12 份历史日志验证两种压力模式和三种 SRAM 初态；同模式下提前发起 EXEC 的两个作业分别相差 10,288 和 6,719 周期。
- 已通过 Python 3.7 实物审计、7 个无效输入检查及项目管理检查。服务器本轮只读获取历史归档。本轮未提交新作业，未测整机周期或吞吐。
- 下一步由 Melodydt 从具有完整端点和时间戳的短 RTL 用例冻结服务参数，先实现片上事件模型，再接入有限队列的 DDR。后续需从并行分支绑定同版本部署拓扑、DMA 物理地址与 DDR 配置，以及独立留出窗口。#265 进行中，PR 保持草稿，登记待合并，Projects 待核验和同步。

## 2026-11-13 16:00（Asia/Shanghai，UTC+08:00）片上周期模型

- [#265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 与[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) 增加[单时钟事件原型](../../project/experiments/instruction_cycle/README.md)，显式建模队首发射、算子占用与发起间隔、共享端口、仲裁、接收端容量及 ACK 背压。已修正同拍争用曾由操作 ID 隐式决定的排序，现按端口优先级与端口内发起顺序。8 个本地用例和项目管理检查通过。
- Slurm 107481 在第一组回执后因测试台结束路径触发超时，修正后 107488 在 c64/node3 用 4 核 6 秒完成（0:0）。真实 S 仲裁 RTL 的 54 个事件和历史作业 100343 的 27 笔 COPY 写接受到提交/释放逐拍一致。[作业、路径及散列](../../work/Melodydt/265/onchip-rtl-107488.json)
- 下一步由 Melodydt 绑定实际 MC/LC 二进制到完整的短程拓扑和分阶段算子/存储服务，逐指令对账。DDR 及 Qwen2.5-3B 整机 tokens/s 仍待评估。#265 进行中，PR 草稿，登记待合并，Projects 待核验与同步。

## 2026-11-13 16:23（Asia/Shanghai，UTC+08:00）A2 真实控制镜像到退休

- [Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 与[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) 接入 A2 实际 MC/LC 二进制、独立 PM、四 bank S feeder、M 与窄口写回。Slurm 107535 在 c64/node3 用 4 核 9 秒完成（0:0），5 次运行从 START 到 RESULT 的 224 个事件全部逐拍一致，含未用于推导的 151/154 拍留出场景。[作业、版本及散列](../../work/Melodydt/265/a2-rtl-107535.json)
- 复核收紧母控 token 范围、非整数周期/容量/地址和逆序或缺任务的回执。13 项本地测试、旧作业 97305 的 81 个事件、107488 的 54 个事件、历史 COPY 的 27 笔及管理检查通过。
- 下一步由 Melodydt 用实际双 U_64 镜像做多目标发起到退休验证，再扩展宽窄口竞争和 DMA/DDR。A2 的 host 窄口在运行窗保持空闲。整机吞吐和同机加速比待测，#265 进行中，PR 保持草稿，登记待合并，Projects 待核验和同步。

## 2026-11-13 17:28（Asia/Shanghai，UTC+08:00）双 U_64 控制到退休

- [Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 与[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) 已绑定三份真实 Compact V2 镜像、双 LC、SRAM PM、E 算子、窄口仲裁与跨 Block 写入/ACK。作业 107643 在 c64/node3 用 4 核 10 秒完成（0:0），正常、原背压、留出背压分别 351/490/470 拍，630 个事件逐拍一致。[运行及散列](../../work/Melodydt/265/dual-u-rtl-107643.json)
- 已对账 100343 三份完整历史日志共 402 个事件。修复空闲跳步跳过 WAIT 释放、LC token 绑定和日志边界校验。16 项单测、管理检查、386 组跳步与逐拍等价检查通过。
- 三组新 RTL 未观测到同拍 S 争用，定向仲裁仍沿用 107488。下一步由 Melodydt 用有限队列 DMA/DDR 短例验证请求身份、返回、写可见性、背压和排空，并将其接入同一时间轴。Qwen2.5-3B 整机吞吐待估，Issue 进行中，PR 草稿，登记待合并，Projects 待核验及同步。

## 2026-11-13 17:55（Asia/Shanghai，UTC+08:00）有限队列 DMA／DDR

- [Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 与[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) 将有限队列 DMA 的回包和 FENCE 接入通用片上时间轴。修复同 Block 的快 FENCE 越过慢写，增加同址差异载荷、队列、事务身份和依赖回归。28 项本地单测通过。
- 107669 在 c64/node3 完成（4 核，12 秒，0:0），冻结 64 B DMA RTL 的 24 项排空证据匹配。107683 及修复后 107695 在 c64/node3 完成，实时读桥复现同址读回包第 50／78 拍，片上联动短例第 105 拍完成。有限参考后端验证写可见，实时 DRAMsim3 拒绝写回调冒充提交。[运行与散列](../../work/Melodydt/265/dma-ddr-receipts.json)
- 下一步由 Melodydt 绑定实际 DDR 的写提交和排空、片上/DDR 时钟转换及 CDC，再接入真实 Qwen DMA 地址与 KV。尚未评估整机 tokens/s 或模型加速比。#265 进行中，PR 草稿，登记待合并，Projects 待核验与同步。

## 2026-11-13 18:13（Asia/Shanghai，UTC+08:00）DDR 写数据结束与跨时钟

- [Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 与[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) 在独立 DRAMsim3 统一队列候选中核对实际 WR 发出和写数据结束。等周期 stock 读回归保持第 50／78 tick，联动 105 拍。300 MHz 与 630 ps 的请求/响应采样、有限 FIFO 和 FENCE 已接入同一时间轴。
- Slurm 107731 在 c64/node3 完成（4 核，15 秒，0:0）。常规与留出共独立对照 22 RD／10 WR，验证不同的新旧数据、同址顺序、FIFO 信用和排空。两个短例分别 50／128 拍。30 项本地单测、独立命令追踪复核和 6 个篡改负例通过。[运行与散列](../../work/Melodydt/265/dram-write-cdc-107731.json)
- 下一步由 Melodydt 绑定同一部署的实际 MC/LC 镜像、物理 DMA 地址及 KV、时钟/CDC 与写完成协议，先对账单层和跨层短窗。现有 300 MHz/统一队列为实验候选，整机 tokens/s 待估，#265 进行中，PR 草稿，登记待合并，Projects 待核验与同步。

## 2026-11-13 19:52（Asia/Shanghai，UTC+08:00）Qwen 原生短窗 DDR 与 KV

- [#265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 与[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) 使用 case 2 的 106093 QKV 与 105530 跨层 RMS 原生归档，验证 17 页 MC、实际 LC、物理地址和已提交载荷。107921 首次执行因描述符重复计数退出，修正后 107931 在 c64/node3 使用 3 核、1 分 33 秒完成（0:0）。四组共 3,165,652 个 DDR 回调完全匹配，输出 SHA-256 全部核验。[实验回执](../../work/Melodydt/265/qwen-native-ddr-107931.json)
- case 2、3 各核验 4 份 step 11→12 原始 S32 K/V 数组及 step 11–13 layer 0/1 的 SSA 依赖。项目结构与现有 30 项本地单测通过。已识别 106093 测试台和 DDR 桥的时钟比例差异；105530 具备同步时钟与整个窗口计数，层间边界时标待补。
- Melodydt 接下来用 105530 的镜像、描述符、路由及起始状态独立生成 DMA 发起／接受时刻，补层间标记，预留 105572 作完整上下文验证。#265 进行中，整机 tokens/s 与同机加速比待估，PR 保持草稿，登记待合并，Projects 待核验和同步。

## 2026-11-13 21:53（Asia/Shanghai，UTC+08:00）105530 周期预测与跨层探针

- [#265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 和[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) 独立展开 8 页、393 次服务和 265 组 WAIT。108173 两种模式各核对 1,318,877 笔普通读地址、128 笔 FFN 激活读和 736 笔写地址及 tag；108184 每模式逐事件匹配首行到首次 MC/LC 镜像读的 267 笔事务。首笔 DDR 接受使用冻结测试台的启动延迟，随后由模型推导。
- 108159 的两种原生 RTL 均通过，Slurm 因散列清单分隔符退出 1:0。108208 仅复核原产物，在 c64/node3 用 1 核 2 秒完成（0:0）。跨层观测为 32,383／32,353 拍，核对 8 份 DDR/KV 散列及两组 1,652 条标记。已通过本地 30 项测试及项目结构检查。[证据与恢复](../../work/Melodydt/265/qwen-105530-cycle-receipt.json)
- 下一步由 Melodydt 接续母控 PM 装载、校验与发射，预测第 1 页全部 DMA，随后验证第 5 页三 P 共享资源；完整上下文 105572 保留作留出。整窗周期、整机 tokens/s 和同机加速比待估，#265 进行中，PR 草稿，登记待合并，Projects 待核验和同步。

## 2026-11-13 22:28（Asia/Shanghai，UTC+08:00）首个指令页与 Q 投影权重

- Melodydt 在 [#265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 的 `task/265-qwen3b-system-evaluation` 提交 MC 读回/CRC、MC/LC 发射、两次 DRL1 及首个 Q 权重记录的周期模型。[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266)
- 108297、108312、108366 均在 c64/node3 用 2 核、6 秒完成（0:0）。108366 每模式精确匹配 306 笔 DDR 读的 1,224 个事件和 11 个控制标记。源码、预测及输出散列通过，项目结构和本地 30 项单测通过。[源码、日志、命令及回执](../../work/Melodydt/265/qwen-105530-first-page-108366.json)
- 108312 和 108366 每模式核对 123 次 WAIT、246 个后续描述符接收边沿及页提交，输入为 RTL 服务退休边沿。下一步由 Melodydt 在同一 105530 冻结窗口继续到 Q 的首个 EXEC 和退休，补 W 双 bank、A COPY/LOAD、M EXEC 的重叠及多请求竞争。后续再验证三 P 并发、跨层和留出 105572。整机 tokens/s 与同机加速比待估。
- #265 进行中，PR 草稿，独立审查人待指定。登记 PR #5 待合并。仓库缺 `config/board.json`，Projects 条目和同步待具权限的维护者处理。

## 2026-11-14（Asia/Shanghai，UTC+08:00）整机 TLM 对照与第二条 Q 权重

- [#265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 由 Melodydt 在 `task/265-qwen3b-system-evaluation` 推进。[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) 固定 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 的 107361 为短程整机 TLM 对照。只读重跑原审计，输出 SHA-256 与归档一致。582 页核对通过，第二步退休间隔 1,045.096187442 ms、0.956849725428261 tok/s，Attention 页占 67.8%。[对照回执](../../work/Melodydt/265/qwen-tlm-decode-107361.json)
- 同一 105530 原生 RTL 窗口已推进到首个 Q 投影的两条权重。108930 在 c64/node3 用 2 核、6 秒完成（0:0），两种模式各匹配 323 笔 DDR 读、1,292 个事件和 11 个控制标记。源码和输出 SHA-256、管理检查和 30 项单测通过。[Slurm 回执](../../work/Melodydt/265/qwen-105530-two-weights-108930.json)
- 下一步由 Melodydt 在首个 Q 投影中建模 A COPY/LOAD、双 bank 就绪和首对 M EXEC，以第三条权重首拍作可观测边界。服务退休、三 P 并发、跨层和完整上下文 105572 留出仍待验证。整机预测误差和同机加速比待匹配 107361 的部署与时钟后实测。
- #265 进行中，PR 草稿，独立审查人待指定。登记 PR #5 待合并。仓库缺 `config/board.json`，Projects 条目与同步待具权限维护者处理。

## 2026-11-14（Asia/Shanghai，UTC+08:00）首对 Q EXEC 与第三条权重

- Melodydt 在 [#265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 的 `task/265-qwen3b-system-evaluation` 接通同 P COPY、A LOAD、双权重 bank 就绪及首对 M EXEC。110583 在 c96/node15 两核 15 秒完成（0:0），两种模式各匹配 340 笔 DDR 读、1,360 个事件和 11 个控制标记。[草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266)
- 110589 在编译前因集群 Python 3.6 参数不兼容退出，110596 在内部审计因 RF EOP 探针字段错误退出。修正后 110601 在 c64/node2 用 8 核 2 分 20 秒完成（0:0），两种模式各匹配 114 个内部边沿和 1,292 个冻结 DDR 事件。源与输出散列、30 项单测及项目结构检查通过。[源码、命令、日志及回执](../../work/Melodydt/265/qwen-105530-projection-pair-110583.json)
- 107361 的 0.9568497254 tok/s 仍作单拍 KV 短程整机 TLM 对照。PR #260 的 108308 另给出同 8-beat KV 配置下 128／512-bit 的 1.20653／2.09091 tok/s。下一步由 Melodydt 建模 W bank 复用、后续记录重叠、下一 K 激活窗口及完整 Q 服务退休。跨页、多 P、105572 留出和整机预测误差待验证。
- Issue 继续进行中，PR 草稿，独立审查人待指定。项目登记 PR #5 待合并，仓库缺 `config/board.json`，Projects 待具权限维护者核验和同步。

## 2026-11-14（Asia/Shanghai，UTC+08:00）整机 Decode 快速估算

- Melodydt [#265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 固定 107361 的 128-bit SRAM、单拍 KV、3,334 ps 核时钟与双通道 630 ps DDR。新估算为 127 间隔 143.489733463362 s、0.8850807437 tok/s。第二步未参与拟合，吞吐误差 +0.05633%。几何上界 1.3317315170 tok/s。仅短程对照和结构覆盖，正式 P512/D128 时序验收待完成。[回执](../../work/Melodydt/265/qwen-decode-evaluation-107361.json)
- 110646、110675、110682、110720 原生 RTL 前缀全部与实时 DRAMsim3 匹配，首个 Q 退休及首个 KV 写提交均通过。105572 留出模式 0 逐事件通过，模式 1 首条权重接收晚五拍。完整原生 QKV 页与后续 Attention 正在验证。
- 110649/110695 在 c64/node2 的九页同机对照为 170/70/60 s。110666 的两步整机回放在 c64/node10 已开始，随 [草稿 PR #266](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/266) 连续跟踪。保持 Issue 进行中，独立审查人待指定。项目登记 PR #5 待合并；仓库缺 `config/board.json`，Projects 由具权限维护者核验。
