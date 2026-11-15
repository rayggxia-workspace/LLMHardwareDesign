# 七模型 512-bit SRAM 吞吐优化

[Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) · [PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) · [全层基线](RESULTS.md)

基线源码为 `009a9eaf368ef0db5e2f396e70a15c410de1d927`。各实验固定输入、检查点、投影权重格式、512-bit 数据 SRAM 与程序存储写宽、3,334 ps 核周期和双通道 DDR 配置。吞吐来自该候选 TLM 的模拟时间。单、四层初筛只覆盖前缀，整模型收益使用全层短 Prefill 和两步 Decode 另行核验。

## 基线差距

DDR 读数是两位置、全层 Prefill 返回的 64 B 事务数，含重复读取、控制和数据。Decode 的层、词表两列取第二次退休前相应母控页的实际执行时间。退休间隔还含页外准备、装页和边界读回，因此相加会略低于退休间隔。

按事务字节数除以 Prefill 总模拟时间，七组有效读取速率为 6.35–7.59 GB/s，模型之间的读取量相差最高 8.23 倍。读取量与权重供给上的等待解释了大部分 Prefill 差距。四层 A/B 中增加权重在途读数即有两位数吞吐收益，保留 FFN 中间值或缩小短历史 KV 的增幅更小。

| 模型 | Prefill DDR 读（百万笔） | Decode 第二步层页（ms） | 词表页（ms） | 词表页占 Decode |
| --- | ---: | ---: | ---: | ---: |
| Qwen3-0.6B | 14.727 | 234.677 | 44.061 | 15.8% |
| Llama-3.2-1B | 32.410 | 322.897 | 73.367 | 18.5% |
| Granite MoE | 26.932 | 399.532 | 21.209 | 5.0% |
| Phi-4-mini | 107.918 | 737.466 | 170.804 | 18.8% |
| Gemma-3-4B | 107.576 | 642.384 | 187.015 | 22.5% |
| Qwen3.5-4B | 121.168 | 576.443 | 177.099 | 23.5% |
| Falcon-H1-3B | 98.417 | 540.480 | 46.847 | 8.0% |

- **Qwen3** 的两位置 Prefill 读取量最小。Decode 的 28 层都走注意力，读取历史 KV 会拉长层页。先扩充每条权重记录的取数窗口。
- **Llama** 虽只有 16 层，2048 维输入和 8192 维 FFN 使 Prefill 读取量达 Qwen3 的 2.20 倍。32 个查询头在基线以 128 维格式执行，包含 64 维补零及 V 分组重复取数。另测真实 64 维缓存。
- **Granite** 每 token 每层只激活实际 top-8/40 专家，Prefill 读数低于 Llama。Decode 第二步需执行 32 层，层页比 Llama 多 76.635 ms。较短的 49,155 词表只抵消 52.158 ms。四层 Prefill 的 MoE 聚合服务（含专家投影）占基线总时间约 65.5%。另测真实 64 维缓存。
- **Phi** 的融合投影仍要从 DDR 供给实际矩阵。32 层、24 个查询头、8192 维 FFN 及 200,064 词表使两阶段都有较重的权重、缓存和词表访问。四层前缀的普通投影占 Prefill 时间约 92.9%。另测复用 Context SRAM 缓存 FFN 中间值。
- **Gemma** 的 Prefill 读取量接近 Phi，另有四类层归一化、256 维注意力和 10,240 维 GELU FFN。它在 Decode 的层页少于 Phi，而 262,208 词表耗时居七者之首。此短测试最大历史长度 514，小于 1,024 的窗口，滑动层在本用例仍需读取全部有效历史。另测 FFN 缓存，基线 S32 数值偏差单独保留。
- **Qwen3.5** 的全层 Prefill 读取量最大。Decode 只有 8 层走全注意力，其余 24 层走 GDN，少读重复的注意力历史，同时需读回 835,584 笔递推或卷积状态。其 Decode 层页比 Phi 少约 161 ms，248,320 词表抵消了部分差异。另测 FFN 缓存。
- **Falcon** 每层兼有 Attention 和 Mamba2，状态跨步读回达 2,134,016 笔。它的全层 Prefill 读取量比 Qwen3.5 少约 1,755 万笔，65,537 词表令第二步词表页比 Qwen3.5 少 130.251 ms。另测 FFN 缓存。

