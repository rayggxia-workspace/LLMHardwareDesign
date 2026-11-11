# Issue246容量研究交接

2026-11-09 Asia/Shanghai；Melodydt；规则rayggxia-project-collab1.0.0。仓库rayggxia-workspace/LLMHardwareDesign，project_id llm-hardware-design；[Issue246](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/246)/[PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，按用户当前会话在task/242-r-load-bounds继续，研究交付待审查/合并、不done；其他242/244/245独立待审范围保持。

源快照D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo（非Git checkout，无本地HEAD/暂存区），通过本人GitHub树/commit/ref lease上传。本轮已测源码8b18e0cb3efd3e8558d9930132282fbe551caf4e，最后文档head见PR；四功能源和15前轮依赖SHA保持。外层work/Melodydt/246为打包/完整回收副本，预生成源/大tar未上传；主快照仅白名单正式源、轻量证据、文档/本人进度交付。无生产RTL改动。

[报告](../experiments/issue-246-sram-capacity.md) · [证据/SHA](../../work/Melodydt/246/README.md) · [运行器](../../project/experiments/sram_capacity_study/README.md)。

服务器yuzelu@10.129.166.172，仅本人/public/home/yuzelu/Melodydt/issue246-sram/run01；source/为代码、inputs/为8个冻结输入、results/为全部结果和二进制。实际启动`cd /public/home/yuzelu/Melodydt/issue246-sram/run01 && sbatch --parsable job.sh`。Job101620/mdt-sram-cap，c64/node1/4核/UNLIMITED，4分02秒COMPLETED0:0；日志slurm-101620.log，终态sacct.txt，启动allocation.txt，结果results/result.json，完整输出清单output-files.sha256。无活动作业，未配置自动监测。

```bash
squeue -j 101620
sacct -j 101620 --format=JobID,JobName,State,ExitCode,NodeList,Elapsed -X
tail -n 35 /public/home/yuzelu/Melodydt/issue246-sram/run01/slurm-101620.log
cat /public/home/yuzelu/Melodydt/issue246-sram/run01/results/result.json
cd /public/home/yuzelu/Melodydt/issue246-sram/run01
sha256sum -c output-files.sha256
```

恢复第一步：读取最新AGENTS/Skill/本人身份/Issue及PR评论与head，运行本地`python -B work/Melodydt/246/verify.py`，核对同Job和SHA，无需重提已结束作业。28case、完整16KiB回归、原225 kernels/4 validation/5 smoke、oracle、7篡改拒绝、逐case容量负例及64KiB完整A流量断言均通过；35回收输出SHA匹配。工具GCC11.4.0/Python3.10.12/SystemC3.0.2，容器和库运行时SHA在tools.sha256。

结论：W8单独扩容16→64KiB为+7.13%，既有组合上容量增量+11.05%；48性能已近64，128在该decode无新增收益；prefill2约+21–23%。需要两个P各自扩容，U不动，保持S吞吐。P端口每64B占用2周期会抵消收益，这是成本敏感性不是测得新SRAM读延迟。48/64KiB实际新S_P地址/描述符/1RW仲裁/高地址负例/时序/物理/能耗仍未验，后续实现与独立审查人待指定。

登记PR5 pending；无board.json/Projects条目工具，看板unverified/同步pending，管理员待指定，须核对Project ID llm-hardware-design和Status In review并读回。CI沿PR实际失败/缺日志回执，不能把本地结构通过写成在线CI成功；管理员查看Actions注释处理。任务未合并不done。
