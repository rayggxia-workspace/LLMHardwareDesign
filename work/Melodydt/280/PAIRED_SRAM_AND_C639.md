# C380 配对空闲、C639 G32 与 512-bit SRAM／PM 端口

2026-11-15（Asia/Shanghai）。项目 `llm-hardware-design`，负责人 Melodydt，任务分支 `task/280-seven-model-energy`。服务器 `yuzelu@10.129.166.172`。实验根为 `/public/home/yuzelu/Melodydt/runs/issue-280`。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [C380 原活动窗](C380_ROUTED_POWER.md)

## C380 配对空闲

`116935` 在 c64/node9 用 8 核，90 秒，`COMPLETED 0:0`。沿用布线 `local_s_base`、TT Liberty、100 MHz 时钟和 C380 的第 4,096 次 KV 回包。活动和空闲分别回放到相同起点，逐字比对四个宏共 1,024 个 128-bit 字，另逐项比对 23,012 个门级信号。空闲暂停新 SRAM 请求，锁存请求数据、地址和方向，允许首个 10 ns 周期退出已有响应。其余窗口验证无新请求，四个 bank 均未选通。活动对照的读回、DDR 事务和周期再次与 `116908` 一致。

每窗 20.48 µs。下表使用完整窗口，包括空闲起点后的首个排空周期。

| 工况 | 活动（mW） | 空闲（mW） | 活动减空闲（mW） | 增量（nJ） |
| --- | ---: | ---: | ---: | ---: |
| 正常 | 35.663966 | 33.811163 | 1.852803 | 37.945404 |
| 背压 | 34.209967 | 33.811033 | 0.398934 | 8.170166 |

每窗标注 17,309 个引脚，覆盖率 99.1806%。`116939` 在 c64/node12 用 2 核，7 秒，`COMPLETED 0:0`。四个窗口的逐引脚清单完全一致，未标注项共 143 个，均为 `bv1_input_diode_<编号>/A`。结果只覆盖普通 128-bit SRAM，零延迟活动未包含延时毛刺。

| 证据 | SHA-256 |
| --- | --- |
| `idle-116935/idle-results.sha256` | `b31aa93ba67d1a95a429f31be4cf34753aba3172753003726fa407b570a3bff7` |
| `power-116935/paired.json` | `982d9dcc72015b6fa61c992e61da82f299a9ed56d7b183dc5f0b156e41e6ac98` |
| 正常活动／空闲 `sram-checkpoint.hex` | `b4fae8c4f8ebda649aec80ecf96bf9984ad030258fcd2e9ba37604448f41f2ca` |
| 背压活动／空闲 `sram-checkpoint.hex` | `58aae633e7b1b1731f79ce588e3b7c3a0fbd92ae833a6a7346882bb30eb6bbe5` |
| `pins-116939/pins-results.sha256` | `e7844f5a54db1576ea03dcfe69770276ef21d06d1242516c76740ce90e99b837` |

首两轮 `116932`、`116933` 退出于测试台寄存器初始化和复位告警。`116934` 的四窗功耗报告完成，最终校验发现 FST 省略宏存储阵列。`116935` 在原采样时刻直接导出宏存储并核对。四个历史作业的日志分别保存在 `gate-c380-idle-01` 至 `gate-c380-idle-04`。

## C639 的物理叶块

在 C639 快照与 #250 交付源之间逐字节核对 `g_s32.sv`、`g_s128_frontend.sv` 及 Nangate 行为库。G32 最终布线工件由 `issue250-p-final-native-diode-gate-GlrL0V/g-final.v` 追溯到 `LLMHardwareDesign/issue-250-g-physical-20261111-08/delivery/6_final.v`。该目录保存同批布线的 ODB、SPEF、SDC 和交付 JSON。C639 G32 的 RTL 作用域为 `TOP/test_native_decode638_product_replay/feed_forward/dut/G`。采样为正常／背压各 81.92 µs 的 Gate/Up 和 Down。

`116937` 读回为 c64/node9 12 核运行。正常工况报告 `PASS q projection`，44 tiles、1,408 输出词、195,485 DDR 读、2,654,967 周期，已保存 11,733,162 B 的 Gate/Up 与 14,658,052 B 的 Down FST。背压及全作业终态对账待完成。`116942` 的首窗预检在 c64/node12 用 4 核、12 秒 `COMPLETED 0:0`，77,423 个引脚已标注、135 个未标注，覆盖率 99.8259%。预检 VCD 已独立统计 G32 端口握手，正常 Gate/Up 窗 G32 的输入和输出握手均为 0，1.323520 mW 只覆盖该窗的静息状态。正式四窗分别记录实际事务。若没有覆盖 G32 运算，补采从首次 G32 输入握手开始的窗口。预检结果清单 SHA-256 为 `764db93374041a6297568b99e0666a690df357cf1ac1ceff73562a7b62e2c97c`。首轮 `116941` 退出于链接地址构造，已为每个物理文件使用显式目标名。

