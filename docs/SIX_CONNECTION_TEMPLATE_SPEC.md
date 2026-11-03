# 六类连接的原生命令与存储模板 v0.5

> v0.5当前主方案：角色/类型/尺度/布局主要由离线编译检查，预制硬件执行必要的原生op、固定接线/有源MUX、拆拼保持和同步。当前三个步骤见[工作报告](STEPS_1_3_WORK_REPORT.md)、[模型绑定](SAMPLE_MODEL_FAMILY_SPEC.md)、[动作降解](SAMPLE_LEGAL_CONNECTION_LEDGER.md)、[静态执行合同](SAMPLE_ONCHIP_SYSTEM_CONTRACT.md)。下文旧通用task/handle/动态标签方案保留为比较与原生阶段参考，不再视为最低必需硬件；不要求每包通用role，也不为每个配方单独造bridge。系统有外存但当前暂不研究；同一M1–M10硬件与M11/M12永久绑定边界保持。

> 2026-11-01 用户边界澄清：**系统有外存，本阶段暂不研究其实现与调度，保留接入灵活性。**本文的片上准入、EXT credit=0/valid=0、无DMA/自动spill仅属于P0片上验证profile，不构成产品永久无外存约束。片上容量缺口只限制P0，不代表完整系统必须全片上驻留。后续地址域、MEM服务和完成语义扩展见[边界与N接口澄清](MEMORY_SCOPE_AND_N_INTERFACE_CLARIFICATION.md)。

> 当前执行前三步的范围已收敛为仓库八样本、保守规模估计与**暂不接入外存的P0片上验证合同**。当前准入见[工作报告](STEPS_1_3_WORK_REPORT.md)、[样本域](SAMPLE_MODEL_FAMILY_SPEC.md)、[角色账本](SAMPLE_LEGAL_CONNECTION_LEDGER.md)及[片上合同](SAMPLE_ONCHIP_SYSTEM_CONTRACT.md)。下文保留总体/历史方案，涉及外存的候选不属于当前阶段，不允许自动spill，也不意味着新增片上容量已经存在。

> 六类模板是回归样例，不限定允许的连接/控制图；覆盖目标为[有限模型家族内全部合法连接](ALL_LEGAL_CONNECTION_SPEC.md)。

本规格基于研究分支faabeda、七宏来源643c6012，配合[总方案](SIX_CONNECTION_SYSTEM_DESIGN.md)、[控制规格](SIX_CONNECTION_CONTROL_SPEC.md)和[逐操作码审计](RTL_NATIVE_CONNECTION_AUDIT.md)。**全部组合流程是待实现候选**；叶宏现有功能、wrapper新逻辑、NUM缺失算术和外存平台分别计价，不把模板描述当作RTL验收。

## 1. 共用原语与边合同

### 1.1 PROJECT_M：一次独立矩阵投影

1. 预留S/外存输入、权重、读出和目的区；将每K8/N8权重排成n-major `8*n+k`，A每row一个128bit容器。loader A每tile保留4或8字，B S8保留4字、S16保留8字，base四字对齐。
2. M_CTRL显式op4配置factor(S16)、left(0..31)，或证明既有scale版本匹配；op6不会恢复scale。S_CTRL提交并行load描述符，首次禁止reuse_b，等待done并take且无错。
3. M op10：index=bank<<5；data=`fmtA | fmtB<<1 | clear<<2 | lastK<<4 | N<<8 | tiles<<12 | rows<<15`。rows/N1..8、tiles1..4、lastK1..8，其他位0。总K超过32则分多个EXEC，首段clear=1，其余clear=0，同一结果上下文锁到最后。
4. 每段等待真实应答并检查故障row mask。EXEC逐行提交，部分行失败时其他行可能已更新，不能盲重试追加命令或声称全命令回滚。
5. op3读两个S64（index=row<<3|pair）；或op5读四S32容器（index=row<<3|half，data=shift|width<<8）。width0/1/2分别S8/S16/S32夹取，shift0..63采用RNE。EXEC应答本身不含投影向量。
6. S16消费者：读两half，各经E13做四S32→四S16低64bit，再拼128bit整字保存；op5已夹S16时E13 shift0。S64消费者须另有已验证宽运算路径。

输出小数位必须从输入/权重/整数factor/left与读出shift推导。M没有浮点缩放和逐channel任意factor；需要不适配该范围的系数时由离线量化或新增数值路径解决。清除、投影切换、专家切换不提供结果context保存/恢复。

