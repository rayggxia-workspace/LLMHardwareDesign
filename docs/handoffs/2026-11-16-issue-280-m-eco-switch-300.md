# Issue #280 M 局部 ECO 与 C639 四端点交换机功耗

2026-11-16（Asia/Shanghai）。仓库 `rayggxia-workspace/LLMHardwareDesign`，项目 `llm-hardware-design`，负责人 Melodydt，分支 `task/280-seven-model-energy`，脚本发布 `446cd2b8028e509dc3cd688cdddde195417f9e4b`。本地管理副本 `D:/Study_material/Study_material/LLMHardwareDesign`。运行和大工件在服务器本人目录。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

登录 `yuzelu@10.129.166.172`，根 `/public/home/yuzelu/Melodydt/runs/issue-280`。在各提交目录执行 `sbatch --parsable <脚本>`。Slurm 日志为 `slurm-<作业号>.log`、结果为 `result-<作业号>/`。

## 时序线

- 117838 在 c64/node1 读原 116976 最终 ODB、SDC、SPEF，复现最差 setup **−1.121800 ns**、hold **−53.419 ps**。留存最大/最小路径报告。四个 hold 端点为源 `a_session[2]` 到 121693，`a_data[209]` 到 123476／124633，`a_data[23]` 到 125313，完整名称见 `baseline-extracted-hold.rpt`。OpenROAD 在提取态 setup 修复进入第一轮时 signal 11，作业 FAILED 11:0。
- 117847 从保存的 5_1 GRT 检查点重新估算寄生，最差 setup 估算 −1.054462 ns，最差 hold +29.507 ps。完成 setup 尺寸优化（调整了 9 个单元），仍有 setup 违例。于增量布线入口发生 signal 11，尚未完成 hold 更新和详细布线。
- 117855（`mdt-280meco5`）在 c64/node1、12 核运行。提交目录 `c639-m-grt-eco-03`，命令 `sbatch --parsable run_c639_m_grt_eco.sbatch`，脚本包清单 SHA-256 `268f4444953827eb080086e5996a2bd1f7f0067bdb525d6a0b4ddfe2eafd5be5`。完成 setup 尺寸优化，GRT 估算 WNS 从 −1.054462 ns 变为 −1.051277 ns，`a_ready` 仍有违例。另用进程在 OpenDB 只修改四个 D 输入，已实际插入 3／1／1／1 级 BUF_X1，进入引脚可达性和全量重布线。OpenDB 插缓冲在现有小型数据库的内存预检通过，原版 ODB 与 SDC 的 SHA-256 已复核。功能源和 300 MHz 时序约束来自同一冻结版。

验收看最终提取的 WNS、TNS、违例数与电气、DRC、逻辑等价及 C639 代表事务。若 setup 仍由 `a_ready` 主导，依据新旧路径对照定位逻辑锥，再评估保留原握手语义的 RTL 组合链重构。

## 功耗线

真实 C639 观察点 `TOP/test_native_decode638_product_replay/controller/cohort/transport` 为四端点，`REBIND_TARGET=4'b0001`、`LOCAL_TARGET=32'b0`。117839 的自动外框无足够引脚位置。117841 在 c64/node1、8 核运行 47 秒，COMPLETED 0:0，采用 **120 × 120 µm** 的独立实验外框，DRC 0，后端逻辑等价通过，300 MHz setup/hold **+746.803/+23.705 ps**。独立外框服务 762 个外部信号位，覆盖范围为交换机单块。

- 117841 的四个正常／背压 Gate/Up、Down 窗口各有 8,192 拍。逐拍检查，四窗均在全部 8,192 拍保持 transport idle，零双向握手。空闲参考 **78.328–78.398 µW**，27.306667 µs 内 **2.13887–2.14079 nJ**。直接标注 762 个边界引脚，3,873 个引脚未直接标注。结果清单 SHA-256 `813de67ef2e393fc7ce186dd0390a7ef9a378b0db7c99ef1e971a598a908c10d`。
- 117854 在 c64/node1 利用冻结 C639 编译库触发实际控制握手，留存正常和背压各 20 个握手周期、8192 拍的 FST。其审计阶段因前缀未到首次激活搬运而未生成的文件退出。117856 按冻结事务的首次实际时间确认无缺失，逐字节核对已发生的 DDR 事务前缀，并复用波形完成功耗。
- 117856（`mdt-280swact2`）在 c64/node9、4 核运行 7 秒，COMPLETED 0:0。正常与背压约 **78.550 µW**、**2.14494 nJ/窗**。分别比同工况空闲参考高约 **0.00607 nJ/窗**。采样从首次收发握手开始，保留波形事件值和相对顺序并在 1 ps 精度转换到 300 MHz。内部活动由工具传播。活跃与空闲增量约 0.28%，且使用不同原生窗口，需用更密集和并发窗口复核。结果清单 SHA-256 `aae03a5033f2415019c83a97014701f856a3421f86b23ed9eecc66f2622937dc`。
- 117729 在 c96/node15 以 12 核编译 ECO 前三路 M 门级回放。后续按正常／背压验证数值、握手、DDR 及门级活动，补匹配空闲。剩余覆盖为母控／局控、DMA、其它计算、完整互连/时钟、SRAM／PM 负载复核。修复后 M 同窗测量、Qwen3 闭环、Granite／Phi／Falcon 对照、其余六模型及 Qwen2.5-3B 参照和系统汇总依次待办。

| 作业 | 提交目录 | 命令中的脚本 |
| --- | --- | --- |
| 117838 | `c639-m-extracted-eco-01` | `run_c639_m_extracted_eco.sbatch` |
| 117841 | `c639-switch-power-300-02` | `run_c639_switch_power_300.sbatch` |
| 117847 | `c639-m-grt-eco-01` | `run_c639_m_grt_eco.sbatch` |
| 117854 | `c639-switch-active-300-01` | `run_c639_switch_active_300.sbatch` |
| 117855 | `c639-m-grt-eco-03` | `run_c639_m_grt_eco.sbatch` |
| 117856 | `c639-switch-active-300-02` | `run_c639_switch_saved_active_300.sbatch` |

```bash
ssh yuzelu@10.129.166.172
cd /public/home/yuzelu/Melodydt/runs/issue-280
squeue -j 117729,117855,117856 -o '%i|%j|%P|%T|%C|%N|%R'
sacct -j 117729,117838,117841,117847,117854,117855,117856 -o JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 30 c639-m-grt-eco-03/slurm-117855.log
tail -n 25 c639-m-grt-eco-03/result-117855/eco.log
tail -n 25 c639-m-grt-eco-03/result-117855/hold-sites.log
tail -n 30 c639-switch-active-300-02/slurm-117856.log
(cd c639-switch-power-300-02/result-117841 && sha256sum -c results.sha256 && cat summary.json)
(cd c639-switch-active-300-02/result-117856 && sha256sum -c results.sha256 && cat summary.json)
```

Bash 语法和 `python scripts/check_project.py` 通过。已完成交换机的等价检查、Slurm 结果和 SHA-256 核验。#280 进行中，PR #281 草稿，登记 PR #5 待合并，Projects 缺配置待维护者核验。
