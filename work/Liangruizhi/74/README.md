# Issue74辅助记录

Issue https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74；负责人Liangruizhi/182389313。根D:/Projects/LLMHardwareDesign-moe-grouped/task/74-moe-grouped，base PR73@88e9c4b；独立子D:/Projects/LLMHardwareDesign-74-granite/task/74-granite-chain，-74-service/task/74-grouped-service，-74-audit/task/74-independent-audit。正式代码project/experiments/moe_grouped，原closure/architecture_extensions只读复用，其他成员55/63不接管。

server /public/home/yuzelu/RuizhiLiang/issue74-moe-grouped-20261024，lrz-i74-*。全部实际模型/张量/服务走Slurm，PC临时D:/Projects/Codex/moe-grouped-20261024-01，只源码/微测试/元数据字节。既有70/72数据与权重只读复用，不重新下载。协议先冻结再执行，分phase commit/SHA与独立输出，不覆盖旧证据。

当前进行中，真实结果尚未生成；阶段源/Slurm/收据/失败/成果位置与SHA随后更新。登记PR5 pending；无board.json/Projects能力，看板unverified、同步pending，管理员/审查人待指定。未验收合并不done。
