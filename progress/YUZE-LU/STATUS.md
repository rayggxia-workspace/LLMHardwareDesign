# YUZE-LU 的进度

## 当前任务：Issue #7

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- Issue：[候选 Block 边界及分层布线流程](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，负责人 YUZE-LU，当前 `in_progress`；审查人和优先级待指定。
- 已完成：读取两个项目的接口／RTL／报告和已有 ACT—MXU 实验；形成 [候选划分及对照矩阵](../../docs/experiments/openTPU-llaccel-block-plan.md)；核实用户授权的集群工程与工具可访问；在独立分支 `task/7-block-routing` 增加正式实验运行器，原参考包和原工作区改动保留。
- 实验：原完整 16-lane VECTOR 的 screening 89442 通过；首试 89441 的工具路径失败记录保留；物理作业 89443 与依赖它的顶层集成作业已提交。实际终态以[试验记录](../../docs/experiments/issue-7-vector-pilot.md)和[轻量索引](../../project/experiments/block_hierarchy/results/issue-7.json)为准，不能将启动作业当作硬化／时序成功。
- 验证：`python scripts/check_project.py`、Python 脚本语法编译、远程 Bash 语法检查和已跟踪文档的 `git diff --check` 通过；完整 core 回归、形式等价性、多计算图、受限定制和系统签核未执行。
- 下一步：完成并核验实际物理产物及宏接口，再准备 F0/H1 对照和 H2 冻结资源规则；不因单宏 shell 成功就外推完整架构收益。
- PR：待创建；本轮脚本提交与实验回执将写入关联 PR，未合并或验收前不标 `done`。
- 接入：管理中心 [登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 本轮读回仍 `OPEN`，登记 `pending`；Projects 缺 `read:project`，无 `config/board.json`，看板 `unverified`、同步 `pending`，由具备权限的管理员处理（待指定），见[持久交接](../../docs/handoffs/2026-10-21-issue-7-projects.md)。

## 历史记录：2026-10-19

- 更新时间：2026-10-19（中国标准时间，UTC+08:00）
- 当前任务：[Issue #1：初始化项目并导入初期资料](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/1)
- 已完成：初期研究资料已进入 `main`；PR #2 已合并。本次按用户要求直接在 `main` 提交并推送更新后的研究资料导读与用户提供的 `ref-project/` 改动；成果提交为 `695587d`、`5c86109`。
- 下一步：完成[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 的审查；由具备 Projects 权限的管理员核验或配置项目看板。`ref-project/` 不纳入 Agent 的主动或例行维护，用户更新后可按要求提交；无需逐项审查或做哈希检查。
- 阻塞：物理实现原始代码、数据库与工具环境未包含在当前资料包；共享存储位置和实际可访问性待核实。
- 本次验证：`python scripts/check_project.py` 通过；导读的 6 个本地相对链接存在；变更文档的 `git diff --check` 通过。未检查参考包内部改动或哈希，未执行业务构建／仿真。本地未配置 `config/board.json`，看板仍待管理员处理。
