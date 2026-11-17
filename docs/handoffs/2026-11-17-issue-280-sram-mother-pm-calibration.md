# Qwen3 SRAM 与母控 PM 的 300 MHz 分项标定

2026-11-17（Asia/Shanghai），Melodydt。工作起点 `a9c91b544924921c34064adc321480511c8efdd1`，分支 `task/280-seven-model-energy`。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [源物理工件恢复](2026-11-17-issue-280-macro-views-recovered.md)

## 物理预检与波形绑定

**38814143** 用 25 秒完成三套 ODB、SDC、SPEF 与 Nangate45／#155 TT SRAM Liberty 的导入。实际时钟周期 3.3333 ns，三套 ODB 均有四个 `s_sram_256x128_freepdk45` 宏。OpenROAD 报告的 setup／hold 最差裕量分别为 S_P **+0.32／+0.01 ns**、S_base **+0.16／+0.03 ns**、母控 **+0.37／+0.01 ns**（日志分辨率 0.01 ns）。

从旧机共同归档 #234 `s-activity-002/` 取回 `cells.v` 和 `bank-functional.v` 及两套 S_P 普通读历史对照。功能模型 SHA-256 为 `62f202ce18b251e751f4c9bfda125e7eef1ce45d96d74d5e3d5c81a06bf4bdfe`、`1871109017b197e12c03beb0a1f2a1bd9f0387898858a831535cf300744fe10e`。在 `incoming/macro-views/sim-models/` 的传输包 SHA-256 为 `69a56f96d441448428ded27480a148da64266a2d0502a6e0c5dbd3f8f508c269`。历史归档作为对照，以下数值来自本轮新回放。

## SRAM 模块配对功耗

**38814341／38814342** 分别对原布线 S_P、S_base 作零延迟 Verilator 5.042 门级回放。每种工况以相同的 64-word 预载和静默起点进入 **512 周期** 的配对窗口，波形按原 SDC 折算至 300 MHz。普通读写断言实际 bank mask、地址与读回，256／512-bit 写按两个／四个连续 128-bit 写计为一组。S_P 的 16 次 feeder 命令产生 **32 次** 四 bank 同址读，同时逐字检查 A/B 输出。S_P 实标 **47,623** 个引脚，S_base **17,309** 个。OpenSTA 的 `Macro` 行作为模块总值的组成保留。

| 布线模块 | 开钟静默总功耗（mW） | 128-bit 读（pJ/次） | 128-bit 写（pJ/次） | 串行 256-bit 写（pJ/组） | 串行 512-bit 写（pJ/组） | 四 bank 同址 512-bit feeder 读（pJ/次） |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S_P | 56.6801 | 27.723 | 12.798 | 32.945 | 69.294 | 16.000 |
| S_base | 47.2607 | 25.022 | 11.894 | 28.560 | 60.248 | — |

操作列为带载减等长静默的模块总能量增量，依赖确定性夹具载荷、地址和实际信号路径。512-bit feeder 按物理四 bank 读次数取分母。四个 TLM 站点对应的实际布局、全模型数据负载和开钟驻留待绑定。[S_P 数据](../../work/Melodydt/280/qwen3_s_p_macro_calibration.json) · [S_base 数据](../../work/Melodydt/280/qwen3_s_base_macro_calibration.json)

## 母控 PM 四个 SRAM 宏

**38814278** 初测已成功。**38814399** 用等长配对窗复核，保留最后一次请求后的完整周期。输入为 **38795749** 已通过功能读回的原始 240／272／1,616 字节页波形。读取四个实际 `program_store.sram.storage.banks[i].memory` 的 `clk0/csb0/web0`，按同一时钟边沿的联合值对 #155 Liberty 内部能量表逐沿积分。静默对照保持窗口长度、时钟和窗口起点端口值，且 CS 保持无效。每页的读写成功数量、选通 bank 和 128-bit 端口数据经检查。OpenSTA 同时读取匹配 ODB／SPEF，按宏逐实例报告边界活动传播的功耗。

| 实际页 | 128-bit 写入／读回次数 | 逐沿内部写能耗增量（nJ/页） | 逐沿内部读能耗增量（nJ/页） | OpenSTA 宏写／读增量（nJ/页） |
| --- | ---: | ---: | ---: | ---: |
| 240 B | 15／15 | 0.210961 | 0.071956 | 0.171350／0.069559 |
| 272 B | 17／17 | 0.239835 | 0.081550 | 0.195204／0.079153 |
| 1,616 B | 101／101 | 1.452536 | 0.484504 | 1.197045／0.482112 |

