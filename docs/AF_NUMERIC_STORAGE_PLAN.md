> 根任务补记：F16在源码b77d6b7bae17e265bf20509e9ea53c1cdc5c4c9d、服务器job95209/node1/Verilator5.042下30CASE通过；完整A/F与样本质量未验收。下文是独立研究阶段记录，r02 pending等历史状态以本补记及F16运行回执更新。

# A/F数值、残差、布局与供参实施路线（F16独立审阅）

Issue151 / PR152；输入研究分支`febc0428e9d47d9bb4d4c83446690ff2e0c7926d`；原生选定源仍为`707878621b2add4ed218b8c43df2e95c9a56e2ba`。本稿只读当前隔离包、既有FamilySpec/角色合同及其锁定原图快照。新F16顶层读取字节对应根提供的修复提交`b77d6b7bae17e265bf20509e9ea53c1cdc5c4c9d`；以下区分源码观察、候选扩展和待验项目。本审阅没有执行RTL仿真、服务器操作或模型推理。

## 1. F16实际闭合了什么

旧A8输出为8个紧凑S16 Fin10值；旧F8只收8个S8 Fin7值，并把这些已窄化值作为自身原残差。因此，即使外侧增加RNE3/clipS8使A8结果能进入F8，残差也已经丢失部分原S16精度。A8本身仍只是QK→Softmax→PV上下文核，不是完整hidden→hidden的Attention子层。

新F16候选保留H8/I8、固定程序与三份S8 Fin7权重，将入口X和可变gamma改为S16 Fin10。N结果直接作为完整S16写回M的宽A容器；不再执行RNE3/clipS8。三次投影均为A16 Fin10×B8 Fin7、factor1/left0，M op5 RNE右移7到S16 Fin10。G fn0/gated=1按SiLU(gate)×up、RNE10得到Fin10 mid；原X独立保存，E7 shift0复制后与down用E0相加。它闭合了**有限核的共同数据单位与原S16残差**，也让gamma从真实输入进入，而非每次写死unity。

它没有实现A8→F16的真实双岛连线、目的存储确认、权重/gamma独立供给、完整A/F、真实H/I、模型量化质量或M11/M12物理绑定。F16入口17拍仍是X、padding、三权重和gamma的固定混合帧；不能把A8的一字输出直接接成这个完整帧。

## 2. 单位必须重新接收，不能借旧质量

令实数输入为`x_raw/2^Fin`。native RMS的整数合同为：

```text
A = floor(sum(x_raw²) * 2^16 / count) + epsilon_code * 2^16
factor = floor(2^38 / isqrt(A))
out_raw = clipS16(RNE30(x_raw * factor * gamma_raw))
```

`epsilon_real = epsilon_code / 2^(2*Fin)`解释其输入平方单位；实际输出还包含上述统计、整数根/除法及RNE误差。gamma_raw/1024是本F16的gamma实值，输出Fin10由gamma合同决定，不能从总线宽度自动推定。

| 本地profile | 输入Fin | epsilon_code | 对应epsilon_real |
|---|---:|---:|---:|
| 旧F8 | 7 | 1 | 0.00006103515625，即2^-14 |
| 新F16候选 | 10 | 1 | 0.00000095367431640625，即2^-20 |

二者相差64倍。FamilySpec中Qwen2.5/Qwen3/Llama/Gemma/Qwen3.5/Granite配置RMS epsilon为1e-6，Phi/Falcon为1e-5；各site精确绑定仍须按原图确认。Fin10时1e-6的理想code为1.048576，取1有约-4.6326%的epsilon相对差；1e-5的理想code为10.48576，不能用本次固定code1冒充。可变gamma也不自动实现RMS0：Gemma/Qwen3.5所需有效gamma=1+weight必须先正确量化并证明范围。F16没有Gemma的GELU/postNorm或Falcon的非线性前MuP。

S16 Fin10本身的实数范围约为[-32,31.999]。N、M、G、最终残差相加仍可能clip；done_saturated与done_error独立。有限整数oracle对齐不等于原模型误差、长序列稳定性或生成质量通过。

## 3. F16精确固定布局及生存期

所有地址为S的128bit字地址；四字对齐服务于真实512bit loader，而不是只有有效8项就只预约一字。

