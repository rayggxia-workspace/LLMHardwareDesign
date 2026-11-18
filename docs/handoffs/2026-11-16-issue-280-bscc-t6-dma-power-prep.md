# Issue #280 BSCC-T6 DMA 测量准备和已验收结果

北京时间 2026-11-16。项目 `llm-hardware-design`，负责人 Melodydt，任务分支 `task/280-seven-model-energy`，本轮起点 `524fa3cc1446d72dc38c636323da52cb511a62a8`。服务器 `ssh.cn-zhongwei-1.paracloud.com`，工作根 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01`，工具在 `~/LLMHardware/opt`。原冻结 Qwen3 回放 116481，C639 重放活动 116937，物理 SDC 源自原 C639 300 MHz 回执。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)

## 已完成

- **38769452** 在 `m3ca2408` 用 24 核运行 23 分 36 秒，17:08:39 `COMPLETED 0:0`。源路径及资产、逐层结果、退休、DDR 快照、单通道／方向计数与积压守恒均通过。经 `sha256sum -c results.sha256` 二次核验。服务器文件 `replay/replay-38769452/dma-windows.json`，SHA-256 `280925a47538286fad54fb530a04ed483003e1d59144e06b7993e74172675123`。
- **38770731** 在 `m3ca0104` 用 8 核运行 27 秒，`COMPLETED 0:0`。原 C639 的两工况 × Gate/Up 与 Down 共四窗口均无 writer 写握手。使用 38769390 最终网表、SDC、寄生及边界波形，得到无写握手参考 **3.949908–3.967356 mW**，漏电约 **0.3064 mW**。每个 27.306667 µs 样本的 2,550 个边界引脚实标，29,310 个其余引脚由工具推算。服务器 `writer-power/power-38770731/results.sha256`，清单散列 `236fc49aac7a9a30a694d542a3e95b777228026ac9194156f0a3bcf120ac65a1`。
- **38771074** 残差写回在 `m3ca0104` 用 12 核运行 5 分 05 秒，`COMPLETED 0:0`。使用冻结绑定的 `s128_kv_store_scope`（`TOPOLOGY=25001`，`ACTIVATION_ROW=1`）、`s128_kv_row_transfer` 和 `s128_ddr64_store`。300 MHz 布线提取 setup **+989.615 ps**、hold **+1.093 ps**、详细布线 DRC **0**。网表／ODB／SDC／SPEF 与报告通过清单验收。位置 `residual/physical-38771074/`，清单 SHA-256 `270f75cf0ef147b48170a9fc5e487d8fa66ed08fc50977ea8913f6178ba4b8c5`。首次 38770759 因漏列 `s128_ddr64_store` 展开失败，补入冻结闭包后通过。
- **38771837** 在 `m3ca1403` 用 12 核运行 2 分 09 秒，`COMPLETED 0:0`。使用 116976 原 ODB、SDC 和 SPEF，复现 M 300 MHz 最差 setup **−1.121800 ns**、最差 hold **−53.419 ps**。路径报告在 `m-sta/sta-38771837/`，清单 SHA-256 `5aaf6d2c48ee5276416219337833e79d1c0742834e4ddeaeef7ebdfac597b952`。此结果是修复前对照。
- `qwen3_dma_power_rollup.py` 使用验收后的 DMA、已归档 DDR＋G32 和逐层回放服务日志完成三个窗口对齐。服务器 `window-rollup/rollup.json`，SHA-256 `16e954a45c28fcec81643265caa3b2ec0a64dc66eb88a7f50750df43dfc4d5af`。服务签名可用于后续归属 M／SRAM／PM。当前只确认调度记录的调用数，逐实例驻留和 SRAM 硬件 bank 数待归属，DMA 瓦数保留空值。

| 入口窗口 | 读完成 | 写完成 | 记录到的 TLM 服务调用 |
| --- | ---: | ---: | ---: |
| Prefill，85.289805 ms | 14,782,150 | 17,920 | 15,738 |
| 首 token，139.703052 ms | 13,794,813 | 8,960 | 9,058 |
| 两次退休间 Decode，139.833835 ms | 13,801,957 | 8,960 | 9,058 |

## 并行作业及追踪

17:37:50 查得 38769386、38769388、38772137 正在运行，38772138 等待依赖。全部为 `v6_384` 和 `UNLIMITED`。命令使用前缀 `sbatch --parsable --time=0`，目录相对工作根。

| 作业 | 目录／节点／核数 | 命令（前缀之后） | 日志与结果 |
| --- | --- | --- | --- |
| 38772137 宽回包和活跃写回波形 | `wide/`，`m3ca0303`，12 核 | `run_bscc_t6_c639_wide.sbatch` | `slurm-38772137.log`，`wide-38772137/replay-38772137/` |
| 38772138 活跃写回功耗 | `writer-active/`，节点待分配，8 核 | `--dependency=afterok:38772137 --kill-on-invalid-dep=yes run_bscc_t6_c639_writeback_power.sbatch 38772137` | `slurm-38772138.log`，`power-38772138/` |
| 38769386 共享读 DMA | `physical/`，`m3ca0405`，12 核 | `run_bscc_t6_dma_physical.sbatch shared` | `slurm-38769386.log`，`physical-38769386/` |
| 38769388 阶段切换 | `phase/`，`m3ca0504`，12 核 | `--job-name=mdt-280dmaphase run_bscc_t6_dma_physical.sbatch phase` | `slurm-38769388.log`，`physical-38769388/` |

38771638 编译完成，运行因归档漏收 `assets.txt` 引用的图像退出，依赖 38771802 随后自动取消。补传九个文件并验证 `assets.txt` 的十二个文件引用全部存在，归档 SHA-256 `f9b3c34ee6a90575fe11f536ee12553b9e030e1111a0d3c0eee77a111ed23c6f`。在原门级 G32＋RTL C639 夹具中复用冻结指令和事务输入，将 trace 位宽设为 8,192，并由真实写握手触发附加窗口。通过判据包括原读、写和激活事务以及提交 KV 的字节一致性、完整 6,144-bit 回包观测和活跃窗存在写事务。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
squeue -j 38769386,38769388,38772137,38772138 -o '%i|%j|%T|%N|%C|%l|%R'
sacct -X -j 38769386,38769388,38772137,38772138 -o JobID,JobName,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 20 wide/slurm-38772137.log wide/wide-38772137/replay-38772137/build.log
tail -n 20 physical/physical-38769386/flow.log phase/physical-38769388/flow.log
(cd wide/wide-38772137/replay-38772137 && sha256sum -c wide-results.sha256)
(cd writer-active/power-38772138 && sha256sum -c results.sha256)
```

Melodydt 下一步核验宽波形和活跃写回功耗，验收读侧网表与布线，并补采残差写回与读侧同窗活动。随后用已对齐的计数将 DMA 融入三窗小计，继续补齐 M、SRAM／PM、控制、互连和时钟。M 的关键路径修复以本轮复现的报告为对照。

项目结构检查、Python AST、Bash 语法、工具固定输入和已完成工件散列已核验。规则 rayggxia-project-collab 1.0.0。#280 进行中，[PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) 草稿待审查，登记 PR #5 待合并，组织 Projects 条目待管理员核验。
