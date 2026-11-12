# Melodydt 的进度

## 2026-11-12 19:17（Asia/Shanghai，UTC+08:00）

- 任务与负责人：[Issue #261](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/261)，Melodydt。
- 已完成：从 PR #251 的 `9abd46f5cbb4534bcfc614571ccd6d402ad11882` 创建 `task/261-llm-asic-benchmarks`，整理 2B–4B 模型的公开 ASIC/NPU 解码吞吐和测试条件。见[调研报告](../../docs/experiments/issue-261-llm-asic-benchmarks.md)。
- 交付：[PR #262](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/262)，基分支 `task/250-w8a16-base-contract`，待独立审查。本地管理参考副本无 Git 元数据。远端文件由 Melodydt 的 GitHub 连接提交。
- 验证：在本地参考副本执行 `python -X utf8 scripts/check_project.py` 通过。文档表列、22 个 HTTPS 引用格式、两处换算、行尾空白通过；核查论文和厂商数据。未启动服务器仿真或板测。
- 下一步：审查来源、计时阶段、硅片与仿真证据及图读数。用于同条件性能验收前，仍需同模型、量化、带宽和 512 输入/128 输出的证据。
- 阻塞与待同步：项目登记 PR #5 待合并。当前没有可用 Projects 条目和字段工具，适用看板待核验、同步待执行，由具权限维护者处理。恢复入口见调研报告的协作交接。
