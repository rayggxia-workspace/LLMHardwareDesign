# 母控/局控 ISA v0.1：指令、描述符和二进制编码

2026-11-04，Asia/Shanghai；[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)，负责人Melodydt。配套[方案与研究步骤](TWO_LEVEL_CONTROL_PLAN.md)。

**proposed研究规范。** 本轮可用参考工具编码/解码指令和记录；没有新增本ISA的RTL执行、控制系统物理、原生服务实现或LLM质量验收。它不是PR152旧表编码或PR163旧C指令的二进制兼容更新。完整镜像装配/语义编译/原生服务注册仍由R1接收，不能将编码器输出当作已可在旧硬件直接运行。

机器规范唯一入口：[isa.json](../../project/control_isa_v0_1/isa.json)；[参考codec/测试](../../project/control_isa_v0_1/README.md)。本文件的位表和记录表由该规范生成，语义仍须按本文件及固定原生ABI落实。

## 1. 通用规则

- 指令固定128bit=16B，程序PC是指令索引，字节地址=instruction_offset+16×PC。
- 指令/记录所有多字节无符号字段均小端；指令word_hex展示高位在左的32个十六进制字符（128位）。二者不能直接照抄为同序字节。
- 指令flags/imm/d及该操作没有列出的a/b/c/x/y字段全部为0；未知操作码、非零保留位、非法角色、越界字段必须拒绝。
- 母控与局控操作码空间分开，NOP共用；版本号在镜像头。下一版本可以扩字段，但不得静默改变v0.1含义。
- 指令操作数a/b/c/d均8bit。描述符索引可编码0..255，实际表项数/硬件profile更小则按更小范围拒绝。
- R0..R7为各控制核独立32bit无符号标量寄存器；L_ADDI的x按有符号32bit补码解释，运算越出uint32报错，不回绕。
- G/L_LOOP使用寄存器计数，入口计数必须>0，先减1，非零才跳回x；x必须指向更早PC。G/L_BRANCH只允许指向更晚的有效PC。零次循环由前向条件跳转绕过。
- 所有程序/任务都有非零max_steps，接收一条指令计一步；正常WAIT停顿不重复计步。预算、外部进展和任务取消策略分别记录；超预算进入错误，不修改有效时序/功能门。
- 编译器必须检查循环计数初始化、循环体对计数器的修改、最大展开步数、类型、资源、地址和对象生命周期；当前codec仅检查位编码和所列PC方向/范围，不证明这些语义。
- flags等字段没有自动错误修正。程序RAM内容不假设由复位初始化；空闲、排空并核验镜像后才准入。

## 2. 128bit指令位布局

| 字段 | 位范围（高:低） | 位数 |
|---|---|---:|
| opcode | 127:120 | 8 |
| flags | 119:112 | 8 |
| a | 111:104 | 8 |
| b | 103:96 | 8 |
| c | 95:88 | 8 |
| d | 87:80 | 8 |
| imm | 79:64 | 16 |
| x | 63:32 | 32 |
| y | 31:0 | 32 |

例如 `G_CALL a=2,b=0,c=1`：

- 高位在左的word_hex：`10000200010000000000000000000000`。
- 按实际内存顺序的16字节：`00 00 00 00 00 00 00 00 00 00 00 01 00 02 00 10`。
- opcode=0x10，Block=2，完成令牌=0，目标局控任务描述符=1；其他字段为0。
- 指令字与其参数快照/消息包不同；G_CALL会根据部署表填充目标镜像/拓扑身份，复制当前GPR快照并分配task_sequence。

## 3. 指令种类、操作码与操作数字段

下表列出的字段以外均必须为0；max是编码范围，实际profile/表项数仍须检查。表中英文语义与isa.json一致，下节补充协议约束。

