# W5-IF：现有核接口、适配缺口与资源账目审计

本轮范围仅为L4内部W5-IF合同前置，不启动L5 RTL。读取已交付路线 `f9a90c845504b198cc3265106e03c67902382ebb` 的control-boundary副本，以及A8 integrated中的现有A8/F8/W1/P2源码；原生锁仍为707。文件SHA、逐端口方向/位宽/声明行和计算值见 [机器审计](../../work/Melodydt/151/w5-if-native-audit.json)。未修改现有RTL、正式文件、GitHub或服务器，未运行仿真。以下事实、proposed接口和未核实物理项分别列明。

## 1. 当前真实host口及本地“mother”是什么

A8和F8的19个信号同名，方向/位宽如下。箭头以核为参照，数值为逻辑信号位数，不是实际M10/LEF/GDS pin、封装pin或布线面积。

| 组 | 输入核 | 输出核 | 小计 |
| --- | --- | --- | --- |
| 时钟/控制 | clk1、reset1、abort1 | — | 3 |
| 输入帧 | in_valid1、in_data128 | in_ready1 | 130 |
| 帧状态 | — | input_stored1 | 1 |
| 启动 | start_valid1 | start_ready1 | 2 |
| 占用 | — | busy1 | 1 |
| 完成 | done_ready1 | done_valid1、done_error1、done_saturated1 | 4 |
| 输出 | out_ready1 | out_valid1、out_data128、out_index10、out_last1 | 141 |
| 合计 | 135 | 147 | **282** |

W1可变MST没有done_saturated，18信号/281逻辑bit；P2 literal MST没有输入帧口，14信号/150逻辑bit。P2在start后用内部literal初始化S，不经过host输入；W1才允许8拍可变输入。不能把P2的start口称为完整tensor任务入口。

P2/W1的 `mother_rom` 只各有16信号/28逻辑bit：start/done、service_valid/ready、service_op4、service_arg10、service_rsp_valid/ready/error及clock/reset/abort。它是21×16bit常量SERVICE/WAIT/END局部顺序器，非芯片母控任务网络；没有跨岛地址、entry、job/epoch、fragment、存储确认或发布接口。A8/F8直接用固定本地FSM，同样未实现全芯片母控。

## 2. 握手、reset/abort和done的真实语义

- 所有核使用同一posedge clk域，reset为高有效同步状态复位；valid/ready还会被reset组合门控。当前没有CDC或物理频率资格。abort没有valid/ready，必须覆盖有效时钟沿，按核内协调reset/cancel处理。
- W1/A8/F8按隐式beat索引接输入；只有每次实际S写ACK都完成才置input_stored、允许start。没有in_last、valid_bytes、长度、地址、role、job/epoch字段。source在in_valid&&!in_ready期间保持data。早到start pulse不排队，持续valid可等到ready，但同帧只接一次。
- busy覆盖首个输入接受、部分帧、stored等待start、RUN及pending DONE；P2无host帧，busy从已接受start覆盖到DONE消费。RUN或pending DONE不能被新帧覆盖。
- 正常input_stored可在RUN及DONE中保持，但不是计算完成；error/reset/abort可清它。成功DONE是在当前核结果已保存、T输出实际被take并RELEASE之后，保持到done_ready。它**不是对端S/MEM的stored ACK**。
- prestart abort丢弃部分或已stored未启动帧而不产生DONE；RUN abort保留一次error DONE；已有DONE遇abort保留原error/sat且ready可同拍消费一次。hard reset取消有效状态/完成，不生成新完成。已接受RAM写或外部已消费输出不回滚。

未来母控RUN可能早于旧核start被接受。因此若RUN已接单、旧核仍在填帧时收到CANCEL，外侧必须用自己的accepted-job状态产生取消终态，不能只等旧核DONE——该DONE按现有语义不会产生。这需要预制mailbox/状态，不能由M11接线补齐。

## 3. 12/16拍数据合同及不能裸接的原因

