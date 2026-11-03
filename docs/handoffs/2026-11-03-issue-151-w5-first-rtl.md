> 主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

# 主线五首轮RTL与服务器仿真交接

2026-11-03T19:19:42.298371+08:00，Asia/Shanghai。rayggxia-workspace/LLMHardwareDesign；project_id llm-hardware-design；Issue151 / PR152，负责人/认证Melodydt。
task/151-six-connection-study → task/143-seven-block-v2，输入9f63d50b7c1aa3d9ff62bc7a06e1391ba2460f70。实际源码分别unit a3ef3778502abfca279ff88a9ce47d33c73b9f16、native AF30a00e220108e4288a175087854fbebc1518df7c；最终资料head以PR读回和回执为准。

## 本地与远端边界
独立API部分包D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/h2-9f63d50/integrated，无.git/HEAD/index/暂存。沿已授权API继承固定树/白名单/expected_sha非force提交；原根参考、旧包和ref-project不覆盖。单位已上传7源，AF再5源，均逐内容/blob读回；其余本轮docs/证据/进度在本包待最终资料提交，不冒称main已合并。

## 真实服务器作业
服务器yuzelu@10.129.166.172，仅本人/public/home/yuzelu/Melodydt目录；使用既有SSH身份和已核验主机公钥，不依赖MobaXterm窗口，不读取或提交私钥。
任务根/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/w5-9f63d50-20261103。

1. unit96170/zenanyan-w5-unit/c64/8CPU/node1/u01，COMPLETED0:0/29秒，真实DMA29+mockSEQ30 PASS，19文本SHA实收。source16输入Git/serverSHA；日志slurm/zenanyan-w5-unit-96170.out/.err及runs/u01/logs，回执runs/u01/results/run-receipt.json。
2. native96183/zenanyan-w5-af/c64/8CPU/node1/n01，已观察RUNNING、compile exit0；18CASE/两完整G1/10流为预声明门，终态未核验。input-n01已34输入Git/serverSHA核对，实际sbatch --parsable submit-n01.sbatch；日志slurm/zenanyan-w5-af-96183.out/.err及runs/n01/logs；结果runs/n01/results/run-receipt.json。独立golden只读复用本人旧AF1024 r03/vectors/base及其原SHA，输入数据版本与新硬件source分开。

恢复第一步：先读Issue/PR最新头和本交接，核目录与是否有并行更新；然后在任务根执行：

```bash
squeue -j96183
sacct -j96183 --format=JobID,State,ExitCode,Elapsed,NodeList
tail -n40 runs/n01/logs/simulate.log
cat runs/n01/results/run-receipt.json
```

终态按真实exit/严格18CASE和10actual长度/SHA验收；源/数据/产物重核SHA，失败现场不覆盖。未结束不得写PASS，不因结束聊天取消作业，无已配置自动监测。若失败，先保存证据再新attempt/source，不能改有效检查只求通过。

## 功能与限制
[实施合同](../W5_CONTROL_FIRST_SLICE.md)、[unit报告](../W5_EDGE_DMA_AND_SEQUENCER_REPORT.md)。首ARM等真实parent start，终态已held后外部abort不更改其payload；原生A/F/边DMA及provider同cohort reset。真实目的SACK与capture不同；sourceT在edgeSACK后退休，整帧stored后native start，F0实际释放/DONE后F1。
ROM/metadata为永久内容读口的仿真模型，尚无上层金属位单元/读出/物理证明。无tag参数与ROM/provider必须cohort排空，不宣称独立warm-reset无限迟到安全。18case不覆盖G2/G3、RUN阶段新母控native错误或host输出prefix取消，不能转移旧内核独立覆盖。L4完整trained整数AF/新数据质量、R/NUM/D/H/X/MEM/物理各自保留。

## 交付状态与PDF
现阶段Issue实际in_progress，PR开放未合并/非done，外部审查和优先级待指定。登记PR5 pending，看板unverified/同步pending（无board.json/Projects item工具），处理人待指定，非已证实权限拒绝。
每步继续原路径覆盖既有本地七宏交流PDF，最终SHA/14页视觉QA以work/Melodydt/151/h2/local-PDF-index.json为准；不新建PDF版本/推Git/发他人。最终源码、状态与证据交付分别核验。

## 最终状态与恢复入口（替代上述排队/运行快照）

当前没有本任务在跑作业。最终源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU/COMPLETED0:0/00:03:01；12终态+18实际G1/10actualSHA通过。96170的29DMA/30SEQ保持独立证据；96183历史正常成功和96192观察窗口失败全部保留。
最终服务器source input-n03，输出runs/n03；日志slurm/zenanyan-w5-af-96208.out/.err与runs/n03/logs，回执runs/n03/results/run-receipt.json。无自动监测；恢复先读PR152/Issue151最新头，再核：

```bash
sacct -j96208 --format=JobID,State,ExitCode,Elapsed,NodeList
cat runs/n03/results/run-receipt.json
tail -n30 runs/n03/logs/simulate.log
```

本地74份文本与4份归档SHA索引在work/Melodydt/151/h2/evidence；四attempt122源/123数据出现记录postSHA通过，索引post-run-proof.json。所有大流bin与编译产物仅本人服务器，仓库没有波形或大二进制。原54源不改；新增5RTL/4TB，完成主线五G1首切片，非整个L5完成。
下一负责人Melodydt：外部审查当前PR后继续主线五产品级参数/编号预约、同RTL换表G2重入，再G3条件/选择与系统故障；原L4质量、R/NUM/D/H/X/MEM/物理门不跳过。Issue已读回status:in_review/非done；PR仍开放未合并；登记pending，看板unverified同步pending，处理人待指定。本轮源码、报告和证据已交付任务分支；最终head及检查回执以PR读回为准，main未合并。原交流PDF已同名覆盖14页，全页视觉QA及19链接/14固定commit目标读回通过，索引local-PDF-index.json；PDF未上传或发送。

