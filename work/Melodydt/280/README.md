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

## 剩余步骤

1. 固定同一三 P 底座及 FFN Mid 的 DDR 路径，测 P0 调度对照和三 P 并行，并核对两种调度的数值和状态。
2. 标定 C380 ATT1、C639 三 P FFN、512-bit 数据 SRAM／PM、母控／局控、DMA、互连和时钟。核对 512-bit 宽写与物理 bank 实现，并对门级活动设留出窗口。
3. 用 Granite 的专家并发与 Phi、Falcon 的 V 读取对照复核归因，再扩到七模型。每完成一模型归档并汇报两阶段速度、DDR mJ/token、平均 W 和片上覆盖，Qwen2.5-3B 作为独立同口径参考。
4. 所有分项覆盖齐备后汇总全系统 mJ/token 和误差。PHY、板级 I/O 与终端能耗按证据单列。

规则版本 `rayggxia-project-collab` 1.0.0。项目管理结构检查和本地器件回归通过。登记 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 待合并。当前项目缺 `config/board.json`，看板仍待具权限维护者核验。
