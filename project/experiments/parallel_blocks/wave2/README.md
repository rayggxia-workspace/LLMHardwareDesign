# 三节点并行工作线

Refs [Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，延续同一草稿 PR #10。用户已明确同意三节点方案；与主线 VECTOR／PG 作业隔离。

- A／node7／64 CPU：ACT 电容裕量0、10、20，各16 CPU；原 RAM 行为与包装连接审计8 CPU，原 GEMM 回归8 CPU，总64。
- B／node8／64 CPU：GEMM裕量10／20、MXU裕量20、合并块裕量20，四路各16 CPU。各块分别判断，ACT的结果不自动授予其它块。
- C／node9／8 CPU：读取首批实际最终 ODB／SDC／SPEF，在新目录导出详细 LEF／时序模型，检查信号pin并形成不同宏别名；保留原电容失败，不作为合格宏。正式顶层对照依赖新块及视图核对，不在准备时占满64核等待。

所有Slurm作业 `--time=0`，提交与计算开始均核对UNLIMITED。各step `srun --exclusive`，总核数不超过实际allocation。无test墙钟超时；保留原测试本身的协议断言和cycle watchdog。一个step失败不取消其它step。

```powershell
python project/experiments/parallel_blocks/wave2/launch.py --attempt parallel-blocks-wave2-01
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-01
```

新openTPU设计先按原probe所需的 `otpu_asic_top` 探测存储，随后只将新包装顶层改名为各自 `llhd_opentpu_*`，保证LEF／Liberty／网表身份一致。原RTL、参数、宽读接口、时钟与IO预算不改；电容裕量明确写入配置和实验记录。初轮runner和冻结结果不修改。

GEMM执行原 `tb/Makefile gemm`，固定seed1，EPILOGUE_FUSION0／1各500例，原物理对象只对应0；不是网表等价。openTPU执行原tech-RAM testbench的12种generic／ASIC逐周期对照（原6种加实际块所用6种维度），另核对实际elaboration的ACT–MXU逐bit连接、外部端口和存储资源；不是完整MXU数值回归或源到物理等价。

物理任务完成后从最终SPEF生成宏时序模型，并额外导出真实逐形状OBS；模型产生不代表电气通过。C只在自己的新目录导出旧结果，原数据库／SPEF不改；别名仅作用于派生视图，明确与原ODB名字区别。synthetic SRAM、未完整边界驱动负载及LEC_CHECK=0的限制继续适用。

三路结束后运行一次性afterany审计，分别核对源归档和新产物SHA，保存每路失败和工具门槛。监视器下载不可改写的completion并核对SHA；不声称临时侧聊提供后台助手通知。新任务以提交回执runner commit及计算节点脚本SHA绑定，后续提交不倒填为已执行版本。
