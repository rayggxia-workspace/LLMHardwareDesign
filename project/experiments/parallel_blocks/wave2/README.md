# 三节点并行工作线

最新：第二轮七路均已完成，严格工具门槛接受ACT20／GEMM20／MXU20。ACT10零计数但负余量的原因及新CTS检查点定向修复见[修复记录](../../../../docs/experiments/issue-7-parallel-blocks-repair.md)。ACT修复已通过，合并块接续根15仍运行；新审计默认同时检查电容计数与最差余量。原冻结runner和历史失败不改写。

Refs [Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，延续同一草稿 PR #10。用户已明确同意三节点方案；与主线 VECTOR／PG 作业隔离。

- A／node7／64 CPU：ACT 电容裕量0、10、20，各16 CPU；原 RAM 行为与包装连接审计8 CPU，原 GEMM 回归8 CPU，总64。
- B／node8／64 CPU：GEMM裕量10／20、MXU裕量20、合并块裕量20，四路各16 CPU。各块分别判断，ACT的结果不自动授予其它块。
- C／node9／8 CPU：读取首批实际最终 ODB／SDC／SPEF，在新目录导出详细 LEF／时序模型，检查信号pin并形成不同宏别名；保留原电容失败，不作为合格宏。正式顶层对照依赖新块及视图核对，不在准备时占满64核等待。

所有Slurm作业 `--time=0`，提交与计算开始均核对UNLIMITED。各step `srun --exclusive`，总核数不超过实际allocation。无test墙钟超时；保留原测试本身的协议断言和cycle watchdog。一个step失败不取消其它step。

```powershell
python project/experiments/parallel_blocks/wave2/launch.py --attempt parallel-blocks-wave2-01
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-01
```

实际执行已推进到 `parallel-blocks-wave2-06`：89497／node7／48 CPU（三路ACT各16），89498／node8／64 CPU（四路大块各16），89499一次性afterany审计。功能验证及C准备已完成，不重新占用空槽等待。首试长TMPDIR触发ABC完成回执停滞，已保存证据并仅终止明确列出的停滞step；接续恢复首轮工具默认临时目录，不改RTL／SDC／ABC脚本或验收。完整故障、纠正采集和接线结果见[第二轮记录](../../../../docs/experiments/issue-7-parallel-blocks-wave2.md)。

```powershell
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-06
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-11
```

ACT三路已完成：0／10／20的电容计数2／0／0，但最差余量−2.65367／−0.77620／+2.44166，不能只以计数0判断通过。新根10的89508逐路核对825源＋154输出条目，严格工具门槛只有20通过，面积比0增加0.321716%，仍待宏资格检查。根11／89510 afterany89499及89511会对七路做相同独立审计，runner f46deb0已在ACT验证。06冻结runner不修改，06原计数门槛不替代11的严格结果。08容器内缺sacct的采集失败和未开始的09审计取消另存，所有物理输出原地保留。

新openTPU设计先按原probe所需的 `otpu_asic_top` 探测存储，随后只将新包装顶层改名为各自 `llhd_opentpu_*`，保证LEF／Liberty／网表身份一致。原RTL、参数、宽读接口、时钟与IO预算不改；电容裕量明确写入配置和实验记录。初轮runner和冻结结果不修改。

GEMM执行原 `tb/Makefile gemm`，固定seed1，EPILOGUE_FUSION0／1各500例，原物理对象只对应0；不是网表等价。openTPU执行原tech-RAM testbench的12种generic／ASIC逐周期对照（原6种加实际块所用6种维度），另核对实际elaboration的ACT–MXU逐bit连接、外部端口和存储资源；不是完整MXU数值回归或源到物理等价。

物理任务完成后从最终SPEF生成宏时序模型，并额外导出真实逐形状OBS；模型产生不代表电气通过。C只在自己的新目录导出旧结果，原数据库／SPEF不改；别名仅作用于派生视图，明确与原ODB名字区别。synthetic SRAM、未完整边界驱动负载及LEC_CHECK=0的限制继续适用。

三路结束后运行一次性afterany审计，分别核对源归档和新产物SHA，保存每路失败和工具门槛。监视器下载不可改写的completion并核对SHA；不声称临时侧聊提供后台助手通知。新任务以提交回执runner commit及计算节点脚本SHA绑定，后续提交不倒填为已执行版本。
