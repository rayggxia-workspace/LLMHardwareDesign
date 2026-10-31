# 合法连接的原生角色与适配profile目录 v0.4

> 当前执行前三步的范围已收敛为仓库八样本、保守规模估计与**无外存片上合同**。当前准入见[工作报告](STEPS_1_3_WORK_REPORT.md)、[样本域](SAMPLE_MODEL_FAMILY_SPEC.md)、[角色账本](SAMPLE_LEGAL_CONNECTION_LEDGER.md)及[片上合同](SAMPLE_ONCHIP_SYSTEM_CONTRACT.md)。下文保留总体/历史方案，涉及外存的候选不属于当前阶段，不允许自动spill，也不意味着新增片上容量已经存在。

任务Issue151，待评审候选。范围为[全合法连接规格](ALL_LEGAL_CONNECTION_SPEC.md)定义的有限家族域；六算法只作回归。本附录沿用36f9c9db/643c6012原生RTL，新增profile全部待实现/验证；当前事实见[原生审计](RTL_NATIVE_CONNECTION_AUDIT.md)。角色清单与适配公式不构成已完成系统硬件。

## 2. 端点目录：先分角色，再谈宏类别

`M/N/E/G/R/S/T` 不是足够精细的端点标识。profile至少使用 `macro.port.operation.role`。命令响应必须先按已接受op分类，不能把所有128bit响应都当张量。

### 2.1 全部原生数据源profile

| 源profile | 真实载荷与有效数 | 必须保留的语义 |
|---|---|---|
| M.RESULT64 | op3每包两个S64，行0..7/pair0..3 | 完整结果单位F、列顺序、结果上下文版本；读取不消费结果 |
| M.QUANT32 | op5每包四个S32容器；逻辑值可能已夹到S8/S16/S32 | logical_width与carrier_width分开；读出shift/舍入位置及sat；不能裸当八S16 |
| M.PARTIAL40 | op12两个S40，各符号扩展为S64 | 有限诊断partial槽/owner/valid；不是完整结果，也不是可任意恢复的上下文 |
| N.NORM16 | op5低count个S16，count1..8 | RMS/L2、gamma/epsilon及声明Fout，完整向量位置 |
| N.EXP16U | op3低count个U16 UQ1.15，范围0..32768 | 原分数/maximum版本；raw32768为正1；不是最终概率 |
| N.PROB16 | op6低count个非负S16 Q1.14，范围0..16384 | 完整Softmax的概率角色；不假设量化后和精确为16384 |
| N.STATS_REC | op7整128bit记录 | bits15:0 count U16，31:16 max S16，47:32 min S16，79:48 sum S32，127:80 sumsq U48；是混合记录，不是同质八S16 |
| N.TOP_ID | op10低k个U16 ID，k1..8，其余零 | ID列表，按score降序/同分ID升序；无score、无原记录索引；ID可以重复，原生未限制专家范围 |
| N.FACTOR32U | op11低32bit U32 factor，其余零 | 本次Norm/Softmax因子的raw定义与上下文；可读出，但不是通用除法服务 |
| E.VEC16 | op0..11每包八S16 | op8非RNE、op10 RNE；FMA C为乘积单位；RoPE为相邻pair；op不同角色不能混同 |
| E.PACK8 | op12低64bit八S8，高64零 | 有效8元素；shift被忽略；不能按四S16 profile解析 |
| E.CAST16 | op13低64bit四S16，高64零 | 有效4元素；来自四S32的RNE/夹取，调用方保留尾部有效数 |
| G.ACT16 | gated=0时每包两S16 | fn1为Q1.14，其余fn0/2/3为Q5.10；尾部count在外部 |
| G.GATED16 | gated=1时每包两S16 | 在声明gate Q5.10下所有fn输出Q5.10；激活支为x，线性支为gate |
| R.OUTPUT32 | op12每包四S32，index0/1，共八值 | 最后成功EXEC的候选输出，单位F；COMMIT会清output_valid，先保存 |
| R.STATE32 | op11每包四S32，index0..2L−1 | active状态；pending时仍旧active，局部COMMIT后才新active；不是shadow导出 |
| R.HISTORY32 | op14每包四S32，index0..5 | active history，单位F；pending时旧history，提交后新history |
| R.META_REC | op13整128bit记录 | length U9、三pending/output位、保留位、owner/epoch/position U32；必须按字段解析 |
| S.READ128 | 普通读响应128bit | 存储本身不携带类型/有效位；须由handle绑定原写入profile、版本和有效数 |
| S.WRITE_ECHO128 | 普通写应答回显刚写的din128 | 是写确认；如显式选择ACK-forward，可转发已知同版本payload，但不得将任意ACK自动当新结果 |
| S.LOADER_A128 | 每次八S8/S16；S8只低64，带bank/row/tile/wide | 不是无元数据通用stream；整个loader事务必须完成所有A/B义务；通用导出模式见全合法规格的1024B整事务spool/预制选路 |
| S.LOADER_B512 | 每次64S8或32S16，带bank/tile/wide/half | S16两half；n-major；可经新增拆包路由，不能假设外部另有wide读地址口 |
| T.READ128 | commit后的顺序128bit读出，含index/last | 类型/有效数在外层租约handle；last是字末尾，不是元素数；最后take后还需release |

