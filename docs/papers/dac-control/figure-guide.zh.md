# 控制章节图解

[双页 diagrams.net 源图](control-figures.drawio)中，方框、文字和连线可单独编辑。两张 SVG 同样保留独立矢量对象和文字。

## 图 1　整体底座与 C Block 局控

![图 1 NoPool 底座和单个 C Block](control-architecture.svg)

**图 1(a) 从全局看。** 横排的 `P0、P1、P2、U0、U1、C0、F0、J0、J1` 是 NoPool 候选中的九个实例。母控居中，向每个 Block 派发任务并接收终态。C0 高亮对应下方的局控详图。实例序号用于读图，实际目标 ID 由部署绑定。下方橙色虚线表示按产品绑定的数据路径，共享 DMA 通过这些路径提供片外 DDR 访问。

**图 1(b) 以局控为主。** 深蓝色的 C 局控接收母控调用，从程序存储取指，经局部服务和适配器驱动 S、R、G、E。S 保留数据，R 提供状态服务，G 做激活，E 做向量运算。母控按 Block 追踪任务终态。局控和适配器负责宏命令、操作数交换、写确认与本地服务完成。

| 画法 | 图 1(b) 的规则 | 读图例子 |
| --- | --- | --- |
| 蓝色实线 | 逻辑接口上的交换，合画指令、控制、数据和返回。 | 母控调用和返回、局控取指、服务适配器与各宏之间的命令及数据交换。 |
| 橙色虚线 | 产品配置需要指定的物理连线。 | G 到 E 的直送，箭头按结果数据方向绘制。实际端点还包括随数据的有效信号和反向接收握手。 |

**G→E 为什么单独画出来。** C 的独立夹具把 G 结果保持在发送端，经分离端点和适配器交给 E。产品若接入该路径，局部程序可选择 G→E 直送。经 S 写回再读出的回放路径也有对照。两条路径的计算语义相同，选择直送时可以省去这一次中间结果的 S 往返。该连接和程序回放已有独立 C 夹具证据，整底座的跨实例接入与联合验收另行进行。[C/F/J 夹具接口与回放](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/211/README.md#L36-L41) · [C 的独立物理网表回放](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/211/README.md#L109-L114)

## 图 2　公共指令与两种真实模型的 FFN

![图 2 指令分类与 Qwen2.5、GPT-2 的 FFN 映射](instruction-topologies.svg)

**图 2(a) 的范围。** 母控栏是 native MC v3 的八条指令。P、U、C、F、J 的有界原生程序共享 `L_EXEC → L_WAIT → L_END`。相同的指令框架可以配合不同执行描述符，镜像、服务和传输接口按目标的 profile 绑定。[五类生成程序](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cad3fa572d3cbf8515532df50868000806990b18/project/control_native_v1/images.py#L17-L62) · [五类 64 位 profile 的证据边界](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/assets/five-leaf-bases/README.md#L40)

### 每条指令在做什么

| 类别 | 指令 | 用途 |
| --- | --- | --- |
| 派发 | `G_CALL` | 选择目标 Block 和完成 token，并快照参数寄存器。Qwen2.5 的 `G_CALL B,t1` 让 P1 执行 Up 投影，同时用 t1 跟踪。 |
| 派发 | `L_EXEC` | 按执行描述符启动一项本地服务。例如图 2 选择 SiLU 门乘或 GELU，以及对应的操作数与结果位置。 |
| 同步 | `G_WAIT` | 等掩码选中的活动 token 都收到匹配终态，再释放这些 token 和对应目标槽。Qwen2.5 的 `0x03` 同时选中 Gate 的 t0 和 Up 的 t1。 |
| 同步 | `G_EVENT` | 消费镜像中事先绑定的 READY 事件，把携带的标量写入目标寄存器，用于已注册的阶段就绪通知。 |
| 同步 | `L_WAIT` | 等匹配的本地服务结果。服务描述符规定完成条件，涉及数据写入时按服务约定等对应写确认。 |
| 参数准备 | `G_MOVI` | 将一个 32 位立即数写入参数寄存器。例如用两条初始化描述符地址的低、高字。 |
| 参数准备 | `G_ADDI64` | 向一个偶数索引开头的 64 位寄存器对加无符号立即数，检查溢出。native P 的连续描述符可用它推进指针。 |
| 程序流 | `G_JNZ` | 检查寄存器是否非零，在镜像编码的两个前向目标 PC 中选择其一。 |
| 程序流 | `G_LOOP` | 递减有界计数器。还有迭代时跳回较早的 PC，最后一轮退出。 |
| 程序流 | `G_END` | 在全局任务义务关闭后返回母控程序终态。 |
| 程序流 | `L_END` | 在局部义务关闭后向母控返回任务终态。 |

### 图 2(b) 模型算子、连接与发令顺序

两幅子图都从 FFN 入口张量 `x` 开始，比较 Transformer 层内部的前馈子层。字母 A、B、C、D 表示各自图中的任务。P0、P1、P2、F0 是示意目标，同一字母在不同模型中可表示不同任务。橙色虚线在图 2(b) 表示候选的张量路径。

| | Qwen2.5-3B-Instruct | GPT-2 |
| --- | --- | --- |
| A | P0 做 Gate 投影，产生门控输入。 | P0 示意承担带偏置的 `c_fc` 投影。 |
| B | P1 做 Up 投影。它与 A 读同一个 `x`，两者可以并行。 | F0 的 G16 执行 tanh 形式的 GELU，输入来自 A。 |
| C | P0 的候选 G32 服务执行 SiLU 和逐元素门乘，同时消费 A、B 的结果。 | P2 示意承担带偏置的 `c_proj` 投影，输入来自 B。 |
| D | P2 对门乘结果执行 Down 投影。 | 串行 MLP 在 C 完成后结束。 |

**Qwen2.5 的连接与程序。** 将 `x` 分送给两个投影目标，然后把 Gate 和 Up 的结果都送到门乘位置。母控先发 A（t0）、B（t1），用 `G_WAIT 0x03` 等两路。随后发 C（t2），等 `0x04`，再发 D（t3），等 `0x08` 后结束。这样形成 `Down(SiLU(Gate(x)) ⊙ Up(x))`。图中 A 和 C 复用 P0，A 的 token 在第一次等待后已退役，局部保存的操作数仍须保留给 C。[Qwen2.5 配置](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/3ca5f5bff0f44b2b436a9aba99b900ab157c9a27/config.json) · [Qwen2 MLP 实现](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen2/modeling_qwen2.py#L42-L55)

**GPT-2 的连接与程序。** 输入只进入 `c_fc`，其结果送到 F0 的 GELU，再送到 `c_proj`。母控按 A（t0）、B（t1）、C（t2）发令，在每步后分别等 `0x01`、`0x02`、`0x04`。同样的调用与等待指令表达出 `c_proj(GELU(c_fc(x)))` 的串行依赖。[GPT-2 原始 MLP、GELU 与仿射投影实现](https://github.com/openai/gpt-2/blob/master/src/model.py)

**部署时还需绑定什么。** 两图以真实模型源码确定算子和依赖，以候选 Block 分配说明控制程序。消费者发令前必须确认输入已写入其可访问的位置。若生产者终态只确认本地写入，部署程序需要另行安排跨 Block 搬运及目的写确认。GPT-2 的偏置和 G16 数据格式也需绑定相应服务并做数值校准。Qwen2.5 的三 P 回归使用同尺寸合成整数输入和共享 G32 服务，作为独立实现证据。[G16/G32 服务与格式约束](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/w8a16_g/PROVIDERS.md) · [三 P FFN RTL 回归](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-three-p-ffn.md)
