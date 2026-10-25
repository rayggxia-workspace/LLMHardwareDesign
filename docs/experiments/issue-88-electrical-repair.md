# Issue88：有界电气修复与完整消费者门级接收

任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/88。负责人 Liangruizhi，基于 Issue86 e3a8fee 的原 Issue84 四种静态变体。执行服务器为本人获授权 CPU Slurm；本机只编辑源码、核项目结构、接收归档字节与原 Git 源码。未修改 Issue55/63、参考资料包或其他成员目录。

## 问题与约束

Issue86 的原始标准单元网表已通过选定完整整数消费者，却存在数千个 slew/cap 违例。不能从这些未修复路径的诊断周期宣称硬件时钟。本任务检验在同一研究库和接口切分下，显式补计缓冲、tie 与驱动成本后，原功能、面积排序和受限时序能否成立。

固定 Nangate45 typical1.1V/25C，原 store82 整体切分，所有非 clk/reset 存储引脚作为端口；10ns 理想时钟，uncertainty0，输入/时钟转换0.05ns，max IO delay0.1ns/min0，输出分别1/10fF。四变体均用400×400um研究core/die与50%上限，即80000um²单元预算；没有实际 placement、线寄生或CTS。库存用原Liberty Decimal面积、Yosys stat和LEF SIZE交叉验证。固定上限相同，不代表四种设计实际占用面积相同。

## 修复配方与保留失败

1. 原 cut.v 常量经 hilomap 显式使用库中 LOGIC0_X1/LOGIC1_X1，保留库 dont_use/dont_touch 定义；repair_tie_fanout 最大16，所有tie拷贝按0.532um²计价。
2. 第1遍：repair_design -pre_placement -max_utilization50 -slew_margin0 -cap_margin0。
3. 第2遍：repair_timing -hold -hold_margin0.005 -max_passes1 -max_iterations1 -max_buffer_percent10 -max_utilization50。
4. 第3遍：再且仅再执行一次与第1遍相同的电气修复。没有频率搜索或无穷循环，四变体统一 phase7@835f330。

初次pilot-v301因 OpenROAD 导出丢失8个恒0输出而被 Yosys check-assert 拒绝，后续依赖任务未运行并取消。不能把未驱动输出默认0当作通过。pilot-v302显式tie后通过接口检查，但仍465个hold违例，最差-0.002446ns；pilot-v303补129个hold buffer后hold全过，却新出现一个1147.024fF负载节点的slew/cap违例。任务负责人据此批准统一增加第三遍上限，所有原始失败和源版本保留。另一次接收作业90778在gate未结束时过早启动而缺少manifest；随后改为afterok依赖，记录为流程失败，不是数值失败。

## 独立验收范围

受控功能输入为原始Granite L0T0、8专家、K512、H1536的完整消费者；每次6291456次MAC，后接重新量化、专家merge、残差与norm。每个变体覆盖quiet与backpressure，复用原始真实打包输入；独立NumPy/Python整数参考核全部acc/down/join/out及计数，并逐字段与原84同配置RTL输出相同。保留实际active reset/no stale completion/SRAM retained三项严格布尔协议。不是8个模型或完整模型质量实验。

结构接收独立重新解析原86 Verilog，从原Liberty识别BUF/INV/tie，按输入端口或原逻辑单元输出建立规范连接签名；逐位比较所有原cell/pin和所有top/cut端口，原寄存器时钟/数据/控制连接也在其中，新增单元只允许透明BUF/INV/tie。检查电气报告BEGIN/END执行标记、全DFF以及全部非恒定输出的setup/hold端点集合；常量输出明确排除。负例包含实际写盘重读的输出码、常量端口、DFF数据连接、协议缺失/错误类型及config类型。

## 结果

最终8条完整消费者门级重放、独立整数参考、原全cell/pin/port规范连接、Liberty/LEF/Yosys面积、严格配置/协议与真实负例均通过。4变体×2负载的内部slew/cap及全部非恒定端点setup/hold均为0违例；接收的总体 `all_variants_internal_electrical_setup_hold_closed=true` 仅适用于上述受限研究条件。

|变体|A缓存|重定标乘法器|原逻辑面积um²|修复后um²|修复增幅|新增BUF/tie；原单元resize|周期：无背压/背压|最差全setup slack(ns)|最差hold slack(ns)|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
|v0|关|独立|57603.630|63947.730|11.013%|2964/40；2589|9061831/10690375|4.249933|0.005719|
|v1|关|共享|50130.626|55713.966|11.138%|2823/40；2015|9061831/10690375|4.508835|0.005719|
|v2|开|独立|58961.028|65404.878|10.929%|3132/8；2569|5919175/7155270|4.140689|0.005719|
|v3|开|共享|51627.142|57432.858|11.245%|2945/8；2013|5919175/7155270|4.400804|0.005717|