| 操作码 | 助记符 | 角色 | 有效操作数字段及范围 | 语义 |
|---|---|---|---|---|
| `0x00` | `NOP` | both | 无 | No state change; advance PC. |
| `0x10` | `G_CALL` | mother | a=0..255；b=0..31；c=0..255 | a=Block ID; b=completion token; c=resident local task descriptor. Snapshot global R0..R7 into task arguments; advance after command packet acceptance. |
| `0x11` | `G_WAIT` | mother | x=1..4294967295 | Wait for ALL completion tokens in x; consume them once. A failed task enters fault handling. |
| `0x12` | `G_EVENT` | mother | a=0..7；b=0..31 | Wait for event b from its configured producer, copy scalar payload to R[a], then consume event. |
| `0x13` | `G_MOVI` | mother | a=0..7；x=0..4294967295 | R[a]=unsigned x. |
| `0x14` | `G_LOOP` | mother | a=0..7；x=0..4294967295 | Require R[a]>0; decrement; if nonzero branch to earlier PC x, otherwise advance. |
| `0x15` | `G_BRANCH` | mother | a=0..7；x=0..4294967295；y=0..4294967295 | Branch to x if R[a]!=0, otherwise y. Both targets must be forward in v0.1. |
| `0x16` | `G_PARAM` | mother | a=0..7；x=0..4294967295 | Read immutable job scalar parameter word x into R[a]; wait for actual response. |
| `0x1E` | `G_FAIL` | mother | x=1..4294967295 | Enter coordinated fault handling with reason x; not successful completion. |
| `0x1F` | `G_END` | mother | 无 | Publish held completion only after all child/data/output obligations and current-job events are closed. |
| `0x40` | `L_OPEN` | local | a=0..15 | Open object a using its resident descriptor. Range/overlap/version checks precede reservation; data initially invalid. |
| `0x41` | `L_EXEC` | local | a=0..7；b=0..7；c=0..255 | a=resource, b=completion token, c=execution descriptor. Begin one typed adapter service. |
| `0x42` | `L_RX` | local | b=0..7；c=0..255 | Arm RX using transfer descriptor c; token b completes only after all real destination S write acknowledgements. |
| `0x43` | `L_TX` | local | b=0..7；c=0..255 | Start TX using transfer descriptor c; token b completes only after matching remote stored acknowledgement. |
| `0x44` | `L_WAIT` | local | x=1..255 | Wait for ALL tokens in x; consume them once; a failed service enters local fault handling. |
| `0x45` | `L_MOVI` | local | a=0..7；x=0..4294967295 | R[a]=unsigned x. |
| `0x46` | `L_ADDI` | local | a=0..7；x=0..4294967295 | Add signed two's-complement imm32 x to R[a]; trap on result outside uint32, never wrap. |
| `0x47` | `L_ARG` | local | a=0..7；b=0..7 | R[a]=immutable task argument b captured at admission. |
| `0x48` | `L_LOOP` | local | a=0..7；x=0..4294967295 | Require R[a]>0; decrement; if nonzero branch to earlier PC x, otherwise advance. |
| `0x49` | `L_DROP` | local | a=0..15 | Release object a only when no writers/readers/transfer obligations remain. |
| `0x4A` | `L_REPORT` | local | a=0..31；b=0..7；c=0..1 | Send event a with scalar R[b]; c=0 READY or c=1 PROGRESS. Preserve current identity and payload until acceptance. |
| `0x4B` | `L_BRANCH` | local | a=0..7；x=0..4294967295；y=0..4294967295 | Branch to x if R[a]!=0 else y; forward targets only in v0.1. |
| `0x4E` | `L_FAIL` | local | x=1..4294967295 | Enter local coordinated fault handling with reason x. |
| `0x4F` | `L_END` | local | 无 | Complete only when service tokens are consumed, resources are closed/transferred by declared policy and output obligations are satisfied. |

### 母控操作的补充语义

