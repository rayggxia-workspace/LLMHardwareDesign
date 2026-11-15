# 七模型三 P FFN 与代表性历史复测

2026-11-15（Asia/Shanghai）。[Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) · [PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275)。从 `fc1327ec4d3a27bcea00a04cc0e6c4e6942fd05c` 续办，保持 512-bit TLM、3,334 ps 核周期和双通道 DDR 配置。

稠密 FFN 的 Gate、Up、激活和 Down 以输出 tile 分到 P0/P1/P2。每批母控发出不同目标的 CALL，再等待该批的共同 WAIT。各目标使用独立的 SRAM、投影及 FFN 供权重状态。FFN Mid 落在经对账的 DDR 缓冲，Down 通过显式读回供数，P1/P2 结果汇入 P0。同一通道的 DMA/DDR 资源仍共享。Granite 从 router logits 选 top-8，按 3/3/2 分成三批，在 SRAM 保留专家选择和权值，按原专家顺序累加。

Decode 在各模型的代表性 512 位置缓存上执行两步，数据来自 `reference-workloads-01/ref-114294` 和 Llama 的 `ref-114313`。K/V 按实际行宽和地址转为 S32/Q16。GDN 键主状态转为回放需要的值主布局，Mamba2 保留原布局，两者均包含卷积缓冲和持久状态。初始归档、每个 DDR 映像的散列、量化范围、地址与完整覆盖均检查。短 Prefill 从两个原始输入位置开始。

## 作业回执

任务根 `/public/home/yuzelu/Melodydt/runs/issue-274`，服务器 `yuzelu@10.129.166.172`。115553 在 `three-p-live-01` 核验五个注意力模型，混合状态因缓存容器处理失败。115562 在 `three-p-live-02` 确认混合状态是显式 stream 字典。115573 在 `three-p-prepare-01` 全部校验成功（`COMPLETED 0:0`，node16，7×12 核，37 秒）。五个注意力模型与两个混合模型的来源和 DDR 映像 SHA 写在各自 `run-115573-*/prepare-live-*/assets/plan.json`。

115593 超出 DDR 地址上限。115600 在修正地址后跑完六个稠密模型的首层两位置，旧串行权重计数检查导致退出 1:0。115605 在 `three-p-all-pilot-01` 完成 7 个三 P 首层及 Granite 串行对照（`COMPLETED 0:0`，node16，8×12 核，1 分 18 秒）。三路权重请求与回包逐路平衡。Qwen3、Gemma 和 Granite 两位置残差与串行首层逐字节一致，Granite 的专家轨迹一致。