### 1.2 NORM_N与SOFTMAX_N：完整组的回放

`BEGIN(op0) → STATS(op1)* → FINALIZE(op2) → NORM_REPLAY(op5)*`，或Softmax再经 `EXP(op3)* → FINISH_EXP(op4) → SOFT_REPLAY(op6)*`。

BEGIN param=0 Softmax、1 RMS、2 L2。Norm epsilon在data低32bit，必须非零；每条数据命令count1..8。N不接收目标总长度，N_CTRL维护每阶段预期总数、原值版本、各包位置/gamma与写确认。允许的全组长度至多65535，不代表向量放得下S。

Norm近似raw公式：RMS的`a=floor((Σx²<<16)/N)+(epsilon_raw<<16)`，L2的`a=(Σx²<<16)+(epsilon_raw<<16)`；`root=floor(sqrt(a))`，`factor=floor(2^38/root)`，`y=sat16(RNE30(x*factor*gamma))`。epsilon以输入raw整数平方为单位，需明确从模型实数epsilon换算；无法表达时不能默默改为1。N不做减均值LayerNorm、beta或自动RMS0。

普通单位gamma_raw=1024按Q10输出。L2→R的Q1.14候选选择gamma_raw=16384，通过原raw公式得到约Q14编码，须独立oracle验证epsilon/舍入误差；不能把普通gamma=1输出裸当Q14。RMS0在外部生成1+weight及对应定点gamma，不是新mode。

Softmax score S16 Q5.10，EXP UQ1.15（raw32768是正1），概率非负S16 Q1.14（0..16384）。保存EXP供回放；不能只留总和。概率总和不保证恰好16384。N无mask口，全mask行或无法证明有限哨兵截零条件时拒绝或增加专用处理。

### 1.3 E/G与容器

E一次8S16，op13特殊为4S32→低64bit4S16；G一次2S16，8lane需4次。E/G没有count，tail有效数外部保留，独占尾字的无效lane填零后整字写S。S无byte mask，部分包先拼整字，共享尾字则新增RMW及仲裁。

E ADD/SUB要同尺度，MUL按shift RNE；FMA op3是`RNE((a*b+c)/2^shift)`，c已经处在乘积raw单位，不能把Q10的c自动当Q20。op8算术右移不RNE，op10才RNE右移但输入仍S16；op12只S16→S8饱和打包且忽略shift，不是任意量化。

G fn0 SiLU、1 Sigmoid、2 GELU_tanh、3 Softplus；in_x是激活输入，in_gate是线性乘数。ungated Sigmoid输出Q1.14，其余ungated Q5.10；gated按gate Q10合同都输出Q10（Sigmoid乘积右移14，其余10）。不同分支不能交换。

## 2. 普通Attention

| 阶段 | 实际原语与交接 | 新控制/数值条件 |
| --- | --- | --- |
| A0 Norm与Q/K/V | NORM_N全H组→PROJECT_M，投影/偏置物化至S/外存 | 偏置用同尺度E ADD；融合QKV需明确Slice布局和长度 |
| A1 可选头Norm与RoPE | 每真实head做NORM_N；E op9相邻pair旋转 | E B_even=cos、B_odd=sin；cos/sin来源及Q格式待提供；前半/后半RoPE先外部重排，非RoPE通道旁路 |
| A2 K/V缓存 | 当前K/V写外存，读合法历史范围，转换M B n-major | 外存与地址生成未在七宏实现，GQA的多个Qhead映射同KVhead由程序指定 |
| A3 QK与缩放/mask | PROJECT_M完成整个D归约；将score量化为Q5.10、物化完整逻辑行 | attention_multiplier来自模型；不默认总是1/sqrt(D)。有限mask按总方案条件处理，至少一个有效key |
| A4 完整行Softmax | SOFTMAX_N统计全有效范围，再EXP/回放 | 任意chunk边界不分裂归约；最后一项可以是新最大值，不能提前出概率 |
| A5 PV与输出 | 概率Q14作M S16 A、V按声明尺度作B，跨整个key范围累加→输出投影→E残差 | 概率不是Q10，PV右移量由实际尺度推导；残差和投影同尺度 |
| A6 发布/释放 | T分批或外存结果根，最后引用释放KV/临时区 | T单批上限，外存版本和消费者可见性另定义 |

