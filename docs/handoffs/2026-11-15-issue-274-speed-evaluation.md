# 七模型 512-bit SRAM 速度评估交接

2026-11-15（中国标准时间）。仓库 `rayggxia-workspace/LLMHardwareDesign`，项目 `llm-hardware-design`，负责人 Melodydt。任务分支 `task/274-seven-model-short-throughput` 从 PR #260 的 `55620f173f2ad540efade8a552c35e9dba0f43c0` 建立。最终速度与数值证据提交为 `d8f775b661c511d6450d5cbe63f4519563114895`。本文件汇总该提交已完成的全层短程实验，可单独复制到其他分支。 [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) · [PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) · [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260)

## 最终速度和数值结果

| 模型 | 短 Prefill（输入 tok/s） | 两步 Decode（tok/s） | Decode 两步 logits 相对 L2 | 短 Prefill 最终残差相对 L2 |
| --- | ---: | ---: | ---: | ---: |
| Qwen3-0.6B | 23.449462 | 7.151345 | 0.82% / 1.07% | 2.7991% |
| Llama-3.2-1B-Instruct | 15.534217 | 5.674618 | 0.61% / 1.07% | 2.8073% |
| Granite-3.1-3B-A800M-Instruct | 16.073199 | 6.940185 | 4.56% / 2.62% | 2.9760% |
| Phi-4-mini-instruct | 4.963337 | 2.028011 | 0.44% / 0.34% | 2.0980% |
| Gemma-3-4B-it（文本，Q12 残差） | 5.058930 | 2.198041 | 0.44% / 0.91% | 3.4982% |
| Qwen3.5-4B（文本） | 4.011233 | 2.194038 | 1.11% / 0.79% | 1.5258% |
| Falcon-H1-3B-Instruct | 4.297764 | 3.020079 | 0.35% / 0.34% | 0.3633% |

