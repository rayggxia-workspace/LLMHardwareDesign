# 控制章节图解

[双页 diagrams.net 源图](control-figures.drawio)中，方框、文字和连线可单独编辑。两张 SVG 同样保留独立矢量对象和文字。

## 图 1　整体底座与 P Block 控制

![图 1 NoPool 底座和单个 P Block](control-architecture.svg)

**图 1(a) 从全局看。** 横排的 `P0、P1、P2、U0、U1、C0、F0、J0、J1` 是 NoPool 候选中的九个实例。字母区分 Block 类型，序号用于读图，实际目标 ID 由部署配置绑定。母控对各实例发任务并收终态。共享 DMA 接片外 DDR。下方橙色虚线表示产品映射要绑定的跨 Block 数据边，所需端点和路径由产品连线确定。

**图 1(b) 的画线规则。** 颜色回答“传什么”，线型回答“图中连接的依据是什么”。两项规则独立。实线的依据是固定源码中已有的 RTL 接口，整底座物理连线与时序另行验收。

| 线 | 读法 | 图中例子 |
| --- | --- | --- |
| 蓝色实线 | 已有控制或指令接口。传调用、取指、请求、命令、确认或状态。 | 母控端口和局控之间的 Call / reply，局控和程序存储之间的 Fetch，服务逻辑向 S 发请求并接收写 ACK。 |
| 橙色实线 | 已有负载数据接口。传描述符本体、操作数、读写数据或计算结果。 | DMA 将描述符送回局控，局控将描述符交给服务逻辑，M 的操作数和结果，S 的读写数据。 |
| 蓝色虚线 | 候选的控制绑定。 | 单个 P 的服务逻辑向本地 G 发命令并接收完成。 |
| 橙色虚线 | 候选或由产品绑定的数据边。 | P 私有 S 与本地 G 之间经适配器交换操作数和结果。 |

**按箭头读一条调用。** 母控把调用和 token 交给局控。局控从程序存储取指，向 Scope DMA 发蓝色读请求，接收橙色描述符。描述符交给服务逻辑后，服务逻辑给 M 发命令并组织供数，同时追踪 S 写回。M 和 S 都同时涉及控制与数据，所以各画一蓝一橙，表示逻辑职责。端口实现可以将这些信息打包或复用。对已验证的 P 范围任务，服务逻辑等所需的目的写 ACK 后才回报成功，局控释放 scope 后再向母控返回终态。图中的候选 G32 归属来自 NoPool 合同。已有三 P FFN 夹具使用一个共享 G32 服务。

**二级控制的价值。** 母控决定何时调用某个 Block、在哪些点等齐，局控和服务逻辑负责局部供数、宏执行和写回背压。只要描述符和完成语义一致，P 内部可以换一种供数顺序，母控程序仍然可用。既有三 P FFN 对照中，固定程序和搬运量时，提前发 EXEC 的供数实现减少了 0.52–1.20% 的 FFN 周期。[P 范围 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/block_local_native/p_stream_scope_node.sv) · [三 P 实验记录](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-three-p-ffn.md)

## 图 2　五类 Block 的局控指令与 FMA 拓扑

![图 2 统一局控子集和 U 的两种 FMA 输入连接](instruction-topologies.svg)

### 图 2(a) 五类 Block 共用哪些指令

P、U、C、F、J 的有界原生程序都用 `L_EXEC → L_WAIT` 执行并等待一个服务，局部任务最后执行 `L_END`。三条共用指令的 opcode 分别是 `0x41`、`0x44`、`0x4F`。同一条 `L_EXEC` 根据执行描述符调用本 Block 注册的服务。图中的母控栏采用 PR #251 的 native MC v3，局控栏采用五类原生程序的公共子集。各 Block 仍按各自的镜像、描述符和传输 profile 装载。

| Block | `L_EXEC` 选择的服务 | 程序示意 |
| --- | --- | --- |
| P | 叶宏 profile 中有装载、M 计算和门控。较新的 native P profile 执行有界 range 服务。 | `EXEC[装载] → WAIT → EXEC[M] → WAIT → END`，或 native P 的单 scope 内核 |
| U | N 归一化、E 向量运算，以及接收预约、发送、接收。 | `EXEC[E/FMA] → WAIT → END` |
| C | R 状态服务、G 激活、E 运算，以及接收预约、发送、接收。 | `EXEC[预约] → WAIT → EXEC[接收] → WAIT → EXEC[R/G/E 服务] → WAIT → END`，按任务选择其中的具体服务 |
| F | G 激活、E 运算，以及接收预约、发送、接收。 | `EXEC[G] → WAIT → EXEC[E] → WAIT → END` |
| J | JOIN 汇合和 RELEASE 租约释放。 | `EXEC[JOIN] → WAIT → EXEC[RELEASE] → WAIT → END` |
 
