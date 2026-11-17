# Qwen3 控制功耗和剩余整模依赖

2026-11-17（Asia/Shanghai），Melodydt。任务分支 `task/280-seven-model-energy`，工作起点 `9610b0d7a1277e33b8d46f44a3d50edf31cc946b`。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [SRAM／母控三窗积分](2026-11-17-issue-280-qwen3-macro-window-reference.md)

## 当前已覆盖

- 六份 C639 FST 元数据对账通过。四组数据 SRAM、母控四个宏、四个局控 PM、一个 G32、一个 cohort 交换机使用同一 RTL 根时钟别名。每个局控 PM 的实测窗口 8,192 个上升沿。G32 采用和前次活跃增量同一组 Down 静默值 **2.668248 mW**，交换机为 **78.328–78.398 µW**，当前 `mc_lc_packet128_switch` 和 `native_three_lc_cohort` 散列与原始 117841 相同。实际完整 Qwen3 物理时钟分配和门控驻留仍需绑定。[时钟和实例数据](../../work/Melodydt/280/qwen3_c639_clock_audit.json) · [原标定回执摘录](../../work/Melodydt/280/qwen3_control_archived_power_reference.json)
- **38815532** 针对载入并认证 352 B 后的局控 PM，在 6 个带载窗上保持同样时钟和非 PM 侧带活动，将运行读端口固定在起点的排空状态。后布线活动传播的静默值 **30.754–30.762 mW/阵列**，按代表窗读次数折算增量 **17.485–23.914 pJ/次**。这个等长对照保留认证状态的边界活动，内部功耗由 OpenSTA 传播估算。[配对数据](../../work/Melodydt/280/qwen3_c639_pm_quiet_pair.json)
- **38815974** 对冻结 `lc_scope_fetch128` 做 300 MHz 布线和六阶段四站点共 **24 窗** 标定。setup **+0.807214 ns**、hold **+6.47854 ps**，详细布线 DRC 通过。各窗后布线估值 **5.6376–5.6626 mW/叶**。首轮 38815622 输入引脚 2,518 个、只有 1,984 个位置，扩大到 400 µm 方形解决。第二轮 38815672 的 hold 修复触及默认缓冲数量上限。最终布局保持原 300 MHz 约束，将本地缓冲比例上限调为 60%，CTS 和全局布线分别插入 2,966／235 个 hold 缓冲，最终 STA 通过。整窗描述符事件及驻留待绑定。[取指测量](../../work/Melodydt/280/qwen3_lc_fetch_power.json)

按 C639 观测到的实例数加一组 G32 空闲、一组交换机空闲、四个局控 PM 驻留空闲，整窗开钟条件下合计新增 **125.762–125.794 mW**。原小计已有 G32 活跃增量，本次只补其匹配的 Down 空闲。局控 PM 启动／CRC、局控读取和描述符取指暂单列。[更新的小计](../../work/Melodydt/280/qwen3_control_idle_reference.json)

| 窗口 | S_P 并行读情景（mJ/token） | S_base 串行读情景（mJ/token） |
| --- | ---: | ---: |
| 短 Prefill | 163.983–164.105 | 162.429–162.552 |
| 首 Decode token | 493.074–493.199 | 488.160–488.285 |
| 稳态 Decode | 493.287–493.412 | 488.369–488.494 |

## 剩余条件

