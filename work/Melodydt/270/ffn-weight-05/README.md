# FFN 四权重 bank 与三路 P 供数

2026-11-14（Asia/Shanghai）。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) · [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。负责人 Melodydt。任务基点 `bbee060feceab03829515713c2b94fecfc47b2eb`，原生父版本为 PR #260 的 `55620f173f2ad540efade8a552c35e9dba0f43c0`。

## 实验与首轮结果

共同配置为 Qwen2.5-3B 原母控程序、512-bit S、ATT1 末轮双窗口、KV 读窗 8 和封存 DDR 配置。A/B 都记录 FFN，B 只在 FFN 打开 PR #260 WeightFetch 模型，含 4 个 M 权重 bank、登记请求、32-beat owner credit、每通道两条 16 深度物理请求队列和 3 深度回包 skid。每层 FFN 为 58 组三 P Gate/Up 和 6 组三 P Down。每个 WAIT 由最后结束的 P 决定，计算三路各自从输入或上条记录就绪到当前权重可执行的累加等待。

| 工作负载 | 同口径基点 | FFN 前四层外推 | 提升 |
| --- | ---: | ---: | ---: |
| 两步 Decode，初始 KV 512，退休间隔 | 2.739536 tok/s（ATT1 第四轮外推） | 2.931091 tok/s | 6.99% |
| 两位置短 Prefill，空初始 KV，到末层残差 | 5.511216 输入 tok/s（ATT1 第四轮完整 TLM） | 6.327444 输入 tok/s | 14.81% |

以 36 层乘以前四层 FFN 页的平均节省。Decode 当前用第一步样本预测第二步退休间隔。短 Prefill 当前将第一位置的节省应用到两个位置。最初两份封存前缀分别有 36/46 个同程序、同 DDR/S 流量页，及 4/5 个成对相同的 8 KiB Down SHA-256。平均每层页节省 0.663 ms（Decode）和 0.650 ms（短 Prefill）。以原第四轮 Prefill 外推 5.504623 为基点时，FFN 外推为 6.318754，已由 113071 的完整 578 页和 SHA-256 校验更新基点。第三轮 112977 的完整短 Prefill 为 5.511880。

前四层 Decode 三路 Gate/Up 的等权重累计为 4.070/4.087/4.001 ms，候选为 3.234/3.325/3.238 ms。Down 为 3.360/3.301/3.314 ms，候选为 1.378/1.378/1.373 ms。各 P 可以并行，表中累积值不可相加为全局时间。候选的 232 组 Gate/Up 中，P1 单独最后完成 109 组，P0 69，P2 53，P1/P2 并列 1 组。

## 原生证据

113181 在 `c64/node12` 用 1 核核验 #260 归档 105802 的正常模式 DDR 轨迹，退出 `0:0`，回包 2,245,632 个，最高在途 63。Gate、Up、Down 加权均值为 6.839、5.713、7.348 个夹具时钟，最长 105 拍。这里的 lane 是 DDR 物理 lane。源输入 SHA-256 与按 lane 统计见 [DDR 回执](native-ddr-113181.json)。

113199 在 `c64/node1` 用 8 核运行两种夹具模式。Verilator 5.042 已构建并写出握手日志。仿真探针采集以 `P/bank/generation/record` 匹配的首发、末发、完整填充、ACK、EXEC 和结果退休。把末发到满填、满填到 ACK、ACK 到 EXEC、EXEC 到结果分开可辨别 DDR 返回、局部确认和执行排队。113195 因夹具要求运行目录的源归档入口，在编译前退出。隔离目录加上指向原归档的链接后提交 113199。原版本 Verilator 夹具只有 C639 这一验证范围。

## 复现与验收

- TLM 使用 Singularity CE 4.3.4、Python 3.10.12、GCC 11.4.0 与固定 DRAMsim3 bridge。运行脚本及逐文件散列见 [TLM 启动脚本](run_ffn_tlm.sbatch)、[生成源码清单](source.sha256)、[输入清单](inputs-113164.sha256)、[原始模型清单](upstream.sha256)。两组 A/B 输入清单已逐字对照。
- 在新的授权运行目录复制 `att1-dot-read-04/tlm` 的 `source/`、`fast_tlm_replay.py`、`fast_tlm_dram.cpp`。从 `issue260-av-weight-GEwVA0Bi/sram-rw-pipeline` 的归档取出清单指定的两个 Python 文件至 `upstream/`。在 TLM 工作目录运行 `python3 -B ../prepare_ffn.py source upstream`，核对 `source.sha256`，再提交 A/B。对账脚本依赖 `att1-selected-01/compare_att1_selected.py`，本次服务器将其复制到 FFN 工作根。
- 原生归档的 SHA-256 为 `8294abc3b8da18f22db091627353b68cdd1498ab2e32c1293a8b0abd56b4a5da`，113199 的 [启动脚本](run_native_probe.sbatch) 为 `64c815130419d4fcd99b4944362028dc0270de857d77b44f221a5140a820754e`。
- 项目结构检查、源和输入清单、Bash 与 Python 语法、两组前缀数值和流量、原生 DDR 归档审计均已执行。完整 FFN A/B 与原生 C639 正常和背压数值回执待收。完整 P512/D128 与 300 MHz 物理 STA 未执行。
- 复现命令、日志、成功判据和后续处理见 [交接](../../../../docs/handoffs/2026-11-14-issue-270-ffn-weight.md)。
