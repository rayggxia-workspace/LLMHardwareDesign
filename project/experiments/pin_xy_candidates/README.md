# pin XY 候选分析脚本

[Issue #119](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/119) · [中文总结/图表](../../../docs/experiments/issue-119-pin-xy-candidates.md)

这些脚本来自已完成的独立分析，保留解析、分束、候选选点、矩形风险筛查和 matplotlib 绘图过程（入库文本统一 LF 并清理行末空白；PNG/压缩 CSV 保持原字节，SVG 仅做空白规范化）。它们不写回 ODB、不重硬化、不执行 P&R，也不改 pin 的层/网络/方向。`build_report.py` 生成原离线交互报告；仓库报告是其图表/数据相同、外链图片和 CSV 的摘要版。

## 仓库交付验证

```sh
python scripts/check_project.py
python project/experiments/pin_xy_candidates/validate_repository.py
```

后者仅用标准库，检查源 JSON 与全部 A/B/C 坐标、pin 名/层/方向/功能/网络/矩形尺寸/边界、常量位保留、PG、图表链接及实际字节 SHA。它不能替代 DRC。

## 在独立目录完整重画

原分析 Python 3.13.5、numpy 2.3.5、pandas 2.3.3、scipy 1.17.1、matplotlib 3.10.7；字体使用本机 Microsoft YaHei，其他系统需配置可用中文字体。完整版本记录在报告 data/tool_receipt.json。

1. 创建独立任务目录，把本目录的 `parse_report.py`、`analyze_layout.py`、`build_report.py` 复制进去；所有输出默认在脚本旁。
2. 运行 `python parse_report.py "仓库中的原始参考 HTML" --out .`。它程序化提取 JSON、图片、元数据，不打印 base64；原 HTML 不改。
3. 按 [source-index.json](../../../docs/experiments/issue-119-pin-xy/data/source-index.json) 恢复只读导出表到 `physical/`。例如远程任务的 `data/act/` 对应本地 `physical/act/`，不得把输入目录当输出写入。先核对各压缩文件的 SHA。
4. 将报告 data 中的 tool_receipt.json 等历史回执和说明复制到独立目录，或明确替换为本次真实来源回执，不伪填版本。
5. 运行 `python analyze_layout.py`。读取原 pin 数据/元数据、physical/ 快照，生成 A/B/C CSV、PNG、SVG、指标和完整交互 HTML。主脚本不联网。

完整重画需要获准读取远程快照；本仓库不含大体积实际布线矩形表，因此仅凭精简仓库不能声称重现了全部物理筛查。源 ODB/LEF 的精确位置与摘要在原元数据中。

`export_odb.tcl` 和 `export_anchors.tcl` 是只读 OpenROAD Tcl 导出器，`export.sh` / `anchors.sh` 为原作业脚本，保留当时任务路径与环境。若重新使用服务器，先读根 AGENTS.md、docs/REMOTE_RULES.md 和用户个人目录规则，并将脚本改到**全新获授权任务目录**；不要直接再次运行历史 shell。缓存/临时文件/日志也必须进入新目录。首次分析的有效单核导出作业为 91824/91825；本次 PR 发布未运行新的服务器任务。

## 解释边界

B 的 1.12 μm 与 C 的 2.24 μm 为候选 pitch，不是全局轨道/DRC 合法性结论。0.56 μm 宏/束间余量是人为设计假设。通孔目标未知时按实际经过层分别分析 M6/M8/M10，未把所有 pin 引到 M11/M12。GEMM 高 256 数据位和高 32 strobe 位恒零，B/C 原位保留；活跃数据与 strobe 按字节关联。

最近端点 L1、XY 移动、真实路由总线长与提取 RC 是不同量。本脚本只输出前两类几何代理以及已有矩形风险；完整接入/RC/STA/DRC 仍待实际验证。