四个宏的漏电合计 **26.8718 mW**，OpenSTA 对应的开钟静默合计 **45.6450–45.9806 mW**。逐沿项只计 Liberty 定义的宏时钟内部能量，OpenSTA 对照按各 pin 活动率与占空比估计条件概率，两种结果分别留档。该报告的单宏输出开关功耗项为零，宏外网络／控制、装载桥及实际母控运行时取指仍需按独立范围补齐。[母控四宏数据](../../work/Melodydt/280/qwen3_mother_pm_macro_calibration.json)

## 作业和复现

BSCC-T6 `ssh.cn-zhongwei-1.paracloud.com`，任务根 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01`，工具目录 `~/LLMHardware/opt`。均在 `v6_384`、`UNLIMITED`，Slurm 均为 `COMPLETED 0:0`。

| 作业 | 核数、节点、耗时 | 提交目录 | 结果目录 |
| --- | --- | --- | --- |
| 38814143 预检 | 4，`m3ca0104`，25 s | `macro-preflight/` | `preflight-38814143/` |
| 38814278 母控首测 | 9，`m3ca0201`，25 s | `mother-pm-macro/` | `result-38814278/` |
| 38814341 S_P | 12，`m3ca0201`，1:03 | `sram-macro-power/` | `sram-38814341/s-p/` |
| 38814342 S_base | 12，`m3ca0301`，28 s | `sram-macro-power/` | `sram-38814342/s-base/` |
| 38814399 母控复核 | 9，`m3ca0201`，22 s | `mother-pm-macro-retry/` | `result-38814399/` |

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
(cd macro-preflight && sbatch --parsable --time=0 run_bscc_t6_qwen3_macro_preflight.sbatch)
(cd sram-macro-power && sbatch --parsable --time=0 --job-name=mdt-280sramp run_bscc_t6_qwen3_sram_macro.sbatch p)
(cd sram-macro-power && sbatch --parsable --time=0 --job-name=mdt-280sramb run_bscc_t6_qwen3_sram_macro.sbatch base)
(cd mother-pm-macro && sbatch --parsable --time=0 run_bscc_t6_qwen3_mother_pm_macro.sbatch)
(cd mother-pm-macro-retry && sbatch --parsable --time=0 run_bscc_t6_qwen3_mother_pm_macro.sbatch)
squeue -j 38814143,38814341,38814342,38814399 -o '%i|%j|%T|%M|%N|%C|%l|%R'
sacct -X -j 38814143,38814278,38814341,38814342,38814399 -o JobID,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 15 macro-preflight/slurm-38814143.log sram-macro-power/slurm-{38814341,38814342}.log mother-pm-macro-retry/slurm-38814399.log
(cd sram-macro-power/sram-38814341/s-p && sha256sum -c results.sha256 && cat calibration.json)
(cd sram-macro-power/sram-38814342/s-base && sha256sum -c results.sha256 && cat calibration.json)
(cd mother-pm-macro-retry/result-38814399 && sha256sum -c results.sha256 && cat mother-pm-macro-power.json)
```

预检顶层结果清单包含容器内的 Liberty 绝对路径，`sha256sum -c` 在相同容器内执行。S_P、S_base、母控复核的逐分项清单 SHA-256 依次为 `2822c1d22a5293c7ea07aeea5031eab2b4a766fd2a1861d506f7281292459ad3`、`6665295a5dc20078ea7bfacd956d2263864369bd4da644a4758a2edb25dd1c5b`、`634cc88796b157ae1059333584b0e4860ef9c6aaec1f1e9f33fc9ab0948fad3f`。项目管理检查、Python AST、Slurm 脚本语法、配对窗口、事务数、波形与结果清单已核验。

OpenROAD 二进制 SHA-256 为 `0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53`。运行的 SRAM 和母控脚本 SHA-256 分别为 `c88e6a72a7d54eb1bc4c0a65ea32ba2651921fb1b3acca172a93ac1b1ab3be3d` 和 `80f4cb0bac06d74824c80264d4b6ab5a6a590ce656b91d6708574bfc81ef3e2b`，已与提交副本对照。

## 接续

Melodydt 继续把 S_P／S_base 分别绑定到实际 Qwen3 站点和多拍宽事件，核对母控页类别、运行读和驻留寿命，避免与独立 PM 桥、局控阵列及全局时钟重计。11:16:59 查验时原版读 DMA 38769386／38769388 已运行 18:34:09，跳过 SHARE 的对照 38795299／38795300 已运行 11:46:20，依赖功耗 38795516–38795519 等待物理输出。读侧合格工件到齐后再汇总含 DMA 三窗。旧版 M 的参考估算仍有独立时序验收边界。任务进行中，PR #281 草稿，登记 PR #5 待合并，Projects 条目待有权限维护者核验。
