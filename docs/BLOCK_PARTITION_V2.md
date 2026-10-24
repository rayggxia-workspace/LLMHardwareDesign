# 算子与Block划分方案v2：单位、范围、状态闭包与可选物理归属

2026-10-24（Asia/Shanghai）；负责人Liangruizhi；Issue64，基于PR62及此前Llama/Qwen证据。状态：有证据的具体候选，非最终最优制造库/芯片验收。Issue66进一步完成完整hidden消费者、整数RMSNorm与连续R/conv及256步范围诊断；最新修订见第9节。新增A/B/C服务器两轮及独立接收已完成；[完整报告](experiments/issue-64-block-v2.md)与[成果索引](../project/experiments/block_decisions/results/issue-64/index.json)可复查。

## 1. 划分方法与证据层级

先按数学函数、格式/单位变化和状态提交点拆语义节点；再以合法舍入、完整归约、范围证明、共享状态和依赖组成可验证闭包；最后才在相同算术、RAM、端口、FIFO和连接预算下选择闭包的物理归属。语义不可破坏不等于所有节点必须同宏：若跨Block接口完整并付出相应代价，拆分仍可行。

每条边至少声明dtype/有效位/单位及scale粒度、shape/layout/valid范围、row/head/K组/digit、partial或complete、mask/window、profile/epoch、owner与release事件。节点包括QUANTIZE、ALIGN_REDUCE、bias、RNE/SAT、KV_APPEND、概率归一化和STATE_COMMIT，不把它们藏在免费通信里。tile是调度单位，Block是重复服务各层的制造模板；不按每个算子实例或每个Q头复制硬件。

比较只有同一数值函数才进入收益排名：提前组RQ、重置状态、跨scale直接相加和没有足够端口都不是合法替代。局部误差、软件整数、条件服务、RTL和物理各自验收；未过数值门的profile可作结构敏感性，不能称可接受应用加速。

## 2. 综合证据矩阵

| 证据 | 实际合同/范围 | 对边界的支持 | 不支持的外推 |
| --- | --- | --- | --- |
| Qwen3-0.6B Issue47/PR49 | 一层完整2Q/1KV，32+8，校准共享QK变换、KV8、整数LUT/P15 | KV共享profile/epoch、追加后发布；单份10240B，按头复制20480B | 1.8%–1.9%局部RMSE不是模型质量；未测真实广播/端口 |
| Llama1B Issue56/PR57 | 一层4Q/1KV，32+8；完整K相同单位 | 提前K128 RQ改变28950/43520输出，完整归约语义不可省 | 矩阵位置和整图加速；该同单位界不能套混合Kscale |
| Llama down Issue59/PR60 | K8192/前16输出，24候选144条件 | 动态K128重要；Wout7.36%→W1285.39%，RQ前4.81%→后5.39%；输出合同是剩余分叉 | 5.39%仍未过原探索门；16输出不代表全层，原失败不改写 |
| 三主测 Issue61/PR62 | Q25全8Q/1KV、Q35全4Q/1KV、Gemma local/global全2Q/1KV；420线性56注意力格式 | 动态A K组改善，P/KV精度独立，5185来源张量含封存Phi | FP64softmax的注意力误差不能和Issue47/56整数LUT/共享变换直接横排模型难度 |
| fixed-W及Psum界 Issue61 | 所见W/scale，受检1474560 PV32输出 | 完整归约可条件INT32，需系数/guard/不可变Vscale | 粗35/44位不能直接判必须64；切片证明也不能删除宽回退或覆盖online未归一化O |
| R/窗口真实证据 | Q35连续初末状态及12原窗口/6边界重放；Gemma1023/1024/1025及4096+32 | 状态owner/epoch/连续history、local/global不同生命周期 | FP32连续性不等于整数状态；框架底层分配不等于硬件必需SRAM |
| RQ同资源服务 Issue51/56/59 | 已声明的局部服务/边界/库存，各自优化调度 | Qwen最大0.5657%、Llama约1.385%/2.334%不足以唯一固化近M | 不同服务边界不能拼成端到端收益，新模型不能继承百分比 |

覆盖的是架构轴：普通dense GQA（Qwen2.5/Llama）、带QK norm的普通attention（Qwen3小模型）、Gemma局部/全局与GELU差异、Qwen3.5递推/全局混合。Phi只封存，不算当前方案的独立泛化通过。原版DeepSeek-R1的MLA/MoE、其他未跑架构和完整训练都未得到本轮数值覆盖，R1蒸馏不能替代原版。论文若扩大到这些架构，应新增真正改变状态/通信的合同与证据，不凭品牌数量声称全覆盖。

