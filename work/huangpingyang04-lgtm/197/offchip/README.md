# Issue #197 SystemC 外存端点回执

[任务](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/197) · [PR #198](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/198) · [接口与结果](../../../../docs/experiments/issue-197-systemc-offchip.md)

- 2026-11-06，Asia/Shanghai，执行人 `huangpingyang04-lgtm`。
- 正式目录 `/public/home/yuzelu/PingyangHuang/issue-197-offchip-CZAeok0o`。源码来自 #154 `5bc9d4b58ca46101ec4c377de0fc5700ae06539a` 的冻结归档；模型输入和冻结输出来自 `/public/home/yuzelu/PingyangHuang/issue-197-long-gzQzpiwn`，原计算作业 98386。
- 构建 `98689`、Qwen3.5 试跑 `98690` 已完成。首次构建 98685 发现 Windows 归档的 CRLF 与 Git 原对象的 LF 不同，试跑前在新目录仅规范化副本并核对原对象后成功。首次日志保留在 `/public/home/yuzelu/PingyangHuang/issue-197-offchip-u0fS2dZT`。
- 全序列七模型数组 `98704` 已完成，按 `phi, gemma, qwen3, qwen35, falcon, qwen25, granite` 索引。原始日志与二进制保存在对应服务器目录。

[源输入摘要](upload.sha256) · [构建产物摘要](build.sha256) · [工具版本](tools.txt) · [试跑终态](pilot-jobs.psv) · [试跑分类流量](pilot-traffic.csv) · [试跑数值与分类核验](pilot-verified.json) · [试跑文件摘要](pilot-outputs.sha256)

- 汇总作业 `98729` 完成，读取所有模型的输入/输出摘要，逐模型校验已验证回执与原始 CSV、hidden、logits 的 SHA-256，轻量结果包含原路径与每分片终态。实际环境为 GCC 8.5.0、CMake 3.26.5 和 SystemC 3.0.1-Accellera。

[完整结果和分阶段流量](offchip-results.json) · [结果摘要](offchip-results.sha256) · [汇总器输入摘要](collect-upload.sha256) · [汇总终态](collect-job.psv)