## 权重窗口初筛

基线 P 同时保留至多四条记录，各记录通常只有一笔读取在途。窗口 4 提前提交同一记录的四笔 DDR 读取，在返回后按地址顺序拼接。每通道 credit 上限仍为 32。DramSim3 的时间线上实际发生的排队顺序允许变化。每组比较都核对实际指令页与映像 SHA、两位置残差、状态写入及读回、DDR 读取与回调。以下百分数是吞吐增幅。

| 模型 | 层数 | 窗口 1（ms） | 窗口 4（ms） | 增幅 | Slurm |
| --- | ---: | ---: | ---: | ---: | --- |
| Qwen3 | 1 | 5.307888 | 3.996696 | 32.81% | 115261 |
| Llama | 4 | 69.650664 | 50.053559 | 39.15% | 115263 |
| Phi | 4 | 115.488360 | 80.011519 | 44.34% | 115264 |
| Gemma | 4 | 118.585826 | 78.754171 | 50.58% | 115265 |
| Granite | 4 | 31.078931 | 22.604797 | 37.49% | 115266 |
| Qwen3.5 | 4 | 127.869872 | 91.241105 | 40.15% | 115267 |
| Falcon | 4 | 106.553850 | 77.357472 | 37.74% | 115268 |

Qwen3 首层窗口 2 为 4.235167 ms，窗口 8 为 3.995362 ms。窗口 4 相比窗口 8 的用时只多约 0.03%，测得每通道峰值分别为 16、32 笔。全层先采用窗口 4。

## 模型适配初筛

| 模型 | 在窗口 4 基础上的改动 | 基线（ms） | 候选（ms） | 额外吞吐 | 减少 DDR 读／写 | Slurm |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Llama | 64 维 KV 行和一次 V 读取 | 50.053559 | 49.678744 | 0.75% | 12,416 / 512 | 115273 |
| Granite | 64 维 KV 行和一次 V 归约 | 22.604797 | 22.308264 | 1.33% | 9,344 / 512 | 115274 |
| Phi | 复用 Context SRAM 保留前 4,096 个 FFN 中间值 | 80.011519 | 78.327126 | 2.15% | 49,136 / 2,048 | 115269 |
| Gemma | 同一 FFN 缓存 | 78.754171 | 77.025312 | 2.24% | 40,944 / 2,048 | 115270 |
| Qwen3.5 | 同一 FFN 缓存 | 91.241105 | 89.671341 | 1.75% | 40,950 / 2,048 | 115271 |
| Falcon | 同一 FFN 缓存 | 77.357472 | 75.656548 | 2.25% | 40,952 / 2,048 | 115272 |

FFN 缓存沿用原有 Context 的 16 KiB 容量。64 维缓存仍走 512-bit SRAM 端口，KV 每行由 512 B 变为 256 B，候选在八行窗口内复用 V 读取。该局控时间模型需要独立 RTL 校准。所有优化比较要求对当前基线的残差和词表输出逐字节一致，原基线与 FP32 的差异另见结果记录。

## 全层 A/B

| 模型 | 候选 Prefill（输入 token/s） | 候选 Decode（token/s） | 运行目录 |
| --- | ---: | ---: | --- |
| Qwen3，权重窗口 4 | 17.897215（+32.76%） | 3.866890（+7.83%） | `opt-weight-window-01/run-115262` |
| Qwen3，再复用 128 维 V | 18.050887（+33.89%） | 4.948742（+38.00%） | `opt-qwen3-vreuse-01/run-115288` |
| Llama | 10.065466（+40.21%） | 4.179466（+65.65%） | `opt-full-01/run-115282` |
| Granite | 11.222629（+39.32%） | 4.693444（+97.53%） | `opt-full-01/run-115283` |
| Phi | 3.192357（+47.44%） | 1.330067（+20.82%） | `opt-full-01/run-115284` |
| Gemma | 3.056720（+53.98%） | 1.549485（+28.55%） | `opt-full-01/run-115285` |
| Qwen3.5 | 2.786758（+42.42%） | 1.683725（+26.90%） | `opt-full-01/run-115286` |
| Falcon | 3.307114（+40.84%） | 2.164785（+27.19%） | `opt-full-01/run-115287` |

