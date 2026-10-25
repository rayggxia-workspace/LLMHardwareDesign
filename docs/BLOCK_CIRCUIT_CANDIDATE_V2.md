# Block 电路候选 v2：数值合同与物理边界收敛

2026-10-25；负责人 Liangruizhi；[Issue109](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/109)。本版基于97已验的研究物理范围、104完整GDN及109真实四profile共享服务。冻结的是下面的数值、状态、响应所有权和有限容量合同；制造宏、跨Block最终拓扑、固定金属层集合仍是待验证候选。

## 1. 可直接继续实现的电路组织

采用一个串行owner lease的有限共享银行：一个16KiB/128bit/1RW暂存S，八个有符号8×8乘法lane，一个有符号32×32→精确64bit服务（两个独立64bit响应槽），一个U128 SFU，以及一个128bit外部桥。M/V、A、Falcon R、GDN R各保留自己的有界语义控制器，由D选择唯一owner。当前controller的加法、比较、shift/RNE、宽guard、地址和暂存寄存并未全部合为一个ALU，其真实门数已计入映射；“唯一服务”不能理解成只有九个乘法器需要付费。

| 组成 | 当前实现与预连线候选 | 必须保留的接口义务 |
|---|---|---|
| M及专用V前端 | S32Q12 gate/up→整数SiLU/LUT→完整K512量化δ/A8→8S8矩阵→RQ/merge/residual→全行norm；A缓存4KiB按本M lease重建 | 完整K归约后才按原合同RQ；每专家δ与scale/格式随所属张量、版本绑定；不能让tile局部量化悄悄改数学 |
| A | 同8S8 lane承担Q8/KV16的3/9limb分解；S保存score/P/tile/output；同S32与SFU完成缩放和概率 | 保留每级I32 guard、完整归约、P15/KV16格式及当前三遍materialized算法；当前没有KV append、online或投影/RoPE |
| Falcon R | 完整D128×N256单head的αS+x(dtB)及readout；宽路径用同S32 | 完整head保守guard、trial/retry、shadow与128bit root发布；单head恢复域不扩成原32head共同epoch |
| GDN R | 完整两头128×128 delta-rule；S64中间量、非对称S32存储、每头I8 unit；3段radix2^31乘积lowering走同S32后一次RNE | 全head取range，失败head整头重标，收齐两头badmask；group numeric_epoch与两个独立unit一致，双metadata+单root原子发布 |
| S | owner选择器前仅一套16KiB/128bit1RW及一个有限响应 | req/wr/addr10/data128→ready，valid/data128→take；响应保持到take，访问与响应所有权不能跨lease漂移 |
| typed S32 | 两个请求端口通过实际仲裁、同一个signed32乘法器，两个64bit响应holder | 各端口req/a32/b32→ready，valid/y64→take；不能把宽GDN直接截断为S32，不能另藏S64/128乘法 |
| SFU | 当前PROFILE1：U128除法128迭代、整数平方根64迭代，单有限响应；乘法由S32承担 | req/op/a128/b128→ready，valid/value/remainder/error→take；本候选只用已定义除法/开方操作，opcode0残留零值路径不构成乘法能力或通用合法opcode |
| D/外部桥 | 单owner命令锁存、S/S32/SFU/link选择、结果导出与排空；当前每外部事务5×128bit线拍 | 区分数据payload、实际beat、request/response generation sideband；控制输入忙时变化不改变已接受命令；所有接受的操作effect-once |

现有连接是实际RTL里的operand/result mux和ready/valid通路。算术和存储端点可以作为制造前固定候选，但mux证明的是运行时复用；它不证明M9–M10金属定制可行。当前没有通用V ISA/外部程序取指，也没有把80的byte ALU、ROM或512B frame额外免费叠加。

## 2. 为什么这些边界应当保留

**完整归约是数值边界。** 当前M的INT32部分和必须保持到完整K512归约完成，随后才进行已有的scale/RQ/round/saturation。若以后在多个物理单元间分摊K，必须传递未重新量化的足够宽部分和及scale/版本，计入传输、缓冲和重对齐；不能把局部A8输出当同一个计算。完整K的量化统计与最终RQ逻辑归属应保持明确，S32服务的物理位置仍可另作同资源比较。

