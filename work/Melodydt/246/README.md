# Issue246容量研究轻量证据

来源：本人Slurm101620，冻结源8b18e0cb3efd3e8558d9930132282fbe551caf4e，28case均通过。[报告](../../../docs/experiments/issue-246-sram-capacity.md) · [源码](../../../project/experiments/sram_capacity_study/README.md) · [交接](../../../docs/handoffs/2026-11-09-issue-246-sram-capacity.md)。

index.json记录源码/输入/生成模型/工具版本/完整结果SHA以及17个轻量证据SHA；summary.json含全部28case，speedup比较同策略16KiB，bus_bytes为整条trace字节（prefill2有2token）。保存三份原始完整case JSON和检查日志。source-files/input-files/output-files清单对应服务器，未回收路径仅服务器保留，不冒称已下载。allocation为启动RUNNING快照，sacct才是终态。

登录yuzelu@10.129.166.172；`/public/home/yuzelu/Melodydt/issue246-sram/run01`保留大trace/完整result.json/全部日志/二进制；本地外层work/Melodydt/246/run01为打包/回收副本，未上传大包。35份回收输出SHA核验通过。没有新RTL、真实权重数值或物理/能耗资格。

```bash
python -B work/Melodydt/246/verify.py
```

仅核对回执和已测功能源，不启动仿真。Issue246/PR243待审查/合并，登记pending，看板unverified/同步pending。负责人Melodydt，规则rayggxia-project-collab1.0.0，2026-11-09 Asia/Shanghai。无活动作业/自动监测。
