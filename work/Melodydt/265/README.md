# Issue #265 整机评估运行清单

[Issue #265](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/265) 的负责人为 Melodydt。目录保存第一步使用的输入、平台清单及提交前检查。恢复顺序、来源和待补证据见[运行交接](../../../docs/handoffs/2026-11-13-issue-265-input-freeze.md)。

`run-manifest.json` 中已知散列来自固定上游回执或索引。运行环境、部署文件和图文件的待核实字段用 `null` 表示。旧基线与 #250 候选使用各自的硬件、工具和部署字段。

```bash
python3 -B work/Melodydt/265/preflight.py --profile legacy
python3 -B work/Melodydt/265/preflight.py --profile candidate_250
```

退出码 0 表示已执行预检并通过，1 表示工件或清单不符，2 表示还缺提交所需证据。预检只读取文件和复算 SHA-256。整机数值与事件验收由后续独立检查执行。