七模型两次退休的 top-1 共 **14/14** 与同历史、同输入 FP32 一致。短 Prefill 相对 L2 按 FP32 最终 RMS 归一后的末层残差计算。14 个阶段均无 S32 残差限幅。独立验收检查了母控页、局控调用、三路权重与回包、DDR 请求及回调、KV 和适用的递推状态，以及两次全词表退休与首 token 实际反馈。6,699 项回放产物和 838 项 FP32 参考文件的 SHA-256 清单已核验。 [全层结果与独立验收](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/THREE_P_LIVE.md#L28-L94)

Qwen2.5-3B 是独立参考。PR #260 的 512-bit 短程回放为 **5.408 输入 tok/s Prefill、2.091 tok/s Decode**，对应 108359、108284。PR #272 后续完整短程的保留值为 **6.316164 输入 tok/s、2.925996 tok/s**，对应 113166/113167、113164/113165。两组都沿用短程计时边界，配置和调度以各自 PR 为准。 [PR #260 短程表](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) · [PR #272 完整 Prefill](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ebd590def47d2da6b46f04a68931c1d47f11538e/work/Melodydt/270/ffn-wait-06/prefill-full.json) · [PR #272 完整 Decode](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ebd590def47d2da6b46f04a68931c1d47f11538e/work/Melodydt/270/ffn-wait-06/decode-full.json)

## 测量方法与共用配置

| 项目 | 固定口径 |
| --- | --- |
| 短 Prefill | Batch 1，从空 KV 和初始化状态开始，执行两个实际输入位置的全部层。仿真起点至第二位置末层完成的时间计入吞吐，包含该区间内的指令加载。公式为 `2 / elapsed_seconds`。 |
| 两步 Decode | Batch 1，从模型自己的真实 512 位置历史起步。执行两次全部层及 HEAD16 全词表投影，第二步消费第一步真实退休 token 和跨步状态。公式为 `1 / (t_retire_2 - t_retire_1)`，时间差以秒计。首步用于建立连续退休窗口。 |
| 执行 | 真实权重与模型冻结输入，投影 W8A16，母控页和局控描述符驱动事务级回放。主机 C++ 投影用于缩短仿真墙钟时间，保留原算术与模拟计时。数据 SRAM 端口与 PM 写宽均为 512 bit，核周期 3,334 ps。 |
| 存储 | DRAMsim3 双通道，每通道 tCK 630 ps、32 个 DMA credit。普通投影与词表权重窗口 4，ATT1 KV 窗口 8。最终测试启用 PR #272 对应的 `combined` 服务调度。 |

PR #272 的对应贡献包括 ATT1 的 V 选择读取、DDR 回包与 S 写确认解耦、双窗口回填和 Dot 读流水，以及用于 FFN Gate/Up/Down 的四权重 bank。三 P 在此基础上为每路建立独立供权重状态。稠密层将 Gate、Up、激活和 Down 按 128 个输出元素的 tile 分给 P0/P1/P2，母控对同批目标发 CALL 后统一 WAIT。FFN 中间结果写入 DDR，Down 通过显式路由读回，P1/P2 结果汇入 P0。三路共享 DMA/DDR。Granite 使用整专家并发，详见下表。 [计时源码](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/qwen3_short.py#L569-L632) · [三 P 指令生成](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/qwen3_short_plan.py#L181-L220) · [PR #272 接入说明](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/fc1327ec4d3a27bcea00a04cc0e6c4e6942fd05c/work/Melodydt/274/PR272_RETEST.md#L7-L27)

## 每个模型实际采用的专项优化和适配

| 模型及运行参数 | 最终实测采用的专项路径 |
| --- | --- |
| **Qwen3** `tile128` | 保留 128 维、512 B 的 K/V 行，在八行窗口中复用同一历史行、同一查询头的 V 读取，配合双窗口回填。保留模型的 Q/K RMS、RoPE 和 GQA。 [ATT1 路径](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/qwen3_short.py#L449-L462) |
| **Llama** `kv64` | `ATT1/2` 使用真实 64 维 KV，移除 128 维对齐产生的填充，行宽从 512 B 缩为 256 B，并复用 V 读取。逻辑数据 SRAM 端口仍按 512 bit 计时。 [Llama 降低](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/llama_short_plan.py#L71-L120) |
| **Granite MoE** `kv64` | 同样使用 64 维紧凑 KV 和 V 读取复用。router 按实际 logits 动态激活 8/40 专家，以 3/3/2 波次将整专家分给三路 P。专家中间值留在各路 SRAM，软最大权值和专家结果按原专家次序聚合。 [MoE 编译与运行](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/granite_short.py) |
| **Phi** `cache` | 128 维 ATT1 走冻结的 V 选择读取与流水实现。融合 QKV、融合 Gate/Up 权重按矩阵区间供数，保留 partial LongRoPE 和大维度 RMS 的 SRAM 布局。 [Phi 降低](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/phi_short_plan.py) |
| **Gemma** `cache` + `MDT_274_GEMMA_WIDE_RESIDUAL=1` | 256 维宽注意力接入双窗口，K/V 各读 1,024 B 整行，保留局部／全局注意力及其 RoPE、Q/K RMS 和 GELU FFN。残差和后 Attention／后 FFN 的 RMS 直接按 Q12 写回，供投影的 RMS 仍用 Q16，消除旧版限幅。此用例的 514 位置处于 1,024 位置局部窗口内。 [Gemma 降低](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/gemma_short_plan.py) · [Q12 复测](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/THREE_P_LIVE.md#L59-L74) |
| **Qwen3.5** `cache` | 8 层 256 维全注意力走宽注意力双窗口及整行 K/V 读取，24 层走 GDN。真实 GDN 键主历史转为值主布局，卷积缓冲和持久状态按显式 DDR 事务恢复、读回和写回。 [GDN 与宽注意力](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/hybrid_short.py) |
| **Falcon** `cache` | 每层保留 Mamba2 与注意力两分支，候选回放先执行递推服务，再执行 128 维 ATT1。ATT1 复用冻结的 V 选择读取流水，高阶递推和卷积状态沿用真实布局并按显式 DDR 事务跨步。 [Falcon 两分支降低](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/hybrid_short.py#L174-L218) |

`cache` 是沿用的脚本参数。它在第一轮单 P 实验中使 Phi、Gemma、Qwen3.5、Falcon 将前 4,096 个 FFN 中间值驻留 Context SRAM。最终三 P 稠密分支走 DDR 中间结果路径，因此读取新回执时应以 `ffn_by_target` 和实际 DDR 路由为准。GDN 和 Mamba2 的状态读写使用实际回调，状态算术和周期由候选 TLM 服务提供。 [首轮单 P 优化与 A/B](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/50ed5b09d5b9fd94bd3769ecd3c5bb1d9c002f75/work/Melodydt/274/OPTIMIZATION.md#L47-L87) · [三 P 路由](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/qwen3_short_plan.py#L181-L220)

在保持输入和原 Q16 的全层短 Prefill 对照中，三 P 调度相对上一轮单 P 使七模型吞吐提高约 39.8%–91.2%，两位置末层残差逐字节一致。区间上限来自旧 Q16 Gemma，Gemma 最终速度采用另行验收的 Q12。Decode 此轮同时改用真实历史，旧混合模型的所谓零历史还包含未清除的卷积和递推缓存，因此历史 Decode 差值涵盖了调度与起始状态变化。旧轮瓶颈分解显示，短 Prefill 主要随权重读量和供数等待变化，Decode 还受历史 KV、活跃专家、递推状态与词表头耗时影响。 [调度对照与旧历史更正](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/THREE_P_LIVE.md#L44-L59) · [各模型瓶颈](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/50ed5b09d5b9fd94bd3769ecd3c5bb1d9c002f75/work/Melodydt/274/OPTIMIZATION.md#L7-L29)

## 复用入口

服务器为 `yuzelu@10.129.166.172`，任务根为 `/public/home/yuzelu/Melodydt/runs/issue-274`。按仓库远程规则访问，归档源和大文件留在项目授权存储。作业目录以下均相对任务根。 [远程规则](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/docs/REMOTE_RULES.md)

| 工件 | 作业与目录 |
| --- | --- |
| 六模型最终短 Prefill | `115618`，`three-p-full-01/run-115618-<模型>`，c96/node13，7×12 核 |
| 六模型最终 Decode | `115619`，`three-p-full-01/run-115619-<模型>`，c96/node14，7×12 核 |
| Gemma Q12 两阶段 | `116000`，`three-p-gemma-q12-02/run-116000`，c96/node19，2×12 核 |
| 独立 FP32 和审计 | `115617`，`three-p-full-01/fp32-115617-<模型>`。`116181`、`116182`，`three-p-audit-01/audit-<作业号>`。 |
| 真实历史来源 | `reference-workloads-01/ref-114294`，Llama 使用 `ref-114313`。每个模型的预备映像 SHA-256 在 `three-p-prepare-01/run-115573-<模型>/prepare-live-*/assets/plan.json`。 |

`<模型>` 使用 `qwen3`、`llama`、`granite`、`phi`、`gemma`、`qwen35`、`falcon`。先核对冻结目录中的 `source.sha256`、`upstream.sha256` 与各次 `output.sha256`，再读阶段子目录的 `result.json`。批量复跑用 `three_p_suite.sbatch prefill`、`three_p_suite.sbatch decode-live`，Gemma 选用独立 Q12 脚本参数。实际提交命令、日志和审计入口见最终回执。 [冻结目录、命令与散列](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/THREE_P_LIVE.md#L9-L26) · [最终复跑入口](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/THREE_P_LIVE.md#L88-L103)

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-274/three-p-full-01
sacct -X -j 115617,115618,115619,116000,116181,116182 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
sha256sum -c source.sha256
sha256sum -c upstream.sha256
sha256sum -c run-115619-qwen3/output.sha256
cat run-115619-qwen3/decode-live-w4-tile128-pr272-combined/result.json
```

环境归档使用 Slurm 23.11.5、Singularity CE 4.3.4、`orfs-current-repacked.sif`、Python 3.12.7、PyTorch 2.10.0+cpu 和 Transformers 5.20.2。DDR 桥库 `run-113164.dram.so` 的 SHA-256 为 `1e74820e1cbe48b447e29fd9f98f55c54b4bd4f3fb493b0f2d8e1317c3cd8c1b`，DDR 配置的 SHA-256 为 `748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766`。 [工具与配置索引](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/RESULTS.md#L61-L65) · [冻结启动脚本](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/d8f775b661c511d6450d5cbe63f4519563114895/work/Melodydt/274/fast_qwen3_short.sbatch)

## 接到能耗评估时保留的边界

- 表中速度为全层短程 TLM，产物标记 `timing_calibrated=false` 和 `rtl_qualified=false`。PR #275 的模型专项改动落在指令生成和事务服务，RTL 源文件改动为零。C380 S128 ATT1 和 C639 FFN 有独立 Verilator 原生回归。整模型 512-bit RTL、物理时序、正式 B1/P512/D128 和能耗测量仍待执行。 [PR #275 文件](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275/files) · [原生局部回归](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/fc1327ec4d3a27bcea00a04cc0e6c4e6942fd05c/work/Melodydt/274/PR272_RETEST.md#L16-L27)
- 继续执行的第一步是固定本表版本，在 Qwen3-0.6B 回放中增加两次退休的 DDR／片上活动累计快照，再复核退休时间、FP32 对齐、状态和回包。现有 DDR 等计数覆盖两个位置，按退休差分后的单步计数才能与 Decode tok/s 配对。后续负责任务由对应 Issue 确认。
- 本次交接以 `rayggxia-project-collab` 1.0.0 编写。`python scripts/check_project.py` 通过，实验验证引用上述既有作业和审计。#274 进行中，#275 为草稿，独立审查人待指定。登记 PR #5 待合并。任务分支缺 `config/board.json`，看板条目待具权限维护者核验与同步。 [管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)