本模板不需要R。数值过大、mask不满足、RoPE精度或模型缩放不能由现有M/E表达的产品暂不纳入冻结集合。仅宏类型允许连接不构成算法成立。

## 3. 额外Norm

这是插在主链特定位置的NORM_N实例集合，不是一颗新宏，也不能统一替换为一次全H RMS。

| 样本差异 | 必须保留的语义 |
| --- | --- |
| Qwen3 Q/K头Norm | 按真实D和Q/K head分别归约；Q投影宽度不一定等于H |
| Gemma RMS0与post Norm | 外部1+weight；Q/K、Attention后、FFN后等位置各自独立context/版本 |
| Qwen3.5全局层Q/K RMS0 | 与部分RoPE范围和Q输出门拆分一致，不能把门向量也送QK统计 |
| GDN Q/K L2及输出head Norm | Q/K L2与后续head RMS不同；后者收全128通道后才门乘 |
| Falcon SSM全channel RMS | 门乘后收完整4096通道，不能按R的8lane独立Norm |

每实例产品参数包含mode、完整元素数、epsilon_raw、gamma版本、输入/输出F、位置布局、tail与下游handle。输入统计到最后回放期间不可被覆盖。超S采用真实外存回放；依赖不满足时阻止FINALIZE或下游发射。

## 4. 门控FFN

`PROJECT_M(gate) → E13/保存 → PROJECT_M(up) → E13/保存 → G(activate(gate)*up) → 保存完整mid → PROJECT_M(down全部K) → E残差 → 发布`。

单M不能在down跨K结果活跃时计算下一块gate/up，再恢复旧down；没有这个恢复口。首版完整物化mid后执行down。I11008时mid S16为22016B，gate/up共44032B，均超S16KiB，必须外存或另行设计有成本的宽partial/多M方案。I8192一个S16 mid已满16KiB，不能忽略其他输入、权重和残差。

最小H=I=8例见总方案：S预留400B，S8整数权重、无输入Norm；显式M op4 data1；A16/B8、row1/tile1/K8/N8、clear1的op10 data=`0x9885`；op5 S16/shift0 data=`0x100`、index0/1；E13 shift0两次拼包；G fn0 gated1、x=Gate、gate=Up；down装新权重reuse_b=0。T一字16B保护输出，另计wrapper寄存器。

若用GELU_tanh更换fn2，同时冻结其表近似/饱和质量；非门控分支用ungated但不能随意省掉算法中的乘数。产品图固定并不消除数据配对和背压。

## 5. Qwen3.5 GDN

### 5.1 真实R状态计算合同

mode0：`D=RNE31(H*decay)`，`pred=RNE14(ΣD*k)`，`e=x-pred`，`eb=RNE31(e*beta)`，`H'=D+RNE14(eb*k)`，`y=RNE14(ΣH'*q)`。q/k Q1.14，decay/beta UQ1.31；H/x/y共同S32单位F，不自动Q16.16。R范围错误报error，不饱和继续。

每state tile：op0 OPEN合法length1..256/身份→op1用2×length包恢复旧state→op2/3装key/query→op4两半装8lane x→op5 index0装decay/beta→op6 mode0→op12 index0/1保存8S32候选并等目的写ACK→op7局部COMMIT并等COPY响应→op11用2×length包导出新active并等ACK。op0/6/7的owner/epoch/position位域各不相同，按[完整R操作表](rtl-contracts/R_NATIVE.md)编码；op7 next_position由外层定义，RTL不强制+1。

### 5.2 完整模型采用两遍与外部版本

| 阶段 | 顺序与依赖 | 改动位置 |
| --- | --- | --- |
| D0 投影/版本准备 | 生成卷积输入、z、系数源，保留old_root，预留privateNext/history与输出 | M、外部MEM/版本服务 |
| D1 conv/history pass | 每8lane tile：OPEN→history op9六包、taps op10四包、x op4两包→EXEC mode2→op12保存卷积输出→op7局部history提交→op14六包导出新history | R_CTRL＋存储；纯conv不读未装载的op11 state |
| D2 激活/布局与QK L2 | 收齐所需conv输出→按F量化→G SiLU→Q/K/V切分；每真实Q/K组完整L2，二者16→32头复用，仅Q额外乘1/sqrt128 | E/G/N与回放；不能每8lane各自L2，K不跟随Q缩放 |
| D3 系数 | 生成符合UQ1.31的decay/beta，校验范围 | 显式NUM_COEFF；G仅提供有限非线性子项 |
| D4 state-update pass | 按5.1从old_root逐tile计算、局部提交、导出privateNext，并收全head输出 | R_CTRL/版本服务；单R不能保留所有pending |
| D5 全head后处理 | R输出转N输入单位→跨128通道RMS→G SiLU(z)*normalized_y→输出投影/残差 | **先Norm后门乘**；z在G.x，归一化y在G.gate |
| D6 发布 | 确认所有tile/输出、发布state+history新根和结果 | 根/输出分别确认及失败恢复，非R/T原子 |

