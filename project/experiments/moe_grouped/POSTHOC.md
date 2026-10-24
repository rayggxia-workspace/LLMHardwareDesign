# Granite 完整整数 MoE 链：原八条件事后分析（Issue74）

日期：2026-10-24。任务：[Issue74](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74)，交付 [PR75](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/75) 待审查。

当前证据不支持把 mid 从 Q12 改为 Q20 作为下一优先实验。原八条件在最终 Q12 舍入之前已有显著误差；最终 Q12 舍入能量很小，后续 A8 编码量程也已用上。此次只分析原产物，不改变数值合同、校准参数、样本或冻结链，不新增实验。

## 运行与来源

- 实际服务器 Slurm 作业 **90308**：`COMPLETED`，调度记录约 3 秒；producer manifest 实测分析耗时 `2.001430925913155` 秒。
- 服务器结果目录：`/public/home/yuzelu/RuizhiLiang/issue74-moe-grouped-20261024/granite-posthoc01/`。
- 报告：上述目录 `report.json`；本机只读 JSON 副本：`D:/Projects/Codex/moe-grouped-20261024-01/metadata/granite-posthoc01/report.json`。
- 报告状态：`POSTHOC_COMPLETE_NOT_RUNTIME_OR_QUALITY_ACCEPTANCE`。
- 固定模型 revision：`a02780686e08a03fe0d2679a293b5c74a90efa89`。
- 服务器分析 source commit：`53840a8c7b8b5d9bab336a16725f2d5bdbc139cb`。本工具原交付 commit：`03cab884c13d5c0e5c92bd028d1c35f378f71601`。
- [posthoc_granite.py](posthoc_granite.py) SHA-256：`f113910cc03a094cf51ba0b81e25059112a713742a9c5a5ae11cb04513c86419`。
- 原八条件 chain source commit 均为 `dbe563db7311818b9a32420f1c78c1642367bea7`，`granite_chain.py` SHA-256 均为 `2211d213e55b29ce35c38f9e95e2d48c7fa12d3c743c23b933ec1777c17a2bd5`。
- 编译输入 `granite-compiled01/manifest.json` SHA-256：`7c92bd403e46538749c9eb5cb7679248f421ad5ced3f72546adffde9b1f517c5`。所有原运行目录、manifest/runtime/diagnostic/report SHA 与 source binding 均保存在报告 `inputs` 中。
- `report.json`：`2,838,632` 字节，SHA-256 `e7a57529484de5c3cb100da46a394d07a5b19e619b863d6e9b59a6c55fb3e289`；此处核对本机 JSON 副本与 manifest 一致。
- `witnesses.npz`：服务器 manifest 登记 `581,633` 字节，SHA-256 `b3e2ab7b1fcf10a221edfd1d912eb3d255b54a7d53432e3c65242c3882eb27d3`。原始实际张量及此 NPZ 未在本机加载或重算。

服务器运行方式（binding 需同时绑定该阶段 commit 与上述 `posthoc_granite_sha256`，输出目录必须新建）：

```text
python project/experiments/moe_grouped/posthoc_granite.py --compiled GRANITE_COMPILED01 --result ORIGINAL_RUN_1 --result ORIGINAL_RUN_2 --result ORIGINAL_RUN_3 --result ORIGINAL_RUN_4 --result ORIGINAL_RUN_5 --result ORIGINAL_RUN_6 --result ORIGINAL_RUN_7 --result ORIGINAL_RUN_8 --binding PHASE.json --out NEW_OUT
```

## 比较口径

范围固定为 layer0 / layer13 × router R8 / R16 × calibration / evaluation，共八条件。每条件 72 token（按协议位置标记为 prefill64 / decode8）、每 token 全部八条真实选中 expert 路径，总计 576 路径。这里是对捕获 row 的离线冻结 cut 重放，后八位置的分组不代表本脚本执行了真实 cached-decode 调度，也不能用于跨 token 免费拼 batch 的延迟结论。expert-mid/down 仅比较同一 token 的相同 expert ID，不按路由排名硬配；未匹配路径不计入这些误差及分母。所有路径仍参加独立的 Q24→Q12 舍入和 Q12→A8 编码诊断。

R16 指实际全路由矩阵的九个 S8 digit dot 与宽重组，不是固定 ID 的 oracle；两者 expert gate/up/down 均保持原 W8A8 / 完整 K INT32 累加合同。R16 的真实硬件成本仍须独立计价。

这里 native/model64 指已接收的显式 eager 模型参考；framework 的 norm 统计、RoPE 与 attention softmax 内部 FP32 cast 仍保留，不声称逐算子全 FP64。

