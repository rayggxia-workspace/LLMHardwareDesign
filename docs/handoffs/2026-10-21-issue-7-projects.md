# Issue #7：登记与看板核验交接

- 更新时间：2026-10-21（中国标准时间，UTC+08:00）。
- 仓库：<https://github.com/rayggxia-workspace/LLMHardwareDesign>。
- 任务：<https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7>；负责人 YUZE-LU。
- 工作分支：`task/7-block-routing`；从 `origin/main` 的 `19c900462c60bc55f534ceabc7eedc64dad4a0a6` 创建独立工作树，已同步PR #4合入后的主干。最终物理运行代码 commit `357dd98a7a07f370a1cc2c67b066c7ecccf3bf9a`；[PR #8](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/8)保存收尾采集修复、结果及当前HEAD回执。

## 本轮实际核验

`gh api user --jq .login` 返回 `YUZE-LU`，GitHub 连接器亦以该账号操作；目标私有仓库可读写。

管理中心登记 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 本轮读回为 `OPEN`、`mergedAt=null`；继续记录为 `pending`，没有另建登记 PR。

本仓库没有 `config/board.json`。按历史交接指定的候选 [组织看板 #1](https://github.com/orgs/rayggxia-workspace/projects/1) 发起只读 GraphQL 查询，返回 `INSUFFICIENT_SCOPES`，缺少 `read:project`。因此未读取看板真实字段、Issue 条目或当前状态，也没有执行加卡或字段同步。现有 GitHub 插件未提供 Projects 操作工具。

看板状态：`unverified`；加卡与同步：`pending`。本轮没有扩大令牌权限或新建替代看板。

## 恢复动作

由具备该看板访问和编辑能力的项目管理员处理，具体人员待指定：

1. 确认看板 #1 与本项目及其私有资料的受众匹配，并确认 `config/board.json` 应采用的实际配置。
2. 查询 Issue #7 的既有条目，复用既有条目或在授权范围内加卡。
3. 核验 `Project ID=llm-hardware-design`、`Status`、负责人 YUZE-LU；优先级未指定，不猜填。
4. 根据 Issue 的实际唯一 `status:*` 标签同步状态，读回并在 Issue/PR 回执补看板 URL、条目 ID、字段与时间。
5. 登记 PR 合并后核对默认分支记录，再把登记从 `pending` 改为 `registered`。

本轮研究成果、物理作业、验证与未完成项的继续入口为 Issue #7 和 `project/experiments/block_hierarchy/`；这些工程工作继续推进，不因看板缺权限而停止。没有审查、合并及验收证据时不得把 Issue 标为 `done`。

## 物理实验恢复入口

实际作业与终态以[轻量索引](../../project/experiments/block_hierarchy/results/issue-7.json)和[现场记录](../experiments/issue-7-vector-pilot.md)为准；原始输出在获授权集群 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/<attempt>/`。运行器提交后必须读回 `TimeLimit=UNLIMITED`，不能为缩短等待再设置人工时限。新试验一律新目录，不覆盖失败记录。

89448 是原默认阶段 LEC 路线，仍未得证明结论、保持UNLIMITED；其后若完成物理实现，必须先从它自己的最终 ODB／SDC／SPEF 生成匹配 LEF／Liberty，再使用新 PG 配置提交新顶层，不能给该路线套用89453的模型。89449是等待48的旧默认PDN配置，确认PENDING后因配置已知不兼容而取消，receipt／reason在 `slurm-obsolete-89449-20261021/`，不是按求解耗时终止48。

独立物理路线89453显式 `LEC_CHECK=0`。89461通过隔离内存修复，89462在真实POST_PDN调用上下文失败；修复后89472完整顶层 `COMPLETED 0:0`，89475最终只读审计 `COMPLETED 0:0`，两者实际UNLIMITED。DRT错误0、最终PSM、唯一固定宏／2246位接口与逐位映射通过；最终源ODB精确哈希和31,506个via的M7–M9独立几何复算闭合。块内部3 ns时序／电容、父级3条setup违例、无父级多宏时钟树、默认活动供电模型和缺少宏功耗模型的限制仍保留。下一位操作者先读当前索引与PR回执，不从历史“运行中”文字推断现状。

本轮成果进入审查，后续研究从同资源F0/H1对照开始；修改模型或约束必须另立可比较实验，不为清除违例直接改预算。H2仍需冻结全部有源单元、时钟／PG和预制端点，限制定制层／通孔，并验证真正不同的计算图。审查人、后续实施负责人和看板管理员均待指定；未审查合并，不标done。
