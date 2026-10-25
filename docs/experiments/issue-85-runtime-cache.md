# Issue85：运行时A缓存旁路、命令握手与中止恢复

2026-10-25 UTC+08，负责人Liangruizhi。[Issue85](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/85)，独立task/85-runtime-cache，基于Issue84源码049a8a663013b7edb3a99a43e2ca9b702def82dc。PR由主会话统一发布，未审查合并不done。实际整数接收、RTL、映射与全包检查仅本人服务器lrz-i85-*，未下载模型。

## 电路增量

一个M核心在cmd_accept锁存cache_mode，仍为8个S8 lane和一个共享S32服务；没有复制两套M。16KiB单1RW不变，cache开占用768..1023行4KiB；关则读取旧成对A/W流。模式在命令边界切换，需要软件选择对应物理输入格式，pack/gather仍是外部成本。

新增cmd_ready/cmd_accept：cmd作为valid保持到握手；cfg优先，尚未消费的配置响应阻止命令接收。计算busy=0不代表cmd_ready。无命令FIFO，共享乘法器每client一个64bit有限响应槽。接收后驱动立即反转mode并清零epsilon/coefficient，完整结果验证实际锁存。

soft_abort同步清除流水/有限响应，保留SRAM并推进32bit epoch；请求携带epoch，响应回显，不匹配响应排空且不能进入新消费者。命令接受也推进epoch。禁止会话内wrap，0xffffffff后cmd_ready低，须协调fabric硬复位。全局reset要求fabric丢弃旧事务；独立硬复位/时钟域/任意重排未验收。

## 完整数值与恢复证据

六个既有Granite输入（层0/13，token0/64/71），每个完整8expert×K512×H1536。quiet和确定性背压两路，每路12主命令（六样本×两模式）＋10阶段中止后重启＋6错误后重启＋迟到旧响应重启＋协调硬复位重启，共30完整输出。正式两路60条；早期60条保留，不把重跑计作新的模型样本。

实际全K INT32 acc、RQ、8expert merge、残差和完整精确RMSNorm逐位等于独立物理payload NumPy/bigint参考及旧codes；没有host注入中间计算。复用84输入在准备和接收阶段逐artifact SHA校验。接收严格要求typed schema、profile/stall、显式旧输入root、六样本两模式及恢复角色；实际改acc并重新SHA的语义负例，以及空/漏键/非布尔/错误计数/额外字段5类协议负例均拒绝。

中止覆盖cache装载/写入、MAC、RQ请求/结果、Norm乘法、均值除法、开方、输出除法；随后反模式完整重启。错误覆盖reserved header非零、负单位shift、确定性RQ INT32溢出；检查状态后ack并完整重启。4拍done/status保持、挂起cfg与cmd竞争、忙时cmd拒收均实测。最终协议记录硬复位前RTL真实abort/stale计数和环境FIFO高水，分析从回执求和，不按枚举常量伪装测量。

**外部恢复测试响应队列有2槽**，每槽128bit payload＋32bit epoch，至少320bit再加valid/control/等待状态；它们未包含在core映射面积。第二槽专门构造旧响应和新读同时在途。普通单inflight核心周期不使用两个并行响应；同资源比较仅限定core库存，不能说恢复fabric与84单槽完全同资源。新增32bit epoch是单独metadata接口；旧128bit五beat计数未覆盖实际NoC tag线网费用。epoch比较器/mux/寄存器/计数器自身已计入映射。

## 周期与资源

|条件|cache关cycles|cache开cycles|对照|
|---|---:|---:|---|
|quiet|9,061,831|5,919,175|与84各静态shared变体一致|
|确定性背压|10,690,375|7,155,270|与84各静态shared变体一致|

运行时核心logic-only面积52,415.566um²；84静态cache/shared为51,627.142um²，增加1.52715%。generic寄存器4309bit，相对4212bit增加97bit。generic实际恰8个S8、1个S32乘法以及一个1024×128 1RW行为存储；新增模式/epoch/计数/握手/mux均计价，动态选择无本批额外core cycles，但不是免费硬件。

同Nangate45研究Liberty SHA8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1、同84恢复后Yosys配方。实例直方图等于Yosys stat，原库Decimal求和核验面积。共同store82整个wrapper黑盒排除；不能称总芯片面积、宏、STA或PPA通过。85没有门级等价/目标宏/布局/时序签核，86结果不能自动成为85资格。

## 失败、来源与未完成项

90697首构建失败：Verilator保留名abort引起C++端口名不匹配，以及auto混合8/32bit声明。改soft_abort/显式类型后通过；仅取消本人4个永远不能满足的未执行依赖，失败保留。正式RTL588f61c，初始完整运行phase2；最终遥测驱动af634db/phase5，RTL字节未变，复用map02前再次核SHA。文档写入曾因本机GBK不能编码符号失败，改明确UTF8后重写，未改实验结果。

完整结果在授权服务器/public/home/yuzelu/RuizhiLiang/issue85-runtime-cache-20261025；原始输入只读Issue84/input01。最终包/SHA、作业、原Git源校验见交接和results/issue-85/final。精选不含完整矩阵输入/完整JSONL，字节检查不代表数值/硬件验收。

未完成：epoch溢出边界的可执行注入、独立fabric/CDC、真实tag打包/互联费用、自动模式策略、更多H/K和多context、SRAM/ROM宏/STA/route、通用V/完整M阵列及整模型质量。可收敛为可选择A驻留＋显式命令/代际合同的单核心候选，保留M/V物理映射自由。

最终实际遥测：两路RTL共22次soft-abort、2个迟到响应丢弃，外部测试FIFO峰各2槽。主60完整输出/94接收命令、12输入错误均有独立接收；全量74,455,001B/255成员、精选588,490B/98成员以及5阶段86个原Git源字节均通过独立检查。具体SHA见交接。
