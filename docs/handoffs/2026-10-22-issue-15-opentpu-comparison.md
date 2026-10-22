# Issue #15 工程入口与接入待办

本记录同时保留尚未解决的协作接入事项；不表示停止正在获授权执行的实验。

- 仓库：`rayggxia-workspace/LLMHardwareDesign`，project_id `llm-hardware-design`。
- [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)，负责人YUZE-LU，实际身份已读回；[草稿PR #17](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17)，base `task/7-parallel-blocks`，依赖PR10，不自合并。
- 当前分支 `task/15-opentpu-compare`；最近物理修复runner `e4e3b9a6ff91fb1b60efe4a85217a99a174477d8`。实际已执行runner分别绑定每条submission回执，不能用更新后的HEAD替换旧运行身份。
- 本地独立工作树 `D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-15-opentpu-compare`；原始输出 `yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15/`。不修改已有PR8／PR10工作树和封存结果；89448不属于本轮。
- 正式代码 `project/experiments/opentpu_compare/`，轻量回执 `results/`，[实验定义与实测](../experiments/issue-15-opentpu-comparison.md)，个人进度 `progress/YUZE-LU/STATUS.md`。

## 已验证与继续入口

已运行管理结构检查、Python编译、差异检查及每轮上传Bash语法检查。真实计算节点核对镜像、工具、输入输出SHA；全部Slurm作业实读UNLIMITED，无耗时取消策略。ACT功能锥及负例、透明分层SPEF自检已通过。块内／父层严格门槛和功能证明按实际终态分别记录，不把结构检查、进程退出或cap计数0当作验收。

第一步运行 `python project/experiments/opentpu_compare/collect.py`，随后 `quality.py`。正式三块m9-act-03／89671、m9-mxu-03／89677、m9-merged-03／89678均严格通过，三块功能证书89687通过。父层从共同封存CTS89700／89701继续，当前合并06／89711正在DRT，拆分07／89722针对宏输出电容加入近端缓冲；后续因真实违例更新候选时，以回执及实验报告最新选择为准。03／04曾因旧引脚命令缓存误判被提前停止，89705直接读ODB证明原几何正确；更正在results/correct-cached-pin-export-diagnosis.json。保持2.5ns／0.5ns、同功能／状态／SRAM，任何调整使用全新尝试目录；不得放宽原预算掩盖违例。

尚需两组父层实际终态、完整分层STA与PG检查、共同引脚几何核对和最终成本对照。synthetic SRAM无真实GDS，上游RTL等价和制造签核未完成；实验为允许M10父层PG和新增缓冲的H1，不是H2冻结底座。

## 管理员与审查待办

- 登记：沿用[管理中心PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)的pending证据，未声称registered。
- 看板：本仓库仍无 `config/board.json`；既有凭据缺少 `read:project`，当前Projects工具也未提供任务条目核验能力。实际条目／字段状态unverified，加入／同步动作pending。
- 待具备权限的管理员（待指定）核对组织总览Projects1是否适合本项目，查找并复用Issue15条目，按 `config/status-mapping.json` 写入真实Project ID和Status后读回，记录条目ID／链接／时间；不能猜测条目或字段ID，也不能自行扩充凭据权限。
- 审查人、优先级待指定；任务仍in_progress，实验完成也须独立审查及合并才能按规则标done。没有期限要求，不填写杜撰日期。
