# 完整控制镜像、装载准入与恢复合同 v0.1

2026-11-04，Asia/Shanghai。Issue179 / Draft PR180，第3步；父提交add63270a2faf707fac035898dd13028ceb1135f。
上游PR176本轮开始仍为08f2ea20a11dfdd09892a67599163e32b7237edb，说明／评论／review无变化；上传前核对记录见[同步索引](../../work/Melodydt/179/pr176-sync.json)。
本合同为proposed研究版本；代码在[control_image_v0_1](../../project/control_image_v0_1/README.md)。它推进R1装载基础，**没有实现R2 PC执行器、控制RTL或完整Block**。

## 1. 从分离机器码到完整镜像

沿用[ISA v0.1](CONTROL_ISA_V0_1.md)，24个操作码、128bit指令及既有记录布局不变。
每份镜像从128B image_header起，随后依次为instruction、task、object、execution、transfer、event_binding。
指令16B、小端；其他段记录分别为64／64／128／64／16B。段非空时紧接上一段且16B对齐，空段count=offset=0；禁止空洞、重叠、尾随字节或未知保留位。
所有PC以指令为单位，段offset和total_bytes以字节为单位，不混用。

母控只拥有指令与event_binding；局控只拥有指令及task/object/execution/transfer。字段意义及头部字节偏移仍由ISA原表定义。
逻辑静态内容上限：母控4608B、局控8192B；加各自128B镜像头后，最大4736B／8320B。
这不是已实现的SRAM规格。若9局控＋1母控均单独保留镜像头，额外1280B，76.5KiB内容预算变为77.75KiB，仍不含参数、队列、活动状态、配置逻辑和物理成本。

| 案例 | 母控 | 局控0 | 局控1 | 总计 |
|---|---:|---:|---:|---:|
| empty_task | 176B | 208B | — | 384B |
| single_M_clear | 176B | 368B | — | 544B |
| receiver_first_16B | 224B | 496B | 432B | 1152B |

3案例7镜像共2080B＝896B头＋464B指令＋720B描述符。bundles.json保存完整hex和manifest，不再只提供分离记录；可逐字重建。

## 2. 镜像集合与准入范围

每次部署为一个cohort：1母控＋所需1～2局控的完整镜像集合。manifest明确schema、bundle、topology_id、native_abi_id、capacity_profile_id，以及每target的bytes、program_image_id、SHA-256。
manifest按UTF-8 JSON、sort_keys=true、分隔符(',',':')、ensure_ascii=false、无末尾换行规范化后再计算SHA-256；主机另提供可信的预期manifest摘要。
每个镜像摘要覆盖含头部在内的全部实际字节。短ID不能替代摘要：三个案例会复用母控ID200／局控ID100，所以“ID相同”不能证明来自同一程序集合。
SHA只检查完整性与配套关系，**不提供来源签名或身份认证**；本轮没有部署安全启动。

研究profile ID=0x17630001，native ABI=65537，topology ID=393400001。它们是有界fixture登记，不是已验证真实M11/M12布线的凭证。
母控支持G_CALL/G_WAIT/G_EVENT/G_MOVI/G_END；局控支持L_OPEN/L_EXEC/L_RX/L_TX/L_WAIT/L_MOVI/L_DROP/L_REPORT/L_END。其余合法ISA在本profile中仍拒绝，循环／分支留待R2后续扩展。
每局控仅1驻留任务、最多1个RAW16对象、1个在途服务；仅接收先行研究路线255→0、0→1。母控每job每局控调用一次，禁止未消耗READY、重复事件／调用和未退休任务。
对象必须合法落在16KiB S地址空间，任务与头部的资源、入口、ABI、拓扑、镜像身份一致。仅允许M service0/op6，不开放其他native运算或动态参数。
对端TX/RX的edge、invocation、fragment、version、格式及字节数必须一一匹配；缺对端、缺READY依赖、错误方向、对象／令牌义务未结束及未使用的服务描述符均拒绝。

这些是静态准入检查；没有据此证明取指行为、实际数值、S写确认、物理连通或无死锁。完整编译器、通用拓扑和全部表容量支持仍待研究。

## 3. 配置动作和装载时序

主机／启动侧软件装载母控与局控本地程序存储；运行母控仍只发送CALL＋参数。
本轮提供[typed配置API](../../project/control_image_v0_1/config_contract.json)，不是新增G_*／L_*，也没有冻结MMIO地址、外部总线或flit编码。JSON hex是文件表示；WRITE16的data是16个二进制字节。

