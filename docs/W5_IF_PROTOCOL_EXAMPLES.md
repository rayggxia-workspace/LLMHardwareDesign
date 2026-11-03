# W5-IF任务、数据和存储确认生命周期候选合同

Issue151 / PR152，Melodydt；本轮研究基线`f9a90c845504b198cc3265106e03c67902382ebb`。来源为该基线继承的三层互联计划、原生接口合同及现有MST/F8/A8切片。计划自身保留历史输入714cab4，不把历史源码/测试资格转移到新接口。

状态：**规格草稿，待审查；不是接口/RTL/物理已冻结**。本轮仍在L4的W5-IF，只定义可交给L5/W2实施的有界合同与待验证要求，没有新增RTL、运行仿真或访问服务器；在线Issue/PR状态按根任务最终回执核验。[通道及候选编码](../work/Melodydt/151/w5-if-protocol-channels.json)列逻辑通道及一个编码算例；[因果时序例](../work/Melodydt/151/w5-if-example-traces.json)给出按因果排序的成功、背压、故障例，时间点不是实测周期。

## 1. 逻辑合同与实现编码分开

母控通过固定任务/事件网络调度local CTRL；local CTRL独占原生小宏端口，处理cmd/rsp、流拍数、S写ACK、N阶段、R/T生命周期。模型相关数据及配套确认路线由M11/M12连接已预制端点。母控不搬运payload、不逐宏op发令。母控程序来自预制有限ROM/profile与永久产品绑定；host只提供已规定的数据/有限运行变量，不启动装载新程序。

role、数值格式、Fin/layout、参数来源及转换合法性由离线编译与永久profile表确定，不在每包携带通用role标签。运行时仍须保留任务关联、实际路由选择、计数、握手、所有权与错误处理；静态语义不能代替MUX/保持/算术/存储硬件。

规范主体是下文的逻辑事件和资源条件。64bit CMD/EVT/ACK、40bit OFFER复用128bit流是**B8预算候选编码**，不是全产品固定ABI；后续可经等价及生存期证明缩字段、复用holding或改串行化。不能因“全局单在途”直接省掉晚事件隔离能力，也不能把一个64bit记录误作自动拥有相应服务。

所有有源适配、解析、MUX、仲裁、驱动/保持、中继、ROM/译码、clock/reset及需要的CDC都须在共同底座有源逻辑冻结前存在。M11/M12只做被动连线/永久选择，不能补造或修复这些逻辑；多个push-pull输出不能因软件互斥而短接。

## 2. B8最小有界候选，不能代替大模型准入

| 项 | B8候选值与边界 |
|---|---|
| 拓扑 | 1 mother、2 physical islands；两岛具有同一已预制smoke能力并集 |
| 时钟/复位 | 单同步域；无独立时钟、CDC或独立端点warm-reset支持 |
| 任务 | 每岛至多1个accepted active任务；不排队保留第二个任务 |
| 传输 | 全系统至多1个未CLOSE的fragment；任务最多1个fragment、1个128bit payload字 |
| 数据 | 单例为8×S16 Fin10、16有效字节；通用合同的dtype/Fin/layout仍由各自静态profile规定 |
| 存储 | 各岛S中分别预留1字input和1字output；另有真实TX/RX holding、ACK/事件保持和关联元数据 |
| W2首例 | 新`SOURCE_COPY_H8`→`SINK_READ_H8`协议smoke；不是已有A8/F8/MST直接兼容接口，也不是完整模型消费者 |

两种永久路线fixture可分别为I0→I1、I1→I0；不在本首例同时运行双向环。两fixture使用相同有源能力并集，不能通过逐产品generate重综合增删MUX/holding。实际共同M1–M10/PG/CTS一致性仍待L8物理验收。

**ARM预约的是任务全部必需的生存期资源，不只是fragment缓存。** 需要全tensor才启动的消费者，须有该tensor及同时存活src/gamma/weights/state、结果/回放等完整可达存储与供给合同。B8的16B RX holding只能容纳一拍，不能作为H3072、prefill或全模型准入凭据。放不下、缺转换/供数或profile未接收时，在ARM前拒绝或记GAP，不静默缩模型、自动spill或假定无限MEM。

扩展profile中的“参数已存储/可用”指已声明版本位于真实可达存储，并有可独立进展的分tile供给合同；不要求所有专家或矩阵同时驻本地S，也不把它们强塞进hidden帧。B8没有这些参数/MEM流服务，相关真实规模仍不能据此准入。

## 3. 逻辑通道与唯一owner