- G_CALL的a是目标Block；b是全局完成令牌0..31；c是该局控镜像中的task描述符索引。只在消息实际接受时计为发出、保存参数快照和建立义务。目标Block接单能力和完成接收信用须预留；不能仅依据空闲预测创建无处返回的任务。
- G_WAIT的x按bit i选择令牌i，必须非零；等待全部成功完成并消费一次，不能把接单当成完成。已出现服务错误时进入故障路径，不被另一个WAIT掩盖。
- G_EVENT的b是全局标量事件槽，源由event_binding固定；匹配当前job/epoch/活动task及事件序号才可接收，copy到R[a]后消费。事件已占用时施加背压，不覆盖旧内容。
- G_PARAM的x是当前job不可变标量参数区的32bit字索引，实际响应后更新寄存器；不是读取任意张量。权重、KV、状态和系数的MEM硬件/带宽另计。
- G_BRANCH以R[a]非零为真；结合运行时标量事件可选择有界后续任务，不改变金属线。
- G_END要求所有子任务完成令牌已消费、当前job事件和最终输出义务已处理，无悬空控制/数据服务；不满足则报状态错误。G_FAIL是显式错误入口，不是成功HALT。

### 局控操作的补充语义

- L_OPEN读取object描述符，对base/length寄存器引用当场求值并快照；检查实际容量、16B分配对齐、与活对象不重叠和版本。新对象数据无效，不能从旧RAM内容推导有效。
- L_EXEC的a为资源编号，b为局部令牌0..7，c为execution描述符。资源缺失/服务未注册报错；资源暂忙或服务队列无空位时保持指令，不重复发射。令牌仅在服务实际接受时分配，完成包含独立service_sequence，WAIT消费后才可复用。
- L_RX/L_TX的a必须0；b为令牌，c为transfer描述符，方向字段必须分别为0/1。所有寄存器派生地址/count/invocation/fragment在服务接受时快照。
- L_WAIT的x仅bit0..7可置位，等待全部匹配令牌后消费。描述符的completion决定该令牌对应原生命令完成、本地实际存储或排空；不能让编译器任意把弱事件升级成强完成。
- L_ARG从任务准入时已锁存的参数副本读取。新任务的局控R0..R7清0；已声明保留的数据/上下文依然按对象/上下文版本管理，不因寄存器清0失去归属。argument_mask未选择的任务参数置0。
- L_REPORT按事件号a发送R[b]快照及身份，c=0为READY、c=1为PROGRESS；消息接受后推进PC。母控未消费时由其事件槽保持；reporter在背压中保持tuple并继续办理数据/返回。
- L_DROP仅在无读写、无未确认消费者/传输、无借用上下文时回收；不能以last或宏busy=0替代。
- L_END要求所有服务令牌已消费，所有报告已接受，非保留对象/上下文已关闭或释放，输出义务已满足。task的retained_object_mask/retained_context_mask只有明确声明的状态可以继续归本Block所有，后续任务必须匹配同job/epoch/版本；切换程序镜像前必须排空/导出/显式丢弃。首个P原型两项保留mask都取0；R状态语义另由R5接收。

## 4. 资源、Block和格式编号

| 类别 | 编码 |
|---|---|
| 资源 | M=0，N=1，E=2，G=3，R=4，S=5，T=6，MEM=7 |
| Block类型 | P=0，U=1，C=2，F=3，J=4 |
| 格式 | S8=0，S16=1，S32=2，S64=3，RAW_BYTES=4 |
| P/U/C/F/J基础资源mask | 0x29 / 0x26 / 0x3C / 0x2C / 0x64，bit i表示资源i |
| 无寄存器引用/无对象 | 0xFF；寄存器有效0..7，对象有效0..15 |

资源类型只说明该实例存在；数值尺度、布局、长度上限、原生操作、上下文和物理可达性由native_abi_id及能力profile进一步限定。相同S16宽度不代表Q5.10、Q1.14等可以无转换互用。MEM bit仅在真实服务已实例化并接通时增加。

## 5. 描述符和消息二进制布局

所有记录按16B对齐。表中偏移是记录起点的字节偏移；每个字段小端。默认255仅用于“无引用”，不可自动解释为对象0或寄存器0。gap和保留字段非零即拒绝。以下9类布局由机器规范生成：

### object：64字节

