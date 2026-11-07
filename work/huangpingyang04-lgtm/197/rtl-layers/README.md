# Issue #197 两层 RTL 联调回执

2026-11-07，Asia/Shanghai。执行人 `huangpingyang04-lgtm`。项目 `llm-hardware-design`。[Issue #197](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/197) · [PR #198](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/198)

成功作业目录 `/public/home/yuzelu/PingyangHuang/issue-197-rtl-layer-nXNzg8B5`。构建 99624、执行 99627、输入和输出核验 99629 均完成。源码和宏库位于 `source/`、`rtl/`、`obj/`，完整输出分别在 `run-systemc/` 与 `run-native/`。原始层输出二进制留在服务器，SHA 收录于结果及各输出清单。

[层级结果](../../../../docs/experiments/issue-197-qwen-rtl-layer-dma.md) · [运行入口](../../../../project/experiments/qwen_layer_dma/README.md) · [轻量结果](layer-results.json) · [结果 SHA-256](layer-results.sha256) · [Slurm 终态](jobs.psv) · [模型输入核验](input-verification.log)

## 源与输入绑定

- 算术和 R 源采用本分支 `d112da17b72e90d3489dfddaf765ca861450b4a4` 的原字节。DMA 为 #182 `24e20d13a71cf65f721a182451308f1ad01ebaec`，R 既有诊断配置来自 #168 `4f1a383049de5efa472f020e352c86be8c308614`。R1024 的参数比较额外保留第 63/126 行的精确位宽诊断配置，原 RTL 保持一致。
- 输入采用前轮 Qwen3.5 冻结检查点和 24 位置 hidden。导出前两个位置的第 0/3 层输入与期望结果，共八个 2,560 维张量。层输入 SHA 及全部生成源位于 `generated-inputs.json`；模型原文件由原长序列清单逐个校验。
- 工具为 Verilator 5.042、SystemC 3.0.1-Accellera，编译容器为项目既有 ORFS 26Q1。所有宏以断言开启模式编译，测试 C++ 保持 `-Wall -Wextra -Werror`。第三方 Verilator 头作为系统头，运行库复用其原生成库。SystemC 使用其提供的旧 API 兼容宏。

[上传源摘要](upload.sha256) · [原生 RTL 逐文件来源](rtl-source-manifest.json) · [生成代码及层输入摘要](generated-inputs.json) · [二进制摘要](build.sha256) · [输入/输出再核验](audit-results.sha256)

## 退休计数与数值

[原生 DMA 累计计数](native/rtl-memory.csv)和[逻辑传输计数](native/layer-traffic.csv)按层边界保存，同布局 [SystemC 计数](systemc/layer-traffic.csv)完全一致。M/N/E/G/R 每个有值响应与参考引擎比较，实际响应继续参与后续计算。完整四层边界二进制在本地实收后也通过验证器；少记一个 R 重载字的负控制被拒绝。

[RTL 运行回执](native/systemc_receipt.json) · [RTL 日志](native/inference.log) · [SystemC 回执](systemc/systemc_receipt.json) · [SystemC 日志](systemc/inference.log) · [输出摘要](native/outputs.sha256)

## 保留的构建迭代

| 作业 | 原目录 | 修复内容 |
| --- | --- | --- |
| 99618 | `/public/home/yuzelu/PingyangHuang/issue-197-rtl-layer-OTXpco3o` | incorrect source subdirectory |
| 99619 | `/public/home/yuzelu/PingyangHuang/issue-197-rtl-layer-OihzljAU` | R1024 parameter width diagnostics |
| 99620 | `/public/home/yuzelu/PingyangHuang/issue-197-rtl-layer-mXEsD7vJ` | SystemC old API compatibility macro needed with container compiler |
| 99623 | `/public/home/yuzelu/PingyangHuang/issue-197-rtl-layer-WJ3qLO8i` | native header include path and Verilator runtime linking |

每次迭代使用新的独立目录，失败日志均保留。最终结果以成功作业和本目录的摘要为准。统一 RTL 母控/局控、全模型时钟和器件校准范围见正式报告。管理中心登记沿用 PR #5 pending，仓库缺 `config/board.json`，Projects 核验与同步待维护者处理，Issue 保持待独立审查。