| 通道 | 方向 | 接收前必须具备的资源/含义 |
|---|---|---|
| TASK_ARM | mother→local | 本地accepted任务槽、完整input/output生存期预约、完成/错误保持与关联表；只接单，不启动计算 |
| TASK_RUN | mother→local | 同key已ARM，所需输入/参数真实stored且版本匹配；接收后由local展开原生程序 |
| TASK_CLOSE_SOURCE | mother→producer | 同key fragment的peer stored ACK已验证，属于本fragment的受保护提交/返回义务已满足；许可释放该fragment，不等于整个任务/native跨fragment上下文均可重用 |
| TASK_CANCEL_PRESTART | mother→local | 仅已ARM但未RUN、未接受fragment OFFER/data、未发原生操作且无不可撤销效果；wrapper自有取消终态 |
| TASK_PUBLISH | mother→local | B8明确reserved/unsupported；不得ARM要求该发布门的profile。R/MEM等发布另行接收，不由枚举名字取得功能 |
| EVENT | local→mother | milestone/terminal错误信息实际保持；母控WAIT时仍接收并登记，不只收当前期待的event |
| FRAGMENT_OFFER | producer→consumer | consumer已ARM、匹配静态路由/预期源key，全部input/RX/S服务/ACK返回资源已预约 |
| FRAGMENT_DATA | producer→consumer | 已接受对应OFFER；每拍实际接收并计数/验证，再由唯一S owner完成目的写 |
| STORED_ACK | consumer→producer | 所有本fragment payload目的S写的真实ACK已消费且尾部/计数正确，才能成功；反向独立保持通路 |

local是普通S请求唯一owner，endpoint/COPY/kernel只经该owner访问S；已接收S响应先take/capture，不能占着它等待另一S访问。loader供数也由明确owner管理。接收/存储ACK与TASK_RUN无关：consumer尚未RUN时，预置接收端也必须能推进。

**控制记录接收不等于任务准入。** CMD valid/ready只表示整条命令已进入local inbox。正确sender须预先知道ARM资源与RUN输入已满足；若仍送来不支持opcode/entry、错误key、错误阶段、无资源ARM/RUN或非法cancel，local在inbox与拒绝详情保持可用时接收并返回同命令key的`CMD_REJECT`，不产生TASK_ADMITTED、不分配新任务、不发native、不改变当前live任务资源。无accepted任务也能返回拒绝；母控将它匹配到outstanding CMD，而非强塞给当前active任务。只在inbox/必需响应容量暂不可用时ready0，返回collector独立前进，不能把无效命令永久挂住CTRL。拒绝期间原CMD字段及reject code/valid保持，不能从另一个任务binding重构。

母控拥有任务/全局fragment预约与有限程序PC；每个local supervisor拥有accepted任务key/错误终态；producer拥有TX payload至有效CLOSE；consumer从DATA handshake开始拥有RX beat，实际S写ACK后建立INPUT_STORED，再由本地kernel消费该输入。不能由多个controller同时认为自己可覆盖同一槽。

## 4. 必须区分的事实和事件

1. `TASK_ADMITTED`：ARM已经接受并预约资源；不是输入完整或计算开始。
2. `COMPUTE_DONE`：本地kernel规定的计算/原生退休已结束；不是对端存储完成，也不自动释放输出。
3. `FRAGMENT_SEALED`：规定payload完整、校验及本地保留完成且不可变；可以OFFER，不是被对端接收。
4. DATA handshake：对端endpoint接收一拍；不是目的S真实写ACK。
5. `INPUT_STORED`：目的全部payload实际S写ACK已消费；组数据可按其静态profile提供给consumer，输入lease仍保留。
6. `REMOTE_STORED`：producer已接收并验证STORED_ACK；重复/错误key不能形成该事实。
7. `SOURCE_RELEASED`：有效CLOSE许可后TX/native输出lease已经实际关闭；此时才能覆盖对应source槽。
8. `OUTPUT_PUBLISHED`：扩展profile的输出/状态发布事实；**B8该event reserved/unsupported**，不生成。B8 stored ACK不被解释为R/T/MEM共同原子发布。
9. `TASK_DONE`：该任务所声明的全部成功义务满足，或已形成稳定失败终态。它不独自证明所有物理资源均可重用；仍看lease/REUSABLE。
10. `REUSABLE`：该任务全部输入/输出lease关闭，原生/传输/ACK无在途，旧完成已交付，本地槽可以接下一个任务。
11. `ERROR/PARTIAL`：第一错误稳定保持；只要已有可能外部可见的RAM写、data接受、T输出或localcommit，就记录partial，不能宣称回滚。