全层源码目录 `three-p-full-01`，`source.sha256` 的 SHA-256 为 `5569752787c253f83e201390416e672d059543e983ca7cf701ac1838442a8c3e`。独立 FP32 参考 115617 在 node16，短 Prefill 115618 在 node13，代表性历史两步 Decode 115619 在 node14。每批 c96 7×12 核。115617、115618 和 115619 均正常结束。Gemma 最终采用下方 116000。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-274/three-p-full-01
sha256sum -c source.sha256
sha256sum -c upstream.sha256
squeue -j 115617,115618,115619
sacct -X -j 115617,115618,115619 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
tail -n 2 run-115618-*/*.log run-115619-*/*.log
```

独立 FP32 按同一模型、首步输入与初始状态生成通常的两步参考。若第二步的反馈 token 分歧，另用 `reference_candidate_token.py` 生成同 token 对照。TLM 在完成每层的 WAIT 后直接采样 U 的残差存储，无额外模拟访问。`compare_fp32_layers.py` 核验每帧与同输入 FP32，报告相对 L2、余弦与饱和计数。后续需定位首个显著偏差并重跑受影响配置。

## 已回读的全层结果

| 模型 | 短 Prefill（输入 tok/s） | 两步 Decode（tok/s） | 同输入 FP32 |
| --- | ---: | ---: | --- |
| Qwen3-0.6B | 23.449462 | 7.151345 | 两步 token 一致。logits 相对 L2 0.82%／1.07%。 |
| Llama-3.2-1B | 15.534217 | 5.674618 | 两步 token 一致。logits 相对 L2 0.61%／1.07%。 |
| Granite MoE | 16.073199 | 6.940185 | 两步 token 一致。logits 相对 L2 4.56%／2.62%。 |
| Phi-4-mini | 4.963337 | 2.028011 | 两步 token 一致。logits 相对 L2 0.44%／0.34%。 |
| Gemma-3-4B | 5.058930 | 2.198041 | 两步 token 一致。logits 相对 L2 0.44%／0.91%。 |
| Qwen3.5-4B | 4.011233 | 2.194038 | 两步 token 一致。logits 相对 L2 1.11%／0.79%。 |
| Falcon-H1-3B | 4.297764 | 3.020079 | 两步 token 一致。logits 相对 L2 0.35%／0.34%。 |

115617 `COMPLETED 0:0`，七个模型的 FP32 两步 logits 与冻结参考复核后输出层级轨迹。完整 Prefill 和 Decode 各自产物与状态以对应模型目录内的 `result.json` 为准。

Gemma 原 Q16 方案在位置 0 第 5 层的 FP32 幅值已超过 51,000，四组冻结 FP32 轨迹的最大值为 298,680.375。Q12 改版在作业 115660 中将该层峰值收回到 51,386.26（FP32 51,397.01），相对 L2 由 36.24% 降至 0.025%。第一版改版同时复跑两个全层阶段，目录 `three-p-gemma-q12-01`，源清单 SHA-256 `447c10ab618377f02bb7932a814b29fe221387c321d38e553578fd7a2a1fc08d`。

## 旧混合模型零历史回执更正

115703 在 c64/node4 以 2×10 核于 20 秒正常结束。`three-p-seed-audit-01/audit-115703` 的两份报告和 `output.sha256` 已读回校验。旧归档 `hybrid-zero-reference-01/ref-115123` 中两模型均标记 `history_payload=zeros`。

| 模型 | 非零 K/V | 非零卷积状态 | 非零递推状态 | 源缓存 SHA-256 |
| --- | ---: | ---: | ---: | --- |
| Qwen3.5 | 0 | 786,432 | 12,582,912 | `da663fcba52357093b66e8076a1a30561600c4b43cbc6e997b743a70253584d2` |
| Falcon | 0 | 589,824 | 33,552,761 | `f3c8a4aea5b0bd563d914448059e22db98f965f569f129ba0589bcf06dfea9be` |

旧 FP32 清零入口漏掉字典中的卷积与递推缓存，故旧混合模型数值差同时包含起始状态变化。`reference_workload.py` 已修正对字典和队列的处理。保留旧归档和回执。新任务以实际 FP32 历史做来源、尺寸和读回校验。

## 全层短 Prefill 的调度对照

115618 于 node13 运行 39 分钟，`COMPLETED 0:0`。按原 S32/Q16 对照，七个模型两位置的末层残差与上一轮串行 P 逐字节匹配。短 Prefill 增幅分别为 Qwen3 39.789%、Llama 75.758%、Granite 57.123%、Phi 79.679%、Gemma 91.163%、Qwen3.5 60.095%、Falcon 41.923%。Gemma 原 Q16 仍有 47 次饱和，该数值仅用于隔离调度。分别核对 `pr272-tlm-01/run-115340` 至 `run-115346` 的 Prefill 与 `three-p-full-01/run-115618-<模型>` 的 `result.json`。

## Gemma 溢出修订和复跑

115660 的 Q12 残差在原饱和点通过。首位置第 32 层的后归一化分支仍以 Q16 写回，因此在进入 Q12 残差加法前触发 `native E service reported S32 clipping`。保留该失败记录。后 Attention 与后 FFN 的 RMS 现在直接以 Q12 写回，残差分支同格式相加。为投影提供输入的 RMS 仍输出 Q16。

最新双阶段作业 116000 以 c96/node19、2×12 核于 55 分 19 秒正常结束，`three-p-gemma-q12-02`，源清单 SHA-256 `badf7b098fe4f821fd6e6c818d3e2bc292f5a725a0e6b8e2de7ba8496377e7b8`。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-274/three-p-gemma-q12-02
squeue -j 116000
sacct -X -j 116000 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
tail -n 10 slurm-116000.log run-116000/*.log
```

第一版 Q12 的 Decode 已结束，2.198041 tok/s，两次 token `496 → 64745` 与同历史 FP32 一致，logits 相对 L2 为 0.44%／0.92%，饱和 0 次。全 Q16 同历史版本保持相同 token，但 logits 相对 L2 为 116.73%／71.86%，饱和 34 次。115660 整批因 Prefill 的 RNE 输出写回溢出为 `FAILED 1:0`。此 Decode 用于证明残差改版，最终两阶段统一采用 116000。

