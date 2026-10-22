# YUZE-LU 的进度

## 2026-10-22 ACT/MXU 同资源物理对照

- 更新时间：2026-10-22 19:12，中国标准时间UTC+08:00；负责人／账号YUZE-LU。
- [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)，分支 `task/15-opentpu-compare`，依赖PR10基线2b76f69，独立工作树，未修改已有PR8/PR10工作树与89448作业。
- 已完成：共同169109映射单元逐型号核对；关闭合并导入额外剪去9DFF等135单元的优化，实际ODB库存一致。89631旧修复严格通过，独立89650核对34个输入。ACT／MXU／合并原候选块均通过电气与物理检查，但含M10信号，须为父层M10 PG策略重新布线。第三轮显式GRT路由上限M9，最终LEF复核；ACT89671、MXU89677已严格通过，MXU最差cap余量提高至+3.090818fF。透明分层STA自检89672通过；ACT映射到物理网表的612状态／存储实例、3210逻辑锥核对89685通过，状态输入突变负例成功检出。
- 已补齐：89678合并块最终提取、89687三块功能锥核对均严格通过。89700／89701封存CTS、PG连通性通过，实际1662bit引脚几何哈希相同；旧03／04因缓存导出误判提前停止，更正证据已保留，旧ODB实际引脚也正确。
- 正在执行：合并父层06／89711已DRC和天线清零、最终PG通过，但完整分层STA setup −0.053027ns及电容余量失败；保留真实结果继续收敛。其40846未标注驱动逐一原生fanout审计89750通过，均无连接负载，部分未标注0。拆分07／89722仍在DRT；08／09联合修复因EST-0104失败，正在验证独立进程、真实ODB检查点交替修复。全部UNLIMITED，不设置期限。草稿PR17保持in_progress，尚无合格父层总PPA。
- 下一步：完成共同die和逐bit引脚的两宏／一宏父层实际布线，检查PG落点及严格原生连通性；拼接真实网表与分层SPEF检查完整路径，按真实违例继续调整。汇总面积／时序／线长／通孔／CTS与缓冲开销，区分叶面积和宏占地避免重复计数。
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