表中 `EXEC[发送]` 等写法表示 `L_EXEC` 的描述符服务。早期通用控制研究另有 `L_RX/L_TX` 等编码，其准入由对应 profile 决定。五类叶宏程序的公共子集使用上述三条指令。[五类程序生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cad3fa572d3cbf8515532df50868000806990b18/project/control_native_v1/images.py#L17-L62) · [U/C/F 服务适配](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/2a66b918df883853b6f276d40fd8490a8b5cdca0/project/control_native_v1/ucf_native_service.sv) · [P/J 服务适配](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/2a66b918df883853b6f276d40fd8490a8b5cdca0/project/control_native_v1/pj_native_service.sv) · [五类 64 位 profile 的版本边界](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/assets/five-leaf-bases/README.md)

### 每条指令在做什么

| 类别 | 指令 | 用途 |
| --- | --- | --- |
| 派发 | `G_CALL` | 选择目标 Block 和完成 token，并快照参数寄存器。例中的 `G_CALL C,t2` 让生产者 C 执行，同时用 t2 跟踪它。 |
| 派发 | `L_EXEC` | 按执行描述符启动一项本地服务。U 的例子中选择 E 的 FMA 以及读几个 S 源地址。 |
| 同步 | `G_WAIT` | 等掩码选中的活动 token 都收到匹配终态，再释放这些 token 和对应目标槽。掩码 `0x03` 等 t0、t1，`0x07` 还等 t2。 |
| 同步 | `G_EVENT` | 消费镜像中事先绑定的 READY 事件，把携带的标量写入目标寄存器，用于已注册的阶段就绪通知。 |
| 同步 | `L_WAIT` | 等匹配的本地服务结果。服务描述符规定完成条件，涉及数据写入时按服务约定等对应写确认。 |
| 参数准备 | `G_MOVI` | 将一个 32 位立即数写入参数寄存器。例如用两条初始化描述符地址的低、高字。 |
| 参数准备 | `G_ADDI64` | 向一个偶数索引开头的 64 位寄存器对加无符号立即数，检查溢出。native P 的连续描述符可用它推进指针。 |
| 程序流 | `G_JNZ` | 检查寄存器是否非零，在镜像编码的两个前向目标 PC 中选择其一。 |
| 程序流 | `G_LOOP` | 递减有界计数器。还有迭代时跳回较早的 PC，最后一轮退出。 |
| 程序流 | `G_END` | 在全局任务义务关闭后返回母控程序终态。 |
| 程序流 | `L_END` | 在局部义务关闭后向母控返回任务终态。native P 会释放 descriptor scope。J 的租约释放则是可由 `L_EXEC` 显式调用的服务。 |

### 图 2(b) 连线和指令一起改变计算结果

**A、B、C 是生产者任务。** A 示意绑定到 P0，交付乘数 `a=2`。B 绑定到 P1，交付乘数 `b=3`。可选的 C 示意绑定到 U1，交付加数 `c=5`。U0 是消费者。它从私有 S 的已绑定地址读入操作数，再交给 E 宏。图中生产者标签与 Block 实例标签分开书写，例如任务 C 位于 U1。

| | 左图，两条输入路径 | 右图，新增第三条输入路径 |
| --- | --- | --- |
| 产品绑定 | A、B 的结果送到 U0.S 的两个输入位置。 | 额外绑定 U1 → U0.S，给 `c` 保留第三个位置。 |
| 母控指令 | 先发 A（t0）、B（t1），用 `G_WAIT 0x03` 等两路。 | 在等待之前插入 `G_CALL C,t2`，把掩码改为 `0x07`。 |
| U 局控指令 | `L_EXEC` 选用两源 FMA 描述符，E 的第三操作数补零。 | `L_EXEC` 选用三源描述符，E 实际读取第三个 S 地址。两边随后都执行 `L_WAIT → L_END`。 |
| 结果 | `2 × 3 = 6`。 | `2 × 3 + 5 = 11`。 |

两段母控程序在输入写确认后才调用 U0（t3），然后用 `G_WAIT 0x08` 等 U0，最后 `G_END`。图中省略了传输控制细节。若生产者的终态已包含写入 U0 的确认，所示等待就能保证输入可用。若生产者只确认本地结果，部署程序还需要显式安排传输和目的写确认。新增连线由产品绑定，运行时按已绑定的路径发任务。第三条路径提供 `c`，母控等待它到位，U 局控再把它选进计算，这三步共同实现 `a × b + c`。

本项目已有独立 U 原生入口测试用实际 SRAM 检查了两源和三源的读取次数及写回结果，分别得到 6 和 11。图中的生产者绑定、跨 Block 路径与母控片段是部署示例，联合拓扑仍需验证。[两源／三源测试源码](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/pu_leaf_base/tb_u_native_entry.sv#L76-L94) · [U 原生入口回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/212/u-native-fix.md#L12-L19)
