# 主线、并发实验、H1 与 HTML 整合回执

- 日期：2026-10-23，中国标准时间 UTC+08:00。
- 规则：rayggxia-project-collab 1.0.0；项目 `LLMHardwareDesign`；实际操作账号 YUZE-LU。
- 用户明确授权完成 [PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)、[PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)、[PR #17](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17) 的整合与合并。关联 [Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)、[Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)。本次技术复核不冒充他人的独立 GitHub 批准。
- 当前交付分支 `task/15-opentpu-compare`；H1 原交付为 `ce5896de47921fcdc422c4ac9c05cefcb6666bff`，并发／HTML 整合输入为 `fbf32c502c6b6b6b68945d91dbcb2a38079ed946`。保留 merge 祖先与所有封存实验来源，不 squash 或重写来源 commit。最终交付 commit 以 PR #17 在线记录为准。

## 成果与合并边界

PR #8 已合入 main，merge commit `a30d598b295fc047d3b34d83b1e631620ab8e275`。其 VECTOR 路线的零 DRT 错误、PG／接口审计与未通过的 setup／电容检查一并保留；合入代码不代表这些质量门槛已通过。PR #10 新提交的两项结构 CI 均通过；PR #10、#17 的最终合并状态以在线 PR 记录为准，本回执随 PR #17 交付。

两份参考 HTML 位于 [模块与接口报告](../../ref-project/llm-routing/docs/模块与接口报告.html) 和 [Block 布局与接口分布报告](../../ref-project/llm-routing/docs/Block布局与接口分布报告.html)。旧模块报告仅移动目录并调整相对资源链接；新布局报告来自用户已审阅的本地快照。报告内的历史实验状态保留，不能读作本次所有实验均已成功。README、导读和结果包入口同步更新。

保留 H1 的 [最终结果](../experiments/issue-15-opentpu-results.html)、[实验过程及失败证据](../experiments/issue-15-opentpu-comparison.md)、主选择 `selection-reuse20-merged13.json` 和补充选择 `selection-split21-merged13-audited.json`。主报告冻结输入 SHA 为 `f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d`；9 个报告产物未重新生成或改写。

H1 对照保持相同初始计算／状态／存储资源，允许物理有源修复，不能等同于 H2 冻结底座／限定制层。仍有单 small 参数、固定引脚、synthetic SRAM 无 GDS，以及未完成上游 RTL 通用等价和制造签核的限制。旧并发修复失败及 VECTOR 等价求解记录均保留。本次不启动 EDA、不取消作业、不改变时限，也不修改 [H2 / Issue #31](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/31) 的工作树或运行任务。

## 实际复核

完整检查机器回执见 [integration-review](../../work/YUZE-LU/7/integration-review-20261023.json)。本地检查共八项：

1. `python scripts/check_project.py`：管理结构通过，不能替代物理验收。
2. `check_quality_gates.py`、`check_repair_hook.py`、`check_resume_config.py`：并发质量门槛、真实 Tcl hook 执行、配置覆盖的正负例通过。
3. `compare.py` 重算主、补充两套封存选择，输出到仓库外审计目录：所选来源记录及成本／时序结果与发布版本一致。实时观察时间不同单独核验，不改写已冻结发布快照。
4. 缺失及错配完整 ODB 成本证明两个负例均被拒绝，且未创建合格结果输出目录。

此外核验两份 HTML 的本地资源及页内锚点，分别为 56 个不同本地资源／24 张图片／25 张表和零外部本地资源／20 张嵌入图片／23 张表；核验报告 9 产物 SHA 不变，解析新增 Python 脚本并检查差异空白。最终新 head 的 GitHub CI 及合并状态需在实际推送后读回，不将离线检查写成远端 CI 已通过。

## 协作接入与恢复入口

- 登记：管理中心 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 本轮读回仍为 OPEN，`pending`。
- 看板：无 `config/board.json`；实际 GraphQL 查询返回 `INSUFFICIENT_SCOPES`，缺 `read:project`。看板 `unverified`，同步 `pending`，处理管理员待指定；未扩大令牌权限或修改组织设置。
- Issue 状态：合并工程成果不自动证明所有科研验收条件完成；保留尚未验收的限制，不伪造独立审查。
- 恢复第一步：读回 PR #8／#10／#17 的 head、base、CI 与 merged 状态，再同步 main；H2 继续通过其自身任务独立交付。若网络暂时不可达，先保留本地整合提交，不报告远端合并成功。

## 历史网络中断与恢复记录

PR #8 的远端合并已确认；PR #10 的新 head `fbf32c502c6b6b6b68945d91dbcb2a38079ed946` 已推送且两项 CI 通过，但发起合并后本机开始持续出现 GitHub API `EOF`、Git `SSL/TLS connection failed`，连接器请求也失败，故其合并结果暂时无法读回。未确认成功不能报告已合并。结束本轮前终止本轮等待连接的 PR #10 CLI 请求，避免遗留后台写操作；这不能撤销服务端可能已收到的请求，恢复时必须先读回。

PR #17 的本地整合提交 `b03e2dc` 及完整树检查回执 `b8efacf` 已完成；推送因同一连接故障失败，远端尚未确认收到整合提交，也尚未 retarget 或执行其合并。本地工作树为 `D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-15-opentpu-compare`。PR #17 的更新说明已备于仓库外 `D:\Data\电路实验\block-placement-20261022-172122\merge-audit-20261023\pr-17-body.md`。

网络恢复后由本任务操作者继续（无需重新请求已有合并授权）：先读取 PR #10 实际状态；如仍 OPEN，核对 head 与 CI 后使用 merge 方法合并；随后推送本地 `task/15-opentpu-compare`、将 PR #17 base 改为 main 并更新说明，等待其新 head CI 通过，再按匹配 head SHA 合并。最后 fetch 并将本地 main 快进到远端 main，核验报告路径、工作树和合并记录。不要触碰 H2 工作树，不要为此改代理、账号、令牌权限或 GitHub 保护设置。

用户再次要求完成合并后，连接器恢复可用，已读回 PR #10 当时仍 OPEN，随后按匹配 head SHA 使用 merge 方法成功合并，返回 `merged: true`、commit `a77d2883f24981f3170ab3fc472f19d4dd06e355`。Git 使用本机已经配置的代理（仅本次命令参数，不改变持久配置）恢复连接，并 fetch／merge 该 main。以上网络中断待办是历史记录；本次继续推送 PR #17、转向 main、核验新 head CI 后完成合并，最终状态以 PR 在线记录为准。