| 字段 | 字节偏移 | 位宽 | 默认/约束 |
|---|---:|---:|---|
| `version` | 0 | 16 | 固定1 |
| `object_id` | 2 | 8 | 最大15 |
| `kind` | 3 | 8 | 最大1 |
| `base_bytes` | 4 | 32 | 无符号 |
| `capacity_bytes` | 8 | 32 | 最小1；无符号 |
| `initial_valid_bytes` | 12 | 32 | 固定0 |
| `format` | 16 | 8 | 最大4 |
| `alignment_log2` | 17 | 8 | 固定4 |
| `flags` | 18 | 16 | 固定0 |
| `object_version` | 20 | 32 | 无符号 |
| `base_reg` | 24 | 8 | 默认255 |
| `length_reg` | 25 | 8 | 默认255 |
| `length_bytes` | 28 | 32 | 最小1；无符号 |
| `native_abi_id` | 32 | 32 | 无符号 |

未列出的字节均为0。

### task：64字节

| 字段 | 字节偏移 | 位宽 | 默认/约束 |
|---|---:|---:|---|
| `version` | 0 | 16 | 固定1 |
| `block_type` | 2 | 8 | 最大4 |
| `argument_mask` | 3 | 8 | 无符号 |
| `entry_pc` | 4 | 32 | 无符号 |
| `input_object_mask` | 8 | 16 | 无符号 |
| `output_object_mask` | 10 | 16 | 无符号 |
| `retained_object_mask` | 12 | 16 | 无符号 |
| `flags` | 14 | 16 | 固定0 |
| `max_steps` | 16 | 32 | 最小1；无符号 |
| `required_resources` | 20 | 32 | 无符号 |
| `program_image_id` | 24 | 32 | 无符号 |
| `topology_id` | 28 | 32 | 无符号 |
| `parameter_base` | 32 | 64 | 无符号 |
| `parameter_bytes` | 40 | 32 | 无符号 |
| `native_abi_id` | 44 | 32 | 无符号 |
| `retained_context_mask` | 48 | 16 | 无符号 |

未列出的字节均为0。

### execution：128字节

| 字段 | 字节偏移 | 位宽 | 默认/约束 |
|---|---:|---:|---|
| `version` | 0 | 16 | 固定1 |
| `resource` | 2 | 8 | 最大7 |
| `service` | 3 | 8 | 最大5 |
| `native_op` | 4 | 16 | 无符号 |
| `flags` | 6 | 16 | 固定0 |
| `src0` | 8 | 8 | 默认255 |
| `src1` | 9 | 8 | 默认255 |
| `src2` | 10 | 8 | 默认255 |
| `dst` | 11 | 8 | 默认255 |
| `context_id` | 12 | 8 | 最大15 |
| `completion` | 13 | 8 | 最大2 |
| `count` | 16 | 32 | 无符号 |
| `count_reg` | 20 | 8 | 默认255 |
| `src0_offset_reg` | 21 | 8 | 默认255 |
| `src1_offset_reg` | 22 | 8 | 默认255 |
| `src2_offset_reg` | 23 | 8 | 默认255 |
| `dst_offset_reg` | 24 | 8 | 默认255 |
| `parameter_index_reg` | 25 | 8 | 默认255 |
| `stride_bytes` | 28 | 32 | 无符号 |
| `src0_offset` | 32 | 32 | 无符号 |
| `src1_offset` | 36 | 32 | 无符号 |
| `src2_offset` | 40 | 32 | 无符号 |
| `dst_offset` | 44 | 32 | 无符号 |
| `parameter_ref` | 48 | 32 | 无符号 |
| `parameter_bytes` | 52 | 32 | 无符号 |
| `native_abi_id` | 56 | 32 | 无符号 |
| `native0` | 64 | 32 | 无符号 |
| `native1` | 68 | 32 | 无符号 |
| `native2` | 72 | 32 | 无符号 |
| `native3` | 76 | 32 | 无符号 |
| `native4` | 80 | 32 | 无符号 |
| `native5` | 84 | 32 | 无符号 |
| `native6` | 88 | 32 | 无符号 |
| `native7` | 92 | 32 | 无符号 |

未列出的字节均为0。

### transfer：64字节

