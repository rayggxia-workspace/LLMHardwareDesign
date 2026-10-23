# Issue31：Projects 接入待管理员处理

仓库：rayggxia-workspace/LLMHardwareDesign；project_id：llm-hardware-design；[Issue31](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/31)，负责人 YUZE-LU。分支 task/31-opentpu-h2。本交接只涉及协作接入，不表示停止实验；物理 runner、当前 SHA／作业索引见 project/experiments/opentpu_h2/results/*-submission.json 与[实验记录](../experiments/issue-31-opentpu-h2.md)。

已实际核对 AGENTS／rayggxia-project-collab 1.0.0、project.json、config/status-mapping.json；仓库无 config/board.json。当前账号为 YUZE-LU，Issue 实际 assignee 为 YUZE-LU、标签 type:task/status:in_progress。2026-10-23 的 GitHub GraphQL 查询 Issue31 projectItems 返回 INSUFFICIENT_SCOPES，需要 read:project；现有凭据 scopes 为 gist、read:org、repo、workflow。连接器没有 Projects 条目字段能力，不改变权限、不新建替代看板。

因此条目是否存在与字段状态为 unverified，同步为 pending。候选入口为 https://github.com/orgs/rayggxia-workspace/projects/1 ，未猜测条目／字段 node ID。需要有权限的管理员（待指定）确认看板与受众，读取当前 Issue 条目并复用或加入，同步 Project ID=llm-hardware-design、Status=In progress、实际 assignee；优先级未指定，不编造；无截止日期。完成后读回条目 URL、ID、字段和核验时间，更新本交接与 Issue，不能只修改本地配置后声称已同步。

登记日常复用管理中心 [PR5](https://github.com/rayggxia-workspace/management-hub/pull/5)，本次连接器实读仍 OPEN、merged=false，登记 pending，不重复登记。不自合并任何 PR。审查人／优先级待指定。

实际工程检查：管理结构和 Python 编译通过；真实完整 DEF 冻结负例／导体开路与错网负例通过；89875 上层 DRC0，89876 实际回装 RC／PG／天线／电气／完整分层 STA 通过。独立完整父层 DRC 89877／89878 仍在 UNLIMITED 运行，无最终通过结论。下一步从 SSH 调度与封存清单核对自然终态，出现违例继续分析；不得据本交接把 Issue 标 done。
