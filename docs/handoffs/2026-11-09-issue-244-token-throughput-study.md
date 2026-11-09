# Issue #244：吞吐研究交接（图复算已完成）

2026-11-09，Asia/Shanghai；负责人Melodydt；规则rayggxia-project-collab1.0.0。

## 仓库、版本与成果

- 仓库 rayggxia-workspace/LLMHardwareDesign，project_id llm-hardware-design；[Issue #244](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/244) / [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。用户要求复用 task/242-r-load-bounds；原#242修复独立验收。
- 本地独立源快照 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo，非Git checkout，无本地HEAD/暂存区。通过本人GitHub连接、tree/commit/ref lease交付；最终head和CI见PR实时记录。
- 服务器研究源码commit **81dfbd0e6e6d1432447750d5b2d4a106e2d786b7**；其六个文件与最后交付相同。原R已测五文件f034be2保留，研究未再修改生产RTL。
- 最新来源快照：PR220 bf31827f7e039038ca2547046a13d29c4bf46901、PR241 e7aeed2097f57a5f910cae70eb51a220c49a8a14。旧attempt277复算与最新34场景分开，不修改他人工作树/作业。
- [正式报告](../experiments/issue-244-token-throughput-study.md) · [工具/复跑](../../project/experiments/token_throughput_study/README.md) · [证据/SHA](../../work/Melodydt/244/README.md)。

## 已执行与边界

本地900图情景/关键链切换/五个非法篡改拒绝；最新34记录算术/容量/阶段核验；三个Decimal目标与上限、四种损坏记录拒绝；结构/语法/文档检查通过。完整旧图服务器复算已终态通过，结果及六个回收输出SHA匹配、六个源码SHA一致；完整图序列化逐字节匹配原件并复现167410840866ticks。没有重跑最新241的34场景SystemC，也没有取得新量化/KV、执行配方、控制RTL、物理或能量资格。

研究结论：241候选W8/context512约2.7146条件token/s；现流量/17.1GB/s下上限4.7438。达到5至少需少184.728MB/token，且其他阶段不变时Dot服务至少提速2.2195倍；不是已实现结果。旧图假设Dot服务减半约1.33757倍、Dot和Product/Add均减半约1.84269倍，只是完整DAG成本敏感性。

## 作业终态及恢复入口

- 登录 yuzelu@10.129.166.172。
- **101608 / mdt-tps-study，c96/node13，4核，UNLIMITED，22秒，COMPLETED 0:0**；无本任务活动作业。
- 目录 /public/home/yuzelu/Melodydt/issue244-token-throughput/run03。
- 实际启动：cd /public/home/yuzelu/Melodydt/issue244-token-throughput/run03 && sbatch --partition=c64,c96 --parsable job.sh。
- 日志 slurm-101608.log；检查check.log；结果results/result.json；完整图results/graph.json；allocation.txt、sacct.txt、resources.txt、output.sha256均保存。
- 源码包SHA 0e82bb48f8b1e33b06ac609d5c682a39436af169717199721bfa9abcdb862957；结果SHA 840e167cccbda790a28dd870036f0d09d3e4f0e0f0389a5ba9bf430043366bc2；完整图SHA daeca8137b507182cf77f623a571176b2c42879b47f405ffde606072929495a3。大图只留服务器，轻量原件在work/Melodydt/244。
- 实际Python3.10.12；运行时容器SHA未额外记录，待核实，不把此前镜像SHA冒称本次启动实测。
- 失败保留：run01的16G请求未受理，无JobID；101601/run02在node1因Windows SHA清单CRLF于读取源码前失败1:0。run03清单写为LF，提交前后六文件校验均通过；未绕过检查、未覆写失败原件。
- 本地原始副本 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/244/run01、run02、run03，包含打包、失败与成功输出。

```bash
sacct -j 101608 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -X
tail -n 30 /public/home/yuzelu/Melodydt/issue244-token-throughput/run03/slurm-101608.log
cat /public/home/yuzelu/Melodydt/issue244-token-throughput/run03/results/result.json
cat /public/home/yuzelu/Melodydt/issue244-token-throughput/run03/output.sha256
```

**恢复第一步**：读取本人身份、最新AGENTS/Skill、Issue/PR及分支head，再核对同一101608的终态和上述SHA；无需重提或监测已结束作业。成功判据已满足：sacct0:0、900校验通过、完整图匹配、基线复现、输入/输出SHA一致。后续先审查研究报告，再独立跟踪P/通道计数、减重复流量、2P/3P同带宽分工以及现有硬件跨元素S状态/打包供数，选中可执行候选需要自己的数值/时序证据。

研究交付状态in_review，未done/未合并；独立审查人和后续实现负责人待指定。#242按其独立待审状态保留。未创建自动监测，无持续后台检查承诺。

登记management-hub PR5仍open/unmerged，pending。无board.json/Projects条目工具，看板unverified、同步pending；管理员待指定，按244的In review状态加卡/复用并核对Project ID llm-hardware-design、Status及读回。CI以最终PR为准，已知失败且原因待核实，未修改workflow或绕过审查。