| 字段 | 字节偏移 | 位宽 | 默认/约束 |
|---|---:|---:|---|
| `version` | 0 | 16 | 固定1 |
| `direction` | 2 | 8 | 最大1 |
| `format` | 3 | 8 | 最大4 |
| `object_id` | 4 | 8 | 最大15 |
| `port_id` | 5 | 8 | 无符号 |
| `offset_reg` | 6 | 8 | 默认255 |
| `count_reg` | 7 | 8 | 默认255 |
| `offset_bytes` | 8 | 32 | 无符号 |
| `count_bytes` | 12 | 32 | 无符号 |
| `stride_bytes` | 16 | 32 | 固定16 |
| `peer_block` | 20 | 8 | 无符号 |
| `peer_port` | 21 | 8 | 无符号 |
| `peer_object` | 22 | 8 | 最大15 |
| `invocation_reg` | 23 | 8 | 默认255 |
| `edge_id` | 24 | 32 | 无符号 |
| `invocation` | 28 | 32 | 无符号 |
| `fragment` | 32 | 32 | 无符号 |
| `fragment_reg` | 36 | 8 | 默认255 |
| `object_version` | 40 | 32 | 无符号 |
| `max_fragment_bytes` | 44 | 32 | 最小1；无符号 |

未列出的字节均为0。

### event_binding：16字节

| 字段 | 字节偏移 | 位宽 | 默认/约束 |
|---|---:|---:|---|
| `event_id` | 0 | 8 | 最大31 |
| `source_block` | 1 | 8 | 无符号 |
| `payload_kind` | 2 | 8 | 固定0 |
| `flags` | 3 | 8 | 固定0 |
| `message_kind` | 4 | 8 | 最大1 |

未列出的字节均为0。

### task_message：64字节

| 字段 | 字节偏移 | 位宽 | 默认/约束 |
|---|---:|---:|---|
| `version` | 0 | 16 | 固定1 |
| `kind` | 2 | 8 | 最大1 |
| `target_block` | 3 | 8 | 无符号 |
| `job_id` | 4 | 32 | 无符号 |
| `epoch` | 8 | 32 | 无符号 |
| `task_sequence` | 12 | 32 | 无符号 |
| `task_descriptor` | 16 | 8 | 无符号 |
| `completion_token` | 17 | 8 | 最大31 |
| `flags` | 18 | 16 | 固定0 |
| `program_image_id` | 20 | 32 | 无符号 |
| `topology_id` | 24 | 32 | 无符号 |
| `arg0` | 32 | 32 | 无符号 |
| `arg1` | 36 | 32 | 无符号 |
| `arg2` | 40 | 32 | 无符号 |
| `arg3` | 44 | 32 | 无符号 |
| `arg4` | 48 | 32 | 无符号 |
| `arg5` | 52 | 32 | 无符号 |
| `arg6` | 56 | 32 | 无符号 |
| `arg7` | 60 | 32 | 无符号 |

未列出的字节均为0。

### event_message：64字节

| 字段 | 字节偏移 | 位宽 | 默认/约束 |
|---|---:|---:|---|
| `version` | 0 | 16 | 固定1 |
| `kind` | 2 | 8 | 最大3 |
| `source_block` | 3 | 8 | 无符号 |
| `job_id` | 4 | 32 | 无符号 |
| `epoch` | 8 | 32 | 无符号 |
| `task_sequence` | 12 | 32 | 无符号 |
| `completion_token` | 16 | 8 | 默认255 |
| `event_id` | 17 | 8 | 默认255 |
| `status` | 18 | 16 | 无符号 |
| `scalar` | 20 | 32 | 无符号 |
| `confirmed_read_bytes` | 24 | 32 | 无符号 |
| `confirmed_write_bytes` | 28 | 32 | 无符号 |
| `flags` | 32 | 32 | 最大7 |
| `event_sequence` | 36 | 32 | 无符号 |
| `error_pc` | 40 | 32 | 默认4294967295 |
| `detail` | 44 | 32 | 无符号 |

未列出的字节均为0。

### image_header：128字节