| 核 | 输入布局与码单位 | 输出 |
| --- | --- | --- |
| P2 literal MST | 固定A/B signedS8整数码，内部8次S初始化写 | 8个raw S64码乘积和，4拍128bit；没有通用Fin标签 |
| W1 MST | 8拍/128B：A8B、B64B，余56B实际写零；B按输出列n-major | 同上，index0..3、last仅3 |
| A8 | 12拍/192B：Q8B、K64B、V64B及56B真零，均S8 Fin7。K offset=8*key+dimension，V=8*channel+key | 8S16 Fin10，一拍16B，index0、last1 |
| F8 | 16拍/256B：x8B、Wgate/up/down各64B及56B真零，均S8 Fin7，矩阵n-major | 8S16 Fin10，一拍16B，index0、last1 |

A8的K/V是已投影的动态操作数/缓存内容，不能称作模型权重。A8尚没有从hidden生成Q/K/V、取完整KV、RoPE/GQA、输出投影或残差的完整A能力。只加重帧wrapper不能把它变成hidden-A子层。

F8的192B权重只是三个8×8 S8小矩阵；Norm gamma当前硬编码1024、epsilon raw1，完整模型可能还需各层Norm参数、量化表/bias等。不能把192B推广为完整F权重容量。现核要求每帧重新送这12个权重beat并收ACK；RAM中可能留着上帧权重，不代表已有独立常驻权重协议。

A8/F8输出虽同为S16 Fin10，F8入口x仍是S8 Fin7。RNE右移3加clip是**有损数值变换**，不仅是拆包；经此重喂旧F8会改变其Norm源与所保存“原始残差”。若未来hidden合同承诺保留上游S16 Fin10残差，必须预制S16入口/残差路径或明确接收新的边界量化profile，不能声称无损串接。通用hidden的H、元素宽、Fin和布局在完整产品中仍未接收，不默认全模型Q10。

未来最小双岛合同可选proposed `COPY_H8_S16_FIN10` 验证核，先验证真实存储/确认；它是待L5实现的核，不是当前已经存在的copy能力。若继续用MST/A8/F8，应明确其入口类型和新增适配，不把128bit相同当语义兼容。

## 4. S/T容量、旧数据和partial可观察边界

| 核 | 固定S预约 | 当前T lease | 正常普通S请求/ACK |
| --- | --- | --- | --- |
| P2/W1 MST | S448..459，192B | 4字/64B | 16=12W+4R |
| A8 | S448..468，336B；462/463不用，实际写19字/304B | 1字/16B | 23=19W+4R |
| F8 | S448..475，448B | 1字/16B | 39=29W+10R |

实体S16KiB/1024×128、T6KiB/384×128保持不变，二者不是共享22KiB RAM。普通S只有一个helper和一个owner，busy只属于loader，不能判普通端口空闲。普通写有回显ACK、没有原生error位；helper rsp_error固定0，TB合成错误不授予存储故障检测能力。

S和T payload不因reset清零；无效周期dout/out_data或holding可保留旧值，必须忽略valid=0的data。S没有初始化有效性标签，权重/输入槽复用须以当前job的完整实际写ACK和外侧有效标志证明。当前全帧及padding实写阻止读旧输入；未来分离供数不能绕过这条门。

现有out_ready只意味着本地输出被接收，最后take会自动推动T RELEASE和DONE，没有等peer stored ACK的接口。A8/F8一拍输出可由新16B保留槽捕获，在peer ACK/CLOSE之前保持不可变，并延迟旧核done_ready/复用；不能仅把out_ready接peer ready就宣称跨岛存储完成。W1四拍若全部消费后才等确认，完整保留需64B；另一候选是利用T保留末字、分开last-sent与final-take，仅在ACK后退最后字，但须单独证明握手/生存期/取消且不暗含重放能力，不能免费假定。

