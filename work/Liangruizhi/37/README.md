# Issue37架构先行、模型选型与实验设计

仓库rayggxia-workspace/LLMHardwareDesign，project_id llm-hardware-design；负责人Liangruizhi
（2663955430@qq.com，ID182389313，认证已核对）。[Issue37](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/37)。
独立task/37-gemma-phi-protocol，D:/Projects/LLMHardwareDesign-gemma-phi，base PR34@4a3f5e4；
临时公开元数据/HTML/脚本在D:/Projects/Codex/gemma-phi-20261023，无权重下载/其他机器任务。

用户中途强调先统一分析所有已提架构，再选型设计；据此停止原拟新增结构微测，
本轮只做metadata、静态源码阅读、逻辑容量和协议检查。没有执行任何新增神经网络推理。
方案docs/MODEL_ARCHITECTURE_REVIEW.md；正式catalog/config/plan/tools在project/experiments/model_selection。
17个变体、12份公开config，5份门控config保留HTTP401；没有用默认构造器/镜像补齐。
官方Gemma报告1024窗口与本地Transformers4.57.6构造器默认4096不同，说明运行前必须核真实config。

最新main0cc36f3已核README/AGENTS/project/协作/状态；PR26@2cd9ca15功能目录已读、评论为空；
PR34@4a3f5e4评论为空。Issue32仍由YUZE-LU优先Qwen修复，PR36只核标题/范围，未整合其结果。
不修改huangpingyang04-lgtm文档/进度，也不接管物理H2任务。

metadata接收脚本build_catalog.py使用本次D盘小文件快照重建目录；无需network/model imports。
配置来源不可变revision/URL/SHA在catalog.json，结果与源码绑定随后记录screen.json/checks.json/manifest.json。
业务检查仅协议/公式，不是模型“跑通”。登记PR5 pending；无board.json/Projects工具，看板unverified/同步pending，
处理人/审查人待指定；新模型执行仍须经过方案中的门槛和排期，不能从选型建议推定已获GPU结果。
