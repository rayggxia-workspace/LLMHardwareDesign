# 0002：先建立可验证的冻结连接模型，衔接物理Block工程

- 日期：2026-10-22（UTC+08:00）
- 状态：proposed，随Issue #11的PR供审查
- 负责人：Liangruizhi；[任务](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/11)

用户明确研究目标为DAC。Issue7已有其他成员的宏与顶层物理工程，仍缺宏资格和受控对照。本轮在独立工作目录新增Python抽象连接pilot，避免重复认领和无输入校准的本地EDA安装。

固定导线按不可拆电气component建模，只允许白名单连接；记录未使用输出的潜在驱动。使用独立全局合法性、映射能力检查、微型精确oracle与软件图数值参考，先验证研究工具的基本可信度。

代码进入 `project/experiments/frozen_routing/`；本地开发输出隔离在其忽略的 `local_runs/`，正式轻量证据后续归档至 `results/`。仅使用现有D盘Python和项目内venv；复用已装NumPy/Matplotlib的事实写入环境记录。大物理产物仍遵循原共享存储约定。

当前不选择最终工艺、Block规模、定制层或投稿届次；不修改已有研究定义、参考包和他人实验。模型层通过不提升为物理H2或PPA结论。后续依据宏资格和受控实验再决定最终方法与论文主张。
