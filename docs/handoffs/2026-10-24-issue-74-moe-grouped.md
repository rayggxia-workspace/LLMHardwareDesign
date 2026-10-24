# Issue74交接：整数MoE与同函数分组驻留

2026-10-24 UTC+08；负责人Liangruizhi。仓库https://github.com/rayggxia-workspace/LLMHardwareDesign；[Issue74](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74)/[PR75](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/75)。分支task/74-moe-grouped，base task/72-numeric-closure@88e9c4b2c3bb1b93b7155ba87ad11853e6c15512。归档phase10源码commit59c940cc7113a65dde2ff876bb4df84abae39202，数学/服务按原phase sourceSHA；最终文档commit取PR75最新head，不能当原执行源。

主目录D:/Projects/LLMHardwareDesign-moe-grouped，三个独立子worktree和职责见work/Liangruizhi/74/README。提交仅本任务及相关共同状态，未覆盖成员55/63/ref-project；交付后读回git status，后续新改动先辨归属。服务器/public/home/yuzelu/RuizhiLiang/issue74-moe-grouped-20261024，51 lrz-i74作业全完成，89448其他成员作业未动。全部实际模型/张量/服务只服务器，PC源码/微合成/元数据/字节；无新模型/其他机器/Phi解封。

实际结果：Granite0/13真实cut与旧条件model64参考逐码0差，8完整router→全部8expert→共同Q12宽merge→0.22真实残差→完整nextnorm独立PASS，24NPZ真实负例；局部误差和token42抵消保留，无整模型质量接受。552960宽RQ实际产品显式S8/字节carry正确；Falcon同g12驻留服务独立PASS/48实际负例，6label字节零差，近M条件完整链slots只省0.001007%–0.016005%，保留M/V映射自由。posthoc不支持提高midF20优先，无新格式试验。Granite grouped服务未执行。

成果索引project/experiments/moe_grouped/results/issue-74/index.json；原10phase/20源Git字节PASS。完整delivery01/full-results.zip 2,102,954,908B/505成员，SHA da4e49f2431924714c786bdc884b97443ed73aa60a23819e0543cfdd84fd02c7。精选selected.zip 8,170,748B/153 metadata，SHA a1a8796fdc50658f3ae7d4756989870d6af402f6a0624ec2fd650f1996addb54。两包服务器逐成员通过，精选PC再核；完整负例/数组留授权服务器，原70/72权重/输入按external_inputs取得。collector/验包后续收据不在原快照，单列索引。

本机63新、closure90/architecture_extensions80旧测试、check_project、diffcheck通过，命令和回执work74/validation.json；精选metadata不是完整math重放。复跑从work74/slurm实际argv和sources源胶囊，用既有环境、原来源和新out，不覆盖、不依赖已过期旧Slurm jobID。

下一步按用户最新要求继续Granite专家→merge有限容量端口/缓冲与宽算术/SFU/ROM校准。恢复/接续第一步：核本人Liangruizhi/182389313认证、最新AGENTS/Skill/Issue/PR/成员进度与服务器作业，验当前成果SHA，再建立明确后续Issue/独立分支，冻结最小数值函数与库存。只补影响边界的分叉，不能把Falcon服务当Granite服务或将候选微费用冒充RTL/时序。

未完成及处理人：Liangruizhi继续上述研究；整模型质量/冻结后Phi、RTL/布线/时序/PPA未验收，物理实现处理人待指定并与成员55/63协调。PR75/依赖PR73等审查人待指定，未经要求审查合并不done。管理中心登记PR5 pending；board.json缺失/无Projects能力，看板状态unverified、同步pending待管理员。常规已授权工作持续，不自行批准合并，不借他人凭据。