同系列全层 115619 在 node14 于 58 分 31 秒完成，`COMPLETED 0:0`。六个已选模型的两步 token 对齐，输出清单已逐项验 SHA-256，回执位于任务根 `audits/three-p-run-115618-<模型>-sha.log` 和 `audits/three-p-run-115619-<模型>-sha.log`。

## 独立数值验收

116181 在 c64/node3 以 6×10 核于 10 秒结束，`COMPLETED 0:0`。验收逐模型核对母控页数和局控调用，三路权重记录与回包齐全，DDR 及 KV／递推状态回读，和两次真实词表退休。两个阶段均无 S32 饱和，逐层完整覆盖。对照按 FP32 最终 RMS 得到的短 Prefill 相对 L2 分别为 Qwen3 2.7991%、Llama 2.8073%、Granite 2.9760%、Phi 2.0980%、Qwen3.5 1.5258%、Falcon 0.3633%。两步 top-1 均通过。

作业目录 `three-p-audit-01`，源清单 SHA-256 `bfbc4bc32cf741ad41437afedc866a4d44878a8e278b55963e3039949ebbaea6`。116181 的 12 项输出清单通过，清单 SHA-256 `9b2c0f74e1c62ce5bf8b698cd1b489ad4b3efcf4fe086ba6e9a749fde4cca138`。FP32 115617 的 838 项输出通过独立核验，清单 SHA-256 `242887ced73ca3e707e590aa2e7c493bfe61f0f3053ef893554ece497fb8cc07`。116182 按 `afterok:116000` 依赖在 c64/node1 完成 Gemma 两阶段验收，11 秒，COMPLETED 0:0。归一化短 Prefill 相对 L2 为 3.4982%，逐层两阶段各 68 项完整覆盖，两步 token 与 FP32 一致。审计 SHA-256 `639704f1fb24f484856ed4f5d050aeea9c198fe3a5ba0466bb136fd679aefc02`，输出清单 SHA-256 `553b8065ae0b24afc07aae3cd1d14c815771a0bab43eeedd809fd33311173ef3`。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-274/three-p-audit-01
sacct -X -j 116181,116182 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
sha256sum -c audit-116181/output.sha256
```

## 最终输出与复用

最终选用的 14 个阶段均完成。全部 Decode 均验收第一步产生 token 的实际反馈及代表性状态读取。七模型、两步共 14 个 top-1 与同历史、同输入 FP32 一致。两阶段均无残差饱和，保留 W8A16 量化误差和 TLM 时序校准范围。相对上一轮的 Decode 变化包含三 P 调度和初始历史变化。

所选模型输出清单合计 6,699 项通过 SHA-256 核验。Gemma 116000 的 1,145 项清单 SHA-256 为 `a5ec4ed90398f2e946eafd91043d21634c0262ff259937eed801886a43a5101c`，Prefill 与 Decode 的 `result.json` SHA-256 分别为 `a16c794a9eaafb758b3273544eee07cf57bf7617ec5820aa855b84adec4dd16b` 和 `5de649df65783a0e7863c0c4eb98155faf6132ddbc79784e366d2612a1e79873`。其余六模型的逐文件核验记录在 `audits/three-p-run-*-sha.log`。完整验收保留在 `three-p-audit-01/audit-116181` 和 `audit-116182`。

复跑在各自冻结目录提交新作业。六模型按照 `three_p_suite.sbatch` 里的参数运行，Gemma 使用下列入口。独立验收通过 `audit_three_p.py REFERENCE FP32_TRACE PREFILL DECODE` 读取参考目录、完整层轨迹和两阶段产物。

```bash
sbatch --parsable -p c96 -N1 -n2 -c12 -t 06:00:00 --job-name=mdt-274gemq12 \
  --export=ALL,MDT_274_NATIVE_MATH=1,MDT_274_THREE_P=1,MDT_274_TRACE_LAYERS=1,MDT_274_GEMMA_WIDE_RESIDUAL=1 \
  -o slurm-%j.log fast_qwen3_short.sbatch gemma prefill:4:cache:combined decode-live:4:cache:combined
```