**整head是R范围与恢复边界。** GDN实际出现超过S32的residual/correction，S64中间量与exact乘积后一次RNE不能因观测子集较小而降宽。trial、proposal、shadow和发布root是不同生命周期；tile只控制搬运/暂存容量，不能独立更换unit。GDN两个head必须收齐guard并以同一root发布；两个独立逐head提交不能替代这个事务。Falcon与GDN分别保留原数学和恢复域，不能用一种R更新式代表全部已选模型。

**服务响应属于原命令。** S32的两个holder、S返回、SFU结果和外部桥在途请求必须在lease交接前消费或合法丢弃。D transport generation只负责请求身份，不能同时充当R numeric_epoch、模型position或checkpoint version。GDN position64与version64独立，不能改成99的alias。

这些结论支持明确的计算/状态控制器边界与有限服务接口。它们没有单独确定M+A合宏、V/R合宏、R独立硬宏或最终跨Block布线拓扑。

## 3. 地址与生命周期：S不能当跨算子的隐含状态

| 数据 | 存放与有效期 | lease交接规则 |
|---|---|---|
| M A8/δ、MID及norm临时量 | 本lease的S/控制寄存，复用实际M生命周期 | 进入A或R后不得假定4KiB A仍保留；下一M命令重新构建 |
| A Q/score/P/key-value tile/output | 近满16KiB的实际A布局；registry只保存KV版本/尺度等元数据 | 不与M frame/A缓存相加；KV是外部caller committed前缀，版本规则跨lease保留 |
| R/GDN scratch | 当前tile、系数与宽运算暂存；每STEP从合法外部状态重载 | 不依赖上一lease留下的S数据；其他profile可以覆盖S |
| Falcon published state/Y/root | 独立0x06000000..0x06100000窗口 | 失败只改private区域；恢复读取真实published descriptor |
| GDN双state、trial、I64 proposal、双Y、双metadata/root | 独立0x06200000..0x06300000窗口；mutable659600B，加32slot系数50176B，共709776B | 32slot是明确上限，不代表256token输入全驻留；pointer/owner/context/position/version必须绑定 |
| LUT与其他profile外存 | C0外部LUT128KiB，M/A各有协议限定窗口 | 不计成片内ROM；每次取数实际占外部桥并计5beat事务 |

两个state/Y bank只支持当前与下一代。当前合同为单owner、禁止busy期间外部并发读写；DONE ACK表示旧一代引用已释放。不能在两轮后覆盖旧bank仍宣称任意历史快照永久immutable。未来多消费者必须引入可实现的引用/credit或spill合同，并计价。

## 4. 导出、候选和提交

M完整结果6144B、A4096B和Falcon候选512B通过共享S口真实读回；GDN候选2048B位于外部Y bank，经同一个外部桥128次16B读取输出。GDN新增基址32bit、索引10bit、pending1bit，并锁定owner/context/position/version/units/numeric_epoch/bank完整273bit候选身份；有界控制寄存与mux在新映射内。

结果通道valid/data/index保持到take。GDN全部128行ACK后才允许candidate accept/reject；导出期间abort必须停止新读并排空D自己的pending请求。accept开始逻辑提交，此后即使root写尚未获fabric接受也不能取消；128bit原子root写ACK后才更新published镜像、DONE和交接。reject或可取消失败不得改变当前published state/Y/root/meta。硬reset必须协调完整fabric，以真实root恢复，不能由host猜测迟到写是否已发生。

当前环境sink最多6KiB，GDN用2048B；结果前缀为provisional，失败须丢弃。另有外部两槽FIFO最低320bit payload+epoch加控制。它们不在core logic area内，也没有实现为下一个Block的事务buffer。**真实下游必须承担完整暂存、commit/revoke与读引用释放责任**；仅把result_take拉高不能证明完整消费者链成立。

## 5. 证据和成本边界