两档输出负载的上述最差值相同。v0/v1分别覆盖3582/3583个DFF，全部setup/hold端点4725/4726，40个原恒0输出单独豁免；v2/v3覆盖3744/3745个DFF，端点4919/4920，8个恒0输出豁免。没有新增或删除寄存器，没有修改原逻辑函数；新增单元仅为计价的BUF与tie，原组合单元另有2589/2015/2569/2013次同函数drive-strength变更。最终完整库存已逐cell按Liberty计算，所以这些resize的面积也包含在总成本中。OpenROAD迭代进度表的Resized0不能当作最终前后网表差分为零；本报告以独立inventory为准。check_setup报告未发现无时钟或未约束端点；输入接口和全部存储切分位保留。

这支持两个有限结论：在固定库/切分/功能与预算下，重定标乘法器共享的标准单元面积优势在计入电气修复后仍成立（无缓存约12.88%、有缓存约12.19%）；A缓存仍保留原周期减少约34.68%/33.07%的效果，修复未改变周期、端口事务或数值。上述数字不是整Block面积、目标芯片速度或模型端到端质量。每个方案的面积实际不同，比较的是相同约束与预算下的代价。

控制/保持树的物理代价不可忽略：一次hold修复会把负载集中到单个新增buffer，需第三遍分散/增强驱动才能同时满足内部slew/cap与hold；最终缓冲、tie与原单元驱动增强合计使标准单元面积增加约10.93%–11.25%。这说明Block边界不能只看算术原语面积，控制扇出和接口驱动也要记账。


## 使用结论的边界

固定input slew没有建模外部driver阻抗，clk仍为理想网络。因此内部电气检查通过不能解释为上游接口/clock-tree负载合格。逐input/cut bit的直接sink数量、首级透明单元、nominal/max-rise-fall电容与output alias负载见inputs-v*.json；不能用把负载推到边界冒充全接口优化。tie的布尔函数/面积存在，但此库未给tie输出完整时序/最大负载约束。

研究库、单一典型角、零线RC、整store82切分、行为存储门级重放，均不能证明目标SRAM/ROM、版图布线、跨PVT/CDC、真实全Block Fmax或制造资格。原Issue84静态设计的结果不传给Issue85/92新增runtime/epoch硬件。后续最小物理研究可在同cut与同负载下做已有LEF的placement/估计线RC；真正全Block交付仍需目标工艺/PVT、时钟/IO预算、实际存储宏视图和clock/reset方案。

## 复现与交付

源码、命令、Slurm资源、工具版本/SHA、输入版本、失败日志与结果位置以work/Liangruizhi/88/execution.json、11个冻结phase binding和delivery-index.json为准。精确source/reception/工具链commit由索引给出，不能拿最新HEAD替代旧执行版本。所有输出目录要求新建，不覆盖既有结果。主会话统一push/PR/Issue/看板；本子任务未推送、未开PR、未自行合并。

最终57个自有作业全部结束：51 COMPLETED、2 FAILED、4 CANCELLED。失败为原导出常量缺失和一次过早接收；4取消均是原失败准备步骤的未执行依赖。最终独立接收为phase10@e98a16f，工具/归档为phase11@c85c993；11阶段98份原Git源码均逐字节核验通过。

- `full-results.zip`：128079530字节，851成员，SHA-256 `c9ae7a88887a3a987f25a499f6cdd940f41164fe9705c594eb2b969457627c25`；服务器位置 `/public/home/yuzelu/RuizhiLiang/issue88-electrical-repair-20261025/delivery01/full-results.zip`。
- `selected.zip`：5378081字节，738成员，SHA-256 `b8e5775d469ab787f412ad93329a1238ce9c4f2becfe2f9ecfffa53845cffefd`；服务器位置 `/public/home/yuzelu/RuizhiLiang/issue88-electrical-repair-20261025/delivery01/selected.zip`。

完整/精选包服务器逐成员校验通过；精选包本机738成员字节核验通过。完整包128.08MB留授权服务器，5.38MB精选包进入仓库；后者含数学接收、真实输出、时序/负载/源绑定，不能替代原始完整数据重跑。
