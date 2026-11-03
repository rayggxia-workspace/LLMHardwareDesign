> 根任务补记：源码a32e5f1a61d137e9e2338b7717b66d5c18085351在服务器95235/node1/c64/8CPU/Verilator5.042实际30CASE通过。下文为独立源码/模型边界审阅，其作者未执行RTL的措辞保留分工；真实运行见A16报告。

# A16独立数值、布局、源码与样本边界审阅

Issue151 / PR152；输入`f665230a392cbcf2422594167e1f163d5e5d1c80`，原生选定源`707878621b2add4ed218b8c43df2e95c9a56e2ba`。已读取本轮冻结`A16_PLAN.md`、新顶层、独立整数参考/向量生成器、旧N/E controller与M/E/N/loader实际源。读取指纹与逐项结论见同名JSON。本审阅未执行RTL编译/仿真、服务器作业、模型推理或物理流程，不是外部PR批准。

当前未发现**所选H8、Sq2、单头、无bias/cache的有限合同**的源级阻断。初稿N命令预计16已纠正为20：RMS两组各4条，Softmax两组各6条。该修正是计数错误纠正，不减少任何phase或错误检查。

## 1. 原生描述符与单位

| 阶段 | 输入/输出单位 | 命令与核对 |
|---|---|---|
| RMS×2 | X、gamma为S16 Fin10，输出S16 Fin10 | N mode1/count8/epsilon_code1；真实src448/452、gamma472、dst480/481，三区互不重叠 |
| Q/K/V、Wo | A16 Fin10×B8 Fin7→S16 Fin10 | rows2、tiles1、K8、N8；EXEC `0x11885`，factor1/left0；op5 data `0x107` |
| RoPE×4 | Q/K Fin10×cos/sin Fin14→Fin10 | E9、shift14、count8；先求两乘积和/差，再一次RNE与S16 clip |
| QK | A16/B16均Fin10，乘factor11585（Fin15）→score Fin10 | EXEC `0x11887`、op5 data `0x119`，右移25；不能照搬旧A8的右移19 |
| Softmax×2 | score S16 Fin10→exact EXP U16→概率S16 Q14 | N mode0/count分别1和2；不能把无效key的零score当有效输入 |
| PV | P Q14×V Fin10→context Fin10 | EXEC `0x11887`、factor1、op5 data `0x10e`，右移14；不能照搬旧A8的右移11 |
| residual×2 | Wo Fin10+各自原X Fin10→S16 Fin10 | E0/shift0；原X448、452与Norm目的分离 |

描述符拆位为rows=2、tiles=1、last_K=8、active_N=8、clear_result=1，bit0为A16；`0x11887`另置bit1为B16。M每组读取index0/1/8/9，分别为row0两half、row1两half；每包四S32载体抽取各自低16，再按lane0..7合为一个S字。两行写ACK后才清理或复用M上下文。

N的epsilon单位为输入码平方：Fin10下code1对应`2^-20=9.5367431640625e-7`；这不是对所有样本epsilon的承诺。gamma Fin10规定该有限输出单位；整数根、factor截断、RNE与各级clip按原生整数合同执行，不冒充FP32等价。

## 2. E9原地RoPE与causal语义

E controller允许srcA=dst：它先分别读入整个128bit A/B，之后才发native E、捕获结果并写dst。count8满足E9的偶数配对约束，系数地址473/474与Q/K地址独立。caller直到最后真实写ACK及service rsp退休前保持唯一普通S owner，故原地写不会覆盖尚未捕获的本次操作数。

E9将相邻lane `(2j,2j+1)`作为一对，B按`[cos_j,sin_j]`排列。它实现`[a0*cos-a1*sin, a1*cos+a0*sin]`，并在完整和/差之后RNE14。A16采用这种pair-interleaved Q/K含义，没有新增从真实模型split-half到相邻pair的自动转换。真实D8 split-half顺序若为`[0,1,2,3,4,5,6,7]`，对应pair排布应为`[0,4,1,5,2,6,3,7]`；实际大D、多头、部分旋转、gamma/投影权重列也须保持一致，不能只替换系数就宣称适配。

