# Issue232 审计材料

负责人 Melodydt；[Issue232](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/232)。分支 `task/232-main-model-readiness`，基于 main c4d7b960599b9d292f27eb4429d5f226a7156c95。PR链接在创建并读回后补入本文。

用途：真实大模型仿真就绪性审计及一次基础U入口服务器冒烟。正式结论见 `docs/experiments/issue-232-main-model-readiness.md`，恢复入口见 `docs/handoffs/2026-11-08-issue-232-main-audit.md`。

- `audit-summary.json`：完整远端树身份、本次681份审计输入路径/Git blob核对范围、250份Python AST检查及未执行项。
- `release-check-findings.json`：五项主干支持脚本与冻结清单SHA不符，包含当前Git blob核对和CRLF反向检查；不修改历史清单。
- `smoke-inputs.json`：main25文件子集、输入包SHA和逐文件SHA256/Git blob。
- `smoke-job.sh`：本轮Slurm包装脚本，只修正工具版本须在既有容器内采集，调用未改主干原生回归。
- `smoke-result.json`、`smoke-native-entry.log`：100556，COMPLETED0:0、三初态3/3；8项输出摘要已回收核验。结果JSON沿用服务器原文件名；本目录文件重命名不改原字节。

原始编译日志、生成入口、工具/容器身份、调度记录及构建产物留在本Issue本地和本人服务器独立目录。100554失败和提交前换行错误均保留，详见交接。没有整模型新输入、输出或物理结果。

规则版本 rayggxia-project-collab1.0.0；project_id=llm-hardware-design；登记沿用management-hub PR5 pending；缺board.json及Projects条目工具，看板unverified/同步pending、管理员待指定。独立审查人待指定，尚未合并或标done。
