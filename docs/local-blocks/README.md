# 局部 Block 图册与重建

正式入口：[设计宗旨](../LOCAL_BLOCK_DESIGN.md)、[七宏流程](SEVEN_MACRO_MODEL_FLOWS.md)、[组合 Block 流程](COMPOSITE_MODEL_FLOWS.md)、[来源/数值边界](SOURCES_AND_GAPS.md)。任务 [#175](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/175)。

`diagrams/*.mmd` 是可编辑源；`assets/*.svg` 是已渲染的独立矢量图，不依赖 GitHub Mermaid 插件。共13张：五个模型/子层七宏图、对应五个组合图、两张共用密集 FFN 图及一张五种 Block 结构图。所有七宏图中的运算名是调用，不是物理实例；组合图才使用同一候选实例池。

## 构建环境与命令

本轮使用 Mermaid **11.4.1**、Playwright/Node 和无头 Chrome；实际版本与 Mermaid 文件 SHA-256 见 [manifest.json](manifest.json) 的 renderer 字段。本轮生成没有引入 npm/锁文件到项目，没有安装系统软件。需要 Playwright 的 Node 环境，并单独取得公开的官方发行文件 `https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js`；它是构建依赖，不是图内容的来源。

从仓库根目录运行，路径替换为本机实际位置：

```powershell
# NODE_PATH 只在 Playwright 不在当前 Node 默认模块路径时需要
$env:NODE_PATH = '<已有 Playwright 的 node_modules 目录>'
node docs/local-blocks/render_diagrams.cjs --mermaid '<mermaid-11.4.1.min.js绝对路径>' --browser '<Chrome或兼容Chromium绝对路径>' --screenshots '<仓库外临时截图目录>'
python -X utf8 -B scripts/check_project.py
python -X utf8 -B work/YUZE-LU/175/validate_docs.py
git diff --check
```

渲染器逐图调用 Mermaid parse/render，检查非空节点标签、SVG尺寸、纯 SVG 文本（无 foreignObject），可输出 PNG 供目视检查。截图留在任务临时目录，仓库交付 SVG 和小型渲染回执。图源修改后需重新渲染、查看和更新 manifest 的对应摘要；不能让旧 SVG 冒充新图结果。浏览器/字体版本不同可能导致字形、布局或 SVG 字节改变，记录新版本并审查差异。

`validate_docs.py` 只检查本轮文档的本地文件链接、图源/SVG配对和 manifest 摘要/固定输入 blob，不访问网络、不修改项目、不代替 RTL/数值/P&R。实际验证记录见[任务回执](../../work/YUZE-LU/175/VALIDATION.md)。

来源 SHA-256 对应固定 Git blob 原字节；工作树比对和文本产物摘要只将 CRLF 规范为 LF，以兼容 Windows checkout，不做其他字节替换。manifest 明确记录这个规则；因此不会把本机换行差异误报成来源变化，也不会掩盖内容改动。
