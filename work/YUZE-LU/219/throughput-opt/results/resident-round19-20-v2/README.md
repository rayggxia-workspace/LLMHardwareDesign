# Issue219 / PR220：迭代19–20证据

本包是冻结检查点，包含通过记录、失败记录及未结束作业的部分回收；不是完整模型或系统验收。
结果解释见 [迭代19](../../ALGORITHM_ROUND_19.md)、[迭代20](../../ALGORITHM_ROUND_20.md)。

`evidence.tar.gz` 为去重审查包，8,203,588字节，SHA-256：
`99698e24be9e3ec9e7c76a2befaa760ef150f158cb08c3f84ce4074537f28cea`。
473个实际成员、2350个精确重复文件和两个最终IR增量均有索引；恢复工具不会覆盖不同内容。

完整原始包保存在获授权项目存储：
`yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/resident-evidence-19-20-0244d3fad73bdfac.tar.gz`。
52,868,971字节；SHA-256：`0244d3fad73bdfaca300aa004dab893097e886249267e20a106e3a3d67e6daf6`。
上传后已在服务器重新计算并核对SHA；完整2861个成员索引见 `raw-index.json`。
过时的展开RTL探针和未使用的大IR仅在完整包保留，不把其编译终止记录算成通过。

在新目录解开审查包后执行：

```text
python work/YUZE-LU/219/throughput-opt/restore_resident_evidence.py PACK/manifest.json EXTRACTED ROUND18_IR
```

`ROUND18_IR` 是此前迭代18包中的 `cover-compare-v1/conditional_reuse/ir.json`，
SHA-256 `3fff3712f59ff04eedd491fe87fd913a7487fd34a01203eaf3afdd70e212165c`。
迭代18包SHA-256为 `e5cc481e76b61fc79cb0f66dfe91d069deb933154dd4dc32bfe8a9b0b9ada93b`。
`dp-ir-overlay.json.gz` / `greedy-ir-overlay.json.gz` 可逐字节重建两个最终IR。
本机已在独立新目录实际解包、恢复并逐项SHA检查全部473+2350文件和两个IR，通过。

`overlap-audit.json`、`row-audit.json`、`row-qualification.json` 是独立审计及原生行服务回执。
原始日志、输入、冻结源包及负向案例位于解包后的 `round19/`、`round20/`、`server/`；
精确名称以 `manifest.json` 为准。服务器作业运行中的快照不代表终态，后续回收需另记。

实证边界：305项Windows/Linux测试；288个原生行案例×三初态；重叠计划独立检查及原程序边界RTL；
两/四行冷tile独立有限S数值。完整新批程序RTL、真实权重批元素、整循环、全图重编译、
KV decode、校准SystemC、DRAM、能耗及token/s均未由本包证明。
