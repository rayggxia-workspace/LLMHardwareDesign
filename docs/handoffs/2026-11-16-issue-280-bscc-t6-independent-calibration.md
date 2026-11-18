# Issue #280 Qwen3 并行标定与 M 时序交接

2026-11-16（Asia/Shanghai）。项目 `llm-hardware-design`，负责人 Melodydt，[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280)，[草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)。继续使用 `task/280-seven-model-energy`，本轮基线 `9673c1d079af0beed96ad3ce677e87c22e639b5e`。BSCC-T6 登录目标 `ssh.cn-zhongwei-1.paracloud.com`，工作根 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01`，工具根 `~/LLMHardware/opt`。原冻结基线为 Qwen3 116481、C639 116937、M 物理 116976。各批作业输入清单和工具版本留在对应服务器目录。

## 已验证的功耗与时序证据

- 38782228 补验收 38772137 的两种工况共六份波形。原作业的 Verilog 回放及波形已落盘，旧 Python 路径导致收尾退出 127，依赖 38772138 随后取消。补验收重跑 QKV 和 DDR 对账，验证读、写、提交 KV、激活及 6,144-bit 回包。每窗 8,192 周期。以下边界事件和翻转仅用于读侧功耗标定，按 DDR owner 和 lane 的明细已保存。清单 SHA-256 `412a49edc11122fcf0edb80244396c8d753db3b78cd5f3032a8bb0bab1f036e0`。

| 工况 | Gate/Up 回包事件／总翻转 | Down 回包事件／总翻转 | FFN 活跃写窗的读回包事件／总翻转 |
| --- | ---: | ---: | ---: |
| 0 | 8,286 / 2,402,315 | 10,935 / 3,173,403 | 2,658 / 768,250 |
| 1 | 7,548 / 2,170,970 | 10,506 / 3,064,956 | 1,842 / 532,004 |

- 38782231 在 300 MHz FFN writer 后布线网表上重放活跃窗口，每种工况写入及退休各 128 笔。全 8,192 周期的总功耗为 3.952648 和 3.951190 mW。清单 SHA-256 `67c9e0142c32908266b110cf18034d8ab917fbf75a63865eb5a9a01894578f75`。
- 38783246 在相同 wave 内使用活跃及等长后续静默片段。工况 0 的活跃／静默功耗为 4.004013／3.922154 mW，增量 0.615 nJ／128 笔（4.803 pJ/笔）。工况 1 为 3.985797／3.921326 mW，增量 0.623 nJ／128 笔（4.871 pJ/笔）。这是 FFN 写回模块用边界波形传播估计的增量。首次 38783130 已算出相同数字，因校验清单引用了错误的文件名退出 1，修正为 `receipt.json` 后重跑核验。清单 SHA-256 `dd772da6e178b8822c3ae31de3f014672d655ad9ffa0bf929fbf996e89f79c87`。
- 38782230 扫描原六窗，均缺残差 writer `feed_forward/next_layer/store` 活动层级。定向补采 38782602 在冻结 typed C639 中选中了旧 `chain_wr_valid` 路径，未触发活跃残差窗，退出 1，依赖 38782604 取消。实际产品第二残差由 `product_residual_add` 写入本地 SRAM。38771074 的 300 MHz `ACTIVATION_ROW=1` 网表作为单独范围的参考保留，不能按此波形计入 Qwen3 DMA。
- 38783129 在固定寄生下更换四个已知缓冲器后，setup 最差由 −1.121800 ns 变为 −1.117046 ns，改善 4.754 ps。hold 仍为 −53.419 ps。此项使用同一冻结 ODB、SDC 和 SPEF，清单 SHA-256 `3245c50e5676dcb5d0e3b3b676314b0d53fd12e8150b56323ed2755adfb5f940`。
- 38783480 反查 ODB，最差 setup 为 `word3[54] → a_ready`，最差 hold 为 `a_session[2] → local_frame[130]`。RTL 中 `a_ready` 的 `A_wait_bind` 用通用 `command_bad`。EXEC 的校验不读 `word3[54]`，该位经检查其他 opcode 的组合逻辑连到 EXEC 握手门控。清单 SHA-256 `bc42327859edd52eafb4344af0f5047c3d2f9bfcd5937dafe5c7aab049e06b43`。
- 38784054 生成 EXEC 专用校验候选，采用同一组 EXEC 字段判据。Verilator 5.042 `--lint-only --Wall` 通过，Yosys SAT 证明等价组合控制模型的 `A_wait_bind`、`bad_A` 和 `a_ready` 相同。领域模型的其他 opcode 响应及下游握手均为独立的符号输入。新 RTL SHA-256 `c29d31b8c21441cdf7abd3be57a47bec56fb67180d7cc143977477c1ef1d2f26`，清单 SHA-256 `015177dce2cb9603657ae73f3071b9529070ea699522575b2e143a78992ac046`。完整 RTL 回归、重新综合布线和 300 MHz setup／hold 待做。

## 已对账的整窗活动

38782605 在 24 分 32 秒内完成，退出 0。三窗 DMA 结果与已验收的 38769452 逐字一致，SHA-256 `280925a47538286fad54fb530a04ed483003e1d59144e06b7993e74172675123`。两份事件文件经 `replay-38782605/results.sha256` 核验，清单 SHA-256 `aaa8869d8ca28d199e1fcadf36bfa73a9d3710c25dd950d4dca821d0323499b6`。

| 整窗 | SRAM 读拍（其中 512-bit） | SRAM 写拍（其中 512-bit） | M 模型计算组／各站点合计忙时 | PM 写拍（母控／局控） |
| --- | ---: | ---: | ---: | ---: |
| 短 Prefill，两输入位置 | 1,969,026（1,364,224） | 866,114（591,040） | 516,096／27.530625 ms | 1,464／24 |
| 首 token | 4,975,417（4,614,648） | 4,280,785（4,066,656） | 258,048／13.765313 ms | 737／24 |
| 稳态 Decode，两次退休间 | 4,982,585（4,621,816） | 4,287,953（4,073,824） | 258,048／13.765313 ms | 737／0 |

SRAM 计数逐站点、逐 128-bit bank 与原 TLM 统计核对。各记录还保留 128/256/384/512 bit 的实际拍宽。M 忙时是每个 TLM 站点的区间并集，再对站点求和。PM 计数保存实际母控和局控加载的字节、读回及包含 DDR 等待的服务时间。TLM 的 512-bit PM 写拍需要与已测 128-bit PM 物理端口对齐后才能积分能量。最终功耗仍需绑定实际门级、物理实例和时钟。

`independent-rollup/rollup-38782605.json` 将这些计数与 Qwen3 的既有 DDR＋G32 小计一起对齐，SHA-256 `2be7652e9bf665f42ed085841a683aab6d906f1a679d0ce594513516f19a758e`。三个窗口的 DDR＋G32 小计约为 2.6953、2.3821、2.3804 W，以及 114.942、332.793、332.857 mJ/token。DMA 瓦数保留为空。

逐个解析 112 份实跑描述符，约束每项写为 512 字节八个 DDR burst，按地址归属 16 项 KV 和 24 项 FFN backing 每层每位置，核对 Slurm 回放中 DMA 三类守恒计数。Prefill 为 KV 7,168 + FFN backing 10,752 = 17,920 笔，首 token 和 Decode 各为 3,584 + 5,376 = 8,960 笔。ADD2 残差分别调用 112、56、56 次，位于 U/SRAM，归属时不得重复计入 DMA。验证结果 `independent-rollup/write-attribution-38782605.json` 包含所有输入描述符 SHA-256，结果 SHA-256 `86b6448e646c86fa276d11e5bc91ce6db2f33c698997f96c1e9bd1fd7f9b032a`。

原六窗的 `typed_dma`／`phase0`／`phase1` 表均匹配阶段包装的 117 个声明、26,307 bit（含时钟、复位和 owner），可用于后续匹配最终路由网表。

## BSCC-T6 作业与追踪

全部作业为 `v6_384`，`TimeLimit=UNLIMITED`。表中目录相对工作根。命令省略统一前缀 `sbatch --parsable --time=0`。日志位于提交目录的 `slurm-<作业号>.log`。

| 作业 | 目录／CPU／节点 | 启动命令（统一前缀之后） | 结果目录（相对提交目录） |
| --- | --- | --- | --- |
| 38782228 宽波形补验收与读侧活动 | `wave-audit/`／8／`m3ca0703` | `run_bscc_t6_c639_wave_audit.sbatch` | `audit-38782228/` |
| 38782230 原残差覆盖扫描 | `residual-power/`／8／`m3ca1302` | `run_bscc_t6_c639_residual_power.sbatch` | `power-38782230/` |
| 38782231 活跃 FFN writer | `writer-active-recovered/`／8／`m3ca0703` | `--dependency=afterok:38782228 --kill-on-invalid-dep=yes run_bscc_t6_c639_writeback_power.sbatch 38772137` | `power-38782231/` |
| 38783246 FFN 同波形配对重测 | `writer-paired/`／8／`m3cd0805` | `run_bscc_t6_c639_writer_pair.sbatch` | `pair-38783246/` |
| 38783129 M 固定寄生换档 | `m-sizing/`／12／`m3ca0204` | `--job-name=mdt-280msize run_bscc_t6_c639_m_sta.sbatch sizing` | `sta-38783129/` |
| 38783480 M 时序网名反查 | `m-path/`／12／`m3ca0104` | `--job-name=mdt-280mpath run_bscc_t6_c639_m_sta.sbatch trace` | `sta-38783480/` |
| 38784054 M EXEC 候选 | `m-exec-ready/`／8／`m3ca1104` | `run_bscc_t6_c639_m_exec_ready.sbatch` | `check-38784054/` |
| 38782602 残差活动补采 | `residual-wave/`／12／`m3ca1001` | `--job-name=mdt-280reswave run_bscc_t6_c639_wide.sbatch residual` | `wide-38782602/replay-38782602/` |
| 38782604 残差写回功耗 | `residual-live-power/`／8／未分配 | `--dependency=afterok:38782602 --kill-on-invalid-dep=yes run_bscc_t6_c639_residual_power.sbatch 38782602` | `power-38782604/` |
| 38782605 Qwen3 分项事件 | `component-observation/`／24／`m3cd0902` | `--job-name=mdt-280component run_bscc_t6_qwen3_dma.sbatch` | `replay-38782605/` |
| 38769386 共享读 DMA | `physical/`／12／`m3ca0405` | `run_bscc_t6_dma_physical.sbatch shared` | `physical-38769386/` |
| 38769388 阶段切换 | `phase/`／12／`m3ca0504` | `--job-name=mdt-280dmaphase run_bscc_t6_dma_physical.sbatch phase` | `physical-38769388/` |

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
jobs=38782602,38782604,38782605,38769386,38769388
squeue -j "$jobs" -o '%i|%j|%T|%N|%C|%l|%R'
sacct -X -j "$jobs" -o JobID,JobName,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 12 residual-wave/slurm-38782602.log residual-live-power/slurm-38782604.log component-observation/slurm-38782605.log
tail -n 12 physical/physical-38769386/flow.log phase/physical-38769388/flow.log
(cd wave-audit/audit-38782228 && sha256sum -c audit-results.sha256)
(cd writer-paired/pair-38783246 && sha256sum -c results.sha256 && cat mode-*/paired.json)
(cd m-exec-ready/check-38784054 && sha256sum -c results.sha256)
```

