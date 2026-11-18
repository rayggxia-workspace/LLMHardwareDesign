# Qwen3 旧版 M 的 300 MHz 功耗参考

2026-11-17（Asia/Shanghai）。负责人 Melodydt，任务分支 `task/280-seven-model-energy`，记录起点 `bcdfc43453fb2f657e8ff83d638adf4c2af131c1`。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

用户选择以旧版 M 继续估算。采用物理作业 **116976** 的布线 ODB、SDC、SPEF 和从同一 ODB 导出的网表。TT 300 MHz 的复查作业 **38771837** 记录 setup **−1.121800 ns**、hold **−0.053419 ns**。继续使用 Nangate45 TT、OpenROAD/OpenSTA 和 Verilator 5.042。服务端记录保留工具、输入和结果散列。

## 功耗证据与折算口径

- **38809661** 用 54 秒完成旧版网表与波形核验。原版 C639 回放 **38772137** 的两种 DDR 工况中，各取 Gate/Up、Down 和写侧活动，分别提取三路 M，共 **18 份**。窗口长度均为 8,192 周期，每份映射到 **1,330** 个顶层端口位。OpenSTA 根据端口活动与布线寄生传播内部节点活动。波形回放补验收为 **38782228**，原输入及工具散列在 `../wide/wide-38772137/inputs.sha256`。
- **38809728** 用 2 分 35 秒完成复位后空载标定。单 M 在时钟运行、无请求时估算 **248.092 mW**，其中 internal **180.443 mW**、switching **49.651 mW**、leakage **17.998 mW**。这个夹具提供空载参照。实际模型等待期会保留数据和状态，尚待同条件波形核验。
- **38809662** 用 11 分 38 秒完成 18 份带载功耗估算，结果清单通过。波形折算为 300 MHz 下的 27.306667 µs。每窗记录到 256–1,704 次 M 激活握手。Gate/Up 为 **268.515–270.072 mW**，Down 为 **271.874–272.194 mW**，写侧活动期间为 **263.415–264.284 mW**。
- **38809915** 将带载样本范围应用到三路永久开钟 M 的 Qwen3 TLM 忙时，剩余时间使用空载参照。短 Prefill／首 Decode token／稳态 Decode 的三路累计忙时依次为 **27.531／13.765／13.765 ms**，占三路累计墙钟预算 **10.760%／3.284%／3.281%**。按同窗退休数计算 W 和 mJ/token，同时给出 DDR 器件、G32 活跃增量及旧 M 的小计。C639 FFN 样本向 Qwen3 不同 M 操作转用是本轮假设，样本范围仅反映已观测输入，结果等级为时序未闭合的参考估算。

| 窗口 | 三路 M（W） | 三路 M（mJ/token） | DDR＋G32 活跃增量＋M（W） | DDR＋G32 活跃增量＋M（mJ/token） |
| --- | ---: | ---: | ---: | ---: |
| 短 Prefill（2 个输入 token） | 0.7492–0.7521 | 31.95–32.07 | 3.4445–3.4474 | 146.89–147.01 |
| 首 Decode token | 0.7458–0.7467 | 104.19–104.31 | 3.1279–3.1288 | 436.98–437.10 |
| 稳态 Decode | 0.7458–0.7466 | 104.29–104.41 | 3.1262–3.1270 | 437.14–437.26 |

四项作业均为 `COMPLETED 0:0`。三窗 [结果 JSON](../../work/Melodydt/280/qwen3_m_baseline_reference.json) 与服务器输出 SHA-256 一致，均为 `f4b8c716aaff7ef5f4d2321fe34725e0a7b6a8454e6dcf7dd98d24d4f7dc1382`。

## 服务器回执

