# Issue110交接：科学闭环完成，待root发布

仓库 https://github.com/rayggxia-workspace/LLMHardwareDesign；身份Liangruizhi/182389313；task/110-attention-width；D:/Projects/LLMHardwareDesign-attention-width。基线106 PR108@7a9fece；最终提交以本文所在commit为准。root负责push/PR/Issue和有权看板，不自行合并/done。

实际RTL fe9ee178、运行f066925、接收f144277/f8d1d56、最终验收归档3b974e1。三变体完整原102/106消费者、两等待全部24套输出/周期/物理事务/协议一致；原106→STYLE0及各变体真实proc-cell SAT/真实FF归纳、独立重建性质通过。34负例/反例和三变体×两模式selected actual raw gate通过。STYLE2 QK34/PV45逻辑125009.626µm²，对本批STYLE0 126029.470仅省0.80921%，无周期加速；旧106历史125966.694独立，不能混baseline。未做宏/STA/物理，不称整库完成；不修改106/109。

106本人Slurm已全部终态104完成、2个零秒调度失败原样保留。完整包87,834,705B/1616成员留授权服务器 `/public/home/yuzelu/RuizhiLiang/issue110-attention-width-20261025/delivery01/full-results.zip`，SHA e3be4dadd6018b5f9dd49a6d2c25d90add4f010bdd8641216bbb28863d96eccc。精选1,299,697B/540成员已入results/issue-110，SHA ea3f7b9560389c264e15036c9ff1d525aa8e777ee13ddc8810fe7a72b8f42206。服务器双包、PC精选及5phase320原Git源字节PASS；作业/原源/失败/命令见work110/execution.json与结果index。

四个建议远端字节读回入口：docs/experiments/issue-110-attention-width.md；project/experiments/attention_width/results/issue-110/index.json；同目录proof-receipt.json；同目录gate-receipt.json。主要比较门槛同目录paired-receipt.json也请读回。PR正文在work/Liangruizhi/110/pr-body.md。

恢复第一步：核最新AGENTS/Issue110/109/98/PR和成员55/63，不重复启动已结束106项作业；核git status和成果SHA、运行check_project。root审查后推本任务分支/PR并置in_review。登记PR5 pending，看板缺配置/read:project unverified/同步pending，管理员待指定。后续仅在新任务接入STYLE2并重新验证实际整合图；保留显式reset/limb不变量和原精度/错误合同。当前A仍materialized/caller committed snapshot；append/online、完整库/物理/产品定制仍未验。