1. **读 DMA**。12:41 服务器核验，原版 38769386／38769388 已运行 19:58:55，跳过 SHARE 的 38795299／38795300 已运行 13:11:06。四条功耗作业 38795516–38795519 等待依赖。任一合格实现可接获用作分窗归并；跳过 SHARE 的版本需核对等价，阶段包装和内含共享 fabric 只计一次。
2. **整窗运行时活动**。冻结 `issue260-native-sram512-SMbOWTw6/native_tlm_timing.py` 的 `bind_local` 在 Python 解码已封存程序，`install_pm` 提供传输和校验估算，`submit_local` 以 `after_cycles` 合并元数据和几项指令延迟。已有 PM 58／30／30 页是页装载和读回口径。全窗口实际母／局控取指、驻留和描述符交通需要端口活动证据。六窗支持局部估算，运行时能量仍待整窗映射。
3. **母控外围和整机互连**。38815704 定位到内层作用域，修正后 38815787 读到真实母控根和 PM，但 `local_enabled_i` 真实为 **9 位**，恢复的 #223 `mother_control_64` 为 **2 位**。冻结活跃母控为 `mother_control_native64_transport128` 包装的九目标路径。#223 母控四宏标定继续用于已核对的 PM 范围。外围需同版九目标网表和寄生。另需整机物理映射、跨块互连和全局时钟树支撑整窗归属。
4. **验收边界**。当前是参考估算，旧 M 的 setup／hold 违例沿用原记录。正式 300 MHz 验收需新版 M 闭合并重标。整个 #280 还需按同一口径扩到其余六模型。Qwen2.5-3B 同口径参照及 DDR PHY、板级 I/O 继续按各自范围报告。

## 服务器回执

BSCC-T6 `ssh.cn-zhongwei-1.paracloud.com`，工作根 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01`，工具目录 `~/LLMHardware/opt`。以下均 `v6_384`、12 核、`UNLIMITED`。作业名为 `mdt-280pmquiet`／`mdt-280lcfetch`／`mdt-280mccontrol`。

| 作业 | 终态、节点、耗时 | 相对提交位置和结果 |
| --- | --- | --- |
| 38815532 | COMPLETED 0:0，`m3ca0808`，34 s | `pm-quiet/quiet-38815532/` |
| 38815622／38815672 | FAILED 2:0，`m3ca0808`／`m3ca0704`，42 s／1:22 | `lc-fetch-300/fetch-<job>/` 的 `flow.log` |
| 38815974 | COMPLETED 0:0，`m3ca0306`，5:05 | `lc-fetch-300-hold/fetch-38815974/` |
| 38815704／38815787 | FAILED 1:0，`m3ca1001`／`m3ca0606`，13 s／13 s | `mother-control-300/mc-<job>/` 及 Slurm 日志 |

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
(cd pm-quiet && sbatch --parsable --time=0 run_bscc_t6_qwen3_c639_pm_quiet.sbatch)
(cd lc-fetch-300-hold && sbatch --parsable --time=0 run_bscc_t6_qwen3_lc_fetch_power.sbatch 400 60)
squeue -j 38815532,38815974,38815704,38815787 -o '%i|%j|%T|%M|%N|%C|%l|%R'
sacct -X -j 38815532,38815622,38815672,38815974,38815704,38815787 -o JobID,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 15 pm-quiet/slurm-38815532.log lc-fetch-300-hold/slurm-38815974.log mother-control-300/slurm-38815787.log
(cd pm-quiet/quiet-38815532 && sha256sum -c results.sha256 && cat pm-quiet-pair.json)
(cd lc-fetch-300-hold/fetch-38815974 && sha256sum -c results.sha256 && cat lc-fetch-power.json)
(cd control-clock-audit && sha256sum -c results.sha256 && cat clocks.json)
```

局控 PM 静默、描述符取指、时钟核对的结果清单 SHA-256 分别为 `ededc7763d074af2c64320b6ef48d0993ef4dab51318ba7e7eb0b3488e5ecc08`、`e54f1a0b1ba256c804b927dca60e01f8dcc1c377a7453a11d055256741e11085`、`6e824049959942fdaf92ec1bd9d1c8942a34000fadd08b6d6333056e5a87b991`。合并脚本 `qwen3_control_idle_reference.py` 在任务个人目录读取五个已记录的 JSON；输出 SHA-256 `512635198eaec1b349c1a2629557726b86d6e7b367fe832a7e080163a808f582`。项目管理检查和 Python AST 已通过。#280 进行中，PR #281 为草稿，登记 PR #5 待合并，Projects 条目待有权限者核验。