done_error只有1bit，sat也只有累计1bit；没有error_code、stage、partial、已发送/已存字节或持久状态版本。既有测试允许输出已被take后再abort产生error DONE，因此error不代表“没有结果被看见”。外侧可根据自己真正观察的TX/RX/ACK计数给保守partial，不能凭旧核的单error位证明内部写/发布全部撤销。R未接入这些核，未来R多tile发布更不能由当前核的失败语义推导全局原子性。

## 5. 分离hidden与权重所需的预制适配

| 缺口 | 需要的实际外侧逻辑/生存期 |
| --- | --- |
| 任务壳 | 完整RUN快照、busy时仍能收CLOSE/CANCEL的mailbox、独立终态；旧start只在完整帧后生效，不能直接代替RUN接受 |
| 输入分离 | 按永久entry解释hidden/operand，不要求通用大role包；header解析、计数、tail/canonical零、实际S写ACK和session绑定；旧核不理解header拍 |
| 权重供给 | 有界provider或真实存储bank、版本/有效标志、地址和不可变lease；F8小fixture192B应真实存储或由可暂停provider重供，不能凭常量base产生数据 |
| F8重帧 | 若保持旧顶层黑盒，需发x保留4字及12权重字；常驻cache需192B payload（可用新接收且预约的S区域），或者外部provider逐字可暂停并保活。若直接复用原S452..463常驻，则必须新RTL改输入协议/owner，而非外部加线跳过beat |
| A8完整hidden入口 | 仍缺Norm/QKV、KV/cache、layout及输出处理；Q/K/V小核接口与完整hidden profile必须分开记录 |
| 数值适配 | 分别准入S16→S8等舍入/饱和和原始残差保真；复用native合法op可减少额外算术，但不能把E12当RNE3或把MST rawS64裸截成S16 |
| 接收确认与源保留 | RX实际slot写ACK后才storedACK；TX保活直到ACK/CLOSE；数据ready、母控事件、ACK独立进展，不能共享一个堵塞队列 |
| 错误/晚事件 | 预声明session/counter/epoch匹配、重复/晚ACK隔离、保守partial和协调reset/drain；当前T owner0/generation1不是动态job身份 |
| S资源选路 | 新hidden/weight provider不能并驱旧helper；需要预制MUX/owner/仲裁，包含ordinary与wide loader的真实占用关系 |

并发预取下一帧权重需要额外bank和仲裁，不包括在单任务基线。多个hidden源同一目标的时分连接需要真实MUX，静态valid互斥不能替代电路。模型权重是固定程序处理的数据，不等于允许加载新控制程序；全部选路、译码、holding、数值和CDC/中继能力须在有源底座冻结前存在。

## 6. B8 proposed逻辑端口预算

以下与本轮协议草案对齐，只是B8/单时钟/每岛一任务的proposed算例；不是已实现ABI，不推广到完整A/F/R/MoE。

| 每方向/每岛对象 | 位数组成 | 逻辑bit |
| --- | --- | --- |
| CMD flit | 64+valid1+ready1 | 66 |
| EVT完整一拍记录 | 64+valid1+ready1 | 66 |
| data单方向 | 128+valid1+ready1+fragment_last1+valid_bytes5 | 136 |
| stored ACK单方向 | 64+valid1+ready1 | 66 |
| 每岛一data-in/out、一ACK-in/out及CMD/EVT | 132+272+132 | **536** |

536是**岛侧功能端口位数之和**；两个岛为1072，未含母控侧端口、clock/reset、test/PG、权重/MEM端口、strap或M10 landing。跨岛data与ACK的源/目的端在两个岛侧被重复计数，不能把1072称唯一wire数或用来估PPA。

仅为规划，可在“点到点母控星形、两相反定制数据路线完全独立、不复用packing/物理线、每条有独立反向ACK”的假设下算：控制网132×2=264个逻辑net位；每条定制有向data+ACK为136+66=202；两条404；合668再另加基础设施。一般式为132I+202L，I和L/实际端口数均未冻结；不是实际布线根数、layer利用或pin可达性结论。