原始出处：[Issue47](experiments/issue-47-primitive-stream.md)、[Issue51](experiments/issue-51-rq-port-placement.md)、[Issue56](experiments/issue-56-llama-cross-model.md)、[Issue59](experiments/issue-59-llama-down-scale.md)、[Issue61](experiments/issue-61-server-models.md)。模型revisions、源码commit、环境、输入SHA和成果索引按这些原合同保留。Phi仅封存不参与当前调优。

## 3. 本版具体Block方案

继续六模板M/V/A/R/S/D：M/V/S/D是基础库候选，A/R保留逻辑闭包，物理独立性待验证。下表描述制造接口/预连线的候选方案，不代表所有算术已实现。

| Block | 计算与内部状态 | 制造前内部预连线 | 外部接口与留给产品的选择 |
| --- | --- | --- | --- |
| M矩阵/受检归约 | 16×16 S8阵列，Ktile128 i32部分和；单位对齐、完整归约/bias后单次RQ；32KiB含双buffer、PE和受限scratch | operand→MAC→组acc反馈；完整/partial typed mux，RQ可绕过；归约引擎数量不得随placement复制 | A8/W8或S8 digit；PARTIAL32+unit/组计数；COMPLETE32/宽格式+证书；ACT8/16；A分组128/更粗及Wout/W128、RQ近M/共享V按合同配置 |
| V向量/转换 | norm、RoPE、SiLU/GELU、残差、scale编译和格式转换；8lane/16KiB候选，宽平方和/移位/比较和SFU单独声明 | shuffle/reduce/可装载表→RNE/SAT；共享ROM/divider真实仲裁；copy/pack也占端口 | 有版本的gamma/epsilon/LUT/scale；动态row delta与消费者/残差对齐；多模型非线性不固化成单一矩阵epilogue |
| A注意力闭包 | 规范化概率、mask、Psum守卫、固定V单位的PV完整归约；32KiB临时，20KiB单读ROM候选 | score→max/exp/sum/div→受检P→PV反馈→最终转换；与M共用矩阵资源，不赠第二阵列 | M→A score/partial及A→M P双向；KV8/16、主路径P15（P7只允许独立接受的受限profile）、长度/窗口/单位/epoch和guard；独立A或同宏M+A仍比较 |
| R递推/conv闭包 | 完整共享key组状态与history/epoch单owner；K128×V32 S32为服务tile、非完整head；old+shadow32KiB无aux余量，tile16本地shadow或tile32/S侧shadow待比较；投影全K后更新 | history环反馈；decay→projection→delta→outer update→从新state形成output→同版本共同commit/发布；不提前partial-K写state | q/k/v/beta/decay格式与初态、共享keyhead、state page epoch；独立R/共享V待整数数值及公平服务对照 |
| S存储slice | 8×32KiB、各128bit1RW候选；权重、全局KV、局部ring、score、recurrence backing按生命周期分配 | RX FIFO→单bank仲裁→SRAM→TX；不因有RX/TX当1R1W | owner/alias/valid length/ring位置，scale同页或静态profile；bank归属、复制/广播与M/V/A/R连接按产品图确定 |
| D搬运/控制 | DMA、tile/digit循环、credit/完成/异常、状态版本及受限页表，8KiB描述符候选 | 制造前命令/完成/错误网和有限队列；先写数据再发布epoch | 引用已有端点/地址/格式profile，运行时换描述符不增加端口/算术/金属；跨块可达/多跳/背压仍付资源 |

仅用S8乘法时，16×8=3个radix128基础积、16×16=9个，加移位/合并/存读；宽乘、整数除法/isqrt、LUT及格式转换不默认为已有能力。原v1库存464KiB、281个S8乘法器只是候选账本，ROM/FIFO/宽功能/物理资产仍需资格。新实验中A20KiB ROM必须与V8KiB区分；不能以8lane声称8次查表/周期。

具体算子映射：QKV/MLP/投影由M分时；norm/RoPE/门控/残差由V；GQA通过共享KV profile和循环适配2/4/8Q，不制造每头专用宏；Gemma local/global主要改变S生命周期/窗口和描述符，不能自动新增两种算术宏；Q35 hybrid需要R语义反馈，但是否独立制造仍未知。不同模型层数/维度是描述符/调度，超容量需合法分块/背压或backing，不能偷偷扩大RAM。

## 4. 已可确定与仍待选择