| 字段 | 字节偏移 | 位宽 | 默认/约束 |
|---|---:|---:|---|
| `magic` | 0 | 64 | 固定0x313041534943424c |
| `version` | 8 | 16 | 固定1 |
| `role` | 10 | 8 | 最大1 |
| `header_units16` | 11 | 8 | 固定8 |
| `total_bytes` | 12 | 32 | 无符号 |
| `entry_pc` | 16 | 32 | 无符号 |
| `instruction_count` | 20 | 32 | 无符号 |
| `instruction_offset` | 24 | 32 | 无符号 |
| `task_count` | 28 | 16 | 无符号 |
| `object_count` | 30 | 16 | 无符号 |
| `execution_count` | 32 | 16 | 无符号 |
| `transfer_count` | 34 | 16 | 无符号 |
| `task_offset` | 36 | 32 | 无符号 |
| `object_offset` | 40 | 32 | 无符号 |
| `execution_offset` | 44 | 32 | 无符号 |
| `transfer_offset` | 48 | 32 | 无符号 |
| `max_steps` | 52 | 32 | 最小1；无符号 |
| `resource_mask` | 56 | 32 | 无符号 |
| `program_image_id` | 60 | 32 | 无符号 |
| `topology_id` | 64 | 32 | 无符号 |
| `native_abi_id` | 68 | 32 | 无符号 |
| `event_binding_count` | 72 | 16 | 无符号 |
| `event_binding_offset` | 76 | 32 | 无符号 |
| `scalar_parameter_words` | 80 | 32 | 无符号 |
| `capacity_profile_id` | 84 | 32 | 无符号 |

未列出的字节均为0。

### data_header：64字节

| 字段 | 字节偏移 | 位宽 | 默认/约束 |
|---|---:|---:|---|
| `version` | 0 | 16 | 固定1 |
| `kind` | 2 | 8 | 最大1 |
| `flags` | 3 | 8 | 最大3 |
| `job_id` | 4 | 32 | 无符号 |
| `epoch` | 8 | 32 | 无符号 |
| `edge_id` | 12 | 32 | 无符号 |
| `invocation` | 16 | 32 | 无符号 |
| `fragment` | 20 | 32 | 无符号 |
| `source_block` | 24 | 8 | 无符号 |
| `source_port` | 25 | 8 | 无符号 |
| `destination_block` | 26 | 8 | 无符号 |
| `destination_port` | 27 | 8 | 无符号 |
| `source_object` | 28 | 8 | 最大15 |
| `destination_object` | 29 | 8 | 最大15 |
| `format` | 30 | 8 | 最大4 |
| `status` | 31 | 8 | 无符号 |
| `object_version` | 32 | 32 | 无符号 |
| `valid_bytes` | 36 | 32 | 无符号 |
| `stored_bytes` | 40 | 32 | 无符号 |

未列出的字节均为0。

## 6. 各类记录的执行含义

**object（64B）。** kind=0为本块S，kind=1为本块T；T仅在实际存在并支持相应操作时使用。format只表示容器位宽，native_abi_id绑定具体尺度/布局。有效基址=base_bytes+可选R[base_reg]；有效逻辑长度在length_reg=0xFF时为length_bytes，否则为R[length_reg]，不得超过capacity_bytes或实际存储容量。初始valid固定0；实际RX/宏写入确认建立有效性。预约空间向16B取整，尾包不能越界。kind=T仍受其begin/fill/commit/drain/release合同约束，不能按随机S操作。

**task（64B）。** entry_pc为本局控程序入口，max_steps和required_resources均检查。input/output mask是对象访问/结果声明，输入尚未到达时程序仍需OPEN/RX/WAIT，不能据mask假定已存。retained mask表达任务结束后的显式归属，不是绕过引用检查的开关。parameter_base/bytes是有界MEM参数区引用，真实读取必须由注册服务完成。program/topology/native ABI与部署镜像匹配。原型只接收预先验证的静态对象布局；复杂跨任务保留由后续合同验证。

**execution（128B）。** 每个动态count/offset/参数索引寄存器只允许0..7或0xFF；count_reg=0xFF取count，否则取R[count_reg]；每个有效偏移=literal_offset+可选R[offset_reg]，加法不得溢出/越界。parameter_index_reg是已登记参数服务的索引输入，不能将其擅自当地址或直接访问任意外存。context_id标识本块宏上下文归属；M/N实际上下文数量按固定源进一步收紧。

