# Issue247 原生P前三项优化接续

2026-11-09，Asia/Shanghai；负责人 Melodydt，独立审查人/优先级待指定。

## 当前终态与交付

本轮源码及验证已完成，交付PR243待审，Issue247为in_review，不done。run10/101756（源码c2359bdeeea83270ab632861eebe6ffc8dcc510e）1:21，run11/101758（源码24f720a788328bd8d73e2bf1a3b0502ded9b937b）1:05，均COMPLETED0:0。四组件通过来自run10；run11补local与完整P。全部作业终态，无活动仿真，未配置自动监测。源、工具、版本及185份轻量证据见[native-p入口](../../work/Melodydt/247/native-p/README.md)。最终上传commit在PR回执记录，不将最终文档head当作运行源码。

无背压local95→71；完整P含释放K59 2112→2032、K11 672→676。15生产RTL两轮SHA相同，29当前功能源核验通过；管理/Python/JSON/链接及163策展结果SHA通过。800+629项全部输出哈希，104+66项回收结果逐项匹配。主结果SHA为97de764fffa64b9eb151204af74f94e4d53ea4cabd1f5b5e96c292a0e75bdec0与0061270c92a28004e87c0eb3dd69dcd3e0bfd0da6ba97d8bec69d89588fd71f2。

下一步由实施方接入真实DMA预取/描述符/信用、控制镜像和整模型数值，并做综合/STA/P&R；审查人待指定。SRAM扩容未实装；功能通过不代表物理或大模型部署验收。登记PR5本次实读open/unmerged，pending；无board.json/Projects能力，看板unverified/同步pending，管理员待指定。源码24f720a7的CI42636841207 failure，无可用step结果，原因待核实；最终head CI以PR回执为准，未改workflow绕过。

run11实际启动：`cd /public/home/yuzelu/Melodydt/issue247-area-speed/run11 && sbatch --parsable --export=ALL,POPT_COMPONENTS=integration job.sh`，mdt-p-native/c64/node1/4核/UNLIMITED。源码source，日志slurm-101758.log，结果results/result.json。可复制查询：

```sh
squeue -j 101756,101758
sacct -j 101756,101758 -X --format=JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 40 /public/home/yuzelu/Melodydt/issue247-area-speed/run11/slurm-101758.log
cat /public/home/yuzelu/Melodydt/issue247-area-speed/run11/results/result.json
```

恢复第一步：读PR最新head/审查意见和本文终态，运行离线verify核对当前源；无需重复提交已完成作业。本地非Git快照位置见下，工作文件已纳入本次显式交付白名单，无ref-project改动；服务器原件保持独立不可覆盖。

## 以下为启动前及启动时的历史记录



- 仓库 https://github.com/rayggxia-workspace/LLMHardwareDesign ，[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)，[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。继续 `task/242-r-load-bounds`，实施起点 `3a66f8de0889925846e9d737690e2d9e297bb173`。
- 本地正式源是非Git快照 `D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo`。通过本人 GitHub tree/commit/ref 租约上传，未宣称本地 checkout/pull。并行工作隔离在外层 `work/Melodydt/247/popt-policy`、`popt-memory`、`popt-context`；仅根整合正式文件。
- 起点458个PR文件Git blob与本地逐项一致，无无关变更；保留既有R修复及研究，不操作ref-project。
- 本轮修改P仲裁、可选bank并发、可选M contexts及B-only LOAD。默认参数保持旧语义。数据S仍16KiB，未实现48/64KiB扩容、真正独立64B读+64B写或外存自适应预取描述符控制。
- [设计与具体做法](../experiments/issue-247-p-native-optimizations.md)。正式源 `project/rtl/`，服务器运行器 `project/experiments/p_native_opt/`。
- 本地 `python scripts/check_project.py` 通过仅管理结构；已完成代码生成与Python AST，EDA未在本地执行。当前尚无本轮仿真作业受理回执；后续上传精确源码后运行独立Slurm作业，立即补充job/commit/目录/命令/SHA。
- 历史run01–09均终态，本轮不会覆盖这些目录。新run10位于本人 `/public/home/yuzelu/Melodydt/issue247-area-speed/`，2026-11-09已确认尚不存在；未提交前不称已运行。
- 源码修改使历史研究的“当前生产源必须与冻结SHA相同”条件不再成立；旧研究冻结源与结果继续保留于各原run，不改旧检查器来掩盖漂移。本轮独立记录新源锁并重跑受影响P业务验证。
- 状态in_progress，未done。登记management-hub PR5 pending；缺board.json/Projects能力，unverified/同步pending，处理人待指定；历史CI无step失败原因待管理员核实。未配置自动监测。

恢复第一步：核对PR实时head与本轮实际源码commit，检查本交接追加的run受理/终态回执；若已提交不得重复提交。随后查看结果JSON及所有失败组件日志，保留失败现场，在新run修复复跑。成功判据为主作业COMPLETED0:0、四组件通过、真实数值/回写ACK/守恒与负例证据齐备，并通过SHA复核；这不等于物理或整模型验收。

## run10 启动回执

源码 `c2359bdeeea83270ab632861eebe6ffc8dcc510e`，25交付文件读回Git blob一致，PR共482文件。payload SHA-256 `697271b9d6de01729b44f44b40839072a1942bd6e85a4f384c56e6e7b5af88de`，32源文件在服务器逐项通过SHA核验；固定输入在测试源中，无外部权重数据。

登录 `yuzelu@10.129.166.172`，工作目录 `/public/home/yuzelu/Melodydt/issue247-area-speed/run10`，源码子目录 `source`；实际启动 `cd /public/home/yuzelu/Melodydt/issue247-area-speed/run10 && sbatch --parsable job.sh`。作业 `101756 / mdt-p-native`，分区c64、4核、UNLIMITED，node1，受理后实读RUNNING，处于原生RTL编译/四组件回归阶段。日志 `slurm-101756.log`，结果 `results/result.json`，均持久保存。本次启动回执不代表测试通过。

```sh
squeue -j 101756
sacct -j 101756 -X --format=JobID,JobName,State,ExitCode,Elapsed,NodeList
tail -n 40 /public/home/yuzelu/Melodydt/issue247-area-speed/run10/slurm-101756.log
cat /public/home/yuzelu/Melodydt/issue247-area-speed/run10/results/result.json
```

未配置聊天结束后的自动监测。若本轮中断，由Melodydt再次唤起，先查询该job终态并核对结果，禁止不检查就重复提交。
