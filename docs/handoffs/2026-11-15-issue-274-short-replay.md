# Issue #274 七模型短程回放交接

2026-11-15（Asia/Shanghai）。任务由 Melodydt 负责，使用 [Issue #274](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/274) 与 [草稿 PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275)，目标仓库为 `rayggxia-workspace/LLMHardwareDesign`。任务分支 `task/274-seven-model-short-throughput` 自 PR #260 的 `55620f173f2ad540efade8a552c35e9dba0f43c0` 建立。已上传七模型回放脚本及首份审计的提交为 `f326d94a89485a210ed9ac7e7dad2fa4819a7395`，后续实测见 PR 分支最新 [结果索引](../../work/Melodydt/274/RESULTS.md)。

本机任务工作文件位于 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/274`，当前本机目录为无 `.git` 的工作副本，任务使用 GitHub 的 Melodydt 连接更新远端任务分支。Llama 原始检查点本机临时副本仅用于上传及校验。原始 checkpoint、权重映像、作业输出与运行副本均保存在授权项目服务器，未加入 PR。可复用数据用各阶段 `output.sha256`、`reference.sha256` 和 `receipts.sha256` 校验。

服务器登录 `yuzelu@10.129.166.172`，任务根 `/public/home/yuzelu/Melodydt/runs/issue-274`。七模型两个阶段均已通过回放审计。512-bit SRAM 和程序存储写宽已逐个核对冻结源码，详见 [结果索引](../../work/Melodydt/274/RESULTS.md)。所有任务作业均已到终态。三个批作业包含失败的 Decode 步，表中引用其成功的 Prefill 步及另行成功的 Decode。回放成功判据为对应 Slurm 步正常退出，两个位置覆盖全层，Decode 完成两次全词表退休并实际反馈首步 token，DDR 回调和跨步状态对账。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-274
J=115055,115056,115103,115109,115122,115124,115125,115126,115128,115129,115130,115197,115250
squeue -j "$J"
sacct -X -j "$J" --format=JobID,Partition,State,ExitCode,AllocCPUS,NodeList,Elapsed
tail -n 5 qwen3-short-fast-01/run-115055/{prefill,decode}.log
sha256sum -c qwen3-short-fast-01/run-115055/output.sha256
```

若继续推进数值资格，由 Melodydt 从 `audits/` 的首次分歧入手，复用 115197 的 Granite 路由及 115250 的同输入 FP32 对照。Gemma 的残差饱和、候选 GDN/Mamba2 时序与数值、独立 RTL 和物理时序校准均有待处理。项目结构、Python 编译、冻结脚本 Bash 语法、来源及输出清单核验通过。独立审查人待指定，登记沿用 [PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) pending。项目缺 `config/board.json`，由具备 Projects 权限的维护者核验任务卡和字段并同步。

## 优化回放续办

七模型优化作业 `115262`、`115282–115288` 均已结束并核验。冻结的源码目录、全层 A/B、SHA-256 及追踪命令见 [优化记录](../../work/Melodydt/274/OPTIMIZATION.md)。恢复时先核验 PR #275 当前 HEAD 并读回对应服务器运行的 `output.sha256`。本次保留草稿和 Issue 进行中状态，尚需数值及 RTL 校准时使用上节的独立参考。

## PR #272 调度重测交接

任务分支已上传接入代码 `209482b226456a7fdc328692470b26ef42ac05e6`。本地报告位于 `work/Melodydt/274/PR272_RETEST.md`，Run 与审计在原任务根的 `pr272-tlm-01/run-115340` 至 `run-115346` 和 `audits/pr272-*-full-*.json`。原生结果见 `pr272-native-01/native-audit.json`（115329/115330）和 `pr272-ffn-native-01/native-ffn-audit.json`（115347）。所有这些作业均为 COMPLETED 0:0。115325/115326 的依赖缺失失败由后续两次 C380 重跑替代，原回执保留。

```bash
cd /public/home/yuzelu/Melodydt/runs/issue-274
sacct -X -j 115329,115330,115340,115341,115342,115343,115344,115345,115346,115347 --format=JobID,State,ExitCode,AllocCPUS,NodeList,Elapsed
sha256sum -c pr272-tlm-01/run-115340/output.sha256
```

继续时先读 [PR #275](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/275) HEAD 和[逐模型重测回执](../../work/Melodydt/274/PR272_RETEST.md)，核对冻结的程序与双阶段输出。由 Melodydt 从既有 FP32 结果定位剩余分歧，整模型 RTL／物理校准待安排。若要评估 ATT1 单独接入，当前冻结脚本已有 `:attention` 入口，可在同一映射和输入上独立复跑。审查人待指定。登记 PR #5 pending。项目仍缺 `config/board.json`，由具权限维护者配置、核验实际任务卡及同步字段。

## 三 P 调度与代表性历史续办

源码继承 `fc1327ec4d3a27bcea00a04cc0e6c4e6942fd05c`，服务器运行目录 `three-p-full-01`。请优先核验 115617/115618/115619 的真实状态和结果散列。先生成同模型、同输入上下文的逐层 FP32 对照，区分原候选的算术误差与三 P 分片引发的变化。复跑命令和未完成项见[全层作业索引](../../work/Melodydt/274/THREE_P_LIVE.md)。Melodydt 续办数值修复与吞吐验收。
