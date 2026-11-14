# 七模型短程回放结果

任务 [#274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274)，交付 [PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275)。继承 [PR #260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260) 的 `55620f173f2ad540efade8a552c35e9dba0f43c0`。服务器 `yuzelu@10.129.166.172`，结果根 `/public/home/yuzelu/Melodydt/runs/issue-274`，各运行目录固定 `source.sha256` 和 `upstream.sha256`。

短 Prefill 将两个位置推进到最后一层残差，吞吐为 2 除以总模拟时间。Decode 从 512 个零历史位置开始，按全词表选出并反馈 token，吞吐取两次全词表退休之间的间隔。首步输入 token 来自实际历史上的 FP32 参考。两种测量采用 PR #260 的事务级时间线，串行 P 调度和模型专用局控形成候选模型，RTL、物理时序及数值资格待核验。Slurm 用时单独记录。

| 模型 | 短 Prefill（输入 token/s） | Decode（token/s） | 作业与结果目录 |
| --- | ---: | ---: | --- |
| Qwen3-0.6B | 13.481376 | 3.585938 | 115055 完成，`qwen3-short-fast-01/run-115055` |
| Llama-3.2-1B | 7.178705 | 运行中 | Prefill `qwen3-short-fast-01/run-115056`，Decode `llama-short-03/` |
| Phi-4-mini | 运行中 | 运行中 | 115103，`phi-short-02/run-115103` |
| Gemma-3-4B | 运行中 | 运行中 | 115122，`gemma-short-03/run-115122` |
| Granite MoE | 运行中 | 运行中 | 115109，`granite-short-01/run-115109` |
| Qwen3.5-4B | 运行中 | 运行中 | 115124，`hybrid-short-01/run-115124` |
| Falcon-H1-3B | 运行中 | 运行中 | Prefill 115125，`hybrid-short-01/run-115125`，Decode 115126，`hybrid-short-02/run-115126` |

## Qwen3-0.6B

115055 在 c64/node11 以 2×10 核运行，总墙钟 00:31:15，COMPLETED 0:0。Prefill 为 148.352804628 ms。Decode 首次退休在 278.563828292 ms，第二次在 557.430880550 ms，间隔 278.867052258 ms。反馈链为 `264 → 1293 → 882`，两步 top-1 与零历史 FP32 一致，logits 相对 L2 为 0.17129565、0.03156741。两项各有 7,168 笔 KV 写入及 3,584 笔跨步读回，DDR 回调分别 14,734,270 和 38,558,938。115033 已完成部分中的 Prefill 时间与 115055 一致。

| 结果、审计或清单 | SHA-256 |
| --- | --- |
| `qwen3-short-fast-01/run-115055/prefill/result.json` | `6a4fd9afdd03e097a51a2a01e4330162cd42eeeab386c1922d9a0755051fa8c2` |
| `qwen3-short-fast-01/run-115055/decode/result.json` | `4b43306de343b78ee419297d28b88fd410fb582bb37b8b037f582db9483a9df8` |
| `audits/qwen3-prefill-115055.json` | `e14de6497437731ee983b39fd6742f0b442c183f9302835d1ea781a93dc22505` |
| `audits/qwen3-decode-115055.json` | `cbcb7eaba21cd51d16bf1cc8806a2fdcc24cdbea8770ec20cd4d4ad2e091be39` |
| `qwen3-short-fast-01/run-115055/output.sha256` | `635ac88b2a69d9b3dd2bc7eacabad1fca4b39afbc6f33198814330a24bb59ad7` |
| `qwen3-zero-reference/ref-115036/qwen3/reference.json` | `5ea2ac7d7af4361b372533e742d91a2efbb62ed433e799de56f57f612ffa9c96` |

## 已核验的阶段结果

- Llama 115056 的 Prefill 覆盖 16 层和两个位置，用时 278.601795884 ms。4,096 笔 KV 写入、2,048 笔跨步读回，32,414,406 笔 DDR 回调。该作业的 Decode 在取 argmax 时因词表长度硬编码失败。独立 Prefill 审计 `audits/llama-prefill-115056.json` SHA-256 为 `90770df7f68b67412b7a22da04d8ced277f1fbd412a0627edb522145659d121f`。
- Gemma 115102 联调两位置、单层、29.721006346 ms，256 笔 KV 写入，128 笔跨步读回。结果 SHA-256 `b00559840e7e00b5725bc86a33d1d07e03f550ce9e3d1028590ad6889735843b`。115107 的 Prefill 第 5 层残差超出 S32，115122 使用显式有计数的饱和操作。
- Granite 115106 联调两位置、单层、7.801003222 ms，实际 router 每次选 8/40 个专家。结果 SHA-256 `71509679499eb12111c3330f64f83af4b6e0e9b216d61323fb91a9e5e671b599`。
- Qwen3.5 115120 联调首个 GDN 层，两位置 32.558220342 ms。69,632 笔递推和卷积状态写入，34,816 笔跨步读回。结果 SHA-256 `e6de21a3385178ebe6a4de13b3ff724f17782b17c4dd775bc7858ed74720d049`。补包 115110 含 250 个张量、7,050,117,120 B，包索引 SHA-256 `b3c357d62dc0c8a8bb5b591c89f132d6b7e34dd1288aaebf4c89dac195c1359f`。
- Falcon 115121 联调首个 Attention/Mamba2 层，两位置 26.758704004 ms，133,376 笔递推和卷积状态写入，66,688 笔跨步读回，另有 64 笔 KV 写入、32 笔跨步读回。结果 SHA-256 `6dd737b95b860a4118278c632f7125fdafb9d37d36e8468358ce4e9c8dcc6056`。

## 候选映射

- Llama 和 Granite 将 64 维头补零到 128 维以复用原生 ATT1。Llama 的 FFN Mid 分置两个 16 KiB S。Phi、Gemma、Qwen3.5 和 Falcon 的 FFN Mid 写入单独 DDR 区后分 K128 读回。
- Gemma 和 Qwen3.5 的 256 维注意力分窗处理完整的 K/V。Gemma 的 1,024 位置窗口完整覆盖本测试；将前 512 个历史位置视为零。Gemma 执行 (1+\gamma) 归一化与 GELU-tanh，用每字 40 周期的候选时序。
- Granite 使用实际投影产生 router logits，取 top-8，并在回放中动态从 DDR 读取专家投影。时钟显式计入路由、结果累加和搬运。加权累加与路由时序尚未用 RTL 校准。
- Qwen3.5 的 24 个 GDN 层和 Falcon 的 32 个 Mamba2 层通过八笔在途的 DDR 窗口执行卷积和递推状态读写。状态在 S32/Q16 与局控内部 FP32 算术间转换。32-lane 状态算术周期是候选值。每个模型第二步核对前一步的全部状态回调。全包保持原始权重和校验索引，实际投影采用 W8A16；词表以 HEAD16 完成，补齐行不参与 argmax。
