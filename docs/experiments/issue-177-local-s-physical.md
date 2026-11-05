# 局部 S：布局布线与 300MHz 验收

2026-11-04 21:42 CST。对应 [Issue177](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/177) / [PR178](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/178)，设计入口为[文档PR176](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/176)。P4/N4/N5三种新增局部S实现均完成实际布局布线，并通过同一封存来源的物理、DRC、最终网表功能和严格LEC四门；六文件及版图图像已接收并逐项核验SHA。PR供独立审查，未合并。

## 实测结果

| 配置 | setup最小裕量(ps) | hold最小裕量(ps) | 真实时序端点数 | active面积(um²) | 最终网表检查数，三初态合计 | 原生 / 完整GDS DRC项数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P4：4客户＋真实feeder | +17.824 | +7.652 | 134,633 | 1,189,952.862 | 254,070 | 0 / 0 |
| N4：4客户，无feeder | +94.092 | +11.531 | 131,875 | 1,174,074.790 | 60,873 | 0 / 0 |
| N5：5客户，无feeder | +100.396 | +5.617 | 132,007 | 1,176,514.808 | 60,978 | 0 / 0 |

时钟为3.333333333333ns（300MHz），P4的die为1850×1850um，N4/N5为1670×1670um，真实16KiB、四bank标准单元存储。active面积按最终ODB中有信号引脚的单元master宽×高累计；物理填充等单元另计，不能将此值当作die面积、SRAM编译器面积或与旧全局S同条件的开销对照。没有进行受控的全局S/局部S PPA比较，也没有测量功耗。

N4对应U/F/J的四普通客户合同，N5对应C的五普通客户合同；P4包含四普通客户和真实512bit feeder。它们是三类独立叶宏实现，未声称九个实例已在完整芯片内同时布局布线。九实例/144KiB跨Block隔离属于[原RTL结果](issue-177-local-s-results.md)。

| 配置 | LEC完整匹配输入 / 输出 | 严格判定 | 原始报告 |
| --- | ---: | --- | --- |
| P4 | 267,511 / 268,088 | UNSAT / IDENTICAL；未匹配边界0 | [物理](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-p4setup-20261104T054519Z/gates/p4/physical/five-macro-physical.json) · [DRC](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-p4setup-20261104T054519Z/gates/p4/drc/five-macro-drc.json) · [功能](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-p4setup-20261104T054519Z/gates/p4/function/final-function.json) · [LEC](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-p4setup-20261104T054519Z/gates/p4/formal/formal.json) |
| N4 | 263,274 / 263,229 | UNSAT / IDENTICAL；未匹配边界0 | [物理](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-production-20261104T023042Z/gates/n4/physical/five-macro-physical.json) · [DRC](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-production-20261104T023042Z/gates/n4/drc/five-macro-drc.json) · [功能](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-production-20261104T023042Z/gates/n4/function/final-function.json) · [LEC](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-production-20261104T023042Z/gates/n4/formal/formal.json) |
| N5 | 263,419 / 263,363 | UNSAT / IDENTICAL；未匹配边界0 | [物理](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-holdeco-20261104T040639Z/gates/n5/physical/five-macro-physical.json) · [DRC](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-holdeco-20261104T040639Z/gates/n5/drc/five-macro-drc.json) · [功能](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-holdeco-20261104T040639Z/gates/n5/function/final-function.json) · [LEC](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-holdeco-20261104T040639Z/gates/n5/formal/formal.json) |

全部真实端点setup/hold非负，原生违例计数均0；电容和转换违例均0。实际RC覆盖、所有使用信号驱动、PG连接、固定M10接口、边界与输入接收器检查通过。未增加slack公差、false path或multicycle例外。

最终完整信号网表的功能检查共375,921次，分别运行全0、全1、随机初始化（Verilator初始化种子177/178/179），请求随机种子固定177；这不是三个不同请求向量集合。覆盖全1024字地址写读、普通口争用公平、随机返回背压、owner保持、reset取消及已写内容保留；P4另检查真实feeder的rows1/5/8、tiles1/4、A/B格式、B复用，以及A/B连续100周期背压下普通口至少10笔进展。功能仿真为零延迟，实际延迟由独立SPEF STA检查。每组两笔请求由定向reset取消，不计作漏返回。

严格LEC比较实际最终信号网表与原综合状态边界，明确要求UNSAT、IDENTICAL及所有正数PI/PO完整匹配；DFF数据/时钟/输出与布尔投影负控制独立重跑。输入型ANTENNA_X1仅在LEC布尔投影中按原合同处理，实际物理及功能网表保留。库中未使用单元的解析警告不能替代对实际使用单元的模型审计。

## 约束与规则

Nangate45 typical，原生M1–M10；M10固定信号引脚，真实BUF_X8输入接收器及输入保护。uncertainty0.1ns、clock transition0.05ns、输入/输出max0.8ns和min0.2ns、BUF_X2外部驱动、50fF输出负载。原生流程中更严格的3.3333ns时钟保留，最终封存使用经过同工具精确序列化控制验证的批准预算；未更改其他预算。