**状态/ACK另列控制profile**：M EXEC故障row mask/scale/clear ACK、N BEGIN/STATS/FINALIZE/FINISH等ACK、R装载/EXEC/COMMIT/REVOKE ACK、S loader done/error、E/G error/sat、T状态/protocol_error。它们默认只进入控制/诊断通路。若算法显式要把某个状态字段作为数据，必须走字段提取和角色绑定，不能靠响应总线宽度相同自动传播。

### 2.2 全部原生数据目的profile

| 目的profile | 原生形状/角色 | 约束 |
|---|---|---|
| M.A8 / M.A16 | A128装八S8/八S16；S8高64填零 | bank/row/tile/wide；最多8row×4tile；A各row独立容器 |
| M.B8 / M.B16 | B512，64S8一次或32S16两half | `8*n+k` n-major；S16 half0先于half1；fmt与EXEC一致 |
| M.SCALE | op4低16bit有符号factor，接着5bit left | 属受控参数端点；index0/保留位0；不是张量直接驱动命令总线 |
| N.STATS_X | op1低count个S16 | mode0分数Q5.10；mode1/2按输入F与epsilon平方单位；未FINALIZE |
| N.EXP_X | op3低count个S16 Q5.10原分数 | 已锁定max的同组原值回放，不能替换为另一个同形状向量 |
| N.NORM_X_GAMMA | op5 data=x、aux=gamma，各低count S16 | 两独立源配对；gamma声明Q5.10，特殊输出编码须明确参数方案；factor合法 |
| N.SOFT_EXP | op6低count个U16 UQ1.15 | 每值≤32768，同一EXP版本；factor/count阶段合法 |
| N.TOP_RECORDS | op9每包1..4条(score S16,ID U16)记录 | 两字段对齐，累计≤40，k≤装载数；score共同单位 |
| N.EPSILON | BEGIN mode1/2的data低32bit正U32 | epsilon为输入raw平方单位；mode/总长度由N_CTRL拥有 |
| E.A16 / E.B16 / E.C16 | 正常各八S16 | op决定所需字段；FMA的C按乘积单位，SELECT C为条件，RoPE B为cos/sin配对 |
| E.A32 | op13 A128中四S32 | B/C无数学作用；shift0..31，低64结果需另profile拼包 |
| G.X16 / G.GATE16 | 各两S16，x Q5.10，gate声明Q5.10 | gated=0不需要一条真实gate数据依赖，可填0；gated=1须显式join |
| R.STATE32_IN | op1每包四S32，2L包 | 立即装active，不是候选；无任何pending，state单位F一致 |
| R.KEY16 / R.QUERY16 | op2/3每包八S16 Q1.14 | index0..31；也分别用于SSM B/C；仅前L元素被计算 |
| R.X32 / R.INJECT32 | op4四S32，x两包、inject两包 | 共同S32单位F；inject是算法算术结果，不只是更宽容器 |
| R.COMMON_COEFF | op5 index0的两个U32：decay低32、beta次32 | UQ1.31且每值≤0x80000000，高64必须0；param_valid必需 |
| R.SKIP32 | op5 index1/2，各四S32 Q16.16 | 只有skip固定Q16.16；不能推及全部R S32 |
| R.HISTORY32_IN | op9四S32，共六包 | 无任何pending，history单位F一致 |
| R.TAPS16 | op10八S16 Q1.14，共四包 | 无任何pending；4×8lane卷积tap布局 |
| R.ELEMENT_DECAY | op15四U32 UQ1.31，2L包 | 每值≤0x80000000，无任何pending；占用inactive/shadow并建立有效位 |
| S.WRITE128 | 普通128bit整字写 | 无byte mask；独占尾字补0整写，或新增RMW；正确取得写ACK |
| T.WRITE128 | FILL状态按index从0顺序写128bit | BEGIN1..384字；写满才SEALED；commit后不能继续写 |

命令描述符、owner/epoch/position、地址、op/shift/count、T begin/commit/release、S load描述符也都是有限控制端点。它们应由唯一局部控制器从受检查描述符构造；动态参数若来源于其他宏，应走显式 `PARAM_BIND`，校验范围/保留位/任务身份后再发令。合法连接不等于让任意payload重解释成完整cmd_data并劫持所有控制字段。

