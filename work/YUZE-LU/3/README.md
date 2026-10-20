# 两份布线报告同步

任务：[Issue #3](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3)。正式成果位于 `ref-project/llm-routing/`，这里仅保存本任务辅助脚本及检查回执。

`sync_reports.py` 默认只读检查已打包报告的引用闭包、锚点、可见图片和清单 SHA-256，需要 Python 与 beautifulsoup4：

```powershell
python work/YUZE-LU/3/sync_reports.py
python scripts/check_project.py
git -c core.whitespace=cr-at-eol diff --cached --check
```

仅在用户明确要求再次更新时，使用 `--sync --source <包含两份正式 HTML 的目录>`。同步保留原便携路径映射，只复制报告引用的文件，删除包内不再引用的单个文件，不创建备份；不修改源报告，不触发物理工具。原始完整数据库与未引用的大体积物理证据不在上传范围。

引用附件逐字节保留源文件的 CRLF；暂存差异检查用 `cr-at-eol` 识别合法换行，仍检查行末空格。没有修改仓库配置。`validation.json` 记录本次实际检查。Projects 权限缺项见 `docs/handoffs/2026-10-20-issue-3-report-board.md`。
