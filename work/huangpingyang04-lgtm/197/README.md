# Issue #197 服务器回执

[Issue #197](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/197)。日期 2026-11-06，Asia/Shanghai。负责人及执行账号 `huangpingyang04-lgtm`。

| 作业 | 运行目录 | 证据入口 |
| --- | --- | --- |
| 98095 | `/public/home/yuzelu/PingyangHuang/issue-197-seven-bench-lu50wdHA` | `systemc-98095.log`、`cd-build/receipt.json`、`systemc-results/systemc-summary.json` |
| 98129 | 同上 | `projection-98129.log`、`projection-results/results.sha256`、各模型整数输入和周期回执 |
| 98131 | 同上 | `control-98131.log`、`control-results/receipt.json` |
| 98124 | `/public/home/yuzelu/PingyangHuang/issue-197-dma-Kg4UlTWh` | `dma-98124.log`、`dma-results/results.sha256`、九种扫描结果 |
| 98150 | `/public/home/yuzelu/PingyangHuang/issue-197-scprojection-GLr1VjpB` | `sc-projection-98150.log`、`sc-projection-results/results.sha256` |
| 98151 | 整模型主目录 | `summary-98151.log`、`seven-model-evidence.sha256` |

[轻量结果 JSON](seven-model-results.json)包含新跑的业务统计、输出/输入摘要、三组控制回归原始计数和九项 DMA 记录。 [作业终态](seven-model-jobs.psv)来自 `sacct -X`。汇总作业终态单列于 [summary-job.psv](summary-job.psv)。[结果 SHA-256](seven-model-evidence.sha256)由服务器汇总作业生成。源码归档和批处理上传清单同目录保存。 [复现入口](../../../project/experiments/seven_model_system_bench/README.md) · [中文报告](../../../docs/experiments/issue-197-seven-model-system-bench.md)

整模型的旧 FP32 数值门通过字节一致性复核。本次对冻结检查点输入逐文件重算 SHA-256，重跑完整 SystemC 程序与 C/D 后核对全部 hidden/logits 字节和 C/D 计数。每个模型重新生成逻辑轨迹并对账，保留原始激活、权重和模型目录。

## 重试记录

- 首次整模型脚本的 shebang 前有空行，`sbatch` 拒绝入队。移除空行后在新目录提交 98095。
- 98123 的 DMA 首次源清单缺 `block_feed_s_macro.sv`，Verilator 在编译前拒绝。在新任务目录补齐完整冻结源后重跑 98124。原失败日志保留在整模型目录的 `dma-results/build.log`。
- 98135 和 98141 的 SystemC 投影编译分别遇到新测试与冻结头文件的旧 `SC_HAS_PROCESS` 在 `-Werror` 下报弃用。新测试使用当前 API，编译开启 SystemC 提供的旧 API 兼容宏供冻结头文件使用，成功重跑 98150。两次失败记录留在各自任务目录。
- 首次汇总提交的组合依赖被 Slurm 拒绝。已完成作业逐一核对终态后，仅以运行中的 98095 为依赖，成功排队 98151。


## 外存访问复核

Slurm **98611** 在 c64/node1 用 1 核运行 48 秒，通过七模型全部 165 个位置的 C/D 计数对账。输入为作业 98386 的七个原目录 `/public/home/yuzelu/PingyangHuang/issue-197-long-gzQzpiwn/long-*` 和[冻结汇总](long/long-systemc-results.json)。每模型读取 `flow-events.jsonl`、`flow-values.csv`、`length-steps.csv` 和 `cd-payload.json` 并与原始清单核对摘要。

- 成功作业目录 `/public/home/yuzelu/PingyangHuang/issue-197-memory-wppZsZFb`，保留审计脚本、冻结汇总、结果和 `slurm-98611.log`。实际脚本上传 SHA-256 为 `533c523705b26ed275366c661339cca3cda57b5141959bd68fe9367b2f29bcad`。
- 98610 在 `/public/home/yuzelu/PingyangHuang/issue-197-memory-j0FU2xvQ` 保留首次对账失败。Gemma 的单元素独立尺度比统一尺度多占一个字，旧轨迹同记为 4 字节。98611 将此歧义限定在未分类项并对账实测字数，其余分类独立计算。

[审计 JSON](long/cd-traffic-audit.json) · [结果 SHA-256](long/cd-traffic-audit.sha256) · [Slurm 终态](long/cd-traffic-audit-jobs.psv) · [七模型能耗与接口覆盖](../../../docs/experiments/issue-197-seven-model-energy-estimate.md#外存访问核对)
