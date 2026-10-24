# Issue72个人辅助记录

[Issue72](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/72) / [PR73](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/73)，负责人Liangruizhi/182389313/2663955430@qq.com。
根D:/Projects/LLMHardwareDesign-numeric-closure，task/72-numeric-closure；base task/70-moe-hybrid@f4d2c4643ef683336bf583739bf117cca8013118。
独立子worktree：D:/Projects/LLMHardwareDesign-72-granite、-72-falcon、-72-audit，分别task/72-granite-routing、task/72-falcon-chain、task/72-closure-audit。没有并行会话同写root/同分支。

本人服务器/public/home/yuzelu/RuizhiLiang/issue72-numeric-closure-20261024，Slurm lrz-i72-*、c96 node13/node14。无新下载/GPU/其他机器任务，成员89448未中断；过程缓存仅本任务D:/Projects/Codex/numeric-closure-20261024-1710和server tmp。

- phases/：15阶段实际源commit/每源SHA/staging档SHA，不能以最新文档HEAD替代旧run源。
- slurm/：完整command/argv/job/phase/bindingSHA；过期依赖提交拒绝日志无job，确认全部20接收后90280直接提交成功。
- collect.py：显式仅本任务目录/日志，不含权重、其他任务。实际phase15@844825b1cfd1e00d6a297705977f3a1b3386951e。
- 正式results/issue-72：完整/精选SHA、逐成员字节验收、43个Git源核验、103作业实际状态、路由/整数/连续/端口指标。完整9.90GB只服务器，精选2.48MB metadata入Git，原Issue70数据/权重外部依赖明确。

恢复先核最新规则/Issue/PR/评论/成员55/63及本人认证，读正式索引，验外包和全部成员SHA，再按原phase源码和slurm JSON里的command复跑到全新out。既有issue61 venv-modern/线程按原配置，不申请服务器误配的--mem，不重下载模型。metadata-only精选不能代替完整数组/原capture；字节接收不是数学/质量/RTL验收。

本机90新边界/80旧模块/管理结构/diffcheck通过；103服务器job100完成、3FAIL保留；所有入比较的接收PASS。未完成：Granite全MoE整数及质量、Falcon整模型/长窗、真实wide/SFU/ROM和grouped-RQ同资源服务/prefill复用、物理宏与PPA。审查/合并待指定，不done；登记PR5 pending，看板unverified/同步pending待管理员。[交接](../../../docs/handoffs/2026-10-24-issue-72-numeric-closure.md)。
