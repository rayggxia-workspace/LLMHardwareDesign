# Melodydt / Issue #244 吞吐研究证据

[Issue #244](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/244) / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。负责人Melodydt；规则rayggxia-project-collab1.0.0。用户指定继续使用 `task/242-r-load-bounds`，研究独立跟踪，原#242 LOAD修复保留。

[正式研究报告](../../../docs/experiments/issue-244-token-throughput-study.md) · [工具/复跑](../../../project/experiments/token_throughput_study/README.md) · [恢复交接](../../../docs/handoffs/2026-11-09-issue-244-token-throughput-study.md)。

| 文件 | 来源与边界 |
| --- | --- |
| preview-bounds.json | 本地Python3.12.14的配置推导与旧关键链必要上限；不是整图仿真 |
| check-local.json | 实际900个独立全路径枚举情景、关键链切换、五个非法/篡改输入拒绝 |
| upstream241-results.json / upstream241-input.json | PR241@e7aeed2的原始已发表34场景/配置字节；SHA见formal目录systemc-evidence.json；不冒称本轮重跑 |
| latest-systemc-assessment.json | 34组记录的算术/容量/阶段一致性核验及目标4/5/10 token/s必要条件 |
| inputs-run02.json | 已上传/提交的6文件源码与包SHA，服务器代码commit81dfbd0 |
| job-state.json | 101601真实PENDING快照及原始scontrol/sacct回执，不把预计启动或0:0占位退出码当作已运行/通过 |
| initial-submission.json | 首轮16G请求未被Slurm受理，无JobID；未运行，不是仿真失败 |
| evidence-index.json | 本目录轻量文件SHA索引 |

新来源：PR220 `bf31827f7e039038ca2547046a13d29c4bf46901`、PR241 `e7aeed2097f57a5f910cae70eb51a220c49a8a14`。原图复算保持原诊断输入SHA，不随上游更新覆写；研究当前结果与旧对照分账。

服务器 `yuzelu@10.129.166.172`；目录 `/public/home/yuzelu/Melodydt/issue244-token-throughput/run02`；实际命令 `cd /public/home/yuzelu/Melodydt/issue244-token-throughput/run02 && sbatch --parsable job.sh`。作业 **101601 / mdt-tps-study**，4核，UNLIMITED，提交后允许c64/c96；最新快照仍PENDING/Priority，节点待分配。研究源码commit `81dfbd0e6e6d1432447750d5b2d4a106e2d786b7`；包SHA `0e82bb48f8b1e33b06ac609d5c682a39436af169717199721bfa9abcdb862957`。完整旧图、图文件及后续大输出只留本人服务器目录，不入Git。

```bash
squeue -j 101601
sacct -j 101601 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -X
tail -n 30 /public/home/yuzelu/Melodydt/issue244-token-throughput/run02/slurm-101601.log
cat /public/home/yuzelu/Melodydt/issue244-token-throughput/run02/results/result.json
```

完整旧图结果尚未回收，Issue244保持in_progress；PR阶段性Refs244，不能关闭。实际模型生成速度、完整新量化/KV数值、新RTL/物理及能量未验收。登记management-hub PR5 pending；无board.json/Projects条目工具，看板unverified、同步pending；处理人待指定。CI以PR实时结果为准，不能把本地检查写成CI通过；未自合并。
