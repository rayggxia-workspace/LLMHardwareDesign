# 吸收 PR #272 RTL 调度后的七模型重测

[Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) · [PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) · [PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)

对照基线为 [上一轮 512-bit 优化](OPTIMIZATION.md)的 `50ed5b09d5b9fd94bd3769ecd3c5bb1d9c002f75`，上游 PR #272 固定 `ebd590def47d2da6b46f04a68931c1d47f11538e`。测试仍用相同检查点、程序和起始 token。短 Prefill 为两个位置，计到第二个位置末层残差。两步 Decode 从 512 个零历史位置开始，计两次全词表退休间隔。数据 SRAM 和程序存储写宽为 512 bit，核周期 3,334 ps。双通道 DDR 配置及每通道 32 credits 同上一轮。

## 接入的调度

| PR #272 机制 | 七模型接入范围 |
| --- | --- |
| ATT1 V 选择读取、回包与 S 写确认解耦、双窗口回填及 Dot 读流水 | Phi、Falcon 直接用冻结 `Attention(..., kv_window=8, pipeline=True)`。Qwen3、Llama、Granite 保留上一轮每行 V 读取复用，分别用 128/64/64 维行。Gemma、Qwen3.5 保留 256 维注意力。在三种行布局上按相同的两窗口机制实现回填和读出，共享原 512-bit S 端口。 |
| FFN 四权重 bank | Gate、Up、Down 和 Granite 实际路由的专家矩阵使用冻结 `Projection(..., rtl_weight_fetch=True)`。记录包含四 bank、32 笔总在途、物理队列、回包缓冲和登记 ACK，使用七模型原有串行投影路由。 |

上一轮的权重窗口仍用于 QKV、O、递推投影、router 和词表。各模型原有 FFN 中间值存储和 KV 行地址保持。提前 EXEC 和两个被上游淘汰的 HEAD16 原生候选保持关闭。PR #272 的 Qwen2.5 成绩不直接换算为这七个模型的成绩。

## 原生 ATT1 验证

在服务器隔离目录 `pr272-native-01` 重跑了 PR #272 固定 C380 夹具及正常／背压两个工况。Verilator 5.042，c64/node4，每组 10 核。第一次提交 115325/115326 在准备阶段缺少归档的 `check_softmax.py`，没有进入 RTL。复制并核对该文件后，115329/115330 均正常退出。

| 工况 | 同分片串行（拍） | PR #272 双窗口与共享 S（拍） | 耗时减少 |
| --- | ---: | ---: | ---: |
| 正常 | 75,877 | 65,932 | 13.11% |
| 背压 | 282,528 | 279,968 | 0.91% |

两组均收到 9,120 笔 KV 回包和 54,087 笔 SRAM 应答。输出逐字与冻结参考一致，双方各 22 项输出清单全部通过。回执 `pr272-native-01/native-audit.json` SHA-256 为 `e293a13b27fb28c060dbfc1967c0b2ee700b9d9e2c4aa81bfbf8ee4e1d2f2bba`。原生夹具的数据 SRAM 为 128 bit，七模型全层重测使用 512-bit TLM。

原生四 bank FFN 回归采用 PR #272 `63781d3c7120f05b127d130c86e91e292feb09bc` 的 C639 探针夹具，输入和权重与该 PR 的 113287 相同。115347 在 c96/node14 使用 12 核跑正常／背压两组，目录 `pr272-ffn-native-01/run-115347`。它复跑保留的 RTL 路径，用于核验功能和事务，逐模型吞吐见 512-bit TLM 结果。

## 运行与验证

服务器登录 `yuzelu@10.129.166.172`，任务根 `/public/home/yuzelu/Melodydt/runs/issue-274`。七模型工作目录 `pr272-tlm-01`，`source.sha256` 的 SHA-256 为 `0232df0a781d55b3f028dfad3c2813473ba71eece1428fd7913838ca74dca27f`。三个不改字节的上游模块来自 `/public/home/yuzelu/Melodydt/runs/issue-270/ffn-weight-05/tlm/source`，其中 Attention 和 Projection 为避免遮盖基线模块而另命名。固定内容如下。

