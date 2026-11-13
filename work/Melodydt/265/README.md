# Issue #265 整机评估运行清单

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
