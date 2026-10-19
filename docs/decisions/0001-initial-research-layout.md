# 0001：初期资料直接进入项目目录

- 日期：2026-10-19
- 状态：accepted
- 决策负责人：@YUZE-LU
- 关联 Issue：[初始化项目 #1](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)
- 替代记录：无

## 背景

项目起步资料包含研究定义、来源笔记和相互引用的布线分析结果。原始 README 是阅读导引，不适合作为新仓库唯一的项目首页。结果包的 HTML、图片和表格使用相对路径。

## 决策与原因

保留 `sources/`、`ref-project/llm-routing/` 和专题 `docs/` 的原有层次，将初版项目说明留在根目录；把原始 README 的全部技术要点整理为根目录 `研究资料导读.md`，由新 README 提供当前项目入口。`ref-project/` 固定为只读参考资料，不纳入后续维护。这样初期资料直接属于当前项目，原作者对研究重点和目录的说明也得以完整保留。

## 考虑过的其他方案

将全部文件放入 `legacy/` 会误示这些初期资料已失效；一次性重排所有结果文件会增加引用断裂和来源核对成本。

## 影响与验证

项目说明和资料导读的内容调整及全部文件的来源／导入 SHA-256 记录在 [`INITIAL_MATERIALS_MANIFEST.csv`](../INITIAL_MATERIALS_MANIFEST.csv)。后续新增实验按 [`DATA_PROVENANCE.md`](../DATA_PROVENANCE.md) 补充可复现信息。