允许合并同拍事实的物理编码，但必须保留上述逻辑区别和依赖。编码表列0..12的任务事实（含未支持OUTPUT_PUBLISHED）以及13=CMD_REJECT；后者来自独立命令拒绝保持，不能只挂在当前task的pending位。每项支持状态在JSON单列；全家族不能靠枚举或64bit reserved空位自动获得额外状态/MoE/MEM语义。

B8候选error_code：0x00 OK、0x01 UNSUPPORTED、0x02 BAD_KEY_EPOCH、0x03 BAD_PHASE、0x04 NOT_ADMISSIBLE（busy/资源/输入不成立）、0x05 BAD_COUNT_LENGTH_TAIL、0x06 INVALID_CANCEL、0x07 DUPLICATE_PROTOCOL、0x08 BAD_ENCODING、0x10 PEER_FAILURE、0x20 LOCAL_GENERIC、0x21 COHORT_ABORT；其余reserved。旧done_error/N/M错误若没有细节，只能映射LOCAL_GENERIC，不能凭布尔信号编造具体算术原因。有效prestart取消用TASK_CANCELLED/error_code0，不伪装成功计算。

accepted任务的first-error一旦非零不覆盖；同拍首次多错时优先顺序为BAD_KEY→BAD_PHASE→BAD_COUNT→DUPLICATE→BAD_ENCODING→PEER_FAILURE→LOCAL_GENERIC→COHORT_ABORT。partial/sat仍对同拍所有已观察事实OR。命令拒绝与accepted任务first-error分开，按unsupported/encoding→key→cancel/phase→admission顺序验证；不因一次被拒绝的新ARM自动污染当前任务。真正hard reset取消旧事务，不能在其后承诺保留first-error。

STORED_ACK成功必须同key、status0、error0、received1、stored_ACK1、partial0且长度/tail/格式正确；status1 FAILED必须error非零，received/stored按已发生的实际0/1记录，不要求写满；可能已经写入或被接受时partial置1。失败即使stored_ACK1也不形成REMOTE_STORED，不允许普通CLOSE成功释放，只能进入失败/协调恢复路径。

当前A8/F8输出被take后，旧T会自行RELEASE并产生本地DONE，不等peer stored ACK；新wrapper须真实保留outspool/源lease，并延迟释放accepted任务。现核prestart abort不造DONE，wrapper接过母控任务后必须自行保存accepted状态及取消/失败终态mailbox，不能永远等旧核done。source egress holding本身是新增资源，不能把旧T释放后数据仍存在当事实。

## 5. 保持、计数、重复与晚事件

所有valid/ready通道都在valid&&ready边沿接受。valid=1而ready=0时，发送方保持valid及全部payload/tag/flags；除合同允许的cohort/hard reset外不撤回。成功/错误终态均保持至消费。接收方ready只在接受该记录所需的完整槽/返回信用已存在时置位，不能接收后才要求对方提供必需空间。

B8任务key为`(epoch16, task_seq16)`，每次新ARM使用唯一seq；fragment key再加`frag_index1`。路由/peer物理身份来自永久表，consumer的ARM保存预期producer seq；不逐拍带runtime role/地址大handle。OFFER与ACK带fragment key。单个OFFER接受至该fragment关闭之间不交错payload，因此DATA可省逐拍key，但RX phase和计数仍必须真实实现。

重复不得再写一次S、再RUN或再释放，但B8**不承诺可靠幂等重传**。已处理的同key ACK可消费后丢弃并记诊断；mother已记录的相同terminal只做去重。重复ARM/RUN/CLOSE、重复OFFER或格式/phase不符的header/data，采取协议故障/quarantine/poison，不自动当成重传成功。特别是`EXPECT_PAYLOAD`看到valid_bytes0的header是phase fault，绝不当OFFER丢弃后继续、也不写S。epoch/seq不匹配不得推进当前任务、槽有效位或内存；保留错误诊断并恢复，不“猜最近任务”。故障后对已接受事务仍有排空/失败返回义务，不能等待从未可能收到的更多数据。硬复位隔离以外，发送方仍保持未被接受的valid直到故障恢复；本profile不含丢包/重发协议。

seq耗尽时停止新ARM，排空任务、payload、ACK、事件和所有旧native响应，达到全cohort quiescence后推进epoch、seq归零。epoch即将回绕时不能依赖“足够大”继续运行；进入维护停机/受控全cohort冷复位，只有证明所有可能旧消息源均关闭才可重新用码。没有外部晚响应隔离证明时保持不可准入，不能自动跨epoch复用。

## 6. 无reset取消、协调复位与失败

