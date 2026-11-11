# 后续优化研究交接：192场景完成待审

2026-11-10 Asia/Shanghai；负责人Melodydt；规则rayggxia-project-collab 1.0.0。
仓库https://github.com/rayggxia-workspace/LLMHardwareDesign，project_id llm-hardware-design。
Issue https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247；PR https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243。
复用task/242-r-load-bounds，当前源码head f1700f031d629e5af33ad8b36ff9523a6393d90b；本记录随报告提交，最终交付commit以PR读回为准。

## 工作目录和范围

本地正式副本D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo是非Git快照，
本阶段只新增三个optimization实验目录及对应报告/证据/管理摘要。既有a32-rtl等worktree的未提交修改原样保留。
生产RTL无修改；本地新增报告待随当前任务分支上传，非main已合并内容。原始回收位于本地work/Melodydt/247/run35、run36、run37/receipts。
完整服务器结果独立保存，仓库只存轻量分析与SHA索引，不声称完整raw进入Git。

## 服务器终态与恢复命令

登录目标yuzelu@10.129.166.172；本人授权父目录/public/home/yuzelu/Melodydt/issue247-area-speed。
每次均在run根执行sbatch --parsable job.sh，代码source/，输出results/；4CPU，c64，node1。

| run / 作业 / 名称 | 源码commit | 终态与耗时 | 日志 |
|---|---|---|---|
| run35 / 102040 / mdt-opt-sweep | e2f91b346f57e872610b0e416290901f5d5e666e | COMPLETED 0:0，17:30，112例 | run35/slurm-102040.log |
| run36 / 102041 / mdt-opt-follow | d9afc95a9b649b096c8a7930d99d56d065d78047 | COMPLETED 0:0，09:07，56例 | run36/slurm-102041.log |
| run37 / 102043 / mdt-opt-bridge | f1700f031d629e5af33ad8b36ff9523a6393d90b | COMPLETED 0:0，04:10，24例 | run37/slurm-102043.log |

```sh
squeue -j 102040,102041,102043
sacct -j 102040,102041,102043 -X --format=JobID,JobName,Partition,AllocCPUS,State,ExitCode,Elapsed,NodeList
tail -n 40 /public/home/yuzelu/Melodydt/issue247-area-speed/run37/slurm-102043.log
cat /public/home/yuzelu/Melodydt/issue247-area-speed/run37/results/result.json
```

run35/36同样替换路径和jobid查看。成功判据已满足：三个result.passed=true，192场景、40完整历史RESULT控制、
960结果负控、4350池数据比较、60生命周期及18事件篡改检查通过；519回收文件SHA逐项验证，日志RESULT重新解析一致。
数值验证只覆盖生成的共享池头/载荷/FIFO，不是新S16桥接/NExp8/M16 RTL资格。所有输入、输出、工具版本及SHA见
[证据索引](../../work/Melodydt/247/optimization-sweep/evidence-index.json)。收集器Python3.6兼容修复不改变仿真结果。

## 研究结果与下一步

[报告](../experiments/issue-247-optimization-sweep.md)保留22种方案×四工作负载×两端口层、面积判断与实施建议。
共享32KiB/17.1GB/s固定：S16桥接＋8路向量4.423812/5.086834 token/s；桥接8拍时4.401308/5.057101。
更大的M16/宽供数/128B读＋向量16＋S16组合最高5.508124。这些是条件SystemC结果；未新增原生整图或物理资格。
下一步Melodydt优先验证S16桥接数值、尾部和背压，再实现8路向量并重新测原生RTL和面积；本轮未授权变更范围内不预先实装。
恢复第一步读取本交接、当前Issue/PR与远端head，对照源码commit及SHA索引；不要重复覆盖或启动已完成run目录。

## 管理回执和限制

研究结果in_review，PR未审查/合并，不标done；正式审查人待指定。
本地python scripts/check_project.py仅管理结构；实际业务证据为上述服务器SystemC。未执行新的RTL仿真、综合、STA/P&R。
结构CI run42828692493 failure，validate job129872670602无steps；具体原因待管理员核实，不绕过workflow。
登记management-hub PR5 pending；config/board.json缺失且无Projects工具，看板unverified/同步pending，处理管理员待指定。
旧run24/25原包上传阻塞保持，本轮未重传；新结果与新索引单独交付。
无活动作业，未配置自动监测。结束聊天不意味着自动持续检查。