| service | 编码 | 目标资源和语义要求 |
|---|---:|---|
| NATIVE_CMD | 0 | 一个已注册原生命令；native_op/native0..7的含义由native_abi_id绑定的原生端口合同决定 |
| M_FEED | 1 | S资源：执行已注册的M供数/装载服务；普通/宽口争用和真实feeder完成保留 |
| M_READOUT | 2 | M资源：真实结果读出/格式化，经适配写dst；要LOCAL_STORED须看到实际S确认 |
| VECTOR_PASS | 3 | N/E/G资源：一个已注册的统计、回放或向量分片服务，不隐含整个模型算子 |
| R_STATE | 4 | R资源：已注册的状态/卷积/递推分片服务；提交与全局发布分开 |
| MEM_REQUEST | 5 | 实际存在的MEM资源：请求有界参数/权重/状态服务，真实外存/D控制另列 |

native0..7按32bit字顺序传给**选定原生ABI注册项**，不是统一解释的八个随意参数。举例M的scale、GEMM分块描述符和RNE读出格式由原生接口明确；N的BEGIN/STATS/EXP/REPLAY等不同原生命令各有合同。R1必须把这些端口字段逐项登记成可机器检查的注册表并给独立向量，未注册native_abi_id/service/native_op组合必须拒绝。当前codec只编码这些容器字段，尚未实现原生运算lowering/检查，不能声称已生成可执行LLM宏程序。

completion=0为已注册的NATIVE_DONE，=1为LOCAL_STORED，=2为DRAINED。哪些service可使用何种完成条件由注册项限定，原生命令busy下降不能自动变成存储/释放事件。src0/src1/src2/dst为本块对象引用或0xFF；值需按服务真实使用情况检查，未使用的native字、引用、offset和count由注册项规定为0/0xFF。stride_bytes的意义也按该注册项限定，不能自由发明端口能力。

**transfer（64B）。** direction RX=0/TX=1。有效offset/count按同样寄存器规则求值；必须count>0、count<=max_fragment_bytes、预约范围足够且通道可达。v0.1对象帧在S中按16B连续字办理，stride_bytes固定16；逻辑尾字节数由count确定，最后16B分配内padding清0/无效字节不作为有效输出。真实S没有字节写使能时不得覆盖相邻未预约数据。invocation/fragment各为literal+可选寄存器，溢出拒绝；发送/接收两侧必须约定相同值。

**task_message（64B）。** kind=0为CALL，=1为指定任务CANCEL。CALL携带目标局控任务描述符、母控分配的完成令牌、8个32bit参数及版本身份。CANCEL保留目标/job/epoch/task_sequence，参数清0，按注册取消策略排空；不能撤回已写数据。控制链路首版建议32bit，每包16个flit，包内不交织；背压时各flit及包归属保持，不能以第一flit接收代替整个任务接受。

**event_message（64B）。** kind=0 READY、1 PROGRESS、2 TASK_DONE、3 ERROR；status=0成功，非零按固定错误表。TASK_DONE/ERROR携带匹配的全局completion_token，普通标量报告event_id有效；不适用的token/event_id=0xFF。event_sequence在同任务报告中单调递增，TASK_DONE取0；接收器检查重复/旧序号，未排空不得回绕。flags bit0为饱和、bit1为已知部分输出、bit2为确认前缀计数有效，其余0。计数表示实际已确认字节，不是未经确认的全部副作用；partial=0不证明没有物理写入。背压期间整包保持。

**data_header（64B）。** kind DATA=0，ACK=1；flags bit0表示最后片段，bit1表示错误，其他0。DATA的stored_bytes和status为0，声明valid_bytes；ACK在实际目的写入后返回stored_bytes/status。成功ACK必须stored_bytes=valid_bytes；错误ACK只报告已知确认前缀，不能成功退休源。匹配键含job、epoch、edge_id、invocation、fragment、双方端点/对象及object_version；ACK中的source/destination保留原DATA定义，不交换字段。数据头每片段一次，其后按顺序传ceil(valid_bytes/16)个128bit字，不能在一个物理端点交织帧；ACK头不跟payload。内部原生流若采用别的较小profile，必须单独注册，不能靠省字段宣称同等隔离。

