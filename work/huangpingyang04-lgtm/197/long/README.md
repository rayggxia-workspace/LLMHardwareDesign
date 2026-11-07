# 七模型长度扩展服务器回执

2026-11-06，Asia/Shanghai。[Issue #197](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/197) · [PR #198](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/198) · [报告](../../../../docs/experiments/issue-197-long-systemc.md)

| Slurm 作业 | 目录和结果 |
| --- | --- |
| 98338（7 分片） | `/public/home/yuzelu/PingyangHuang/issue-197-long-gzQzpiwn`。每模型 `case-<model>/reference_logits.bin`、`reference_hidden.bin`、`export_receipt.json` 和 `reference-<model>.sha256`。各分片独立加载 FP32 权重并生成 12 个 token。 |
| 98385 | `/public/home/yuzelu/PingyangHuang/issue-197-long-build-oIOGNneh`。从固定 #154 源归档构建带逐步观察的 C/D 程序，两个原自测试通过。 |
| 98386（7 分片） | `/public/home/yuzelu/PingyangHuang/issue-197-long-gzQzpiwn`。每模型 `long-<model>/`，包含推理和验证日志、逐步观测、原始 flow、隐藏层和 logits、原数值门及输出 SHA-256。 |
| 98403 | 同上，`short-equivalence/`。Qwen3-0.6B 的旧 9 位置输出与活动一致。 |
| 98408 | 同上。逐一复核原始参考和 SystemC 原件 SHA-256，收集完整轻量结果。 |

[逐模型结果与参考对照](long-systemc-results.json) · [运行作业终态](long-jobs.psv) · [汇总作业终态](long-collect-job.psv) · [SHA-256](long-evidence.sha256)

98360 的首次构建在源锚点处停止，98372 在编译阶段被 `-Werror=misleading-indentation` 拒绝。两份失败目录和日志保留，第三次修正观察代码缩进后正常构建。七模型正式回放均使用 98385 的同一程序。