M60 输入文件 `m_native_leaf_s32.sv` 的差异包含事件探针。`m_native_s32.sv` 的差异还包含槽位状态、队列元数据及退休逻辑，影响物理实现。现有 M60 保留为候选，待同源重走物理或完成针对当前快照的等价证明。C639 快照的 `weight_records.sv` 声明 `reg [511:0] data [0:3][0:17]`，对应活动层级为 `weights/registers`。这个 512-bit fill 入口目前归入寄存器活动。C639 相同代码的局部 `local_s_base` 继续按普通 128-bit 存储端口解释。

## P SRAM 及 PM 位宽

`116938` 在 c64/node9 用 8 核，30 秒，`COMPLETED 0:0`。同一断言夹具分别运行原生 RTL 与 #200 布线 `local_s_p`，对账 512-bit 数据、应答、背压和阶段隔离。逐拍监控四个物理 SRAM bank 的 `csb0`、`web0`、`addr0`，都观测到两次 512-bit feeder 读以 `1111` 同地址选通四个 bank、四次 128-bit 单 bank 写、一次 128-bit 单 bank 读。`116936` 的 RTL 同样通过，门级编译退出于 364 个未连接的 `Z`／`ZN` 输出告警。修订仅在目标布线网表中屏蔽该类告警。最终 `wide-results.sha256` 的 SHA-256 为 `413a08454d39372cacc4889618bb82054c9afd8a8f632f55466907f701c423ca`。

源码核实 `control_pm` 的读写数据及 `lc_program_store_1k` 的写入／读取均为 128-bit。`native_product_controller.pm_rsp_data` 为 512-bit 上游回包。#234 原生 `native_pm_image_stream` 把每个 512-bit DDR 回包按 128-bit 片写入 LC PM，归档 `issue234-native-pm-stream-20261112-01/run-103489/replay.log` 报告六次真实 DDR 回包和 22 次有校验的 PM 写确认。P SRAM 的 512-bit 读与现有 PM 拆分写在物理功耗分项中分别处理。匹配七模型配置的 512-bit 写实现及控制链路物理标定待办。

## 作业、结果与接续

| 作业 | 提交目录 | 启动文件 | 结果目录 | 源 commit |
| --- | --- | --- | --- | --- |
| 116935 | `gate-c380-idle-04` | `run_c380_idle.sbatch` | `idle-116935/`、`power-116935/` | `a197be7cd90b680c3ff020941aefa34f0b126054` |
| 116939 | `gate-c380-pin-audit-01` | `run_c380_pin_audit.sbatch` | `pins-116939/` | `768b70ffcb7800fea8dffbf8e8217792764d6233` |
| 116937 | `c639-g32-gate-01` | `run_c639_g32_gate.sbatch` | `c639-g32-116937/replay-116937/` | `318714eae0cf761b3464594edfbca4ba09d0de0a` |
| 116938 | `wide-sram-pm-02` | `run_wide_sram_pm.sbatch` | `wide-116938/` | `cbecccaffeb8bc71881036b3b79a886ed79f8d67` |
| 116942 | `c639-g32-power-02` | `run_c639_g32_power.sbatch` | `power-116942/` | `99c9800eab1c5d136a5ac7d77466a899aae1a234` |
| 116943 | `c639-g32-power-03` | `run_c639_g32_power.sbatch` | `power-116943/` 待分配 | `8e4d889478b632f4b86ce81492e2661d3e68b085` |

实际上传的脚本和提交版本由对应目录的 `bundle.sha256` 与 `source-commit.txt` 固定。除功耗两项外，均在对应目录执行 `sbatch --parsable <启动文件>`。预检追加 `--export=ALL,G32_PREFLIGHT=1`，四窗功耗 `116943` 追加 `--dependency=afterok:116937 --kill-on-invalid-dep=yes`。最后读回 `116943 PENDING (Dependency)`，节点待分配。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280
squeue -j 116937,116943 -o '%i|%j|%P|%T|%C|%N|%R'
sacct -j 116935,116937,116938,116939,116942,116943 -o JobID,State,ExitCode,Elapsed,NodeList
tail -n 30 c639-g32-gate-01/slurm-116937.log
tail -n 30 c639-g32-power-03/slurm-116943.log
sha256sum -c gate-c380-idle-04/idle-116935/idle-results.sha256
sha256sum -c gate-c380-pin-audit-01/pins-116939/pins-results.sha256
sha256sum -c wide-sram-pm-02/wide-116938/wide-results.sha256
(cd c639-g32-gate-01/c639-g32-116937 && sha256sum -c gate-results.sha256)
sha256sum -c c639-g32-power-03/power-116943/power-results.sha256
```

后续由 Melodydt 读取 C639 门级终态，核对完整 DDR 读写、KV、周期和四个 FST，随后用匹配的 G32 布线工件报告活动功耗。继续给 C639 的 M、其余控制和互连补同版本物理证据。为 512-bit 写和 PM 找到可绑定的实现，完成 bank、母控、局控、DMA、互连与时钟分项。之后完成 Granite／Phi／Falcon 专项 A/B、七模型扩测及 Qwen2.5-3B 同口径参照，待覆盖齐备后汇总系统能耗和误差。

#280 进行中，PR #281 草稿，独立审查人待指定。项目登记 PR #5 待合并，Projects 缺配置待维护者核验。
