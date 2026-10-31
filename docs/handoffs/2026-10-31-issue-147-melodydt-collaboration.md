# Issue #147：Melodydt 本地接入与协作规则交接

- 更新时间：2026-10-31 11:47（Asia/Shanghai，UTC+08:00）；交接人/负责人 Melodydt。
- 仓库：[rayggxia-workspace/LLMHardwareDesign](https://github.com/rayggxia-workspace/LLMHardwareDesign)；project_id：llm-hardware-design；认证 ID 172562968。
- 任务：[Issue #147](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/147)；远端分支 `task/147-melodydt-collaboration`；PR 待创建。
- 基线 commit：`a103da352b7e431cedc69f54b9f71c05371be1b3`；成果 commit 待上传后在 PR/验证回执记录，当前不编造。
- 本地项目：`D:\Study_material\Study_material\LLMHardwareDesign`，对应应用项目“课题研究 大模型硬件化”。开始时目录为空且无 .git。本次只落地管理参考文件及任务成果，尚不是 Git checkout；不要从这里执行会将缺失项目文件判为删除的全量上传，也不要声称本地 HEAD 与远端一致。
- 当前聊天旧目录 `C:\Users\Administrator\Documents\ChatGPT\课题研究 大模型硬件化` 是另一个无远端、无提交的空 Git 仓库。本任务的准备资料在其中的独立任务子目录，不将旧仓库绑定为目标仓库。
- 成果：AGENTS.md 保留主干全文后补充八项协作要求；progress/Melodydt/STATUS.md、本任务 work README 和本交接。实际验证与文件 SHA 将保存到 work/Melodydt/147/verification.json。
- 实际验证：待执行；业务构建、RTL/SystemC 仿真、物理实现未执行，本任务未修改相关源或作业。
- 本地文件来自目标分支基线的管理资料；未同步完整研究资料、ref-project/、其他成员 work/progress 或活动实施分支，不能据本地缺文件推断远端缺项。

## 已核对的协作范围

- #5 / PR #6 由 Liangruizhi 负责，OPEN/未合并；已读其任务分支 AGENTS 和交接。通用条目与本任务有重叠，独立审查人需协调共同 AGENTS.md 的合并，不复制其个人身份绑定、不接管其任务。
- #121、#143 是已有宏实现任务，#145 / PR #146 是 SystemC 任务；PR #144 仍在实现与验收。最新 Issue/PR 比 main 的摘要更新，不把主干“尚待实现”当成活动分支没有成果，也不把活动分支的成果当作主干已验收。
- 本任务不修改 RTL、实验配置、参考结果包、服务器目录或已有作业，不给其他成员派活或改状态。

## 尚未完成与恢复第一步

1. 接手者先用 Melodydt 认证重新读取本 Issue、PR 和最新 AGENTS/Skill；核对应用项目路径、目录内容、是否已有新的 Git checkout 及其他会话占用，再继续。已存在本任务 PR 时复用，避免重建。
2. 当前本机 CLI 未核验 Melodydt 认证，未执行 clone/fetch/push。沙箱内旧版 Git 有 DLL 重定位错误，沙箱外只读 Git 可运行。远端提交使用本人 GitHub 插件；需要完整本地源码时，由本人接通已核验的 Git 认证并在独立目录获取真实 checkout，保留本次成果后再整合，不覆盖现有文件或冒充其他成员。
3. 登记 pending：管理中心默认分支尚无本项目记录，[既有 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) OPEN/未合并。复用此登记，不重复建 PR；由获授权审查者处理，具体人待指定。
4. 看板 unverified / 同步 pending：主干 config/ 无 board.json，当前工具无 Projects 条目读写能力；并非已经证实 Melodydt 账号没有看板权限。有工具和权限的项目管理员（待指定）先核验候选组织看板 #1 的受众、实际字段和本 Issue 既有条目，复用/加卡，按 status-mapping 填 Project ID、实际 Status 及已确定的 Priority，再读回条目 ID、链接和时间。
5. 完成本地验证后上传任务分支并创建 PR；更新本人进度和 Issue 至真实阶段。独立审查人待指定，未满足审查、合并与验收前不自合并、不关闭 Issue 或标 done。
