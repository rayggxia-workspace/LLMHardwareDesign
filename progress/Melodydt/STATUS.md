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