以下误差均为本层冻结 cut 的局部诊断。L2 表示 `||actual-reference||2 / ||reference||2`；表中以百分数显示。SSE 单位为解码后的实际浮点值平方和。Q12 最终 RNE 的参考是相同整数操作数所产生的 Q24 product，不是原生 FP64。额外 A8 损失的参考是当前 Q12 mid，而非原生 FP64。

令 `u=mid_product64/2^24`、`q=expert_mid_q12/2^12`、`r=native_mid`：`e_up=u-r`，`e_round=q-u`，`e_total=q-r`，因此 `SSE_total=SSE_up+SSE_round+2·dot(e_up,e_round)`。上游项同时包含输入 norm、gate/up W8A8/RQ、SiLU LUT 等影响，不能单独归给其中某一项。round/total 能量比也不是因果贡献比例；完整交叉项保存在 JSON。

## 全 72 token：最终 Q12 舍入不是主导误差

| 条件 | 匹配路径/576 | mid 前 RNE L2 % | mid Q12 L2 % | down L2 % | Q12 RNE SSE | RNE SSE / total mid SSE | 额外 A8 L2 % |
|---|---:|---:|---:|---:|---:|---:|---:|
| L0 R8 calibration | 565 | 11.131444 | 11.131444 | 11.256808 | 1.42407219e-3 | 3.15764744e-8 | 3.178082 |
| L0 R8 evaluation | 561 | 11.027986 | 11.027992 | 11.247294 | 1.41929608e-3 | 3.75070159e-8 | 3.246292 |
| L0 R16 calibration | 576 | 11.141319 | 11.141319 | 11.262914 | 1.45187691e-3 | 3.20077867e-8 | 3.181572 |
| L0 R16 evaluation | 576 | 11.042203 | 11.042209 | 11.258051 | 1.45694248e-3 | 3.81399200e-8 | 3.240050 |
| L13 R8 calibration | 569 | 5.231003 | 5.231025 | 5.684255 | 1.44677609e-3 | 3.11739332e-6 | 3.198154 |
| L13 R8 evaluation | 573 | 5.129198 | 5.129207 | 5.689305 | 1.45196848e-3 | 2.61897398e-6 | 3.176565 |
| L13 R16 calibration | 575 | 5.224793 | 5.224815 | 5.680930 | 1.46253690e-3 | 3.13637158e-6 | 3.192258 |
| L13 R16 evaluation | 576 | 5.125480 | 5.125489 | 5.687442 | 1.45948032e-3 | 2.62463762e-6 | 3.171055 |

| 条件 | mid Q12 vs native 最大绝对误差 | down vs native 最大绝对误差 | 同操作数 Q12 RNE 最大绝对误差 | 额外 A8 最大绝对误差 |
|---|---:|---:|---:|---:|
| L0 R8 calibration | 5.692775561 | 1.502804232 | 0.0001220703125 | 0.999755859 |
| L0 R8 evaluation | 4.368090474 | 1.245342058 | 0.0001220703125 | 1.000000000 |
| L0 R16 calibration | 5.692775561 | 1.502804232 | 0.0001220703125 | 0.999755859 |
| L0 R16 evaluation | 4.368090474 | 1.245342058 | 0.0001220703125 | 1.000000000 |
| L13 R8 calibration | 15.958755956 | 4.087539360 | 0.0001220703125 | 0.467041016 |
| L13 R8 evaluation | 18.474020311 | 4.824651939 | 0.0001220703125 | 0.467041016 |
| L13 R16 calibration | 15.958755956 | 4.087539360 | 0.0001220703125 | 0.467041016 |
| L13 R16 evaluation | 18.474020311 | 4.824651939 | 0.0001220703125 | 0.467041016 |

例如 L0/R16/evaluation：native→current product SSE 为 `38199.89500523936`，最终 Q12 RNE SSE 仅 `0.001456942476707468`，交叉项为 `0.03883595621584337`，总 SSE 为 `38199.935298138065`。这支持“主要误差已发生在最后 Q12 RNE 之前”；不能从该恒等式推导替代格式对 down 或 nextnorm 的因果收益。

R16 在 L0 两 split 均恢复相同的 native 路由集合，但 matched-ID down L2 仍约 11.26%。因此提高 router 精度不足以解决整条 MoE 链的数值问题。

## Prefill / decode 分开核验

表中每格为 prefill64 / decode8；匹配路径上限分别为 512 / 64。A8 编码损失仍覆盖该阶段所有原路径。

