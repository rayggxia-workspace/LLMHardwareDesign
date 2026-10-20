# AGENTS.md 协作规则补充

- 关联 Issue：[本仓库 Issue #5](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/5)
- 负责人：Liangruizhi
- 资料更新时间：2026-10-20（中国标准时间，UTC+08:00）
- 用途：保存本任务的核验摘要；正式规则位于根目录 [AGENTS.md](../../../AGENTS.md)，进度位于 [STATUS.md](../../../progress/Liangruizhi/STATUS.md)。PR 待创建。

## 核验与范围

- 认证查询返回 GitHub 用户 ID `182389313`、账号 `Liangruizhi`、邮箱 `2663955430@qq.com`；只使用该连接。仓库为 `rayggxia-workspace/LLMHardwareDesign`，私有，默认分支 `main`，当前账号具有 pull/push/triage 权限。
- 基线为 `19c900462c60bc55f534ceabc7eedc64dad4a0a6`。本地原为空目录，已通过 GitHub 插件导入该提交的管理文件，建立浅层稀疏 Git 副本；`origin` 指向目标仓库。命令行 Git 认证仍待接通，不声称已通过 CLI clone/push。
- 本任务修改范围仅为 `AGENTS.md`、个人进度、本说明、本任务交接和交接索引。未改变研究阶段、其他成员进度、权限或参考结果。
- 已读取 README、AGENTS、统一协作 Skill 1.0.0、CONTRIBUTING、project.json、协作说明、状态、架构、资料来源边界、进度与任务资料模板，以及 Issue #1/#3、PR #2/#4 和报告任务分支中的交接。PR #4 尚未合并，避免重复接手。

## 已执行验证

- `python scripts/check_project.py`：通过，仅验证管理结构。
- `git diff --check`：通过。
- `git fsck --connectivity-only`：通过；仅核验本地 Git 对象连接，不是对参考报告的内容审计。
- `git diff --cached --check`：通过；暂存范围为上述 5 个任务文件，无额外文件。
- 业务构建、仿真、物理实现：未执行；当前没有相关实现或工具链，本任务只修改协作文档。
- 正式规则文件 SHA-256：`397906fecacb28a49c12bdfd2230c1f3137abf3b0d202af0bbe75344e2536d54`。

## 接入事实

- 登记：pending；2026-10-20 核验管理中心默认分支 registry 尚无本项目记录，已有登记 PR #5 仍 OPEN，不重复创建登记。
- 看板：unverified / 同步 pending；本仓库没有 `config/board.json`。管理中心 portfolio 提供组织 Projects #1 的候选配置，但当前插件没有 Projects 工具，未读取或修改在线条目，不据此推断本人缺少看板权限。
- 后续操作与处理人见[交接](../../../docs/handoffs/2026-10-20-issue-5-collaboration.md)。
