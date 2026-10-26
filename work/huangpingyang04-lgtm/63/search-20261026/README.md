# Issue63 通信优化实验精选证据

主实验源38bd309、19格×三方法×两轮；补充源b68f060、相同12主表格×强化贪心×两轮。两个源的主模型/搜索/独立checker/driver字节与当前发布一致；后续源仅新增强化贪心和测试。完整commit与Slurm/源码SHA见delivery和receipt。

- science.json：预定主实验/分块/搜索消融/小实例穷举，负例与退化均保留。comparison.csv可直接比较。
- receipt.json、replay_receipt.json：两个独立源码工作区、新进程的冻结输入/源码/结果SHA。science逐字节相同，SHA d7f6c3d847e3865493fff01a10b2f459f86f328e6f46bc5df93d7616efcdc14c。
- tie_science.json、stronger_greedy.csv：发现M0固定tie偏差后追加更强贪心，使用全部相同12格，不覆盖主表。两个源码副本的science SHA b0219fc13eb1b3410d430a5aa40be4ac0683a410dc9ae7776c1fd43a1cbdccb6。
- runtime01/02与tie_runtime01/02：真实算法耗时及源SHA；硬件节点/并发不同，禁止直接跨节点推断算法CPU加速，更不能当芯片时延。
- regression_receipt.json：最终源b68f060实际223 tests/0 skip、10旧场景独立复跑，原两图/expected/来源与#48原字节不变。primary_regression_receipt保存主表源的221项回执，历史不改。
- run.sbatch、tie.sbatch：实际Slurm脚本。原输出目录已存在，不直接重复运行脚本；复跑使用全新目录。development_failures保留开发失败的实际范围，不伪造完整日志。

原始DAG、全部计划、大mapping_request和stdout/stderr仅留delivery列出的服务器独立目录，不下载/上传大中间数据。没有读取或修改#55活动文件、作业；未安装软件。

从干净的新任务repo，经Slurm分配CPU后：

```bash
python3.11 -B -m project.analysis.workload_mapping.search_experiment --suite full --workers 4 --export --output-dir .local/runs/search-new
python3.11 -B -m project.analysis.workload_mapping.search_tie_audit --workers 2 --output-dir .local/runs/tie-new
```

所有容量、精度、内核能力、LRU/write-through/串行策略均为明确合成条件。M0/M1是合成matrix池命名，gemm_complete_rq要求显式full-K后RQ能力；不证明真实v2 M可免费融合V的RQ。接真实实例需重新确定RQ位置/跨块通信并复跑。没有实际模型权重/质量或真实物理时延/PPA结论。正式合同导出保留数据/通信/存储；重新调度必须同时读取workload.json中的显式控制依赖。主说明见docs/WORKLOAD_MAPPING_INPUT.md；PR79待审查、不合并、不关闭Issue。
