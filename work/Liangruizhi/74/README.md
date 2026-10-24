# Issue74 实验记录与接收

[Issue74](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/74)/[PR75](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/75)，负责人Liangruizhi/182389313。主目录D:/Projects/LLMHardwareDesign-moe-grouped、task/74-moe-grouped，base PR73@88e9c4b。三个独立子worktree为D:/Projects/LLMHardwareDesign-74-granite、-74-service、-74-audit，对应task/74-granite-chain、task/74-grouped-service、task/74-independent-audit。子工具合入任务分支，未修改成员55/63或ref-project。

正式工具project/experiments/moe_grouped，[报告](../../../docs/experiments/issue-74-moe-grouped.md)、[索引](../../../project/experiments/moe_grouped/results/issue-74/index.json)。全部实际模型/张量/服务本人服务器/public/home/yuzelu/RuizhiLiang/issue74-moe-grouped-20261024、Slurm lrz-i74-*。PC临时仅D:/Projects/Codex/moe-grouped-20261024-01，源码/微合成/JSON/字节接收。既有70/72输入和权重只读，无新下载/其他机器/Phi解封。

sources/phaseN-staging.json记录10phase原commit、每源SHA、source.zip大小/SHA；slurm/*-submit.json为51实际参数列表/Slurm argv和jobID。依原phase源复跑且out换新，不覆盖；Bash环境OMP/MKL/OPENBLAS1，capture threads8。c96无--mem，因站点RealMemory1MB配置，不改调度器。原stage1采集、2wide、3compile/run、4Granite接收、5调试服务、6正式服务、7独立服务接收、8posthoc、9独立配对、10归档/字节验证；旧phase5不排名。

51作业全COMPLETED，真实sacct记录见结果final-slurm.json。8数学/12服务独立PASS、72实际SHA重写负例、6label零差；compile/FP诊断和runtime整数边界分开。新63、相关旧90/80小型测试和管理结构通过，提交前diffcheck记录validation.json。完整包2,102,954,908B/505成员，精选8,170,748B/153；两包服务器逐成员、精选PC再验，10phase/20原Git源字节PASS。

collect.py与collection-config.json明确白名单，仅本任务目录/48既有日志，含全部原source/capture/NPZ/真实负例及调试pilot；不含权重/cache。collector/验包自己的后续3日志/收据在快照之外，由final Slurm和独立接收回执索引，不能声称在自己早先归档内。verify_sources.py只核原Git字节，不做模型/数组数值。

Granite官方两shard/config/index SHA来源见granite-download-receipt.json和granite-source-verification.json。原72/70来源由collection-config及统一索引external_inputs指定，不能因新包可解压而省掉旧输入。全部大文件留本人授权服务器，仓库精选不是完整数学数据替代。

本批通过PR75交付待审查，不自行合并或done。登记management-hub PR5 pending；config/board.json返回404且无Projects能力，看板unverified/同步pending，管理员/审查人待指定。用户新要求的Granite有限expert→merge服务及wide/SFU/ROM校准作为后续明确任务继续，不把这些写为本批已完成。