| 对象 | 已有证据 | 可使用的结论 |
|---|---|---|
| 97独立V/M消费者 | [98 / PR111](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/111)：研究Nangate、整store82切口、固定I/O下布局/CTS/详细route/RCX/全端点时序与严格电气、精确最终4×2正常gate | 76964.174µm²为这个研究logic-island的实际单元面积；真实SRAM/上游drive/PG/PVT目标工艺与固定M1–M8资格仍缺 |
| 104独立GDN | [报告](experiments/issue-104-gdn-state.md)：native32/portable12完整两head、真实重标、独立数学/恢复与selected raw gate | 确认实际完整更新/guard/发布合同，不能自动授予共享109的接口或物理资格 |
| 109四profile共享 | [报告](experiments/issue-109-shared-gdn.md)：两路13混合/44恢复完整数值与11项实际文件负例通过；两路selected raw gate各8完整命令/真实重标逐字节和独立数学通过 | 单一真实资源银行可执行这四个有界profile，logical mapping163901.220µm²；未进行新top宏/时序/布局布线验收 |

97的76964.174µm²已含其研究物理修复，109的163901.220µm²是功能更多且无物理修复的logic-only。不能相减得同函数划分收益，109不能继承98的79600.5µm²预算、10ns资格、端点或固定层方案。M/A/R交替执行证明资源复用；它们来自不同代表输入，不是一个模型的端到端数据链。

GDN候选导出需128外部事务、2048B payload、10240B wire和1024B generation sideband。quiet native步骤2296327周期，真实legacy重标步骤3907725周期，完整重标/宽S32/端口费用均保留；两个输入不同，不用差值宣称优化收益。D导出时间与R OFFER等待重叠，不能相加重复计周期。

Issue110已在独立任务通过完整数值/周期/事务比较、真实proc-cell SAT/FF归纳及选定raw gate，当前未合入109。其STYLE2 QK34/PV45在同一fresh shared106对照中为125009.626µm²，STYLE0为126029.470µm²，logic-only少0.80921%；不能改用历史106面积作baseline或直接移植到109。该等价微优化作为后续可选实现，需显式STYLE=2（模块默认仍0），不改变上述分区，也不能代替整个新共享核的面积、时序和宏验收。

## 6. 真正影响物理定稿的最小下一门槛

1. **实现一个真实事务消费者接口。** 沿现有输入选择一个已需跨边界的完整输出，不增加模型。让下游在有限2048B或6144B容量、实际端口下接收provisional结果，执行commit/revoke、读引用释放和backpressure。覆盖中途取消、最后一行保持、迟到响应和不可撤销root；比较端到端同精度/同资源成本。若所需buffer/端口超过候选预算，重新比较合并边界或spill策略。
2. **冻结可用S宏及真实上下游drive/PG/PVT合同。** 明确16KiB128bit1RW的同步延迟、读写冲突、reset语义、响应保持、时钟/供电/阻挡/端点和真实driver/load。实际`store82.sv`的reset只清响应valid/dout，不初始化words[0:1023]。每次读取前必须由当前数据加载或有效性证明保证内容；测试台cfg写入的canary/输入初始化属于本实验setup，需与核心命令周期分列。真实宏读延迟、冲突、响应保持、clock/power及物理端点仍待定，不能由行为wrapper直接签核S边界。
3. **对实际新top作有限物理实现。** 先固定面积/频率/端点/允许buffer-resize预算；从109或经完整复验后的可选优化源生成精确网表。完整时序/strict cap/slew、RCX/DRC、实际宏阻挡和PG一起验，精确后网表再跑已选完整checkpoint。失败不能放宽端点/隐藏debug或继承97结果。观测端口若要删除，需单独固定产品接口并重新核功能与成本。
4. **再比较制造前固定与产品后定制。** 与55/63的端点/固定层交付对接，给出真实可达pin、局部预连线、允许变更的金属/通孔及阻挡。仅在同算术/容量/精度和物理预算下比较候选M+A、R独立或V/R关联；当前不冻结任何M9–M10拓扑，也不额外扩模型矩阵。

门槛1验证真实消费者和缓冲边界，门槛2/3验证存储/端口/时序是否容纳候选，门槛4才回答制造划分的最终可行性。没有通过的项继续保留为未完成；不能用某一项周期或逻辑面积改善抵消数值、原子提交或电气失败。
