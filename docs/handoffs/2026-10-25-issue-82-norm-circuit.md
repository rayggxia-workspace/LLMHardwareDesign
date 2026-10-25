# Issue82 归一化与真实 M 消费者交接

2026-10-25 UTC+08，Liangruizhi/182389313。仓库https://github.com/rayggxia-workspace/LLMHardwareDesign；[Issue82](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/82)/[PR83](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/83)，task/82-norm-circuit，D:/Projects/LLMHardwareDesign-norm-circuit，base PR81@7ad23a73c49f199beed20f682decca897c4f487f。最终M执行源phase7=6b9a3f7b3b59bad1e335e018ef799265314e611c；冻结整理phase8=e0e845efbbed280e91bfa8d3bd755fe6539350bd；文档/最终交付commit以PR head为准。本任务独立提交，最终工作区状态/远端readback见PR回执。

已执行：三种同精度SFU/乘法方案、完整H1536归一化、raw权重/A单位的RTL合成与命令参数锁存、真实K512/8expert/H1536 down-M到完整merge/残差/norm。正式174命令及实际重SHA改码负例独立PASS；前序72条M命令按版本保留。100本人Slurm作业97完成/3M综合top错误失败保留，均已结束，无其他成员任务中断；PC24轻量检查通过。

重要结论：norm P0/P2为258244/61492 cycles，但当前完整链为9084871/8888119，仅改善2.166%，logic-only面积增26.44%，不能定4步SFU为默认。M喂数/协议主导；优先比较4096B A-cache及RQ乘法器复用，并保持资源/生命周期/端口/metadata和时序公平。不同PROFILE是制造版本，非免费互联配置。

成果：[报告](../experiments/issue-82-norm-circuit.md)、[规格/原型入口](../../project/experiments/norm_circuit/README.md)、[Blockv2第16节](../BLOCK_PARTITION_V2.md)、[统一索引](../../project/experiments/norm_circuit/results/issue-82/index.json)、[实际执行](../../work/Liangruizhi/82/execution.json)。全部计算只本人CPU服务器/public/home/yuzelu/RuizhiLiang/issue82-norm-circuit-20261025，lrz-i82-*；旧74/80只读，无新模型/软件/其他机器/Phi/成员接管。

完整包delivery03/full-results.zip，493855753B/1253成员，SHA256 b84301765a83eb37db7dfd04f5b3b84e53e079344d140843c7cf082556a6100d。精选3283478B/708成员在仓库，SHA256 f38b5e4eb9b2767a2c35a24fd51c3f789690e847fa60931d5aae93f5b0fbb505。服务器两包/PC精选与8phase150条原Git源码绑定已核；精选含收据和整数小样，完整M payload仍需服务器包。D:/Projects/Codex/norm-circuit-20261025-01保留可复查源码/轻量检查和接收记录。

未完成：目标SRAM/ROM宏/LEF/Liberty/PVT/时序/布局与功耗、一般K/H与多context、通用18函数V/ROM整合、fabric独立复位/CDC、全模型质量。M输入cut之前的router/SiLU/编码以及实际pack/DMA耗时不在RTL闭包；不把当前保守输入协议当最终平台带宽。

协作：Issue82交付in_review，不done、不自合并。审查人待指定；父PR81未合并。成员55仍in_progress/PR58 draft、63/PR79 in_review，接口工程由其继续。登记PR5 pending；board.json404，Projects实际查询缺read:project，看板unverified/同步pending，需要管理员明确配置并由有权限操作者读回，处理人待指定。本人身份不可改用其他账号。

恢复第一步：核最新AGENTS/Skill、Issue82/PR83/父81、成员55/63/PR79及交接，先接收索引和源码SHA，勿重复跑本批。新实验另Issue/分支/目录，以减少喂数/共享算术或提供物理时序资格为验收目标；不得用扩大精度、容量或免费端口制造收益。报告本地、远端上传、待审查合并和看板各自真实状态。