本样本Q/K均由16个key头复用至32个value头，只有Q在L2之后额外乘1/sqrt(128)。源ONNX顺序为RepeatHeads后L2；先L2再复用只能作为另证等价的优化，且L2 epsilon尚未从省略payload的图JSON确认。候选用gamma_raw=16384形成L2的Q14，再以E op2、常量c_raw=1448（RNE(2^14/sqrt128)）、shift14给Q做一次Q14乘法；K不乘此系数。系数量化和额外RNE误差须独立oracle与模型质量验收。连续分组布局选择key_head=floor(value_head/2)，Q/K共享同映射；这是待编译合同，精简图只证明RepeatHeads而未展开原始轴序，须在正式图编译时核对或显式重排。不能把未缩放L2的Q直接送R声称匹配样本。

R没有通用exp(-exp(...))、dt/模型系数转换或高精度通用乘除端口。N内部group和EXP不是外部通用数值服务。Sigmoid Q14可明确非负左移17形成UQ1.31编码，但精度仍14bit；衰减与模型常数的复合表达式需独立NUM定义、范围与质量门，不把“32bit重打包”当完成系数算法。

## 6. Falcon SSM及混合层

R mode1：`D=RNE31(H*element_decay)`，`H'=D+RNE14(inject*B)`，`y0=RNE14(ΣH'*C)`，`y=y0+RNE16(x*skip)`。B/C Q1.14、skip Q16.16、逐元素decay UQ1.31；state/x/inject/y共同S32单位F。inject生成不是普通重打包。

| 阶段 | 原生顺序 | 硬件/存储条件 |
| --- | --- | --- |
| S0 双分支准备 | Attention分支按模板2保存；SSM投影Z/XBC/dt及MuP缩放 | 同token/position/版本的join元数据 |
| S1 conv/history pass | 与GDN D1同类流程，逐tile保存输出、局部history提交、只op14导出 | state/decay不必在这个纯conv context装入 |
| S2 激活/递推参数 | 收齐conv结果→SiLU/布局→B/C、x/inject与每state元素decay | NUM_COEFF提供dt/Clip/负EXP/inject及范围；不能由E16位运算自动保证 |
| S3 state-update pass | 每tile新OPEN、op1旧state、op2/3 B/C、op4 index0..3装x/inject、op5 index0合法公共参数、op5 index1/2两个skip半包、op15全部2×length个decay半行→mode1 | param_valid仍要求op5 index0，不能因算术不用公共beta/decay而漏发；所有有效位必须齐全 |
| S4 导出 | op12保存输出→op7局部提交等响应→op11导出新active写privateNext | 此纯state context不无条件op14；mode1启动即消耗decay有效位，下轮重载 |
| S5 后处理 | 收全输出，G.x=Z、G.gate=R输出Q10，SiLU门乘→完整4096channel RMS→输出投影/缩放 | **先门乘后Norm**，与GDN次序相反 |
| S6 汇合发布 | 与保存的Attention分支E合并，再残差，发布版本/结果 | MuP各位置分别定尺度，不能一个统一常数替换 |

单tile融合是另一种受限切片：必须在conv产生pending_history前装旧state/op15；conv输出先保存，外围计算后补参数，state EXEC后共同commit history/state。完整多tile首选上表两遍，不能把融合预载顺序强加给新OPEN的state pass，也不能以融合切片证明全4096通道闭合。

外部history(tile,t→t+1)与state(tile,t→t+1)分别跟踪，同token最终根绑定二者；不能两遍各盲增一次全局position。外部一份state为`4*L*C_state` B，一份history为`12*C_conv` B，old/next各一份，另计卷积/输出/系数staging。R单active8KiB不代表这些都能放进S。

