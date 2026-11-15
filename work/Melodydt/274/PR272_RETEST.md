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

原生四 bank FFN 回归采用 PR #272 `63781d3c7120f05b127d130c86e91e292feb09bc` 的 C639 探针夹具，输入和权重与该 PR 的 113287 相同。115347 在 c96/node14 使用 12 核，Verilator 5.042，于 00:25:28 正常结束。正常工况 2,654,967 拍，背压工况 2,845,147 拍，均与归档一致。每种工况均通过 44 个 Q tile、1,408 个输出字、195,485 笔 DDR 读取和 128 次 FFN WAIT，Gate、Up、Down 各 44,032 个权重记录。完整 FFN 探针、提交的 KV 数据和三类 DDR 事务逐字节匹配归档，98 项散列校验通过。回执 `pr272-ffn-native-01/native-ffn-audit.json` SHA-256 为 `58d0a5955365aeb465abce9c61d49f20bde4b4fb1fc814049ec28b8ccca720f5`。

## 运行与验证

服务器登录 `yuzelu@10.129.166.172`，任务根 `/public/home/yuzelu/Melodydt/runs/issue-274`。七模型工作目录 `pr272-tlm-01`，`source.sha256` 的 SHA-256 为 `0232df0a781d55b3f028dfad3c2813473ba71eece1428fd7913838ca74dca27f`。

全层重测的代码提交为 `209482b226456a7fdc328692470b26ef42ac05e6`。运行环境沿用[上一轮环境及输入来源](RESULTS.md)。五个适配模型以原 512-bit S 端口进行回填。64/128 维每个半窗口为四行，256 维为两行。适配版本最多容许 8 笔 DDR 在途、16 个回包槽和 4 笔未确认 S 写。检查点和权重映像的散列随各次 `assets/plan.json` 及工作目录保留。24 项本地源、23 项上游依赖、3 项冻结模块清单已复验。`upstream.sha256` 的 SHA-256 为 `4ca74101851ca51024b81c2b345e7833f35991a1cd0156ec53d90fb8dbe63ca4`。GCC 8.5.0 的主机算术库在七次重测中均为 `77e4420fac9f0550f24cfa9198f4d3167b99a4dde2a65964906caaacdefebf07`。

三个不改字节的上游模块来自 `/public/home/yuzelu/Melodydt/runs/issue-270/ffn-weight-05/tlm/source`，其中 Attention 和 Projection 为避免遮盖基线模块而另命名。固定内容如下。

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

本轮 7 个 Slurm 作业均为 `COMPLETED 0:0`，一起核验 14 个阶段和 3,601 项输出清单。下表变化相对上一轮各模型的 512-bit 优化配置。

| 模型 | 短 Prefill（输入 tok/s） | 两步 Decode（tok/s） | Slurm |
| --- | ---: | ---: | --- |
| Qwen3-0.6B | 18.0509 → 16.7749（−7.07%） | 4.9487 → 6.3790（+28.90%） | 115340 |
| Llama-3.2-1B | 10.0655 → 8.8384（−12.19%） | 4.1795 → 4.4446（+6.34%） | 115341 |
| Granite MoE | 11.2226 → 10.2297（−8.85%） | 4.6934 → 5.5666（+18.60%） | 115342 |
| Phi-4-mini | 3.1924 → 2.7623（−13.47%） | 1.3301 → 1.5290（+14.95%） | 115343 |
| Gemma-3-4B | 3.0567 → 2.6464（−13.42%） | 1.5495 → 1.5747（+1.63%） | 115344 |
| Qwen3.5-4B | 2.7868 → 2.5055（−10.09%） | 1.6837 → 1.6516（−1.91%） | 115345 |
| Falcon-H1-3B | 3.3071 → 3.0282（−8.43%） | 2.1648 → 2.3332（+7.78%） | 115346 |

115340 已核验 Qwen3 全 28 层 Prefill。用时从 110.797878478 ms 增至 119.225630358 ms。程序、两个位置的最终残差、状态写入和 DDR 流量一致。投影服务增加 8.812 ms，注意力服务减少 0.390 ms。审计 `audits/pr272-qwen3-full-prefill-115340.json` SHA-256 为 `7286d0e61fc872693eeefa8269bb308a251a22b927aba8fc32f10fed14c5b9ae`。

Qwen3 115340 在 c96/node15 以 2×12 核于 00:13:23 正常结束。Decode 退休间隔由 202.071542894 ms 降至 156.764806692 ms，字节结果、动态反馈和 DDR 流量一致。第二步注意力服务由 105.304 ms 缩到 55.600 ms，投影增加约 4.402 ms。审计 SHA-256 `d36eeedce03566b8d259acdc33382315788d4d1901ea4b3d044709f2f265c2fa`。本作业 499 项输出清单通过重验，清单 SHA-256 `9c04c3dc673f144fc9b6df38a96f26549a543c889d7be59c0e1ee401d170e5af`。

Granite 115342 的全层 Prefill 用时从 178.211365146 ms 增至 195.509560760 ms，动态专家路径、程序和字节结果一致。MoE 局控（含专家投影）增加约 17.782 ms，注意力服务减少约 0.498 ms。审计 SHA-256 为 `d44724672a621109012855379eb8bf7ae59e4f1c7eb1ab88d4f9710e4af699ca`。

