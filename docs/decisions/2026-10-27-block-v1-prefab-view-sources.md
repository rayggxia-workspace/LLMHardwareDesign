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

142已在2026-10-27 12:41 CST不可变部署，源码67afb20ebf672369314075279101497410ebf7bc、归档SHA256 c9e73f013304d5f5ac39bfe8b6cdabd3e4e37d9182149dbdd435146f99da06ee，154成员/1034240字节；dispatcher状态为空，无Slurm job，等待134/135整组成功。部署不是视图生成通过。

另设 `native-timing-model-probe-group`，在一个16CPU allocation内A/C各8CPU对133实际封存的最终T6K做只读模型导出和原生工具接口读回，先验证当前安装工具能否处理实际规模。该诊断可在独立物理接收尚未结束时执行，但逐文件核验生产者完整回执和最终五文件/准备pin来源，结束后重新检查源未变。其输出只叫`diagnostic.lib`，结果明确不具有物理/边界/功能/十二层/宏资格；正式视图入口不读取此文件。143拟用于这项实际诊断，尚未运行；是否得到完整接口与何种timing arc以真实回执为准，不能把准备代码当结果。

2026-10-27 12:49 CST：143/92226实际自然失败51秒，TotalCPU2:39.191、MaxRSS3002100K；两路都成功写出并由原生工具读入模型，各399个pin，但旧解析断言要求`get_full_name`返回库/cell前缀，实际安装工具返回的是局部pin名。保留组和两子任务全部失败回执，不把成功导出当完整诊断通过。修复为共享`native_lib_pins.tcl`：精确库/cell查询必须恰好匹配一个cell，错误库和错误cell查询均须为空，从限定查询返回的局部pin名构造完整身份，再与原准备pin方向逐项核对。正式视图和诊断使用同一脚本并保存其SHA；不接受未限定库/cell的裸名称。

142只部署、没有job，因使用旧读回假设而停用，不覆盖原不可变归档。144将执行修复后的两路实际诊断；145将保留原134/135整组成功依赖，部署修正脚本的正式四视图组。此时144/145尚未部署。13来源反例及4种真实stub编排控制在修复源码上再次通过，索引`view-controls-144.json`，仍不替代真实工具诊断或物理资格。

2026-10-27 12:54 CST：144/92227两路再次严格失败49秒，TotalCPU2:41.247、MaxRSS3184988K。限定库/cell及错库/错cell控制实际通过，386个真实signal bit全部存在且方向一致；额外查询对象为11个Liberty bus容器与VDD/VSS。原接收已区分PG，但尚未区分bus容器，故接口检查仍失败，原回执保留。模型分别360706/360660字节；均有31 combinational、195 rising_edge、189 setup_rising、189 hold_rising、各1 min/max_clock_tree_path，数量仅描述导出结果，不证明时序覆盖或边界精度。

共享脚本现按实际Liberty对象的`is_bus`与`member_iterator`区分bus容器，逐项证明所有成员也存在于同一限定查询且方向一致；容器及全成员表另存`lib-buses.tsv`，信号bit仍要求与全部原386端点精确对应，未知额外scalar pin继续拒绝。API参考[OpenSTA的bus成员展开](https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/sdc/Sdc.tcl)（2026-10-27读取）；当前容器上的实际执行另由新145诊断验证，不假定上游当前源码等于安装版本。编号用途更新：145用于此项修复后的双路实际诊断，146用于后续正式四视图；尚未部署，不复用144失败或142旧部署。

2026-10-27 12:59 CST：145/92228两路实际诊断全部通过，51秒、TotalCPU2:40.345、MaxRSS3108328K；一个16CPU allocation内A/C各8CPU。源码fb39b8cd33bb9ca5b3973a6677dd6a9fa0878e77、归档SHA256 ef2588f61d4f6d6dc3d8410b318fc9e3db262a0381ff438d858f08e0c9564d8d（156成员/1044480字节）。每路386信号bit完全对应、11个真实bus容器及全部成员保留；无缺失/额外scalar/方向错误，错库/错cell查询为空。共同脚本SHA256 cfa6c21cbb7351c02f184ea8bc0373d4ebbe9562be3eec6f492091186e0107ba。组与子回执见`run145-group-terminal`、`run145a-terminal`、`run145c-terminal`；143/144失败不改写。

正式两条新管线的视图入口现在还要求145完整成功组/子回执、全部实际接口门槛、同SHA共享脚本、逐成员bus表和同SHA实际OpenROAD程序。146将以当前新源码部署四视图组，等待134/135/145整组成功；此时146尚未部署。`view-controls-146.json`再次通过13来源反例及4种真实stub编排。145只证明实际模型导出和接口可读，不证明flat/abstract时序精度；标量输入约束、输入线阻、完整时序边界和一般十二层RC仍未通过。

2026-10-27 13:03 CST：正式四视图当前部署入口为147/node20/32CPU，依赖134/135/145整组成功，尚无Slurm job；源码0e65b27d5a57732a60a2c5ef42ab3b68da71eebe、归档SHA256 df998dd76f17b0e06b31507b32047a446fd37d33efa078582062239357b07d44（156成员/1054720字节），部署索引`run147-deployment`、stage143 manifest。146曾以完全相同归档部署到node21，同样无job，因141完整组合也固定使用node21且每个allocation申请整节点RAM，为避免等待其长任务而停用146，保留不可变索引`run146-deployment`；没有取消任何Slurm作业。147使用独立node20，后续可与141/node21及134/node23并行，仍由统一dispatcher计入最多8个本任务allocation。142/146都不再调度，不能把空部署写成运行或验收通过。最终计划文件SHA重新核验不变。
