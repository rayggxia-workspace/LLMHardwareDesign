# 控制章节图解

[四页 diagrams.net 源图](control-figures.drawio)中，方框、文字和连线可单独编辑。四张 SVG 同样保留独立矢量对象和文字。

## 图 1　整体底座与 C Block 局控

![图 1 NoPool 底座和单个 C Block](control-architecture.svg)

**图 1(a) 从全局看。** 横排的 `P0、P1、P2、U0、U1、C0、F0、J0、J1` 是 NoPool 候选中的九个实例。母控居中，向每个 Block 派发任务并接收终态。C0 高亮对应下方的局控详图。实例序号用于读图，实际目标 ID 由部署绑定。下方橙色虚线表示按产品绑定的数据路径，共享 DMA 通过这些路径提供片外 DDR 访问。

**图 1(b) 以局控为主。** 深蓝色的 C 局控接收母控调用，从程序存储取指，经局部服务和适配器驱动 S、R、G、E。S 保留数据，R 提供状态服务，G 做激活，E 做向量运算。母控按 Block 追踪任务终态。局控和适配器负责宏命令、操作数交换、写确认与本地服务完成。

| 画法 | 图 1(b) 的规则 | 读图例子 |
| --- | --- | --- |
| 蓝色实线箭头 | 表示局控和服务适配器上的控制与数据交换，包括固定的 SRAM 访问。 | R、G、E 通过既有仲裁和适配器访问 S。 |
| 橙色横带和接入横带的虚线箭头 | 按图 1(a) 的方式汇总产品后制路径，箭头按数据方向绘制。 | G 向横带输出，E 从横带接收。该路径有独立 C 夹具的物理连线和网表回放记录。 |
| 橙色短虚线 | 表示需要进一步设计的候选端点，短线在横带前断开。 | S 和 R 可作为后续设计的候选，图中未给它们绑定后制路径。 |

