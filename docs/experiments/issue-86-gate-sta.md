# Issue86：精确门级重放与存储切分后的逻辑时序

2026-10-25 UTC+08；负责人 Liangruizhi；[Issue86](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/86)。独立 task/86-gate-sta，源基于 Issue84 049a8a663013b7edb3a99a43e2ca9b702def82dc；本轮不改84、85及成员55/63。实际计算全在本人服务器 c96/node13，经 lrz-i86-*。远端 PR/进度由主会话统一交付，本地提交不等于上传、审查或合并。

## 可接受的结果

**四种 Issue84 网表的八条完整消费者门级重放通过，物理时序没有收敛。** 每变体复用同一真实 Granite L0/token0 的完整8expert×K512×H1536，安静/背压各一次；这是一个不同输入的八个执行条件，不是八个模型或新样本。每次实际执行6,291,456个S8 MAC，经RQ、宽merge、残差及完整norm；独立NumPy/bigint按物理payload重算所有acc/down/join/out，并核对原RTL所有计数、cycles、配置、完整输入SHA和输出。保留原精度/模型质量边界。

实际done保持、active M reset、存储保留通过；最终接收严格要求三个协议键的bool真值，逐级绑定gate/build/prepared/mapping的variant、状态、输入和SHA。8个输出改位文件及7个variant/协议篡改文件经过实际保存、重新SHA和拒绝；不靠仅比较相同cycles判断v0/v1是否接错二进制。

门级单元功能由同一原Liberty经Yosys解析导出，原mapped JSON逐字节复用，没有重新综合。Verilator使用这些标准单元功能＋原store82行为模型＋原被动driver。**这是选定输入的零延迟门级回归，不是全状态形式等价、SDF仿真或SRAM门级实现。**

## 时序合同及完整覆盖

使用现有OpenSTA3.0.0与Nangate45 typical研究库，nom_process1、1.10V、25°C，time_unit1ns/cap1fF；Liberty SHA256 `8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1`。这是研究参考角，不是目标可制造PDK/PVT。

从原网表删除恰好一个store82实例，保持其他全部标准单元、连接、原ports/netnames逐字段不变；除store自身clk/reset外，其全部数据/控制引脚逐bit暴露为外部切分端点。没有SRAM时序或内部存储路径被当作已经分析。每变体471个输入bit、1183个输出bit包含该切分接口；存储本体、宏clock/reset路径、宏面积和功耗完全在本时序范围之外。

所有变体固定10ns理想时钟、0不确定度、0.05ns时钟/输入transition、输入/输出max delay0.1ns与min0。输出负载分别1fF和10fF，无布线RC、CTS或布局寄生；这些都是显式探测条件，不是产品时钟承诺。check_setup逐项无warning，未报告无时钟或未约束端点；全部映射DFF数据端都取得R2R最坏路径（覆盖如下）。未用false path把reset或大扇出路径隐藏。

|变体|已分析R2R端点/DFF|未修复R2R诊断周期 ns|最大slew违规|最大cap违规（1fF）|
|---|---:|---:|---:|---:|
|v0|3582/3582|13.097319|4306|171|
|v1|3583/3583|9.183252|3178|207|
|v2|3744/3744|12.812428|4023|179|
|v3|3745/3745|13.467542|3935|191|

10fF时v1/v2的cap违规分别208/180，其余不变；所有R2R诊断周期相同。完整IO路径也有失败，例如v0报告中的reset输入路径到DFF约21.96ns数据到达；因此不能仅以R2R子集或原logic-only面积宣布电路已经可用。大量slew/cap约束违反，尚需缓冲/尺寸优化及再次等价、面积和时序验证。

以上数值由10ns减最坏R2R slack得出，仅供定位未经修复的网表；**不是合格周期下界或Fmax，不能用于接受速度排名。** 原84 quiet的缓存同时间必要时钟比为5,919,175/9,061,831≈0.653199；当前未修复诊断的v3/v0逆周期比约0.972510，v3/v2约0.951356，均不能替代满足电气/宏/RC约束后的时钟比。特别是85新增运行时模式、epoch等硬件，完全没有继承本轮84的时序资格。

## 工具恢复、失败与记录

未安装软件。既有STA不在PATH，其Bazel重定位后的ELF解释器为相对路径；第一批4个STA直接exec失败。通过同版只读`lib64/ld-linux-x86-64.so.2 --library-path .../usr/lib/x86_64-linux-gnu`调用恢复，实际版本/二进制/loader SHA和argv留档。第二批4个STA已经执行，但导出用了该版本不支持的arrival属性，保存失败后统一改用slack，最终四变体×两负载成功执行。

首个独立receiver在解释Yosys重新命名的实例时失败，未宣称数值失败或通过；其依赖的本人receiver取消。最终保留实际发射Verilog pin名，明确未解析回原RTL语义位置，重新独立接收通过，不根据生成的编号推断其属于哪一个算子。

34个本人作业最终24COMPLETED、9FAILED、1CANCELLED；9失败为上述8个STA入口/导出和1个接收解释错误，所有原日志保留。八条gate运行2m38s—4m58s。独立最终数学/范围接收为receive03，源42706e1；精确phase1—8的源码commit/SHA、Slurm命令及失败见work/Liangruizhi/86/execution.json和final-slurm.log。没有取消其他成员作业。

## 交付和下一步

完整包 `/public/home/yuzelu/RuizhiLiang/issue86-gate-sta-20261025/delivery01/full-results.zip`，19158542B、434成员，SHA256 `823e96231f7d35fde8625bc4583d8fd2d8ee13f0cd000b1dcc4ba9973ea8f129`；精选1966113B、402成员，SHA256 `a6790d059ea326246551ac536a7bb717e136718a3bf663bd7292769abdb199df`。服务器两包逐成员字节接收、PC精选接收、8phase/57条原Git blob源码绑定全部PASS。精选含实际完整gate输出/STA日志/接口和源绑定；编译中间对象不打包，完整包保留gate二进制。原84 `input01`物理输入作为授权服务器只读依赖，由index和receipt记录manifest SHA，没有声称当前包独立包含全部原始数据。

后续优先进行**同资源约束下的高扇出缓冲/尺寸修复**，重算新增面积、端口接口与周期，再对新网表重放。之后才接合法SRAM/ROM宏、真实floorplan/RC/clock和成员55/63同版M8接入合同。一般M/A/R、通用V/ROM、整模型质量及最终物理边界仍未完成，不因本轮门级PASS或无缺约束将这些项目标done。

远端交付：[PR90](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/90)已上传，Issue86为in_review，待指定独立审查与合并；按不可变commit读回报告/交接/个人进度与原Git blob一致，后续仅文档同步。