**可以确定的是合同**：同单位组i32、混合单位显式ALIGN_REDUCE、bias与完整归约先于一次最终RQ；共享GQA的KV格式/profile/epoch；状态单owner/连续history；local/global不同有效生命周期；每个物理传输的位宽/元数据/打包/端口和完成事件。guard失败必须回退/拒绝，不能饱和后仍称等价。

**优先制造前固定的候选内部连接**：MAC局部acc反馈、SRAM单口仲裁、有限FIFO控制、版本提交与出错检测、同一已选择算术中的循环反馈。这些功能义务已有证据；具体tile尺寸、lane/吞吐和gate实现仍待RTL/物理资格。完整归约闭包可以跨物理边界实现，不把合同强说成必须同宏。

**留给产品的连接/映射**：M↔A双向配对、M↔V宽旁路/RQ、各计算块↔S slice、V↔R与state backing、广播/复制/多跳、启用数量/绑定（不超过制造前固定实例数）、银行分配与运行调度。产品确定后只选择制造前已存在的端点和限定金属/过孔，不补有源buffer/端口。Issue55/63物理/适配器由其他成员负责，本任务交合同和证据，不重复其工程。

**尚不能确定的制造边界**：M+A是否合宏、R是否独立、近M RQ唯一性、全路径INT8还是局部ACT16、全部混合归约32或宽回退、真实KV bank/总线拓扑，以及端到端收益。不得把“全候选通过”“全模型整数可用”“物理布线/时序通过”写进本版结论。

## 5. 新输出实验对候选的修正

服务器90048/90049两轮（源码46c0b46e46f786c785489ce8b316bc0a72fd3d28）固定180组A/W/acc，比较6种Y合同共1080条件，每轮410112 Fraction最终码，三科学文件字节一致。沿用已观察的诊断样本，不能事后改写Issue59失败或宣布新独立质量通过。

| 所选down，动态A128/W128 | 原Y8/2xcal | 同物理范围Y16 | 整数row-delta Y8 |
| --- | ---: | ---: | ---: |
| Llama layer0 | 5.394% | 4.811% | 4.926% |
| Gemma layer0 | 3.810% | 2.884% | 3.105% |
| Gemma layer5 | 4.000% | 3.770% | 3.839% |
| Qwen2.5 layer0 | 3.372% | 2.956% | 3.090% |
| Qwen3.5 layer3 | 4.829% | 0.840% | 2.486% |

Y16_same_range精确保持旧Y8上下端点（代码[-32768,32512]、原step/256），不是偷偷扩大动态范围。Gemma q/o在相同范围Y16下仍有原21/5次饱和；扩大到4xcal的Y16或当前整数row delta可消除本批饱和，但有各自范围/存储/计算代价。简单扩大Y8范围反而降低分辨率，不能一律加裕量。

row delta完全由acc/unit/base计算，不读FP评价目标；它是**每个16输出tile的逐行增量**，不是全hidden行统一scale。进入下一矩阵可能形成K16单位，需同样的ALIGN_REDUCE或先转到K128统一单位；Issue64当时未测该后继；Issue66已补完整hidden链，见第9节，不能仍按旧16输出估计。因此保留ACT16和带tile/epoch scale的ACT8接口，暂不把动态delta强固化。在本轮声明的64B外header、32B坐标、16B逐输出指数和16B Y8的packet中，每行1B显式delta使decode物理包128B→192B，与该tile Y16相同；复用已预留字段才保持128B。若坐标已在header、scale驻留，Y8/Y16也可能同为128B，不能外推成任意协议必加64B。扫描/完整tile等待/暂存与后继矩阵16×8的3基础积均非免费。

## 6. 整数attention闭包的新增证据

90050/90051两轮从相同三主测完整GQA采样，56条件均执行成功：QK32全7106560值、PV32全1474560值与I64参考一致；27850个概率Fraction见证。原FP32→S32Q20、KV静态scale、scaling/LUT离线编译仍明确，**此边界之后**QK、S32Q12重定标、LUT、U64 sum/div RNE、P15及受检PV都走整数，尚非完整整数模型或硬件。

相对于同编码Q/K/V、FP64softmax再P15的输出，LUT步1/128最坏新增相对RMSE约0.0747%，步1/256约0.0436%；Qwen2.5 KV8的原约12.50%误差并未被换整数softmax消除，不能用非线性精度掩盖KV瓶颈。两份表为8196/16388B：A20KiB候选可容纳，V8KiB不能原样接收，即使小表也超4B。常量端点旁路压缩表属于需另冻结/证明的优化，不把表字节抹去。

