# Issue247 U 队列与 NExp 区域可执行交接

负责人 Melodydt；仓库 rayggxia-workspace/LLMHardwareDesign；Issue247 / PR243。
远端分支 task/242-r-load-bounds；原生源 0109de8555cda51ee73498f9966df69cb550ba19，模型源 e6b2c31f1a593ee9393be0088f90c9d762622e94。
本地正式快照 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo，非 Git 工作树；由 Melodydt 连接以 Git tree/commit 和 expected_sha 更新远端。
本轮根代理独占 U/新实验文件，未改其他 worktree 或 ref-project。文档交付 commit 见 PR；main 未合并本轮。
本地辅助目录 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/247；报告 docs/experiments/issue-247-u-queue-native.md，PDF 位于 docs/experiments/pdf/；证据 work/Melodydt/247/u-queue-native。

run44/job102083 FAILED1:0，原因见 failed-run44.json；run45/job102084、run46/job102092 已 COMPLETED0:0，c64/node1/4核。
服务器 yuzelu@10.129.166.172；运行根 /public/home/yuzelu/Melodydt/issue247-area-speed/run45 和 run46；代码 source/，日志 slurm-<job>.log，结果 results/result.json；完整文件 output-files.sha256。
提交命令在各根执行 sbatch --parsable job.sh；恢复查看：sacct -j 102084,102092 -X --format=JobID,State,ExitCode,Elapsed,NodeList，tail -n 30 对应日志，cat 对应 result.json。
成功判据：退出0:0、result.passed=true、195原生/6面积/27默认对、40模型/16完整控制/200负控、SHA及日志RESULT核验；本轮均满足。

恢复第一步：读取 AGENTS/Skill、最新 Issue/评论、PR/CI 与远端 head，核对本地快照和文件范围，再读本轮分析；不能把旧本地副本当远端最新。
后续由 Melodydt 推进原图 S32 E 子集或真实量化合同、两槽 U 区域以及本地 S 仲裁连续请求。量化尺度和激活值待提供/确认，禁止直接截短S32。
未做：全图 RTL、真实模型推理质量、全 U/芯片综合面积、STA/P&R、300MHz物理验收、正式审查合并。队列参数默认0；NExp需要caller暂存和尺度声明。
CI42858846633 failure、validate无steps/logs，具体原因待管理员核实；不绕过。登记PR5 open/unmerged pending；无board配置及Projects工具，看板unverified/同步pending，处理人待指定。
本地实现/服务器验证完成，远端交付经PR待审；Issue in_review，未合并/not done。没有活动作业或自动监测，需用户再次唤起检查。
