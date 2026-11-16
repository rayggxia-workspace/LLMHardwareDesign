# Issue #280 三项 300 MHz 片上功耗标定

2026-11-16（Asia/Shanghai），负责人 Melodydt，项目 `llm-hardware-design`，仓库 `rayggxia-workspace/LLMHardwareDesign`，分支 `task/280-seven-model-energy`，脚本发布到 `475d605dcc078104e402b91aa76a47cefac9ef85`。本地目录 `D:/Study_material/Study_material/LLMHardwareDesign` 为管理副本。实际运行与大工件在 Melodydt 的服务器目录。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

## 作业与状态

登录 `yuzelu@10.129.166.172`，根目录 `/public/home/yuzelu/Melodydt/runs/issue-280`。以下均从相应提交目录执行 `sbatch --parsable <脚本>`，日志 `slurm-<作业号>.log`，结果 `result-<作业号>/`。

| 作业／名称 | 分区、节点、核数 | 状态 | 提交目录、脚本 | 实际提交 commit |
| --- | --- | --- | --- | --- |
| 117728 `mdt-280chip300` | c96、node15、12 | COMPLETED 0:0，9 秒 | `c380-g32-power-300-02`，`run_c380_g32_power_300.sbatch` | `6c031ed93ef9a97bf442d4a9e2c1f9ae23a46c18` |
| 117729 `mdt-280mgate` | c96、node15、12 | RUNNING，C++ 编译 | `c639-m-gate-300-02`，`run_c639_m_gate_300.sbatch` | `6c031ed93ef9a97bf442d4a9e2c1f9ae23a46c18` |
| 117743 `mdt-280s512pwr` | c64、node9、8 | COMPLETED 0:0，44 秒 | `wide-sram-power-300-03`，`run_wide_sram_power_300.sbatch` | `36d30a0d7db936b65b5f5eea5951ed4c30a000c9` |
| 117749 `mdt-280chip300` | c96、node15、12 | COMPLETED 0:0，10 秒 | `c380-g32-power-300-03`，`run_c380_g32_power_300.sbatch` | `b13aa675f9ab5339eea397ac40b6aa08d7e15b66` |
| 117751 `mdt-280pm300` | c96、node15、12 | RUNNING，ABC 映射 | `c639-pm-power-300-03`，`run_c639_pm_power_300.sbatch` | `475d605dcc078104e402b91aa76a47cefac9ef85` |

早期 117712／117726／117727 的清洁容器未收到提交目录，修订显式传入目录。117730 的 SRAM 功能已通过，波形实际层级为 `test_compact_s/p`，修订后已通过整个流程。PM 117746 使用默认前端，遇到 SystemVerilog 函数 return；117748 使用容器内置 Slang，识别得 8,192-bit 阵列但触发默认 4,096-bit 容量预算。117751 按实际阵列容量配置预算，已进入 ABC，保留原 RTL 和功能对账。上述失败日志和输入包均在对应 01／02 提交目录保留。

## 完成的子项

- **512-bit 数据 SRAM**。#200 布线 `local_s_p`，TT，原 300 MHz SDC，Verilator 5.042 零延迟活动。三组共用相同 16 行预置和 1,024 拍采样长度（3.413333 µs）。读出全数据断言对账 32 次四 bank 同地址读，写入断言和逐字回读对账 64 次单 bank 128-bit 写。实标 47,623 引脚，178 未直接标注。空闲 56.67650 mW，读窗 56.75875 mW，写窗 56.99968 mW。活跃扣配对空闲后，512-bit 读 **8.773 pJ/次**，128-bit 写 **17.236 pJ/次**。读增量接近空闲基线，需更广数据、占空比、争用和实际工作负载验证。作业结果清单 SHA-256 `fa661687ca6d88e1ae330f9dff9c5b52a1b99d34ed9a47ef206663354cf20816`。
- **C380 ATT1 SRAM**。用原 C380 的两个配对门级窗口和 300 MHz SDC 重算。实标 17,309 引脚，普通 128-bit 端口。正常／背压平均总功耗 52.826／48.461 mW，两个匹配空闲窗约 47.258 mW，对应增量 **38.015／8.217 nJ/窗**。原布线的 `Clock` 组约 0.515 mW，已计入该块总值。
- **C639 G32**。常规四窗 **2.660–2.703 mW**。另测每窗 64 次实际输入握手的两窗，正常／背压为 **2.781／2.770 mW**，相对同工况 Gate/Up 采样高约 4.55%／2.47%。该差值表示两组采样的活动差异。实标 77,423 引脚。`Clock` 组 0.867 mW，已计入 G32 总值。C380 和 G32 10 窗结果清单 SHA-256 `5721433759bf30562480f23d72d2a5f439e7587a65453aa56caf843783de77d2`。

## 待验收和下一步

1. 117729：读回构建与两种完整事务回放，核对原 C639 的提交、DDR、输出和窗口。验收三路 M 的 12 窗直接内部活动覆盖，并补匹配的空闲窗，与 117660 的端口传播估算做同窗对照。
2. 117751：核对后端产物、300 MHz STA 的适用范围、6 次实际 DDR 回包与 22 次 128-bit 写确认、同状态空闲，以及读写结果 SHA-256。原 DDR→PM 档案的局控存储与冻结 C639 源码逐字节相同（`900aa36b508ad28f53451d01f9a4c222ea1008d5f20ea788e1680939a4c8c045`）。本项覆盖局控程序存储，完整 PM 装载控制链路仍需分项。
3. 给其余计算、母控／局控、DMA、互连和系统时钟绑定 300 MHz 实际活动与布线工件，补独立背压／并发校准。已核到 #223 独立 `mother_control_64` 工件和 #250 packet 互连 ODB/SPEF 候选。前者证明范围含行为式局控 PM，后者是跨端点物理预算。完成冻结 C639 源与实例的同源或等价检查后才并入系统功耗。
4. M ECO 117651 收敛后复测并比较。随后闭环 Qwen3，做 Granite／Phi／Falcon 专项对照、其余六模型和 Qwen2.5-3B 参照，最终汇总 mJ/token、覆盖和误差。

```bash
ssh yuzelu@10.129.166.172
cd /public/home/yuzelu/Melodydt/runs/issue-280
squeue -j 117651,117729,117751 -o '%i|%j|%P|%T|%C|%N|%R'
sacct -j 117651,117729,117743,117749,117751 -o JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 25 c639-m-gate-300-02/slurm-117729.log
tail -n 20 c639-m-gate-300-02/result-117729/replay-117729/build.log
tail -n 25 c639-pm-power-300-03/slurm-117751.log
tail -n 20 c639-pm-power-300-03/result-117751/flow.log
(cd wide-sram-power-300-03/result-117743 && sha256sum -c results.sha256 && cat summary.json)
(cd c380-g32-power-300-03/result-117749 && sha256sum -c results.sha256 && cat summary.json)
```

`python scripts/check_project.py` 通过，服务器 Bash 语法、真实 Slurm、配对功能和已完成结果 SHA-256 已核对。负责人 Melodydt。#280 进行中，PR 草稿，登记 PR #5 待合并，Projects 缺配置待有权限维护者核验。当前未配置自动跟踪。
