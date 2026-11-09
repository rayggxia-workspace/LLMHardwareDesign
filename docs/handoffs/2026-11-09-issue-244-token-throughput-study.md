# Issue #244：吞吐研究与排队图复算交接

2026-11-09，Asia/Shanghai；负责人Melodydt。规则rayggxia-project-collab1.0.0。

## 分支、输入和成果

- 仓库 `rayggxia-workspace/LLMHardwareDesign`，project_id `llm-hardware-design`；[Issue #244](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/244)，复用 [PR #243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。用户明确要求在本分支研究，未另建重复PR，不更改#242验收范围。
- 远端分支 `task/242-r-load-bounds`；服务器研究源码commit `81dfbd0e6e6d1432447750d5b2d4a106e2d786b7`。原R修复源码 `f034be2b7c87137b92f7bfce274a5485647e512d` 的五个文件保留。
- 独立本地源快照 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`，不是Git checkout，无本地HEAD/暂存区；通过本人GitHub连接tree/commit及ref lease发布。原始打包输入另在 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/244/run01`、`run02`，不上传大包或无关文件。
- [正式报告](../experiments/issue-244-token-throughput-study.md)、[工具与输入](../../project/experiments/token_throughput_study/README.md)、[轻量证据](../../work/Melodydt/244/README.md)。最终交付head与CI以PR实时记录为准；本文件后的文档/研究模块不改排队作业的六文件快照。
- 最新上游PR220 `bf31827f7e039038ca2547046a13d29c4bf46901`、PR241 `e7aeed2097f57a5f910cae70eb51a220c49a8a14`，已在05:31UTC重新读取。服务器作业保留旧attempt277基线，不将其输出当作最新34场景复跑。不改YUZE-LU的分支、工作树或作业。

## 实际验证与未完成项

已完成：本地900个DAG情景与独立全路径穷举一致、关键链切换与五个非法/篡改输入拒绝；配置推导及旧关键链必要上限；最新PR241的34记录算术/存储/阶段一致性检查，目标4/5/10 token/s所需流量及Dot改善条件。没有重新执行上游34组SystemC、没有新增生产RTL或物理资格。原#242的9次RTL正向/3次负控制证据保留，不冒称本轮重跑。

当前结论：最新241候选W8/context512约2.7146条件token/s；17.1GB/s和现流量下理想上限4.7438。达到5至少需要少184.728MB/token，并在其他阶段不变时使Dot服务至少提速2.2195倍；这两个条件不是已实现结果。优先做P/通道计数、减重复流量和2P/3P同带宽消融；原硬件线上继续验证跨元素有限S状态和打包供数。

未完成：作业101601完整旧图复算、选中新配方/真实KV数值、候选服务/控制RTL、物理、能量、同条件FPGA验收。Issue244保持in_progress，Refs244，不done；#242维持其独立待审状态。后续实现/审查负责人未明确者记待指定，不自行分派给其他成员。

## 作业追踪

- 登录：`yuzelu@10.129.166.172`。
- 工作根：`/public/home/yuzelu/Melodydt/issue244-token-throughput/run02`。
- 实际启动：`cd /public/home/yuzelu/Melodydt/issue244-token-throughput/run02 && sbatch --parsable job.sh`。
- 作业 **101601 / mdt-tps-study**，4核、UNLIMITED；提交时c64，排队中只将分区扩为c64,c96，无取消/重提。最新保存快照仍PENDING/Priority，节点待分配；Slurm预计启动值不作为承诺。
- 日志 `slurm-101601.log`；检查 `check.log`；结果 `results/result.json`；完整图 `results/graph.json`；分配回执 `allocation.txt`。排队时日志和结果可能尚未创建。
- 包SHA `0e82bb48f8b1e33b06ac609d5c682a39436af169717199721bfa9abcdb862957`；源码文件SHA见inputs-run02.json。输入IR/plan/probe均按固定SHA拒绝漂移，原始707MiB IR只读。进程虚拟内存上限12GiB；c64真实内存未配置为可调度资源，首次16G请求未受理，无JobID。

```bash
squeue -j 101601
sacct -j 101601 --format=JobID,JobName,State,ExitCode,Elapsed,NodeList -X
tail -n 30 /public/home/yuzelu/Melodydt/issue244-token-throughput/run02/slurm-101601.log
cat /public/home/yuzelu/Melodydt/issue244-token-throughput/run02/check.log
cat /public/home/yuzelu/Melodydt/issue244-token-throughput/run02/results/result.json
```

**恢复第一步**：核对本人身份、最新AGENTS/Skill、Issue/PR和分支head，再读取同一101601状态；不要重新提交或覆写冻结源。进入RUNNING后记录实际节点和阶段；结束后核对sacct退出0:0、900情景检查、完整图序列化SHA等于PR241原件、基线167410840866及逐情景结果/输出SHA。记录实际Python与容器版本；只有复算合同通过才能将结果写为已执行。失败时保留原件、定位后使用新输出目录。图灵敏度仍非新计划或已校准吞吐。

未创建自动监测；聊天结束后不自动持续检查，需成员再次唤起。作业独立于聊天持久保存，不因本轮结束而取消。

登记management-hub PR5仍open/unmerged，pending。无config/board.json与Projects条目操作能力，看板unverified/同步pending；管理员待指定负责配置、加卡/复用244、Project ID/Status字段和读回。CI已知失败、具体原因待核实，不能通过修改workflow绕过；详见PR回执。