Psum证明现在在这个实际整数归一化候选下得到执行验证，但仍受固定Vscale/合法mask/长度和guard约束。head256 scaling可合入dyadic RNE；head128非dyadic缩放需要显式32×32→64或有成本的S8分解；U64除法/单ROM口是潜在主导资源。A闭包是更有依据的逻辑模板，M+A是否同宏仍交同库存服务/物理对照。

## 7. 同库存attention服务：合宏还不能固化

90056/90057两轮各576调度、96优化配对。比较四种完整GQA组、T128/1024、q1/4、KV8/16、exp II1/8/32；两侧相同16×16 S8阵列、8lane、宽单元、RAM、单读ROM、128bit bus、2KiB FIFO与credit，候选各自选已声明fifo/critical中较优策略。受限pack/transpose、score两读、P15归一化/守卫、所有head/PV limb和consumer均入图。该服务采用portable PV64/O16条件，不偷换为B的PV32数值验收；已发布Q/K/V之前的投影、生产布局、KV追加不在边界。

只改物理标签的colocated_control在96/96配对与split完全相同。colocated_stream仅删除内部M↔A packet header，payload/RAM/同bus/credit保留，模型完成周期减少**0.0833%–0.1675%**。这说明在本轮保守pack、逐头KV重读和64步U64除法假设下，省header不足以固化M+A；不证明所有实现的合宏收益都小，也不是整图/PPA结论。先校准布局/宽SFU/端口，更可能改变本轮决策。C的T≤1024未越Gemma窗口，同shape local/global服务相同；窗口生命周期来自既有真实捕获，不是C的周期对照。独立接收重构96配对、核验3轨迹的依赖/端口/有限credit与4种负例；两轮6科学文件字节相同。

## 8. 最小剩余验证及冻结条件（Issue66后）

Issue64 A/B/C，以及Issue66消费者/整数norm、连续R/conv、原256步诊断已在服务器完成双轮；独立全值验算只覆盖接收前固定的三个长窗见证，其余长条件核二轮SHA，不重复完整模型/品牌矩阵。下一组仅保留尚影响物理归属的分叉。

| 优先级 | 剩余分叉 | 决策所需最小证据 |
| --- | --- | --- |
| P1 | V归一化与RQ/streaming | 冻结同一整数精度/范围，对完整H输入、两遍scale scan、gamma/K128 tile、新A8及所有写读做有限16KiB/1RW/FIFO调度；比较同资源近M与共享V。仅有字节/乘积下界不能选位置 |
| P1 | R范围/提交与物理归属 | 先冻结范围guard、合法重定标epoch或回退，不能掩盖184/193饱和；再公平比较V16、V32+S-shadow及有证明的原位提交，叠加相同FFN/attention竞争。R内SiLU/QK L2norm/GatedRMS/gates仍需整数合同 |
| P2 | M/A及宽SFU物理资格 | 以适用RTL校准K/V pack、32×32/64bit算术、整数sqrt/div、ROM/银行端口；只对剩余一对组织做合法连接/时序/布线，与Issue55/63协调，不接管他人工程 |
| 冻结后 | Phi及端到端 | 冻结profile/映射/阈值后才解封；完整应用质量和同资源整图/物理收益另行验收，失败不事后调参仍称独立 |

## 9. Issue66修订：完整消费者和连续整数状态

[实际报告](experiments/issue-66-scale-state.md)、[数据及SHA索引](../project/experiments/scale_state/results/issue-66/index.json)补充了前述证据。完整down输出H2560→残差→完整RMSNorm→下一QKV投影前16/8192输出，而不是旧16通道孤立down。两组文本校准/评价分开，未重用Phi。以下是可据此收敛的义务与仍保留的选择。