## 当前作业和下一步

- 20:32:36 两项旧读侧物理作业 38769386 和 38769388 已运行约 3 小时 50 分，仍在 Yosys `SHARE`。自 16:44 无新综合里程碑，作业步骤累计 CPU 继续增长，RSS 约 8.2/8.5 GiB。映射与布线尚未开始，剩余时间无法可靠估计。
- Melodydt 读回两项共享读 DMA 和阶段 mux 的 300 MHz 网表、SDC、SPEF、STA 和 DRC；确保共享读 DMA 与阶段 mux 的重叠层级只计一次。按已验收的六窗做 normal/backpressure 对照，拟合读侧活动与空闲功耗。
- 对 Qwen3 的 KV 和 FFN backing 两类八拍写分别校准，并用描述符握手和地址检查写侧映射。C639 的 128 笔 FFN writer 配对值单独保存，待确认对两类 Qwen3 写流的适用性。
- 同步继续 M 的 RTL 功能回归与 300 MHz 重新综合布线。核验 `word3[54] → a_ready` 的修复并单独关闭 hold，之后才更新 M 校准边界。继续补齐 SRAM 拍宽、母控/局控 PM、控制、互连和时钟的物理活动与功耗。
- 对齐三窗逐项积分，合并 DDR、G32、DMA 和片内分项，报告每窗 W 和 mJ/token 以及公开缺口。Qwen3 完成后按相同验收口径推进其余模型。

验证包括 `python scripts/check_project.py`、Python AST、被提交脚本的 Bash 语法、Slurm 终态和完成工件清单。项目规则 rayggxia-project-collab 1.0.0。#280 保持进行中，#281 草稿待审查，独立审查人待指定。登记 PR #5 待合并，组织 Projects 缺 `config/board.json`，条目待具权限的维护者核验。