无reset取消只适用于3节的严格prestart条件。RUN命令一旦被接受、OFFER被接受或原生请求进入在途，B8不承诺无reset任意取消/回滚；拒绝该取消并保持资源，或依固定故障策略停止新增发令、收尽可收响应，进入poison及协调cohort reset。未被接受的命令若已经valid而ready低，也不能任意撤回；母控应从调度上避免发出将阻塞必需CLOSE的未来ARM。

supervisor与已接单终态mailbox需跨**叶cohort reset**保留：停止新发令→记录错误/possible partial→保持/排空当前返回→同步reset参与native/helper/端点→确认所有valid和在途清除→以原任务key交付失败终态→母控消费并完成quiescence→epoch推进后重新ARM。不能仅reset一个端点而让另一端继续旧流。

真正hard reset若同时清除mother与全部supervisor，会取消旧事务及旧终态义务；恢复前必须全参与者/链路安静并作冷启动初始化。S RAM内容不因reset自动变零，slot-valid/frame marker及epoch必须重新建立。B8没有MEM外部晚返回、跨clock、掉电恢复的证明；这些是扩展准入GAP，不用16bit epoch虚构永久安全。

## 7. 独立进展与禁止资源环

- 母控WAIT只暂停其程序推进，不关EVENT接收。每local的event capture、sticky milestone/terminal事实、ACK tx/rx保持独立于kernel RUN与payload ready；事件槽满不能阻止已预约的S ACK/反向stored ACK先被捕获。
- 母控可串行消费事件，但需公平，不只接“当前期待类型”；至少为accepted任务的terminal/first-error保留记录能力。一次发生多个事实时，使用显式latched/pending位或有界队列，不能覆盖未消费事件。
- 事件发出顺序须满足生命周期，不可盲目按code最小位优先：本task的ERROR/PARTIAL及应交付milestone先排空，再形成稳定TASK_DONE/TASK_CANCELLED；它们被消费后，且其他旧task pending/mailbox已空，REUSABLE才可最后发出。REUSABLE握手前persistent key/detail仍不能改写。这样不会新ARM后从新binding误造旧pending事件。
- pending期间事件字段必须有稳定来源。B8 key/peer存在persistent binding，fragment0、1字/16B等固定profile值可重构，first-error/partial/sat和每个已形成的event mailbox另行锁存；保持中的mailbox不因后续partial事实变化而改写，后续变化另报pending事件。动态多fragment/可变计数扩展须在计数或绑定覆盖前保存该事件的tag/detail/计数快照，不能只留pending位再从“当前最后计数”推导旧记录。
- **先ARM consumer并预约全部存储及ACK槽，再RUN producer。** 不能producer等consumer stored ACK，而consumer准入又等producer TASK_DONE/T release。
- 每岛只1 active任务且不排第二个任务。**ARM与RUN均须满足母控已知的准入前置后才发valid**：ARM需已知REUSABLE/全部预约可用，RUN需匹配任务及全部输入stored。禁止把不可能满足的ARM/RUN valid停在单CMD前端，挡住当前任务必需的CLOSE/CANCEL/恢复；不能依靠“稍后ready”修复错误发令。必需关闭命令信用预留。
- 全局fragment lease预留TX、RX、目的完整槽、ACK返回保持及错误终态空间；持有它时不再等待未预约的同类资源。same-S/同T再入必须先关闭或真实物化，不能在同一被占岛启动依赖其未释放输出的第二任务。
- B8两种fixture各只有一条有向边；一般fork/join、feedback初值、多消费者源释放与多fragment公平性留W6。静态DAG不是资源无死锁证明，本合同给的是待实现约束，不声称已有形式活性证明。

## 8. B8候选线编码与成本口径

逻辑CMD/EVT/ACK各用一个候选64bit flit，valid/ready各1；CMD有效字段53bit、EVT48bit、ACK46bit，其余固定零。具体bit表在JSON，后续产品可另选编码。

数据bundle为128bit data＋valid/ready＋fragment_last＋valid_bytes[4:0]，合136逻辑端点bit/方向。40bit OFFER候选复用同bundle第一拍：RX仅在`EXPECT_HEADER`解释`valid_bytes=0,last=0`，data[39:0]为header、其余位0；然后在`EXPECT_PAYLOAD`只允许1..16有效字节并与OFFER核对。B8是1拍header+1拍16B payload，线拍数2，payload字数1。header不能写入S/T payload计数或占用T的384 payload字；它不是空tensor、dtype或可在复位后随意重同步的标记。phase错误进入故障，不自动把任意零bytes拍当新header。

