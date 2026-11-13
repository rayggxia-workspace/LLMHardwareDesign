# Issue #265 整机评估运行清单

## 快速周期评估

[Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 当前研究指令与拓扑驱动的快速周期估算。方案、输入及验证顺序见[决策记录](../../../docs/decisions/0265-instruction-driven-cycle-estimation.md)。本目录保留前期输入冻结和参考环境证据。

第一步的[片上模型和验证入口](../../../project/experiments/instruction_cycle/README.md)包含发射顺序、冲突、仲裁和背压的实现。短程 RTL [107488 回执](onchip-rtl-107488.json)及双 U_64 [COPY 对照输入](copy-rtl-input.json)记录两个已经逐拍核验的范围。

实际镜像到退休的 A2 联合验证见 [107535 回执](a2-rtl-107535.json)和[模型与复跑命令](../../../project/experiments/instruction_cycle/README.md#a2-母控局控与片上算子联合验证)。

双 U_64 的两路局控、SRAM 和跨 Block 链路逐拍验证见 [107643 回执](dual-u-rtl-107643.json)和[复跑命令](../../../project/experiments/instruction_cycle/README.md#双-u_64-从-start-到-result)。

有限队列 DMA、实时 DRAMsim3 读桥及独立 RTL 验证见 [DMA／DDR 回执](dma-ddr-receipts.json)和[复跑命令](../../../project/experiments/instruction_cycle/README.md#有限-dma-队列与实时-dramsim3)。

统一队列候选的 DDR 写数据结束、跨时钟回包和 FENCE 见 [107731 回执](dram-write-cdc-107731.json)及[验证说明](../../../project/experiments/instruction_cycle/README.md#ddr-写数据结束与跨时钟采样)。

`audit_fast_cycle_inputs.py` 在 Python 3.7.0 上运行，通过两个历史作业的归档恢复三 P FFN 控制顺序，并对照原有 RTL 日志。原始归档按 [#251 索引](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/250/native-services/ffnnative/index.json) 从项目服务器只读获取。两个作业归档登记的源提交均为 `ab7611d43e4c007cc966ab5e61903118d33fcb4a`。将其命名为 `<job>-receipts.tar.gz`。`fast-cycle-inputs.local/` 为本地未提交缓存。

| 作业 | 服务器相对 `/public/home/yuzelu/project-circuit/` 的位置 | SHA-256 |
| --- | --- | --- |
| 102603 | `issue250-ffnnative-20261111-21/receipts.tar.gz` | `f1ef4555cb5dcbac48f79d65c8b5ebde4d1b59e44cae55af42b38dabae777b8f` |
| 102604 | `issue250-ffnnative-20261111-20/receipts.tar.gz` | `bc072788c2648b6008c0c6c18000ec33df8147ed0ae38c545ad6f86ca1920712` |

```bash
python -B work/Melodydt/265/audit_fast_cycle_inputs.py --receipts-dir work/Melodydt/265/fast-cycle-inputs.local --output work/Melodydt/265/fast-cycle-input-audit.json
```

结果 [fast-cycle-input-audit.json](fast-cycle-input-audit.json) 的 SHA-256 为 `b11ea3d61c2427859eed47b69882f3bf09073dac3e3aab1a48418ba117c570a7`，审计脚本的 SHA-256 为 `87b3cb941eb91b914ed9815a21fddff9fb150e62a18de4038167f4db96dd5aa0`。审计覆盖固定 seed 25001 的 12 份运行日志及两份控制镜像和描述符包。`observed_rtl_profiles` 记录历史 RTL 的阶段周期及计数。

## 运行输入冻结

[Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 的负责人为 Melodydt。目录保存第一步使用的输入、平台清单及提交前检查。恢复顺序、来源和待补证据见[运行交接](../../../docs/handoffs/2026-11-13-issue-265-input-freeze.md)。

`run-manifest.json` 中已知散列来自固定上游回执或索引。运行环境、部署文件和图文件的待核实字段用 `null` 表示。旧基线与 #250 候选使用各自的硬件、工具和部署字段。

```bash
python3 -B work/Melodydt/265/preflight.py --profile legacy
python3 -B work/Melodydt/265/preflight.py --profile candidate_250
```

退出码 0 表示已执行预检并通过，1 表示工件或清单不符，2 表示还缺提交所需证据。预检只读取文件和复算 SHA-256。整机数值与事件验收由后续独立检查执行。

## 参考环境验证

`reference_smoke.py` 接受分别核验的 checkpoint、参考输入和 ONNX 目录。它验证九份模型文件、六份参考输入及回执、四份 ONNX，然后以冻结的两个 P512 用例各运行一次完整 FP32 prefill 和一次缓存 decode。前两个 token 与冻结参考对账，缓存解码和独立全前缀 logits 使用历史参考容差。脚本也执行实际 P512 ONNX 图的词表输出，保留与 FP32 参考的偏差。该测试的范围为参考环境与数值冒烟。

在 `/public/home/yuzelu/Melodydt/runs/issue-265/reference-smoke-<attempt>/` 内放置同版本的 `reference_smoke.py`、`reference_smoke.sbatch`、`preflight.py`、`run-manifest.json`，生成 LF 格式的 `source.sha256` 并读回验证。使用经校验的任务 checkpoint 和容器内 Python 环境。

```bash
sha256sum reference_smoke.py reference_smoke.sbatch preflight.py run-manifest.json > source.sha256
bash -n reference_smoke.sbatch
sbatch --parsable --output=slurm-%j.out reference_smoke.sbatch "$CHECKPOINT" "$REFERENCE_ENV"
```

提交前完整部署预检的 `--manifest` 参数可填写运行绑定，冻结字段以本目录的版本为准。控制镜像的 `source` 使用上游约定的规范化 JSON 散列。为其在 `topology.json` 的 `program_target.source_artifacts` 登记 IR、硬件与计划的相对路径，并把原始文件的散列纳入 `build-inputs.sha256`。
