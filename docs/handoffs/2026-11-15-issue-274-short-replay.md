# Issue #274 七模型短程回放交接

2026-11-15（Asia/Shanghai）。任务由 Melodydt 负责，使用 [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 与 [草稿 PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275)，目标仓库为 `rayggxia-workspace/LLMHardwareDesign`。任务分支 `task/274-seven-model-short-throughput` 自 PR #260 的 `55620f173f2ad540efade8a552c35e9dba0f43c0` 建立。已上传七模型回放脚本及首份审计的提交为 `f326d94a89485a210ed9ac7e7dad2fa4819a7395`，后续实测见 PR 分支最新 [结果索引](../../work/Melodydt/274/RESULTS.md)。

本机任务工作文件位于 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/274`，当前本机目录为无 `.git` 的工作副本，任务使用 GitHub 的 Melodydt 连接更新远端任务分支。Llama 原始检查点本机临时副本仅用于上传及校验。原始 checkpoint、权重映像、作业输出与运行副本均保存在授权项目服务器，未加入 PR。可复用数据用各阶段 `output.sha256`、`reference.sha256` 和 `receipts.sha256` 校验。

服务器登录 `yuzelu@10.129.166.172`，任务根 `/public/home/yuzelu/Melodydt/runs/issue-274`。作业 `115055` 已完成并核验，两步词表 token 与零历史 FP32 一致。七模型后续当前结果按 [结果索引](../../work/Melodydt/274/RESULTS.md) 更新。成功判据为相应 Slurm 步正常退出，两个位置覆盖全层，Decode 两次全词表退休且第二步输入为首步结果，DDR 回调和跨步状态全部对账。数值对照与候选周期另记。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-274
J=115055,115056,115103,115109,115122,115124,115125,115126,115128,115129,115130
squeue -j "$J"
sacct -X -j "$J" --format=JobID,Partition,State,ExitCode,AllocCPUS,NodeList,Elapsed
tail -n 5 qwen3-short-fast-01/run-115055/{prefill,decode}.log
sha256sum -c qwen3-short-fast-01/run-115055/output.sha256
```

恢复第一步是读回作业状态与日志，按结果索引中的目录核验每个阶段成功退出、数据散列与 `audits/` 报告，再更新 #274、PR #275 和个人进度。管理结构和 Python 编译已通过。RTL 与物理时序验证目前待完成，独立审查人待指定。登记沿用 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) pending，项目缺 `config/board.json`，由具备 Projects 权限的维护者核验任务卡和字段并同步。仿真保持 Slurm 独立运行。