stored ACK使用独立M11反向64bit+valid/ready，不藏入ready；CLOSE经固定母控CMD，必须等SOURCE_RELEASED事件。每岛一入一出data与一入一出ACK，加CMD/EVT，共`132+272+132=536`逻辑端点bit，2岛1072；不含mother重复计数、clk/reset/PG/测试、MEM/weights、CDC/中继等，也不是实际M10 pin或物理面积结果。

`fragment_last`仅标当前fragment的最后payload拍；`whole_input_last`须由OFFER/永久frame计划的目标fragment数及全部实际stored计数共同确定。B8一fragment两者碰巧同时成立，不能据此删掉大frame完整性义务。

保守holding示例：TX/RX payload各128、CMD/EVT/ACKtx/ACKrx各64、TX/RX OFFER各40、persistent task-binding64，共656bit=82B/岛。另计lifecycle/phase、valid/owner、至少13 latched+13 pending任务事实、命令拒绝pending及error-code（原CMD inbox在拒绝event形成前不覆盖）、计数、error/partial/poison/seen、复位及母控状态。母控每岛另有CMD hold64与EVENT capture64（仅这两项16B/岛），另有task-binding/已见事实、epoch/seq、ROM PC、全局fragment租约及恢复状态。82B/16B不被当成完整控制器或芯片成本；profile参数ROM、source/gamma/weight/state、片上SRAM slot、原叶端口holding及必要物理buffer均另计，未经生存期证明不扣除。

## 9. 成功与故障例、原入口不兼容

[因果时序例](../work/Melodydt/151/w5-if-example-traces.json)成功例使用epoch3、producer task41、consumer task42、fragment0。A的初始输入已由fixture通过真实S ACK建立；B先ARM预留完整16B输入、接收/确认资源；A COPY后保留输出→header/data handshake→B真实S写ACK→独立STORED_ACK→A REMOTE_STORED→mother CLOSE A→A实际release；B再RUN SINK_READ，消费本地输入及ACK→稳定TASK_DONE/REUSABLE。初始fixture不是MEM/host控制器已实现证据；SOURCE_COPY/SINK_READ本身也尚须L5真实RTL。

背压例刻意让B的S写ACK延迟、mother EVENT ready延迟，验证DATA已接受不释放A、反向ACK及S响应独立保留、母控WAIT仍能最终收齐事实。失败例显示header后原生/传输错误或ACK待回reset时，目的RAM可能已写，source保持poison，双方按cohort恢复返回稳定error/partial；无自动重放和无全局原子承诺。

现A8输入12拍是Q8B+K64B+V64B+56B padding，K/V是动态算子输入；F8输入16拍是原X8B+三权重64B+56B padding；MST8拍输入、4拍raw S64输出。A8/F8输出虽为一字S16 Fin10，也不能直接驱动另一核的S8输入帧。缺失的不只是权重/帧：RNE3 clip有损转换会改变原X/Norm/残差生存期，A8也未实现hidden→QKV。新wrapper可保留一字16B egress至peerACK+CLOSE；不能假定免费复用原S468/473输出region，当前顶层没有对外S读口，若保真实region还须实现读取和不可覆盖lease。MST若先取完四字才等ACK，需64B保持；另一待验证策略是分4个16B fragment，每个out_ready受本fragment ACK+CLOSE门，T保留尚未消费字。不能取完64B只留16B却声称可回放全部。多fragment还需扩frag计数/关联及T生存期，本B8不自动覆盖。所有转换/重帧/供数必须单独接收，不能按“128bit相同”准入。

## 10. R/MoE/MEM及真实规模的扩展GAP

R需要不可取消op7 COPY窗口、history/state分阶段localcommit、完整old/next/root和partial语义；本ACK不提供跨R/T/MEM全token原子性。MoE需要TopK ID/score/rank、专家选择与归并、分支未选不等待、宽累加单位及专家供给。MEM需要实际地址/容量/带宽、写完成与持久性范围、故障/晚响应/隔离/恢复。三者不能靠64bit reserved位自动实现，须在共同底座冻结前补完整逻辑/存储/事件合同和成本。

样本Hmax3072时单token S16为6144B，恰T384word，但不含header/参数/prefill，也未确定所有hidden都用S16；S32单token12288B。现Nctrl count<=257且word/index6bit，H3072需384字、H4096需512字，不能只改guard扩范围；H3072的S16 src/gamma/dst合18432B已超过S16KiB。真实模型映射、chunk全归约/回放、状态及外存供给仍GAP。本合同退出只接受所选有界接口、资源和时序自洽，不代表完整模型程序、RTL/EDA或L5已开始。
