# Issue21 划分研究交接

仓库rayggxia-workspace/LLMHardwareDesign；project_id=llm-hardware-design；负责人Liangruizhi（2663955430@qq.com，ID182389313）。Issue21，分支task/21-operator-partition，目录D:/Projects/LLMHardwareDesign-partition；base task/19-interface-contract，保留PR20/18/14/12依赖。正式运行源码680dbbeed9a9189c06b047918ab4ae2ea6eedc28；交付head以PR实际读回为准。

用户共同问题、推理范围、代表模型选择与自主执行授权已写docs/RESEARCH_QUESTION.md及AGENTS。首轮方法docs/OPERATOR_BLOCK_PARTITION.md，实际结果docs/experiments/issue-21-operator-partition.md。完整解决算子/Block划分仍是持续研究目标，不能因本阶段微实验通过标为整体完成。

成果project/experiments/operator_partition/results/issue-21-run01/evidence.zip（233685bytes），SHA256 f85b1f120065f91d13df95cdf343d35eb48640d9a56d2755b46da5c6ed82306d。630调度、11340容量/边界条件、378数值正例＋3负例，164业务检查、独立审计和逐字节重放通过；原始官方配置/来源及独立代码在本人work目录。GitHub通过已核验账号的插件Git对象API上传，非CLI push。

并行研究只写D:/Projects/Codex/operator-partition-20261022/{deepseek,qwen-llama,method-review}/，root显式复制；未并行修改root工作树。没有本轮服务器作业，不读取/修改ref-project，不改其他成员进度/工作树/作业。D盘运行与重放、调研和源证据仍用于后续复查，保留；旧轮被审批拒绝清理的目录未操作。

## 待办和真实状态

1. 审查/合并：任务分支及交付PR待指定审查人，未自合并。源PR依赖仍未合并；新阶段不改写旧实验结果。
2. 管理登记：沿用management-hub PR5 pending；看板无board.json及当前Projects工具，在线状态unverified、同步pending，管理员待指定。核验Issue21条目、Project ID、In review与用户明确的首要研究优先级后读回，不能声称本地状态自动同步。
3. 研究：未执行真实权重推理/质量或硬件端到端。下一任务优先核对可公开获得的小型Qwen代表模型环境与权重版本，实际prefill/decode trace；同时把两引擎/两bank账本扩为端口和到达/服务约束。只承认现有适用范围；少量代表不等于全系列支持。
4. 物理依赖：Issue15/PR17由YUZE-LU继续真实顶层，恢复时核对最新终态和来源再复用；当前微实验不依赖接管其作业。
5. 自动目标：2026-10-22后续：用户明确回复已清除旧目标；get_goal读回null后，create_goal成功登记算子与Block划分持续研究目标，get_goal核验status=active。目标覆盖代表性推理工作负载、计算/状态/通信归属、真实存储/端口/布线/时序约束和端到端收益或失败边界；无token预算。阶段微实验或待审查PR不等于整体目标完成。

## 恢复第一步

核对指定GitHub身份、origin、工作目录/任务分支、git status、最新Issue21/PR和Issue15/PR17及评论/交接；运行verify.py对正式ZIP核SHA并重放事件（命令见工具README）。若继续全量重跑，使用记录的源码commit在新独立目录，避免把交付文档变动当原运行源码；不要覆盖run-01/replay-01。查看正式实验表和结论边界，先选择下一项可证伪问题再开独立任务。

目标平台历史：曾按官方Goals说明请求用户清除旧目标；用户已处理，上述阻塞已解除，无待用户操作。
