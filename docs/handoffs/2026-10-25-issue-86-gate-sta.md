# Issue86交接

仓库https://github.com/rayggxia-workspace/LLMHardwareDesign；负责人Liangruizhi；task/86-gate-sta，D:/Projects/LLMHardwareDesign-gate-sta。独立基线Issue84@049a8a6，冻结phase8@42706e1；最终文档commit以实际git HEAD为准。主会话统一push/PR/Issue/看板，本子任务未推送、未开PR、未合并。

八条完整消费者门级回归及独立整数/协议/variant接收PASS；四变体两负载的存储切分STA完整覆盖DFF，无check_setup缺项，但数千slew/cap违规、全逻辑时序未收敛。详细报告docs/experiments/issue-86-gate-sta.md；results/issue-86有精选/index/数学接收/字节及原源接收，work/Liangruizhi/86有34作业命令与最终结束状态。完整19.16MB包及原84输入依赖留本人授权服务器。未修改Issue84/85/55/63。

未完成：电气修复和新增面积验证、目标SRAM/ROM/PVT/RC/CTS/布局、门级全状态形式等价、85新硬件时序、一般M/A/R和系统状态协议。不能把未修复诊断周期或参考Nangate视图称目标Fmax/物理验收。

恢复第一步：核最新AGENTS/Skill、Issue84/85/86及关联PR/成员55/63；接收本轮索引和源码SHA后，另任务在独立目录对同一四变体高扇出/尺寸进行有约束修复，再全函数gate重放并测面积/STA。保持存储切分和电气违规显式，未有合法宏前继续标完整核物理资格未验。所有i86作业已结束；本目录无未提交改动的最终状态须以交付git status为准。审查/管理员待指定；登记PR5 pending、看板配置/read:project缺项由主会话核最新后同步。

后续已认领[Issue88](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/88)，独立task/88-electrical-repair/服务器新根，按同cut/负载有界修复并验证所有新增面积；不是目标工艺签核。Issue86当前交付以PR head为准，源码历史SHA保留。

远端交付：[PR90](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/90)已上传，Issue86为in_review，待指定独立审查与合并；按不可变commit读回报告/交接/个人进度与原Git blob一致，后续仅文档同步。