Qwen3 全 28 层 Prefill 用时由 148.352804628 ms 降至 111.749228710 ms。两位置残差逐字节一致，指令页面、DDR 事务总数和 KV 读写一致。审计 `audits/qwen3-full-prefill-115262.json` SHA-256 为 `12f79934238a56f4945bbd838e3ed9eedf6bccb3e891f50b8356406b2bdb2fc3`。

115262 于 c96/node15 正常结束，2×10 核，墙钟 00:20:06。Qwen3 Decode 由 278.867052258 ms 降至 258.605784148 ms。两步候选与基线残差、logits 和 token 逐字节一致，程序、KV 和 DDR 事务总量一致。Decode 审计 `audits/qwen3-full-decode-115262.json` SHA-256 为 `3b58a513b192e06c8bb4c104666cdf353a2a29f969798f7f55c5328fbefef6f9`。497 个输出文件已逐项重验，`output.sha256` 的 SHA-256 为 `dfdcc4f224f755322f803cd259e36fa284bbfe3ab95c4164824ac86bbf368181`。

在窗口 4 的 Qwen3 中，跨两位置 Prefill 的 P 投影服务累计 74.598 ms，注意力服务为 2.188 ms。Decode 第二步 P 投影 37.270 ms，ATT1 161.827 ms，占退休间隔 62.6%。115288 保留 128 维 K/V 行，在相同 512-bit 端口和八行 SRAM 窗口内合并同一查询头的 V 读取。实际将每历史行每查询头的 V 读取从 32 笔降至 8 笔，两步总 DDR 读减少 11,042,304 笔，第二步 ATT1 时间降为 105.304 ms。较窗口 4 的吞吐另增 0.86%（Prefill）和 27.98%（Decode）。115288 在 c96/node13、2×12 核于 00:12:23 正常结束。独立 A/B SHA-256 为 `4f7a3ce30ab11437f2a03a84f15ffa87868fbf5c8c250683413098c4f509ed61` 与 `75e0209a53c5993a27ca47ee52e18e77d6f35baebfdd5ecbbf1526e90f94acf6`。

Llama 的全 16 层 Prefill 减少 49,664 笔 DDR 读取和 2,048 笔写入，Granite 的全 32 层分别减少 74,752 和 4,096。两组均保持残差一致，且 64 维的每位置 KV 状态均完成写入和跨位置回读。Prefill 审计 SHA-256 分别为 `096e768c694c01b8dcfe62121171a95b0899bca7b8c402fab4e9678aa3b52f66` 和 `d3b4145323c901bfc0a805a521cef42f21fde66c024869bc913c67bbe69352b2`。

Llama 115282 和 Granite 115283 在 c96/node15 各用 2×12 核，分别于 00:15:18 和 00:14:25 正常结束。Decode 的新旧残差、词表结果及 token 一致，Granite 的 64 份动态专家路由也一致。紧凑 KV 和 V 读取复用合计减少 16,826,880／25,240,576 笔两步 DDR 读。其中每历史行每查询头的 K+V 由 40 笔减至 8 笔，解释了两组的大部分事务减少量。Decode 审计 SHA-256 分别为 `5ed67ed4008e5aad3792fb485eee345ef111a322bd131d194b700e98a3935ea2` 与 `666865d7a8cb9522ddc684413c17d2144d26ac431fbcb3aad97e7a68805477fc`。

两模型的整层 Decode 增幅同时包括权重窗口和改用紧凑 KV。四层短 Prefill 补做了仅改变 KV 的对照。Qwen3 的 V 读取 A/B 还改变了 SRAM staging 和归约服务的建模。DDR 计数覆盖两步，吞吐计时为两次退休之间的单步间隔。跨步状态对账逐笔检查提交、回读与覆盖，本次回执的逐字节 SHA 指最终残差和词表 logits。

