# Issue #280 Qwen3 写侧及片内标定交接

2026-11-16（Asia/Shanghai）。负责人 Melodydt，任务分支 `task/280-seven-model-energy`，起点 `cbfb6f380b20d530de9c7bbc92ecef869f97fc3f`。[Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [草稿 PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281) · [上轮归属证据](2026-11-16-issue-280-bscc-t6-independent-calibration.md)

所有新仿真位于 BSCC-T6 `ssh.cn-zhongwei-1.paracloud.com`，工作根 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01`，工具根 `~/LLMHardware/opt`。使用 Verilator 5.042、ORFS/OpenROAD/Yosys、Nangate45。

## 已完成

- **写侧物理 38792114** 在 4 分 20 秒结束，退出 0。使用 `s128_kv_store_scope` 的 `SHARED_STORE=1`、`TOPOLOGY=25001`，覆盖 KV 和 8 拍激活写。300 MHz setup/hold **+1.16031 ns／+0.801165 ps**，详细布线 DRC 报告为空。网表、SDC、SPEF 和报告清单 SHA-256 `f3b5eb0c3b4f024730fabd72418ab95c5fc2d3e2588c790f76fc13991609e82f`。
- **写侧波形 38792400** 结束于 11 秒，退出 0。来自 Qwen3 Decode 位置 513 第 0 层的 K、V、FFN 中间激活描述符，分别使用真实源地址和目的地址，负载使用确定性替代数据。正常与背压中逐拍验证写数据、地址、tag、完成和 32 笔 S128 读。每种活跃用例均 8 笔发出／8 笔退休；背压用例各阻塞 68 周期。清单 SHA-256 `7877ea14d085bde0d42b60c45d19a13978a92dd76c329aca96d655b4f9803695`。
- **写侧功耗 38792563** 结束于 44 秒，退出 0。用同一 300 MHz 物理模块和等长活跃／静默配对，采样窗口 1,045 个源周期。K 两工况为 **23.403／23.255 pJ/64 B**，V 为 **23.301／23.155 pJ/64 B**，FFN 中间激活为 **23.335／23.192 pJ/64 B**。活跃总功耗 **4.819–4.824 mW**。实标 2,284 个边界引脚，其余 34,479 个未直接标注。数据依赖和整模型实例归属待测。清单 SHA-256 `d9c63831b1ab9de70f11bbb6e3d1de67a9f5c8f9aa9b74d49ecea9907179cca4`。
- **片内活动 38792815** 结束于 10 秒，退出 0。SRAM 512-bit 读同址选通四个 128-bit bank，普通 128-bit 访问只有一个 bank。U ADD2 按实际描述符的 256 words 完成逐字比对、别名拒绝和取消排空。PM 1,664 字节程序分成 26 个 512-bit 回包和 104 个 128-bit 写确认，352 字节短页分成 6 个回包和 22 个写确认。两组各通过正常／背压。VCD 和回执清单 SHA-256 `7d02b7afdb1422d2496a4f3942f1d59b330846bc66700012e0c4ceb9e7960a34`。
- **PM 桥接功耗 38793273** 结束于 2 分 28 秒，退出 0。保持 300 MHz 约束，160 µm 方形布局完成后提取，setup/hold **+1.220930 ns／+8.55022 ps**，详细布线 DRC 报告为空。1,664 字节真实数据页的配对增量 **0.631–0.663 nJ/页**，352 字节短页 **0.628–0.727 nJ/页**。这是 `native_pm_image_stream` 的边界活动传播估计。母控／局控 PM 阵列以及实际部署拓扑需要另行绑定。清单 SHA-256 `63e9b993247db0892b6c836b64ee22c8c28326bd6b9e0ddce6ab16b798e3dc95`。
- **SRAM 参考归属**。使用既有 P SRAM 的 512-bit 读与 128-bit 写增量系数，仅匹配拍宽的覆盖项为短 Prefill **15.228 µJ/窗**、首 token **43.108 µJ/窗**、稳态 Decode **43.171 µJ/窗**。其余读拍及宽写、各站点实际物理、空闲及漏电仍需补齐。每个 Decode 窗口的 56 次 U 残差包含 28,672 次 128-bit 读和 14,336 次 128-bit 写，已包含在 SRAM 窗口计数。结果 `covered-sram/estimate.json`，SHA-256 `f5bf51e5907f5536a716f32c0095d67742e10fc2d142c13801b1029cbf8d383f`。
- **M 产品回归 38792112** 结束于 20 分 59 秒，退出 0。相同冻结 C639 指令及 DDR 输入下，两模式 QKV、DDR 事务、提交 KV 和激活逐字对账通过。功能版和物理版源文件的差异只有 `ifndef SYNTHESIS` 的 28 行权重活动监视。结果清单 SHA-256 `2949c89ed2d4feaea6a309b3fe73468fe60e9681ea0a2d957c42b37d885ac252`。该候选物理签核仍在运行。
- **读侧准备 38793408** 结束于 49 秒，退出 0。以两项作业的 Yosys canonical RTLIL 声明绑定完整六窗。共享 DMA 59 端口、13,154 bit，阶段包装 117 端口、26,307 bit。两套分别导出六窗共 12 份独立 `dut` VCD，严格核验位宽、有效值和 8,192 周期时钟。清单 SHA-256 `57260f689cd1b22c0f16612d14195f72258a80cfb70306e3e041eb5f7b6a6496`。

## 作业回执和恢复入口

所有作业为 `v6_384` 和 `UNLIMITED`，命令统一前缀为 `sbatch --parsable --time=0`，每个提交目录的日志为 `slurm-<作业号>.log`。

| 作业 | 提交目录／核数／节点 | 命令（统一前缀之后） | 结果目录 |
| --- | --- | --- | --- |
| 38792112 M 产品回归 | `m-product/`／12／`m3ca1101` | `--job-name=mdt-280mproduct run_bscc_t6_c639_wide.sbatch m-exec` | `wide-38792112/replay-38792112/` |
| 38792357 M 300 MHz 物理 | `m-physical-exec/`／12／`m3ca0103` | `run_bscc_t6_m_exec_physical.sbatch` | `physical-38792357/` |
| 38792114 共享写侧物理 | `write-span/`／12／`m3ca1601` | `--job-name=mdt-280writespan run_bscc_t6_dma_physical.sbatch write-span` | `physical-38792114/` |
| 38792400 写侧回放 | `write-span-replay/`／8／`m3ca0103` | `run_bscc_t6_qwen3_write_span.sbatch wave` | `span-38792400/` |
| 38792563 写侧功耗 | `write-span-replay/`／8／查看作业快照 | `--job-name=mdt-280spanpower run_bscc_t6_qwen3_write_span.sbatch power 38792400 38792114` | `span-38792563/` |
| 38792815 片内活动 | `component-checks/`／12／`m3ca0208` | `run_bscc_t6_qwen3_component_checks.sbatch` | `check-38792815/` |
| 38793273 PM 桥接功耗 | `pm-bridge-power/`／8／`m3ca0606` | `run_bscc_t6_qwen3_pm_power.sbatch 38792815` | `pm-38793273/` |
| 38793408 读侧 VCD | `read-port-preflight/`／4／`m3ca0805` | `run_bscc_t6_c639_read_stage.sbatch` | `stage-38793408/` |

原 M 作业 38792113 因默认的推断存储尺寸限制退出。复跑允许原有的 36,864-bit 权重寄存器阵列。写侧回放在修正夹具的布尔位宽判断后通过。功耗首轮的层级名和窗口末时间分别在 38792401 和 38792504 暴露，修正后通过 12 份标注。PM 38793043 在 320 µm 布局的 CTS 阶段触及 hold 缓冲上限，160 µm 复跑通过。

```bash
cd ~/LLMHardware/zenanyan/issue-280-bscc-t6-01
jobs=38769386,38769388,38792357
squeue -j "$jobs" -o '%i|%j|%T|%M|%N|%C|%l|%R'
sacct -X -j "$jobs" -o JobID,JobName,State,ExitCode,Elapsed,NodeList,Timelimit
tail -n 15 physical/physical-38769386/flow.log phase/physical-38769388/flow.log m-physical-exec/physical-38792357/flow.log
(cd write-span-replay/span-38792563 && sha256sum -c results.sha256)
(cd pm-bridge-power/pm-38793273 && sha256sum -c results.sha256)
(cd read-port-preflight/stage-38793408 && sha256sum -c results.sha256)
(cd m-product/wide-38792112/replay-38792112 && sha256sum -c wide-results.sha256)
```

22:55:52 查得 38769386 与 38769388 运行约 6 小时 13 分，仍在 `SHARE`，没有可用于推算完成时间的映射/布线里程碑。M 候选 38792357 已运行约 21 分钟，处于 ABC 映射入口，尚无映射后 STA。预计按照小时级规划，以映射结束和布局进度重估剩余时长。

Melodydt 后续验收两个读侧最终网表、SDC、SPEF、STA 和 DRC，调用 12 份 VCD 完成门级功耗标定，并给共享逻辑去重。读回 M 候选 300 MHz setup/hold 和 DRC，以其闭合版继续活动标定。补齐真实写侧数据敏感性、SRAM 宽写、PM 阵列、U 算术、控制、互连和时钟后，再出短 Prefill、首 token、稳态 Decode 的 W 和 mJ/token。

规则 rayggxia-project-collab 1.0.0。项目管理检查、Python AST、脚本语法、Slurm 终态和短任务工件散列已查验。#280 保持进行中，#281 草稿待审查，独立审查人待指定。登记 PR #5 待合并。看板条目待有权限维护者核验。
