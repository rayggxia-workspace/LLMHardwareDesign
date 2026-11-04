# Issue162 continuation checkpoint86

更新时间：2026-11-05T01:04:53+08:00。YUZE-LU；[Issue162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162) / [Draft PR163](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/163)。承接[85](continuation-checkpoint-85.md)。**仍无完整整图零冲突、实际几何/PG及三档分布RC300MHz setup/hold/电气联合通过，继续任务、不合并。** 六宏/R256/S1350内部驱动、23类型138单块六文件、345状态宿主、453/S5380和外部R/其他任务边界保留。

source1496 `c43f06aa7ec21062165130cb3aa98f7d3d5acd68` 新增默认关闭的普通网占用惩罚增长：每4或8轮翻倍，上限256倍；只改变搜索代价。参考[VPR pres_fac_mult原则](https://docs.verilogtorouting.org/en/latest/vpr/command_line_usage/)，是独立整数实现，无代码移植。1498核对1028源/归档/四文件精确回退、原有限资源成本分支及全部selftest字节不变；1024其他源含RTL/固定宏/资源求解和全部最终门不变，通用fallback的native系数仍为原公式。source1508/1514/1526只修改回归刺激，生产代码与1496相同；各1028源/归档/单文件精确回退通过。当前冻结运行源1526为 `6c066dc2eb5cf11e500b62f08f480b0844798962`，归档SHA `397ee4691c74117b29dd35b6648408371a96d0b18c8967b30db82f5293c025f4`。

1500/1501的16原小图各全零，但没有第16轮后的实际细化，因此整体失败。15110/15111增加24交叉流仍缺覆盖；15180/15181的超容量负例被原容量门正确提前拒绝，也不满足晚轮覆盖。六份整体失败、全部原输出和门均保留。source1526保留超容量负例，另加顶点下界1750–1850、低于原2048容量门的独立压力刺激，未放宽任何门。实际15300/15301各20案例16零/4明确失败、18默认完整字节回放、16关闭新策略的实际guide字节回放、905/993多端点细化、7项拒绝、单轮失败及真实post16细化/实际增长系数通过。小图不授予全图资格。

15340/15341分别使用增长周期4/8，进入原七阶段。1535严格14规格/六键/当前453函数与各自未来几何PG三档RC路径通过；1536实际32份完整17字段输入头相对14030全部一致，主体/原native前缀一致，32实际进程及actualnode24六组互斥16CPU通过。两次动态准入依次为257GiB/322GiB预测，需要324.4GiB/402.4GiB实际可用；不是两次都322。真实回归finished早于各自准入的原文件/时间/SHA已保存。只经fresh specSHA/UID/job96222/actualnode24/PID/命令/源/453/全部日志/无最终输出/内存守卫替换本人7921/source790子步骤，原件及父节点保留。

现有CUGR/TritonRoute流程4项源与已实际通过的373预检逐字一致；15220将此已通过组件用于当前453/S5380，保留完整七阶段。1524严格7规格/六键/当前函数和各自未来物理门通过，1533核对实际11149连接、重构摆放与当前5380逐项一致、TCL确实执行CUGR50轮后TritonRoute/16线程、实际parser回归及node25六组互斥16CPU。它预测32GiB，使节点总320GiB需400GiB实际可用；若同槽放65GiB候选，总353GiB需439.6GiB，早先实际仅约414GiB。因此保留六槽并行并换用适合内存的已验证后端，没有降低门。旧359/CUGR3751未动。搜索marker/引导网格不是最终宏版图，必须通过实际导入/几何/native XOR/PG/三档RC300MHz后才可交付组合。

1502错误按64GiB估计旧6562，守卫在取消前拒绝；1503读回实际32GiB后，1504按node25的304GiB/380.8GiB、actualnode24的272GiB/342.4GiB重新核验才替换6562/7920。原失败保留。1533另按原SHA勘误1524继承的人类scope“warm-seed”措辞：15220实际是OpenROAD，无native warm导入，结构化七阶段/当前函数/未来门检查不变。1538只修正打包器对首个准入257GiB的错误期望，在已验证空的未完成86目录续包，不修改物理/准入门或原件。1536初次首轮未就绪拒绝，实际就绪后通过。

[2579份远程原字节](continuation-proof-86/index.json)与[49份辅助材料](continuation-proof-86/local-index.json)已按ZIP CRC/字节/SHA接收，实际暂存blob另行核验。8父节点36×16动态、两c96各六槽保留。继续全部声明组合最终六文件/版图/实际M11–M12/300MHz及源绑定交付，不在本检查点收尾。

规则rayggxia-project-collab1.0.0；Issue in_progress/PR Draft；登记PR5 pending，看板unverified/同步pending（无board.json），审查待指定。