| 地址 | 字数/字节 | 内容及格式 | 产生、最后消费与保护 |
|---|---:|---|---|
| 448 | 1/16 | 原X，后覆写Norm X，均8×S16 Fin10 | beat0真实ACK；原X先复制466；474回读后才覆写448；Norm值到gate/up loader完毕前保活 |
| 449..451 | 3/48 | 宽A容器实际零padding | beats1..3硬件写零，不能仅靠无效lane标记或旧RAM值；gate/up loader可读取整个容器 |
| 452..455 | 4/64 | Wgate，64×S8 Fin7 | beats4..7；输出列n-major、k-minor；对应M执行消费完成前不可改 |
| 456..459 | 4/64 | Wup，同格式 | beats8..11；保存gate到464后才clear/re用M，up存465前不得覆盖 |
| 460..463 | 4/64 | Wdown，同格式 | beats12..15；down执行完成前保活 |
| 464/465 | 各1/16 | gate/up，8×S16 Fin10 | 各M两次op5四S32载体抽低16拼包，真实S写ACK；G配对读取两路后才能释放 |
| 466 | 1/16 | 原始X副本S16 Fin10 | start后实际保存；N统计/回放和E7 shift0都读它，绝不替换为Norm输出 |
| 467 | 1/16 | residual，原X的精确S16副本 | E7 shift0真实写ACK；一直保留到最终E0读完成 |
| 468 | 1/16 | gated mid，S16 Fin10 | G所有lane退休并写ACK；down宽A读取前不可改 |
| 469..471 | 3/48 | mid宽A实际零padding | G完成后逐字写零并ACK，才允许down loader |
| 472 | 1/16 | down，S16 Fin10 | M结果存S并ACK后交E0；M内部不能代替此保存 |
| 473 | 1/16 | final，S16 Fin10 | E0写ACK→真实S回读→T写入/commit→消费→release；peer stored ACK不在本核内 |
| 474 | 1/16 | N归一化结果，S16 Fin10 | N最后dst写ACK后服务完成，top再回读并覆写448；不是残差来源 |
| 475 | 1/16 | 可变gamma，8×S16 Fin10 | beat16单独映射此地址并实际ACK；N group全程不可变；不覆盖464，不再写literal unity |

固定预约窗口448..475共28字/448B；本实现不回收或别名这些窗口，按全部窗口保留预算。入口写17字/272B，其中有效224B（X16+权重192+gamma16），padding48B。T仅预约一字/16B，任务S/T payload预约合计464B；这不是整个控制器面积，也不是S16KiB+T6KiB物理宏总容量。helper/adapter/native上下文、hold寄存器和输入/输出控制另计，未用逻辑声明量冒充综合FF/PPA。

正常成功路径的普通S计数为39=29W+10R：

| 阶段 | 读 | 写 |
|---|---:|---:|
| 17拍入口 | 0 | 17 |
| 原X存466 | 0 | 1 |
| N RMS8统计、回放、gamma、dst | 3 | 1 |
| 474回读、Norm写448 | 1 | 1 |
| E7 shift0 residual | 1 | 1 |
| gate/up/down三次M结果保存 | 0 | 3 |
| G双输入与mid保存 | 2 | 1 |
| mid三字padding | 0 | 3 |
| E0 down+residual | 2 | 1 |
| final真实回读 | 1 | 0 |

此外M15命令/应答、loader3、N4命令/应答、E2服务、G1服务、T1字take及release。相同39总数不是未改数据流：F16多1个入口gamma写，去掉旧F8的literal unity gamma写。loader快速读不混入ordinary-S计数。错误/abort路径只能按已发生前缀计数，不能强行套正常39。

## 4. 扩H/I必须跨过的实际能力门

native loader每次rows1..8、tiles1..4，每tile K8，N输出列≤8；A按完整4×128bit容器组存储，B的8输出列×8K以n-major排列，S16 B还需两512bit half。现F16仅rows1/tiles1/H8/I8，换数组尺寸不会自动生成大矩阵程序。

单M可以对**同一输出tile**分K chunk累加S64，最终一次op5 RNE/clip；不能先把每个chunk窄化到Fin10再相加冒充同一数值。累加期间不能穿插会clear或覆盖merged上下文的其它投影。面积优先路线先完成gate/up、物化全部mid，再让down连续消费mid并累计；I过大时需真实MEM物化/回放。不能一边用同M算新gate/up、一边假定down的S64 partial免费保留/恢复。增加独立M或外部宽累加器是另一个待预算方案，不属于当前已实现能力。

