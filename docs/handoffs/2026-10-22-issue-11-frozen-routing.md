# Issue #11 冻结连接实验交接

- 日期：2026-10-22，UTC+08:00；Liangruizhi／2663955430@qq.com。
- 仓库：rayggxia-workspace/LLMHardwareDesign；project_id=llm-hardware-design。
- [Issue11](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/11)／[PR12](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/12)，分支task/11-frozen-routing-pilot，未审查／未合并。实际运行源码commit `6ab796b3f6e754aa30c79ab91bb2795f6a6f056c`；后续归档提交以PR当前head读回，不反写运行输入。
- 独立工作目录：D:/Projects/LLMHardwareDesign-dac。原目录D:/Projects/liangruizhi仍在Issue5分支，未切换或修改。当前提交后是否有新改动先执行git status核对，不覆盖其他会话。
- 正式代码：project/experiments/frozen_routing/；正式结果：其results/issue-11-run01/；原始开发／运行／图表副本在忽略的local_runs/。项目研究计划docs/DAC_RESEARCH_PLAN.md；实际实验docs/experiments/issue-11-frozen-routing.md。
- 实际结果：192例，顺序32/96、多顺序44/96，76解全局合法、81次数值通过；24小例中15可行／9不可行，所有精确结果与启发式成功解一致。17项业务检查、管理结构、全量hash读回及连接重放通过。部分固定映射无白名单路径，其余失败仍未知。
- 原始manifest SHA256 f1b67f4fde2daea3d1d15d62e08348a73ef21d6bbe0c9467fd2b95b51fa030cd；raw-evidence.zip SHA256 a87b746333ab72eb59c3d971bb98f7d58d658152606207d2831831417d748e9b；其他值见实验记录。未运行本地EDA／物理H2／STA／LEC／真实LLM。

## 恢复第一步

1. 用本人的Liangruizhi身份重新核对远端Issue11、PR12及PR8/10/6；读取最新AGENTS、Skill、状态和此交接。核对当前目录与branch，避免重复任务和重复PR。
2. 运行package.py --verify核对归档；在新local_runs目录解包后运行verify.py --replay。所有旧attempt保持不变，新增实验记录当时真实commit与配置。
3. 审查本PR的模型与基线局限。下一研究任务应先明确宏资格与真实端点校准，或预声明端点感知映射的受控对照；另立Issue，不直接覆盖Issue7的VECTOR/PG或并行电容修复工作。处理人待指定。
4. 本地是认证API建立的浅层稀疏副本，未取ref-project/sources及更早历史；省略路径保持跟踪。CLI本人认证未接通，远端写入使用已核验插件，不借用其他账号，不声称普通CLI clone/push已执行。
5. 管理中心PR5在本轮仍OPEN，默认registry未登记：pending。复用已有PR，待有权限审查者处理。
6. Projects事实unverified／同步pending：插件无Projects工具、本项目无board.json。具备权限和工具的管理员（待指定）核验组织看板1及受众，查询Issue11条目，复用／加卡，按实际status同步Project ID=llm-hardware-design及已明确字段，读回条目ID／链接／状态／时间后补证据。没有优先级或截止日期时不猜填。

本任务保持in_review直到项目要求的审查、合并和验收完成。DAC官方窗口仅作研究规划，未提交会议、未承诺届次或录用；VPNA作者稿已有高度相关先例，不能把当前工具正确性当作新颖性或把其预制三态分时共享判为非法。
