# Issue247 PDF 与新版 token/s 接续

2026-11-09，Asia/Shanghai。负责人 Melodydt；Issue247 本轮交付in_review，PR243 open/unmerged，审查人待指定。仓库 rayggxia-workspace/LLMHardwareDesign，分支 task/242-r-load-bounds，main 未因本轮交付改变。登记 PR5 pending；缺 board.json/Projects 工具，看板 unverified、同步 pending，由有权限的管理员处理。

本地正式源非 Git 快照：`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`。并行辅助分别位于 outer247/pdf-export、token-model、token-audit、token-calibration，不共同改正式目录；root 统一整合。当前已上传源 `e2b8c9f98b9c14a2d016062e77fcb094640e8dcc`；新增模型已按 b5ff1f708b1b1809bb78d5849d1f025dc5f3b6d1 完成run14；报告/证据的最终交付commit以PR读回为准。

## PDF

[7页正式PDF](../experiments/pdf/issue-247-p-native-optimizations.pdf)固定源文档 cf570ea69ff05b009c076b79414629b44a86d346，源 SHA-256 `88ed0dd1c610a81734b666c614bf140c29635a0fa97fed7a16d75bfb8aeab2e6`，PDF SHA-256 `b6469f2fd6c6f8ec646c1bc36beb9e3746859ac9d73d219b12c3d0032b635b3c`。171内容单元、4表33行、3代码块、8原文链接完整；7页逐页视觉检查、字体嵌入通过。[生成脚本和QA](../../work/Melodydt/247/pdf-export/qa.json)。未把尚未完成的新 token/s 写入该冻结文档。

## 已结束的历史重现作业

- 登录：`yuzelu@10.129.166.172`。
- run12：`/public/home/yuzelu/Melodydt/issue247-area-speed/run12`；源码子目录 `source/`。
- 源码 commit：`e2b8c9f98b9c14a2d016062e77fcb094640e8dcc`。
- 启动：在 run12 执行 `sbatch --parsable job.sh`。
- 作业 101767 / mdt-token-legacy，c64，4核，node1，1:03，COMPLETED 0:0。
- 日志 `slurm-101767.log`；结果 `results/result.json`。
- 成功判据：4个完整RESULT与run05全字段相等，并通过原独立工作守恒审计。已满足。
- 18个输出SHA、12个回收结果SHA核验通过；主结果SHA `e8c72c436d52969f35eb6c623b8fbedbcdbd48d35c8a4fc69f5cc2ad94ec6c41`，回收包SHA `52d7ba831386aa01ded35eea9a49d5f3304a34c5eb5082b22caf6b7f1cfd19d0`。
- W8 decode512 3.49616888299，W16 decode512 2.11665860003，W8 decode2048 2.55280435873，W8 prefill2 3.69669737899 token/s。仅旧 S32/S96/理想1R1W 条件模型，不是新版原生 RTL 实测。

```bash
cd /public/home/yuzelu/Melodydt/issue247-area-speed/run12
squeue -j 101767
sacct -j 101767 --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n 40 slurm-101767.log
cat results/result.json
sha256sum -c output-files.sha256
```

## 新版整图已结束的作业

run14 / 101777 / mdt-token-native，源码 b5ff1f708b1b1809bb78d5849d1f025dc5f3b6d1。c64/node1/4核，10:34，COMPLETED 0:0。服务器 `/public/home/yuzelu/Melodydt/issue247-area-speed/run14`，源 `source/`、日志 `slurm-101777.log`、结果 `results/result.json`；实际启动目录内 `sbatch --parsable job.sh`。38个全输出SHA、31个回收结果SHA通过；主结果SHA `afa8c326958295957c912f6f0a7836bb98ea235670cd8192cdbcdd64583f480f`，回收包SHA `1ef88173b89e41e5395594742b4612c9821e00b3d41ebaaa3d900a89fdfcb9e6`。

9个case/4组配对、4份原生准入拒绝、独立数值168组/40884源乘积/6边界拒绝、9336个实测RTL事件校准、6项回执篡改拒绝全部满足成功判据。新条件模型W8/context512 0.06758220→0.08174053 token/s，W16 0.04491781→0.05052530，W8/context2048 0.04826512→0.05507842，prefill2两版0.07723904。ctx1→8 +26.60%，单ctx较legacy−4.46%。它们不是完整原生RTL或真实权重生成速度；原始trace原生资格仍拒绝。

run13 / 101769 实际P校准，源eb8a40bc8de0cf6659701188cb5f2225e3320c23，14秒COMPLETED0:0，112输出SHA/12回收结果SHA核验；主SHA `fa7674d19f36f8b743d8101664a0b3f40aa35aa5f2ea233a77447374a204beb9`。2后端×3初态、每次1556事件一致，12数值case通过。

```bash
cd /public/home/yuzelu/Melodydt/issue247-area-speed/run14
squeue -j 101777
sacct -j 101777 --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n 40 slurm-101777.log
cat results/result.json
sha256sum -c output-files.sha256
```

[完整报告](../experiments/issue-247-native-token-throughput.md)、[证据索引](../../work/Melodydt/247/token-throughput/index.json)、[分析](../../work/Melodydt/247/token-throughput/analysis.md)。三轮全部终态，无活动作业，无自动监测，不重复提交或取消。大二进制/生成文件保留本人服务器原目录，本地和仓库保留可逆压缩轻量原件。当前正式源、PDF及报告不等于已合并main，服务器现场也不会被最终文档commit改写。

## 恢复执行第一步

读回Issue247、PR243最新head/审查/CI，运行 `python -B work/Melodydt/247/token-throughput/verify.py`；该检查核验88策展原件、55回收输出和164当前功能源。确认当前本地正式非Git快照与远端一致后再开新任务阶段，不覆盖本轮运行目录。根负责正式源整合，子任务工作区仅辅助，不可直接当远端交付。

下一步由独立审查人（待指定）审查报告/模型；若要求真实原生大模型token/s，实施方需要明确真实权重/激活格式、完整编译与控制/DMA、S32无损或量化合同及原生U路径，再做数值和物理资格。当前研究不自动授权扩大其他成员范围，不实装48/64KiB SRAM。负责人Melodydt；管理员待核实CI、登记PR5和Projects配置/同步。未执行的真实权重生成、完整RTL/网表、面积/时序/P&R保持未验收；管理结构PASS不替代业务测试。
