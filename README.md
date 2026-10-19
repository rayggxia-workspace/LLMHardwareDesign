# LLMHardwareDesign：预制计算底座研究

本项目研究面向多个计算图的预制计算底座：预先确定计算 Block 和部分物理资源，再通过有限的金属／通孔层定制跨 Block 互联。当前处于**架构定义与研究方案整理阶段**；具体工艺、Block 库、定制层集合和实现工具链仍待确定。性能、能耗和成本优势是待验证目标，不是已有结论。

## 从哪里开始

1. [项目说明 v1.0](预制计算底座项目说明_v1.0.md)：研究问题、已确认边界、候选方案和待决策清单。
2. [研究资料导读](研究资料导读.md)：原 README 的完整内容，保留初期阅读顺序、架构和 EDA 工作思路。
3. [项目简介](docs/PROJECT_BRIEF.md)、[架构与目录](docs/ARCHITECTURE.md)、[当前状态](docs/STATUS.md)：持续更新的项目入口。
4. [不同 LLM 架构下的 Block 研究](docs/面向不同%20LLM%20架构的预制计算底座.md)、[Gemmini 学习笔记](docs/Gemmini学习笔记.md)、[工艺互连资料](docs/常见开源工艺金属互连线.md)：研究背景与候选方向。
5. [布线分析图文报告](ref-project/llm-routing/index.html)与[结果包阅读说明](ref-project/llm-routing/阅读说明.txt)：四个参考项目、六个案例的已有分析及其证据边界。

`sources/` 保存手写笔记和讨论资料；`ref-project/llm-routing/` 保存参考项目的轻量结果包。布线结果包包含报告、图表和统计表，**不包含**源代码、完整物理数据库、工具环境或运行日志，不能单靠仓库内容重新运行物理实现。详情见[来源与复现边界](docs/DATA_PROVENANCE.md)。

## 当前工作方式

任务、负责人和验收条件以本仓库 [Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues) 为准。每项任务使用独立分支和 PR；开始工作前阅读 [AGENTS.md](AGENTS.md) 与[协作说明](docs/COLLABORATION.md)。实际测试命令随实现建立，目前仅有模板结构检查：

```powershell
python scripts/check_project.py
```

上面的命令只验证项目管理文件结构，不验证芯片架构或布线分析结论。
