# Issue #222 下层对照计算完成交接

项目rayggxia-workspace/LLMHardwareDesign，执行账号huangpingyang04-lgtm，沿用task/222-qwen-native-coupling和Draft PR225。固定旧#206/#216；不混用#213/#214新底座。

2252983条已识别非边界网络全部达到本轮数值精度；点估计99.77%绝对变化≤1%，最大81.899%，独立完整场景约82.158%。2491条接口齐全、原整体矩阵逐行一致，17条精细面检查无超过5SE的已分辨差异。10个最大变化独立控制全过。见[主报告](../../work/huangpingyang04-lgtm/222/lower-rc/README.md)和[完整统计](../../work/huangpingyang04-lgtm/222/lower-rc/results/final-summary.json)。

先读取既有结果和SHA，不重复开启布线或全量提取。100838/100952的部分CANCELLED只是未启动任务迁移；101188的128/129在短回填时限超时，完整行12882条原样保留、只续4504缺项，101230成功，canonical结果仍在原remaining-production目录。100863、100864、100865、100908–100910、100879、100884均成功完成。

全量表116419804字节，保留在本人授权服务器；路径/SHA在[大文件索引](../../work/huangpingyang04-lgtm/222/lower-rc/results/artifacts-index.json)。源码、冻结输入、完整命令、退出状态及复用证据在[依赖记录](../../work/huangpingyang04-lgtm/222/lower-rc/complete-workflow.json)和[复用审计](../../work/huangpingyang04-lgtm/222/lower-rc/results/reuse-audit.json)。

后续第一步：独立审查比较表与完整场景极值证据，然后明确哪些变化涉及实际工作路径，再用更新参数检查速度。负责人与独立审查人待指定。输出是均匀介质/其他信号静止设置的金属电容比较；不是新节点级SPEF、新Liberty、器件/PVT或一般切换签核。不能用单线82%电容增幅替代宏延迟误差。旧时序原基线已有误判，须与新增耦合分开。

计算阶段提交in_review，Issue保持开放、PR保持Draft，不标done、不合并。规则rayggxia-project-collab 1.0.0；登记management-hub PR5 pending，缺board.json，Projects条目unverified/同步pending。GitHub结构CI此前失败且步骤为空，原因未确认；本地等价检查及Slurm数值检查单列，不冒称CI通过。
