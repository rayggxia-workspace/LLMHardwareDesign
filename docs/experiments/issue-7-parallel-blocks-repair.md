# Issue #7：严格电容验收与检查点定向修复

- 日期：2026-10-21，中国标准时间（UTC+08:00）。Refs [Issue #7](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/7)，延续[草稿 PR #10](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/10)。
- 本页只记录并行工作树自己的实验；主线 PR #8 的 VECTOR／PG、状态页、工作树和作业均未改动。
- 原始物理根为 `yuzelu@10.129.166.172:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06/`。本轮在新根12–16保存修复、失败和诊断；原始输入与冻结runner不改写。

## 第二轮完整终态

89497／node7／48 CPU已完成6:00；89498／node8／64 CPU已完成45:14，四路大块各16 CPU。89499产物审计完成45秒，89510／node9／1 CPU严格审计完成1:54，89511封存完成5秒；均COMPLETED0:0、UNLIMITED。已取回并验证[06冻结终态](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-06-completion.json)和[11严格审计终态](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-11-completion.json)，不再描述为仍运行。

| case | max-cap计数 | 最差电容余量 fF | setup WS ns | hold WS ns | 非filler实例面积 µm² | 本次严格工具门槛 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| ACT／0 | 2 | −2.653673 | 1.225990 | 0.032272 | 35,870.1 | 未通过 |
| ACT／10 | 0 | −0.776201 | 1.210240 | 0.030058 | 35,899.1 | 未通过 |
| ACT／20 | 0 | +2.441659 | 1.260070 | 0.032226 | 35,985.5 | 通过 |
| GEMM／10 | 8 | −5.769668 | 0.786571 | 0.037556 | 472,359 | 未通过 |
| GEMM／20 | 0 | +0.221413 | 0.775024 | 0.051811 | 473,321 | 通过 |
| MXU／20 | 0 | +0.842449 | 0.242689 | 0.051380 | 429,634 | 通过 |
| ACT＋MXU／20 | 4 | −6.343030 | 0.488026 | 0.041573 | 461,456 | 未通过 |

七路均DRC／天线0、setup／hold TNS0、slew／fanout计数0；上述通过只表示列出的工具预算门槛，仍不是完整宏资格或系统／制造签核。GEMM／20的正电容余量尤其小，后续改变边界负载、宏布局或预算后需要重新验证。

## ACT／10为何计数0仍不接收

同一镜像中首先读取的Nangate45 Liberty和合成SRAM Liberty均为 `capacitive_load_unit (1,ff)`，最终SPEF为 `*C_UNIT 1 PF`。因此本组报告原始电容值可以核对为fF；以前冻结记录保留其当时“单位待核实”的原文，不回填修改历史。

计数端采用 `fuzzyLess(slack, 0)`，接近零的绝对容差为 `1e-15 F ≈ 1 fF`。实际镜像中可执行文件的 `sta::fuzzyEqual` 反汇编也读取此常量：地址 `0x1531708` 的小端字节 `7d1d9026` 为 `1.0000000036274937e-15`。所以−0.776 fF会被违例计数忽略，直接余量报告仍为负。这是固定绝对容差造成的筛选差异，不能将其当作余量已非负。上游依据：[电容检查](https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/search/CheckCapacitances.cc)、[零值容差](https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/util/Fuzzy.cc)。上游链接用于解释逻辑；本次证据另绑定实际镜像、可执行文件及反汇编，未编造工具源码revision。

具体匹配到 `_5406_/Z`（MUX2_X1），对应网 `u_act.g_row[1].g_pc[0].u_act.ra[4]`：最终线电容46.2773 fF，三个SRAM读地址输入各5 fF，合计61.2773 fF；驱动限制60.5011 fF，复算余量−0.7762 fF，与最差报告吻合，超出1.283%。全局布线阶段的最差余量仍为正，负值出现在详细布线后提取；不同阶段的最差值不当作同一根网的逐阶段差值。

同一地址网在ACT／0的线电容为43.2899 fF，ACT／10为46.2773 fF；裕量参数不会使所有网单调改善。ACT／20在该MUX后插入BUF_X4，使MUX侧线电容降至1.82237 fF。问题证据指向块内地址分发和布线负载，不据此否定Block划分。

89513／node9／1CPU独立诊断完成19秒，实际runner `5ff95b7`；[诊断原字节](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-12-diagnostic.json)已按计算节点输出manifest核对SHA：`0712fdfc7530ab2acd070036cf3fff3f11b0e7be7757c99f701c41aed3210ace`。原反汇编、输入SHA留在根12的 `cap-diagnostic/`。

## ACT定向修复已通过本次工具门槛

用户授权修复后，从ACT／10的原 `4_cts.odb/.sdc` 检查点复制到新根12，逐文件对照原输出manifest SHA后再复制并核对。保留原电容裕量10、参数、RTL、时钟和IO预算，只将 `_5406_` 从MUX2_X1换为MUX2_X2，在全局布线前重新合法化，随后重新执行全局／详细布线、寄生提取、最终报告和宏视图导出。未重跑综合／放置／CTS，没有向原目录写入。

89512.0／node7／16CPU完成4:07、COMPLETED0:0，实际runner `5ff95b7`。89514独立产物／严格门槛审计完成，ACT修复路825项源文件和89项输出manifest校验全部通过。

| ACT／10 | 修复前 | 定向修复后 |
| --- | ---: | ---: |
| 最差电容余量 fF | −0.776201 | **+1.218952** |
| 电容余量／限制 | −1.28295% | **+7.60813%** |
| max-cap／slew／fanout计数 | 0／0／0 | 0／0／0 |
| DRC／天线 | 0／0 | 0／0 |
| Setup WS ns | 1.210240 | 1.206690 |
| Hold WS ns | 0.0300581 | 0.0314514 |
| 非filler实例面积 µm² | 35,899.1 | 35,899.6 |

修复后setup余量约减少3.55ps，仍为正；面积仅约增加0.5µm²。冻结证据：[12终态](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-12-completion.json)。ACT／20继续保留为余量较充足的候选，修复后的ACT／10是面积更小的备选，两者均待完整宏资格检查；未追溯修改原ACT／10的未通过结论。

未来作业的 `audit.py` 已增加最差电容余量和归一化余量非负、setup／hold TNS、天线及slew／fanout余量检查。基于七路冻结数据的回归验证只接受ACT20／GEMM20／MXU20，明确拒绝计数0但余量负的ACT10；缺失及非有限余量也拒绝。已提交06／11／12的runner和终态都保持原样。

## 合并块接续及保留的失败

原合并块／20有4处负电容余量：MXU移位寄存器Q端−6.343 fF、place15504/Z约−4.90 fF、place15492/Z约−1.27 fF、place15563/Z约−1.00 fF。新接续将原DFF_X1替换为DFF_X2，后三个BUF_X1替换为BUF_X2；同样从原CTS检查点续跑，不重做其它已通过块。

- 根12／89512.1：原最终报告实例名在CTS的OpenDB名称空间中未直接匹配，校验立即退出1，12秒。A批次因该路失败仍为FAILED1，不能用ACT路通过或89514产物审计通过覆盖它。
- 根13／89515：改为输出网定位后，未转义的总线名仍未匹配，12秒退出1；89516仅对失败产物校验通过。
- 根14／89517：Python百分号格式化误解释Tcl `format %c`，7秒退出1；89518只封存失败产物。该生成器错误由本次修复脚本引入，未进入EDA修改。
- 根15／89519／node8／16CPU：实际runner `bb0994d`。生成器改用明确占位替换，增加Tcl解释器回归；输出网按去除OpenDB转义后的完整名称唯一匹配，实际找到带 `\[1\]` 的寄存器驱动，4项单元替换日志均已写出，正在重新布线。89520为一次性afterany审计，均UNLIMITED。

三个失败尝试及其非零退出、输入和产物均保留：[12](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-12-completion.json)、[13](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-13-completion.json)、[14](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-14-completion.json)。Tcl解释器回归执行了普通名、带总线转义的网／实例名、缺目标和错误单元类型四种情况；后两种在修改前拒绝。这只检查生成器，不冒充OpenROAD物理验收。

## 宏视图与后续

已通过工具门槛的ACT20／MXU20／GEMM20视图均存在，LEF信号pin数量为860／2172／3753，Liberty timing group数量为910／3553／5894，均有详细OBS。但三个时序模型均无 `minimum_period/min_period`，完整arc覆盖、内部周期约束传递、相邻块驱动／负载、PG几何及源到物理等价仍待验证，`qualified_hard_macro=false`。

根16的89521／node9／1CPU及89522后处理均已COMPLETED0:0（16秒／6秒），实际runner `034b02c`；MUX2_X1/X2、BUF_X1/X2、DFF_X1/X2的Liberty端口逻辑／顺序状态方程签名均相同。这是局部替换依据，不能替代整份最终网表的形式等价。[16诊断原字节](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-16-diagnostic.json)SHA为 `419d6f7bea6f93bcf81a8cff3913bc16d553e5848da4d1efaecf220bd13d7e91`；[16冻结审计](../../project/experiments/parallel_blocks/results/parallel-blocks-wave2-16-completion.json)SHA为 `a7a7bf214ddd41e0e102762d74132d58a9a3208ebcf39dcd6666cc9c2ca4f6e1`，已核对。

恢复入口：

```powershell
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-15
python project/experiments/parallel_blocks/wave2/monitor.py --attempt parallel-blocks-wave2-16
python project/experiments/parallel_blocks/wave2/check_quality_gates.py
python project/experiments/parallel_blocks/wave2/check_repair_hook.py
```

先核对15和16的实际终态、严格门槛与SHA，再选择宏和同die顶层对照。暂未新启动正式顶层PNR，不宣称H2固定底座或制造签核。所有新作业无墙钟截止，未按耗时终止任务；临时侧聊不具备定时助手唤醒，已提交的只是一次性Slurm后处理。
