# Qwen3-0.6B 同底座 P0／三 P DDR 能耗对照

2026-11-15（Asia/Shanghai）。负责人 Melodydt。三 P 采用已验收的 116481（FP32 补审 116496），P0 为 116787，回放源提交 `6c057be1166d4a28cebd72c14f501df47f3be6d9`，部署 ZIP SHA-256 `fcd162062fba431dcc748aea61f7dc77238c240c9ca346159b2a78bd0d1e16c9`。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [三 P 绝对结果](QWEN3_DDR_PILOT.md)

两组同 W8A16、真实 512 位置起点、三目标底座、512-bit SRAM TLM、3,334 ps 核周期、双通道 DDR4 及探针库。DDR 中间结果存储地址与字节数、Down route 4 回读地址、FFN 权重记录总量均通过 A/B 对账。P0 只把 FFN 运算发往 P0，随之减少到 P1/P2 的中间片上搬运。

| 窗口 | P0 耗时（ms） | 三 P 耗时（ms） | P0 → 三 P 吞吐（tok/s） | P0 → 三 P DDR（mJ/token） | 三 P DDR 能耗变化 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 短 Prefill，两输入位置 | 122.150178 | 85.289805 | 16.373288 → 23.449462 | 156.262806 → 114.939879 | −26.44% |
| 首 Decode token | 158.122221 | 139.703052 | — | 374.073273 → 332.791363 | −11.04% |
| 两次退休间 Decode | 158.214283 | 139.833835 | 6.320542 → 7.151345 | 374.004159 → 332.854675 | −11.00% |

三 P 的短 Prefill、两退休 Decode 吞吐分别提升 43.22%、13.14%。短 Prefill 平均 DDR 功耗从 2.559 W 到 2.695 W，Decode 从 2.364 W 到 2.380 W。用逐窗积分拆分，短 Prefill 每输入 token 的 DDR 能耗减少 41.323 mJ，其中背景少 35.416 mJ。Decode 每输出 token 的 DDR 能耗减少 41.149 mJ，其中背景少 35.258 mJ。两种窗口约 85.7% 的降幅来自背景能耗缩减。覆盖范围是双通道 DDR 器件模型，片上、PHY、板级能耗待加入。

两组逐层残差和两次完整词表 logits 的散列一致，两个阶段均 28 层×两个位置且零残差限幅。独立 FP32 对照 Decode 两次 top-1 一致，token 为 `72349 → 5785`，logits 相对 L2 为 0.8209%／1.0694%。短 Prefill 的 FP32 末层归一化残差相对 L2 为 2.7991%。P0 短 Prefill 供数记录为 516,096／0／0，审计也核对了 Decode 的对应三路配置、权重完结及状态。

## 作业与复现

服务器 `yuzelu@10.129.166.172`，提交目录 `/public/home/yuzelu/Melodydt/runs/issue-280/p0-ab-01`，命令 `sbatch --parsable run_qwen3_p0.sbatch`，日志 `slurm-116787.log`。任务从 c96 原请求调整为 c64,c96、两阶段各 1 核、时限 1 小时。实际在 c64/node9，以 20 分 22 秒 `COMPLETED 0:0`。Slurm 父作业分配 12 核，Prefill 与 Decode 步骤各绑 1 核，运行时长分别为 7 分 55 秒和 20 分 11 秒。独立对照在 1 核步骤完成，4 秒。回放包 1,068 项输出由作业逐项核验，回读另核验 7 项输入及最终 3 项结果清单。

| 文件（相对提交目录） | SHA-256 |
| --- | --- |
| `ab-116787/ab-results.json` | `aea66b41f49a9535075c6bb5d7b9f98e8df232eb98a367224bd84d743f8bfcf7` |
| `ab-116787/ab-results.sha256` | `7a30357e6dd80cbad16b6e4ffcf6f29f797592d344c02b6d2671b4675cb457d8` |
| `ab-116787/ab-inputs.sha256` | `ab65ae1e199e867e24c40ef22bf2d8991c03560dc25586a98e6855d18323d33f` |
| `ab-116787/run-116787/output.sha256` | `0c323a45b704e69eb9e5eb1ba8c659a86a8a097a7fd8e23754a598142089384d` |

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280/p0-ab-01
sacct -j 116787 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
sha256sum -c ab-116787/ab-inputs.sha256
sha256sum -c ab-116787/ab-results.sha256
cat ab-116787/ab-results.json
```
