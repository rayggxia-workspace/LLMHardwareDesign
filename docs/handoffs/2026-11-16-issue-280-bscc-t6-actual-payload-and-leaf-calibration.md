# Issue #280 真实写数据、PM 和 U 功耗标定交接

2026-11-16（Asia/Shanghai）。Melodydt，分支 `task/280-seven-model-energy`，本轮起点 `7ef674ac56a6f0c61ae87127667aa037b3e4bb51`。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [上轮物理标定](2026-11-16-issue-280-bscc-t6-physical-calibration.md)

工作根为 BSCC-T6 `ssh.cn-zhongwei-1.paracloud.com` 的 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01`，工具根 `~/LLMHardware/opt`。继续用仓库冻结 RTL、300 MHz Nangate45 约束、Verilator 5.042、ORFS/OpenROAD/Yosys。作业均为 `v6_384`、`UNLIMITED`。每个目录的 `inputs.sha256`、`physical.sha256`／`results.sha256` 和服务器快照标识其实际输入与输出。

## 已完成与复查入口

- **38794389** 用 21 分 26 秒完成真实数据回放。保持 TLM 调度，采集地址、tag、发出／提交时间和 64 字节小端载荷。与合格的三窗 DDR 回放对账，得到 **17,920／8,960／8,960** 笔提交。每窗还记录实际安装 PM 页的源地址、有效字节和起止时刻。 `real-activity/replay-38794389/results.sha256` 的 SHA-256 为 `c3d3382676d313c0b3047521d8947ca46268699b3a7a021b50d4d877ef6c81d5`。
- **38795264／38795265／38795266** 用 2:44／2:16／1:54 完成三窗写侧重测。全部 4,480 个八拍写跨度与真实地址逐笔核对，选择固定对照、每跨度内部相邻 512-bit 拍翻转数的中位数及第 90 百分位，重复样本去重，共 26 个代表跨度。每个在正常和背压工况分别做活跃／静默配对。全范围 **22.52–24.46 pJ/64 B**；稳态 Decode 同描述符 K/V/FFN 正常工况为 **24.302／23.752／23.251 pJ/64 B**。同网表替代数据原值为 23.403／23.301／23.335 pJ/64 B。抽样范围不作为全模型逐拍上界。三个 `real-span-power/span-<job>/results.sha256` 的 SHA-256 依次为 `b7c757d797b4508e033cf8b6eebe0cb61cdbb4d98f36b08ea2899b6ed11cf27a`、`41ec90af2a2ecaea6b14c427599937437bda812a073e7b45e38910b18a8f9b87`、`655a5a854d336f4bd206d0485266ee829efd57cbcdb1949ae0469e5f37e43528`。
- **38794460／38794931／38795055** 完成局控 PM 候选 `lc_program_store_1k` 的布线、功能回放、活跃／静默标定。原始真实 352 字节程序含 22 个有效 128-bit 字，合格写、CRC 和逐字读通过。TT 300 MHz setup **+1.0965 ns**、hold **+6.859 ps**、详细布线 DRC 报告空。写入加 CRC 增量 **0.067392 nJ/页**，22 字读回 **0.187457 nJ**。测量覆盖 1 KiB 局控寄存器阵列候选，运行时的整个产品 fetch 次数仍待对应。功耗结果 `pm-arrays/array-38795055/results.sha256` 的 SHA-256 为 `9ae313a9f18d3c356be9ff4477edea11af6a3de062086ccbbbb5482642c49c84`。
- **38795749** 按真实装载有效长度复查。母控 **1,616／240／272** 字节对应 **101／15／17** 个物理 128-bit 读和写；1,616 字节页从 26 个 512-bit 回包载入，四 bank 分别执行 26、25、25、25 次对应读写。原 1,664 字节文件含填充，其桥接测量单独保留。实际 1,616 字节 PM 桥接增量 **0.595–0.701 nJ/页**；240／272 字节页分别 **0.631–0.754／0.670–0.796 nJ/页**，实际局控 352 字节页 **0.629–0.727 nJ/页**。母控阵列只有功能活动证据，尚缺 TT 宏库及物理绑定。结果 `pm-real-length/pm-38795749/results.sha256` 的 SHA-256 为 `18ba1ceca4fc26c4e8089926ddfca9b9c4ac42b2ca0233ed1ae77a2c43bdeea2`。
- **38795282／38795283／38795284** 单独绑定 U 的字级控制、ADD2 调度、E32 算术。三者物理作业 **38794459／38794680／38794679** 均满足 300 MHz setup/hold，详细布线 DRC 报告空。相同 32-word 退休窗口与等长先前空闲窗口的增量为 **3.624／0.475／118.929 nJ**，不包含 SRAM 实体。使用确定性残差夹具，同样的数据隔离/负载跨模型仍待核。三清单 SHA-256 依次为 `488d230232649a2549b25e984dfd92fc3f0fee7b27055e242c302939dbe993ad`、`99f117392a247914881125a17dbd4bbfc8bedf497824fc7cbdd10f8f23013fd5`、`f6c15779f29379953e815ed3fd3c4d44acb068c97467d7625abb94ef94470689`。
- **38795515** 对当前 S128 路径做 96 次 128-bit 读和 96 次写的数据、bank 选通和读回对账。16 组逻辑 256-bit 写以两拍串行，16 组逻辑 512-bit 写以四拍串行。512-bit feeder 读仍为同址四 bank。稳态 Decode 在四个 TLM 站点累计 **360,769** 次普通 128-bit 读；按此串行路径折算 **16,571,425** 次 128-bit 写。该折算描述现有端口路径和事件量，最终物理调度及新增功耗仍需绑定。 `sram-width-check/width-38795515/results.sha256` 的 SHA-256 为 `e726e78b6a6e9a3f0bf75e2daa705984bed848a3e5ae5e0cdee8bb10efb537ff`。
- **38796084** 核验 M 同源 C639 回归的三实例 × 六窗口共 **18 份** 1,330-bit 端口波形，准备后布线输入。清单 SHA-256 `fe5438666b593d8dddbe2e5c2061d6bd4a53f701568f7d11d286a80530113e8a`。
- **38796363** 完成母控核、母控交接和四组局控／调度等 11 个逻辑作用域的六窗活动清单，保存位宽、翻转数与共享 VCD 标识。不能直接由该清单得出控制功耗。位置 `control-activity/activity-38796363/`，清单 SHA-256 `5752535e3915c283390acbab4114014dfeea2600365da58f09a12a1c1de73d49`。38796285 因宿主 glibc 版本不匹配退出，复跑在已验证容器内完成。
- 分项校准表 `calibrated-coverage/windows.json` 已对齐三窗。写侧抽样缩放后为 **419.0–428.4／206.2–217.3／205.9–216.7 nJ/窗**。U、PM、SRAM 的参考项单列，保留其输入范围及去重边界。清单 SHA-256 `d779e8ecb846356e327f2e1b57aee6f9c3679e273cf55aa03cf218164c51b4a0`。尚无完整片内和含 DMA 总功耗。

## 持久作业与下一步

命令均使用 `sbatch --parsable --time=0`。可在以下服务器目录查看 `slurm-<job>.log` 与清单。状态以 `sacct` 和物理日志为准。

| 作业 | 目录、核数 | 入口参数／依赖 |
| --- | --- | --- |
| 38794389 真数据回放 | `real-activity/`，2×12 核 | `--job-name=mdt-280realwrite run_bscc_t6_qwen3_dma.sbatch` |
| 38795264／265／266 写侧真数据功耗 | `real-span-power/`，8 核各 | `--dependency=afterok:38794389 --kill-on-invalid-dep=yes run_bscc_t6_qwen3_real_span_power.sbatch 38794389 <prefill\|first_token\|decode>` |
| 38794460 局控阵列布线 | `leaf-physical/`，8 核 | `run_bscc_t6_leaf_physical.sbatch lc-pm` |
| 38794931／38795055 PM 阵列波形／功耗 | `pm-arrays/`，8 核各 | `run_bscc_t6_qwen3_pm_arrays.sbatch wave`／`power 38794931 38794460` |
| 38795749 实际 PM 页 | `pm-real-length/`，8 核 | `run_bscc_t6_qwen3_pm_real.sbatch 38794389` |
| 38794459／38794680／38794679 U 布线 | `leaf-physical/`／`leaf-physical-retry/`，8 核各 | `run_bscc_t6_leaf_physical.sbatch <u-lane\|u-dispatch\|u-arith>` |
| 38795282／283／284 U 功耗 | `u-component-power/`，4 核各 | `run_bscc_t6_qwen3_u_power.sbatch <add\|scope\|e> <物理作业目录>` |
| 38795515 SRAM 端口 | `sram-width-check/`，8 核 | `run_bscc_t6_qwen3_sram_width.sbatch` |
| 38796363 控制边界 | `control-activity/`，4 核 | `run_bscc_t6_c639_control_activity.sbatch` |
| 38796084／38796085 M 波形／功耗 | `m-candidate-power/`，8 核各 | `run_bscc_t6_m_candidate_power.sbatch wave`／`power 38796084`，功耗等待 38792357 |
| 38795299／38795300 读侧跳过 SHARE 对照 | `read-shared-noshare/`／`read-phase-noshare/`，12 核各 | `run_bscc_t6_dma_physical.sbatch <shared\|phase> no-share` |
| 38795516／517 原读侧功耗 | `read-calibration/`，8 核各 | `run_bscc_t6_c639_read_power.sbatch <shared\|phase> <物理作业目录>`，分别等待 38769386／38769388 |
| 38795518／519 跳过 SHARE 对照功耗 | `read-calibration/`，8 核各 | 同上，分别等待 38795299／38795300。此路径作为对照保留，纳入正式模型前需完成等价证据。 |

首次 U 算术占用面积过高，首次 ADD2 调度 I/O 数超限，按实际单元与引脚数量扩展布局后通过。U 首轮 64 words 的空闲对照不足，缩为 32 words 且验证同样窗口。一份 M 波形预检因映射 Verilog 端口与 wire 交错而提前结束，隔离顶层端口声明后通过。所有正式结果均引用成功复跑。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
jobs=38769386,38769388,38792357,38795299,38795300,38795516,38795517,38795518,38795519,38796085
squeue -j "$jobs" -o '%i|%j|%T|%M|%N|%C|%l|%R'
sacct -X -j "$jobs" -o JobID,JobName,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 12 physical/physical-38769386/flow.log phase/physical-38769388/flow.log m-physical-exec/physical-38792357/flow.log
tail -n 12 read-shared-noshare/physical-38795299/flow.log read-phase-noshare/physical-38795300/flow.log
sha256sum -c calibrated-coverage/results.sha256
```

