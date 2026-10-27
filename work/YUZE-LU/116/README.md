# Issue #116：模型分析目录归档

- 任务：[Issue #116](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/116)，实际账号/负责人 YUZE-LU。
- 规则：rayggxia-project-collab 1.0.0；分支 `task/116-model-analysis-docs`，基线 `2113afef4afc1f16391e0ed929158bdfc3f70b94`。
- 正式入口：[docs/model-analysis](../../../docs/model-analysis/README.md)。
- 范围：导入已生成的精简/完整计算图资料，迁移 PR #115 的分析报告，补索引、旧路径跳转与必要导航。
- 原实验未重跑，原独立目录和服务器 ONNX 保留；旧手工图与校正版字符图的差异明确记录。

## 检查与证据

- `archive-manifest.json`：183 份字节相同的导入文件摘要、Issue #114 历史辅助文件摘要、分析报告迁移规则。
- `archive_docs.py`：本轮已执行的一次性导入脚本；目标存在时拒绝再次导入，不覆盖已有归档。
- `validate_archive.py`：检查报告迁移只改变相对链接、历史记录不变、导入 SHA、Markdown/HTML静态和图册动态路径、40个内嵌SVG以及十组成功回执。
- `validation.json`：本次实际检查结果；管理结构检查与 `git diff --check` 另行执行。

实际结果：183 份导入文件 SHA 一致、Issue #114 的 3 份历史辅助文件不变、196 个本地引用存在、40 个内嵌 SVG 可解析、10 组成功 receipt 与轻量产物摘要匹配，报告正文除相对链接外不变；管理结构检查通过；新增说明文档的差分空白检查通过。graphs 快照保留原始换行与空白，以原始 SHA-256 一致性验收；其 `.gitattributes` 禁止自动换行转换。

## 提交回执

- 项目：rayggxia-workspace/LLMHardwareDesign；project_id=llm-hardware-design。
- 更新时间：2026-10-27 14:25 CST；用户已明确授权提交到 main。本轮通过现有任务分支、PR、实际 CI 和正常合并交付；当前正在准备提交，最终 PR/commit/合并状态以 Issue #116 在线读回回执为准。
- 既有分析报告由 PR #115 合并，本次归档不改变 Issue #114 的完成事实或任何来源实验资格。
- 项目登记：本次已读回 management-hub PR #5 仍 open/未合并，pending；不修改其他项目登记。
- 看板：未配置 `config/board.json`，当前连接器无 Projects 条目工具；条目 unverified、同步 pending，管理员待指定。不扩大权限。
- 下一步：同步最新 main 并保留其他任务文档，提交该任务分支并创建 PR，检查 CI 后按本次用户明确授权正常合并，再读回 main 内容。没有代替其他人提交独立审查，不绕过任何服务器保护；不合并其他 PR，不修改实验或服务器任务。
