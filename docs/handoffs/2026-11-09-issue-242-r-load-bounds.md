# Issue #242：R LOAD 边界修复交接

更新时间：2026-11-09（Asia/Shanghai）；负责人 Melodydt。规则 rayggxia-project-collab 1.0.0。

- 仓库：`rayggxia-workspace/LLMHardwareDesign`；project_id `llm-hardware-design`；[Issue #242](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/242) / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。成果已在远端任务分支，待独立审查与合并，Issue 保持 in_review。
- 远端任务分支：`task/242-r-load-bounds`，从 main `c4d7b960599b9d292f27eb4429d5f226a7156c95` 建立。已测源码 commit `f034be2b7c87137b92f7bfce274a5485647e512d`；后续文档/证据提交不改变五个已测代码文件。
- 独立本地目录：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`。这是经 GitHub tree/blob 核对的任务源快照，排除 ref-project，并非本地 Git checkout；无本地 HEAD、暂存区或 CLI pull。发布经本人 GitHub 连接在任务分支创建 commit，未操作主干或他人分支。
- 本地任务根目录还保存 baseline、code-commit.txt、run01 打包输入/完整输出；辅助原始文件未上传。交付 allowlist 仅包含本任务 RTL、回归、文档及 work/Melodydt/242 轻量证据；以 PR changed-files 核对远端最终范围。

## 作业与验证

源码、工具、输入/输出 SHA 和详细覆盖见[实验报告](../experiments/issue-242-r-load-bounds.md)与[证据索引](../../work/Melodydt/242/README.md)。

- 登录目标：`yuzelu@10.129.166.172`。
- 工作/结果根：`/public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01`。
- 实际启动：`cd /public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01 && sbatch --parsable job.sh`。
- 作业：`101572_0-3`，名称 `mdt-rbounds`，c64，每例 4 核，最多两例并行；节点 node1，UNLIMITED。
- 终态：四项全部 COMPLETED 0:0；R256/R1024/C 适配器共 9/9 次正向通过，旧 main 三次均在 target0/index64 检出预期错误。无本任务活动作业。
- 日志：`slurm-101572_*.log`；结果：`results-raw256`、`results-raw1024`、`results-service256`、`results-negative`；完整包 `evidence.tar.gz`，SHA `949031ef34ed9b2dc5cd841c67df6b9c82284128adb24d75d722c8e88eab348b`。
- 管理结构及 Python 语法检查通过；输入源码及 12 份输出日志 SHA 核验通过。原有编译警告保留；同配置警告头无新增。未执行原 192 项最终网表回归及物理重新验收，旧物理资格仅绑定旧源。

```bash
squeue -j 101572 -o "%.18i %.16j %.10T %.20N"
sacct -j 101572 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -X
tail -n 25 /public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01/slurm-101572_0.log
cat /public/home/yuzelu/Melodydt/issue242-r-load-bounds/run01/results-raw256/result.json
```

## 恢复的第一步与待办

先用本人 GitHub 身份读取本 Issue、PR、main 及任务分支最新 head 和 changed-files，再读取本 Skill/AGENTS；不要根据旧摘要覆盖其他会话成果。原始非法 LOAD 无握手，直接使用者需预校验/撤回；协议层以现有 C 适配器显式地址错误为例。

1. 文档/证据已上传 PR #243，源码及文档证据提交分别为 `f034be2b7c87137b92f7bfce274a5485647e512d` / `ea9fcefbc166c649a36e17878823fdd1de29f766`，本交接后的链接回执提交不改源码。最终交付 head 与 CI 见 PR 实时记录；审查人待指定，本任务只有获得要求的审查并合并后才可验收关闭。
2. 物理实现负责人待指定：如采用新增保护后的 R 硬宏，应另行跟踪完整综合、最终网表功能、等价、STA/DRC 等物理重新验收；不能使用原六文件替代新源资格。
3. 管理员待指定：登记 [management-hub PR #5](https://github.com/rayggxia-workspace/management-hub/pull/5) 未合并，状态 pending。无 `config/board.json`，当前连接也无 Projects 条目操作；配置/查询获授权看板，复用或加入 #242，设置 Project ID `llm-hardware-design`、Status `In review` 及已确定优先级并读回验证。看板 unverified、同步 pending。
4. #232/PR233 和 #179/PR180 有各自未合并进度。若其先后合并导致个人 STATUS 冲突，应保留各任务入口，不能覆盖其他任务更新。本修复不处理 #232 另一处母控超时问题。

未创建自动监测；短回归已核验结束。后续审查或服务器状态由成员再次唤起检查。
