# Issue245：P/DMA研究可恢复交接

2026-11-09，Asia/Shanghai；规则rayggxia-project-collab1.0.0；负责人Melodydt。[Issue245](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/245) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，研究成果待审查/合并，不done。

仓库`rayggxia-workspace/LLMHardwareDesign`，project_id `llm-hardware-design`。用户明确指定沿`task/242-r-load-bounds`，不重复开PR；#242 LOAD修复、#244原研究验收独立。main基线c4d7b960599b9d292f27eb4429d5f226a7156c95；本轮最终已测功能源commit **727f297cd0ec3436e108e351aad5799c013c0338**，15功能文件与交付相同，文档提交head以PR实时读回为准。

本地独立源快照`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`，非Git checkout，没有本地HEAD/暂存区；不把其外层管理副本当主仓库。通过Melodydt本人连接创建tree/commit并以expected_sha的ref lease上传，未借用身份/强推。辅助输入/打包/完整回收在外层`D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/245/`；其中大trace、tar、生成模型不在上传范围。没有改动他人目录/作业或生产RTL。

成果：[中文报告](../experiments/issue-245-p-dma-study.md)、[正式脚本/复跑依赖](../../project/experiments/p_dma_study/README.md)、[本人轻量回执与SHA](../../work/Melodydt/245/README.md)、[个人进度](../../progress/Melodydt/STATUS.md)。测试源码锁定PR241 e7aeed2097f57a5f910cae70eb51a220c49a8a14，220只读上下文3a9f98a926134ad4ee0d57f4a2c3545ee8df8c7d。

## 服务器真实状态

登录`yuzelu@10.129.166.172`；仅本人`/public/home/yuzelu/Melodydt/issue245-pdma/`。作业名均mdt-pdma、c64/node1/4核、UNLIMITED，所有本任务作业均已终态，无活动仿真，未创建自动监测。

| 子目录 | JobID | 源码commit | 终态 |
|---|---:|---|---|
| run01 | 101611 | 0439f6795e4d9fe521f0514e0f52f6f91551856a | FAILED1:0/12秒；严格编译缩进告警，未仿真 |
| run02 | 101612 | 247657283d849d7e78450a05ec70a5ff3ed39567 | COMPLETED0:0/4分59秒，26次 |
| run03 | 101614 | 29e50549c45f5b56550081a07fcade659d5ebfbb | COMPLETED0:0/2分55秒，18次 |
| run04 | 101615 | 727f297cd0ec3436e108e351aad5799c013c0338 | COMPLETED0:0/3分31秒，18次 |

实际启动均为`cd /public/home/yuzelu/Melodydt/issue245-pdma/run0N && sbatch --parsable job.sh`。run03/04在run.py末尾分别带`--phase followup`、`--phase adaptive`，外层实际job.sh单独保存SHA。源码在各目录`source/`、输入`inputs/`、日志`slurm-<JobID>.log`、结果`results/result.json`及各case JSON/log，源码/输入清单`source-files.sha256`/`input-files.sha256`，输出清单`output-files.sha256`，allocation.txt为启动时RUNNING快照，sacct.txt为实际终态。完整输入、二进制、全量日志只留服务器。

```bash
squeue -j 101615
sacct -j 101611,101612,101614,101615 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -X
tail -n 30 /public/home/yuzelu/Melodydt/issue245-pdma/run04/slurm-101615.log
cat /public/home/yuzelu/Melodydt/issue245-pdma/run04/results/result.json
cd /public/home/yuzelu/Melodydt/issue245-pdma/run04
sha256sum -c output-files.sha256
```

末条只校验本任务既有结果，不重跑实验。已结束作业可能不再显示于squeue；以sacct退出码及完整PASS回执为准。恢复第一步：重新读取身份、AGENTS/Skill、Issue/PR评论与head，运行本地`python -B work/Melodydt/245/verify.py`，核对相同JobID及index.json中的完整结果SHA，无需重提已完成作业。如需新模型实验，使用新目录、先上传新源码，再Slurm冻结输入，保留所有失败。

## 验证、建议与未完成项

三轮共62次完整trace（含重复对照），每轮225 kernels/4 validation/5 smoke/软件oracle通过；原版/观测版全部原指标与上游W8/W16均精确相同，逐通道/类别/形状/阶段、S/信用/ACK审计通过；后两轮七个篡改拒绝通过。91份回收输出、44份Git轻量证据及15最终功能源SHA可核对；68输出清单项保留服务器。GCC11.4.0/Python3.10.12/SystemC3.0.2，容器/库本轮运行时散列见tools.sha256，不使用他人Python环境。

W8/context512权重占85.60%、A占11.90%；有限A前缀仅+1.10%，容量选择预取策略单独+10.74%，组合+12.86%到3.063655条件token/s。组合context128/2048及prefill2均改善；W16单策略更好。仅省2.15%字节，上限4.84811仍不足5。保留全局关队列长context退化、小K/单缓冲/少信用等阴性结果。建议优先验证按A驻留容量限制预取、S消费者仲裁，再评估前缀/写合并。模式切换/指令成本未实装；真实张量数值、量化KV质量、DDR、RTL/物理/能耗未获资格，后续负责人待指定。

本任务本地研究和服务器实验完成；通过分支/PR交付待独立审查，未合并、未done。管理结构和回执检查不替代业务或物理验收；CI以PR实时记录为准，已知Actions存在失败且未提供详细日志，不改workflow/绕过。审查人待指定，管理员须检查Actions具体注释并解除原因。

登记[management-hub PR5](https://github.com/rayggxia-workspace/management-hub/pull/5)本轮读回open/unmerged，pending。无config/board.json、无Projects条目工具，看板unverified/同步pending；待指定管理员复用/加入#245，Project ID=llm-hardware-design、Status=In review，按配置同步并读回，不把本地进度当在线卡片更新。#242/#244各自待审状态保留。
