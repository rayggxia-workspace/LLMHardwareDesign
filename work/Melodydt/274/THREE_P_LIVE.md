# 七模型三 P FFN 与代表性历史复测

2026-11-15（Asia/Shanghai）。[Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) · [PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275)。从 `fc1327ec4d3a27bcea00a04cc0e6c4e6942fd05c` 续办，保持 512-bit TLM、3,334 ps 核周期和双通道 DDR 配置。

稠密 FFN 的 Gate、Up、激活和 Down 以输出 tile 分到 P0/P1/P2。每批母控发出不同目标的 CALL，再等待该批的共同 WAIT。各目标使用独立的 SRAM、投影及 FFN 供权重状态。FFN Mid 落在经对账的 DDR 缓冲，Down 通过显式读回供数，P1/P2 结果汇入 P0。同一通道的 DMA/DDR 资源仍共享。Granite 从 router logits 选 top-8，按 3/3/2 分成三批，在 SRAM 保留专家选择和权值，按原专家顺序累加。

Decode 在各模型的代表性 512 位置缓存上执行两步，数据来自 `reference-workloads-01/ref-114294` 和 Llama 的 `ref-114313`。K/V 按实际行宽和地址转为 S32/Q16。GDN 键主状态转为回放需要的值主布局，Mamba2 保留原布局，两者均包含卷积缓冲和持久状态。初始归档、每个 DDR 映像的散列、量化范围、地址与完整覆盖均检查。短 Prefill 从两个原始输入位置开始。

## 作业回执

任务根 `/public/home/yuzelu/Melodydt/runs/issue-274`，服务器 `yuzelu@10.129.166.172`。115553 在 `three-p-live-01` 核验五个注意力模型，混合状态因缓存容器处理失败。115562 在 `three-p-live-02` 确认混合状态是显式 stream 字典。115573 在 `three-p-prepare-01` 全部校验成功（`COMPLETED 0:0`，node16，7×12 核，37 秒）。五个注意力模型与两个混合模型的来源和 DDR 映像 SHA 写在各自 `run-115573-*/prepare-live-*/assets/plan.json`。

115593 超出 DDR 地址上限。115600 在修正地址后跑完六个稠密模型的首层两位置，旧串行权重计数检查导致退出 1:0。115605 在 `three-p-all-pilot-01` 完成 7 个三 P 首层及 Granite 串行对照（`COMPLETED 0:0`，node16，8×12 核，1 分 18 秒）。三路权重请求与回包逐路平衡。Qwen3、Gemma 和 Granite 两位置残差与串行首层逐字节一致，Granite 的专家轨迹一致。

全层源码目录 `three-p-full-01`，`source.sha256` 的 SHA-256 为 `5569752787c253f83e201390416e672d059543e983ca7cf701ac1838442a8c3e`。独立 FP32 参考 115617 在 node16，短 Prefill 115618 在 node13，代表性历史两步 Decode 115619 在 node14。每批 c96 7×12 核。全层数值、吞吐及输出散列待结果回读。

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
| Qwen3-0.6B | 23.449462 | 7.151345 | 两步 token `72349 → 5785` 一致。logits 相对 L2 为 0.82%／1.07%。 |

115617 `COMPLETED 0:0`，七个模型的 FP32 两步 logits 与冻结参考复核后输出层级轨迹。完整 Prefill 和 Decode 各自产物与状态以对应模型目录内的 `result.json` 为准。

Gemma 原 Q16 方案在位置 0 第 5 层的 FP32 幅值已超过 51,000，四组冻结 FP32 轨迹的最大值为 298,680.375。Q12 改版在作业 115660 中将该层峰值收回到 51,386.26（FP32 51,397.01），相对 L2 由 36.24% 降至 0.025%。改版同时复跑两个全层阶段，目录 `three-p-gemma-q12-01`，源清单 SHA-256 `447c10ab618377f02bb7932a814b29fe221387c321d38e553578fd7a2a1fc08d`。