Ncontroller当前count≤257，words_hold/word_index均6bit；把guard改大不够。H3072需要384字，words_hold至少9bit；4096项需要512字，若hold/index共宽实现至少10bit。请求count虽16bit，地址仍10bit/1024字，扩展加法和末地址检查必须同步保持。H3072的src/gamma/dst三段相离S16数组已需18432B>S16KiB；H2560三段15360B也只剩1024B，不能据此认定包含其它工作区的F/A可驻留。应设计真实供参/回放路径或不同存储控制器，整组统计与全组因子不能变成逐chunk独立RMS。

| 样本 | H/I | 仅S16 mid | H三数组Norm | 候选S8三份FFN权重 |
|---|---:|---:|---:|---:|
| Qwen2.5 | 2048/11008 | 22016B | 12288B | 67633152B |
| Qwen3 | 1024/3072 | 6144B | 6144B | 9437184B |
| Llama重建 | 2048/8192 | 16384B | 12288B | 50331648B |
| Gemma | 2560/10240 | 20480B | 15360B | 78643200B |
| Phi | 3072/8192 | 16384B | 18432B | 75497472B |
| Qwen3.5 | 2560/9216 | 18432B | 15360B | 70778880B |
| Granite单专家，非完整F | 1536/512 | 1024B | 9216B | 2359296B/专家 |
| Falcon | 2560/6144 | 12288B | 15360B | 47185920B |

以上是算术需求例，非接受S8权重量化或驻留全部权重的要求。参数可从版本明确的真实存储流式供给，ARM/固定程序必须证明可达性、chunk预约和供给进展；M11不能生成读控制、任意transpose、FIFO、位宽转换或MEM ACK。MEM接口/地址/带宽/故障与late-response隔离本轮仍GAP。

T6KiB只在S16、B1、单token、H3072纯payload条件下恰装一行6144B。prefill须按B×Sq×H×2算；Phi Sq2已有12288B，尚未计参数/工作区。真实模型H/头/维度保留，不为适配T改成8。

## 5. 现A8缺项与下一有界A候选

现A8仅接Q/K/V的S8 Fin7已排列操作数，完成QK→Softmax→PV，输出8×S16 Fin10。完整A_plain/A_gate还需要：原hidden保活与preNorm；Q/K/V（含源bias/融合切分）及Wo投影；Q/K headNorm；RoPE真实pair与cos/sin供给；位置/mask/window/GQA/KV缓存；head布局还原；可选gate；源gain/postNorm；最后原X残差。Q宽可能不等于H，不能把Wo输入也按H推断。

建议下一**新候选**为`A16_H8_SQ2_CAUSAL`：B1、Sq2、H8、D8、一Q/KV头、无cache、无bias、普通RMS、完整旋转、固定causal前缀，所有形状/程序永久固定，输入数据/权重/gamma可变，cos/sin来自声明的系数源。它按以下阶段覆盖非退化attention及残差，而不是只扩大A8操作数宽度：

1. 保存两个原X，逐token RMS8得到Fin10；读取四份S8 Fin7的Wq/Wk/Wv/Wo，投影均RNE7到Fin10。
2. 真实gather把split-half旋转对排为E9相邻pair，cos/sin候选S16 Fin14；E9对两个乘积的和/差一次RNE14，再还原head布局。不能将E3的低尺度C直接当作已对齐乘积尺度的FMA补项。
3. QK改为A16/B16、两输入Fin10；保留`11585≈2^15/sqrt(8)`，score到Fin10应RNE25，不是沿用旧S8 QK的RNE19。所有query行score先保存，才复用单M。
4. causal行0只对第一个key统计/Softmax，行1对前两个key；prefix length分别1和2，避免把有限负数冒充负无穷。exact EXP按U16保存/回放，概率Q14；未参与key的PV lane实际置零/按真实K尾约束，不能混入统计。
5. PV为概率Q14×V Fin10，RNE14到Fin10；真实transpose/gather到Wo输入；Wo后与对应原X在共同Fin10相加、报告clip，输出两个S16 hidden字。

