# block-v2-offline/1 输入合同（固定两图）

本文件与`replay.validate()`定义本地输入格式；它不是通用JSON Schema引擎或Issue #63适配器。所有下述字段必填、未知键拒绝；整数不接受bool/float，重复JSON键/NaN/Infinity拒绝。未知时钟/服务率明确用null；已知epoch=0、version=0不能与未知混淆。

| 顶层字段 | 类型和本版约束 |
| --- | --- |
| `contract_version` | 精确字符串`block-v2-offline/1`，与旧`llm-resource-input/1`无冒充关系 |
| `source_commit` | 精确`88e9c4b2c3bb1b93b7155ba87ad11853e6c15512`，仅合同文档来源，不是新文件执行commit |
| `graph_id` | `graph1_reduce_rq`或`graph2_state_commit` |
| `nodes` | 每个节点有id/block/op/depends_on，必须与fixture所列相同；图2含previous_commit跨步依赖 |
| `edges` | 完整有向依赖列表，与固定图匹配；图内边与跨块传输区分 |
| `link` | bits=128、header_bytes=64、payload_alignment_bytes=64、max_packet_bytes=2048、hops=1、metadata_in_header=true |
| `initial_residency` | 固定每块驻留对象清单及`runtime_setup_charged=false`，详见README独立setup账 |
| `resources` | 只含instances/private_bytes/endpoint_fifo_bytes/max_inflight_messages/clock_hz/service_rate；实例各1，private容量≥显式峰值，FIFO每端点128..2048B，单在途=1，频率/服务率null |
| `protocol` | 两图分别使用下述固定数值/状态协议，修改顺序/端口/单位等拒绝 |
| `data` | 两图分别列张量、K分组或状态步骤；不内嵌expected |

张量对象精确包含`dtype, logical_bits, storage_bits, signedness, unit, shape, layout, values`。dtype与bits一致，容器不隐式提升，signedness固定signed，values逐维验证shape及每个码范围。

| 图1字段 | 约束 |
| --- | --- |
| data.x | INT8，unit1，shape[4]，layout=K |
| data.W | INT8，unit1，shape[2,4]，layout=output_channel,K |
| data.residual | INT8，unit2，shape[2]，layout=output_channel |
| data.groups | 两个唯一id0/1，各含id/k_start/k_stop/unit/dtype/shape/path；范围[0,2)/[2,4)，unit1，INT32[2]，path=[M,V] |
| protocol | reduce_order=[0,1]，rq_position=after_complete，rq_divisor=2，rounding=RNE，saturate_bits=8，output_bits=16 |
| 数据/驻留所有权 | M拥有x/W和partial槽，V拥有残差及归约/RQ/消费者输出；没有可写跨步持久状态 |
| 释放 | 静态槽整图保留；有效值的产生/释放按README所列依赖 |

| 图2字段 | 约束 |
| --- | --- |
| data.s0 | INT16[2]，unit1，layout=state_lane |
| data.input_format | dtype=INT16、logical_bits/storage_bits=16、signedness=signed、shape[2]、layout=state_lane |
| data.steps | 恰三步；每步含step/owner/unit/epoch/expected_version/values；step=1..3、owner=R、unit1、epoch0、expected_version=0..2、两个INT16码 |
| protocol | owner=R、snapshot_owner=S、unit1、epoch0、initial_version0、proposal_dtype=INT32、commit=atomic、overflow=reject、s_port=1RW、chunk_policy=preserve、failure_policy=abort_retry_same_step |
| 状态/缓冲所有权 | R old为唯一提交态，proposal/shadow私有；S snapshot独立只读copy，输入池可重读；显式控制元数据不能借FIFO保存 |
| guard/commit | 所有proposal lane精确可写INT16才整体提交，state/version同一概念事件发布；失败没有有效输出，保留旧态/版本/快照 |
| 重试 | 原step、unit/epoch/expected_version不变；失败输入传输付费，成功只一次；再次旧请求拒绝 |
| chunk/checkpoint | 状态/元数据/已计费日志一起保存；成功prefix恢复，不重置state/version；无真实模型history |

expected为独立文件，完整逐键/类型/列表顺序比较。图1包含合法数值、非法提前RQ反例、通信/容量账；图2包含正常轨迹、t2失败后的公开观察、重试轨迹、恢复一致性、setup/容量账。`fixtures/sha256.json`只在初次人工作者保存后建立，运行器/测试没有更新路径；同时替换实现、expected与checksum不在其防篡改保证内。

Python API验证相同类型/顺序合同的数值变体；CLI交付还要求输入和expected原字节与固定SHA一致。因此更改数字后即使另造匹配expected也不能伪装本批固定小图通过。输入格式错误/顺序改变/数值不匹配/容量不足均以清晰错误拒绝，不把未知信息写成0以凑检查。
