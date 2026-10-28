# LLMHardwareDesign：预制计算底座研究

当前第一版计算积木为 **M/V/R/S/T五个物理宏，每种一个基础实现**；本轮交付是逐块最终M1–M10布局布线与同源验收。见[五宏规格](docs/BLOCK_LIBRARY_V1.md)、[实施计划](docs/plans/block-v1-library-implementation.md)及[当前交付索引](work/YUZE-LU/121/delivery/README.md)。五块最终原生布局布线、四项独立同源验收及最终文件接收均通过；五块完整原生几何及最终包均齐，项目独立审查待完成。阵列、多实例、跨块预连及产品留下一轮，裕量版本暂不做。下方既有共同边界和历史证据保留各自范围。

本项目研究面向多个计算图的预制计算底座：预先确定计算 Block 和部分物理资源，再通过有限的金属／通孔层定制跨 Block 互联。第一版采用 **Nangate45 原生 M1–M10、via1–via9 预制，自建研究层 M11/M12、via10/via11 后定制**；五块原生单块已有实际实现与验收结果，层次模型和上层互联资格另行验证。性能、能耗和成本优势仍待验证。

**当前阶段提示：叶块冻结不等于共同底座冻结。** 首轮先形成可用 Block 与接口；同类实例数量、不同裕量物理版本的组合、排布和固定预连线由共同底座阶段确定。共同底座冻结后，不同产品只改变声明允许的定制图形。详见[当前实施边界与分阶段冻结](docs/decisions/0004-block-library-base-freeze.md)；具体实现范围和验收状态以 [Issue #121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121) / [PR #122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122) 为准。

## 从哪里开始

1. [项目说明 v1.0](预制计算底座项目说明_v1.0.md)：研究问题、已确认边界、候选方案和待决策清单。
2. [研究资料导读](研究资料导读.md)：依据原 README 完整要点整理的阅读顺序、架构问题和 EDA 研究路线。
3. [项目简介](docs/PROJECT_BRIEF.md)、[架构与目录](docs/ARCHITECTURE.md)、[当前状态](docs/STATUS.md)：持续更新的项目入口。
4. [不同 LLM 架构下的 Block 研究](docs/面向不同%20LLM%20架构的预制计算底座.md)、[Gemmini 学习笔记](docs/Gemmini学习笔记.md)、[工艺互连资料](docs/常见开源工艺金属互连线.md)：研究背景与候选方向。
5. [布线总报告](ref-project/llm-routing/总报告.html)、[线长报告](ref-project/llm-routing/线长报告.html)、[模块与接口报告](ref-project/llm-routing/docs/模块与接口报告.html)、[Block 布局与接口分布报告](ref-project/llm-routing/docs/Block布局与接口分布报告.html)与[结果包阅读说明](ref-project/llm-routing/阅读说明.txt)：参考项目的布线分析、模块接口及其证据边界。
6. [openTPU ACT/MXU 同资源物理对照](docs/experiments/issue-15-opentpu-results.html)、[实验过程与失败证据](docs/experiments/issue-15-opentpu-comparison.md)：本项目实际完成的块内和顶层布局布线，含面积、完整时序及布线成本。H1允许有源修复，尚未实现H2冻结底座／限定制层；单small参数及synthetic SRAM的限制见报告。

`sources/` 保存手写笔记和讨论资料；`ref-project/llm-routing/` 保存参考项目结果包，**不纳入 Agent 的主动或例行维护范围**；用户更新后可按要求提交，无需逐项审查或做哈希检查。该包不包含源代码、完整物理数据库、工具环境或运行日志，不能单靠仓库内容重新运行物理实现。详情见[来源与复现边界](docs/DATA_PROVENANCE.md)。

## 真实模型实验与 Block 分析

[阶段性分析报告](docs/model-analysis/MODEL_EXPERIMENT_ANALYSIS.md)汇总八个具体模型的运行目的、实际范围、关键结果与失败，并将证据对应到 P1–P15 能力和 M/V/A/R/S/D 逻辑域。原实验以固定 commit 链接追溯；本报告集成不等于来源 PR 或整模型硬件验收。

模型资料统一归档在 [docs/model-analysis](docs/model-analysis/README.md)：可阅读[精简字符算子图](docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md)，或通过[完整图册说明](docs/model-analysis/COMPUTATION_GRAPHS_FULL.md)查看手工、原始 ONNX 与 onnxsim 图及验证边界。

## 当前工作方式

远程计算资源与目录权限见[远程服务器使用规则](docs/REMOTE_RULES.md)，使用服务器前请先阅读。

任务、负责人和验收条件以本仓库 [Issues](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues) 为准。每项任务使用独立分支和 PR；开始工作前阅读 [AGENTS.md](AGENTS.md) 与[协作说明](docs/COLLABORATION.md)。实际物理实验及冻结结果生成命令见[架构与运行](docs/ARCHITECTURE.md)；管理结构检查为：

```powershell
python scripts/check_project.py
```

上面的命令只验证项目管理文件结构，不验证芯片架构或布线分析结论。
