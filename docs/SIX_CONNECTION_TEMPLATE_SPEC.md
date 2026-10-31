# 六类连接与控制总方案：阶段、类型、资源及最小验证实例

研究任务：[Issue #151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)，延续[PR #152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)。本文是详细设计候选，不是新增RTL或新仿真结果。配套[总方案](SIX_CONNECTION_SYSTEM_DESIGN.md)与[控制规格](SIX_CONNECTION_CONTROL_SPEC.md)；本轮未修改叶宏或运行服务器/仿真。

## 0. 来源、状态与边界

| 项目 | 固定来源/状态 |
|---|---|
| 已有六类研究 | `49a34e75657025244fd33af56111029868008db8`，Issue151/PR152的方案、bridge审计和协调候选 |
| 样本算法 | main `a103da352b7e431cedc69f54b9f71c05371be1b3`，八模型、十种代表层；文本图不是可执行IR |
| 七宏协议参考 | PR144旧合同 `5e787714362d957b79c2997141cf05eeebb85afc`；本表按该接口编写，仍为未合并实施参考 |
| PR144新增公开头 | `aacac9238f2eb3d8f0e251bda5affab0423b1a5e`；本轮已核对：叶宏RTL/接口未改；R仍未取得完整最终资格；详见总方案来源与system-source-index.json |
| SystemC参考 | `4ad1ad4643d08cabf2fcc35e9465424556b1f325`；无时钟事务模型，E尚未覆盖RTL op13；枚举13是Reset |
| 本稿验证 | 未执行RTL/SystemC、模型重跑、综合、布局布线或物理互联实验 |

术语标记：**已实现**只指固定来源已有的局部叶宏或明确旧组合；**新增候选**指要实现的wrapper、存储访问、控制与接口；**数值缺口**指现有七宏尚未形成对应算法的精确/定点闭包。旧专用 `attention106/m106/norm106/r106/gdn109` 可参考访问、状态和整数算法，不能直接视为七宏整链或转移其资格。

原八模型图主要验证FP32、B=1/S=2、use_cache=False；Llama采用配置重建/随机参数。decode历史缓存、全部长度/模型范围、整模型定点质量与系统吞吐均不能从该图或本稿推出。embedding、位置/掩码生成、末尾Norm、LM head和采样不在代表层导出边界。

## 1. 总体分工：固定执行结构，运行时握手与参数化循环

每个定制产品可以固定执行图、操作模板、矩阵维度、激活类型、Norm范围、分块规则和合法线路；运行时仍有输入/历史长度、prefill/decode入口、MoE ID、R状态、数据值、访存/背压和错误。首版不需要任意DAG的在线重规划，但不能用预估拍数替代真实完成确认。

候选分工如下。所有外部子控均为**新增候选**；叶宏原有FSM并未因表中角色名称而自动扩充。

| 子控/资源 | 唯一职责与发令权 | 约束 |
|---|---|---|
| 全局产品序列器 | 固定模板调用、layer/token/head/tile循环、资源租约、跨阶段数据版本、join、提交次序与故障停止 | Attention/FFN是子程序；共享M/S不能同时归两个算法子控直接操作 |
| M执行子控 | 请求S loader、管理A/B银行/身份、配置尺度、执行、失败行掩码、读出及结果物化 | 一条追加链占用M完整结果上下文，不能被另一计算阶段覆盖 |
| N向量子控 | 单向量BEGIN/STATS/FINALIZE/EXP/REPLAY及全组计数 | cmd_ready不等于可切换整向量；未完成上下文不交给别的Norm |
| E/G流适配子控 | E命令、G两输入join、4/8/2元素包装、尾包、在途顺序、错误/饱和传播 | G标签由外层保存；现有RTL没有通用task_id端口 |
| R事务子控 | OPEN、state/history/系数载入、卷积/递推、候选输出读出、commit/revoke | 不能混淆候选、活动状态及已发布结果；控制者必须处理pending_history |
| S访问/供数管理 | 普通128bit请求/响应归属、地址和生命周期、与内部宽loader的时段协调 | S仍只有真实四bank；宽读优先、窄口没有无限带宽或无饥饿保证 |
| T批次子控 | 预留、BEGIN、连续WRITE、COMMIT、TAKE、RELEASE | 单批1..384字；未释放不能把它当另一份6KiB缓冲 |

共用事件是系统候选，不是叶宏现成引脚：`cmd_accept`、`compute_done`、`data_ready`、`publish_done`、`release_done`。S写响应排空、目标数据可见后才发`data_ready`；T的写入以write握手计数，最后一字自动SEALED；R/T的COMMIT语义分别跟踪。跨宏原子发布、掉电恢复和透明重试仍须额外协议。

同一底座的主候选为相同预制顺序器/固定ROM，M11/M12永久选择已预编译产品入口；备选为预制可写控制存储在冷启动一次装载并锁定。两者均不要求运行期间换图；固定ROM的完整程序和容量必须在底座冻结前接收。每模型重新综合不同FSM会改变有源底座。

## 2. 类型化连接族

每条逻辑边应绑定：源实例/端口/操作阶段、目的实例/端口/阶段、tensor/token/head/tile/version、元素位宽/符号/共同尺度、布局/步长/顺序、有效元素数与容器包装、源/目标槽、实际物理路径、就绪/发布/释放条件。当前标签主要由wrapper持有，不默认存在于原生总线。

| 连接族 | 来源→目标与原生容器 | 可复用内容 | 新增候选/强制检查 |
|---|---|---|---|
| L1 矩阵供数 | S内部宽读→M.A128、M.B512 | S内loader及A/B独立握手已实现 | 记录bank、row、tile、S8/S16；B按n-major且S16 half0先于half1；reuse_b须核对权重身份 |
| L2 矩阵结果 | M.op3/op5响应→S/T或转换入口 | op3读2×S64；op5读4×S32容器已实现 | EXEC响应只含状态/失败掩码；不可当结果。对op5的有效4元素重排；选择一次明确的数值舍入位置 |
| L3 基础向量 | S/保持槽→E.A/B/C128→S/T | 八S16算术、RoPE和op13已实现 | FMA单位、三输入配对；op13是四S32→低64位四S16，不能消费高64填零为四个真实元素 |
| L4 激活门乘 | S/保持槽→G.x32/G.gate32→S/T | 两S16、四级可背压流水已实现 | x与gate角色、函数/门乘码随包保持；8元素需四个两元素包，输出需分/拼包 |
| L5 统计/回放 | S→N.data128/aux128→S/T | Softmax、RMS/L2、TopK已实现 | STATS全组屏障，原值/EXP/gamma的地址与生命周期；EXP UQ1.15、概率S16 Q1.14、Norm输出需分别标识 |
| L6 递推载入 | S/明确系数服务→R.cmd_data128 | state/x/inject为4×S32；Q/K/taps为8×S16 | 每种op的index与编码不同；UQ1.31 decay/beta不能用任意S16码替代 |
| L7 递推读出 | R.op12响应→S→E/N/G | 4×S32候选读出已实现 | 在COMMIT前读并保存；R输出共同单位必须声明。E op13可缩窄，不能恢复已丢失精度 |
| L8 路由元数据 | N.TopK ID→score gather/专家地址→N/M | 40选8只返回ID | 唯一0..39 ID约束、原score保存、selected-logit gather、专家权重访问和rank匹配均须实现 |
| L9 旁路/fork/join | 原张量/多分支→有限保存区→消费者 | 叶宏各有局部保持资源 | 生命周期、消费者确认、同token/tile/version汇合；一条read_take不能直接分给可独立暂停的多个消费者 |
| L10 发布与回读 | 结果→T→S/外部输出 | T单批提交/消费已实现；旧M→T/T→S有特定实验 | 新任务标签、任意基址、S写响应排空、一般错误处理和新版负载不能复用旧桥结论 |
| L11 系数/宽归并 | 显式数值服务↔R/MoE结果区 | 有旧专用消费者可参考 | 数值缺口：通用负EXP、S32 inject、UQ1.31系数、S32/S64加权归并；不能隐藏为免费协议桥 |

算法图不要求所有连接族都成为每对宏的专用直连。首版可经明确的S/外存路径物化后回放；热路径旁路须按收益与实际RC单独选择。S中转的访问网络、MUX、地址发生器、响应槽和寄存均为预制有源资源，也不是现成的无限互联。

纯M11/M12只能连接已有合法端点；不能新增分/拼包、FIFO、仲裁、计算、事件表或时钟资源。S无byte mask：部分字有效数据要先拼成128bit，或整字padding并计实际容量/流量；不能默认字节写。

## 3. 六类模板的具体阶段

### 3.1 常规注意力：M/E/N多遍计算与KV保留

| 阶段 | 输入→输出/存储 | 负责子控 | 等待事件与提交/释放 |
|---|---|---|---|
| A0 输入及投影准备 | 隐藏X、gamma、QKV权重→Norm输入区/权重窗口；保留X残差 | 全局、S、N | X/gamma版本有效，S范围已预留；N全组统计和回放完成后发布Norm数据 |
| A1 Q/K/V投影 | Norm(X)→M→Qraw/Kraw/V区 | M、S | loader交付≠M完成；分别等EXEC结果检查、op5读出和目标写确认。Q/K/V保存后才可覆盖M结果上下文 |
| A2 位置/布局 | Q/K→额外Norm（若需要）→RoPE、偏置等；V保留 | N、E/G流适配、S | 取得cos/sin、mask和头布局；Q/K/V位置、head、scale匹配后可发布Q/K。局部配对RoPE不等于任意Transpose |
| A3 QK | Q与对应K历史窗口→M跨K归约→缩放/mask→分数区 | M、E、S | 完成整个head K归约才产生最终分数；保存/写确认后进入Softmax。不得各K片独立归一化 |
| A4 Softmax | 分数→N统计→EXP区→N归一化→概率区 | N、S、T（可选） | max全组FINALIZE、EXP总数达标、FINISH_EXP、全部SOFT_REPLAY完成；不能把单子命令done当全组完成 |
| A5 PV/输出投影 | 概率Q1.14＋V→M(PV)→物化上下文→M(Wo) | M、S | P/V布局和单位匹配；PV完整输出先保存再复用同M做Wo。概率值兼容S16不表示已拥有A/B装载元信息 |
| A6 残差与发布 | Wo输出＋原X→E→T或结果区 | E、T、全局 | 同token join，全部结果写齐再发布；最后消费者确认后释放X、Q/K/V临时区及T租约 |

**已实现**：M计算、N Softmax、E局部算术/转换、S loader、T局部协议。**新增候选**：完整KV访问、布局与阶段控制、typed版本、通用回放/存储访问。**数值缺口/待验证**：QK缩放/有限mask码、FP32→当前S16的质量和缓存完整性。原有decode章节只有语义，不能声称历史KV路径已完成模型验证。

### 3.2 额外Norm：Q/K头内与输出后置范围

| 阶段 | 输入→输出/存储 | 负责子控 | 等待事件与提交/释放 |
|---|---|---|---|
| N0 绑定范围 | 固定head/H范围、RMS/RMS0/L2模式、epsilon、gamma→向量描述 | 全局、N | 区分每头D、整个H和Falcon4096通道；N整向量lease可用 |
| N1 原值与gamma准备 | M投影或分支输出→S原值；gamma或1+weight→参数区 | S、E（可选） | 所有写确认；gamma单位及饱和已核对，不能把FP32 1+weight默认为无损S16加法 |
| N2 全组统计 | 原值分批→N STATS→唯一统计上下文 | N、S | count达到精确向量长度才FINALIZE；其他head不能插入覆盖 |
| N3 因子和回放 | 原值/gamma→N NORM_REPLAY→归一化区 | N、S | 因子合法、完整回放确认；每条命令最多8元素，长度大于8仍属同一上下文 |
| N4 后继连接 | Q/K Norm→RoPE；Gemma后置Norm→残差E；其他Norm→M | 全局、E/M | 目的任务的类型、布局、数据范围已就绪；所有消费者结束再释放原值/参数区 |

**已实现**：N的数学与局部状态。**新增候选**：范围模板、gamma流式访问、上下文lease和地址生命周期。不能从旧norm106的H1536/H2560 S32专用结果转移N S16合同的质量或整链资格。

### 3.3 门控FFN：gate/up双输入与单M阶段切换

| 阶段 | 输入→输出/存储 | 负责子控 | 等待事件与提交/释放 |
|---|---|---|---|
| F0 输入与投影计划 | Norm输入、gate/up/down权重、原残差→存储布局 | 全局、S | 预算能容纳活跃中间量；当前M无其他活跃累加链；必要外存已明确 |
| F1 gate投影 | X→M(Wgate)→S Gate | M、S、E/包装器 | 完整计算、合法读出和紧凑化、S写确认后Gate_ready；读出前不能复用M结果 |
| F2 up投影 | X→同M(Wup)→S Up | M、S、E/包装器 | Up_ready；Phi融合gate_up时按明确Slice而非两次投影。不能把Gate保留在已被覆盖的M寄存器里 |
| F3 激活门乘 | Gate到G.x，Up到G.gate→G输出Mid | E/G适配、S | 两输入同token/tile/单位，G每包两元素，所有在途包退休且Mid写确认才发Mid_ready |
| F4 下投影 | 完整或按合法外存策略准备的Mid→M(Wdown)→Y | M、S | M完整结果上下文在整个跨K追加链内独占；不得用下一Gate/Up片覆盖它 |
| F5 后置Norm/残差 | Y→N（Gemma）或直接与残差→E→结果区/T | N、E、T、全局 | 相同范围与版本join；结果发布后再释放各中间区，T末字消费后RELEASE |

**已实现**：投影、G激活/紧邻门乘。**新增候选**：双输入join、分包、存储物化、M上下文lease。**数值决策**：固定S16基线与整K动态A8量化不等价；采用后者必须真实实现全K扫描、scale发布和存储，不是仅新增任务表条目。

### 3.4 Qwen3.5 GDN：卷积往返及先Norm后门乘

| 阶段 | 输入→输出/存储 | 负责子控 | 等待事件与提交/释放 |
|---|---|---|---|
| D0 投影/版本准备 | Norm(X)→M QKV/Z/beta原量/dt原量；保存old_root，预留状态/history privateNext和输出staging | M、S、版本服务、全局 | 各区域版本/容量有效；每tile原生owner/epoch/position已定义，不能一次装载供所有tile复用 |
| D1 卷积tile循环 | 每tile OPEN/装旧history和taps→卷积→op12保存输出→局部history COMMIT→op14导出到privateNext | R、S/外存、版本服务 | 先保存输出再commit，等真实提交响应和history写ACK后才OPEN下一tile；纯卷积未装state时不假定op11可读 |
| D2 激活与Q/K处理 | 卷积输出→E op13等转换→G SiLU→Q/K/V切分；Q/K→N L2及声明缩放→R | E/G、N、R、S | Q/K的Q1.14和V的S32单位有效；head重复映射清楚；N完整向量回放结束 |
| D3 系数生成/载入 | beta原量→Sigmoid；dt原量→Softplus；A*dt→负EXP→decay→R参数 | 显式数值服务候选、G、R | R要求UQ1.31 beta/decay及正确范围。外部已给系数可作为切片输入，但必须标出没有片上生成闭包 |
| D4 递推tile循环 | 每tile新OPEN/装old_root的旧state及Q/K/V/beta/decay→GDN→op12保存候选输出→局部COMMIT→op11导出新active到privateNext | R、S/外存、版本服务 | 所有输入有效才EXEC；输出先保存；提交响应、state写ACK齐全后才处理下一tile。history pass与state pass的逻辑位置绑定避免重复推进token |
| D5 全组屏障/输出Norm/门乘 | 收齐一个value-head的全部tile输出→E→N完整128通道RMS；独立Z→G.x，Norm(R)→G.gate | N、E/G、S/外存 | 全部tile输出及私有状态记录齐全；不能对8lane tile各自Norm。G执行SiLU(Z)*Norm(R)，同token/head join |
| D6 投影/产品发布 | 门乘→M(Wout)→残差；privateNext状态/history根与T/外存结果按产品协议发布 | M、E、版本服务、T、全局 | 各tile已局部提交/导出，此处不是一次整token原生R_COMMIT；分别确认根发布和输出发布，异常保留恢复资料，不宣称联合原子性 |

**数值缺口**：G无通用EXP；N的EXP依附Softmax统计最大值/计数、输出UQ1.15，不是独立UQ1.31指数服务。G Sigmoid Q1.14左移17位可换容器但不能恢复精度；E普通算术输出S16，不能默认产生任意S32注入。选择新数值服务、扩展叶宏或明确外部系数输入后，才能冻结D3。

上表为完整多tile候选的两pass次序。D1尚未局部提交时的history候选可按合同REVOKE；已经局部提交时不能REVOKE回滚，应保留old_root、停止/排空并显式恢复。单tile驻留且不依赖其他卷积tile时，也可保留pending_history穿过E/G/N后与state共同提交，但这是独立切片模板，不能替代上表完整token顺序。

### 3.5 Falcon SSM：先装decay、门乘后全通道Norm与双分支汇合

| 阶段 | 输入→输出/存储 | 负责子控 | 等待事件与提交/释放 |
|---|---|---|---|
| S0 双分支计划 | 同一Norm(X)分别供Attention和SSM，保存原残差 | 全局、S | 共享M/S由唯一所有者调度；双分支可以时分，不代表自动有双份硬件 |
| S1 投影/系数与版本准备 | M投影及MuP缩放→Z/XBC/dt；准备old_root、privateNext及每tile的state/history/decay记录 | M、数值服务、版本服务 | dt/Clip/负EXP/inject/skip真实存在。若采用单tile融合切片，state/op15必须在卷积前装完；完整两pass则在S4每个新context无pending时装入 |
| S2 卷积tile循环 | 每tile装history/taps→卷积→op12保存输出→局部history COMMIT→op14写privateNext | R、S/外存、版本服务 | 提交和写ACK后才OPEN下一tile；pending_history时仍禁止op1/op15。不能持有一个tile候选等待其他卷积tile输出 |
| S3 激活/递推输入 | 收齐所需卷积输出→E→G SiLU→X/B/C切分，物化Q1.14 B/C与S32 x/inject | E/G、S/外存 | 全组输入/参数版本齐全，不把多个tile未经保存的“最新值”相连 |
| S4 状态tile循环 | 新OPEN，装旧state和本轮decay/输入→SSM→op12保存输出→局部COMMIT→op11写privateNext | R、S/外存、版本服务 | 每tile无pending时装op1/op15，EXEC消耗decay；输出先保存，提交响应/状态写ACK齐全后处理下tile |
| S5 门乘与全组Norm | 收齐全部所需tile；独立Z→G.x，R读出→G.gate；G全组输出→N跨4096通道RMS | E/G、N、S/外存 | 先SiLU(Z)*R再Norm；全部通道统计屏障后回放，不能每128通道或每8lane各自归一化 |
| S6 混合层汇合/发布 | N输出→M输出投影/缩放；与Attention输出→E，再加残差；发布私有版本根与结果 | M、E、版本服务、T、全局 | 同token/position/version两分支齐备；此处不是首次R局部提交。根/输出发布分别确认，异常进入明确恢复 |

上表完整链采用分开的history和state-update pass。若另验收同一局部context卷积/SSM融合切片，则保留S1先装state/decay、S2卷积、S3外围处理、S4递推后共同提交的原生顺序；该切片不能声称覆盖完整4096通道Norm。两者均需真实组合验证，数值系数与S32 inject也尚未由当前E/G闭合。

### 3.6 Granite MoE：ID到数据访问、八专家时分与宽归并

| 阶段 | 输入→输出/存储 | 负责子控 | 等待事件与提交/释放 |
|---|---|---|---|
| E0 Router | token→M→40个S16 logits，保存原score表 | M、E/包装、S | score表80B按40元素物化；首版ID限定唯一0..39；尺度在实例合同中固定，相关数值验证为前置条件 |
| E1 TopK | (score,ID)→N TOP_BEGIN/TOP_LOAD/TOP_SELECT→8个ID | N | 只得到ID，不是selected logits；保存rank及token关联，重复/越界ID按合同拒绝 |
| E2 Selected-logit gather/Softmax | ID索引保留score表→8个分数→N Softmax→8个路由权重 | S访问器、N | gather需实际实现；TopK上下文后明确进入Softmax。权重与ID/rank同序保存 |
| E3 专家执行 | token及expert ID→权重地址；8轮M/G/M→专家输出 | 全局、访问器、M、E/G | 单M顺序循环rank0..7；每轮FFN遵守F0–F5及容量；完成当前expert的结果物化后才复用M |
| E4 加权归并 | 专家S32/S64结果＋对应权重→token归并区 | 显式宽归并服务或经证明的M缩放策略 | 不是普通S16 E乘法即可承担；不得在做下一expert时覆盖前一个活跃M归并上下文 |
| E5 缩放/残差发布 | 全部8专家返回→0.22缩放→残差→结果区/T | 数值服务/M、E、T、全局 | 缺任一rank不能发布完整token；归并及源数据在最后消费者确认前保留 |

**已实现**：M/N/G局部运算。**新增候选**：score gather、ID地址、专家循环/返回元数据、存储生命周期。**数值缺口**：宽加权ReduceSum和最终舍入位置。任意/重复ID的通用TopK仅返回ID时不总能恢复选中原记录；若超出唯一0..39首版，应扩展返回位置/score或另定更强规则并验证。

不能直接让单M一边累加MoE跨专家结果、一边拿同一完整结果寄存器计算下一expert。可采用外部宽归并、独立M实例，或真实上下文保存恢复的新宏合同；仅用任务表命名两个逻辑上下文并不能分出第二套寄存器。

一个可供评审的具体数值服务候选为`NUM_WACC`，不是已实现或已冻结的新宏：

- 输入选为M op5读出的S32专家结果，所有expert在同一声明单位；路由权重为N输出的非负S16 Q1.14，范围0..16384，rank限定0..7。
- 每8元素tile保留8份S64精确累加，共64B，仅是累加payload；还需rank有效mask、token/tile/scale/version、输入保持、控制及输出寄存，不能把64B当总面积/总存储。
- 每rank的8个S32结果来自两个128bit包，须明确完整rank准入/暂存或部分接收故障策略。例如暂存完整8元素再入账还需32B，避免仅半个rank已加入就误标完成。拒绝重复rank和不同token/tile混入。
- 不使用“权重和必为1”缩窄范围。最多8个expert，每项幅度不超过2^31×2^14，因此累加幅度不超过2^48，可由S64保留。
- Granite的0.22可比较整数近似7209/32768。候选在精确sum上乘7209，再作一次最终RNE；当专家输入与目标输出共同小数尺度相同时总右移29位（14位路由权重＋15位缩放），其他情况还需加入F_in−F_out，而不是每个expert提前舍入；乘积幅度小于2^61，仍可用S64承载。最终输出宽度、饱和/拒绝策略、残差单位及近似误差需独立oracle决定。
- 只有rank mask=0xff且全部接收/累加结束后才允许发布该tile。若专家输出改成S64，或改变权重/系数范围，以上范围证明立即失效，必须重新分析更宽乘积/累加及硬件资源。
- 该候选的整数可行性不等于原FP32 MoE数学完全一致；输入量化、M读出饱和、0.22近似及最终输出质量仍待验证。

一般二进制尺度公式为`shift=29+Fin−Fout`，首版仅接收已证明范围的非负右移；负shift涉及左移，须重新证明范围和硬件能力。这里的一次最终RNE仅指NUM归并内部，M op5此前仍可能按自身合同量化；详见总方案§8.2。

## 4. 八样本差异到模板的覆盖表

| 样本/层型 | 需要的模板与不能省略的区别 |
|---|---|
| Qwen2.5-3B | 常规Attention＋SiLU门控FFN；Q/K/V投影有偏置；GQA比例16/2=8；H2048、I11008需明确大中间量存储 |
| Qwen3-0.6B | 常规Attention＋Q/K头内RMS＋SiLU FFN；Q_heads×D=2048而H1024，不可由H/heads推D |
| Llama-3.2-1B | 无Q/K头内Norm的常规GQA与SiLU FFN；D64、GQA32/8=4；该样本来源为随机参数配置重建 |
| Gemma-3-4B局部/全局 | Q/K RMS0、注意力后及FFN后RMS0、GELU_tanh；六组Norm；局部窗口1024与全局mask/位置频率不同，不能只换一个统一mask常量 |
| Phi-4-mini | 融合QKV和gate_up投影后的Slice/分发；D128只有96通道RoPE，其余旁路后重合；GQA24/8=3 |
| Qwen3.5-4B全局/GDN | 层序列[GDN,GDN,GDN,GlobalAttention]重复；全局层Q同时产生输出门、Q/K RMS0、部分RoPE64/256；GDN无QK Softmax/RoPE，卷积/递推及先Norm后门乘 |
| Granite-3.3B | 普通Attention＋40选8 MoE；attention_multiplier=0.015625不可换成1/sqrt(D)；0.22缩放；每expert I512不是全部专家总中间宽度 |
| Falcon-H1-3B | Attention/SSM双分支并行语义和同token汇合；多处不同MuP缩放；K在RoPE前额外scale；SSM先门乘、后4096通道RMS |

这些差异可由固定产品程序和参数表达，但所调用的数值运算、地址/布局资源必须真实存在。没有把八模型的FP32图自动转换成当前七宏定点实现，所有新增精度选择都需独立整数oracle及模型质量评估。

### 单R tile与完整token的额外状态服务

下面D0–D6、S0–S6的R事务表首先描述一个可驻留的局部tile。当前R的value/channel方向只有8lane；GDN每value-head的128通道Norm及Falcon4096通道Norm必须收集多个tile。不能将所有tile候选同时留在一个R影子银行，等整组Norm后才一次R_COMMIT。

完整链主候选增加STATE_VERSION_CTRL职责及真实外存版本存储（它是母控/存储服务内的元数据角色，不新增一层独立原生命令所有者）：保留已发布old_root，为每tile准备私有next版本；R_CTRL计算、先读候选输出、完成本tile局部提交，再将新active及history按原生可读接口保存到next，确认后才能OPEN/装入下tile。完整输出范围汇齐后才做全组Norm和后续投影。最终状态根、输出staging和消费者可见性需另有发布/恢复合同。

因此事件至少区分R_LOCAL_COMMIT_DONE、STATE_TILE_SAVED、STATE_ROOT_PUBLISHED和OUTPUT_PUBLISHED。R内局部提交不等于整token发布；旧根未发布前保持可恢复，但失败后仍须排空并显式重装，不能声称本地状态从未改变。外存容量/带宽、history去重和映射、根描述符、发布门与复位恢复均为新增候选，未实现前只验收单tile切片。R/T仍无联合原子提交或掉电保证。

## 5. 单M、S16KiB、T6KiB的明确资源规则

1. M有有限A/B双银行与64份S64完整结果，并非任意数量可抢占上下文。跨K追加期间全局序列器锁住相应完整结果；相同M计算gate/up/下一个expert可能覆盖该结果。当前没有通用完整结果重装接口，不能只“存S再恢复”而不设计新动作。
2. 大FFN先物化全中间量再切换M是可定义基线，但可能必须外存：I11008的gate/up两个S16向量共44032B，单gated中间量22016B，均超S。对I10240同样单向量20480B超S；Phi I8192单向量已占满16KiB，其他活跃输入/权重/残差不能被忽略。
3. 为同一M分配多个算法子程序不增加寄存器、乘法器或端口。多实例或增加宽partial归并能改变这一限制，但必须作为有成本的新底座候选。
4. S普通口是128bit整字；每个bank实际1RW，宽loader占四bank。调度器限制一次普通请求的响应归属，并按loader描述符边界安排窄访问窗口；不能假定持续宽读下窄口总能服务。
5. 所有S区按实际容器计价：A一行虽可能只用8个S8，S loader仍按128bit A容器、四行一组512bit读；填充必须计字节。E/G半包不能用不存在的byte mask写入。
6. T一次最多384字=6144B。紧凑S16只容纳3072元素；Falcon4096输出8192B需分批T或其他输出区，分批不能冒充整向量原子发布。
7. N统计长度最多65535不表示原向量可驻留S。65535个S16原值131070B；外存/回放和有限输出发布必须有方案。
8. S中转不保证物理最小或最快，只提供一种功能基线。全局存储访问网络和各wrapper也要预制、计面积、引脚、PG/CTS、控制线、长线驱动与负载。

## 6. 最小门控FFN分配与事件实例

### 6.1 固定配置和性质

这是**新增候选验收实例**，不是八模型完整FFN。选择一个token、H=8、I=8、输出H=8，不含输入Norm；输入X和残差均为八个Q5.10 S16，三矩阵均为8×8 S8整数权重，采用SiLU门乘。M为S16×S8、一个K8 tile、一个A行、N=8；缩放factor=1、left_shift=0。初始样例可取三矩阵为单位阵、小范围输入（例如-2,-1,-0.5,0,0.5,1,2,3），之后再加入非单位随机小权重。

M op5选择S16饱和、right_shift=0，响应仍为四S32容器。先以E op13 shift=0做四S16包装，两个半包合成一个S字；数值已由M限制到S16，包装阶段不得再次引入非零缩放。G输出Q5.10，down矩阵S8整数使单位保持Q5.10，最终E ADD与相同Q5.10残差相加。所有溢出/饱和标志按策略核对，不能只比较低16位。三次切换Wgate/Wup/Wdown时均显式load_reuse_b=0，M描述符匹配fmtA=1/fmtB=0、rows=1、tiles=1、lastK=8、N=8及同一目标bank；不能误复用上一份驻留B。

| S128bit字地址 | 预留字数 | 用途/布局 |
|---|---:|---|
| 0..3 | 4 | M的X A组：word0装八S16，其余为对齐填充；同时word0保留作残差 |
| 4..7 | 4 | Wgate：一个S8 K8×N8块，n-major `8*n+k`，64B |
| 8..11 | 4 | Wup：同上，64B |
| 12..15 | 4 | Wdown：同上，64B |
| 16 | 1 | 紧凑Gate八S16 |
| 17 | 1 | 紧凑Up八S16 |
| 18 | 1 | 紧凑Mid八S16 |
| 19 | 1 | 对齐预留/不可当第二个中间向量 |
| 20..23 | 4 | down A组：word20为Mid副本，其余为对齐填充 |
| 24 | 1 | down Y八S16临时区 |

S预留0..24共25字=400B，已包含A组和地址对齐预留，不包含宏内A/B存储、wrapper寄存、标签或控制表。T预留1字=16B用于最终结果。这里没有隐含第二套S，也没有权重DMA；源数据由实例初始化明确写入并排空响应。

### 6.2 固定阶段事件

| 步骤 | 操作/等待 | 产生事件 | 何时可释放 |
|---|---|---|---|
| f0 | 初始化S0..24所需数据；每次写接受后消费真实S响应；预留T/控制事件槽 | `ffn_input_ready(v)` | X残差在最终ADD前不可释放 |
| f1 | S loader A_base=0/B_base=4，rows=1/tiles=1/A_wide=1/B_wide=0；等done并take；M op10 clear=1，等错误检查；两次op5、两次E13并合包写S16 | `gate_ready(v)` | M读出已物化后允许下一投影覆盖M结果；S16直到G消费后才释放 |
| f2 | 相同A_base=0，B_base=8计算Up；读出/包装写S17 | `up_ready(v)` | 原X仍供残差；Up保留至G全部输入接受 |
| f3 | 等gate/up两个ready；读S16/S17，按四个两元素包送G，SiLU且gated=1；collect四包写S18并等S写响应 | `mid_ready(v)` | G已接受源包且不需重放时可按策略释放Gate/Up；不得用G首包响应代表全部八元素完成 |
| f4 | 读S18写S20，S21..23初始化填充；确认写响应；loader A_base=20/B_base=12；M新clear=1完成down，读出/包装写S24 | `down_ready(v)` | 同M的Gate/Up阶段已彻底结束；无另一条M追加上下文同时存活 |
| f5 | E ADD读取S24与S0；T BEGIN(words=1)已被接受，E输出按真实T写握手写入index0；等T SEALED再COMMIT | `ffn_publish_done(v)` | 提交前失败可REVOKE；不能在T未接收输出时宣称结果已发布 |
| f6 | 下游TAKE index0且last=1，再RELEASE握手；清本次S槽的逻辑有效/所有权 | `ffn_release_done(v)` | 全部承诺消费者及在途响应已结束，才复用token/version与槽 |

这条实例刻意先完整物化Gate/Up/Mid，再让同一个M执行down，避免M跨K上下文冲突。它不能用来证明I11008时只靠400B或16KiB即可完成。

## 7. 257元素Softmax的分配、阶段和事件实例

### 7.1 分配与数据格式

这是**新增候选RTL组合验收实例**；仓库已有SystemC 257轨迹可作为顺序阅读参考，不能代替本控制硬件实现。

| 区域 | 地址/容量 | 类型与用途 |
|---|---|---|
| S原始X | 128bit字0..32，共33字=528B | Q5.10、257个S16，最后一字仅lane0有效，填充不参与统计 |
| S EXP | 字64..96，共33字=528B | UQ1.15中间值，独立于原始区；32768是合法EXP(0)，不能按负S16解释 |
| T输出 | index0..32，共33字=528B | 最终非负S16 Q1.14；最后一字有效数1，read_last指包尾而不是单独说明元素数 |

有效S区共66字=1056B；地址间的空隙不是额外向量缓存。T另528B，wrapper、N统计/因子和事件表另计。首版保留原值/EXP分区便于审计，之后可在证明无其他消费者时评估原位覆盖，不提前把节省计入。

可沿用教学输入：前256项循环[-1,0,1,2]，第257项为4（按Q5.10编码）。测试必须检查最后一个元素到达前不出现最终最大值4；概率采用独立LUT/RNE合同参考，不要求独立量化后概率总和恰为16384。

### 7.2 固定程序与完成条件

| 阶段 | 子控操作 | 必须等待 | 可发出的事件 |
|---|---|---|---|
| p0 | 原值写S，保留唯一N向量lease和T的33字资源额度 | 所有S写响应排空，X版本有效 | `soft_input_ready(v,257)` |
| p1 | N BEGIN(mode0)；33轮S读→N STATS，count为8×32后1 | 每轮命令/响应对应，实际接受元素总数257 | `stats_complete(v,257)`；尚不能输出概率 |
| p2 | N FINALIZE | 因子前置阶段响应成功、最大值已固定 | `max_final(v)` |
| p3 | 33轮重读X→N EXP，原样保存每包有效结果到EXP区 | 每包N响应与S写确认；EXP累计元素257，所有保存写响应排空 | `exp_data_ready(v,257)` |
| p4 | N FINISH_EXP | exp_count等于count、exp_sum非零，因子响应无错误 | `factor_ready(v)` |
| p5 | T BEGIN(words=33)；33轮S读EXP→N SOFT_REPLAY→T WRITE(index0..32) | 末包count=1；每个输出保持至T接受，累计257元素/33个字，T已SEALED | `soft_output_filled(v,257)` |
| p6 | T COMMIT | commit握手，数据不再属于可撤销填充 | `soft_publish_done(v)`；不是所有消费者已经完成 |
| p7 | 下游顺序TAKE 33字，检查index和最后字last；RELEASE | 末字消费、release握手及所有在途事务排空 | `soft_release_done(v)`，此后释放N上下文与S原值/EXP区 |

N原生接口没有目标长度字段自动代表本程序的257；wrapper必须维护预期总长与每阶段计数。不得发32次STATS后提前FINALIZE，也不得只保存EXP总和而丢掉随后回放需要的257个EXP编码。

## 8. 验收用例与分阶段接受条件

以下均为**待执行候选用例**，不是测试结果。真实运行必须固定代码/工具/输入/输出SHA和全新目录，遵守服务器/Slurm规则，提交后提供作业号、追踪命令、日志与结果路径。

| 编号 | 验收对象 | 正例与必须检出的负例 |
|---|---|---|
| V01 | 类型及连接静态检查 | 拒绝4×S32当8×S16、EXP UQ1.15当最终概率、错误scale/head/tile/version、无实际物理路径或S地址越界 |
| V02 | S管理/包装 | 每次请求/响应恰好归属一个消费者；E四元素和G两元素拼包；拒绝无byte mask的虚构部分写；宽loader期间窄口等待可恢复 |
| V03 | 最小FFN | 上述400B分配、单位阵及随机小权重独立整数参考；乱序gate/up包、尾部、G背压、M响应未物化即覆盖必须拒绝 |
| V04 | M上下文/错误 | 同时分配Gate/Up与down追加链的冲突拒绝；混合成功/失败行及追加命令盲重试负例；不能将失败行保留误当整命令回滚 |
| V05 | 257Softmax | 最后一项新最大值、count/EXP/replay=257；有限随机背压下33个输出字守恒；提前FINALIZE/FINISH、丢末元素、重复回放拒绝 |
| V06 | 额外Norm | RMS、RMS0、L2的不同oracle，gamma尾块、epsilon、head128/256与H2560；不得把Falcon4096拆成独立128维Norm |
| V07 | Attention | 小头QK完整K归约→全组Softmax→PV→Wo；GQA/Phi Slice/部分RoPE；mask有限码及量化误差分别核对 |
| V08 | GDN往返 | 卷积→SiLU→L2→R、R→N→G；G的x/gate角色、beta/decay范围、候选输出先读、后续失败留下history候选后REVOKE |
| V09 | SSM顺序/混合层 | 先装本轮decay→卷积→激活→SSM→读出→共同提交；在pending_history时装decay应拒绝；Attention/SSM乱序完成仍正确join |
| V10 | MoE | 40选8 tie/唯一ID、80B logits gather、8权重与rank对应、不同token不能互相归并；少一expert禁止发布；宽累加溢出和M上下文冲突 |
| V11 | 生命周期/复位 | T未写满、重复index、提交后撤销、未消费末字即release；N上下文未完成切换；已接受存储写不能靠本地reset假装撤销 |
| V12 | 活性与成本 | 声明容量/公平性下有限等待、无ready组合环、事件与数据槽分别预留；报告最大队列占用、实际S/外存字节和控制开销；永久不ready不承诺完成 |

第一阶段通过静态表、整数oracle和wrapper RTL组合后，才可声明对应有限模板功能成立；之后才开展新增支持宏及实际系统路径的综合/物理表征。单宏300MHz、旧bridge或SystemC无时钟通过均不能替代这两阶段。

## 9. 固定证据链接

- [既有六类研究49a34e75](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/49a34e75657025244fd33af56111029868008db8/docs/SIX_CONNECTION_SCHEMES_STUDY.md)
- [既有协调候选49a34e75](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/49a34e75657025244fd33af56111029868008db8/docs/SIX_CONNECTION_COORDINATION_CANDIDATE.md)
- [既有bridge来源审计49a34e75](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/49a34e75657025244fd33af56111029868008db8/docs/SIX_CONNECTION_BRIDGE_AUDIT.md)
- [样本图及导出边界a103da35](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/a103da352b7e431cedc69f54b9f71c05371be1b3/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md)
- [七宏旧固定合同5e787714](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/docs/BLOCK_V2.md)
- [M寄存器、命令与行提交](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_m.sv)
- [N阶段许可及TopK仅ID](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_n.sv)
- [E包装、RNE及op13](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_e.sv)
- [G输入角色及整体背压](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_g.sv)
- [R载入限制、候选输出和COMMIT](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_library_v1/block_v1_r.sv)
- [S loader有限槽与装载完成](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_feed_v1/block_feed_loader.sv)
- [S真实bank及窄宽仲裁](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_feed_v1/block_feed_s16k.sv)
- [T单租约生命周期](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v1/transaction6k.sv)
- [SystemC257元素顺序参考](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4ad1ad4643d08cabf2fcc35e9465424556b1f325/project/systemc/examples/softmax_trace.cpp)
- [SystemC E旧操作集](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4ad1ad4643d08cabf2fcc35e9465424556b1f325/project/systemc/include/blocks/e.hpp)
