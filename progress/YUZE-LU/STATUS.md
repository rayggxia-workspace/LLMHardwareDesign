# YUZE-LU 的进度

## 2026-10-22 ACT/MXU 同资源物理对照

- 更新时间：2026-10-22，中国标准时间UTC+08:00；负责人／账号YUZE-LU。
- [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)，分支 `task/15-opentpu-compare`，依赖PR10基线2b76f69，独立工作树，未修改已有PR8/PR10工作树与89448作业。
- 已完成：查实旧margin30/40由dont_touch冲突失败；新修复已继续路由。共同169109映射单元逐型号核对；发现合并导入又剪去9DFF等135单元，关闭优化后实际库存一致。新ACT块已严格通过，面积35985.5µm²、setup+1.25790ns、hold+0.0326128ns、最差电容余量+2.540645fF、DRC/天线0。
- 正在执行：89642 MXU，89647固定资源合并块，89631旧合并定向修复；89640仅保留剪枝诊断。均实读UNLIMITED。两组正式顶层布线尚待块内合格及视图准备，PR待创建。
- 下一步：读取冻结终态，按真实违例迭代，运行共同die和逐bit引脚的两宏／一宏父层布线；拼接真实网表与分层SPEF检查完整路径，汇总面积／时序／线长／通孔／CTS与缓冲开销。
- 接入：登记PR5沿用pending证据；本仓库无board.json、已知read:project权限缺项，看板unverified／同步pending，处理管理员待指定。审查人／优先级待指定，不自合并或标done。
- 代码与实际作业runner各自按回执绑定；[实验记录](../../docs/experiments/issue-15-opentpu-comparison.md)与 `project/experiments/opentpu_compare/results/` 保留失败和通过证据。

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）
- 当前任务：[Issue #3：同步两份布线报告并补入 llaccel 引擎分析](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/3)。负责人 YUZE-LU，优先级待指定。
- 已完成：同步最新总报告、线长报告及其引用资源；总报告增加 llaccel 三个引擎的中文分析与 9 张图。保持图片直接展示、长表可展开；不创建备份或多余首页。更新来源边界和包说明。
- 验证：管理结构检查、报告依赖/锚点检查、包内清单哈希、正文/表格保留和差异检查；具体结果见本任务 PR 回执与 `work/YUZE-LU/3/validation.json`。没有重跑物理实现或 STA。
- 交付：[PR #4](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/4)，分支 `task/3-update-routing-reports`，报告成果 commit `b041d53`；2026-10-21 按用户明确要求已合并到 main，合并提交 `1d80491`。
- 下一步：继续审查[管理中心登记 PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)。登记仍为 pending。
- 阻塞/接入缺项：报告上传可独立完成；本仓库没有看板配置，当前凭据缺少 `read:project`，无法核验或同步 Projects。由有相应权限的管理员处理，处理人待指定；详见[交接](../../docs/handoffs/2026-10-20-issue-3-report-board.md)。不自行扩大凭据权限。
- 历史：Issue #1 的初期资料由 PR #2 导入，后续参考资料提交 `695587d`、`5c86109` 已进入 main。`ref-project/` 仍不属于 Agent 主动或例行维护范围。

## 2026-10-21 补充交付

- 按用户要求补入 `ref-project/llm-routing/模块与接口报告.html`，保留原文，并复制其引用资源；README、研究资料导读及阅读说明补充入口。
- 本次仅检查新报告的本地引用是否存在及管理结构、文档差异；不执行哈希检查，不重算参考数据，不修改原有清单。原清单不覆盖此次新增文件。
- 沿用 Issue #3、任务分支及 PR #4 上传；2026-10-21 已按用户要求合并到 main。看板权限缺项沿用上述交接。

## 2026-10-21 远程服务器规则

- [Issue #9](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/9)：记录服务器节点、`/public/home/yuzelu` 下的目录权限和 sbatch 任务命名要求，README、AGENTS.md 提供规则入口。
- 任务名采用“本人姓名缩写-任务缩写”，如 `hpy-block`；脚本和提交时覆盖的任务名均应遵守，便于在 squeue 的 NAME 中辨认。
- 验证：管理结构检查及所改文档的差异检查通过；未登录或修改远程服务器。通过 PR #4 上传，2026-10-21 已按用户要求合并到 main；看板同步仍待具备权限的管理员处理。

## 2026-10-21 main 集成

- 按用户“最新状态都提交到 main”的明确要求，将报告、远程规则及此前未提交的工艺互连资料补充一并纳入 PR #4 并合并。合并提交 `1d804912927602900aa074339db33156a805c582`；本地已同步到 main。
- 管理结构及文档差异检查通过；未重算参考数据。其他成员的独立 PR 未合并。登记、看板的既有待办继续保留，不宣称已完成。
