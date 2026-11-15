# C639 活动验收与 C380 门级接口绑定

2026-11-15（Asia/Shanghai），负责人 Melodydt。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [S128 与 C380 原始采样](GATE_ACTIVITY_01.md)

## C639 的终态

原生回放步骤 `116856.0` 在 c64/node9、12 核，23 分 44 秒 `COMPLETED 0:0`。两个完整工况的周期、Q tile 数和 DDR 读取与 `115347` 一致，DDR 读事务、写事务、激活事务及提交的 KV 文件逐字节一致。父作业 `116856` 在 24 分 05 秒时因日志层级新增 `TOP.` 导致字节比较失败。第一次后置对账 `116858` 处理了层级前缀，仍因 Verilator 在同拍交错打印不同来源的事件而退出。两份原日志与失败证据均保留。 [提交与初始状态](../../../docs/handoffs/2026-11-15-issue-280-c639-activity.md)

修订对账 `116887`（`mdt-280c639a`）在 c64/node12 单核运行 23 秒，`COMPLETED 0:0`。源码 `4de8147f54fc146872557e6b8ff0f6e93b0249b7`，按皮秒对齐并逐项保留同一来源的输出顺序，验证每条事件的字段、时刻及同拍内每来源的序列。允许同一时刻不同来源的日志交错。另独立比对完整事务、KV、功能结果和 FST 窗口清单。未重做模型仿真，复用 `116856` 的四份原始波形。

| 工况 | 完整回放周期 | 验证 FFN 事件数 | 同拍交错的时间点 | 活动窗口 |
| --- | ---: | ---: | ---: | --- |
| 正常 | 2,654,967 | 1,944,591 | 458 | Gate/Up、Down 各 81.92 µs |
| 背压 | 2,845,147 | 1,941,100 | 420 | Gate/Up、Down 各 81.92 µs |

服务器 `yuzelu@10.129.166.172`，复核工作目录 `/public/home/yuzelu/Melodydt/runs/issue-280/gate-c639-01/semantic-audit-01`，命令 `sbatch --parsable audit_c639_activity.sbatch 116856`，日志 `slurm-audit-116887.log`，结果 `audit-116856-116887/`。结果清单 SHA-256 为 `576392983654e749b0b83c598e8b3c224676292d3afa063742aab91129e1da09`。

| 波形（相对原回放的 `c639-116856/replay-116856`） | SHA-256 |
| --- | --- |
| `DDR-0/ffn-gate-up.fst` | `bc241e48dfb13c19b58fca4d606fbd7206745a65b8fbeba78ea4f086570f154d` |
| `DDR-0/ffn-down.fst` | `584fb8d342ec517977c655c48c9fbb6fc8b3e7b1b083646762d030dc14f5bff2` |
| `DDR-1/ffn-gate-up.fst` | `bfa98d282fc1e70a223ee23094ac89c84e317a03f02d540af8ae55fcdca15c0a` |
| `DDR-1/ffn-down.fst` | `54ed11c195d07b77629c2c2a740e965f3a17dbfa1e7d648839c448c88f56c7af` |

## 实际端口与物理证据

作业 `116893`（`mdt-280bind`）在 c64/node9 单核运行 14 秒，`COMPLETED 0:0`。源码 `00d6a68a34e2d7cb0444dd8ec18c04236c74085d`，部署包 SHA-256 `f3d60002077e3026a624b053cbf5947f62ba210cff9db11394507fa82595a891`。使用 Verilator 5.042 自带的 FST 读取源码核对六份波形的实际时间边界、层级、信号名和位宽。读取器、源和结果均由 SHA-256 固定。

- **C380**。两份 20.48 µs 波形各有 26,575 个含变量的作用域和 120,949 个信号名。从 `TOP/test_native_attention_core_scope/storage` 找到全部 10 个普通 SRAM 端口，共 **273 位**。与 #200 `run08-base0` 的已布线 `local_s_base` 网表端口名和位宽逐项匹配。对比 C380 和原标定已归档 RTL，`local_s_base.sv` 与 `block_feed_s16k_sram.sv` 逐字节一致。已核验原 Liberty、ODB、SPEF、SDC、网表和其它归档输入共 9 项的摘要。
- **C639**。四份 81.92 µs 波形各有 106,459 个含变量的作用域和 493,038 个信号名。P0/P1/P2 对应的层级计数分别为 76／81／81，覆盖三路 M 及相关 RTL 层级。C639 的匹配门级分块、寄生和引脚活动映射待继续。

C380 的结论是已建立 **128-bit SRAM 边界端口**对应；从活动窗口得到门级功耗，还需用一致的 SRAM 初态复放，并验证门级内部引脚覆盖、时钟和寄生。512-bit SRAM／PM 宽写及 bank 掩码仍待对应实现和标定。C639 当前为原生 RTL 活动证据。

服务器提交目录 `/public/home/yuzelu/Melodydt/runs/issue-280/gate-binding-01`，命令 `sbatch --parsable run_gate_binding.sbatch`，日志 `slurm-116893.log`，结果 `bind-116893/`。`binding.json` SHA-256 `6394ced9fc9d331bfea7b58e492f4a0e7ce741886e07d24efed0cc67b14b6807`，`output.sha256` SHA-256 `fb7b22a78e9c8e3cee6ddfc46bd4d5239f08bcb799ed6b95901a65005370a7f8`。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-280/gate-c639-01/semantic-audit-01
sacct -j 116856,116858,116887 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
sha256sum -c audit-116856-116887/activity-results.sha256
cd /public/home/yuzelu/Melodydt/runs/issue-280/gate-binding-01
sacct -j 116893 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
sha256sum -c bind-116893/output.sha256
cat bind-116893/binding.json
```

## 剩余步骤

1. 用已绑定的 C380 SRAM 边界信号驱动匹配门级网表，复核初态、功能输出和引脚活动，再计算配对窗口功耗。继续寻找 C639 三路 M／G、局控和互连对应的门级分块并验证映射。
2. 核验实际 512-bit SRAM／PM 的宽读写、各 bank 使能及争用，补齐控制、DMA、互连、时钟等片上标定及留出工况误差。
3. 执行 Granite 专家并发与 Phi、Falcon 的 V 读取优化 A/B。
4. 对七模型逐一测短 Prefill、首 token、两退休 Decode，单列 Qwen2.5-3B 同口径参照。
5. 补齐片上、DDR 芯片、PHY 和板级范围后汇总全系统 mJ/token、各分项贡献和误差。
