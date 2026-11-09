# Issue247 固定SRAM提速研究接续

2026-11-09 Asia/Shanghai；负责人 Melodydt；规则 rayggxia-project-collab 1.0.0。[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。用户授权按顺序研究并接受一定面积增加，SRAM扩容保留候选、暂不实装。

仓库 rayggxia-workspace/LLMHardwareDesign，分支 `task/242-r-load-bounds`；本地源快照 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo` 是非Git目录，不能把它描述为本地HEAD或已pull。通过本人GitHub tree/commit/ref租约上传；最后已上传源45e45bf75f35ebf35111f525de655076f7e122be，最终文档head以PR读回为准。本地新增研究代码与本轮文档/轻量证据属于本任务，原R修复和Issue244/245/246证据保持。

服务器 `yuzelu@10.129.166.172`，仅本人 `/public/home/yuzelu/Melodydt/issue247-area-speed/`；每个run独立 `source/`、日志、`results/`。三个作业均4核、c64/node1、UNLIMITED，不取消作业，不修改他人目录。

| 阶段 | 源码commit | run/作业 | 实际状态 |
|---|---|---|---|
| 多部分和 | 9015effa13879bf8b5779905a4c83f53af8f2085 | run01/101631 mdt-area-speed | COMPLETED 0:0，4分57秒 |
| 尾块+弹性RTL | be603f4d7661dfc3a42c17d797e1ce74772284c3 | run02/101635 mdt-area-feed | COMPLETED 0:0，24秒 |
| 端口→第三P→向量 | 45e45bf75f35ebf35111f525de655076f7e122be | run03/101638 mdt-area-hw | COMPLETED 0:0，4分42秒 |

实际启动均为进入对应run目录后 `sbatch --parsable job.sh`，不要恢复时重复提交。直接追踪：

```bash
squeue -j 101638
sacct -j 101631,101635,101638 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -X
tail -n 40 /public/home/yuzelu/Melodydt/issue247-area-speed/run03/slurm-101638.log
cat /public/home/yuzelu/Melodydt/issue247-area-speed/run03/results/result.json
```

前两轮已核验92/85份回收输出SHA；run01完整结果62c787396bd331cb2c6d8a0a4352a4ebb83456616eb141bc50c33655d84f3fc3，run02 cc7a4aceeef4b1d53c19229c686a8beb909f22b4ce66390ce8db6a5f3cddfba0。35完整trace、480数值配置/120生命周期/20错误注入及原kernel/validation/smoke通过；第二轮实际21候选+6baseline+5非法CLI通过。两槽link持续吞吐128→256beats/256拍，但原P程序各三例两版都288拍；仅配对link的映射面积2.1745倍，无布局布线/时序资格。

第三轮也已回收核验65份输出SHA，完整结果5c5e4c02084b1cc76be8f1b92fbbe5bde32fe538bb3a43a6fa94f240552507f9。21完整case通过；两P同容量1R1W+8contexts为3.496169条件token/s，对前轮最佳+14.12%；三P均分退化，向量宽化收益较小。三轮共56完整trace、32边界调用，242回收输出SHA；63轻量证据与50最新功能源一致性通过。[报告](../experiments/issue-247-area-speed.md)/[索引](../../work/Melodydt/247/index.json)。无活动作业，不需重复提交。

恢复第一步：核验本人身份、最新规则、Issue/PR head及评论，运行`python -B work/Melodydt/247/verify.py`，核对同Job/source/result SHA。接续为独立审查研究证据，或另定实际P同容量读写并发的RTL/宏/时序实施范围；实施及独立审查负责人待指定。N16/N32、通道感知三P分工、U融合未执行；未测组合不外推收益。任务未审查合并不done。最终文档/证据上传后，源与服务器已测功能保持；远端head以PR读回为准。

PR未合并，独立审查人待指定；登记management-hub PR5 pending，无board.json/Projects工具，看板unverified/同步pending。GitHub CI此前failure且日志不可用，需继续读回本次CI；管理员待指定，不改工作流绕过检查。所有性能数值为条件模型，PR241原生S32/M/E接口与实际权重/KV/DDR/物理未资格化；实际生产RTL未改。没有配置聊天结束后的自动监测。