两行QK均保存8个score，但Softmax真正只取前1/2项。N controller对原score统计及EXP/概率均用相同count，并把目的尾部实际置零；PV读取的未参与key lane因此是零。它没有以某个有限负数近似负无穷，也没有把未来key加入row0分母。数值参考的future_token_changed向量用于检查row0不受未来token变化影响，不能把这个有限算例扩成任意mask/window支持。

## 3. loader、转置和单M生命周期

所有M A/B基址均四S字对齐且末地址小于1024。rows2/tiles1在原生loader的rows1..8/tiles1..4范围内；A读取一个512bit组并仅退休前两个128bit行容器。QK的A488组还会从RAM读到K490/491，但rows2不会将它们作为A行退休；无需把这两字错误清零。Norm/P/context的另两行容器482/483、518/519、522/523则按合同实际清零。

K的B16矩阵496..503按输出列n-major：col0=旋后K0、col1=旋后K1，其余六列是实际全零。V的B16矩阵504..511按输出通道h存一列：`[V0[h],V1[h],0,0,0,0,0,0]`。S16 B每个8×8 tile需两次512bit half装载，不能将一次窄B装载当完整宽矩阵。

新top实现了有限有源布局逻辑。V0先捕获到v_hold0；V1响应当拍第一列直接使用`v_hold0,h_rsp_data`，避开非阻塞赋值下尚未更新的v_hold1；之后列使用两个稳定holding。每列真实写ACK后才推进索引，最后才开始QK。这个selector、双holding和局部FSM都不是M11金属可补的逻辑。

每个M服务先完成两行结果保存，才进入其它投影/阶段：row0 READ1之后先收该行S写ACK，再发row1 READ2/3；row1保存ACK后才换projection、N或E。Q/K/V原值先全部物化，再完成RoPE；QK所有score物化后才进入两组Softmax。未假设单M能免费恢复被clear的merged S64上下文。

## 4. 精确S布局、容量与事务预算

| S地址 | 内容与最后消费 |
|---|---|
| 448..455 | 原X0在448、原X1在452，六字入口padding实际零；原X保留到各自最终E0读完成 |
| 456..471 | Wq/Wk/Wv/Wo各64B S8 Fin7、n-major/k-minor；对应M完成前不可改 |
| 472、473..474 | gamma S16 Fin10；两个位置的RoPE系数S16 Fin14；输入真实ACK后分别供N/E |
| 480..483 | 两行Norm与两行实际zero，供Q/K/V三个loader |
| 488..493 | Q0/Q1/K0/K1/V0/V1；Q/K先普通投影写、再由E原地更新，V保持原投影值 |
| 496..503 | K的宽B staging，先2复制后6全零；QK loader完成前保留 |
| 504..511 | V的8列宽B staging；PV loader完成前保留 |
| 512..517 | 两行score、两行exact EXP、两行P；每组统计/回放/最终写ACK依序完成 |
| 518..519、520..523 | P padding；两行context与其padding，供PV/Wo loader |
| 524..525 | Wo两行结果，供对应residual E0读取 |
| 528..529 | 两行final；真实读S后进入T，输出消费和release后才DONE |

输入27拍/432B=336B有效（X32、四权重256、gamma16、系数32）+96B实际零padding。地址包络448..529共82字/1312B，实际触及69字/1104B；475..479、484..487、494..495、526..527共13字孔洞不因此获得并发共享许可。T另预约2字/32B，按完整包络保守预约共1344B。这里没有计入native S/T整宏容量、所有hold/控制寄存器或PPA，亦未证明最小面积。