该候选仍需新本地控制/布局适配、精确地址分配、独立整数oracle、leaf/helper租约与真实RTL测试；它不是八样本完整A准入。两字输出也不能直接套W5-IF B8单字单fragment样例；跨岛分片另行接收。后续A_gate扩展用G fn1/gated=1，in_x为gate logit、in_gate为Fin10 context；Sigmoid Q14乘context后RNE14输出Fin10。不能按`fn1`一律标输出Q14，也不能把context误当非线性输入。

## 6. 有限样本差异不能被共同底座抹平

| 样本 | A所需额外路径 | F所需额外路径 |
|---|---|---|
| Qwen2.5 | QKV bias；Q16/KV2/D128；GQA×8 | RMS+SiLU门控，I11008 |
| Qwen3 | Q/K逐头RMS128；Q宽2048≠H1024；GQA×2 | 普通RMS+SiLU，I3072 |
| Llama重建 | D64/GQA×4；Llama3位置频率来源 | 普通RMS+SiLU；只保留重建图资格 |
| Gemma local/global | RMS0；Q/K head256；postAttention Norm在残差前；window1024/全局位置规则不同 | GELU_tanh（需独立接收G fn2近似）及postFFN Norm后才加原Y |
| Phi | 融合QKV切分；96/128部分RoPE；LongRoPE系数；GQA×3 | 融合gate_up拆分；epsilon配置1e-5，不能套F16code1 |
| Qwen3.5 global | Q+gate8192切分；RMS0/headNorm；64/256部分RoPE；PV后、Wo前Sigmoid gate | RMS0+SiLU；另24层D不由A/F覆盖 |
| Granite | Attention multiplier0.015625、branch gain0.22；GQA×3 | 实际为X/MoE，不把完整F重复Norm/残差套进每专家 |
| Falcon | H内Attention/SSM共用一次inputNorm并join；普通完整A不是它的独立分支边界 | SiLU前MuP、down后源尺度；epsilon配置1e-5，I6144 |

共同预制能力可按永久profile/参数表选择，role/Fin/layout主要由静态程序证明，不要求每payload携带通用role或大handle。所有有限产品的完整程序、数值/布局证书、容量与供参上限必须在有源底座冻结前接收；“有限样本域”不表示未知模型自动可运行，也不允许各产品另综合控制器来弥补缺功能。

## 7. 实施与接收顺序

先用独立F16整数参考验证signed gamma、epsilon单位、负tie、各级clip和原X残差，随后按固定17拍/39S路径做真实RTL数值与生命周期测试；旧N/F8/A8回归结果分别保留。F16通过只关闭自身有界数值路径。

下一A16候选可与F16并行规格化，不需要等所有真实H的F或物理结果后才开始。先冻结上述完整bounded A的数值、pair/layout和causal有效项，再实施QKV/RoPE/Wo/残差与本地控制。之后分别接收QKnorm、bias、Gemma额外Norm/GELU、Phi部分RoPE、A_gate，保持源图顺序。扩真实H/I时同时完成N长组/存储、单M累计与MEM供参程序；不能把B8互联合同或T一行fit当作这些缺口已解决。

## 8. 独立源码审阅结论与证据边界

已只读审阅本轮`block_w4_f16_top.sv`草稿：17拍映射、gamma475真实ACK、原X466、Norm474→448、E7 shift0、三次A16/0x9885/0x107、M结果保存后clear、G配对与mid padding、单S owner直到adapter rsp、T release后DONE，未发现这份有限合同的阻断性单位/布局/计数矛盾。观察锚点及读取SHA列于机器文件；读取后的源码变化需重新审阅。

这不是外部PR批准，不是RTL执行结果。根报告首轮作业95206在编译时因line125的`5'd16?`词法问题失败，未执行测试；当前字节仅补分隔空格，不能因此预填编译/功能PASS。第二轮95209已提交，实际结果由根按日志/回执补充，本稿不预填。S写ACK错误不代表可回滚已发生写，abort/error只保证声明的协调复位与错误完成前缀；完整hidden尺度/模型误差、真实H/I、MEM、跨岛stored ACK、物理和整模型外围仍待接收。管理结构检查实际PASS，只验证项目管理结构；本稿容量与计数是源码/规格算术核对。
