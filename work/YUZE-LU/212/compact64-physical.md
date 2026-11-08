# P/U 的 128 位与 64 位指令版本

后续覆盖更正：本文 U 数据为历史测量，未覆盖双 U 同时 SEND 和普通三源 FMA 入口。新 U 硬件及独立重验收见 [PR #221](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/221) 和 [修复索引](u-native-fix.json)。P 资格不变。

任务：[Issue #212](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/212)，交付：[PR #214](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/214)。负责人 YUZE-LU。

最终独立验收状态（2026-11-07 17:10 CST）：P_64/U_64 均通过原版完整 GDS DRC、原生与代表上层检查、最终网表回归及本地回收校验。[机器可读回执](compact64-acceptance.json)。工程验收完成，独立审查与 PR 合并待办，不自行合并。

| 版本 | 原生 setup / hold | 最终网表回归 | 原版完整 GDS DRC |
| --- | --- | --- | --- |
| P_64 | +86.461 / +7.498 ps | 9 次通过 | 0，99666 |
| U_64 | +100.376 / +8.670 ps | 60 次通过 | 0，99609 |

范围：Nangate45、TT 1.1 V、25 °C、300 MHz 的独立组底座工程检查。上层为 34/130 根、8 µm 的代表研究连接及 low/base/high 三档几何 RC，不能外推成九组顶层或其他 PVT 的验收。最终网表回归无 SDF；时序由最终提取 SPEF 下的 STA 单独判定。

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

## 实现与验收过程记录

以下保留各次检查时的过程状态；“拒收／运行中”指对应检查当时，最终资格以本文顶部及机器回执为准。

物理输入快照 `smoke-q03BOp/source.tar.gz`：SHA-256 `0137d4f467409e6da5aaf5c1a768a94ec47915161e17fe43e501bb5a939eda73`。99550_44/45 分别从新 RTL 开始生成 P_64/U_64，各分配 10 核。

最终需完成：独立新网表的 M1–M10 P&R，原版完整 GDS DRC、电气/PG/信号连通、原 TT 300 MHz setup/hold、代表上层接入的几何和三档 RC、最终网表三初态程序回归、六文件/源绑定及归档回收校验。**当前 RTL 通过不代表上述物理门已通过。** 后续在本节记录选定候选和实际数值。

首轮 P_64 提取结果 setup/hold 为 −23.198/−46.980 ps，并有 M 输入转换时间违例；U_64 为 +15.951/−35.317 ps。二者均拒收，未把布线完成当成验收完成。99570/99573 从各自新的 GRT 检查点修复延迟、驱动和几何；没有使用旧 128 版数据库。

首轮修复也说明，仅列前 120 个低裕量端点不足以指导修复。后续独立审计和三档上层 RC 均输出最多 20000 个端点，若达到上限则直接报错；原始 setup/hold、电气、频率及 IO 验收约束不变。诊断源码另封存为 `smoke-QXOtSB/source.tar.gz`，SHA-256 `639dc2751ecbdae5182fae69ce06d60f621a7611b146b8d95ac399ba21cf67da`。这项改变扩大修复报告，不缩减任何验收检查。

继续修复的工程源快照为 `smoke-9IjPXp/source.tar.gz`，SHA-256 `96e4658ff8196d50752731a7546961454e9c5fc6d55ded82990032bf06cde245`。原生审计扩展报告后，U 的负 hold 端点先从 465 个减到 30 个，再减到 1 个；P 第二轮也只剩一个负 hold 端点，但仍有一条 M 输入的 slew 违例。这些候选均未收为合格版本。

物理续跑可以设置独立的 setup 优化裕量、对真实 marker 指向的 M9/via9 接入添加临时布线避让，并对已足够大驱动但接收端仍超限的长线添加接收缓冲。新增单元进入最终网表、面积、PG、RC 和功能回归；叶宏不改。临时避让在最终提取前删除。setup 优化目标不改变原 300 MHz 验收 SDC。上层日志的电气分类也限定在实际电气报告段，setup/hold 仍独立判定，任一失败仍拒收。

登记沿用管理中心 PR #5 pending；缺少 `config/board.json`，看板 unverified、同步 pending。独立审查人待指定，不自合并。

### 最终候选复核记录

U 的 `smoke-9IjPXp/notches-99608` 在实际同网 M10 接入缺口补铜后重新流出 GDS、重新提取。99609 的原生 setup/hold 为 +100.376/+8.670 ps，电气、PG、研究上层几何通过；130 根代表接入三档 RC 均为 +134.399/+8.670 ps。原版完整 DRC 仍在运行，尚不能称物理验收通过。

99610_3、99611_3、99612_3、99613_3 分别对这份最终网表执行正常紧凑程序、偶数条指令、v1 镜像和两源 FMA。每套五场景三初态，共 60 次通过，网表 SHA-256 `c048d562ff8ae154edc0c3bc5fd74a84f5b086064d0bcd615a85c2f6e505ced2`。复核目录 `gate64-u-1Rhegg/{normal,even,legacy,fma}/fixture-3`。

P 的 `resume-99602` 原生 setup/hold 为 +91.359/+4.531 ps，M 输入的 slew 已修复，仍有新增小缓冲的电气违例及 M10 缺口，拒收。99625 继续从该版本的 GRT 检查点放大实际报告的驱动并修复低裕量端点，不重复运行会产生新小缓冲的提取后 setup 修复；99626 独立复核。原版验收 SDC 不变。

工程源码绑定：本地 `ea3ab01270fbfc940df00ea79a6cd50b11d2011a`，远端树等价 `cd102a2b7d7bab2af237138c26b4f907fc949b1e`，tree `360527800b1677db6f47e8d33d46a57acb38d20f`。初始实际综合快照 `smoke-q03BOp` 与续跑快照 `smoke-9IjPXp` 的 15 份 RTL/取指生成器/接口合同逐项与提交源核对一致（仅归一 CRLF）。初始快照早于 `control-variants.json` 身份索引，该索引不参与硬件生成；其差异单独记载，不混入硬件匹配结论。

[归档脚本](package-compact64.py) 仅在全部验收成功后执行，并独立检查完整 DRC、时序、电气、PG、上层几何及每份最终网表回归。交付包包含六文件、原规则、程序镜像、功能源、ECO 谱系和文件级 SHA-256，不依靠“作业退出成功”判断验收。

P 的 99625 已清除全部电气违例，但原生 hold 还剩两个负端点，继续拒收。99641 对原生及上层三档报告合并得到的 14 个低裕量端点加延迟，得到 +86.461/+7.498 ps；99665 只修复四处实际同网 M10 缺口后重新提取，裕量不变。99666 的几何预检为零项，电气和 PG 通过，随后进行三档 RC 与原版完整 DRC。最终候选为 `smoke-9IjPXp/notches-99665`，程序回归为 `gate64-p-zReWL1/{normal,even,legacy}/fixture-2`（99668_2/99669_2/99670_2）。完整 DRC 尚未结束。

P 的三个缺口分别在真实 S/G 端口处，补铜执行时检查实际网和端口绑定；第四处是 `datapath.g_other[30]` 自身绕线缺口。99658 导出附近父层 M10 几何，补铜矩形内无其他父层信号，99671 另外用原生 G 叶宏 GDS 核对该矩形内没有叶宏 M10。相邻网络位于矩形外，未把“附近有其他网络”误判为矩形内交叠，也未忽略实际交叠检查。

[本地回收校验](verify-compact64.py) 不执行解包文件，通过归档流逐项复核完整清单、六文件、原版规则 SHA-256、DRC XML、原生与三档 RC、最终网表哈希和全部回归日志。

U 的 99609 完成原版完整 GDS DRC，0 项，工具日志 `Total elapsed: 3602.850s`。最终交付是 `receipt-compact64-u-images/u64-accepted.tar.gz`，SHA-256 `48b2976aa5e322f8c55dc0019bd2f017c3b5394c12645ec82b2d83c2f3f2fa42`。99675 归档含 1480 个清单文件，已回收到本地并逐项通过校验。初包遗漏了实际执行的 `.mem` 镜像，已被上述新包替代；归档脚本冻结，运行中检查自身 SHA-256，避免脚本更新与打包并发造成源回执不一致。

P 的 99682 另外快速复核原规则中的 M10/VIA9 全部 10 条规则语句（含宽度、宽线间距和包围），0 项。这是补铜预检，不能替代仍在执行的完整原版 DRC。

## 最终交付与回收

P 的 99666 随后完成原版完整 GDS DRC，0 项，工具日志 `Total elapsed: 5927.120s`；独立 `check_native.py` 返回 `passed=true`。P 的 34 根代表接入 low/base/high 三档均为 setup/hold +102.353/+10.137 ps；U 的 130 根代表接入三档均为 +134.399/+8.670 ps。这是该短连接样例的结果，不外推长距离产品连线。

| 版本 | 最终归档（相对上述服务器根目录） | 清单文件数 | SHA-256 |
| --- | --- | --- | --- |
| P_64 | `receipt-compact64-p-images/p64-accepted.tar.gz` | 1122 | `13545e6ee575512edac07aebe553bf5d6c8666ccec3b040afde581cd4f35c390` |
| U_64 | `receipt-compact64-u-images/u64-accepted.tar.gz` | 1480 | `48b2976aa5e322f8c55dc0019bd2f017c3b5394c12645ec82b2d83c2f3f2fa42` |

归档作业为 99676（P）和 99675（U），各 2 核。两包已回收到 `C:\Users\wine10\AppData\Local\Codex\issue-212-compact64-acceptance`。本地分别运行 `verify-compact64.py <archive> <sha256>`，整体哈希及全部 2602 个清单文件一致，DRC XML 0、原生日志与结果 JSON、六文件、原版规则哈希、三档上层结果、9/60 次程序日志和实际母/局控 `.mem` 镜像版本/偶数边界均通过。校验还核对冻结归档脚本自身哈希与回执一致。

包内 `native/` 为最终 DEF/GDS/ODB/SDC/SPEF/V 及叶宏视图，`upper/` 为代表连接和 RC 检查，`gate/` 为本次最终网表的回归日志、程序镜像及功能源，`provenance/` 为源码归档、初始映射网表、控制生成源和不可变 ECO 谱系。`gate/*/staged` 中保留的旧参考报告只用于固定夹具溯源，不计入本次新增回归次数。基础功能宏仍独立，没有把控制分组导出成新的组合硬宏。

后续只剩独立代码审查与 PR 合并；登记沿用 management-hub PR #5 pending，看板缺 `config/board.json`，状态 unverified、同步 pending。Issue 进入 `in_review`，不标记 `done`，不自合并。
