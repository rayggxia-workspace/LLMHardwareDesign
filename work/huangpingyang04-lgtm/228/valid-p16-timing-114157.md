# 算法 2 旧 P16 VALID 路径的分段延迟

Slurm 作业 `114157` 复用作业 `111831` 的历史布线和 STA 输入，在旧 P16 底座上重跑 [PR #259 的 VALID 对照](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/77f840a1992e19a89c46ebca5458268f65b50b3a/work/YUZE-LU/228/fixed-base-validation.md)。两组均为 300 MHz、高研究 RC，使用同一 ORFS 容器内的 OpenROAD/OpenSTA。作业耗时 3 分 44 秒，终态 `COMPLETED`，退出码 `0:0`。

## 测量结果

| 方案或分段 | 引脚 | M11/M12 线长（µm） | OpenSTA 增量延迟（ps） | 完整路径 setup 裕量（ps） |
| --- | --- | ---: | ---: | ---: |
| 直连 | `P0/eco_relay_12/Z` → `P0/hold40266/A` | 4800 | 645.236 | −238.876 |
| 中继前段 | `P0/eco_relay_12/Z` → `P0/upper_valid_repeater/A` | 2416 | 327.832 | +33.879（完整中继路径） |
| 中继单元 `BUF_X32` | `P0/upper_valid_repeater/A` → `P0/upper_valid_repeater/Z` | — | 134.243 | — |
| 中继后段 | `P0/upper_valid_repeater/Z` → `P0/hold40266/A` | 2400 | 36.624 | — |

线长沿用 PR #259 的上层布线统计。引脚到引脚延迟取 OpenSTA 报告的接收引脚增量，包含上下层接入及所用 RC 模型。中继单元延迟取 `A → Z` 增量。Setup 裕量来自同一条完整寄存器时序路径。

## 复核与证据

作业复用 `111831` 的高 RC 直连和中继 Tcl，使用 `report_checks` 的 `full_clock_expanded` 格式与 `input_pins` 字段显示逐引脚增量。OpenSTA 提示 `nets` 为未知显示字段，所需引脚已按 `input_pins` 输出。原日志保留历史 SPEF 未连注释警告。

| 原始工件 | SHA-256 |
| --- | --- |
| `111831` 输入 `direct-high.verified.tcl` | `1bd7f59520aed623f869a5d5cc448da037723e4fd3606194383223f0fcdf1cac` |
| `111831` 输入 `relay-high.verified.tcl` | `5652b62c485d0e00f09c1f1e97fd34ea604b36e2b3f7a5e3b52ea6c1ab38ee61` |
| `114157` 输出 `direct.log` | `8ed02a6c9e63d07465aa849c37291ea9e6ac45a16f48a0a9024656a1ac72e4b0` |
| `114157` 输出 `relay.log` | `7620202de7ec57b8434052ec57779373784144d4eaa3dbccb0daed77a6b13655` |

原始作业和日志保存在项目服务器的 `hpy-valid271-audit-vxAiyX` 作业目录。上述结果适用于旧 P16 和本次研究 RC 条件。[PR #271 的新排布](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/271)需取得同版冻结视图的 VALID 端点和实体中继绑定后单独测量。
