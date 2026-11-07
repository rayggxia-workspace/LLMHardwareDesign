# P/U 的 128 位与 64 位指令版本

任务：[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212)，交付：[PR #214](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/214)。负责人 YUZE-LU。

## 版本边界

现有两份合格底座命名为 `P_128`、`U_128`。既有 ODB、网表中的模块名仍为 `pu_p_controlled`、`pu_u_controlled`，原包及哈希不变，不修改旧数据库来追认新版本。

- P_128：`receipt-YSrgJh/p-accepted.tar.gz`，SHA-256 `5ea762aae33f422e97985156f1bcee445ef6b13146b37395255a00c819e7229f`。
- U_128：修复 E 操作数个数后的 `receipt-e-qualified-vatxlG/u-e-fixed-accepted.tar.gz`，SHA-256 `a1f35c0d6910bd006b8be8ef15bda563eb5ddc1c82312afab207e1bcf6ae2f3a`。旧的有缺陷 U 归档不能用于交付。

新 `P_64`、`U_64` 的物理顶层分别为 `pu_p_controlled_64`、`pu_u_controlled_64`。保留相同独立叶宏、服务适配器、数据端点、描述符、300 MHz 原始约束与叶宏布局基线。设置 `PU_INSTRUCTION_BITS=64` 选择新版本；默认 128 保持原流程。

64 指令取指和展开文件逐字取自 #180 的 `b54531b3359167668f8e696c97bd5882a7bee473`，SHA-256 `cf2316ebe7b6248b5bf297f508f2190dd80b7bcb1daa789cf3cd55b5fcba8c8c`。在 #195 固定原生服务控制核上移植版本检查、取指地址、奇偶半字选择、表偏移与非零尾部补齐检查。支持镜像 v2，保留 v1 兼容；内部译码寄存器和 PM 总线仍为 128 位。

**这是有界原生服务控制核的紧凑取指版本，不是 #180 最新控制核全部功能的移植。** 原先不支持的分支等指令仍不能宣称支持。母控仿真参考和另一端局控也使用相同取指改动，实际读取紧凑镜像，没有在程序存储器中先展开为 128 位。新旧版本不能互换物理资格。

## 已完成的功能验证

远程所有路径以 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-212-pu-leaf-base/` 为根。

| 作业 | 输入和结果 |
| --- | --- |
| 99548_2/3 | `smoke-q03BOp`：P 三初态 3 次、U 五场景三初态 15 次紧凑程序通过 |
| 99552_2/3 | `smoke-rtbaUF`：偶数条指令镜像，P 3 次、U 15 次通过 |
| 99554_3 | `replay64-fma-sRApxa`：U 的两源 FMA，含 S[0]=5 的反例，五场景三初态 15 次通过 |
| 99555_2/3 | `replay64-legacy-vaXQhV`：64 取指硬件执行旧 v1 镜像，P 3 次、U 15 次通过 |
| 99556 | `fetch64-test-gf829h`：真实 SV 取指测试覆盖高低半字、奇偶尾部、非零尾部、256 条边界、v1 兼容、非法版本拒绝 |

本地另外用上述 #180 固定版本的 `compact.encode` 独立核对母/局控 1/2/3/4/255/256 条指令共 12 组镜像，紧凑字节逐字一致，描述符字节及修正后的表地址一致。

## 物理验收进行中

物理输入快照 `smoke-q03BOp/source.tar.gz`：SHA-256 `0137d4f467409e6da5aaf5c1a768a94ec47915161e17fe43e501bb5a939eda73`。99550_44/45 分别从新 RTL 开始生成 P_64/U_64，各分配 10 核。

最终需完成：独立新网表的 M1–M10 P&R，原版完整 GDS DRC、电气/PG/信号连通、原 TT 300 MHz setup/hold、代表上层接入的几何和三档 RC、最终网表三初态程序回归、六文件/源绑定及归档回收校验。**当前 RTL 通过不代表上述物理门已通过。** 后续在本节记录选定候选和实际数值。

首轮 P_64 提取结果 setup/hold 为 −23.198/−46.980 ps，并有 M 输入转换时间违例；U_64 为 +15.951/−35.317 ps。二者均拒收，未把布线完成当成验收完成。99570/99573 从各自新的 GRT 检查点修复延迟、驱动和几何；没有使用旧 128 版数据库。

首轮修复也说明，仅列前 120 个低裕量端点不足以指导修复。后续独立审计和三档上层 RC 均输出最多 20000 个端点，若达到上限则直接报错；原始 setup/hold、电气、频率及 IO 验收约束不变。诊断源码另封存为 `smoke-QXOtSB/source.tar.gz`，SHA-256 `639dc2751ecbdae5182fae69ce06d60f621a7611b146b8d95ac399ba21cf67da`。这项改变扩大修复报告，不缩减任何验收检查。

登记沿用管理中心 PR #5 pending；缺少 `config/board.json`，看板 unverified、同步 pending。独立审查人待指定，不自合并。
