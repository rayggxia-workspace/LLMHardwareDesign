# 383 六队列实际准入

Refs #121 / PR #122。选择R344→345→346、V380→381→382。控制代码源5a6e0be8，配置cdcfc85f。24个远端文件SHA、原归档及实际源Git blobs核验；正反控制通过。PID3315105的实际UID/cmdline/启动tick和两轮status读回见launch-readback.json及capture-start/index.json。

仅替换377轻量登录控制器；旧377 PID3065817经过身份核验后终止，无EDA取消。仅尚未分配的376退休；已运行375及R旧任务正常收尾。首次实际提交V380为93441，2026-10-29 13:38:26 UTC，后确认node17 RUNNING。前置378七检查及379七测量均实际通过。381/382仍等待真实前置，不能当作完成。

Issue121 allocation上限8，pending/unknown/旧实验/其他本Issue任务均计入；默认6×16独立槽即完即补，实际依赖与RAM预测×1.2+16GiB保留/liveRSS约束。首次准入观察已有6个本Issue allocation，提交380后7个；无关feed任务不操作。调度与文件准备不构成最终资格。