DRC对实际完整最终ODB执行原生检查，对从相同最终DEF生成的实际GDS执行完整原始FreePDK45.lydrc，包含原规则集的antenna检查，无排除或豁免；规则集SHA-256为`4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147`。这是提供的开源规则集验收，未新增原规则集本来没有的规则，不能当作代工厂制造签核。

## 成功来源与作业

所有任务输出均在获授权的`/public/home/yuzelu/PingyangHuang/`新目录，任务名hpy-*，长任务经Slurm c96/UNLIMITED、每作业16CPU执行；未修改旧工程、其他人的文件或作业。下表作业顺序为物理 / 完整DRC / 功能 / 严格LEC / 本来源交付，实际终态见[调度回执](../../work/huangpingyang04-lgtm/177/physical-evidence/sacct.txt)。

| 配置 | 封存实现目录（上述前缀下） | 执行源码commit | 作业ID |
| --- | --- | --- | --- |
| P4 | `issue177-s-p4setup-20261104T054519Z` | `7a8f71dc2164e27aca3e064863d219d5f4840407` | 97131 / 97132 / 97133 / 97134 / 97135 |
| N4 | `issue177-s-production-20261104T023042Z` | `7c5314374f2a458bdab7af5bc89a33ce52b6cc68` | 97035 / 97036 / 97037 / 97038 / 97039 |
| N5 | `issue177-s-holdeco-20261104T040639Z` | `fe4bc2ae8311f415a21565c9e87939bcc1805dc8` | 97105 / 97106 / 97107 / 97108 / 97109 |

统一接收目录为`/public/home/yuzelu/PingyangHuang/issue177-s-aggregate-20261104T131959Z`，其源码commit见source-snapshot原件；该目录只在每个候选全部四门成功后重新校验来源、复制六文件并绘制实际版图，不替换候选的执行源码或验收回执。四份RTL与原已测试`8b92b67ea88dc651a151b3f265e72d97487545fc`保持一致；合格来源的完整项目输入快照与各自Git原始blob逐字节核验。

本地复核核验18份规范Git源码快照，另明确保留160312Z的拒收快照：其中7个文件被CRLF转换，Slurm未接受其脚本，没有作业或资格。检查器要求这份失败快照的固定SHA、原commit和已知CRLF差异全部吻合，并禁止任何合格来源/门回执引用它；没有把失败快照改写成通过。

统一交付97205/97206/97207及最终打包97210仅做文件核验、复制、原生版图导出和归档，在空闲node27/debug以每作业4CPU、30分钟上限执行。首次归档调度因旧成功作业ID已过slurmctld依赖保留期而被拒，未提交作业；核对持久sacct确为COMPLETED0:0及四门原件SHA/来源后建立新作业。其后常规分区满载，核本人UID/任务名/精确路径后取消仅排队的97201–97204归档作业，在新目录转debug。97208工具清单误用不存在的OpenROAD源码路径而失败，未形成完整接收manifest；修正为PATH实际二进制的版本和SHA，在新目录97210重新打包。原始生产验收及其16CPU资源/结果未改；拒绝、取消、失败和改队回执均保留。

## 时序修复与保留的失败

N5原布局布线的独立物理97044实测setup +100.396ps、hold −2.253ps，一个真实hold违例。新目录只将实测数据路径的`wire1414`从BUF_X2改BUF_X1；候选中的`hold40630`替换反而使hold降至−5.310ps，明确排除。实际新RCX后hold +5.617ps，全部四门重新通过，未沿用失败来源的物理资格。

P4原生替代配置97074实测setup −73.894ps、17个违例端点；完整增量优化配置97026仍为−60.166ps、10个违例。两者均保留为失败。实测公共reset数据路径的累计等价替换，一个缓冲后setup −22.623ps，两个后+17.824ps；第三至第六个不能改善全局最差值，最终只将`hold44884`、`hold43351`从CLKBUF_X1改BUF_X1。这两处是SIGNAL数据网络，不是时钟或PG网络。

两种ECO均要求实际Liberty函数为A且无状态、新master不超原占位，完整DEF仅有指定组件master变化，所有其他路由/位置/端口/连接逐字节不变；变换后的A/Z/VDD/VSS须与真实导体正面积接触，漏改/额外修改/移动/漏接触负控制须失败。之后重新执行原生最终报告、完整LEC、新RCX和DEF/SDC读回，再在新输出目录封存并重跑全部四门。未通过试探数据、单元等价推断或旧S资格直接赋予验收结论。

