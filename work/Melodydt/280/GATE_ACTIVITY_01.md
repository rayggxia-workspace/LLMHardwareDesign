# 局部存储门级功耗复现与 ATT1 活动采样

2026-11-15（Asia/Shanghai），负责人 Melodydt。项目 `llm-hardware-design`。此前的 Qwen3 DDR 能耗来自双通道器件模型，片上活动的复现和标定沿本记录继续。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [Qwen3 DDR 回执](QWEN3_DDR_PILOT.md)

## S128 普通端口的配对门级窗口

作业 `116809`（`mdt-280s128`）实际运行于 c64/node2，单核、12 秒、`COMPLETED 0:0`。脚本源码 `167312e1b56ffbcc7483198bf8ccff9f7575a34e`。在相同的已布线 `local_s_p` ODB、SPEF、SDC、门级波形、Nangate45 typical 和 S128 TT 1.1 V、25 °C 的 Liberty 上复核 OpenROAD 活动输入。容器为 `orfs-current-repacked.sif`，OpenROAD 版本字符串为 `unknown`。原始归档所有输入与归一化 VCD 的摘要已逐项核对。 [原标定回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/eaf3008868982e5ac6c2f70878250c148ec6d009/work/YUZE-LU/234/s-activity-result-002.json)

| 窗口 | 时长 | 操作 | 内部（mW） | 开关（mW） | 漏电（mW） | 总功耗（mW） |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| 空闲 | 5.18 µs | 0 读、0 写 | 26.833387 | 2.304628 | 27.516289 | 56.654304 |
| 活动 | 5.18 µs | 516 读、2 写 | 27.495863 | 2.886415 | 27.518442 | 57.900719 |

重跑的四项功耗与原回执一致。两个窗口各标注 47,623 个引脚，178 个未标注，覆盖率 99.6276%。活动比空闲多 **1.246415 mW**，窗口增量 **6.456430 nJ**。这组增量对应整个混合读写窗口，测量范围为 S128 普通端口。

服务器 `yuzelu@10.129.166.172`，提交目录 `/public/home/yuzelu/Melodydt/runs/issue-280/gate-s128-01`，启动命令 `sbatch --parsable replay_s128_power.py`，日志 `slurm-116809.log`。输入清单、活动与空闲的日志及结果清单均已读回校验。

| 文件（相对提交目录） | SHA-256 |
| --- | --- |
| `s128-116809/calibration.json` | `ee18c1ae7233f7c8ad9e05f868e4ad6178fa318ac1c2ed34806d8893b09d34aa` |
| `s128-116809/output.sha256` | `f45c0e9f5c7bdf2e1173ae7fa3c5ba3e9652e98e2aa945156060665cb6644f2b` |

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280/gate-s128-01
sacct -j 116809 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
sha256sum -c inputs.sha256
sha256sum -c s128-116809/output.sha256
cat s128-116809/calibration.json
```

## C380 采样与 512-bit 实物边界

C380 归档使用 10 ns 的原生时钟和 S128 普通端口，`local_s_base` 将宽读口关闭。归档的共享后端有四个 256×128 的 1RW bank，具有 512-bit 宽读入口及独立的窄写入口。整模型的 512-bit TLM 数据与 PM 写宽还需对应的宽写实现、bank 使能和匹配的物理时序。C639 原生 FFN 归档保留功能、计时和事务证据，已检查的回执目录尚无活动波形和对应的 ODB／SPEF。

C380 作业 `116817` 的源为 `50da20b4c1b8e9183ba334990a40e5b183839637`，提交包 SHA-256 `a5329a3bf0c19e4e78b54cdfe91154f22ae57d2dd933e990bc87066dcd981f4c`。服务器提交目录 `/public/home/yuzelu/Melodydt/runs/issue-280/gate-c380-01`，命令 `sbatch --parsable run_c380_activity.sbatch`，日志 `slurm-116817.log`，结果 `c380-116817/`。正常／背压两个用例均从第 4,096 个 KV 回包触发，采集有界 FST，并以完整读回、事务轨迹、周期、生成物及清单和归档 115330 对账。采样窗口用于后续功能活动绑定，C380 物理功耗待匹配网表与寄生参数。

`116817` 在 c64/node2 单核运行 6 分 30 秒，`COMPLETED 0:0`，Verilator 5.042。两用例均逐字核对读回、DDR 事务轨迹和生成物，并核对全运行周期、9,120 个 KV 回包和 54,087 个 SRAM ACK。窗口持续 20.48 µs，覆盖 2,048 个 10 ns 核周期。

| 工况 | 全回放周期 | FST 起止（ps） | 窗口内新增 KV 回包 | 文件大小（字节） |
| --- | ---: | ---: | ---: | ---: |
| 正常 | 65,932 | 414,725,000 至 435,205,000 | 434 | 1,207,291 |
| 背压 | 279,968 | 1,695,035,000 至 1,715,515,000 | 84 | 829,217 |

| 文件（相对 `c380-116817/`） | SHA-256 |
| --- | --- |
| `replay-116817/mode-0/attention.fst` | `77cec6f3b7446e2fe23c283f6b81855cd5bb613a10344fd0837e083a55bc0a0a` |
| `replay-116817/mode-1/attention.fst` | `cf6d8bfe6294ff88629e7467187c26c9b766d5d2889e724cbf1e0d1ecefecdf7` |
| `activity-results.sha256` | `82f6eed1052eaa796db601279a51fb29bedd2109e65880f0bc897d07f61a26a7` |
| `replay-116817/proof.sha256` | `92d10c620e2394b5063549e7665a0305316d2ef109ace9c3b60c54b174c7f3ea` |

三份源码、两份活动及原生功能输出的 SHA-256 清单已在生成目录读回核验。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280/gate-c380-01
sacct -j 116817 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
tail -n 30 slurm-116817.log
cd c380-116817
sha256sum -c activity-source.sha256
sha256sum -c activity-results.sha256
(cd replay-116817 && sha256sum -c proof.sha256)
```

剩余步骤包括 C380 样本的层级映射和相应物理输入绑定、C639 活动采样、实际 512-bit SRAM／PM 宽读写和 bank 使能标定、控制及互连的片上功耗覆盖。单 P／三 P 的 Qwen3 对照作业 116787 仍排队。之后完成 Granite、Phi、Falcon 专项验证、七模型同口径扩测和系统能耗汇总。
