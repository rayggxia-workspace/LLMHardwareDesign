# 共享32KiB继续扩宽：评估完成待审

Issue247 / PR243，负责人Melodydt，2026-11-10 Asia/Shanghai。正式分支task/242-r-load-bounds；实验源码ffa5410be225037c7f13c3092c2ee3487fa07ec0。run33/job102011/mdt-prefill-width在c64/node1/4核执行10:33，COMPLETED0:0，passed=true、24cases。当前没有活动作业或自动监测。生产RTL未改动。

原prefill2/W8条件体系最高4.42958258026 token/s，未到5；64/128B双组交错完全同速，较32B仅+0.1450%（shared）/+0.6972%（idealdual）。后者服务已达到原M计算成本，进一步加速A被计算覆盖。旧5.0507/5.4549外推已由实测条件结果纠正。

8控制精确、7250原数值＋120定向数值、100生命周期负例、80事件负控、360主场景负控通过。99源/18输入SHA、全部392输出索引、172回收输出、独立重审及数值复算通过；原始事件未本地重放，保留服务器，不能把条件SystemC当原生RTL/物理验收。

报告docs/experiments/issue-247-prefill-width-evaluation.md；分析与独立复核work/Melodydt/247/shared-width；完整本地回收外层work/Melodydt/247/run33/receipts。服务器yuzelu@10.129.166.172个人/public/home/yuzelu/Melodydt/issue247-area-speed/run33，source/、slurm-102011.log、results/保留。result SHA e2887d8b137c7c4ca69d442586b26ac711427abf9ff26e5072a1a7115093de9b；receipts.tar SHA f858ad316e9a5522a80c8d20cc0efa663609f0d267a21b11aa473e25765d1205。

下一步：负责人Melodydt先读PR最新head与报告，安排独立审查；性能方向优先实际32B入口，继续扩大64/128无明显整图收益。如继续研究，重新定义M/输入ACK/非Dot范围，另建个人run并记录源码commit；不要重跑或覆盖旧run。当前in_review，PR未合并、不done。登记management-hub PR5 pending，无Projects工具/board配置，看板unverified/同步pending，审查人/管理员待指定。

追踪已结束作业：sacct -j 102011 -X --format=JobID,State,ExitCode,Elapsed,NodeList；查看results/result.json或日志。完整原始事件、生成模型和二进制留服务器；仓库仅分析及索引。未配置自动监测。

## 开始时回执（历史记录，作业现已完成）

# 共享32KiB继续扩宽：服务器评估接续

Issue247 / PR243，负责人Melodydt，2026-11-10 Asia/Shanghai。生产RTL未修改。当前分支task/242-r-load-bounds，实际实验源码commit ffa5410be225037c7f13c3092c2ee3487fa07ec0；10个新增源码文件已逐远端内容读回，静态生成10配置通过。

run33 / job102011 / mdt-prefill-width 已读回RUNNING，c64/node1/4核。登录yuzelu@10.129.166.172；工作目录/public/home/yuzelu/Melodydt/issue247-area-speed/run33，source/为实际源码，slurm-102011.log为日志，results/为持久输出。实际启动：在run33内执行sbatch --parsable job.sh；不重复提交。

本次计划20个pool32 prefill2/W8扩宽场景及4个pool0控制。每P入口16/32/64/128B，单64B服务和双64B组连续/交错映射，两种原本地端口层。旧16/32完整RESULT应精确回归；新数值/有限FIFO/真实选择时刻/分组冲突/双行消费必须通过。仍是S32/K256/S96条件体系，非原生整图RTL token/s或物理资格。

成功判据：Slurm COMPLETED0:0、results/result.json passed=true及24cases，8个run30控制逐字段相等，所有配置独立数值/事件/负控通过，源/输入/工具/输出SHA核验。作业受理、功能通过、性能结论及PR审查分开记录。

追踪命令（登录服务器后）：
```bash
squeue -j 102011
sacct -j 102011 -X --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n 40 /public/home/yuzelu/Melodydt/issue247-area-speed/run33/slurm-102011.log
cat /public/home/yuzelu/Melodydt/issue247-area-speed/run33/results/result.json
```

本地独立Git worktree在work/Melodydt/247/shared32-rtl/width-{runner,model,tests,audit}，正式完整副本为work/Melodydt/242/r-load-bounds/repo（非Git）；独立source-subset基线160a3de不作为上游commit。新正式源码位于project/experiments/shared_width_study。原生RTL及旧run原件保留。run33本地payload SHA a88a462d2f4be22f7bc2263665b5f35d8d6656f6c88cf55dd2a8281b9df99fc9，99源/18输入。

下一步负责人Melodydt：先读回作业终态；成功则运行collect_server.py回收并SHA核验，再用analyze.py和独立复核汇总token/s；失败保留原run，修复后另建run目录。不在本机或登录节点运行EDA。当前任务in_progress，未审查/合并，不done。登记PR5 pending；无Projects工具和board配置，看板unverified/同步pending。未配置聊天结束后的自动监控。


最新已核验的GitHub结构CI：报告提交a2e8dd0上的run42798032710与42798022115均failure；validate job129768121194 steps为空、runner_name为空，未取得CI通过证据，原因仍待仓库管理员核实。正式快照本地python scripts/check_project.py通过；它不代替CI或业务验证，也未绕过workflow。该限制不改变服务器run33已完成的独立结果。