**event_binding（16B）。** 每个事件槽绑定允许的source_block和message_kind，只接当前任务相关标量报告；它不是动态计算路由。未登记事件或错误来源拒绝/进入故障路径。

**image_header（128B）。** magic按内存字节为ASCII `LBCISA01`；version=1，role=0母控/1局控，header_units16=8。各段按offset/count寻址，记录大小按本规范；offset必须16B对齐，不重叠，不越total_bytes；空段count=0时offset=0。指令段非空且entry_pc有效。程序/任务/对象/执行/传输/事件绑定最大项数按容量profile限制。镜像SHA-256放部署清单，与短image/topology/ABI/profile ID共同核对；短ID不替代完整性校验。当前pack-record只编码/检查记录字段与保留字节，完整镜像段/内容/资源检查器仍待R1实现。

### 公共完成状态与错误码

| status | 含义 |
|---:|---|
| 0 | OK |
| 1 | BAD_OPCODE |
| 2 | BAD_FIELD_OR_RESERVED |
| 3 | BAD_IMAGE_OR_ABI |
| 4 | BAD_RESOURCE |
| 5 | BAD_DESCRIPTOR |
| 6 | BAD_RANGE_OR_FORMAT |
| 7 | BAD_STATE_OR_TOKEN |
| 8 | BAD_TAG_OR_SEQUENCE |
| 9 | NATIVE_ERROR |
| 10 | MEMORY_SERVICE_ERROR |
| 11 | CANCELLED |
| 12 | STEP_BUDGET_EXCEEDED |
| 13 | DRAIN_OR_RESET_REQUIRED |
| 14 | EXPLICIT_FAIL |

其他值保留。G_FAIL/L_FAIL的x保存为detail，status=14；其他错误detail保存固定ABI定义的错误细节，例如M失败行掩码。error_pc为触发指令PC，无对应指令时为0xFFFFFFFF。成功完成/标量报告的error_pc取0xFFFFFFFF、detail取0。错误不伪造成功token；等待中发现服务错误要进入相应故障处理，已持有的完成内容不能被随后错误改写。

## 7. 正常顺序与编号/完成边界

建议母控先G_CALL接收Block，让其OPEN+L_RX，并L_REPORT READY；母控G_EVENT得到准备事实后再G_CALL生产者；最后G_WAIT双方令牌。G_EVENT/WAIT不能阻止局控、收发和返回继续运行。

局部令牌、宏上下文、S对象、数据帧及母任务分别有生命周期。8个局部令牌可复用，但每次适配服务都有service_sequence并在接受时绑定身份；原生无tag端口只允许单在途并协调排空。job/epoch/task/event/service/fragment计数带在途事务不得回绕。错误/复位后的晚返回隔离、cohort和已写前缀按[方案第7节](TWO_LEVEL_CONTROL_PLAN.md#7-错误复位与状态发布)验证，不能据外层tag位数宣称无限迟到安全。

## 8. 示例、工具和实际接收范围

[examples.json](../../project/control_isa_v0_1/examples.json)含母控“先接收、等READY、后生产、等双方完成”及局控投影骨架，编码产物见[control-example-programs.json](../../work/Melodydt/179/control-example-programs.json)。这些示例展示机器码和控制顺序，尚无完整原生描述符/MEM/数值执行，不代表可直接驱动旧RTL。

在仓库根运行：

```powershell
python -X utf8 -B -m unittest discover -s project/control_isa_v0_1 -p test_codec.py -v
python -X utf8 -B project/control_isa_v0_1/codec.py examples --output work/Melodydt/179/control-example-programs.json
python -X utf8 -B project/control_isa_v0_1/codec.py decode --role mother --word 0x10000200010000000000000000000000
```

参考工具支持encode/decode及pack-record/unpack-record，验证明确限定为：固定编码/端序、角色、保留位、字段边界、记录布局和所列PC范围。独立人工机器码/内存字节向量与描述符字节向量、非法编码/角色/保留位/范围/分支拒绝检查属于本轮软件证据。没有执行本ISA的RTL、服务器、模型、物理或完整编译器语义验证；R1到R7保持待执行。
