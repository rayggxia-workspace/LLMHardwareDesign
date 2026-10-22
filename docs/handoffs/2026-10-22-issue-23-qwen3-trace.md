# Issue23 真实权重轨迹工作入口

仓库rayggxia-workspace/LLMHardwareDesign，负责人Liangruizhi，身份2663955430@qq.com/182389313。[Issue23](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/23)，分支task/23-qwen3-trace，独立目录D:/Projects/LLMHardwareDesign-inference，base PR22/adf077d04a5f0a3cc2ae13b77f16371bb637591d。当前新增代码/辅助文档尚待源码冻结上传与正式运行；PR尚未创建。

持续研究Goal已active；本阶段不完成整体目标。官方8文件已在D:/Projects/Codex/qwen3-inference-20261022/environment/weights/下载并验证，权重1503300328bytes、SHA f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b，其余SHA见work/Liangruizhi/23/model-download-manifest.json和实验配置。隔离环境安装CPU包，导入和模型实际运行状态以后续真实记录为准；此刻未执行正式模型。下载不是模型已跑通。

正式目录project/experiments/qwen3_trace/；experiment.json冻结输入、版本和误差阈值。numeric模块由独立numeric-runner目录交付，trace/run由root编写；另一agent只读接口审查，resource agent独占environment目录。并行未写同一工作树。所有临时目录D:/Projects/Codex/qwen3-inference-20261022/，不清理他人文件；保留仍有用途的数据/环境。

下一步：核对最新Issue/PR与指定身份、git status；等环境导入/CPU检查后跑随机小模型协议与observer异常恢复测试；完成审查后上传清洁源码commit，再运行固定真实权重（run.py拒绝dirty与覆盖输出）。保存包括失败的输入、结果、日志、源码/依赖/数据SHA；不可只挑成功。

Issue15物理收敛不重复：最新观察PR17 head6b3fe103，split07/merged06仍full-hierarchy失败，12轮仅提交回执。实际终态继续由负责人处理。登记management-hub PR5 pending；本地无board.json及Projects工具，在线状态unverified/同步pending，管理员待指定。恢复先查实际远端状态，不将本文件视为看板同步。

运行前进展：环境25个runtime wheel已逐源SHA核对、离线require-hashes安装成功，pip check/CPU原生Qwen3导入通过；6个数值协议测试及随机小模型196事件/异常恢复集成通过。源码/API独立审查已关闭8文件绑定和status schema问题，无阻塞项；官方真实权重尚未运行，先冻结干净源码。依赖安装曾遇D盘pycache长路径预编译警告（安装exit0），保留日志；后续统一-B，不更改系统配置。