**G→E 的用途。** G 的结果可经 S 写回、再由 E 读出。通过后制旁路时，保持槽与接收适配器通过独立端点传递数据和有效信号，E 返回接收握手，省去该中间结果的 SRAM 往返。横带归纳按产品选定的点对点路径，每条实际连线由端点清单确定。[C 端点与握手 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/block_cfj_v1/block_cfj_cf.sv#L30-L35) · [C 直送与回放对照](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/211/README.md#L109-L114)

**S、R 是否也能参加后制连线。** 架构上可以预留，例如 R→E 可以让 E 直接消费 R 的输出。底座需要先提供可接出的 R 结果、可接收的 E 输入、兼容的数据格式和握手，产品后制才能把两端连起来。S 也可以是后制路径的源或目的，此时仍需保留存储访问的仲裁和确认。项目中 J 夹具的 E→S 写回已经使用独立后制端点，可作为涉及 S 的例子。C 当前可回查的宏间后制旁路是 G→E，涉及 S 或 R 的新路径仍是候选。[C/F/J 端点说明](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/211/README.md#L36-L41) · [夹具后制与网表证据](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/211/README.md#L63-L73)

## 图 2　指令分类与两种模型的 Q/K 前处理

![图 2 指令分类与 Llama 3.2、Qwen3 的 Q/K 前处理](instruction-topologies.svg)

**图 2(a) 的四类指令。** 派发用于在 Block 上启动任务或在 Block 内启动服务。同步用于等所需任务或服务完成，也可以接收已绑定的就绪事件。参数准备负责初始化参数和推进描述符地址。程序流负责分支、有限循环和结束执行。P、U、C、F、J 的有界局控程序共用启动服务、等待完成、返回终态的基本顺序。[五类局控生成程序](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cad3fa572d3cbf8515532df50868000806990b18/project/control_native_v1/images.py#L17-L62)

### 每条指令在做什么

| 类别 | 指令 | 用途 |
| --- | --- | --- |
| 派发 | `G_CALL` | 选择目标 Block 和完成 token，并快照参数寄存器。图 2 的 `G_CALL Ak,t1` 让 P1 执行 K 投影，用 t1 跟踪。 |
| 派发 | `L_EXEC` | 按执行描述符启动一项本地服务。例如在 U 内选择 N 的归一化或 E 的旋转，并绑定操作数和结果位置。 |
| 同步 | `G_WAIT` | 等掩码选中的活动 token 都收到匹配终态，再释放这些 token 和对应目标槽。图 2 的 `0x03` 同时选中 Q 投影的 t0 和 K 投影的 t1。 |
| 同步 | `G_EVENT` | 消费镜像中事先绑定的 READY 事件，把携带的标量写入目标寄存器，用于已注册的阶段就绪通知。 |
| 同步 | `L_WAIT` | 等匹配的本地服务结果。服务描述符规定完成条件，涉及数据写入时按服务约定等对应写确认。 |
| 参数准备 | `G_MOVI` | 将一个 32 位立即数写入参数寄存器。例如用两条初始化描述符地址的低、高字。 |
| 参数准备 | `G_ADDI64` | 向一个偶数索引开头的 64 位寄存器对加无符号立即数，检查溢出。native P 的连续描述符可用它推进指针。 |
| 程序流 | `G_JNZ` | 检查寄存器是否非零，在镜像编码的两个前向目标 PC 中选择其一。 |
| 程序流 | `G_LOOP` | 递减有界计数器。还有迭代时跳回较早的 PC，最后一轮退出。 |
| 程序流 | `G_END` | 在全局任务义务关闭后返回母控程序终态。 |
| 程序流 | `L_END` | 在局部义务关闭后向母控返回任务终态。 |

### 图 2(b) 模型算子、连接与发令顺序

两例比较同一段注意力前处理，从输入张量 `x` 得到施加旋转位置编码后的 Q、K。A 表示投影，B 表示逐头 RMSNorm，C 表示 RoPE。后缀 q/k 表示查询或键分支。V 投影、KV cache 和注意力分数计算在此图的范围之外。[Llama 实现](https://github.com/huggingface/transformers/blob/v4.53.3/src/transformers/models/llama/modeling_llama.py#L187-L215) · [Qwen3 实现](https://github.com/huggingface/transformers/blob/v4.53.3/src/transformers/models/qwen3/modeling_qwen3.py#L159-L190) · [Qwen3-4B 配置](https://huggingface.co/Qwen/Qwen3-4B/blob/e619e22b5609bd7c38a835536155c19825f8fa5e/config.json)

| 阶段 | 候选位置 | Llama 3.2-3B | Qwen3-4B |
| --- | --- | --- | --- |
| Aq / Ak | P0 / P1 | 从同一个 `x` 分别产生 Q 和 K。 | 同样分别产生 Q 和 K。 |
| Bq / Bk | U0.N / U1.N | 投影结果直接进入 RoPE 阶段。 | 各自沿 head 维度做 RMSNorm。Q、K 使用各自的缩放参数。 |
| Cq / Ck | U0.E / U1.E | 对投影结果应用 RoPE。 | 对归一化后的 Q、K 应用 RoPE。 |

**数据路径。** Llama 的 P0 和 P1 把 Q、K 分别写到 U0 和 U1 的输入位置，由 E 读取并执行 RoPE。Qwen3 的对应路径先送到各自的 N。图例采用本地 S 回放，N 把归一化结果写回 S，再由 E 读出。图中的蓝色箭头表示张量依赖。两个程序可以在一套 Block 清单上表达不同依赖，各条路径须绑定到已实现的端口和缓冲区。[U 的 N/E/S 宏组织](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/pu_leaf_base/README.md#L18) · [RMSNorm 合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/BLOCK_V2.md#L62-L70) · [RoPE 合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/BLOCK_V2.md#L46-L50)

**指令顺序。** 两边都先发 Aq、Ak，分配 t0、t1，用 `G_WAIT 0x03` 等两个投影结果到达各 U。在 Llama 中，下一批是 Cq、Ck，等 `0x0C` 后结束。在 Qwen3 中，下一批是 Bq、Bk，先等 `0x0C` 确认两份归一化结果。U0、U1 的前序任务退役后，母控复用它们执行 Cq、Ck，用 `0x30` 等两路 RoPE 结束。每批的双路等待是图中选用的示例调度，两条分支的实际数据依赖各自独立。

**部署条件。** 两图是算子级候选映射。描述符还需绑定权重、逐头归一化参数、RoPE 系数与 lane 排列，以及数据格式和地址。若生产者的终态只确认本地写入，程序需要安排跨 Block 搬运并等待目的写确认。两种模型的完整数值和端到端 RTL 执行留待验证。

## 图 3　三 P FFN 的程序与描述符复用

![图 3 三 P FFN 的程序与描述符复用](ffn-program-reuse.svg)

**图 3(a) 一份循环体如何调用三个 P。** 左栏展示母控程序结构。初始化将描述符指针 `p` 设到基地址 `B`，把循环次数设为 64。每轮依次调用 P0、P1、P2，分别分配 t0、t1、t2。每次调用会捕获当时的描述符引用，随后 `G_ADDI64` 将指针增加 128 字节，指向下一条记录。三次调用发出后，`G_WAIT 0x07` 等齐三路任务终态。随后 `G_LOOP` 回到循环开头，最后一轮执行完后进入 `G_END`。图中的 `p` 是 64 位描述符指针对的简称。 [母控程序生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/block_local_native/ffn_program_emit.py#L20-L49)

**右栏展示局控复用。** P0、P1、P2 各装一份内容相同的 352 B 镜像。母控消息携带描述符引用，局控经共享 DMA 取回实际记录。记录里的权重地址、输出列范围和 SRAM 位置随任务变化。每个局控用同样的 `L_EXEC → L_WAIT → L_END` 启动服务、等待结果、返回终态。 [局控镜像生成器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/shared_x_control/make_lc_kernel.py#L15-L34)

**图 3(b) 每轮怎样选描述符。** `B` 是 DDR 描述符区的基地址，`D0` 等是从零开始编号的记录。第 0 轮给 P0、P1、P2 分配 `D0`、`D1`、`D2`。第 1 轮从 `B + 384` 开始，依次取 `D3` 到 `D5`。第 63 轮用 `D189` 到 `D191`。一般地，第 `r` 轮的 `P_i` 读 `D[3r+i]`，字节地址为 `B + 128(3r+i)`。橙色格是 DDR 记录，蓝色格是轮末的等待。掩码 `0x07` 选中 bit 0、1、2，对应 t0、t1、t2，等齐后下一轮才能复用这些 token。 [循环展开与地址校验](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/block_local_native/ffn_program_emit.py#L20-L49)

| 存储或计数 | 本实验的值 | 含义 |
| --- | --- | --- |
| 母控镜像 | 272 B | 128 B 头部、17 条 8 B 指令、8 B 对齐填充。17 条由 8 条初始化、8 条循环体和 1 条结束指令组成。 |
| 局控镜像 | 352 B / P | 每个 P 各装一份相同镜像，包含三条指令和镜像内的任务表、执行记录等。 |
| 四份程序镜像合计 | 1,328 B | 一份母控镜像，加三份局控镜像。 |
| DDR 描述符区 | 24,576 B（24 KiB） | 192 条记录，每条 128 B，单独保存任务参数。 |
| 运行时调用 | 192 次 | 64 轮，每轮调用三个 P。 |

**论文中的主张。** 母控只保存一次重复调度的循环体，局控内核按目标 Block 复用，逐任务变化保存在 DDR 描述符中。这组数字来自三 P FFN 夹具。实验采用 Qwen2.5-3B 的 FFN 尺寸和合成整数权重，K 分块搬运和外层 Gate/Up、Down 阶段由夹具组织。 [FFN 实验与范围](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/experiments/issue-250-three-p-ffn.md#L17-L25)

## 图 4　保持母控指令流，调整 Block 内部算子

![图 4 二级控制如何隔离局部算子变化](scheduling-decoupling.svg)

**上半图逐项对照母控层。** 左右各画同一组 C0、U0 和母控。C0 把输入 `x` 发给 U0，U0 把准备好的操作数 `b` 送回 C0。两个方向的蓝色箭头在左右完全对齐。四个指令框也逐项对应，先 `G_CALL C0,t2`，再 `G_CALL U0,t3`，接着 `G_WAIT 0x0C` 等 t2 和 t3，最后 `G_END`。两列从各自的 C0 向下展开，因此同一组跨 Block 连接和同一段母控程序可以直接对照。 [C/U 参考程序](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/cad3fa572d3cbf8515532df50868000806990b18/project/control_native_v1/images.py#L19-L35) · [母控调用与等待](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/mother_control_native/mc_native_controller.sv#L327-L352) · [局部写回和完成](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/block_cfj_v1/ucf_s_compute_client.sv#L46-L80)

**下半图展开交换完成后的 C0。** 两版保留 C0 的交换前缀、输入输出地址和格式。成功终态都在 `y` 写确认后返回。B 的 `α` 在产品配置时装入 C0 的 S。U0 的程序和跨 Block 接口在两个示例中共用。

| | A　激活加偏置 | B　激活乘增益后加偏置 |
| --- | --- | --- |
| 计算 | `y = SiLU(x) + b` | `y = α × SiLU(x) + b` |
| 中间结果 | G 将 `g` 写到 S。E 从 S 读取 `g` 和 `b`。 | G 通过橙色旁路把 `g` 送给 E 的第一操作数端口。E 从 S 取 `α`，将乘积 `m` 写回 S。随后同一颗 E 从 S 读 `m`、`b` 做加法。 |
| 局控程序 | 两对 `L_EXEC / L_WAIT`，执行 SiLU、ADD，最后 `L_END`。 | 三对 `L_EXEC / L_WAIT`，执行 SiLU、MUL、ADD，最后 `L_END`。 |
| 产品连接 | 使用经过适配器的固定 S 路径。 | 在预留的 G/E 端点之间接入后制旁路，最终写回仍走固定 S 路径。 |

**局控和描述符分别改什么。** `d0–d2` 对应 C0 两版共用的 RESERVE、SEND、RECEIVE，已经用上半图的数据箭头表达。下半图从 `d3` 开始。A 的 `d3` 指定激活结果写到 S，`d4` 指定 ADD。B 的 `d3` 选旁路输出，`d4` 指定 MUL 并选旁路第一操作数，`d5` 指定 ADD。新增的一对指令改变局控指令流。每次局控等待复用局部 token 0，母控 t2 贯穿整个 C0 任务。图中重复的 E 是同一颗宏的两次调用，重复的 S 是同一颗 SRAM 的不同地址。 [局控执行记录示例](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/experiments/cfj_leaf_base/stage_groups.py#L113-L139) · [E 适配器](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/block_cfj_v1/cfj_e_port.sv#L16-L35)

**证据范围。** 该示例以兼容的入口、依赖、张量格式、可见时点和服务约束为前提。定点实现须遵守舍入、饱和和有效 lane 约束。旁路跨过的是 `g` 的 SRAM 中转，现有适配器仍可能按描述符读取占位操作数。C 夹具已验证 G→E 直送与 SRAM 回放的同功能对照，本图的增益版本尚未端到端验证。 [定点算术](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/docs/BLOCK_V2.md#L46-L60) · [旁路端点 RTL](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/project/rtl/block_cfj_v1/block_cfj_cf.sv#L100-L132) · [物理网表回放](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/9abd46f5cbb4534bcfc614571ccd6d402ad11882/work/YUZE-LU/211/README.md#L109-L114)