## 7. Granite MoE

`M router → S16 logits表 → N TOP_BEGIN(k8) → TOP_LOAD(每次≤4对，共40) → TOP_SELECT → 保存8个ID → gather所选原score → N Softmax(8项) → rank0..7专家FFN → NUM_WACC → gain/残差 → 发布`。

N只返回ID，不返回score或原记录位置。首版约束唯一ID0..39，保留80B score表和rank对应表，gather按ID读原分数，禁止把ID本身送Softmax。动态专家ID决定权重地址，但专家循环/算子顺序固定。任一rank缺失、重复或尺度/版本不匹配时不发布。

单M完成本expert并物化结果后才切下一expert，不能同时把M结果寄存当跨expert归并区。NUM_WACC候选输入为M op5 S32、所有expert共同Fin；概率N输出Q14且0..16384。8lane S64累加payload64B，加完整rank暂存32B及标签/valid/control；不是总面积只有64B。

每项绝对值≤2^31*2^14，8项总幅度≤2^48，不假定权重和精确1。Granite gain0.22候选为7209/32768，`sum*7209`幅度<2^61，可在S64内精确乘后一次RNE，`shift=29+Fin−Fout`。首版只接受已证明0..63右移；负shift/更宽输入须另证范围与硬件。一次RNE仅指NUM内部，M之前仍可能量化/饱和。输出宽度、饱和策略、共享分支、残差和FP32质量待独立oracle。E普通S16 MUL/ADD不承担此宽归并。

## 8. 八样本对固定程序的最低要求

以下样本差异沿用已核验的[样本图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a103da352b7e431cedc69f54b9f71c05371be1b3/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md)，是编译输入，尚非已验收定点实现。

| 样本 | 不能省略的区别 |
| --- | --- |
| Qwen2.5-3B | QKV偏置、GQA16/2、H2048/I11008的大中间量 |
| Qwen3-0.6B | Q/K头RMS；Q投影宽2048而H1024，不能H/heads推D |
| Llama-3.2-1B | 无Q/K头Norm、D64、GQA32/8；样本为随机参数配置重建 |
| Gemma-3-4B | RMS0及post Norm、GELU_tanh、局部窗口1024/全局位置频率差异 |
| Phi-4-mini | 融合QKV/gate_up后Slice；D128仅96通道RoPE；GQA24/8 |
| Qwen3.5-4B | [GDN,GDN,GDN,GlobalAttention]层序列；全局Q输出门、QK RMS0、部分RoPE64/256；GDN不经过QK Softmax |
| Granite-3.3B | 40选8、每expert I512、Attention系数0.015625和MoE gain0.22 |
| Falcon-H1-3B | Attention/SSM同token汇合、不同MuP位置缩放、K在RoPE前scale、门乘后4096通道RMS |

模型程序必须绑定完整层序列、形状、数值策略、ROM版本、路径与存储计划；目前只有模板和示例，没有完成全部产品编译，不能凭model_id宣称八模型均可执行。

## 9. 最小验收与边界

先做总方案FFN8与Softmax257：分别验证M/S/E/G/T组合和N全组回放。Softmax257需score33字、EXP33字，活动S1056B，T33字528B，末字1元素；S按0..32/64..96布局时保留跨度1552B。T首读有启动等待，之后连续take可每拍一字，反压时保持。

随后覆盖：跨K/多row M混合成功失败、scale跨任务、E FMA单位/CAST、G gated Sigmoid与流水停顿、N早FINALIZE/错回放/全mask拒绝、R pending合法矩阵/局部提交前后可见性/多tile旧根恢复、SSM param_valid和decay消耗、MoE ID/score/rank及宽范围、T非法begin/错写index/未读完释放。独立整数oracle和系统RTL仿真均待执行；静态合同检查只检查声明一致性，不能证明时序、精度、活性或PPA。

R局部commit成功且old_root/输出尚未发布时，可停止并从旧根恢复；一旦新根或输出已部分可见，只能报告partial_completion并进入另定恢复协议。T不提供R联合回滚，外存根原子切换和掉电恢复也不是七宏已有能力。

本轮样本核对还确认Falcon conv包含bias而R卷积无bias端口，必须补偏置数值路径；当前NUM_SERVICE.CONV_BIAS32只是候选，不能无证据换成E16加法或删bias。详见前三步工作报告。
