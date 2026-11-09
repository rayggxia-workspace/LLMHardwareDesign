# Melodydt / Issue #244 吞吐研究证据

[Issue #244](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/244) / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。负责人Melodydt，规则rayggxia-project-collab1.0.0。按用户要求复用 task/242-r-load-bounds，原#242修复保留。

[正式报告](../../../docs/experiments/issue-244-token-throughput-study.md) · [工具/复跑](../../../project/experiments/token_throughput_study/README.md) · [终态交接](../../../docs/handoffs/2026-11-09-issue-244-token-throughput-study.md)。

| 文件 | 来源与用途 |
| --- | --- |
| preview-bounds.json / check-local.json | 本地配置推导、旧链必要上限、900图/拒绝检查；非硬件吞吐 |
| upstream241-results.json / upstream241-input.json | PR241@e7aeed2已发表34场景与配置原字节；来源SHA见systemc-evidence.json，未冒称重跑 |
| latest-systemc-assessment.json / assessment-check.json | 34记录算术/容量/阶段核验，4/5/10目标必要条件，独立Decimal及损坏输入拒绝 |
| server-result.json / server-check.log | 101608实际完整旧图结果及服务器900校验；非最新34场景复跑 |
| server-verification.json / output-101608.sha256 | 六源码/六回收输出SHA核对及完整图服务器SHA |
| sacct-101608.txt / resources-101608.txt / allocation-101608.txt | 作业终态、实际节点/核数/时限/资源 |
| slurm-101608.log | 成功作业原始输出 |
| slurm-101601-failure.log | CRLF清单失败原件，读取源码前退出1:0 |
| inputs-run02.json / inputs-run03.json / initial-submission.json | 保留首次未受理和失败输入；成功轮六文件源码与包SHA，LF清单 |
| job-state.json | 成功终态和失败历史；不将历史排队占位退出码当通过 |
| evidence-index.json | 本目录轻量文件SHA索引 |

**101608 / mdt-tps-study，c96/node13，4核、UNLIMITED，22秒，COMPLETED 0:0**。六源码、六回收输出SHA通过；完整任务图序列化逐字节匹配原件，基线167410840866ticks复现。旧图假设Dot服务减半约1.33757倍、两组主要服务均减半约1.84269倍；这是敏感性，不是新配方或实际生成速度。

服务器yuzelu@10.129.166.172；目录/public/home/yuzelu/Melodydt/issue244-token-throughput/run03；实际命令在该目录执行 sbatch --partition=c64,c96 --parsable job.sh。源码81dfbd0e6e6d1432447750d5b2d4a106e2d786b7，包SHA0e82bb48f8b1e33b06ac609d5c682a39436af169717199721bfa9abcdb862957。完整graph.json保留服务器，SHA daeca8137b507182cf77f623a571176b2c42879b47f405ffde606072929495a3。

```bash
sacct -j 101608 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -X
tail -n 30 /public/home/yuzelu/Melodydt/issue244-token-throughput/run03/slurm-101608.log
cat /public/home/yuzelu/Melodydt/issue244-token-throughput/run03/results/result.json
```

最新来源PR220@bf31827f7e039038ca2547046a13d29c4bf46901、PR241@e7aeed2097f57a5f910cae70eb51a220c49a8a14与旧attempt277基线分账。失败和成功原件均保留；本地大包在D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/244/run01、run02、run03。运行时Python3.10.12；容器启动时SHA未额外记录，待核实。

研究进入in_review，未合并/未done；无本任务活动作业或自动监测。新量化/KV、可部署配方、RTL/物理及能量未验收。登记PR5 pending，看板unverified/同步pending，CI以PR最终回执为准，管理员和独立审查人待指定。
