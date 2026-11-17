# 七模型短程能耗试点

2026-11-15（Asia/Shanghai）。项目 `llm-hardware-design`，负责人 Melodydt。任务分支 `task/280-seven-model-energy` 从七模型速度分支的 `fbff1bd0e455739f28d9b7dd00b97216fe7bb847` 建立，速度证据提交为 `d8f775b661c511d6450d5cbe63f4519563114895`。 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280) · [速度交接](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/f1e61ca7155b070bd1e5364778da8bdd499a7331/docs/handoffs/2026-11-15-issue-274-speed-evaluation.md)

## 已完成

- 固定短 Prefill 从仿真起点到第二输入位置末层结束，按两个输入 token 归一。Decode 同时抓取首 token 及两次词表退休之间的能量，后者按一个输出 token 归一。沿用两路 630 ps DDR 及 3,334 ps 核周期。末层采样位置与原速度计时一致。
- 新探针读取已经归档的 epoch 计数与当前 epoch 计数，保存两通道的实际命令、完成计数、各 rank 驻留时长和对应器件能量。采样过程保持时钟、队列、统计 epoch 和刷新状态继续运行。汇总器对照原生终态 `dramsim3.json`，检查每个 rank 的时间闭合、分项与总量，并用 `tCK_ps × 10⁻¹⁵` 将 mW·tick 转成 J。 [DRAMsim3 能量与计数公式](https://github.com/umd-memsys/DRAMsim3/blob/29817593b3389f1337235d63cac515024ab8fd6e/src/simple_stats.cc#L391-L429)
- 本地用 g++ 14.2.0 和 Python 3.7.0，基于 DRAMsim3 `29817593b3389f1337235d63cac515024ab8fd6e` 与项目已归档的严格写回补丁构建探针。公开源码包 SHA-256 为 `32110a7fcaa2026e1557acc9f29ca82b1871929baf4d004881899b94255627ac`。混合读写测试运行两个独立通道、640 个回调。开启前后的回调时刻、顺序与原生终态统计一致，覆盖刷新和跨 epoch。该测试是器件统计回归，七模型的能耗仍待测。
- 本地 `check_ddr_probe.py` 第二窗合计 ACT 324、PRE 328、RD 214、WR 106、REF 6，器件模型积分为 23.453950464 µJ。两个输入位置的模拟边界也经过汇总器回归。源代码及生成 Python 语法均通过。输出留本地 `tmp/energy-280-smoke-003/candidate/`，Decode／Prefill 回归文件的 SHA-256 分别为 `4d484da69e0e1951cae575c6bf2afc4b69474dd297277e75064cbe89e1893ded`／`7cdc55b178c0be81748adca7623dc4a5c14db5fef7a1e7f550af20ae41181b41`。回归试验的退休标记来自夹具，功耗数字仅代表此混合读写序列。

## 服务器恢复入口

服务器 `yuzelu@10.129.166.172` 已恢复公钥登录。Qwen3 试点回放 116481 的两个模型步骤和 DDR 分窗对账均成功，独立 FP32 由补跑 116496 验收通过。 [本轮终态、分窗数值和散列](QWEN3_DDR_PILOT.md)

- Qwen3-0.6B 冻结回放目录为 `/public/home/yuzelu/Melodydt/runs/issue-274/three-p-full-01`，对照作业为短 Prefill `115618` 和 Decode `115619`。首先校验 `source.sha256`、`upstream.sha256` 和两个运行的 `output.sha256`。
- 构建源与桥接脚本按 #270 作业 113164 的冻结依赖读回。原桥的 SHA-256 为 `1e74820e1cbe48b447e29fd9f98f55c54b4bd4f3fb493b0f2d8e1317c3cd8c1b`，原 DDR 配置 SHA-256 为 `748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766`。本地回归采用独立器件配置和编译环境，服务器使用原依赖另行核验。 [冻结构建入口](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/ebd590def47d2da6b46f04a68931c1d47f11538e/work/Melodydt/270/ffn-weight-05/run_ffn_tlm.sbatch)
- 在本人 `/public/home/yuzelu/Melodydt/runs/issue-280/ddr-pilot-01` 建新目录。把核对过的 `fast_tlm_dram.cpp` 和 `fast_tlm_replay.py` 与 `qwen3_short.py`、`fast_qwen3_short.sbatch` 放入临时输入目录，用 `python3 -B stage_ddr_probe.py DRAM_SOURCE STAGED --replay FROZEN_INPUTS` 生成隔离副本，参数替换为实际核对过的路径。用原容器和原编译参数构建 `STAGED/dramsim3` 与 `STAGED/replay/fast_tlm_dram.cpp`，保存原/新源码和库的 SHA-256。运行目录从原冻结回放复制脚本文件，再应用四个生成文件并生成新 `source.sha256`，复用原 `upstream.sha256`。
- 编译和最小回归通过后，在新目录把 `MDT_280_DDR_LIBRARY` 指向新库绝对路径。按 `sbatch --parsable -p c96 -N1 -n2 -c12 -t 06:00:00 --job-name=mdt-280qwen3 -o slurm-%j.log --export=ALL,MDT_274_NATIVE_MATH=1,MDT_274_THREE_P=1,MDT_274_TRACE_LAYERS=1 fast_qwen3_short.sbatch qwen3 prefill:4:tile128:combined decode-live:4:tile128:combined` 提交。实际提交后记录作业号、状态、节点和目录。产物在 `run-<作业号>/{prefill-w4-tile128-pr272-combined,decode-live-w4-tile128-pr272-combined}`。
- 每阶段运行 `python3 -B ddr_window_energy.py CANDIDATE --baseline FROZEN_BASELINE`，核对时间、残差、logits、退休、逐层轨迹及请求。随后用 #274 的 `audit_three_p.py` 独立核验 FP32、跨步状态和三路供数。作业和审计通过后发布 DDR 芯片估算及其适用边界。

### 一次提交完成试点与审计

SSH 恢复后，把任务分支同一提交上的 `run_qwen3_ddr_pilot.py`、`stage_ddr_probe.py`、`ddr_snapshot.inc`、`ddr_window_energy.py` 传到本人 `/public/home/yuzelu/Melodydt/runs/issue-280/ddr-pilot-01`，将实际来源的完整 commit 写到 `source-commit.txt`。在该目录提交。

```bash
sha256sum source-commit.txt run_qwen3_ddr_pilot.py stage_ddr_probe.py ddr_snapshot.inc ddr_window_energy.py > bundle.sha256
sbatch --parsable run_qwen3_ddr_pilot.py
```

脚本默认 c96 单节点，两个任务各 12 核。先核验归档、DDR 配置与旧桥的 SHA-256，再构建独立库，然后以相同回放参数运行 Qwen3 两阶段。两阶段都必须通过同速度基线的严格对账，FP32 独立验收沿用原容器。日志在 `slurm-<JOB>.log`，两阶段能耗、验收和散列保存在 `pilot-<JOB>/`。

```bash
squeue -j "$JOB"
sacct -X -j "$JOB" --format=JobID,State,ExitCode,Partition,AllocCPUS,NodeList,Elapsed
tail -n 20 "slurm-$JOB.log"
sha256sum -c "pilot-$JOB/pilot-results.sha256"
cat "pilot-$JOB/ddr-prefill.json" "pilot-$JOB/ddr-decode.json"
```

本地已验证调度入口的参数拼装、两组冻结基线路径、容器内 FP32 审计和摘要不符时终止。Slurm、服务器编译及真实模型回放待完成。

## 2026-11-16 Qwen3 三窗功耗进展（Asia/Shanghai）

- 非 DMA 已覆盖小计为双通道 DDR 芯片与 300 MHz G32 FFN 活跃增量。短 Prefill 114.9417–114.9420 mJ/输入 token，首 token 332.7932–332.7934 mJ，两次退休间 332.8565–332.8567 mJ/输出 token。其他片上分项待按相同窗口对齐。 [口径、结果和复跑](../../../docs/handoffs/2026-11-16-issue-280-qwen3-non-dma-subtotal.md)
- Qwen3 作业 118132 已用 `--time=0` 提交并读回 `UNLIMITED`。15:24 仍按优先级排队，节点待分配。已从冻结快照归档三窗 DDR 器件完成计数。片上 DMA 的提交、接收、在途和等待由 118132 补采。 [计数、脚本验证和作业追踪](../../../docs/handoffs/2026-11-16-issue-280-qwen3-dma-windows.md)
- 117939 和 117729 已按指示取消，DMA 物理／功耗与 M 实际门级活动仍缺标定。117940 局控取指 hold 修复遇缓冲上限，117855 M ECO 最终等价检查异常退出。先回收并核对 118132 的三窗事务，再补 DMA 和其他片上分项。 [终态和日志散列](../../../docs/handoffs/2026-11-16-issue-280-qwen3-dma-windows.md)

## 2026-11-17 Qwen3 TLM 分项能耗 v1（Asia/Shanghai）

[结果 JSON](qwen3_tlm_power_v1.json) 按冻结 TLM 时间和分项标定积分，列出片上已覆盖、DDR 器件和读 DMA 动态敏感性。[计算脚本](qwen3_tlm_power_v1.py) 与完整输入、SHA-256、复算命令见[三窗回执](../../../docs/handoffs/2026-11-17-issue-280-qwen3-tlm-power-v1.md)。后续读 DMA 以综合网表、Liberty、300 MHz SDC 和匹配 VCD 做布局前估算。

## 持续更新的七模型功耗报告

[当前 PDF](../../../docs/experiments/seven-model-energy-evaluation.pdf) 汇总评估方案、三窗指标、分项覆盖、读 DMA 暂估和综合后直接估功耗。第 1.0 版仅收录 Qwen3-0.6B 结果。

每次发布一个新模型的功耗结果，或用合格的综合后标定替换已有代理值时，同一次提交都更新 PDF：

1. 保存该模型的可核验结果 JSON。沿用 [Qwen3 v1](qwen3_tlm_power_v1.json) 的三窗结构，记录输入、模型配置、专项优化、覆盖范围、工具版本和散列。
2. 更新 [报告索引](energy_report_models.json) 的版本、日期、模型状态、结果路径、SHA-256 和对应证据。数据页直接从 JSON 生成。
3. 从仓库根目录执行下面的命令，逐页渲染核对数值、版面与来源链接。使用同一个 PDF 路径提交，PR 保留各版历史。

```powershell
python work/Melodydt/280/build_energy_report.py --output docs/experiments/seven-model-energy-evaluation.pdf
```

生成器依赖 Python 和 ReportLab，默认使用 Windows 等线字体。其他环境可通过 `--regular-font` 与 `--bold-font` 指定支持简体中文的 TrueType 字体。

## 剩余步骤

1. 固定同一三 P 底座及 FFN Mid 的 DDR 路径，测 P0 调度对照和三 P 并行，并核对两种调度的数值和状态。
2. 标定 C380 ATT1、C639 三 P FFN、512-bit 数据 SRAM／PM、母控／局控、DMA、互连和时钟。核对 512-bit 宽写与物理 bank 实现，并对门级活动设留出窗口。
3. 用 Granite 的专家并发与 Phi、Falcon 的 V 读取对照复核归因，再扩到七模型。每完成一模型归档并汇报两阶段速度、DDR mJ/token、平均 W 和片上覆盖，Qwen2.5-3B 作为独立同口径参考。
4. 所有分项覆盖齐备后汇总全系统 mJ/token 和误差。PHY、板级 I/O 与终端能耗按证据单列。

规则版本 `rayggxia-project-collab` 1.0.0。项目管理结构检查和本地器件回归通过。登记 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待合并。当前项目缺 `config/board.json`，看板仍待具权限维护者核验。


## 2026-11-17 六模型 TLM 能耗扩测

按用户授权连续扩测 Llama、Granite、Phi、Gemma、Qwen3.5、Falcon。复用已验收的完整模型执行计划和真实历史，先迁移文件，计算节点核验全部传输 SHA-256，然后重放短 Prefill 与两步 Decode。新入口要求完整 result、logits、残差与逐层文件一致，并分别核验 DDR 和 SRAM 计数。Granite 嵌套激活、Gemma GELU、PM 实际页长和普通投影 M 忙时独立计数；缺少匹配标定的算子不能作为零能耗处理。

启动脚本 `run_six_model_energy.sbatch` 使用 v6_384、两个阶段各 12 核、`--time=0`。目录为 BSCC-T6 的 `~/LLMHardware/zenanyan/issue-280-bscc-t6-01/six-model-energy-01`。本次提交时 Llama 工件正在迁移，尚无新模型作业号或能耗结果。源版本与作业号以随后启动回执为准。每个模型三窗验收后更新同名 PDF。

验证：本地四份 Python AST、`python scripts/check_project.py` 已通过。业务回放尚未执行。#280 进行中，PR #281 草稿待独立审查；登记 PR #5 pending，任务分支 `config/board.json` 404，Projects 条目未核验、同步 pending。


## 六模型扩测入口

2026-11-17，Llama、Granite 已在 BSCC-T6 进入不限时回放，其余模型迁移中。使用冻结计划和逐文件验证，不重新访问检查点。结果输出必须与已验收全层回放一致后才做分项积分。[启动、失败记录、工件散列和完整后续步骤](../../../docs/handoffs/2026-11-17-issue-280-six-model-energy.md)。

## Granite 首份扩测能耗（2026-11-17）

回放 38820602、积分 38820947 均 COMPLETED 0:0。三窗结果见 [granite_tlm_power_v1.json](granite_tlm_power_v1.json)，复算输入在 [six-model-results/granite](six-model-results/granite)。源/结果 SHA 与本地复算字节一致；未匹配标定的 MoE 算术及控制仍为缺项。全部六模型输入已迁移，五个剩余模型运行；后续逐模型验收并维护同名 PDF。[作业、成功判据与命令](../../../docs/handoffs/2026-11-17-issue-280-six-model-energy.md)。
