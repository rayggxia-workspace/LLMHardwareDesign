# Issue #15 当前工程入口与接入待办

更新时间：2026-10-23 04:37 CST（UTC+08:00）。最后两条物理路线及其配套证明均已自然完成，无耗时取消。

- 仓库`rayggxia-workspace/LLMHardwareDesign`；project_id `llm-hardware-design`；负责人／实际账号YUZE-LU。
- [Issue #15](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/15)、[PR #17](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/17)，base `task/7-parallel-blocks`，依赖PR10；工程检查齐备，交付in_review／待独立审查，不自合并。
- 分支`task/15-opentpu-compare`，工程代码`76516bc9385b766fd3f194b9caabbf5edcdd6d46`；最终交付HEAD以PR实读为准。报告生成代码`8a646d80b08845079da4e1b7a544233d6a94ffbf`。实际各原生runner以results/*-submission.json绑定；不能用最新HEAD替换旧执行身份。
- 本地工作树`D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-15-opentpu-compare`；原始输出`yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15/`。PR8／PR10工作树、VECTOR、89448均未修改。

## 已合格成果

[中文HTML和三类图表](../experiments/issue-15-opentpu-results.html)及[过程／失败证据](../experiments/issue-15-opentpu-comparison.md)。选择selection-reuse20-merged13.json：m9-act-03／89671、m9-mxu-03／89677、m9-merged-03／89678、top-split-reuse-20-01／89829、top-merged-13／89772，加三块功能89687、父层功能89831、非支持库存89733、双子块RC89798、覆盖89832、完整ODB成本89833，共十一份封存来源严格通过compare。全部真实UNLIMITED，无耗时取消策略。

拆分／合并总叶面积484240.4／482252.4µm²、总信号线6647739／6204600µm、通孔1322289／1284106，完整setup +0.102306／+0.065642ns、hold +0.036146／+0.013027ns。两组DRC／天线／电气／PG／完整STA全部通过；相同计算状态和12 SRAM、2.5ns／0.5ns预算与实际1662bit引脚。支持成本完整计入，宏占地和共同die另列。

快照SHA f65688a957f13ef70216e923891ef6ff539adfc6f81c3e29a74ba5d10332720d；report-manifest.json绑定HTML、六图及两JSON共9个文件。delivery-validation.json记录全部来源／工具／UNLIMITED／首次清单核对、实际三PNG和浏览器核验及两个成本证明负例。结构检查、Python编译和diff检查通过；临时预览服务及页面已关闭。

## 当前继续入口

1. 全量清线重布21／89826自然COMPLETED0（1:02:26），匹配功能89827、覆盖89828及五ODB成本89835也全部通过；selection-split21-merged13-audited.json另存完整十一来源对照于results/alternates/full-clear21/，SHA72b9829d0df7ac7d30c5b7a6f8e602f11e317c2070cbacab4f55e466299cce0f。原主快照和9报告产物SHA不变，两套合计15份唯一来源全部UNLIMITED／自然完成。
2. 本轮实现、违例修复和交付检查已齐备，无仍需启动／等待的原生作业。后续先读Issue／PR最新在线状态、规则和来源，再由独立审查人检查结果、处理依赖PR10、合并及最终验收；审查人待指定，不自行合并或done。
3. 若要重新选择来源或新增H2实验，另立明确验收范围；所有新原生尝试仍须全新目录和runner身份、实际UNLIMITED。当前collect只更新实时观测，不改写主／补充快照；不得混用实时值。

H1允许新增有源缓冲及完整父层路由，不冒充H2冻结资源／少量定制层。单small、Nangate45 typical、固定宏位置与引脚；synthetic SRAM无真实GDS，上游RTL通用等价和制造签核未完成。历史所有失败及03／04因引脚缓存误判而误停的更正保留在实验记录及results，不重写旧终态。

访问核验回执见work/YUZE-LU/15/2026-10-23-delivery-access.json；标签列表已通过CLI实读，账号与连接器均为YUZE-LU，未扩权。

## 管理员与审查待办

- 登记：[管理中心PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5)于本次核验仍OPEN、merged=false，pending；不重复登记。
- 看板：本仓库没有config/board.json；config/status-mapping.json已有映射，但没有Projects条目核验工具，本次CLI实际GraphQL查询返回INSUFFICIENT_SCOPES，缺read:project。实际条目／字段unverified，加入／同步pending。
- 待具备权限的管理员（待指定）确认候选组织Projects1的受众和本项目接入，查找复用Issue15条目，按真实配置写入Project ID及Status、读回条目ID／链接／时间。不猜ID、不自行扩权。
- 审查人／优先级待指定；独立审查、合并及最终验收尚待处理。无用户期限要求，不填杜撰日期。
