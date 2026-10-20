# Issue #5：协作规则与本地工作区交接

- 更新时间与交接人：2026-10-20 20:23（中国标准时间，UTC+08:00）；Liangruizhi。
- 仓库：[rayggxia-workspace/LLMHardwareDesign](https://github.com/rayggxia-workspace/LLMHardwareDesign)；项目 ID：`llm-hardware-design`。
- 任务：[Issue #5](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/5)；负责人 Liangruizhi；PR 待创建，当前 in_progress。
- 工作目录：`D:\Projects\liangruizhi`；独立分支：`task/5-collaboration-rules`；基线 commit：`19c900462c60bc55f534ceabc7eedc64dad4a0a6`。交付 commit 尚待产生。
- 当前变更：根目录 `AGENTS.md`、`progress/Liangruizhi/STATUS.md`、`work/Liangruizhi/5/README.md`、本交接及交接索引；仅本任务文档，上传状态以 PR 回执为准。
- 验证：`python scripts/check_project.py`、`git diff --check`、`git diff --cached --check`、`git fsck --connectivity-only` 通过；暂存仅上述 5 个任务文件。未执行业务构建、仿真、物理实现或参考结果内容核验。

## 保留的上下文

- 由本用户发起的后续会话使用 **Liangruizhi / 2663955430@qq.com**；仓库负责人 YUZE-LU 不是本用户登录身份。仅配置了本仓库 Git 作者与账号偏好，未改全局设置或存储凭据。
- YUZE-LU 的 [Issue #3](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3) / [PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4) 尚待审查；最新进度、报告交接在 `task/3-update-routing-reports` 分支，开始相关工作前先读该分支，不能只依赖 main 的旧摘要。
- 本地为浅层稀疏副本：导入 main 的管理文件，省略 `ref-project/` 和 `sources/` 的内容及更早历史。省略路径仍受 Git 跟踪，未产生删除；不要把本地目录未出现解释为远端缺失。未对参考包追加哈希审计。

## 待处理事项与恢复第一步

1. 接手者先用指定账号重新读取 Issue #5、任务分支 PR 和最新规则，检查本地 `git status`、当前 commit 与远端分支，确认没有其他会话占用本工作目录；核对 PR 回执后继续，避免重复提交。
2. 本任务 PR 尚待创建；上传后填写真实 PR 与成果 commit，更新个人进度及 Issue 为 in_review。审查人待指定，按项目约定审查、合并、验收后才标 done。
3. 本机命令行 Git 没有可用的 Liangruizhi 凭据。目前由已认证的 GitHub 插件完成远端读写；需要 CLI fetch/push 或展开稀疏目录时，由本用户接通本人账号的 Git 认证，再按任务需要获取缺失对象。不得借用其他成员账号或把凭据写入仓库。
4. 项目登记复用[管理中心 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)，2026-10-20 核验仍 OPEN，默认分支尚未登记。待有权限的审查者处理，具体人待指定；不直接合并或重复建登记。
5. 看板事实 unverified、同步 pending：本项目未配置 `config/board.json`，当前 GitHub 插件没有 Projects 读写工具。管理中心 `config/portfolio.json` 仅提供[组织 Projects #1](https://github.com/orgs/rayggxia-workspace/projects/1) 的候选配置。具备 Projects 能力及权限的管理员（具体人待指定）先核验目标看板、受众和真实字段，再复用/添加 Issue #5，填 `Project ID=llm-hardware-design`、实际 Status；优先级待指定。操作后读回字段、条目 ID、链接和时间，补入本任务回执。

资料和业务工具链的既有缺项继续见项目状态；本任务未产生新实验数据，也不更改其他任务的状态。