| 边界 | 本轮证据 | 固定的合同/候选能力 | 暂不固定的物理决定 |
| --- | --- | --- | --- |
| M输出→V | 静态8/同范围16均37次sat；tileδ零sat；提前K128每行省128B但norm/未最终RQ的next16误差增加 | typed ACT8/ACT16、逐通道base+tileδ、完整K归约后RQ、范围守卫；不能跨单位直接加 | ACT16统一启用、强制早转K128、近M RQ独占 |
| 残差→norm→新A8 | 整数RMS相同X16误差约0.00005%，计重编码为最高0.05862%；next相对旧桥变化最高0.4975% | 完整hidden统计、alignment/RNE、gamma/epsilon版本、新A8K128单位及发布顺序；sqrt/div/宽乘是显式候选成本 | V16KiB内整行不适配，两遍源读或spill/streaming需公平调度；未证明一定同宏或硬件已支持 |
| R状态闭包 | 新32步S16/D15输出0.644%，S32/D31约0.0567%；同范围长窗仍有184/193次sat | 完整K预测先于delta/update、从新state输出、owner/position/epoch及范围失败协议；S32优先工作参考而非普遍合格 | 固定S32范围、D31必需、R专用模板；不能只看低输出RMSE跳过sat |
| R/conv/入口 | coupled32步输出约0.86%–0.96%；入口clip102/initial14，两种history位宽均存在 | 连续非零history、相同范围位宽对照、输入clip独立于R内部sat；FP SiLU/QK norm/gates边界 | 整条全整数GDN、只提高history bits就消除范围问题 |
| R↔S | V32 old/new共32KiB已无aux；S32全head64KiB，全模型backing48MiB候选 | shadow/commit读写、Vhead状态不别名、跨Vtile的完整head norm屏障、bank/credit付费 | V16与外部shadow/合法原位之间须同资源比较，不凭32KiB标签宣布R独立 |

整数norm候选的对齐行20,480B、mixed输入25,600B均超V16KiB。两遍源读51,200B/row，或显式aligned spill写读40,960B加一遍源；与X16平方融合/物化分别是互斥路线。单口动作下界6084/6404beats并非目标周期。32/64次sqrt/div参考迭代也不是目标时序。gamma+norm行20,480B需分tile/流式，不赠容量。

D15把真实近1 decay中106/512编码成1，D31消除了这一分辨率损失，但同窗S32输出只小幅改善、S16略差，尚无普遍必须D31的证据。S32降低舍入不扩大动态范围；184/193是定义的最终饱和，内核执行成功仍不能称无饱和或模型已接受。当前整数input RMSNorm不覆盖R内部q/k L2norm及GatedRMSNorm。A/R逻辑闭包更加明确，M/V/A/R/S/D六模板的物理数目和相邻预连线仍是待验证候选。

## 10. Issue68：范围协议与物理边界接续（2026-10-24）

[R范围/同资源服务记录](experiments/issue-68-range-service.md)补上因果重定标：当前整数proposal越界时，旧提交态按head做一次RNE右移、unit加一，并完整重试同token；多次逐一RNE不能合并为一次更大移位。state、output、units、epoch、version共同发布，失败attempt不可先更新消费者或history。源S32仍同物理范围，不能靠扩大到任意INT32偷过guard。独立接收确认固定旧256步窗S32/D31两次rescale后完整通过，原193次sat消除；新32步源没有触发，不能视为重定标的新独立质量验证。S16局部误差并未改善；全生命周期、下游gated-norm/SiLU和模型质量仍未验收。

本批需要制造模板保留的义务更具体：R先完整K归约、全group范围guard后才从新generation形成输出，全部V分块完成后共同提交；S/D必须携带单位/epoch/version及失效、重试和代际发布接口。具体把guard/RNE/SFU放在哪个宏仍可选择，但不能删除这些资源或把读写当免费。跨chunk保存所有上述状态已逐码测试，checksum只是软件完整性，不是硬件认证资格。

完整双head S32状态old/new各128KiB，48MiB全模型状态在声明有限EXT中保留，S256KiB还承担其他流，不能把两个整代免费常驻在R32KiB。实际服务候选采用tile16的old/new各8KiB+aux8KiB（R24KiB），或tile32 old16KiB+aux8KiB、new16KiB放S4。失败首次重试还需完整双head clone及坏head重编码。原位方案未证明同样abort/rollback语义，故不进placement主排名。

V完整H2560 mixed sum+unit为25600B，超过16KiB。服务先付原SoA到K128 blocked打包，再完整5120B单位预扫，随后比较两遍源读或aligned spill，gamma与新A8/Ae另计。不能把选了finest unit后的对齐当免费，也不能把旧6084/6404B每行下界说成已经含本次新增预扫/布局成本。

两套各56配置/112完整调度均已双轮及独立接收，每套48对同lane/路由标签对照为零差。tile16本地shadow在两个EXT条件下作为下一轮工作基线；tile32/S侧shadow线上流量更大，norm spill有多字节却同周期的反例。shared8是另一发射粒度，不把其较短周期归成合宏收益。当前S8宽算术假设下R lane接近饱和、BUS较空，下一步先校准宽算术/合法M阵列复用及真实端口，不据此冻结独立R宏或V/R合宏。保留完整guard、两代分页、试算副本、单位/epoch和原子发布义务；不赠整状态SRAM或无回退的原位更新。