## 3. 完整有限profile集合：不再依赖“相同128bit”

每个profile应有唯一ID、版本、输入/输出角色集合、准确bit映射、有效数、数值公式、异常策略、状态机、资源/容量预算和验证证据。下表是需要实现的完整候选族，不是可省略的“以后再说”。一个族可以有有限参数实例。

为使“全部recipe”具有有限分母，采用规范形式：`EXPORT → [FIELD/ID语义解析] → [一次直接NUM_CAST] → [一次已合成LAYOUT_MAP] → BITPACK → 有界存储/拓扑交接 → IMPORT`。不同字段可各有一条数值转换支路，再组装记录。布局映射应合成而非任意叠加空转；同一条语义边不允许为了增加recipe数量无限串联cast/pack。若算法有意多次量化或反馈，这些是FamilySpec中的显式算子/版本边，分别验收，不能当作透明适配。实际存储route与快速路径也来自有限登记表，均需覆盖，不生成无限绕路。

| ID | profile族 | 作用与必要变体 |
|---|---|---|
| P01 EXPORT_SELECT | 原生响应选路/分类 | 全部M/N/E/G/R源profile、S读/写回显/loader输出、T读；按已接受命令识别数据或ACK，错误结果不作有效数据 |
| P02 NUM_CAST | 同质数值转换 | S8/S16/S32/S64、U16/U32/U64；字段S40/U48先精确扩到S64/U64；逐元素处理有无符号、F变化、RNE、SAT或REJECT，包含完整S64转换 |
| P03 BITPACK | lane/载体变换 | 2/4/8/32/64元素组、32/64/128/512bit载体；E12低64八S8、E13低64四S16、M op5四S32 logical8/16/32分别列子profile；补零/拆拼不改变数值 |
| P04 LAYOUT_MAP | 有界布局/地址生成 | contiguous、M_A、M_B n-major、RoPE相邻/半区、state行/半行、history/tap；AFFINE/TRANSPOSE/SLICE/REPEAT/GATHER/SCATTER_UNIQUE参数化；重复写散加不在本族 |
| P05 RECORD_FIELDS | 混合记录 | N.STATS、N.TOP_RECORDS、R.META、R.COMMON_COEFF等按schema提取/组装；支持字段符号扩展、顺序和保留位检查；不能整体numeric-cast |
| P06 ID_RESOLVE | ID/索引语义 | TopK ID保存、索引边界、gather score/weight地址、rank映射；唯一/重复ID策略由目标操作指定；不能把ID默认当logit |
| P07 STORE_FORWARD | S/外存物化与回放 | 有类型handle、版本、地址/范围、只读引用、写确认、重放；包含显式S写ACK-forward，省掉重复读但仍等待存储可见 |
| P08 TX_TRANSFER | T租约 | BEGIN/FILL/SEALED/COMMIT/DRAIN/RELEASE、tail外包；>384字分批与全tensor发布策略；T→T同实例必须先spool后重开 |
| P09 FORK | 有界多消费者 | 捕获payload＋pending消费者mask，各消费者恰好接收一次，最后一方完成才释放；支持独立背压、错误和取消 |
| P10 JOIN | 有界多生产者 | 每输入独立保持槽，按task/epoch/range/type/version匹配；E A/B/C、G x/gate、N x/gamma、TopK score/ID记录、R各角色就绪屏障 |
| P11 REENTER | 同资源串行复用/反馈 | 同一lease的RESUME按原生阶段guard续作，可保持N组或R pending_history；新context的REENTER才需保存旧输出并释放/提交/撤销；图环有初始token和显式版本延迟，不暗示M有结果恢复口 |
| P12 PARAM_BIND | 数据导出的受控参数 | 标量/字段先转换与值域验证，再写M factor、N epsilon、R系数或受限地址/索引描述符；控制端口唯一owner，禁止无验证cmd透传 |
| P13 FORMAT_SEMANTICS | 显式语义转换 | numeric field extraction、ID_AS_INT等；ID作为算术整数时显式设F=0，再做数值转换，而不是隐式伪装成score/概率；opaque→typed必须有原写入/初始化schema |
| P14 ERROR_DRAIN | 故障/取消/复位 | 原生命令error、sat策略、T粘性错误、已呈现valid保持、排空、旧epoch丢弃；不可把已提交写入宣称回滚 |
| P15 RESOURCE_CREDIT | 有界流量/所有权 | 任务/包/响应slot credit、S仲裁/loader完成、R/N/M上下文、T单租约、容量及无死锁；不允许无限FIFO或隐藏外存 |