| 正常成功阶段 | 普通S读 | 普通S写 |
|---|---:|---:|
| 入口 | 0 | 27 |
| 三种A容器共6字padding初始化 | 0 | 6 |
| 两组RMS | 6 | 2 |
| Q/K/V六行结果保存 | 0 | 6 |
| 四次RoPE | 8 | 4 |
| K staging复制/清零 | 2 | 8 |
| V staging transpose | 2 | 8 |
| QK两行保存 | 0 | 2 |
| 两组Softmax | 6 | 4 |
| PV两行保存 | 0 | 2 |
| Wo两行保存 | 0 | 2 |
| 两次residual | 4 | 2 |
| final两行回读 | 2 | 0 |
| **总计** | **30** | **73** |

普通S共103请求/ACK；loader快速路径另外是14次512bit读、12个A行beat、8个B half/窄beat。六组M共42cmd/rsp，N四服务共20cmd/rsp，E六服务，G/R无实例。错误、reset、abort只核对已发生前缀，不能强套正常总数或宣称全局回滚。

T按BEGIN2→WRITE0(final0)→WRITE1(held final1)→COMMIT→两字DRAIN→RELEASE。两个final S响应分别有独立保持位置，WRITE0背压不会丢掉final1；last在index1。native T消费不是目的stored ACK，本核没有实现跨岛所有权转移。

## 5. 独立oracle审阅

已读`a16_integer_reference.py`及生成器，预期来自signed整数dot、数学重建EXP表、RNE与clip，不消费DUT输出。RMS raw公式、相邻pair RoPE一次舍入、QK25/PV14、prefix count1/2、原X residual、每地址S写历史均与所选合同相符。向量包括真实系数causal基线、未来token变化、zero-gamma精确残差、signed/nonunity gamma、零输入、正负极值、quarter-turn布局与两组固定种子数据。

每地址S_write_history记录该地址被写入的值，不是全局周期时间表；纯Python预期、1025节点EXP一致性和本次源码阅读都不能替代真实RTL握手/错误/恢复测试。此处未由审阅者重跑生成器或仿真；实际执行结果须由根按作业/退出码/日志/源SHA补充。读取后有源码变化须重新审阅。

## 6. 八样本仍需的真实差异

| 样本 | 与本A16的差异/待接收内容 |
|---|---|
| Qwen2.5 | H2048、Q16/KV2、D128；QKV bias、GQA×8、模型位置系数、长组/长context和供参 |
| Qwen3 | H1024但Q宽2048；Q/K逐头RMS128、GQA×2、head布局与真实参数 |
| Llama重建 | H2048/D64/GQA×4、Llama3频率规则；仍是配置重建/随机参数来源边界 |
| Gemma local/global | H2560/D256、RMS0/headNorm、postAttention Norm在残差前、局部window1024与全局不同位置规则；F还需GELU/postNorm |
| Phi | H3072/D128、融合QKV切分、96维部分RoPE/LongRoPE、GQA×3；配置epsilon1e-5不能套本code1 |
| Qwen3.5 global | Q4096、combined Q/gate8192、RMS0/QK Norm、64/256部分RoPE、PV后Wo前Sigmoid gate；另24层D不由本A覆盖 |
| Granite | H1536/D64/GQA×3、attention multiplier0.015625、branch gain0.22；后续为X而非普通完整F |
| Falcon | H混合mixer内的Attention分支与SSM共享inputNorm并join；不能直接套带独立Norm/residual的普通完整A；配置epsilon1e-5 |

真实hidden最大H3072，在S16单token纯payload下为6144B恰等T6KiB，但Sq2已12288B。N现controller count≤257/6bit word计数，H3072需384字，三相离Norm数组18432B>S16KiB；真实prefill、Q/K多头及KV cache须另做程序/存储/供参。source max_position不是已接受context上限。模型split-half、partial RoPE、cos/sin生成/位置、mask/window、GQA和KV版本都未因本小核而获得资格。

有限产品的完整程序、numeric/layout/容量与供参证书应在共同有源底座冻结前接收；role/Fin主要为静态契约，不要求每payload新增通用role或大handle。当前结论不扩大为未知模型、M11/M12实现、一般控制网、MEM、整模型外围或物理验收。
