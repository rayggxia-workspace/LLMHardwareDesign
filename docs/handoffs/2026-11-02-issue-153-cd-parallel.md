# C/D平行实验接续

Issue153/PR154；分支task/153-systemc-llm-inference；起点7bfa3cff40c24f5bfde43392737af12b315dfaa4。负责人YUZE-LU。


## 2026-11-02：C/D平行实验阶段1

按用户要求新增project/systemc/llm_cd，与llm平行，原实验代码/数值门/证据不改。复用真实SystemC C/D模型，新增经16KiB S的载荷通路和32KiB固定外存窗，C实际SUBMIT/WAIT控制LOAD/STORE。最终phase06 -Werror/UBSan 2/2 CTest通过：三发送者27窗口/54完成，数值selftest479窗口/958完成；输入SHA、control源快照和原始日志见llm_cd/results/phase1。设计/命令/失败/结果/边界持续记录在llm_cd/README.md、EXPERIMENT_LOG.md。

这是外层Tensor边界的C/D搬运接入；权重、KV/R原始状态和计算命令调度仍走host。七真实模型九位置尚未用新通路重跑，不追认此前数值资格。R按本次授权继续作为SystemC实验内容，不修改RTL生产发射。后续先补宏命令适配与真实权重/状态通路，再重跑三组合/七模型冻结门；不能把阶段1作为整系统/物理/性能通过。

恢复入口：阅读project/systemc/llm_cd/EXPERIMENT_LOG.md及results/phase1/receipt.json，先核对执行源SHA。生成副本由run.py建立，不编辑原llm程序。独立审查人待指定，不自合并。登记沿用PR5 pending证据；无board.json/Projects条目工具，看板unverified/同步pending、管理员待指定。
