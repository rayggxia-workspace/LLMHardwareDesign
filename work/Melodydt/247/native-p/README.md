# Issue247 原生P实现与服务器证据

用途：保存本轮仲裁、固定16KiB bank并发、八组S64上下文与A复用的源码/输入/输出追溯。来源：本人获授权服务器的run10/11原始结果；不包含ref-project资料。

[详细方案](../../../../docs/experiments/issue-247-p-native-optimizations.md) · [完整M逐case分析](context-analysis.md) · [机器摘要](summary.json) · [逐原件索引](index.json) · [交接](../../../../docs/handoffs/2026-11-09-issue-247-p-native.md)。

| 运行 | 源码commit | 作业/终态 | 作用 |
|---|---|---|---|
| run10 | c2359bdeeea83270ab632861eebe6ffc8dcc510e | 101756，COMPLETED0:0，1:21 | 四组件完整回归 |
| run11 | 24f720a788328bd8d73e2bf1a3b0502ded9b937b | 101758，COMPLETED0:0，1:05 | local无背压/32拍背压与B-only边界、P完整释放计时 |

两轮均`yuzelu@10.129.166.172`、c64/node1/4核/UNLIMITED，目录`/public/home/yuzelu/Melodydt/issue247-area-speed/run10`与`run11`。源码`source/`，日志`slurm-<job>.log`，结果`results/`。实际启动分别为工作目录内`sbatch --parsable job.sh`及`sbatch --parsable --export=ALL,POPT_COMPONENTS=integration job.sh`。所有作业已终态，无活动仿真，未配置自动监测。

完整输出仍在服务器；`output-files.sha256`分别记录800和629项，包括未回收二进制/对象文件。轻量归档已逐字节SHA回收，104与66项结果校验通过；仓库索引保存185份轻量原件，含必要JSON、日志和JSONL。`.gz.b64`是gzip后base64，mtime固定0，仅压缩，不改原内容。索引同时记录存储字节和解码原字节SHA。`collect.py`是终态采集器，不提交/取消作业，不修改源。

在仓库根目录离线验证：

```sh
python -B work/Melodydt/247/native-p/verify.py
python scripts/check_project.py
```

第一项验证原件SHA、实际作业终态、163份已策展结果、29份当前功能源、132个M参数/场景的独立工作和周期守恒、旧接口精确回归及完整P释放成本；生成`summary.json`。第二项仅管理结构。正式服务器执行命令见[实验README](../../../../project/experiments/p_native_opt/README.md)。不得将离线复核说成重新执行RTL。

run10主结果SHA `97de764fffa64b9eb151204af74f94e4d53ea4cabd1f5b5e96c292a0e75bdec0`；run11 `0061270c92a28004e87c0eb3dd69dcd3e0bfd0da6ba97d8bec69d89588fd71f2`。两轮15份生产RTL的SHA完全相同。固定输入嵌入测试程序，来源/版本由实际source commit及清单锁定；不涉及真实模型权重或KV。

验收边界：新功能默认关闭，已通过RTL回归；真实DMA预取描述符/信用、完整控制镜像、整模型生成、面积/STA/P&R未验收，SRAM扩容未实装。Issue保持待独立审查，未合并不done。登记PR5 pending；看板unverified/同步pending。GitHub CI与最终上传状态以交接及PR实时回执为准。
