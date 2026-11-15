# Qwen3-0.6B 双通道 DDR 能耗试点回执

2026-11-15（Asia/Shanghai），负责人 Melodydt。回放源码 `ac2a7265d4510e0fc73164a83ebb5355da586a88`。沿用 #274 的三 P FFN、512-bit SRAM TLM、3,334 ps 核周期、双通道 DDR4 630 ps 与每通道 32 个 credit，Decode 从真实 512 位置历史起步。短 Prefill 的冻结对照为 115618，Decode 为 115619，独立 FP32 使用 115617 的 Qwen3 轨迹和原始模型输入。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [速度基线](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/THREE_P_LIVE.md)

## 能耗和速度

| 窗口 | 模拟时间（ms） | tok/s | DDR 器件 mJ/token | 命令／背景 mJ/token | 平均 DDR 器件 W |
| --- | ---: | ---: | ---: | ---: | ---: |
| 短 Prefill，两输入 token | 85.289805 | 23.449462 | 114.939879 | 36.843831 / 78.096048 | 2.695278 |
| 首 token，从仿真起点到第一次退休 | 139.703052 | — | 332.791363 | 88.639538 / 244.151825 | 2.382134 |
| Decode，两退休间隔 | 139.833835 | 7.151345 | 332.854675 | 88.717139 / 244.137537 | 2.380359 |

DDR 模型积分包含两通道的实际 ACT/RD/WR/REF 及各 rank 背景能量，共用现有确定的 DRAMsim3 配置。Prefill 两输入合计 0.2298797573 J，第二个 Decode 窗口为 0.3328546755 J。背景分别占短 Prefill 与 Decode 窗口能量的 67.95% 和 73.35%。覆盖边界为 DDR 芯片模型，片上模块、DDR PHY、板级 I/O 和终端待另行标定或核算。

两阶段的计时、各位置残差、完整词表 logits、DDR 回调与三路供数对照冻结版本一致。独立审计的位置序列为 `264 → 72349 → 5785`，两次退休均与同输入 FP32 top-1 一致，logits 相对 L2 为 0.8209% 和 1.0694%。短 Prefill 归一后残差相对 L2 为 2.7991%。两阶段各审计 56 个层输出，残差限幅均为 0。回放包含双通道终态统计核对和 rank 驻留周期闭合。

## 作业与证据

- `116481.3` 与 `116481.4` 分别完成 Prefill 和 Decode，在 c96/node15 各 12 核，退出均为 `COMPLETED 0:0`。启动和两个 DDR 分窗汇总也均完成。母作业 `116481` 记录为 `FAILED 1:0`，原因是步骤 `116481.5` 引用了错误的 FP32 审计脚本目录。原始产物和日志保留。
- 补跑 `116496`（`mdt-280audit`）在 c64/node1 用 10 核，21 秒 `COMPLETED 0:0`。使用 #274 原审计目录 `three-p-audit-01` 的脚本和源码清单，复核既有模型产物。当前启动器已改为直接引用该目录并核验其源清单。启动器改动做了语法和归档路径检查，原模型回放由 116481 完成，补审由 116496 完成。
- 在服务器 `yuzelu@10.129.166.172` 的 `/public/home/yuzelu/Melodydt/runs/issue-280/ddr-pilot-02` 读回输入清单 8 项、结果清单 7 项、回放输出清单 1,068 项，均通过 SHA-256 校验。两次作业使用 `sbatch --parsable run_qwen3_ddr_pilot.py` 和 `sbatch --parsable audit_qwen3_116481.sbatch` 提交。

| 文件（相对提交目录） | SHA-256 |
| --- | --- |
| `pilot-116481/ddr-prefill.json` | `0ae8486ad2747d06866de1dd2e111a4772d7a7e82f241fe0b4c7130af7905fa3` |
| `pilot-116481/ddr-decode.json` | `16ed053bb0a946dc7884483599bc2d91b9bf6fa8e70434886cc98d56bd259ac9` |
| `pilot-116481/pilot-inputs.sha256` | `2c5454812681ea939b107ef4c5d09cbda2d1a1a4d144acb1f8292f61d566873f` |
| `audit-116481-116496/audit-three-p.json` | `a3df957c35c5e6c69f60348e7ce74b99ae8764b66a24f0036a9ff525eed54a71` |
| `audit-116481-116496/pilot-results.sha256` | `6ca584117c902faa16e96c01b4f62b56317d33faebb60aff3e27fba95fbe95b4` |
| `audit_qwen3_116481.sbatch` | `fa93d0b18180e9bc955824d684922fedd7b553ebd7c33598440a8a4ef5cd711b` |

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280/ddr-pilot-02
sacct -j 116481,116496 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
sha256sum -c audit-116481-116496/pilot-results.sha256
sha256sum -c pilot-116481/staged/replay/run-116481/output.sha256
cat pilot-116481/ddr-prefill.json pilot-116481/ddr-decode.json
```

## 剩余步骤

1. 在同一三 P 资源配置、同输入与历史、同 FFN Mid DDR 路径上做 P0 单路与三 P 并行 A/B。核对输出与跨步状态，逐窗比较延迟、mJ/token 和读写及背景分项。
2. 用 C380 ATT1 与 C639 FFN 激励开展门级活动标定。核对实际 512-bit SRAM／PM 宽读写与 bank 使能，再补母控／局控、DMA、时钟、互连和模型专用算子，用背压及并发样本验证误差。
3. 用 Granite 专家并发及 Phi、Falcon 的 V 读取优化做专项 A/B，辨别能耗变化来源。
4. 扩测七模型的短 Prefill、首 token 和两退休 Decode。逐模型归档速度、平均 W、DDR／片上已覆盖 mJ/token 及误差，Qwen2.5-3B 另列同口径参考。
5. 覆盖齐备后汇总全系统 mJ/token 和误差，报告片上、DDR 芯片、PHY 与板级分项。
