# C380 布线 SRAM 门级回放与活动功耗

2026-11-15（Asia/Shanghai）。项目 `llm-hardware-design`，负责人 Melodydt，任务分支 `task/280-seven-model-energy`。使用原生 C380 回放 `115330` 和对应的 RTL 活动窗口 `116817`。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [物理边界绑定](GATE_BINDING_02.md)

## 门级功能回放

在原生 C380 测试台编译 #200 `run08-base0` 的布线 `local_s_base` 网表，使用 #234 的标准单元行为库及零延迟 SRAM 功能视图。预装载 32 个字仍由测试台的原 SRAM 端口逐词写入，使用相同的输入、指令、DDR 配置与两种种子模式。原测试台的其他 RTL 和断言保留。

`116908` 在 c64/node9 使用 8 核，1 分 5 秒，`COMPLETED 0:0`。两种工况的完整读回、`transactions.tsv`、运行周期、S 重叠计数、生成的 8 个功能输入工件和采样边界与各自基准一致。每种工况全程收到 9,120 个 KV 回包与 54,087 个 SRAM ACK，DDR 读 583,808 B、写 512 B。

| 工况 | 全回放周期 | 活动窗口起止（ps） | 窗口新增 KV 回包 |
| --- | ---: | ---: | ---: |
| 正常 | 65,932 | 414,725,000 至 435,205,000 | 434 |
| 背压 | 279,968 | 1,695,035,000 至 1,715,515,000 | 84 |

## OpenROAD 活动窗口估算

`116918` 在 c64/node9 使用 4 核，12 秒，`COMPLETED 0:0`。对两份门级 FST 按原始事件值导出 VCD，核对各 2,048 个周期，复用原 ODB、SPEF 和 TT 1.1 V、25 °C SRAM Liberty。功耗分析的 SDC 副本仅把 `core` 时钟周期设置为测试台的 10 ns。每窗 20.48 µs，波形作用域为 `TOP/test_native_attention_core_scope/storage`。表中能量等于该窗平均总功耗乘以 20.48 µs，含泄漏。

| 工况 | 内部（mW） | 开关（mW） | 泄漏（mW） | 总功耗（mW） | 窗口能量（nJ） |
| --- | ---: | ---: | ---: | ---: | ---: |
| 正常 | 7.427516 | 1.153431 | 27.083019 | 35.663966 | 730.398026 |
| 背压 | 6.760584 | 0.364794 | 27.084587 | 34.209967 | 700.620117 |

每个窗口标注 17,309 个引脚，143 个未标注，覆盖率 99.1806%。导出的 `logic` 统一使用 VCD `wire` 声明，保持 ID、位宽、时刻及值。剩余每份 22 条 VCD 类型警告逐条定位到目标作用域以外。143 个未标注引脚待逐项核实。零延迟活动不含延时引起的毛刺。这些数字覆盖 `local_s_base` 的普通 128-bit 读写端口及其四个 SRAM bank，配对空闲增量与实际 512-bit SRAM／PM 仍待标定。

## 复跑与追溯

服务器 `yuzelu@10.129.166.172`，实验根 `/public/home/yuzelu/Melodydt/runs/issue-280`。远端每个提交目录保存 `source-commit.txt`、`bundle.sha256`、`job-id.txt`。复跑脚本在新 Slurm 作业目录持久化输出。

| 作业 | 实际提交目录 | 提交命令 | 启动源码 commit |
| --- | --- | --- | --- |
| 116908 | `gate-c380-routed-02` | `sbatch --parsable run_c380_gate.sbatch` | `3adad312b749a54646bc417ad3411e0f9f63e549` |
| 116918 | `gate-c380-power-03` | `sbatch --parsable run_c380_gate_power.sbatch` | `f8f56fa930305522132cd93cef0fbfdd864bf215` |

首次门级 `116904` 缺另一路径仍需要的 feeder RTL。首个功耗 `116911` 的 FST 导出顺序导致信号值缺失。`116916` 识别 `logic` 声明失败，覆盖率低于原有 99% 门槛。三个失败回执均保留在各自目录。最终门级工具为 Verilator 5.042。OpenROAD 版本字符串为 `unknown`，以二进制 SHA-256 `0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53` 固定。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280
squeue -j 116908,116918 -o '%i|%j|%P|%T|%C|%N|%R'
sacct -j 116908,116918 -o JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 30 gate-c380-routed-02/slurm-116908.log
tail -n 30 gate-c380-power-03/slurm-116918.log
(cd gate-c380-routed-02/c380-gate-116908 && sha256sum -c gate-results.sha256)
sha256sum -c gate-c380-power-03/power-116918/power-results.sha256
```

| 证据 | SHA-256 |
| --- | --- |
| 门级 `gate-results.sha256` | `3c758c30645311dd243b4defba50e64e3a959e1aa6ac2cee95bab833eaf51a1a` |
| 功耗 `power-results.sha256` | `196203bae9c432945710d02f4b9b7439638148bb6839fbc5f843cc1ca3522659` |
| 100 MHz `6_final.sdc` 副本 | `8de3178d1eb8a7ac1f5391b478c6b7dc70eec916b1de9cd5c96230d474954252` |
| 两种模式 `readback.hex` | `994dc727df03121bf5cb902b630890ef3d6da48df3e762ca9987bd63dd85e3ee` |
| 正常 `attention.fst` | `69e4709445b0b40d3e8669081888dd6584bb066c829bbc99520d87b65bf33d06` |
| 背压 `attention.fst` | `9f2619f80b014f77b87fcf3c93024f67daedafb0e9ff7c2c899c49d189973133` |
| 正常 `normalized.vcd` | `2a017e81cc03e7c1fb5d74413e2b4dd809b31f9f1685325c7415bbd917828cbc` |
| 背压 `normalized.vcd` | `fbba60e87fca41c44ddc8070e49093e6b0f8c222e2b8503a8455d38e6db8f136` |

## 剩余步骤

1. 从相同 SRAM 状态补 C380 的 100 MHz 配对空闲窗口，核实未标注引脚，报告活动减空闲能量。
2. 绑定 C639 的布线计算分块，对齐已采集的 Gate/Up、Down 正常与背压波形并回放校准。
3. 用真实指令检查 512-bit SRAM／PM 宽读写和 bank 掩码，标定母控、局控、DMA、互连、时钟和余下计算模块。
4. 完成 Granite 专家并发与 Phi、Falcon 的 V 读取专项 A/B。
5. 逐个扩测七个模型，记录短 Prefill、首个 Decode token、两次退休间 Decode 的时间、平均功耗、能耗、覆盖和误差。补 Qwen2.5-3B 同口径参照。
6. 用齐备的片上、DDR 芯片、PHY 和板级证据汇总系统 mJ/token 与误差区间。

#280 进行中，PR #281 草稿待独立审查。登记 PR #5 待合并。Projects 缺配置，待具权限维护者核验。
