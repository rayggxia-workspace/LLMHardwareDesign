# 新预制候选的同源宏视图入口

任务：[Issue 121](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/121)，交付：[草稿 PR 122](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/122)。本条接续已批准的十层预制、两层定制计划，不改变资源、数值或制造边界。

当前 C8 采用 `native_pipeline_const_protected.json`（128 生产、134 独立接收），T6K 采用 `native_pipeline_viaonly.json`（133 生产、135 独立接收）。旧视图生成器不接受这两条新来源；不能把旧运行的 LEF/Liberty 配给新的最终 ODB/GDS。

新增 `native-prefab-view-<shared109|transaction6k>-<a|c>`，分别锁定上述管线。生成前逐项核验实际生产与接收回执、报告 SHA、top/policy/pipeline、源目录和源回执 SHA、全部物理门槛、零独立 DRC、原生详细路由零 DRC、RC 覆盖及完整最终 LEC。失败、历史合同、缺失门槛或另一候选的报告均拒绝。读取的最终 ODB/SDC/SPEF/Verilog/DEF、GDS 及 pin/PG/OBS 的原有逐项核验保留，另外记录管线文件、生成器和实际读回 Tcl 的 SHA。

`native-prefab-view-group` 在一个 32CPU allocation 内组织四路各 8CPU 的完整原生工具生成和读回，独立工作目录、日志、回执，一路失败后仍收齐其他分支。按实际 MemAvailable 与既有完整 C8 峰值 180451804 KiB 加 20% 余量选择 4/2/1 路；该峰值来自旧完整流程，并非新视图阶段的实测内存。部署依赖 134 与 135 整组成功；依赖未通过不得提前生成或借旧视图占位。此项不启动嵌套 sbatch。

可复现控制：

```powershell
python project/experiments/block_v1/native_view_control.py <全新控制JSON路径>
```

已执行 1 个显式合成来源正例、13 个坏来源/坏门槛反例，以及实际 stub 子进程四路/两路/串行/单路失败四种控制。反例全部拒绝，子进程实测重叠与声明并发一致，失败分支的其他三路回执保留。证据为 `work/YUZE-LU/121/view-controls-142.json`。这些是来源校验和编排控制，不能作为真实 EDA 或 CPU 利用率证据。

目前真实四视图尚未执行。即使生成与读回通过，产物仍为候选视图：原生 OpenSTA `write_timing_model` 的标量输入 setup/hold 及省略输入线阻问题尚需完整 flat/abstract 边界验证，不能用接口一致代替时序等价。记录继续显式保持 `flat_abstract_boundary_qualified`、`exact_final_function_qualified`、`twelve_layer_qualified`、`qualified_hard_macro` 为 false。父层所有真实 glue 的物理成本、完整恢复/epoch、一般十二层分布 RC/拼接、共同底座和两个产品仍有独立验收责任。