优化后的 Granite Decode 反超 Llama。第二步层页 Granite 仍多 24.178 ms，但词表页少 50.431 ms。两项差值接近实际退休间隔的 26.202 ms 差距。

Qwen3.5 115286 在 c96/node14 以 2×12 核运行，00:40:58 正常结束。两个阶段各减少 327,600 笔 DDR 读及 16,384 笔写，KV 和 GDN 递推读回一致。第二步词表仍耗 169.617 ms，占新退休间隔的 28.6%。Prefill、Decode 审计 SHA-256 分别为 `f5e4f4fdb5389b62ad43e9484c2bf871f0c7cb15b2855c9c29b8825d9deb8e27` 与 `6425585852b13db51ef9af0d07665395adb499b8440a34d8b7faf39e057d725e`。

Falcon 115287 在 c96/node13 以 2×12 核运行，00:35:09 正常结束。两个阶段各减少 327,616 笔 DDR 读及 16,384 笔写，KV 和 Mamba2 递推读回一致。第二步 Mamba2 服务仍耗约 34.589 ms。Prefill、Decode 审计 SHA-256 分别为 `d7d66004403df89649a776648ad822901099d7873aa5a2b0a6e291ab7fc85c93` 与 `9d70cf3cb75ca594d6ba68b88ad4e27542042f8eb1f44e4671e841ec278584b7`。

Phi、Gemma 的全层 Prefill 分别完成于 626.496310874 ms 和 654.296059712 ms。两模型分别减少 393,088 和 348,024 笔 DDR 读，所有残差与基线一致。Prefill 审计 SHA-256 分别为 `01856124bbcb05946f9ebb7961fe975320b399a0d883df7380f9800d5a6d4a61` 和 `44215307269f0b00980f4ecbca13eeb6d5687300e3700aeb8fe93a99ccf75a56`。

Phi 115284 在 c96/node14 以 2×12 核于 00:52:51 正常结束。Decode 从 908.406735018 ms 降至 751.842001666 ms。两步完整词表与残差一致，分别核对两次退休及 4,096 笔跨步 KV 读回。第二步层页仍耗 588.578 ms，词表页 163.113 ms。Decode 审计 SHA-256 为 `d6a22bc1952259c2ebd11ff9d0bd56aaafc11f25d4d8545f464dfb54ea806609`。

Gemma 115285 在 c96/node14 以 2×12 核于 00:42:44 正常结束。Decode 由 829.625648618 ms 降至 645.375575972 ms，两个输出和基线一致，仍记录 17 次 Decode 残差饱和。候选的第二步词表页仍耗 179.108 ms。Decode 审计 SHA-256 为 `e2a8b3d8b626f39c9749c9d89c5364113b02c48098213bc6de7312d0ece2590a`。

115280 证明可选的 C++ 主机端投影算术与归档 Python 在 4,096 组 W8A16 和 HEAD16 用例一致，包括非法填充、scale 及算术溢出。对 Qwen3 首层窗口 4，模拟时间、结果、计数与分项时间完全相同。审计 `audits/qwen3-native-math-115280.json` SHA-256 为 `850314731bf56912d686707a127bfd64643d63de988c12750516170235cf57af`。Qwen3 的 V 复用和其余六模型全层作业启用此主机算术。

GCC 8.5.0 编译的主机算术验证库 SHA-256 为 `77e4420fac9f0550f24cfa9198f4d3167b99a4dde2a65964906caaacdefebf07`。整层对账脚本服务器版本 `audits/compare-short-v3.py` SHA-256 为 `71feffb55123942fa336156f7e30221ee7f2fb6aedb43cc489f7d5489eae144d`。

## 运行与复核

服务器 `yuzelu@10.129.166.172`，任务根 `/public/home/yuzelu/Melodydt/runs/issue-274`。以下路径均相对此根。

