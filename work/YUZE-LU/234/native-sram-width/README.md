# 128-bit and 512-bit SRAM timing experiment

Issue [#234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234) and PR [#260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260).

The 128-bit and 512-bit runs use the same sealed Qwen2.5-3B program, 512 positions of representative KV, two complete 36-layer decode steps, a 3,334 ps core period, two DRAMsim3 channels, 32 DMA credits per channel and an eight-beat KV window. The two-token 512-bit prefill starts with empty KV and ends at the second position's final residual. See the [execution commands](../../../../project/experiments/systemc_benchmark/README.md).

| Run | Slurm job | Source manifest |
| --- | --- | --- |
| 128-bit decode | 107947 | [128-source.sha256](128-source.sha256) |
| 512-bit decode | 108284 | [source.sha256](source.sha256) |
| Width comparison | 108308 | [compare.py](compare.py) |
| 512-bit prefill | 108359 | [prefill-source.sha256](prefill-source.sha256) |

The manifests identify the archived source and runner bytes for the individual jobs. The public replay uses the same short-run modes and takes the paths to the archived inputs as arguments. The inputs stay in the project archive.

| Archived input | SHA-256 |
| --- | --- |
| Sealed deployment proof | `74078b0b40fdeb73aeae71e3091db3e6a25fc5f27bc03c9981214bfef92b39ef` |
| Decode KV binding | `78347abd13135d71a678ff87b4760175ea81fb701a4edb022e080165321f2b4e` |
| DRAMsim3 bridge | `363d38212c06ded6b012c609cf834d2176fb51acb41ec0fedca918768cfbe292` |
| DDR4 channel configuration | `748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766` |
| Initial DDR image table | `e55ce2d889261daccbf43335875be922fe813fe92dc0ae9ee28fd1f5b880d7b5` |

The first four complete layers took 80.203 ms at 128 bits and 43.540 ms at 512 bits. Their per-page DDR read and write counts and mother instruction cycle counts matched. The complete trace audits supply the short-run throughput.

## 讨论与回执

[瓶颈分析、对照表及方案验证状态](PERFORMANCE_ANALYSIS.md) · [审计输出及归档散列](evidence/)

| Slurm 作业 | 项目服务器归档目录，根为 `/public/home/yuzelu/project-circuit` |
| --- | --- |
| 107358 | `issue260-native-two-waits-TRl0y7Ug` |
| 107361 | `issue260-native-two-dma-sRx1azw1` |
| 107947 | `issue260-native-kv-window-jL6neTvA` |
| 108284、108308 | `issue260-native-sram512-SMbOWTw6` |
| 108359 | `issue260-native-sram512-full-zrXP7jjS` |

每个回放目录内的 `run-JOB/page-timing.jsonl` 是完整时间线，旁边是 `execution.json` 与适用的审计。归档根目录保留源码、运行脚本与源码散列。`evidence/ARCHIVED_TRACES.sha256` 固定这些逐页归档的字节，文件名按作业号分组。比较作业在归档根目录写入 `comparison-108308.json`。

### 源代码查证点

以下路径相对于研究工作树根目录。RTL 与合同使用本轮本地研究基线 `6fc51dce420eaa8d29cbad473d9dc697f7fa996e`。

| 观察 | 位置 |
| --- | --- |
| 逐笔等待 DDR 与 SRAM 写确认 | KV 加载器 RTL `project/rtl/block_local_native/s128_ddr_range_load.sv:88` |
| 四银行、两响应槽和宽读 | SRAM RTL `project/rtl/s_sram/block_feed_s16k_sram.sv:17` |
| Attention S32 点积 | 调用 `project/rtl/block_local_native/s128_attention_core_scope.sv:129` · 计算核 `project/rtl/native_s32_dot/dot_s32_core.sv:23` |
| 接口宽度与发射限制 | 底座合同 `docs/plans/w8a16-next-base-contract.md:45` · 母控 DMA `project/rtl/mother_control_native/mc_dma_fabric_typed_p.sv:244` · M `project/rtl/w8a16_v1/m_native_leaf_s32.sv:5` · G32 `project/rtl/w8a16_v1/g_s32.sv:9` · E32 AP64 `project/rtl/w8a16_v1/e_s32_ap64.sv:6` |