| 条件 | 匹配路径 P/D | mid Q12 L2 % P/D | down L2 % P/D | 额外 A8 L2 % P/D | Q12 RNE / total mid SSE P/D |
|---|---:|---:|---:|---:|---:|
| L0 R8 calibration | 502/63 | 11.063596 / 11.651261 | 11.203213 / 11.670845 | 3.238686 / 2.651299 | 3.19824575e-8 / 2.86976716e-8 |
| L0 R8 evaluation | 498/63 | 11.074691 / 10.666668 | 11.313848 / 10.731062 | 3.286613 / 2.917756 | 3.73889448e-8 / 3.84736130e-8 |
| L0 R16 calibration | 512/64 | 11.075334 / 11.649110 | 11.210971 / 11.665816 | 3.242714 / 2.650795 | 3.24102975e-8 / 2.91355563e-8 |
| L0 R16 evaluation | 512/64 | 11.090340 / 10.666728 | 11.325854 / 10.728156 | 3.279618 / 2.916734 | 3.80288225e-8 / 3.90588955e-8 |
| L13 R8 calibration | 506/63 | 5.393300 / 4.055363 | 5.666728 / 5.824924 | 3.100975 / 3.739164 | 3.01716043e-6 / 4.24002306e-6 |
| L13 R8 evaluation | 509/64 | 5.315691 / 2.851816 | 5.786388 / 4.432817 | 3.180116 / 3.143903 | 2.39847632e-6 / 9.76770438e-6 |
| L13 R16 calibration | 512/63 | 5.385016 / 4.055363 | 5.663103 / 5.824924 | 3.094102 / 3.739164 | 3.03834322e-6 / 4.24002306e-6 |
| L13 R16 evaluation | 512/64 | 5.310820 / 2.851816 | 5.784015 / 4.432817 | 3.174006 / 3.143903 | 2.40499494e-6 / 9.76770438e-6 |

分阶段最大的最终 Q12 RNE / total 能量比也仅 `9.76770438e-6`（约 `0.00097677%`），出现在 L13/evaluation/decode。没有发现某一原阶段由最终 Q12 舍入主导。

## A8 量程、mid delta 与归零

每条件的全部 576 路径均没有 delta=0；报告的“delta0 且 0<峰值<64/127”计数与全零 mid 行也均为 0。这些数据不支持先前“mid 过小而 Q12 格式让 A8 用不满量程”的假设。delta 是当前行在线最小 RNE 右移量，最终 A8 的实际单位为 `2^(delta-12)`。

| 条件 | mid_delta 全路径直方图（delta:路径数） | delta0 且 0<峰值<64 | delta0 且 0<峰值<127 | 全零 mid 行 |
|---|---|---:|---:|---:|
| L0 R8 calibration | 7:23, 8:77, 9:176, 10:206, 11:59, 12:22, 13:13 | 0 | 0 | 0 |
| L0 R8 evaluation | 7:31, 8:82, 9:174, 10:191, 11:53, 12:35, 13:10 | 0 | 0 | 0 |
| L0 R16 calibration | 7:22, 8:76, 9:177, 10:207, 11:59, 12:22, 13:13 | 0 | 0 | 0 |
| L0 R16 evaluation | 7:32, 8:84, 9:171, 10:192, 11:52, 12:35, 13:10 | 0 | 0 | 0 |
| L13 R8 calibration | 6:14, 7:167, 8:274, 9:105, 10:15, 12:1 | 0 | 0 | 0 |
| L13 R8 evaluation | 6:2, 7:129, 8:290, 9:132, 10:22, 12:1 | 0 | 0 | 0 |
| L13 R16 calibration | 6:14, 7:166, 8:276, 9:104, 10:15, 12:1 | 0 | 0 | 0 |
| L13 R16 evaluation | 6:2, 7:129, 8:291, 9:131, 10:22, 12:1 | 0 | 0 | 0 |

| 条件 | 匹配 native 非零→mid Q12 零 / native 非零 | 其中 native abs≤Q12 半 LSB 数 | 全路径 product 非零→mid Q12 零 / product 非零 |
|---|---:|---:|---:|
| L0 R8 calibration | 2284 / 289280 | 1867 | 136 / 292730 |
| L0 R8 evaluation | 2420 / 287232 | 2102 | 123 / 292550 |
| L0 R16 calibration | 2368 / 294912 | 1950 | 135 / 292679 |
| L0 R16 evaluation | 2478 / 294912 | 2155 | 122 / 292556 |
| L13 R8 calibration | 517 / 291328 | 277 | 162 / 294555 |
| L13 R8 evaluation | 498 / 293376 | 271 | 181 / 294594 |
| L13 R16 calibration | 525 / 294400 | 280 | 163 / 294550 |
| L13 R16 evaluation | 498 / 294912 | 271 | 180 / 294594 |

Q12 半 LSB 为 `2^-13 = 0.0001220703125`。native 非零→Q12 零包含上游 product 已为零的元素，不能全部归因于最后的 Q12 舍入。直接由同操作数最后一步归零的 product 非零元素，每条件仅 122–181 个；“有归零”与“主导误差”也不是同一判断。

