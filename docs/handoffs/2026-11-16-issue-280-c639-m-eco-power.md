# C639 M 300 MHz ECO 与布线版功耗标定

2026-11-16（Asia/Shanghai），仓库 `rayggxia-workspace/LLMHardwareDesign`，项目 `llm-hardware-design`，负责人 Melodydt，分支 `task/280-seven-model-energy`。源 commit `e1b28d1872c20be96cd3b113826b3e42699e410b`。本地管理目录 `D:/Study_material/Study_material/LLMHardwareDesign` 为文件副本，在线交付在任务分支，原始结果保存在服务器。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

## 作业与验收

登录 `yuzelu@10.129.166.172`，目录根 `/public/home/yuzelu/Melodydt/runs/issue-280`。两项独立提交，每项 12 核。ECO 在 c64 运行，功耗作业已完成。

| 作业 | 名称、节点 | 提交目录 | 原始日志 | 结果目录 |
| --- | --- | --- | --- | --- |
| 117651 | `mdt-280meco`，node1 | `c639-m-eco-01` | `slurm-117651.log` | `eco-117651/` |
| 117652 | `mdt-280mpwr`，node2 | `c639-m-port-power-01` | `slurm-117652.log` | `power-117652/` |

两项分别在其提交目录执行 `sbatch --parsable run_c639_m_timing_eco.sbatch` 与 `sbatch --parsable run_c639_m_port_power.sbatch`。实际构建源与脚本均以固定 SHA-256 核验。下表散列是各目录 `bundle.sha256` 文件的 SHA-256。

| 目录 | SHA-256 |
| --- | --- |
| `c639-m-eco-01` | `161d0c5738a18015ca711c911d75a9efd063d1a28727092fd560b856c6482e1c` |
| `c639-m-port-power-01` | `57071444fe13928ac4f28a02fc1b63e3c58cf3b1ca942fdc032b46c73c643323` |

- **ECO** 从 116976 的 CTS 检查点恢复，沿用 300 MHz I/O 与时钟约束，重新全局和详细布线，setup、hold 分开修复。原版最终 setup WNS 为 −1.1218 ns，最差路径从 `native.weights.state[3][1]` 到 `a_ready`。hold WNS 为 −0.0534195 ns。ECO 已读入 CTS 并进入全局布线。成功判据为最终 SPEF 可验、setup 与 hold WNS 均非负、DRC/电气和逻辑等价复查通过。若 `a_ready` 仍为关键路径，定位组合链重新标定物理优化或评估保持握手语义的 RTL 重构。
- **功耗** 用 116976 布线 ODB、SPEF 和 Nangate45 TT Liberty。100 MHz 约束副本匹配冻结 C639 FST 的时间轴。正常/背压各取 Gate/Up 和 Down，三路 P 各有 8,192 周期，共 12 窗。117652 在 c64/node2 以 12 核运行 6 分 48 秒，COMPLETED 0:0。各窗实标 1,330 个边界引脚，1,788,456 个内部引脚由工具传播估算。结果清单 SHA-256 为 `a31174f8a22f3d9dfc90d966f241edc4298ceb8cea7c26ba749f557b4115eb07`，已逐项复核。完整门级活动、配对空闲、延迟毛刺、300 MHz 功耗和整模型 mJ/token 待测。

| 工况／阶段 | P0（mW） | P1（mW） | P2（mW） |
| --- | ---: | ---: | ---: |
| 正常 Gate/Up | 101.955 | 102.044 | 102.023 |
| 正常 Down | 102.765 | 102.759 | 102.759 |
| 背压 Gate/Up | 101.523 | 101.595 | 101.569 |
| 背压 Down | 102.658 | 102.654 | 102.663 |

单路单窗 81.92 µs，功耗含内部、开关和泄漏。换算得到 8.317–8.418 µJ/窗。

```bash
ssh yuzelu@10.129.166.172
cd /public/home/yuzelu/Melodydt/runs/issue-280
squeue -j 117651,117652 -o '%i|%j|%P|%T|%C|%N|%R'
sacct -j 117651,117652 -o JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 25 c639-m-eco-01/slurm-117651.log
tail -n 25 c639-m-eco-01/eco-117651/flow.log
tail -n 25 c639-m-port-power-01/slurm-117652.log
cat c639-m-port-power-01/power-117652/power.json
(cd c639-m-eco-01/eco-117651 && sha256sum -c eco-results.sha256)
(cd c639-m-port-power-01/power-117652 && sha256sum -c power-results.sha256)
```

后续由 Melodydt 读回两项终态和证据清单，对 ECO 做提取时序、DRC、电气、等价和代表事务复验，补同窗门级功耗及配对空闲。测 512-bit 四 bank 在同拍读下的功耗，补 SRAM／PM 实际写路径及母控、局控、DMA、互连和时钟。完成三个专项消融和七模型及 Qwen2.5-3B 复测后汇总系统能耗与误差。项目管理结构检查 `python scripts/check_project.py` 通过。服务器端 Bash 语法和实际容器 Python 3.10 语法检查通过。登记 PR #5 待合并，缺 `config/board.json`，Projects unverified，待维护者核验。#280 保持进行中，PR #281 草稿，独立审查人待指定。

## 300 MHz 补测

用户确认目标为 300 MHz。100 MHz 来自原始 C639 10 ns 波形，保留作对照。作业 117660（`mdt-280m300`）在 c64/node2 以 12 核运行 6 分 53 秒，`COMPLETED 0:0`。提交源码 `0dd44e032be4980fbfeedb712df03928b8fd22a6`，脚本包清单 SHA-256 `cc6a348e9a2ebba14533447dfca30bcdfcff29c0a6b86a03eb58ac51320c184b`。

沿用 116976 的布线 ODB、SPEF 和原 300 MHz SDC，已逐字节核对 SDC。保持冻结 RTL VCD 的事件值及顺序，在 1 ps 精度把相对时间压缩为三分之一。各窗 8,192 拍、27.306667 µs，标注 1,330 个引脚，内部活动传播估算。100/300 MHz 时间轴与值保真测试都在实际容器中通过。下表单位 mW，含内部、开关与泄漏。

| 工况／阶段 | P0 | P1 | P2 |
| --- | ---: | ---: | ---: |
| 正常 Gate/Up | 269.809 | 270.072 | 270.009 |
| 正常 Down | 272.194 | 272.177 | 272.174 |
| 背压 Gate/Up | 268.515 | 268.724 | 268.646 |
| 背压 Down | 271.886 | 271.874 | 271.902 |

单路窗口能量 7.332–7.433 µJ。结果为 ECO 前网表的 300 MHz 活动功耗估算，实际 300 MHz 功能、延迟驱动活动和 ECO 后功耗待验。功耗结果清单 SHA-256 `c196deecd021c65f653f80de4866410047aed45765f1b37b09db50e71423f6f5`，已逐项核对，`power.json` SHA-256 `baccf22942359bbf9b9947265902f228013a93fa72474795e5abf65b0135bda6`。117651 仍在 c64/node1 执行物理修复。后续以 300 MHz 作为 M 标定和 ECO 前后对照口径。

```bash
ssh yuzelu@10.129.166.172
cd /public/home/yuzelu/Melodydt/runs/issue-280/c639-m-port-power-300-01
squeue -j 117651,117660 -o '%i|%j|%P|%T|%C|%N|%R'
sacct -j 117651,117660 -o JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 25 slurm-117660.log
cat power-117660/power.json
(cd power-117660 && sha256sum -c power-results.sha256)
# 同口径复跑
sbatch --parsable run_c639_m_port_power.sbatch 300
```