23:52:43，M 38792357 运行约 1 小时 17 分，已经进入 CTS；详细布线和寄生提取仍待完成，按小时级安排。原 38769386／38769388 运行超过 7 小时，最后日志仍为 `SHARE`。跳过 `SHARE` 的 38795299／38795300 已运行约 22 分钟，推进至 `OPT_MEM_PRIORITY`，尚无可据以估算完成时刻的映射／布线路标。运行步骤 CPU 累计持续增长。5 项功耗依赖均等待相应物理作业。

Melodydt 后续验收 M 和读侧的路由、寄生、300 MHz STA／DRC 与功能条件，读取依赖作业产出的功耗并按共享层级去重。普通 128-bit、宽写映射、母控 PM 的门级能耗仍需匹配 `s_sram_256x128_freepdk45_TT_1p1V_25C.lib`、宏 LEF 和原布线工件。BSCC-T6 当前只有该宏的功能 Verilog。旧服务器主机指纹核对通过，但批量身份认证失败。补档入口为共享项目 `issue-155/bank-views-011` 及 #200 SRAM 路由归档。完成分项物理绑定后再出短 Prefill、首 token、稳态 Decode 的 W 和 mJ/token。

规则 rayggxia-project-collab 1.0.0。项目管理检查、Python AST、脚本语法、完成工件散列与 Slurm 终态均查验。#280 进行中，#281 草稿待审查，独立审查人待指定。登记 PR #5 待合并。看板条目待有权限维护者核验。
