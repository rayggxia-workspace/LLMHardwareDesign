# P2：最新RTL同步与最小MST协调原型

任务[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)，[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，负责人Melodydt。用户明确要求同步PR144最新RTL并开始第二步。本报告区分源码同步、实际控制RTL、局部仿真与剩余验收，不将P2原型当成完整模型或共同底座。

## 1. 输入版本与同步范围

研究输入be10e69bb9ad625079f68361fb47b4747d6ce040。本轮开始读回PR144头707878621b2add4ed218b8c43df2e95c9a56e2ba，逐个读取14个核心RTL/include；相对已导入643c6012，13个Git blob相同，仅project/rtl/block_library_v1/block_v1_r.sv更新。新R blob为6483793b0a183906e7410a0fe3b1ae0eabb1b109，与P1观察到的adb819版本相同。七类宏149个顶层端口的规范化名称/方向/类型/宽度/符号均与P1一致。

本次采用7078786的14核心源，R的RNE输入/输出、fits32输入和value中间量扩展为S128，并对应调整符号扩展。这不是R数值、周期或物理等价证明，也不接管Issue143的最终资格。M/S/T在此更新中逐字节不变，P2使用这三类宏的原生接口。完整来源和逐文件Git blob/SHA-256见[源码锁](../work/Melodydt/151/phase2-source-lock.json)，声明见[接口清单](../work/Melodydt/151/phase2-native-ports.json)。

只同步所需核心源码，不导入上游服务器作业、物理数据库或其他成员的研究记录。P1在be10e69的合同与回执作为历史证据保留，不将其643源回执改写为707源通过。复现P1旧检查应使用其固定提交；当前版本按P2入口验证。用户授权继续P2不等于独立审查已完成。

## 2. 控制分工与实际硬件归属

原生S包含16KiB存储及有限loader，后者直接驱动M的A128/B512握手；S内部没有M实例。新增协调逻辑位于project/rtl/block_connection_p2/，并列于现有叶宏外侧，尚无独立物理bridge宏或布局视图。

S普通端口helper采用单在途请求，锁存地址/读写/data，发出一次原生请求，等待并消费响应，再将响应保持到上层接收。写操作也走完整ACK路径；原生S没有普通端口错误位，helper不虚构存储故障检测。S的busy只属于loader，不能替代普通端口ready/valid。

最小顶层实例化真实S/M/T及helper。母控以固定ROM发SERVICE/WAIT/END，局部服务用计数器处理多字初始化、M读取、写S和填T；每个原生端口有唯一驱动者。这个ROM只是MST程序的有限骨架，不等于八模型编译器、全部产品程序或已证明的完整ROM容量。原较完整64bit指令候选合同仍属后续扩展；本原型不借用其预算作实现结论。

M的命令ACK、EXEC状态和结果payload分别处理。loader done只代表供数完成；母控随后发M EXEC并检查error，成功后才发op3读实际S64结果。每个结果字保存到S并收到写ACK后，才进入T填充阶段。T先BEGIN4、顺序写满、COMMIT，再交付外部sink；末字真实take后仍须RELEASE，之后才向上层报告完成。外部背压不改变已呈现的data/index/last。

## 3. 固定的最小数据路径

采用[P1固定向量](../work/Melodydt/151/phase1-mst-vectors.json)的P2_S8_DOT8_RAW64：bank0、一行、一tile、K8/N8、A/B为S8，scale factor1/shift0。S中A448..451、B452..455、结果456..459，共192B测试预留；T中四字64B。

A为[1,-2,3,-4,5,-6,7,-8]，B按n-major排列且第n列八个系数均为n+1。八个整数结果为[-4,-8,-12,-16,-20,-24,-28,-32]；相邻两列低/高S64打包为四个128bit字。没有把S64裸截断成S16，也没有引入E/G或另造数值转换器。

```text
start
  -> M CLEAR_ALL/SET_SCALE，各自收ACK
  -> S初始化8字，各自收ACK
  -> S loader供数并取done/error
  -> M EXEC 0x9884并取状态
  -> M op3读4字 -> S结果4字并逐笔收ACK
  -> T BEGIN4 -> S读4字/顺序写T -> COMMIT
  -> sink接收4字 -> RELEASE -> done
```

重复运行必须重新初始化并走完整生命周期。abort是顶层协调同步复位：helper、S/loader、M、T及母控同时复位，丢弃未完成事务，不报告该任务成功。它不是无复位取消、已提交外部状态回滚或只复位单个叶宏。S/T RAM旧字节不必清零；重新初始化/完整填充及valid状态控制可见性。复位前sink已接收的输出不能撤回。

## 4. 验证与证据

实际执行结果以[检查回执](../work/Melodydt/151/phase2-checks.json)和[验证状态](../work/Melodydt/151/phase2-verification-status.json)为准。独立testbench使用固定literal结果，而不是读取DUT内部计算结果生成预期；握手计数、稳定性、超时及故障注入独立检查。测试可对内部ready/valid许可进行分层控制，以激发真实端点等待路径；这些许可不是产品运行配置接口。

逐场景测试方法、实际计数与未覆盖边界见[独立RTL验证报告](PHASE2_MST_VERIFICATION.md)。

本机ModelSim SE-64 2020.4可用，版本查询在沙箱外执行成功；原沙箱内原生程序启动出现Windows DLL重定位错误。工具仅在本任务独立目录编译/仿真，不修改系统配置、读取license内容或使用服务器。精确命令、工具版本、源码/输入/输出SHA与实际日志随回执提供。

正式路径实跑结果：vlog/vsim版本查询、vlib、vlog编译、helper仿真、MST仿真六项工具命令均exit0。14核心文件（12个.sv＋2个.svh/include）全部按源锁核验并编译；对N/E/G/R这仅是语法/解析门。helper通过6场景、141周期；MST通过13场景、1101周期。19个CASE_PASS及两个总PASS标记均来自实际RTL仿真。精确源码、工具二进制和输入/日志SHA见[原始运行回执](../work/Melodydt/151/phase2-rtl-evidence/run-receipt.json)。

已测场景包括：literal四字S64全链数值、每个正常任务16笔S请求/16笔ACK、7个M命令/7个应答、loader一次A/一次B与完成、T四字写/commit/消费/release；S请求背压及应答保持、M应答和T输出/完成背压；busy时start不排队；重复运行；等待S ACK时abort、已有DONE与abort同拍消费、T首输出停顿时硬复位及恢复；实际EXEC保留位错误和loader未对齐描述符错误传播及恢复。总轨迹Sreq113/Sack112的差1是abort主动丢弃的一笔未消费ACK，五个成功任务逐批守恒；不能把全局相差1隐藏为正常任务丢ACK。

测试的有限许可在请求发出前设置，不将已呈现的valid随意撤回当作合法反压；M响应与T输出直接由ready施加停顿。固定ROM不产生非法描述符，相关错误由TB对真实原生字段注入，不能称产品已有可变模型配置接口。

验收按原P1要求逐项记录已测切片和未覆盖部分，不能把一次MST成功等同于P2全部退出门。尤其真实多形状/多bank、S普通/宽端口长期竞争、所有错误行的恢复策略、各状态reset、程序循环/多服务调度和资源/路线反馈仍需对应实测证据。

当前P2尚未整体验收：S16/多K段/append和op5/op12真实RTL覆盖、混合成功/失败行、A/B独立长停顿/reuse_b、T1..384及全部非法时序、无复位drain取消、随机有界停顿、跨bank/fmt/scale重用，以及完整64bit指令/模板capture/十服务接收bank/epoch-credit防陈旧控制均未在本原型完成。它们保留在验证矩阵，不用19场景代替这些义务。

## 5. 与后续阶段及物理目标的边界

P3 E/G和FFN、P4 N和Softmax257、P5同S/T及一般拓扑、P6 R/NUM和多tile状态、P7八模型完整程序/实际MEM/共同底座物理均不因该原型通过而完成。系统有外存，只是本轮不研究具体接口/带宽/调度；192B/64B是测试范围，不是模型容量上限。

母控与子服务现为可综合RTL层次，未进行综合、布局、扇出、走线或时序接收；不能声称多层控制已解决后端问题。新增控制、MUX和保持均须在共同有源底座冻结前实际实现；M11/M12只能永久选择已有程序/路径，不能在定制时补有源bridge。本原型仍不能证明两个完整模型产品的M1–M10完全一致。

首轮静态资源反馈如下，全部仅为声明字段量，未扣除或复用现有叶资源：

| 项目 | 声明量 | 解释 |
| --- | --- | --- |
| 母控状态 | 8bit | state2、pc5、done_error1 |
| 服务后端状态 | 142bit | state4、operation4、step4、held_data128、service响应valid/error各1 |
| S helper状态 | 269bit | state2、write1、addr10、请求data128、响应data128 |
| 新控制运行态小计 | 419bit | 不是综合后触发器数量或面积 |
| 程序ROM | 336bit | 21×16bit，当前10个服务及END |
| fixture初始化常量表 | 1024bit逻辑表 | 8×128bit，含3零项；综合可能优化，未计面积 |
| 顶层接口 | 14端口/150bit | 输入6bit、输出144bit；不包含内部跨宏线数或走线长度 |

原生S16KiB、T6KiB、loader队列与M内部状态仍实际实例化。419bit不包含叶状态、所有组合逻辑、PG/CTS/重置/中继或未来capture/spool；不能与此前完整系统预算直接相减宣称节省率。

交付通过原任务分支和PR，独立审查人待指定，不自行合并或标done。登记PR5与看板配置/条目工具缺项分别报告；实际线上状态以PR/Issue读回为准。恢复先读源码锁、检查回执和当前头，再补验证矩阵的缺项。
