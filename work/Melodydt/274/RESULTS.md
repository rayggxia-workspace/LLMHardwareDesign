# 七模型短程回放结果

任务 [#274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274)，交付 [PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275)。继承 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 的 `55620f173f2ad540efade8a552c35e9dba0f43c0`。服务器 `yuzelu@10.129.166.172`，结果根 `/public/home/yuzelu/Melodydt/runs/issue-274`，各运行目录固定 `source.sha256` 和 `upstream.sha256`。

短 Prefill 将两个位置推进到最后一层残差，吞吐为 2 除以总模拟时间。Decode 从 512 个零历史位置开始，按全词表选出并反馈 token，吞吐取两次全词表退休之间的间隔。首步输入 token 来自实际历史上的 FP32 参考。两种测量采用 PR #260 的事务级时间线，串行 P 调度和模型专用局控形成候选模型，RTL、物理时序及数值资格待核验。Slurm 用时单独记录。

已对产出下表的全部冻结源码执行 `sha256sum -c source.sha256`，数据 SRAM 均用 `S128(..., port_bits=512)`，程序存储写入均用 `pm_write_bits=512`。`S128` 表示模型以 128-bit 字寻址，512-bit 端口每个对齐传输拍最多容纳 4 字（64 B）。

| 模型 | 短 Prefill（输入 token/s） | Decode（token/s） | 作业与结果目录 |
| --- | ---: | ---: | --- |
| Qwen3-0.6B | 13.481376 | 3.585938 | 115055 完成，`qwen3-short-fast-01/run-115055` |
| Llama-3.2-1B | 7.178705 | 2.523063 | Prefill `qwen3-short-fast-01/run-115056`，Decode `llama-short-03/run-115128` |
| Phi-4-mini | 2.165252 | 1.100828 | Prefill `phi-short-02/run-115103`，Decode `phi-short-03/run-115129` |
| Gemma-3-4B | 1.985153 | 1.205363 | 115122 完成，`gemma-short-03/run-115122` |
| Granite MoE | 8.055319 | 2.376006 | Prefill `granite-short-01/run-115109`，Decode `granite-short-02/run-115130` |
| Qwen3.5-4B | 1.956770 | 1.326854 | 115124 完成，`hybrid-short-01/run-115124` |
| Falcon-H1-3B | 2.348169 | 1.702030 | Prefill `hybrid-short-01/run-115125`，Decode `hybrid-short-02/run-115126` |

## Qwen3-0.6B

115055 在 c64/node11 以 2×10 核运行，总墙钟 00:31:15，COMPLETED 0:0。Prefill 为 148.352804628 ms。Decode 首次退休在 278.563828292 ms，第二次在 557.430880550 ms，间隔 278.867052258 ms。反馈链为 `264 → 1293 → 882`，两步 top-1 与零历史 FP32 一致，logits 相对 L2 为 0.17129565、0.03156741。两项各有 7,168 笔 KV 写入及 3,584 笔跨步读回，DDR 回调分别 14,734,270 和 38,558,938。原始逐周期适配器 115033 在 c64/node4 以 2×12 核于 01:05:36 正常结束。原版和加速版两个阶段的模拟时间及两步 logits SHA 完全一致。主机墙钟对照条件包括不同节点及核分配。

| 结果、审计或清单 | SHA-256 |
| --- | --- |
| `qwen3-short-fast-01/run-115055/prefill/result.json` | `6a4fd9afdd03e097a51a2a01e4330162cd42eeeab386c1922d9a0755051fa8c2` |
| `qwen3-short-fast-01/run-115055/decode/result.json` | `4b43306de343b78ee419297d28b88fd410fb582bb37b8b037f582db9483a9df8` |
| `audits/qwen3-prefill-115055.json` | `e14de6497437731ee983b39fd6742f0b442c183f9302835d1ea781a93dc22505` |
| `audits/qwen3-decode-115055.json` | `cbcb7eaba21cd51d16bf1cc8806a2fdcc24cdbea8770ec20cd4d4ad2e091be39` |
| `qwen3-short-fast-01/run-115055/output.sha256` | `635ac88b2a69d9b3dd2bc7eacabad1fca4b39afbc6f33198814330a24bb59ad7` |
| `qwen3-zero-reference/ref-115036/qwen3/reference.json` | `5ea2ac7d7af4361b372533e742d91a2efbb62ed433e799de56f57f612ffa9c96` |
| `audits/qwen3-decode-115033.json` | `b4dbae4ba4742691189752ad14579216b18484fa721b1fa666828418a3f2b2b8` |
| `qwen3-short-01/run-115033/decode/result.json` | `02476fba711a97ce1a0adb44546fc4e6df4a5450db319ed35d6aef5c7d30e5b6` |

## 已核验的阶段结果

- Llama 115056.1 的 Prefill 在 c64/node11 正常退出，覆盖 16 层和两个位置，用时 278.601795884 ms。4,096 笔 KV 写入、2,048 笔跨步读回，32,414,406 笔 DDR 回调。该作业的 Decode 在取 argmax 时因词表长度硬编码失败。独立 Prefill 审计 `audits/llama-prefill-115056.json` SHA-256 为 `90770df7f68b67412b7a22da04d8ced277f1fbd412a0627edb522145659d121f`。
- Llama 115128 在 c96/node17 以 10 核运行，00:30:32，COMPLETED 0:0。全词表两次退休间隔 396.343586200 ms，token `7576 → 527 → 539`，与零历史 FP32 两步一致，logits 相对 L2 为 2.9470%、2.5609%。Decode 4,096 笔 KV 写入，2,048 笔读回，62,624,638 笔 DDR 回调。结果 SHA-256 `d3c7bf1ecf7ef42f175eea0b0101f01dc3370e085acf5475d90c177cd105058d`，审计 `audits/llama-decode-115128-v3.json` SHA-256 `a9aecfad99ffdb1c71e3639af4d93d489c1bd7be71ca0d90488287668dfee62e`。
- Gemma 115102 联调两位置、单层、29.721006346 ms，256 笔 KV 写入，128 笔跨步读回。结果 SHA-256 `b00559840e7e00b5725bc86a33d1d07e03f550ce9e3d1028590ad6889735843b`。115107 的 Prefill 第 5 层残差超出 S32，115122 使用显式有计数的饱和操作。
- Granite 115106 联调两位置、单层、7.801003222 ms，实际 router 每次选 8/40 个专家。结果 SHA-256 `71509679499eb12111c3330f64f83af4b6e0e9b216d61323fb91a9e5e671b599`。
- Qwen3.5 115120 联调首个 GDN 层，两位置 32.558220342 ms。69,632 笔递推和卷积状态写入，34,816 笔跨步读回。结果 SHA-256 `e6de21a3385178ebe6a4de13b3ff724f17782b17c4dd775bc7858ed74720d049`。补包 115110 含 250 个张量、7,050,117,120 B，包索引 SHA-256 `b3c357d62dc0c8a8bb5b591c89f132d6b7e34dd1288aaebf4c89dac195c1359f`。
- Falcon 115121 联调首个 Attention/Mamba2 层，两位置 26.758704004 ms，133,376 笔递推和卷积状态写入，66,688 笔跨步读回，另有 64 笔 KV 写入、32 笔跨步读回。结果 SHA-256 `6dd737b95b860a4118278c632f7125fdafb9d37d36e8468358ce4e9c8dcc6056`。
- Granite 115109 的 Prefill 在 c64/node10 跑完两位置 × 32 层，覆盖 64 份路由与 26,940,138 笔 DDR 回调。总模拟时间 248.283146700 ms，结果 SHA-256 `603abdc3758d19c3c2a9f746407ec9bedeca3802fca75bf9902ef61c1aca2cdc`。独立审计 `audits/granite-prefill-115109.json` SHA-256 `8872e8e2699d3f8fa6a4d77a323305933b6c2fe95c0eede3df6d2acc960b0822`。
- Granite 115130 在 c96/node13 以 10 核运行，00:32:43，COMPLETED 0:0。Decode 两次退休间隔 420.874271356 ms。反馈链 `312 → 203 → 18873`，FP32 为 `312 → 203 → 46647`，两步 logits 相对 L2 为 1.8827%、122.0626%。首步 top-1 一致，第二步发生数值分歧。64 份动态专家路由、4,096 笔 KV 读回和 61,053,806 笔 DDR 回调均通过流程审计。结果 SHA-256 `d1176d5a6ecafe31a0b47817aa85c81604622a7534d653b7fc73e801277893f6`，审计 `audits/granite-decode-115130-v3.json` SHA-256 `e96961470717970e9d9e2266a5795ac420803a66bf5a86184127975391fca4c9`。
- Granite 独立路由诊断 115197 在 c64/node1 正常退出，逐字节复现零历史 FP32 两步 logits。候选与 FP32 每层各 8 个专家，第一步 253/256 名额重合，第二步 242/256 重合，后者从第 19 层首次分歧，末层仅 4/8 重合。该对照定位分歧传播的位置，首次数值偏差来源仍需逐层核对。报告 `granite-routes-01/run-115197/comparison.json` SHA-256 `fb9adcf5dcf11ac5b22c95d8ed92f4d78c1dcee7b3750ee2cb293e6e7c75925f`。
- Phi 115103 的 Prefill 在 c96/node15 跑完两位置 × 32 层，用时 923.680199100 ms，66 页、28,738 次局控调用。结果 SHA-256 `c9129235d3ea3690eaea1008c7811518697c6388e839dddac2bb65906f088a01`，独立审计 `audits/phi-prefill-115103.json` SHA-256 `b396ec3132e447562cbefd7160c25297f72d8b4cc5e2bb971a74766bd70350d8`。
- Phi 115129 在 c96/node17 以 10 核运行，01:12:58，COMPLETED 0:0。两次退休间隔 908.406735018 ms。反馈链 `261 → 64535 → 14928` 两步与 FP32 一致，logits 相对 L2 为 28.0415%、4.6292%。4,096 笔跨步 KV 读回，161,029,736 笔 DDR 回调。115103 虽有最后 argmax 的范围常量，离线检查表明本用例两步的全词表最大值都在该范围内，115129 修复后两个 logits SHA、token 和两次退休时间完全相同。115129 结果 SHA-256 `88c26c2a0bf27963371d91d14233bac32c4a96aabbe5cd296d8b336206882f97`，审计 `audits/phi-decode-115129-v3.json` SHA-256 `9d2f12d2ea7ea9c21fd61a0d982ea42a3afe58d943a08f7a7af41dfed14b82bd`。
- Gemma 115122 的 Prefill 在 c96/node17 跑完两位置 × 34 层，用时 1,007.479138870 ms。两位置 47 次残差饱和，4,352 笔跨步 KV 读回，107,628,382 笔 DDR 回调。结果 SHA-256 `e18141d2af6748e48e0856ce96a0733c8315600691aa5b3c1f69dd72584391e5`。
- Gemma 115122 在 c96/node17 以 2×10 核运行，01:02:57，COMPLETED 0:0。Decode 两次退休间隔 829.625648618 ms，反馈链 `8735 → 173449 → 5843`。标准 FP32 首步选出 239781，首步 logits 相对 L2 为 90.1127%。Decode 有 17 次残差饱和、4,352 笔跨步 KV 读回、140,148,536 笔 DDR 回调。结果 SHA-256 `34d0c746885f18fa3c4f1a3ceb11f9b10adf9c49f1b3a15c725b23a5968cd8d7`，审计 `audits/gemma-decode-115122-v3.json` SHA-256 `367674ec3d6dcf7243ce2c84a79f8a833f2854d85f1028e158d6ddc8f8424aae`。
- Qwen3.5 115124 的 Prefill 在 c96/node17 跑完两位置 × 32 层，用时 1,022.092280914 ms。1,024 笔跨步 KV 读回、835,584 笔 GDN 状态读回，122,914,758 笔 DDR 回调。结果 SHA-256 `e6bcae2e261142aecb0e50014167515f914fd36d86c6f3b15a76efecd22674f2`。
- Qwen3.5 115124 在 c96/node17 以 2×10 核运行，01:01:39，COMPLETED 0:0。Decode 两次退休间隔 753.662442348 ms，反馈链 `264 → 846 → 69`，标准 FP32 首步选出 69892。首步 logits 相对 L2 为 81.2655%。Decode 有 1,024 笔跨步 KV 读回、835,584 笔 GDN 状态读回、149,465,964 笔 DDR 回调。结果 SHA-256 `4fc2bb0cc27e78a5e06898a2d474959d6f9094418a086c6f762458ba8c6ce583`，审计 `audits/qwen35-decode-115124-v3.json` SHA-256 `7a7d3e1ddad3bba3b4ec921ee8f9dfad7efd511a1a80b9c7b1693bda5887a341`。
- Falcon Prefill 的 115125.1 在 c64/node1 以 10 核运行，COMPLETED 0:0。115125 批作业因独立 Decode 编译时的归一化权重名错误而 FAILED 1:0。Prefill 覆盖 32 层，两位置 851.727561450 ms、1,024 笔跨步 KV 读回、2,134,016 笔 Mamba2 状态读回、102,746,602 笔 DDR 回调。结果 SHA-256 `87ca1adc9fbf284ec03ae85538fc447dffb3d625feb77589908d28b7f3782c26`。
- Falcon Decode 修正版 115126 在 c64/node1 以 10 核运行，01:05:49，COMPLETED 0:0。两次退休间隔 587.533603224 ms，反馈链 `772 → 532 → 731`，标准 FP32 首步选出 731。首步 logits 相对 L2 为 53.7022%。Decode 有 1,024 笔跨步 KV 读回、2,134,016 笔 Mamba2 状态读回、121,755,156 笔 DDR 回调。结果 SHA-256 `5bdbce92303bc7b81bd387324a8840a763c0ab6d7f4ecd8088683c9f3f57504b`，审计 `audits/falcon-decode-115126-v3.json` SHA-256 `75e04651beb3717304fcafe134137010cb0d0e166824585911a2696cbf00fb40`。

## 候选映射

- Llama 和 Granite 将 64 维头补零到 128 维以复用原生 ATT1。Llama 的 FFN Mid 分置两个 16 KiB S。Phi、Gemma、Qwen3.5 和 Falcon 的 FFN Mid 写入单独 DDR 区后分 K128 读回。
- Gemma 和 Qwen3.5 的 256 维注意力分窗处理完整的 K/V。Gemma 的 1,024 位置窗口完整覆盖本测试；将前 512 个历史位置视为零。Gemma 执行 (1+\gamma) 归一化与 GELU-tanh，用每字 40 周期的候选时序。
- Granite 使用实际投影产生 router logits，取 top-8，并在回放中动态从 DDR 读取专家投影。时钟显式计入路由、结果累加和搬运。加权累加与路由时序尚未用 RTL 校准。
- Qwen3.5 的 24 个 GDN 层和 Falcon 的 32 个 Mamba2 层通过八笔在途的 DDR 窗口执行卷积和递推状态读写。状态在 S32/Q16 与局控内部 FP32 算术间转换。32-lane 状态算术周期是候选值。每个模型第二步核对前一步的全部状态回调。全包保持原始权重和校验索引，实际投影采用 W8A16；词表以 HEAD16 完成，补齐行不参与 argmax。

## 复跑与审计

登录服务器后进入表中 `run-<job>` 的上级目录。使用该目录的冻结脚本和上游清单。下例的 `-n2 -c10` 分别运行 Prefill 和 Decode 各 10 核。单阶段仅保留一个模式并使用 `-n1`。多模型准备按节点配额分批，c96 可用 8×12 核，60 核配置可用 6×10 核。

环境为 Slurm 23.11.5、Singularity CE 4.3.4、ORFS 容器 `orfs-current-repacked.sif`。容器内 Python 3.12.7、NumPy 2.2.6、PyTorch 2.10.0+cpu、Transformers 5.20.2、safetensors 0.8.0。加速适配器的 DRAMsim3 库 `run-113164.dram.so` SHA-256 为 `1e74820e1cbe48b447e29fd9f98f55c54b4bd4f3fb493b0f2d8e1317c3cd8c1b`，配置 `DDR4-single-channel.ini` SHA-256 为 `748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766`。两个独立通道使用同一个单通道配置。

```bash
R=/public/home/yuzelu/Melodydt/runs/issue-274
cd "$R/hybrid-short-01"
sha256sum -c source.sha256
sha256sum -c upstream.sha256
sbatch --parsable --job-name=mdt-274gdnfull -p c96,c64 -N1 -n2 -c10 -t 08:00:00 -o slurm-%j.log fast_qwen3_short.sbatch qwen35 prefill decode
sacct -X -j 115124 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
tail -n 10 run-115124/prefill.log run-115124/decode.log
sha256sum -c run-115124/output.sha256
```

使用 `audit_short.py` 核对两位置、层数、程序页、DDR 回调、跨位置状态和反馈 token。Decode 审计可提供 `--reference`，仅在输入 token 一致时计算该步的 logits 相对 L2。所有日志、MC 页面、LC 描述符、权重映像和状态结果均保存在授权服务器。冻结参考的 SHA-256 索引为 `dense-zero-reference-02/ref-115104/reference.sha256`（`3ee5aba543abeaeab427edf879c2068313492fcffa6acf632b9585230dec8510`）和 `hybrid-zero-reference-01/ref-115123/reference.sha256`（`fa000dcfec03304c6d56c380e1a6bb61536f6809a84051c39bbefc4bf7d17e00`）。

### Prefill 数值对照

将最后位置的残差在审计中用实际权重做离线最终 RMS，再与独立 FP32 输出比较。离线运算不计入 Prefill 时间。

| 模型 | 相对 L2 | 余弦相似度 | 审计 SHA-256 |
| --- | ---: | ---: | --- |
| Qwen3 | 2.7991% | 0.9996083 | `a167b2a603d7bfb700f8f99aaad026d98aa0c457331391fa77eb740714848ef3` |
| Llama | 2.8073% | 0.9996060 | `23011cf6306e61404e8578e240be1e1d1a9040cc956dfc1b16b7702235fbe384` |
| Phi | 2.0980% | 0.9997805 | `6813fe077d8e2ec1acd5b1d46b551d8eb66f0f643363564502d770796bd02068` |
| Granite | 2.9760% | 0.9995573 | `06ea4604384f18f8e42fe7db3414a2947fefa3d8e9f4a719dc14c2d33837c04d` |
| Gemma | 72.5720% | 0.7848847 | `adfc5bd64a54de21e1ca63be856f18e1d4c8f805f33fb1e027c6d020a228f8e7` |
| Qwen3.5 | 1.5258% | 0.9998837 | `ed2686c6dc46278e6e9c238caf3940903dd059ec1eb1e10c59a3ccf6f3d4afbb` |
| Falcon | 0.3633% | 0.9999935 | `1983426f8733773c628f50a7d3a4dcd31ba7645af2cf5ecac58bd62393cd6cfe` |

### Decode 同输入对照

115250 在 c96/node15 用 3×10 核运行，COMPLETED 0:0，复现了三个模型的独立 FP32 第一步，并在第二步使用各回放第一步实际选出的 token。输出清单 `decode-aligned-reference-01/output-115250.sha256` 已逐项核验，SHA-256 为 `a009884985d5199cfc096c869b04be938018f70efbda72e25509df979822e3ed`。

| 模型 | 第二步共同输入 | 候选 top-1 | FP32 top-1 | logits 相对 L2 | 同输入审计 SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- |
| Gemma | 173449 | 5843 | 10720 | 97.6143% | `63297d3ce758f1a2a8920b5f472334c9e83be049e5df1593d7c05c5c3a4ab281` |
| Qwen3.5 | 846 | 69 | 264 | 91.9639% | `e69381507f8d5a4cc223780f0ef7c237339e33a18ed65b35854b9aa827578e15` |
| Falcon | 532 | 731 | 731 | 34.6192% | `3643ee63989b97766b121e8f254fb57cfe41ca3600c02e4f2045025e7a0a6c51` |

下表的 `output.sha256` 已在服务器上逐项读回校验。作业步骤例外及独立审计详见上文。

| 作业 | 文件数 | `output.sha256` 的 SHA-256 |
| --- | ---: | --- |
| 115055 | 497 | `635ac88b2a69d9b3dd2bc7eacabad1fca4b39afbc6f33198814330a24bb59ad7` |
| 115033 | 497 | `229e161a69b3a7bd8bbf4a11438d28e8c9bb642919ea9baa06055a016e8d441f` |
| 115056 | 232 | `69c79427a8f89746c82fbbb9125a9ecb4cad4936445d51f3d9ac931db3f341c7` |
| 115128 | 124 | `a3403bb9e29ae10b8994625f0f8f768a1c62c1ec42d6be8d5f92a37df04dc1f7` |
| 115103 | 433 | `10accf0d1b77cb53024a19ebae29e30a2d672bcb7c0d2523e4e2b11ba1ad4824` |
| 115129 | 220 | `5e5e0ec24be80f6770b90f3bce5c42383fba8d986e6db46681f87e2a8d2dd9e8` |
| 115122 | 733 | `ec825fade42e9951ebfe4eb2ba8ab2fbc635c490397c6abb46a981da323329bb` |
| 115109 | 551 | `74592c1e39c25decaa9638ca91a1ee4e11c0984682a4044e1653416bd1caae35` |
| 115130 | 284 | `d23955d1043932b3228321abc49e5a924846386940634cdbf070ca42f1a11344` |
| 115124 | 561 | `9b2dbdf86fe56f0948999a5b8954e6c510519239bf4e60dccddaa4168b4c87cf` |
| 115125 | 443 | `797c10876e7bb7003f572492d3ad9fdc662e90185d969194062888d73d3d6283` |
| 115126 | 284 | `2c427881bb570962ab54efd8d0a9f08e91f1a8b45f67f79cc8e80c27de8b1751` |