| 运行目录 | 源码清单 SHA-256 |
| --- | --- |
| `opt-weight-window-01` | `9772afb604d490f1f8790c68a778e2d06dd7c0e54697ddd4b8bad6e345415fd1` |
| `opt-ffn-context-01` | `ce1b2dc00b7a288c3406e1cd67637ed130edb0f6367df859ac4edca70c72bf76` |
| `opt-compact-kv-01` | `4abb6b390515815180810cc63eebed47a7c6bb5dc90ad0a8379753f9238e30e3` |
| `opt-full-01` | `9ca0d5bd5c682fe47a639607ffe82130444d110ae614efeb2b6b4998237aab77` |
| `opt-qwen3-vreuse-01` | `192304e2c10b0d7c2ca036fb080b5bb8119c0f815391db2aecf81d9cfba48e57` |

四层 A/B 的报告在服务器 `audits/`，对应 `<模型>-weight-<作业号>.json`、`<模型>-mid-<作业号>.json`、`<模型>-kv64-<作业号>.json`。每次回放的 `progress.json` 有逐页模拟时间，`result.json` 有各组描述符从发射到分派及从分派到完成的累计时间。Granite 的专家投影耗时计在 MoE 局控内部。

已对以下冻结运行的 `output.sha256` 逐项核验。

| 作业 | 文件数 | 输出清单 SHA-256 |
| --- | ---: | --- |
| 115262 | 497 | `dfdcc4f224f755322f803cd259e36fa284bbfe3ab95c4164824ac86bbf368181` |
| 115282 | 243 | `b388c3e89c34025a069d12a3f2cb29fa660af0446baa5654e934c968dee5441d` |
| 115283 | 563 | `6dbcc3d102e46cf8c6e2aed39fc79c9dbababe2b0ed6488c62044c2950b73911` |
| 115284 | 435 | `0986c9cca0cf66cdb31bd409cad7836ed958ef9147c834d0c149b0eabd2425c3` |
| 115285 | 735 | `ab152a084d6a5775b07fca2cdc825b7798fa253ee94308317184df4f09232f1d` |
| 115286 | 563 | `ecec40b1d17f1f3a0b2ab3b613b61f72955417e56162e9da1416d05bf6ba216c` |
| 115287 | 563 | `d04c1ba37e2ed7cd173f2af1f875359dd08bd05e06292b0d4de9d422d841870a` |
| 115288 | 499 | `21bb2403af0ee47f9d2d7b474fd27c1f7d49ff50bef1aaecda7a1ec80a32b27f` |

```bash
R=/public/home/yuzelu/Melodydt/runs/issue-274
cd "$R/opt-weight-window-01"
sha256sum -c source.sha256
sha256sum -c upstream.sha256
sacct -X -j 115261,115262,115263,115264,115265,115266,115267,115268 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
python3 "$R/opt-compact-kv-01/compare_short.py" run-115263/slice-w1 run-115263/slice-w4 --same-plan
sha256sum -c run-115263/output.sha256

cd "$R/opt-full-01"
for m in llama granite phi gemma qwen35 falcon; do
  variant=cache
  if [[ "$m" == llama || "$m" == granite ]]; then variant=kv64; fi
  sbatch --parsable --job-name="mdt-274f-$m" -p c96 -N1 -n2 -c12 -t 06:00:00 -o slurm-%j.log --export=ALL,MDT_274_NATIVE_MATH=1 fast_qwen3_short.sbatch "$m" "prefill:4:$variant" "decode:4:$variant"
done
sacct -X -j 115282,115283,115284,115285,115286,115287 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed

cd "$R/opt-qwen3-vreuse-01"
sbatch --parsable --job-name=mdt-274qvreuse -p c96 -N1 -n2 -c12 -t 06:00:00 -o slurm-%j.log --export=ALL,MDT_274_NATIVE_MATH=1 fast_qwen3_short.sbatch qwen3 prefill:4:tile128 decode:4:tile128
sacct -X -j 115288 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
```

独立对账脚本 `compare_short.py` 可读入两组回放，核验数据与状态边界并提取分项时间。加 `--same-plan` 时对账地址、映像 SHA、调用计数和 DDR 事务总量，适用于只改变权重窗口。系列结果、日志和再现所需映像均保留在服务器。