## 路由抵消与 gate 对照

三个非加性集合差异分别为 U（native→同 current integer norm 的 FP64 router）、R（该 FP64 router→integer router）、T（native→integer）。这里比较 top8 集合，排名变化不等价于集合变化。

| 条件 | U/R/T（72 token） | gate 匹配 ID L2 % | dense40 gate L2 % |
|---|---:|---:|---:|
| L0 R8 calibration | 0/11/11 | 2.071732 | 6.485976 |
| L0 R8 evaluation | 0/15/15 | 1.944875 | 6.260347 |
| L0 R16 calibration | 0/0/0 | 0.070369 | 0.070369 |
| L0 R16 evaluation | 0/0/0 | 0.065302 | 0.065302 |
| L13 R8 calibration | 1/6/7 | 1.137712 | 9.180802 |
| L13 R8 evaluation | 1/4/3 | 1.164472 | 4.860744 |
| L13 R16 calibration | 1/0/1 | 0.117329 | 3.732342 |
| L13 R16 evaluation | 1/1/0 | 0.123671 | 0.123671 |

**L13/evaluation token42（零起始）**：R8 与 R16 均出现联合 flags `110`。norm/外部 cut 的变化先使同 current-norm FP64 路由集合不同于 native，integer router 的差异又将集合改回 native。因此 R16/evaluation 的最终 `T=0` 不能写为 router 本身没有差异，实际 `U=1,R=1,T=0`。R8/evaluation 为 `U=1,R=4,T=3`，也包含该抵消。L13/calibration 的上游一次变化发生于 decode，R16 为 `1/0/1`。

dense40 gate 对照将未选 expert 权重置零，包含换 expert 的影响；匹配 ID gate 对照只涵盖共同 expert，两者分母与含义不同。不能以较低的匹配 ID gate 误差隐藏重路由损失。

## 决策：本阶段不新增 F20 实验

1. 全部八条件及两个阶段均不支持“最后 Q12 RNE 主导”的假设：该步能量远小于已有上游 mid 误差。
2. 全部 mid_delta 已为 6–13；A8 量程未闲置。若只把同一个 Q24 product 改为 RNE4→I32Q20，随后最小 A8 右移量通常增加约 8，最终 A8 物理步长可能不变，不能声称普遍多 8 位有效精度。边界双重舍入仍可能变化，但当前没有证据表明值得优先增加条件。
3. Q20 还将 I32 物理范围从 Q12 的约 ±524288 缩为约 ±2048，必须有独立范围守卫；下游 RQ 也需将 shift 从 `31-wexp-delta` 改为 `39-wexp-delta`。这属于新数值合同，不是无代价复用旧结果。
4. 若后续继续定位，应先区分最终 product 之前的 gate/up 输入/权重/RQ 与 SiLU 等阶段误差，以及当前 per-row A8 量程的代价，再决定精度或粒度候选。此次没有实现这些新条件，也没有据评价样本调整 scale。

对 Block 划分的含义：需要把 router 精度/真实 top8 与 expert 数据路径的数值合同分别保留；R16 路由恢复不能替代 expert 链验证。mid→A8 是独立的重新量化接口，需要显式单位和在线控制成本。此结果支持继续比较这些接口的精度与资源，但不足以冻结新的 M/V 物理边界。

## 范围、验证与未完成项

- 本脚本仅事后读取原八条件；没有新推理、训练、格式拟合、挑样、scale 搜索或 runtime 浮点回退。原 chain、cal/eval 数据与旧失败保持不变。
- matched-ID 统计剔除未匹配 expert；`witnesses.npz` 中相关未匹配占位零必须配 `matched_ID` mask 使用，不能计作零误差。
- 外部残差来自已限定的 model64 参考 cut，Attention、先前层和整模型应用质量不在此整数闭环内。旧 native FP32 失败不由新参考或本诊断翻案。
- 同 current-norm FP64 router、native 对照、SSE 分解都是离线观察，不构成新的在线硬件能力。局部误差也不能直接换算硬件周期、PPA、端到端任务质量或速度收益。
- 本工具检查原 artifact SHA、恰好八条件、完整 shape、Q24→Q12/A8 的存储码一致性及 gate/topk 格式；不能替代独立 receiver 的全链算术接收或质量验收。
- 工具交付时本机仅运行 7 项小合成测试、`python scripts/check_project.py` 与 `git diff --check`，均通过。本报告新增仅 Markdown，核对 JSON 指标与来源；没有在本机加载实际 NPZ 或计算真实张量。
- F20 实验：**未执行，当前证据不支持优先新增**。划分研究与完整模型质量仍需按主任务证据继续收敛，Issue74/PR75 不因本次诊断标 done 或自动合并。
