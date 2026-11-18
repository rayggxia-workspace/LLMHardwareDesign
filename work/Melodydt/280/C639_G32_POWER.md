# C639 G32 门级功能、静息及计算窗口功耗

2026-11-15（Asia/Shanghai），`llm-hardware-design`，任务分支 `task/280-seven-model-energy`，负责人 Melodydt。此前的 C380 配对空闲、P SRAM 四 bank 和 G32 物理来源记录在 [配对与物理回执](PAIRED_SRAM_AND_C639.md)。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

## 门级功能和按原计划采集的四个窗口

`116937` 在 c64/node9 用 12 核运行 26 分 53 秒，`COMPLETED 0:0`。两种工况的完整 DDR 读写事务、激活事务和已提交 KV 字节与 `116856` 门级替换前的回放相同，PASS 日志、历史位置与四个采样边界对账通过。每种工况 44 个 Q tile、1,408 个输出词、195,485 次 DDR 读。正常 2,654,967 周期，背压 2,845,147 周期。

`116943` 在 c64/node12 用 4 核运行 31 秒，`COMPLETED 0:0`。全部窗口使用匹配的 #250 G32 ODB、SPEF、标准单元 Liberty 及按回放调整到 100 MHz 的 SDC。四个 81.92 µs 窗口各有 77,423 个已标注引脚、135 个未标注引脚，覆盖率 99.826%。四组 G32 输入、输出握手均为零，数值用于该叶的静息参考。

| 工况 | 相位 | 输入／输出握手 | 平均总功耗（mW） |
| --- | --- | ---: | ---: |
| 正常 | Gate/Up | 0／0 | 1.323520 |
| 正常 | Down | 0／0 | 1.333336 |
| 背压 | Gate/Up | 0／0 | 1.370850 |
| 背压 | Down | 0／0 | 1.333336 |

| 证据 | SHA-256 |
| --- | --- |
| `c639-g32-gate-01/c639-g32-116937/gate-results.sha256` | `3cce8aa16cbc75b8e5407a1c8e510f1a55ebc13819505ba647ef2a9b62d7a8d0` |
| `c639-g32-power-03/power-116943/power-results.sha256` | `d88f0c3d43b84e34a8b32a80b11fe9ada99a38f5048e83d541c92ce528e3c746` |

## 从首个有效事务补采

`116950`（`mdt-280ag639`）从 `c639-g32-active-01` 执行 `sbatch --parsable run_c639_g32_active.sbatch`。启动源 `f94f309cf3b6f697091279a860f50eb58428e630`，脚本 SHA-256 `a15d1c9e4d2fd8d1a5dad5d602306e6568b3d576d0e02e3533e3d10fac65785a`。冻结自 `116937` 的门级模型归档、DDR bridge 和 Verilator 库，仅重链接观测驱动。两种工况在同一 2 核分配内各用单核并行。驱动识别第一个 Gate/Up 下游 G32 实际输入握手，从这一时刻采集 81.92 µs。短回放结束后，检查 DDR 读写和激活事务的产生前缀，独立解析波形握手，再用同一物理数据分析功耗。

`116950` 在 c64/node12 运行 4 分 59 秒，`COMPLETED 0:0`。驱动各计 64 次输入，首个上升沿后的 FST 各有 63 次输入、64 次输出。六份已产生的 DDR 读、写与激活事务前缀逐字节匹配冻结回放。两个 OpenROAD 窗口均标注 77,423 个引脚、135 个未标注，覆盖率 99.826%。能量包括内部、开关和泄漏。

| 工况 | 采样起止（ps） | 输入／输出 | 内部（mW） | 开关（mW） | 泄漏（mW） | 总功耗（mW） | 总能量（nJ） |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 正常 | 8,655,315,000 至 8,737,235,000 | 64／64 | 0.525169 | 0.175083 | 0.680535 | 1.380787 | 113.114061 |
| 背压 | 9,387,395,000 至 9,469,315,000 | 64／64 | 0.520801 | 0.175633 | 0.680572 | 1.377006 | 112.804318 |

| 证据 | SHA-256 |
| --- | --- |
| `active-116950/active-results.sha256` | `6ea49d1f72755b87f36a1a8b2adf54d33a22d5bdb2d2255d04212e9a9006b266` |
| `active-116950/reused-model.sha256` | `86f54d4b4c3fdaa747ebbb5f2f2c296a9daded1fb03078a992e82d62bc24d97a` |
| 正常 `ffn-g32-active.fst` | `95c7766d3c4e62d455fbe4e159cd18761a4f8e5650f63c47d9a58bfd202f5cc7` |
| 背压 `ffn-g32-active.fst` | `9253f617e65eeee8cd2cb32f269927a5af30d0fe7aab4f1e2f57234695c1f254` |
| `power-116950/summary.json` | `da497c44f7764e4a693ae0f2acff4244b5248714fc0bdb53b649fa9d0806010b` |
| `power-116950/power-results.sha256` | `45a12901861a6b0e075e17754b081c9e2338e98971da10819e153a2a04a9e2a1` |

登录 `yuzelu@10.129.166.172` 后可核对 Slurm 和摘要。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280/c639-g32-active-01
squeue -j 116950 -o '%i|%j|%P|%T|%C|%N|%R'
sacct -j 116950 -o JobID,State,ExitCode,Elapsed,NodeList
tail -n 40 slurm-116950.log
sha256sum -c active-116950/active-results.sha256
cat power-116950/summary.json
```

此处功耗作用域为 C639 公用的 `G32` 叶块。零延迟门级活动未包含延时毛刺。若需计算配对增量，应从相同 G32 初始状态补空闲对照。下一步为 C639 的 M、局控、互连和剩余计算块补同源布线。随后验证实际 512-bit SRAM／PM 写入及 bank、母控、局控、DMA、互连和时钟，完成 Granite／Phi／Falcon 专项 A/B、七模型和 Qwen2.5-3B 同口径扩测，再汇总系统能耗与误差。Issue #280 仍进行中，PR #281 草稿，登记待合并，Projects 缺配置待维护者核验。