| 早期记录 | 真实结果及处理 |
| --- | --- |
| 160146Z / 160312Z / 160337Z | 分派名错误、CRLF调度拒绝、ABC固定路径错误；分别修复调用/原始blob打包/实际安装定位，未进入成功物理资格 |
| 160503Z / buffer161454Z | 无放置RC的高扇出修复无效；删除ABC实现缓冲后按真实位置重新分组。额外20ps hold优化对大量已正裕量端点插入过多缓冲，核本人身份/精确目录后取消，原件保留 |
| hold162651Z / 96587 | 20ps CTS目标导致108561保持缓冲、RSZ-0060及真实负hold；P4早期无界理想时钟优化超时。改为放置hold额外目标0、CTS额外目标5ps；仅理想时钟放置最多200次，CTS新进程完整优化。最终检查仍要求所有真实裕量非负 |
| 96634 / 96644 / 96659 / 96686 / 96695 / 96750 | debug30分钟窗口内长布线超时；后续在常规分区完成，不将超时记为通过 |
| P4替代/完整失败源、N5原失败源 | 原始数据和失败报告保留；确认本人UID、任务名、精确路径后取消其无用后续门，调度记录保留真实取消状态；不转移通过标记 |
| 可选DRC deep诊断97127 | 仅性能诊断；核本人UID/任务名/精确目录后取消，以释放资源供必要功能验收，日志及取消回执保留。未用于生产资格，最终三份验收均使用原始flat规则执行 |

N4/N5采用ORFS原生SKIP_INCREMENTAL_REPAIR=1，跳过全局布线后可选增量电气/时序优化段；全局/详细布线、保护/天线、新RC提取和全部最终门均实际执行。P4成功来源保留完整增量优化。检查点仅接收日志与哈希证明成功的阶段，原失败整轮回执继续标false；没有从失败CTS或超时布线继承资格。更早的RTL失败与reset修复见原RTL报告。

## 文件实收与复核

[远程索引](../../work/huangpingyang04-lgtm/177/physical-evidence/remote-index.json)列出完整原始小文件、四个归档、成功来源、工具版本和二进制/库/规则/容器SHA；[本地接收回执](../../work/huangpingyang04-lgtm/177/physical-evidence/LOCAL_RECEPTION.json)记录归档、成员与实际落盘三层SHA核验。每个配置包含`6_final.v/.sdc/.def/.odb/.spef/.gds`及实际1600×1600版图PNG，共21份文件/图像、9,192,379,548字节；逐项SHA见索引，图像已逐张查看。

完整原始小文件归档含3,394份、227,947,383字节；大中间JSON/数据库仍在服务器。PR提交664份原始验收/来源报告、必要小日志及三份实际版图PNG，列表和原始SHA见[COMMITTED_SUBSET](../../work/huangpingyang04-lgtm/177/physical-evidence/COMMITTED_SUBSET.json)。不修剪原生日志尾空格，不把大物理数据库放入Git。完整接收位于本机`C:/Users/86188/Documents/ChatGPT/2026DAC/deliveries/issue177-local-s-20261103/rx-20261104T133110Z`，服务器归档位于`/public/home/yuzelu/PingyangHuang/issue177-s-package-20261104T132358Z`。

[P4实际版图PNG](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-aggregate-20261104T131959Z/delivery/p4/layout.png) · [N4实际版图PNG](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-aggregate-20261104T131959Z/delivery/n4/layout.png) · [N5实际版图PNG](../../work/huangpingyang04-lgtm/177/physical-evidence/raw/issue177-s-aggregate-20261104T131959Z/delivery/n5/layout.png)。三图来自实际最终GDS原生全层绘图，保持原始字节。全层概览以阱层填充为主，细节可在交付的GDS中切换图层查看。首次本地解包遇到Windows路径长度限制，改用较短的rx接收目录；复用下载前后均按服务器SHA清单核验，并在新目录完整重核，未修改机器全局设置或原件。

```powershell
python -X utf8 -B scripts/check_project.py
python -X utf8 -B work/huangpingyang04-lgtm/177/check_evidence.py
python -X utf8 -B work/huangpingyang04-lgtm/177/check_physical_evidence.py
python -X utf8 -B work/huangpingyang04-lgtm/177/check_physical_evidence.py --raw-root "C:/Users/86188/Documents/ChatGPT/2026DAC/deliveries/issue177-local-s-20261103/rx-20261104T133110Z/evidence/raw" --files-root "C:/Users/86188/Documents/ChatGPT/2026DAC/deliveries/issue177-local-s-20261103/rx-20261104T133110Z/files"
```

默认物理复核只重新读取Git中的原始报告子集与已记录接收结果；最后一条才重新读取完整小原件与21份大文件/图像。两种模式及原RTL原件检查均已实际执行。完整重跑入口见[架构说明](../ARCHITECTURE.md)，新增输出目录不得覆盖封存轮次。

本次通过范围为原生M1–M10、TT、300MHz的16KiB局部S叶宏；未包含PR176的P.S32KiB、层级Liberty、M11/M12、完整计算Block/母控/NoC、三个LLM执行、功耗或代工厂签核。独立审查人待指定；Issue进入in_review，未自行合并或标done。登记与看板缺项见[持久交接](../handoffs/2026-11-03-issue-177-projects.md)。