Granite 115342 在 c96/node13 以 2×12 核于 00:16:59 正常结束。Decode 退休间隔由 213.063167446 ms 降至 179.641964542 ms。两步残差、专家路径、完整 logits 和 DDR 流量一致。第二步注意力减少 42.316 ms，含专家投影的 MoE 局控增加 8.910 ms。审计 SHA-256 为 `172d32a3fda7259a4b0e35697b8785daaab05aeb61806aa7c6d52f4f9934ed92`。

Llama 115341 的全层 Prefill 用时从 198.699201894 ms 增至 226.284864590 ms，程序、64 维 KV 事务和残差一致，DDR 总量一致。投影服务增加约 27.880 ms，注意力服务减少约 0.338 ms。审计 SHA-256 为 `44d8ecc49aab43914fb25d8dbe8964617318cb69aa50a639c66586e4f3853ce6`。

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

Llama 115341 在 c96/node13 以 2×12 核于 00:19:04 正常结束。Decode 退休间隔由 239.265003432 ms 降至 224.990379078 ms，程序、结果和 DDR 流量一致。第二步注意力减少 28.273 ms，投影增加 13.975 ms。审计 SHA-256 为 `6c7fdc3cee8c17100f2b4ae617778eaf08cd952e383d0d00b1c178384160d21a`。243 项输出清单通过重验，清单 SHA-256 为 `8a89ba4ec87d5b9d59bb620d78a6342b6275b2288f4dae60e017957c13d2819b`。Granite 115342 的 563 项输出清单也通过重验，清单 SHA-256 为 `39e061d73ecd1473f4723779daf5b2f635e3d9f52921900bb2a46df43d1c4347`。

Falcon 115346 在 c96/node15 以 2×12 核于 00:41:48 正常结束。短 Prefill 从 604.756847184 ms 增至 660.452427406 ms，两步 Decode 退休间隔从 461.939586110 ms 降至 428.603013462 ms。短 Prefill 与两步 Decode 分别少读 15,360 和 5,258,240 笔 DDR，匹配 32 层 × 10 个查询头 × 每行少 16 笔 V 读取。第二步注意力减少 61.356 ms，投影增加 27.994 ms。两位置残差、完整 logits、动态反馈与递推状态事务一致。Prefill 审计 SHA-256 为 `1f7ab2eae74e48748a3f4dfc7fd59a12a1a7f3205da397e95298f241d923e968`，Decode 为 `7787d9d969ec83a5921fa5dfe6e7e4a0c9ca8cab5dd52642271d3ed6b11cf4cf`。563 项输出清单通过重验，清单 SHA-256 为 `def1dce11e1b6477648f9e907bff2bea7f715f6881ca31ee106110aa23024b02`。

Qwen3.5-4B 115345 在 c96/node15 以 2×12 核于 00:52:49 正常结束。短 Prefill 用时 717.680→798.232 ms，注意力减少 0.227 ms，投影增加 80.761 ms。Decode 退休间隔为 593.921→605.470 ms，第二步注意力减少 28.801 ms，投影增加 40.336 ms。DDR 总读写量一致。程序、两位置残差、词表 logits 和反馈 token 逐字节一致。Prefill 审计 SHA-256 为 `33b364ce067e31dc15a8cf4a127d51548408425392e0bfaeb5e9ce096eab833b`，Decode 为 `6c6542beeab47bc8ff7cad3adb3e01b061373e8c5488c1e63ce6351af187a1ad`。563 项输出清单通过重验，清单 SHA-256 为 `00ad8cba66322e6a880f9757ee7217c1a90b18c24a87b0796a57d7cde99a2725`。

Gemma-3-4B 115344 在 c96/node13 以 2×12 核于 00:55:46 正常结束。短 Prefill 用时 654.296→755.744 ms，注意力减少 0.488 ms，投影增加 101.906 ms。Decode 退休间隔为 645.376→635.047 ms，第二步注意力减少 61.248 ms，投影增加 50.934 ms。DDR 总读写量一致。程序、两位置残差、词表 logits 和反馈 token 逐字节一致。Prefill 审计 SHA-256 为 `96998293c803d686261cf97cf21dbd416bc875943653ce68bf8a1622336b8abb`，Decode 为 `69af0350f53e89f0f1f68e95de710edebddbbc5a8f5d5f7368b0892cd50de1ee`。735 项输出清单通过重验，清单 SHA-256 为 `42b5f4181803ff3060472e0be3fa13b4b2e0c194b39672bab17bd715c1092e61`。

Phi-4-mini 115343 在 c96/node13 以 2×12 核于 01:00:35 正常结束。短 Prefill 用时 626.496→724.024 ms，注意力减少 0.535 ms，投影增加 98.062 ms。Decode 退休间隔为 751.842→654.038 ms，第二步注意力减少 147.177 ms，投影增加 49.387 ms。短 Prefill 和两步 Decode 分别少读 36,864 和 12,619,776 笔 DDR。程序、两位置残差、词表 logits 和反馈 token 逐字节一致。Prefill 审计 SHA-256 为 `c9f7c10934cff6efb6e9e0a80d05861685cc004d84cb4d53693abe8ea95ad373`，Decode 为 `b861c8174bebc37131dc30be8b557d087f3830e3679d8238a4671efd0b1b68d6`。435 项输出清单通过重验，清单 SHA-256 为 `a4d2af906b769819987b62f1a63d2e738327f0a461e79e62a737ff228e86fee2`。

本轮独立对账脚本 `audits/compare-pr272-v2.py` SHA-256 为 `5f2b3f02c74169bfeb5c804a0405ddb49f4db1b812dcaf076e07c872ab38672d`。
