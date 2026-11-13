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
