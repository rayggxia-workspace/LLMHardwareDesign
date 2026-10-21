# Issue #7 并发实验恢复与主线协调

- 仓库：`rayggxia-workspace/LLMHardwareDesign`；project_id `llm-hardware-design`；操作者 YUZE-LU。
- Issue：[任务 #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)。本批[草稿 PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)是主线 PR #8 的独立补充，不重复接管 VECTOR／供电修复。
- 分支／本地路径：`task/7-parallel-blocks`；`D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-7-parallel-blocks`。
- 执行 runner commit：`2568623f91f871e139c4b7544d00d0181ce4cb01`；监视／审计代码快照 `017a0a7e16c40e47a837e75101789c57b34625e6`。后续文档／监视器提交见本 PR head，不将其冒称为最初已执行代码；计算节点 SHA 索引绑定实际输入。
- 远程根：`yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-01/`。仅此新目录写输出，源 repo／参考包只读。

## 已提交工作与边界

89458 `lyz-par4`：c64 node7，一个64 CPU allocation，四个独立 step 各16 CPU，实读 `UNLIMITED`。89458.0=MXU、.1=ACT、.2=GEMM、.3=ACT＋MXU。各case独立源归档／配置／日志／工作目录／退出码；一路失败不会取消其它路。ACT 已 COMPLETED0:0、路由 DRC0，但 max-cap2，不能标完整电气通过；其它终态见最新索引。

89460 `lyz-par-audit`：c64、1 CPU、afterany89458、`UNLIMITED`。已冻结 `observer-v1/`，结束后自动在计算节点核对各输出 SHA 并写 `completion.json`、`completion.sha256`、逐case校验日志和工具预算门槛。它是一次性流水线后处理，没有后台助手循环通知。临时侧聊的 heartbeat 创建被工具明确拒绝为“不支持临时侧聊”，没有成功创建自动化。

两项目源 commit／工具镜像、完整参数及模型限制在[实验记录](../experiments/issue-7-parallel-blocks.md)。openTPU 是原 small 的 synthetic fakeram 研究模型，不是真实 SRAM／GDS；物理阶段 LEC 显式关闭，不能套用主线证明。合并包装不加周期和缓存，原宽接口保持；分开宏尚未组成实际顶层。原始与本批 IO 时钟/hold预算不同，不做历史PPA的直接收益比较。

## 恢复第一步

确认分支和工作区，读取最新 AGENTS／远程规则后运行：

```powershell
python project/experiments/parallel_blocks/monitor.py --attempt parallel-blocks-01
```

该命令只读远程轻量报告，刷新本分支 `project/experiments/parallel_blocks/results/parallel-blocks-01-latest.json`；若89460已完成，会校验远程 SHA 并下载终态 JSON。先按实际sacct逐step状态、退出码、数据库＋收尾metrics、DRC、setup/hold、电气及PSM判读，不能只看批作业状态。无终态时保留运行，不设置时限或取消慢作业；不要重跑已成功case。新故障先保存证据和具体恢复方案，新attempt不得覆盖旧输入。

需要继续后台助手监视时，应从主线／普通聊天创建监视，而不是声称本临时侧聊可定时唤醒。一次性 Slurm 审计已提交，不因聊天关闭而取消。

## 同步和检查

本批只维护 `parallel_blocks/`、本实验文档、此交接和个人补充，不修改主线 `block_hierarchy/`、`docs/STATUS.md` 或 `progress/YUZE-LU/STATUS.md`。本地原工作区仍由主线管理，不切换它的分支、不合并或覆盖未提交内容。本分支仅新增专有路径，原工作区核对为干净；主线工作树的修改保留。

更新同一条[Issue #7并发回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7#issuecomment-6312241685)和本PR描述，避免刷重复评论或覆盖主线正文。代码／记录供主线审查后决定合入顺序，不自合并。尚在运行时保留草稿，整体 Issue 状态由主线据实际验收协调。

已过：`python scripts/check_project.py`、Python compileall、远程 Bash -n、Git diff whitespace；代码快照017a0a7的[Project structure CI](https://github.com/rayggxia-workspace/LLMHardwareDesign/actions/runs/39576321826) success。未完成的独立功能／等价／物理／系统验收不能由管理CI代替。

登记沿用management-hub PR5（本轮读回仍OPEN／未合并，pending）；本项目无board.json、当前缺read:project，看板unverified／同步pending，由有权限管理员处理，具体人待指定。审查人与优先级待指定，无新增期限。