B8 proposed fragment先用现128bit bundle发40bit header（valid_bytes0、last0，其余清零），第二拍才发16B payload（valid_bytes16、last1）；header不另加专口，但必须新增解析/保持/phase，且增加传输拍数。此定义不能直接喂旧核，它会把header当tensor。ACK独立，不藏在ready里；CLOSE经母控CMD，源释放另报事件。B8 EVT是完整64bit一拍记录，区别于旧控制文档的128bit事件串2拍；旧编码仅留历史算例，不当本轮事实或默认通用ABI。

## 7. 缓冲与寄存预算：枚举不等于最小面积

| 本地proposed记录 | 逻辑存储bit | 必须并存的原因 |
| --- | --- | --- |
| TX/RX payload各128 | 256 | 输入等待实际写ACK与输出等待peer ACK/CLOSE可独立存在 |
| CMD/EVT/ACK-tx/ACK-rx各64 | 256 | busy时仍接控制，事件背压不阻塞ACK，ACK不冒充数据ready |
| TX/RX header各40 | 80 | 各自会话/片段身份保留到对应数据及确认生命周期结束 |
| task binding64 | 64 | 成功ARM准入至REUSABLE握手；与独立拒绝记录并存；不能被新CLOSE/CANCEL mailbox覆盖 |
| 本地枚举小计 | **656bit=82B** | 不是完整CTRL预算或面积下界 |

协议另列13个latched与13个pending事实bit。母控每local还列CMD hold64+EVT capture64=128bit/16B。仅这些payload记录为每岛配对784bit/98B；加26事实后810bit；另加rejectpending1+rejectcode8为819bit/岛配对、两岛1638bit。拒绝原命令复用已计入的CMD mailbox64，不能覆盖live task binding64。lifecycle、TX/RX phase、valid/owner/partial/poison/seen、计数、母控binding/事实/epoch/seq/PC、global lease、程序ROM、CDC/中继及权重/MEM均未包含，必须继续列账。

82B方案显式选择额外RX/TX寄存holding；真实源/目的16B槽仍在内部S，不能用holding取代目的存储确认。若实现打算复用helper/T/S的已有保持以减寄存器，须给所有者、同时生存期、背压、取消、ACK到达时刻及原资源复用证明后再扣除，不能默认“已经有S/T所以零缓冲”。完整hidden/chunk/weights也不由16B holding自动容纳；更长fragment需有界长度/进度计数，位数ceil(log2(Bmax+1))，Bmax尚未全家族确定。

为避免把旧临时预算误作新增接口成本，JSON还机械记录现有clocked module-level reg声明：P2 top142、W1 top149、A8 top230、F8 top360、S helper269、Nctrl666、Ectrl575、Gctrl438 bit（函数组合临时量不计）。加局部mother8后的P2非叶示例为419，W1为426；A8 top/helper/Nctrl为1165，F8再含E/G为2308。这是源码声明账目，排除了所有native内部存储/控制，可能被综合常量化或重用，既不是实际FF数/PPA，也不能不经生存期分析与82B相加或互相抵扣。

## 8. 未知项和合同退出边界

最终岛数、full hidden H/宽度/Fin/layout、完整模型权重与KV容量、地址域/版本字段宽、扩展事件、目标频率、CDC、实际pin/landing、线长/负载/中继、MEM带宽及物理层分配都仍待核实。B8的epoch/taskseq等字段只属于本轮候选，不强加为全产品通用宽度。

固定母控网是f9路线的proposed主候选；当前没有该网络的RTL或物理验收。W5-IF退出只代表所选有界接口/事件/资源表与生产者—消费者时序可互相核对；L5/W2才实现母控与双岛真实stored ACK闭环，W6扩一般拓扑。完整A/F、大shape、TopK/R多tile发布、MEM/外存及共同M1–M10/M11差分仍另行接收。不能把本次静态合同或现有核通过标成全合法连接、无死锁或共同底座冻结。