| 动作 | 关键输入与单位 | 状态变化及约束 |
|---|---|---|
| BEGIN | manifest、可信预期manifest SHA | 全cohort空闲、元数据合法后，全部旧valid清零，软件generation加1，进入LOADING |
| WRITE16 | target、字节offset、16B data、generation | 从0开始连续写；不允许乱序、重复、越界或写已VERIFY的目标 |
| VERIFY | target、generation | 全长已到后核实际SHA、镜像头／段／服务；仅标记verified，仍不能执行 |
| COMMIT | generation | 所有目标均verified；重新核实际RAM、manifest及跨镜像相容性，一次性置全cohort valid，进入READY |
| START | 预期manifest SHA | 身份及有效位正确、再次校验且空闲后进入RUNNING；本模型仅记录准入，不运行PC |
| QUIESCE | 无 | READY／RUNNING→DRAINING；硬件实现须停止新接单并继续已有义务 |
| OBSERVE_ACTIVITY | 五类0..8计数，须全提供 | 输入外部观测；不能把写0理解成硬件已自动排空 |
| DRAIN_ACK | 无 | 五类义务全0且无复位确认待办，DRAINING→READY |
| RESET | 无 | 全部valid清零、INVALID；保留RAM和观测，要求provider协同复位确认 |
| RESET_ACK | all_providers_reset=true | 外部事实；清除观测与待确认位，仍INVALID，必须完整重装 |
| ABORT | 无 | LOADING→INVALID，不自动恢复旧镜像 |

首版采用单bank。BEGIN元数据错误在接受之前拒绝，保留原READY；一旦合法BEGIN接受，旧镜像全部失效，中途失败须重装，不能依赖旧RAM自动回滚。
LOADING中写序、generation、校验或提交错误使整个候选集合INVALID；其他状态的写入直接拒绝并保持已提交RAM。
VERIFY与COMMIT之间、COMMIT与START之间都再次核实际字节，避免“曾校验”被误当成“现在仍正确”。
主机／参考模型承担SHA和重型静态检查；未来硬件须提供不可绕过的状态／写入／valid互锁。片上SHA、读回接口、软件信任边界及面积仍待冻结／计价。

## 4. 排空、复位与无tag宏

装载前同时核五类义务：tasks（活动任务）、data（传输／写入／ACK）、returns（返回／事件holding）、contexts（对象借用／原生上下文）、untagged（无tag provider命令／响应）。
五类分别非零都阻止DRAIN_ACK及更新；不能只看busy、CALL令牌或程序PC结束。计数0..8是软件模型的有限观测界限，不是RTL队列深度配置。
仅母控／局控复位不足以保证M/G等原生provider没有旧响应。软件generation只拒绝旧配置写，**没有给native端口增加tag**。
硬复位后须让本次cohort涉及的provider、适配器、收发端及返回holding共同复位／清理，并取得外部确认；之后仍从BEGIN完整装载。
RESET_ACK参数在本模型中是测试／调用者提供的事实，不是已存在的硬件信号，更不证明真实provider已经复位。后续RTL必须明确产生方、覆盖范围、接受时点和验证用例。
空闲状态意外观察到非零义务／迟到响应立即失效全部镜像并要求cohort复位，不能将其当成新任务结果。

本轮不支持运行中改程序、断电保持、热切换、双bank回滚、活动任务续跑或宏级电源开关。

## 5. 验证、上一轮纠正及下一步

30组镜像／装载测试覆盖手写头部字节向量、7镜像重建、错误头／偏移／保留位／能力、对端与READY、部分装载、跨案例同短ID混用、有效位原子提交、运行中写、校验后损坏、五类排空、迟到响应及复位重装。
上一轮参考轨迹修正：消费者READY经G_EVENT写入母控R0=1，所以后续生产者CALL快照arg0应为1，即使task.argument_mask=0会在局控丢弃该参数。cases.json、golden_traces.json与oracle已同步，新增第28组轨迹检查；原27组的历史回执保留。
连同ISA 8组、接口15组、轨迹28组共81组通过；管理结构检查另计。实际命令、工具、输入／输出SHA见[来源](../../work/Melodydt/179/control-image-sources.json)及[验证](../../work/Melodydt/179/control-image-validation.json)。
测试不是RTL、模型数值或物理通过；没有启动服务器作业／自动监测。

下一步：直接从这7份二进制镜像取指，实现有界母控／局控PC执行模型。禁止用cases.json作为运行端调度脚本；它只用于独立oracle。执行端实现有限寄存器、令牌、对象与队列，产生实际CALL／命令／READY／ACK／释放轨迹，与修正后的独立参考比较，再验证背压、错误及连续job。完整Block仍是外部接入门。

## 第4步接续（2026-11-04 19:46 CST）

[二进制执行模型](CONTROL_EXECUTION_MODEL_V0_1.md)现接在本装载参考后：经WRITE16／VERIFY／COMMIT／START准入，再由独立Machine按PC读取实际镜像。loader.START自身仍不执行指令；Machine成功／已排空M错误终态后返回READY，可不重装、不复位连续运行。重装后必须新建绑定新镜像的Machine。新增执行证据没有实现本合同中实际provider协同复位确认或硬件写口互锁，这些仍待研究。

