# #270 FFN EXEC 单变量对照交接

2026-11-14（Asia/Shanghai）。Melodydt。[Issue #270](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/270) · [草稿 PR #272](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/272)。分支 `task/270-qwen-rtl-throughput`，本轮基点 `63781d3c7120f05b127d130c86e91e292feb09bc`，PR 基分支 `task/234-whole-system-throughput-handoff`。本机为资料副本，原生源码均在各自服务器作业目录。实验和补丁通过草稿 PR 交付。

服务器 `yuzelu@10.129.166.172`，工作根 `/public/home/yuzelu/Melodydt/runs/issue-270/ffn-exec-07`，均为 8 核 c64。原生归档及提交脚本的 SHA-256 已记录。生成脚本复用相邻 FFN 两轮的探针；执行前从这些轮次各回收 `prepare_native_probe.py`、`prepare_ffn_wait.py`、`audit_ffn_wait.py` 到工作根。

| 作业 | 节点 | 命令 | 状态 |
| --- | --- | --- | --- |
| 113742 | node7 | `sbatch --parsable run_ffn_exec.sbatch` | COMPLETED 0:0 |
| 113759 | node7 | `sbatch --parsable --job-name=zny-ffn-guard-b run_ffn_guard.sbatch base` | COMPLETED 0:0，54 项 |
| 113762 | node7 | `sbatch --parsable --job-name=zny-ffn-guard-c run_ffn_guard.sbatch exec` | COMPLETED 0:0，54 项 |
| 113850 | node3 | `sbatch --parsable run_ffn_exec_scoped.sbatch` | COMPLETED 0:0，正常和背压均核验 |
 
```bash
cd /public/home/yuzelu/Melodydt/runs/issue-270/ffn-exec-07
sacct -X -j 113742,113743,113744,113759,113760,113762,113850 -o JobID,JobName,Partition,AllocCPUS,State,ExitCode,Elapsed,Nodelist
tail -n 12 slurm-113850.out
d=run-113850/replay-113850
ls "$d"/{replay-*.log,ffn-wait.sha256,verified-proof.log}
bash finish_exec_pair.sh 113850
cat results/113850/sensitivity-{0,1}.json
```

后续每完成一个步骤都报告两项固定负载速度、证据范围和余下全部步骤。

113850 正常和背压分别核验了前序指纹、128 个 WAIT、事务及已提交字节散列。两模式 Gate/Up、Down 均慢约 11%，此轮调度归档为淘汰候选。沿用上一轮完整 TLM 基线 2.925996 tok/s 和 6.316164 输入 tok/s。

1. 完成 HEAD16 权重、M、读回、argmax 与退休归因。逐项 A/B 既有权重预取和输出/归约重叠，核对 151,936 列、并列选择和退休 token。短 Prefill 同步回归。
2. 重排热点，按测量决定 QKV/O 是否复用供数机制。补 ATT1 共享端口故障/背压/排空及分片取舍。
3. 冻结组合，做完整短程、原生联合及 300 MHz setup/hold、面积和资源回归。
4. 通过 PR #272 向 #234 交付，检查正式 B1/P512/D128 连续反馈、自生成 KV、数值、TTFT、吞吐与 J/token；独立审查及合并后完成 #270。

Melodydt 接续，Issue 进行中，PR 草稿，审查人待指定。规则 `rayggxia-project-collab 1.0.0`，项目 `llm-hardware-design`，登记 PR #5 待合并，因缺 `config/board.json` 由具权限维护者核验 Projects 及同步。