新增算术服务另有独立profile目录，例如NUM_COEFF、NUM_WACC、散加、超S64运算。连接可以**依赖**这些已声明算术任务，但P02/P04不能假装包含它们。举例：G Sigmoid→R beta的编码转换属于P02/P03；Softplus→任意decay还要负指数等计算，属于算术链，不能只用P02命名盖过。

### 3.1 P02必须真正覆盖S64，而非以E13替代

规定每个同质数值为 `real=raw×2^(-F)`，转换的精确参考是：

`rounded = RNE_even(raw_in × 2^(Fout−Fin))`，随后按目标signedness/width执行 **SAT**（夹取并置sat）或 **REJECT**（拒绝发布并报转换错误）。

约束和实现义务：

1. 类型集合是有限的：S8/S16/S32/S64/U16/U32/U64。原生S40 partial、U48 sumsq等字段先精确扩展到对应64bit类型，F不变。不能将两个S64重解释为四S32；不能只取低位或先夹S32再声称保持了S64范围。
2. `F`是编译期登记尺度标签，不是已有叶宏端口。产品程序使用有限尺度表；不用人为假造叶宏只允许某个F区间。转换硬件可按下述有限delta类别支持任意已登记Fin/Fout，避免巨大左移器。
3. delta=Fin−Fout。delta=0精确扩宽/缩窄；delta=1..63做有符号一致的RNE右移；delta=64单独处理边界；delta>64对宽度≤64的所有输入RNE为0。特别是U64在右移64时可能舍入到1，而S64的INT64_MIN右移64是−0.5、ties-to-even为0，不能拿有符号算术移位近似。
4. delta<0为左移。移位1..63须先按目标上下界检查，再精确移位；移位≥64时任何非零输入均不可能落入上述≤64bit目标类型，按SAT或REJECT处理，零仍为零。因此无需制造S192中间寄存器。编译器将大delta折叠为有限“large-right/large-left”变体。
5. S64 INT64_MIN的幅度不能在S64内直接abs；参考/硬件必须保留额外符号/幅度位或等价安全算法。U64→S64、U32系数→S32等转换先按数学整数判断范围，不能重解释符号位。负数→无符号也必须按策略检查。
6. E13仅能实现P02的一个子集：四S32→S16、非负右移0..31、SAT、低64结果。E op10仅S16→S16；M op5只转换本M当前结果，不能给其他源充当通用宽转换器。全部合法目标要求新增完整宽转换路径；不能用“可改走M op5”排除N U48/R记录等其他宽源。
7. 数值乘任意gain、随机舍入、零点/非对称量化不是此公式的隐含能力；若要允许，应单列新的有限profile。对S64输入再乘任意S16 gain会需要精确S80中间值，不能沿用“已有S64累加器足够”的证明。

**例子**：M.RESULT64中raw=`2^40`、Fin=40，要得到S16 Q10，应一次RNE右移30得到1024。E13不能接原始S64；先截S32会变成0。N.STATS.sum_sq字段要作为数值使用，则先P05取U48、零扩U64，绑定F=2Fin，再P02转目标；不能读整128bit记录后当向量乘。

### 3.2 不能遗漏的N与E/G profile变体

- N.NORM16、N.PROB16、N.EXP16U是三个源类型，不能只记一个“N128”。EXP raw32768直接按S16传到E/M会变负数；但**EXP经U16/Q15→S16/Q14的显式数值转换后，作为未归一化指数权重参与另一个合法算术任务**可以允许。禁止的是把它隐称为Softmax概率，不是永久禁止N.EXP与M之间存在合法路径。
- N.STATS五字段分别可存储、诊断或经显式字段/数值绑定参与算术；N.FACTOR32U也可按其真实公式供明确的系数用途。没有“某源是统计结果，所以任何数据连接都不允许”的宏级黑名单。
- N.TOP_ID默认是索引；MoE需P06按ID gather原score。若另一算法明确把ID作为整数特征，则允许P13 ID_AS_INT（F=0）后接P02，而不是借裸bitcast绕过语义。重复ID在原生TopK中合法，但对要求唯一地址写入的scatter必须先检查/定义冲突策略。
- N.TOP_RECORDS目的需要score/ID zip；即使两字段分别来自不同宏，也要经过P10/P05形成每32bit记录。N统计/gamma/EXP输入的相同128bit形状，不能省略真实阶段和版本绑定。
- E.PACK8有8个S8，E.CAST16有4个S16，均只有低64bit有载荷。M.QUANT32逻辑值为S8时仍有四个S32。三者必须是不同BITPACK profile，不能共享“低半包四元素”的固定解释。
- G.ACT16 fn1是Q14；其余ACT16和声明Q10 gate下的全部G.GATED16是Q10。gated标志必须进入输出类型解析。G两lane尾数、E普通八lane尾数及E13四lane尾数都在外部记录，任何无效lane都不应被算成真实元素。