| 冻结模块 | SHA-256 |
| --- | --- |
| `pr272_native_attention.py` | `f6f2c2530947a67ce5d3fdad7e07b990484db16373b5079df186205869bc35a4` |
| `pr272_native_projection.py` | `fcf1c313b46a9b74dd5e149e85b4aee15607963c53668d2b6758c8ace3ead4a3` |
| `native_tlm_pipeline.py` | `c98fcf554e086f4d57ec9ecb2588ac7efd18f6f7b8f4b5f6fd4dea542e11490d` |

四层联调 `115331–115337` 使用 `combined`，Qwen3 的 `115338` 同时运行原版、`attention` 和 `ffn` 三个配置。完整对账要求新旧 MC/LC 图像、调用、最终残差、完整 logits 和反馈 token 一致。核对 KV 与递推状态提交和跨位置读回，并检查 DDR 返回与请求配平。Phi、Falcon 的 ATT1 可能减少实际 DDR 读事务，因此使用 `compare_short.py --same-program` 核验程序而单列变化的流量。

### 四层联调回执

七个组合方案均正常退出。程序和两位置残差逐字节一致。FFN DDR issue/return 齐全，适用注意力的 DDR 在途、回包槽和写确认均在上限内。下表仅计两个位置的四层短 Prefill。

| 模型 | 上一轮（ms） | 接入 PR #272（ms） | 吞吐变化 | Slurm |
| --- | ---: | ---: | ---: | --- |
| Qwen3 | 15.834470 | 17.041274 | −7.08% | 115331 |
| Llama | 49.678744 | 56.587342 | −12.21% | 115332 |
| Granite | 22.308264 | 24.455300 | −8.78% | 115333 |
| Phi | 78.327126 | 90.510522 | −13.46% | 115334 |
| Gemma | 77.025312 | 88.996426 | −13.45% | 115335 |
| Qwen3.5 | 89.671341 | 99.792965 | −10.14% | 115336 |
| Falcon | 75.656548 | 82.643052 | −8.45% | 115337 |

Qwen3 四层单因素的 `attention` 用时 15.792818 ms（吞吐 +0.26%），`ffn` 为 17.077662 ms（−7.28%）。都在同一批 `115338`，程序和输出一致。结合上下游证据，带登记握手的四 bank 在既有串行 P 与窗口 4 的基线上没有复现 Qwen2.5 三 P 的收益。该归因只使用单因素前缀，不外推为完整 Decode。

### 全层重测

| 模型 | 运行目录 | 短 Prefill | 两步 Decode |
| --- | --- | --- | --- |
| Qwen3 | `pr272-tlm-01/run-115340` | 运行中 | 运行中 |
| Llama | `pr272-tlm-01/run-115341` | 运行中 | 运行中 |
| Granite | `pr272-tlm-01/run-115342` | 运行中 | 运行中 |
| Phi | `pr272-tlm-01/run-115343` | 运行中 | 运行中 |
| Gemma | `pr272-tlm-01/run-115344` | 运行中 | 运行中 |
| Qwen3.5 | `pr272-tlm-01/run-115345` | 运行中 | 运行中 |
| Falcon | `pr272-tlm-01/run-115346` | 运行中 | 运行中 |

```bash
R=/public/home/yuzelu/Melodydt/runs/issue-274
cd "$R/pr272-tlm-01"
sha256sum -c source.sha256
sha256sum -c upstream.sha256
sha256sum -c pr272-source.sha256
for k in qwen3:tile128 llama:kv64 granite:kv64 phi:cache gemma:cache qwen35:cache falcon:cache; do
  m="${k%:*}"
  map="${k#*:}"
  sbatch --parsable --job-name="mdt-274rfull-$m" -p c96 -N1 -n2 -c12 -t 06:00:00 -o slurm-%j.log \
    --export=ALL,MDT_274_NATIVE_MATH=1 fast_qwen3_short.sbatch "$m" \
    "prefill:4:$map:combined" "decode:4:$map:combined"
done
sacct -X -j 115340,115341,115342,115343,115344,115345,115346 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
tail -n 5 run-115340/*.log
python3 "$R/audits/compare-pr272-v2.py" "$R/opt-qwen3-vreuse-01/run-115288/decode-w4-tile128" \
  run-115340/decode-w4-tile128-pr272-combined --same-program
sha256sum -c run-115340/output.sha256
```

本轮独立对账脚本 `audits/compare-pr272-v2.py` SHA-256 为 `5f2b3f02c74169bfeb5c804a0405ddb49f4db1b812dcaf076e07c872ab38672d`。
