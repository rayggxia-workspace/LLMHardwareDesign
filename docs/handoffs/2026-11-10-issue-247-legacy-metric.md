# Issue247 旧评价体系复评接续

2026-11-10T00:50+08:00（Asia/Shanghai）。负责人 Melodydt。仓库 rayggxia-workspace/LLMHardwareDesign，Issue247 / PR243，分支 task/242-r-load-bounds。本轮待独立审查，in_review，不done；PR未自行合并。登记PR5 pending；看板状态unverified/同步pending（缺配置和工具），管理员及独立审查人待指定。

正式本地非Git源码快照：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`。上传使用当前认证Melodydt的Git tree/commit/ref租约，不将非Git快照描述为checkout。新增运行器源码commit `3e62b85c8da19caca31784cb380c40d323295157` 已上传并读回；最终文档/证据head以PR读回为准，main未因本轮交付改变。服务器仍绑定该运行源码。辅助工作目录outer247/legacy-eval-plan、legacy-eval-audit、legacy-eval-analysis分开，root统一整合正式文件。

## 服务器运行与证据

本轮实际作业 **101800 / mdt-legacy-metric**，c64 / node1 / 4核，耗时 **00:03:22**，**COMPLETED 0:0**。源码 commit `3e62b85c8da19caca31784cb380c40d323295157`；源目录及输入以部署清单绑定。Python 3.10.12、g++ (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0、SystemC 3.0.2，C++17/O2/Wall/Wextra/Werror。运行在既有 ORFS 容器中，容器和 libsystemc 的 SHA 见 `tools.sha256`。

登录 `yuzelu@10.129.166.172`；目录 `/public/home/yuzelu/Melodydt/issue247-area-speed/run15`，源码 `source/`、日志 `slurm-101800.log`、结果 `results/result.json`。实际启动命令为目录内 `sbatch --parsable job.sh`，4核上最多4个并发case。没有本地或登录节点 EDA 仿真。

```bash
cd /public/home/yuzelu/Melodydt/issue247-area-speed/run15
squeue -j 101800
sacct -j 101800 --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n 40 slurm-101800.log
cat results/result.json
sha256sum -c output-files.sha256
```

- 21个完整场景全部执行；逐场景独立工作/流量/容量/端口审计及U参考通过。
- 原有225个kernel数值、4个validation、5个smoke通过；7个回执篡改、2个非法CLI、源码及历史结果SHA漂移均被拒绝。
- 新生成5个C++文件与run12 SHA完全一致；全部旧模型源、输入冻结。run05和run12适用场景全RESULT精确相等；run04仅新增policy元数据；run01所有原字段递归零容差核对，新增资源元数据另行审计。21个场景都有历史参考，不只比较token/s。
- 63份当前源码、16份部署输入绑定；75个服务器输出SHA、63个回收结果SHA、74份轻量原件。大二进制/生成源码保留本人服务器，仓库采用可逆压缩并同时记录原文和存储SHA。
- 主结果 SHA-256：`31213ac812866f463c8bd6e32a97d41e74e570b5310b6689f15e1e8fc6727cbc`。
- 管理结构检查通过只代表管理结构；完整原生RTL大模型、真实权重生成、模型质量、面积/STA/P&R均未在本次执行。


当前阶段：21场景旧体系复评已完成；[正式报告](../experiments/issue-247-legacy-metric-evaluation.md)和[轻量证据](../../work/Melodydt/247/legacy-metric-eval/README.md)待独立审查。W8 decode512基线3.063655，共享口ctx8=3.230811，理想端口ctx8=3.496169；prefill2扩容参考48/64KiB=4.467001/4.547434。当前4×1RW和S64不继承理想1R1W/S96资格；没有扩容实装、原生整图或物理验收。

恢复第一步：读回Issue247、PR243最新head/CI/审查，核对本地文件，再运行 `python -B work/Melodydt/247/legacy-metric-eval/verify.py`。该命令只读核验证据及源码，不重跑仿真；若重新实验，创建新run目录并按README/REMOTE_RULES提交Slurm，不覆盖run15。所有作业已终态，无自动监测；不因下一轮接续重复提交当前任务。

未完成：独立审查及合并（待指定）；CI原因与登记/Projects处理（有权限管理员）；真实bank并发地址/调度及完整原生模型另需明确验收。原生模型run14与旧体系run15是各自独立的评价口径，禁止把不同口径拼成版本加速/回退。
