# C/D平行实验接续

Issue153/PR154；分支task/153-systemc-llm-inference；起点7bfa3cff40c24f5bfde43392737af12b315dfaa4。负责人YUZE-LU。


## 2026-11-02：C/D平行实验阶段1

按用户要求新增project/systemc/llm_cd，与llm平行，原实验代码/数值门/证据不改。复用真实SystemC C/D模型，新增经16KiB S的载荷通路和32KiB固定外存窗，C实际SUBMIT/WAIT控制LOAD/STORE。最终phase06 -Werror/UBSan 2/2 CTest通过：三发送者27窗口/54完成，数值selftest479窗口/958完成；输入SHA、control源快照和原始日志见llm_cd/results/phase1。设计/命令/失败/结果/边界持续记录在llm_cd/README.md、EXPERIMENT_LOG.md。

这是外层Tensor边界的C/D搬运接入；权重、KV/R原始状态和计算命令调度仍走host。七真实模型九位置尚未用新通路重跑，不追认此前数值资格。R按本次授权继续作为SystemC实验内容，不修改RTL生产发射。后续先补宏命令适配与真实权重/状态通路，再重跑三组合/七模型冻结门；不能把阶段1作为整系统/物理/性能通过。

恢复入口：阅读project/systemc/llm_cd/EXPERIMENT_LOG.md及results/phase1/receipt.json，先核对执行源SHA。生成副本由run.py建立，不编辑原llm程序。独立审查人待指定，不自合并。登记沿用PR5 pending证据；无board.json/Projects条目工具，看板unverified/同步pending、管理员待指定。


## 2026-11-02：C/D平行通路七模型最终数值通过

更新时间：2026-11-02T12:20:23+08:00（UTC+08:00）。[Issue153](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/153) / [PR154](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/154)，负责人YUZE-LU。独立目录project/systemc/llm_cd保留原实验，复用PR146 SystemC C/D及原S，新程序真实LOAD/STORE运输外层Tensor。95069/node1自然COMPLETED/0:0（19:13），六个单线程任务动态补位，七真实模型各9位置全部Top1/独立greedy/冻结hidden和logits门通过；不是追认旧结果。95083独立封存审计自然COMPLETED/0:0（51秒），本地重算63位置及24编译源绑定均通过。C累计3,120,438项提交与完成完全一致。两次构建失败原日志保留，未放宽-Werror或数值门；本地UBSan 2/2，服务器Release明确无UBSan。

正式入口：project/systemc/llm_cd/README.md、EXPERIMENT_LOG.md、results/seven-cd-03/index.json。执行源包492e30e2、二进制ed4dfb27，全SHA及原始validation/命令/源/输入/输出绑定在索引；大数据仍在授权服务器。本轮代码/文档/证据继续提交同一PR，不修改其他工作树或作业，不自合并。

边界：此轮通过外层Tensor搬运，静态权重、KV/R原始状态与计算任务发射仍由host承担；双S、AXI错误排空/复位、计算块旁适配器以及真实系统性能/物理互联未由本轮验收。R按授权继续参加SystemC推理，不改RTL生产选择；不能替代PR163的RTL/物理证明。

下一步：独立审查本轮源绑定、有限资源及数值证据；若继续硬件化主机职责，复用PR163 ABI，逐项接入权重/状态和计算适配器。Issue保持open/status:in_review，PR仍Draft，独立审查人待指定。规则rayggxia-project-collab1.0.0；登记沿用PR5 pending证据、本次未重核；无board.json/Projects条目工具，看板unverified/同步pending，管理员待指定。恢复时先运行verify_evidence.py重算七模型门，再核对当前PR head和交接；勿把旧阶段1尚未重跑的记录当当前状态。
