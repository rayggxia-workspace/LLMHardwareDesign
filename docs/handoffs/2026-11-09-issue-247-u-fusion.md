# Issue247 融合与流水研究交接

2026-11-09 Asia/Shanghai；Melodydt；[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，task/242-r-load-bounds，in_review。统一规则rayggxia-project-collab1.0.0。最新实测模型源码af9e43282c82ed8bc43cdaf3c2ec3c1ce8fc53b2，FIFO源码1e6e10a7618f3d37542d1f22dd51af6ad1958eb8；后续文档提交不改实测功能源。

本地非Git源码快照：D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo。外层work/Melodydt/247存打包/回收，子任务各自独立fusion-model/fusion-audit/fusion-contract目录，仅root整合正式文件。未宣称本地checkout/pull或main合并；正式源码project/experiments/u_fusion_study，轻量证据work/Melodydt/247/fusion，报告docs/experiments/issue-247-u-fusion.md。

服务器yuzelu@10.129.166.172，自己的/public/home/yuzelu/Melodydt/issue247-area-speed/run06–09，每个目录source为源码，results为结果，slurm-作业号.log为日志，inputs.json含真实commit和输入SHA。实际启动均在各目录执行sbatch --parsable job.sh；c64/node1/4核/UNLIMITED。

| run | 作业 | 状态 | 说明 |
|---|---|---|---|
| run06 | 101712/mdt-u-fusion | FAILED1:0/22秒 | 原生通过；generated目录缺失，现场保留 |
| run07 | 101720/mdt-u-overlap | COMPLETED0:0/21秒 | 108项RTL、满恢复/reset通过 |
| run08 | 101721/mdt-u-fusion | FAILED1:0/91秒 | 原生通过；错误三输入guard，现场保留 |
| run09 | 101728/mdt-u-fusion | COMPLETED0:0/9:56 | 22完整case、9默认回归、12小trace、3非法CLI和原生24测量通过 |

run09结果SHA f65520c819194e07af2d2d8764cde506406913d5d4818c78bc1cb48bcd202919；run07 e8aa9c641b299ed4c43b6dcea6583cfb77fad7220c1de783190fe2150f37d860。run06/07/08/09回收15/20/48/104份原始输出SHA通过；日志无损压缩与完整结果可本地验证，完整JSONL和二进制留服务器，未把索引当实际上传。

```sh
squeue -j 101712,101720,101721,101728
sacct -j 101712,101720,101721,101728 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -X
tail -n 40 /public/home/yuzelu/Melodydt/issue247-area-speed/run09/slurm-101728.log
cat /public/home/yuzelu/Melodydt/issue247-area-speed/run09/results/result.json
cat /public/home/yuzelu/Melodydt/issue247-area-speed/run07/results/result.json
python -B work/Melodydt/247/fusion/verify.py --repo . --index work/Melodydt/247/fusion/index.json
```

恢复第一步：核对最新Issue/PR/head，读报告和上述验证，不重复提交旧作业。成功判据包括COMPLETED0:0、passed和SHA；不能改判旧失败。实际融合、冻结阶段流水预测和原生S16局部周期分账。生产RTL保持，SRAM扩容不实装。未完成：生产取消/drain、顶层命令/地址别名、完整并发DDR/cache模型、综合/STA/P&R、实际模型生成和独立审查，负责人待指定。

文件通过本人连接沿PR交付，分支上传/审查合并/登记/看板分别报告。登记management-hub PR5仍open/unmerged为pending；缺board.json/Projects能力，看板unverified/同步pending，管理员待指定。CI失败或待核实不冒称通过，详情留PR。无活动作业，未配置自动监测；后续需要再次唤起核验。
