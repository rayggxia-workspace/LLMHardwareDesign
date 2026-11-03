> 主线五G1首切片最终：源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU自然COMPLETED0:0/3分1秒；12终态定向+18实际AF及10actualSHA通过。另unit96170的DMA29/SEQ30通过，共89项不同预声明检查，非全图证明。n01/96183原18项成功、n02/96192失败及12项组件成功均保留，不把失败整合当通过。当前无本任务在跑作业、无自动监测。

# 主线五首轮共同控制与边存储实验

Issue151 / PR152，Melodydt，2026-11-03T19:19:42.298371+08:00（Asia/Shanghai）。
输入9f63d50b7c1aa3d9ff62bc7a06e1391ba2460f70；unit源码a3ef3778502abfca279ff88a9ce47d33c73b9f16，实际AF源码30a00e220108e4288a175087854fbebc1518df7c。所有源码先推Git并核Git/server SHA再运行，旧54runtime不改。

- unit-contract/run_units：真实S DMA29与mock服务母控30，96170/u01/node1/c64/8CPU/COMPLETED0:0/29秒，59CASE PASS。7+17 warnings非lintclean。
- af-contract/run_af：新共同表控制、真实A/F和真实接收SACK，两完整G1/18CASE/10actual流预声明；96183/n01已提交并实际RUNNING node1，编译通过，终态及数值尚待实收。
- build_control_tables：H1 little-endian记录转成仿真只读numeric memory视图，含256×128bit ROM/17×512bit metadata，非启动装载或制造ROM。
- evidence/units-u01：19份实际文本、source manifest/Slurm脚本/日志/生成表，逐SHA实收；无二进制/波形Git上传。

冻结输入为本人既有AF1024 base向量（原source b3e14e27），每份只读核原fixture-contract及独立数学来源SHA。host4096B、参数7168B、A6MiB/F18MiB、输出4096B分别计价，不假定MEM或参数缓存免费。
下一等待实际AF终态并逐CASE/10streamSHA核验；未通过不将其记为已验证共同A/F。G2/G3、RUN错误与hostprefix取消、异步MEM/金属ROM/物理及主线四trained质量仍后续门。所有仿真仅本人服务器；没有自动监测配置。

## 最终状态与恢复入口（替代上述排队/运行快照）

当前没有本任务在跑作业。最终源码7a656a3fe4a86342d24b72ebecdc524052bf86d7，96208/n03/node1/c64/8CPU/COMPLETED0:0/00:03:01；12终态+18实际G1/10actualSHA通过。96170的29DMA/30SEQ保持独立证据；96183历史正常成功和96192观察窗口失败全部保留。
最终服务器source input-n03，输出runs/n03；日志slurm/zenanyan-w5-af-96208.out/.err与runs/n03/logs，回执runs/n03/results/run-receipt.json。无自动监测；恢复先读PR152/Issue151最新头，再核：

```bash
sacct -j96208 --format=JobID,State,ExitCode,Elapsed,NodeList
cat runs/n03/results/run-receipt.json
tail -n30 runs/n03/logs/simulate.log
```

本地74份文本与4份归档SHA索引在work/Melodydt/151/h2/evidence；四attempt122源/123数据出现记录postSHA通过，索引post-run-proof.json。所有大流bin与编译产物仅本人服务器，仓库没有波形或大二进制。原54源不改；新增5RTL/4TB，完成主线五G1首切片，非整个L5完成。
下一负责人Melodydt：外部审查当前PR后继续主线五产品级参数/编号预约、同RTL换表G2重入，再G3条件/选择与系统故障；原L4质量、R/NUM/D/H/X/MEM/物理门不跳过。Issue待审查/非done；登记pending，看板unverified同步pending，处理人待指定。当前本包本轮文档/证据等待最终资料commit，最终回执以PR读回为准，不冒称main已合并。