BSCC-T6 `ssh.cn-zhongwei-1.paracloud.com`，提交目录 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01/m-baseline-power`。工具目录 `~/LLMHardware/opt`。作业均在 `v6_384`，时限 `UNLIMITED`。

| 作业 | 作业名 | 核数与节点 | 结果目录 |
| --- | --- | --- | --- |
| 38809661 | `mdt-280mbasewave` | 8，`m3ca0206` | `m-38809661/` |
| 38809662 | `mdt-280mbasepwr` | 12，`m3ca0305` | `m-38809662/` |
| 38809728 | `mdt-280mbaseidle` | 8，`m3ca0206` | `idle-38809728/` |
| 38809915 | `mdt-280mbasecase` | 1，`m3ca0406` | `scenario-38809915/` |

实际启动命令如下。折算提交时空载已完成且清单通过，因此 Slurm 只等待带载作业，折算脚本再次校验两套输入。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01/m-baseline-power
sbatch --parsable --time=0 --job-name=mdt-280mbasewave run_bscc_t6_m_candidate_power.sbatch baseline-wave
sbatch --parsable --time=0 -c 12 --job-name=mdt-280mbasepwr --dependency=afterok:38809661 --kill-on-invalid-dep=yes run_bscc_t6_m_candidate_power.sbatch baseline-power 38809661
sbatch --parsable --time=0 run_bscc_t6_m_baseline_idle.sbatch 38809661
sbatch --parsable --time=0 --dependency=afterok:38809662 --kill-on-invalid-dep=yes run_bscc_t6_m_baseline_scenario.sbatch 38809662 38809728
```

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01/m-baseline-power
jobs=38809661,38809662,38809728,38809915
squeue -j "$jobs" -o '%i|%j|%T|%M|%N|%C|%l|%R'
sacct -X -j "$jobs" -o JobID,JobName,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 12 slurm-{38809661,38809662,38809728,38809915}.log
find m-38809662 -name receipt.json | wc -l
(cd m-38809661 && sha256sum -c results.sha256)
(cd m-38809662 && sha256sum -c results.sha256)
(cd idle-38809728 && sha256sum -c results.sha256)
sha256sum -c scenario-inputs.sha256
sha256sum -c scenario-38809915/results.sha256
cat scenario-38809915/qwen3-m-reference.json
```

`m-38809661/results.sha256` 的 SHA-256 为 `d0fcadbed8845d4571b12f8010d7004a5beabde0e8edd547975ad2c2ee9abdd6`。`idle-38809728/results.sha256` 为 `3a6b6a46b6f7f8432e420d1bd8df100e557705f03d00cca8cc96fdef51c5b6b7`。空载 RTL 和工具清单见 `idle-inputs.sha256`。折算输入清单 `scenario-inputs.sha256` 为 `ab4dce44080bd33ab282c85b8e2c827ff61d2f3cb688ed68ad2b575b9be13aa70`。

`m-38809662/results.sha256` 的 SHA-256 为 `9bbfb476b84e11e559865f8bda78e01780bc0b83e14834e3c3e7e6e4559ccaf85`，`scenario-38809915/results.sha256` 为 `1bb80f828f7375de05963f35b05d267a18748e8f9b504ee1422147a1d98987d8`。Python AST、服务器 `bash -n`、结果散列、Slurm 终态和 `python scripts/check_project.py` 已核验。

## 剩余步骤

1. Melodydt 继续把已标定的写 DMA、U ADD2、PM 桥和局控阵列按实例、三窗事件和已计入的时钟／空载归属。在 `calibrated-coverage/windows.json` 单列参考项。已有写 DMA 增量可按对齐后的三窗加入分项账本。
2. 读 DMA 原版 **38769386／38769388** 与跳过 SHARE 对照 **38795299／38795300** 等映射完成，再核验物理和活动。08:38 查验时四项都在 ABC 映射，依赖功耗作业 **38795516–38795519** 仍在等待。
3. 补齐 512-bit 数据路径所用 S128 bank 和母控 PM 的匹配 Liberty／LEF、布线与寄生，以及剩余控制、互连和时钟归属。整模型 W 与 mJ/token 待读 DMA 和这些分项归属。新版 M **38792357** 在 CTS 的 hold 缓冲插入阶段以 `2:0` 退出。继续修复时从 `m-physical-exec/physical-38792357/` 的 `3_place.odb` 回溯独立验收。

任务继续进行，PR #281 为草稿。登记 PR #5 待合并。Projects 条目待有权限维护者核验。
