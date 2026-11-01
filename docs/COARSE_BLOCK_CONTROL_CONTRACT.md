# 粗粒度大Block的母控、本地控制与永久绑定候选

Issue151 / PR152；输入研究提交`1cc43a93a0c985587745ceba5e0d8d425d43a843`，读取P1/P2、家族与静态执行资料。叶源固定PR144 `707878621b2add4ed218b8c43df2e95c9a56e2ba`；M/S/T与P1旧源字节相同，R升级资格单列。本稿只提出候选，不实现新RTL、不接管后端或外存研究；正式整合和远端交付状态见PR回执。现有P2局部仿真结果不转移成粗粒度系统通过。

## 1. 主候选与真实层级

母控按**完整子层任务**派发，本地控制按七宏原生操作执行。主候选功能profile为A完整Attention、F FFN、D GDN、H Falcon Attention+SSM混合mixer、X MoE；SSM、router、expert、merge和LINEAR/MST是本地子程序/基础核，不默认作为母控层的公开完整子层API。各模型准确Norm/残差位置、Attention与SSM的汇合、形状和数值合同必须随完整程序接收，不能仅凭profile名称推断。

功能profile数不等于物理Block数。当前主候选允许若干同构island，每个含M/N/E/G/R/S/T及确实需要的适配、NUM、本地控制和存储能力并集；物理数量、是否每岛每类都恰好一个、几何、pin与裕量均未冻结。用于接口说明的上限取**4个island、每岛1个已接收任务、每输入/输出物理端口1条有序传输**，不是面积、性能或模型映射结论。若产品需要更多并行度/端口，必须冻结前扩容和验证。

母控负责：永久选定的完整模型程序、层/子层/分支的依赖，island选择、输入/输出槽预约、启动/恢复/收尾、跨岛事件、全组发布门、错误停止及协调排空。母控不逐拍发每个M/N/E/G/R opcode，也不经过母控转发每字payload。

本地控制负责：从预制本地ROM展开具体native op，选择本地MUX，tiling/循环、tail/布局/数值profile、M输入bank和唯一结果上下文、N统计/EXP/回放、G在途计数、S普通口与loader仲裁/ACK、R候选/本地commit/导出及T批次生命周期。一个共享端口始终只有一个本地owner；本地子程序共享M/S时不能各自并驱。

这个层级减少母控长线上的逐字/逐op控制，但会增加本地ROM、任务接收、存储预约和事件端点；不能从层级名称推出后端更容易或面积更小。母控仍有全局事件/发令扇出，需真实布局、时序、拥塞和时钟复位证据。

## 2. 固定底座与M11/M12各自做什么

| 冻结前共同M1–M10有源能力 | M11/M12永久被动绑定 | 运行时合法变化 |
|---|---|---|
| 母控PC/循环/等待/事件采集；每岛本地FSM、ROM读/译码、所有选路MUX/仲裁/保持/计数、数值服务、buffer、同步/CDC、错误和复位；固定pin/landing、驱动/接收和必要中继；共同PG/CTS | 选择已预制完整模型程序入口、已接收参数表/合法路线与选择bit；跨岛连接已存在的端点 | 固定模型程序内选择A/F/D/H/X中的合法调用；layer/head/tile循环索引，token/length/position、地址、MoE ID、ready/valid等待与错误 |

profile不是每个island永久锁死的一种算法。永久固定的是**完整模型程序、允许调用集合、参数域、路由模板和硬件能力并集**；同一island可随该固定程序先执行A再执行F，或在另一产品执行D/H/X，前提是这些本地程序/算术/路线全部已预制接收。profile ID不能指向尚不存在的程序，也不能通过某个运行时参数跨出已接收语法。

首选母控和本地ROM都在冻结前包含有限产品/子程序全集，M11/M12从常量源/预留strap landing永久选择入口及参数集。selector的有源读取、非法码处理、fanout、MUX和寄存器同样预制。程序参数按layer/head等索引查ROM/表，不把每层scale当同一条常量线。未知新结构不能仅增加family_id得到支持；完整程序编译与ROM容量目前未证明。

跨Block物理边界包括命令、事件和数据端点。推荐母控到各岛的命令/事件形成固定点到点逻辑星形，payload用有限预制端口及profile选路。它们可在允许的上层金属经过被动布线，但**普通push-pull输出不能短接**；所有时分选择、仲裁、fanout缓冲、holding/寄存切片、CDC、CTS和reset分发必须事先有有源实现。M11/M12不能在定制时插这些单元。路由模板及未用端点tie-off必须合法；任何clock/reset的可定制长线都需共同预制驱动/接收与时序合同，不能让各产品补一棵CTS。优先共同固定clock/reset树，定制只选数据/控制合法线路。

这不是用软件互斥代替MUX。即使某一产品只用两个输出中的一个，静态物理接法也只能选一个合法驱动；若同一产品内两源分阶段共用输入，就要预制有源MUX及阶段route-select。

## 3. 最小候选接口：子层任务层与内部核层分开

不恢复每条tensor的通用256bit handle或运行时type/role网包。源op/目的op、元素格式/F/layout、有效tail、数值规则和资源生存期主要由离线程序证据及永久表证明。硬件仍执行计数、地址检查、实际MUX、算术、保持和握手。

以下位宽只是一个可复核的**候选编码/存储算例，不是新增通用控制ABI或已实现接口**。优先让永久表按entry/layer/phase索引给出地址/格式/参数，只传确有动态性的少量变量；完整程序编译可能使编码进一步变化，不能用本算例要求所有子层填统一大描述符。

**子层任务命令算例**：独立64bit ready/valid控制flit，先一个64bit header，再按该entry永久规定的0..1个64bit参数字，包内不交错，全部接收并检验后才启动native工作。header字段为kind2、entry8、job_seq32、epoch8、layer8、nargs3、flags3，合计64bit。RUN/RESUME/CLOSE/CANCEL四种kind只调用预制入口，不加载程序。layer8是当前八样本的候选上限，不等于已支持256层；越界拒收并报错。entry8最多索引256个本地入口，实际entry表/程序字数尚未编译。

主算例只有一个可省略的动态参数字：count32+position32。src/dst/aux绑定及权重、KV、root基址优先来自永久entry/layer表，加上已检查的运行时循环offset/版本选择。每岛按最多16B接收存储预算（header8B+动态字8B）；未接完整包不可发native valid。这未证明所有完整profile只需这一个动态字；额外动态输入先列缺口，不能藏进“aux指向任意描述符”。

若MEM/产品调用确实需要运行时可变64bit src/dst/aux基址，可另评估header后最多四字的扩展算例：src_base64、dst_base64、count32+position32、aux_base64，接收存储增至40B。地址域、相干/ACK/错误语义随MEM尚待研究，该扩展当前禁用且不是默认ABI。native S仍为10bit wholeword口，必须经真实已实现服务检查/转换，64bit地址本身不创造MEM控制器。runtime job尺寸/地址只是固定程序的数据，不是启动装载控制程序。

**数据端点**：候选每方向一个128bit payload端口，valid/ready、fragment_last、valid_bytes[4:0]，共136bit/方向；fragment末包1..16有效字节，其余包16字节。fragment_last只结束当前有界fragment，**不是完整子层结束**；fragment序号、预期字节数与输入角色按固定任务/phase绑定，完整子层还需全部fragment及终态JOB_COMPLETE门。数据类型、端序和数值规则由固定entry/端口/阶段解释，不逐包携带type。每个物理端口一次只有一个预约fragment；不交错、不乱序，命令与本地frame状态绑定。支持多输入operand可按预制阶段顺序串行fragment或增加明确的端口；profile如需同时两源，不能只画一个接口后假设免费并口。128bit是核外逻辑接口候选，是否需更宽/更多口由带宽/物理门决定；不是把原生M A128/B512直接抹平。

**事件端点**：独立128bit逻辑记录、64bit ready/valid flit串行两拍。字段为kind4、status4、error_code8、job_seq32、epoch8、phase8、progress32、detail32，总128bit。kind定义其progress/detail含义，例如当前chunk字节数/序号或首个native错误信息；不承诺一个32bit进度能描述无界tensor。整profile的总字节算术至少64bit并检查溢出，单次chunk大小受真实buffer限制。事件全记录先锁存，valid/data保持到接收；每岛至少一个16B事件槽，母控每岛一个16B接收槽和持续公平采集，不能等某一个任务最终done时停止收其他中间事件。

RUN接收header/args和ready握手只代表接单。默认任务槽直到本任务所有保留phase/output/state义务关闭才归还。RESUME/CLOSE/CANCEL必须精确匹配已保留job_seq/epoch及永久许可的phase；它们走预制控制mailbox且可在保留任务时被接收，不能被“只有空闲才ready”的RUN规则堵死。不得覆盖已保存任务参数；可仅接header的RESUME/CLOSE使用0参数入口，需更新的地址/尺寸先经过独立预制resume参数capture。该mailbox至少另一个8B header槽；若某resume入口需要参数，需另计其最大capture（本候选默认0参数）。

epoch8和job_seq32只是此有限候选的运输标签；它们不是R原生owner/epoch/position，也不提供权限。seq达到最大值先停止新RUN并排空全系统，才能经明确的协调重建进入新epoch；epoch也不得回绕，耗尽后终止或受控全平台重初始化。保留R/N phase或仍有link/MEM响应时不能靠改epoch“消除”旧义务。对不带tag的原生口仍只能按本地顺序保持/排空；MEM晚响应处理取决于尚未设计的平台合同。

内部LINEAR/MST接口另属本地核层，展开native descriptor、bank/fmt/scale、S地址、T words等；不能拿它代替完整A/F/D/H/X任务入口。P2固定fixture的start/out接口既不是上述任务包，也不是完整输入tensor API。

## 4. 六种完成语义与输出租约

| 事件/条件 | 精确含义 | 尚不代表 |
|---|---|---|
| COMMAND_ACCEPTED | 对应完整包已进入保留槽，参数稳定且资源准入通过 | native已执行或tensor存在 |
| PHASE_READY | 指定阶段结果/计数已达到，允许永久程序回访/推进；R/N等锁可继续持有 | 任务结束或新RUN可抢本地上下文 |
| RESULT_SEALED | 本chunk结果完整产生、错误已检查、实际目的存储写ACK完成，所覆盖范围保持不可变 | 跨岛已收到；也不是R/T/MEM全局commit |
| TRANSFER_DONE | 本chunk所有data beat已被对端端点握手接收 | 对端最终S/MEM写ACK；源可覆盖buffer |
| INPUT_STORED／REUSABLE | 对端实际存储ACK并发INPUT_STORED；母控确认该依赖后向源发CLOSE；源释放输出及其余义务后报REUSABLE/JOB_COMPLETE | 任意消费者都已完成；持久state已全局发布 |
| STATE_PUBLISHED | 完整指定state/history版本已保存并通过root发布门，对协作消费者可见 | 输出、T批次和MEM一起原子提交或崩溃一致 |

COMMAND_ACCEPTED通常由握手隐含，不额外占事件记录。PHASE_READY/SEALED/TX_DONE/INPUT_STORED/STATE_PUBLISHED/终态分别使用已定义事件kind；事件表不能把同一个done位复用为所有含义。JOB_COMPLETE必须声明是否可重用、是否partial、保留phase是否已清；母控按其所需门判定依赖，不能见busy下降即调下一任务。

默认存储转发：先按有限chunk预约并完整物化、检查和sealed，再发跨岛payload；目的端先预约其真实输入槽，再接收，写入实际存储并ACK后报INPUT_STORED。输入握手可只进入一个16B holding，不能即当最终存储。源在TX_DONE后保留不可变结果，收到对应CLOSE才覆盖。这个保守选择增加保持与event开销，但给出了错误和复用边界。cut-through或双buffer可另做候选，不由“粗粒度”自动具备。

本候选需最少两个不同完成通路：数据返回/写ACK可独立推进，event/控制采集始终可推进。母控直接接payload会造成中央带宽与hold风险，本方案不采用。

## 5. 反压、fork/join、反馈与死锁规则

1. 接受RUN前，预约全包槽、至少一个event槽、输入holding及真实chunk槽、输出holding及真实chunk槽和必要state区域。母控向消费者先做输入准入，再允许生产者发送；不能将源不可释放的输出放在等待消费者临时腾空间的环中。这里必须检查**物理island复用冲突**：一个producer尚保留任务/输出时，同一island不能再接consumer RUN；逻辑DAG也会因多任务回用岛形成资源等待环。保守默认可按永久程序串行“写真实MEM staging→等ACK→释放producer→再派consumer”；同岛片上保留跨任务buffer只有在实现独立buffer生命周期和空间证明后才用。MEM暂缓时，需要spill的完整模型保持not_mapped，不能承诺1任务槽天然无死锁。不同岛可并行的有限小图也必须同时预留全部必需槽，不能只预留16B holding冒充完整输入空间。
2. 控制/事件进展与data credit分开。母控即使WAIT，也持续公平收所有事件；本地即使等跨岛数据，也不能阻塞既已接受的S ACK、M/N/R应答、G退休、loader A/B/done或MEM返回。普通S响应先捕获再请求下一S访问，不占着一个S响应等另一次S访问。
3. fork使用预制有限扇出/复制和输出租约计数。最小候选按静态消费者表顺序传同一immutable chunk，并维护最多4消费者的4bit stored_mask；每个实际分支INPUT_STORED才置bit，全部需要的bit完成后才CLOSE源。这个mask不创造到四个目的端的物理路线：单个点到点输出只能到已连邻居；多目的需要冻结前的多landing/有源选择、复制或实际MEM中转，未选方案时相关fork仍mapping gap。不能把多个ready输出短接或OR多个take让一字被不同延迟的消费者错配。必要多副本/并发带宽另计。
4. join按固定程序的输入槽和job绑定收齐版本/长度一致的数据；分支SKIP必须显式成为该分支已关闭条件，不等不存在的done。最小候选最多2个join输入，更多输入分解或预制扩容并证明；缺口不从合法目录删除。
5. 图有反馈时须有明确初值/上一版本及至少一个真实可用buffer credit。静态DAG或“有限模型”均不证明无死锁；对保留N/R lease、共享S/T与跨岛反压共同建等待图，再仿真/形式检查。资源不足标mapping gap，缺MUX/phase/NUM/MEM标implementation gap，不改成semantic非法。
6. 同一T旧租约读完并RELEASE后才能BEGIN新批。T→本地计算→同T的新批需要完整保留旧批：候选最坏6144B spool真实成本；loader一般导出在串行S策略下需另计1024B capture，S snapshot/spool计算区也按原合同计，未经生存期证明不扣除。P2未实现这些通用能力。现八样本最大H3072，一个token的H输出S16为6144B恰为整T容量，S32为12288B已超T；prefill还乘真实token数。S虽总16KiB，旧P0计算区仅9216B且还有输入/临时值/状态占用，不能假设全层输出及输入都能驻留。必须按fragment、实际空间和完整子层终态定义处理，不能把fragment_last当整层done。

这些是可执行准入/状态规则候选，不是已经证明的全图死锁保证。所有公平性、最大停顿、不可取消窗口和异常排空都需成为环境假设及独立验收项。拥塞导致的无限外部停顿无法仅靠本地控制器承诺最终done。

## 6. R、全层多tile与发布故障

每个island中的原生R仍只有一个上下文、2048×S32 active和shadow两bank、八lane输出以及24个S32 history。全层D/H任务在本地程序循环中使用它；原生active/shadow不是所有头/通道的全层状态仓。根表按完整递推层标识，当前样本最多32层递推root（Falcon32；Qwen3.5为24GDN），不能把每native tile都误作独立完整token版本。多岛分配由永久layer→island/root表唯一指定；同一layer/token不能在两岛同时推进同一root。

卷积两遍/全组处理合同不因封装而消失：每tile保存op12候选输出→op7 local history commit并等COPY应答→op14导出新history并等实际存储ACK→才OPEN下tile；全组后处理完成后，按old root恢复state，装满各原生所需参数/因子，state EXEC→保存op12→op7 local state commit并等COPY→op11导出新active并ACK。GDN完整128维、SSM完整4096通道Norm必须取得真实完整范围或已证明算法分解，不能用八lane局部Norm代替。

op7一旦接受，COPY窗口不可用op8撤销；R op8无原生身份比较且不回滚已提交active/history。conv成功的pending_history可能在之后state失败时仍保留。本地owner必须按原生guard保护pending阶段、保存输出，并对失败明确commit/revoke/停止策略，不让母控误认所有失败都回滚。

全层候选state/history写privateNext，old root保持不变；完整必需范围实际ACK、数值/下游门通过后才发布根。若只做了部分localcommit而未根发布，next区域脏数据隔离并排空，保留可恢复old版本；是否可重算需数值与外存写语义证明。若root或输出已可见，记录partial_completion并停止，不盲目回放或声称全token原子。R localcommit、T commit、跨岛INPUT_STORED和root publish没有硬件联合事务；固定顺序只能限定窗口，不能创造全局原子性。

state/history payload和双版本容量不放进几十字节命令预算。旧静态root候选每层32B运行元数据、64B永久四基址/stride表，最多32层的1024B动态root记录可作为比较点；粗粒度分片后存放/数量/持久性需重新验收，不能默删。实际GDN每层2MiB/版本、Falcon SSM每层4MiB/版本及history需求仍超单S容量；系统有外存，但MEM控制器/PHY、地址域、容量/带宽、完成/故障和晚响应语义本轮未设计。缺这些服务时完整D/H映射仍gap，不是profile已有。

## 7. 从当前P2变成大Block还缺什么

P2实际有：三叶M/S/T、独立S helper、21×16bit常量ROM、局部循环/128bit保持、真实ACK和T release，有限反压/错误/abort组合已有独立局部RTL证据。它是可复用起点。

仍缺：N/E/G/R及所需NUM的本地集成；五完整子层程序及参数/层表；外部输入/输出tensor与资源准入API；header/args接收和phase/resume mailbox；128bit通用frame边界/tail；多岛command/event端点与mother依赖scoreboard；跨岛stored ACK/CLOSE租约；fork/join/反馈；真实MEM/state版本；所有预制MUX/route模板、buffer、时钟复位和物理视图。P2输入在函数里固定、S地址/EXEC/loader/Twords写死，外部只有start和四S64输出，不能直接包装后宣称已支持完整Attention/FFN或一般大Block任务。

P2 M_STORE四包循环是本地LINEAR出口示例：M op3应答→held_data→S写→S ACK→下一包。它不是未来唯一出口；目的需要S16时可复用M op5等已有op并按已证明数值合同提取/合包，不必一律先输出裸S64再增加通用转换器。P2的abort是协调reset，先前已交给外部的T前缀不能撤回；粗粒度接口需要新增无reset停止/排空/不可取消窗口合同，不能把P2行为直接升级成事务取消。

## 8. 成本和接收门

每岛候选新增transport存储先列清：16B完整RUN capture、8B无参控制mailbox、16B event hold、16B input hold、16B output hold，共72B；母控每岛另16B事件接收。4岛算例仅这些为352B。若启用四参数字地址扩展，增加每岛24B、四岛96B，相关小计448B；当前不默认启用。尚不含两侧控制flit当前拍寄存/序列化计数、PC/循环/参数表、native phase与在途计数、root元数据、chunk payload/spool、S/loader/M/T既有资源、MEM/PHY或物理中继；因此**不能当总预算**。如果实现复用capture或组合读，必须给具体握手/生存期证明再减。程序ROM容量、chunk字节数、port数和island数均需完整程序/映射及后端反馈，不沿用旧2MiB/32KiB预算冒充最低成本。

下一门应先冻结接口/phase事件和资源准入模型，编译两个不同完整产品到同一ROM能力并集，明确每个entry的输入、输出、NUM/MEM与状态要求；再把P2改为可加载tensor数据而固定程序的本地LINEAR核、实现一个完整F/A子层入口及双island传输/存储ACK；独立验证反压、复用、fork/join和异常排空后扩D/H/X。大Block后端表征与跨块线路需和控制/端口预算并行，不等全部功能写完才第一次评估。后端/外存具体实施由原任务边界另定，本稿不擅派负责人或期限。

本稿运行`python scripts/check_project.py`管理检查PASS，以及本目录`check_coarse_control.py`的17项JSON字段总宽/预算算术/候选边界检查PASS；回执见`coarse-control-checks.json`。复算命令为`python -B -X utf8 work/Melodydt/151/check_coarse_control.py --directory work/Melodydt/151 --report docs/COARSE_BLOCK_CONTROL_CONTRACT.md`。这些仅为规格检查；未执行新RTL/SystemC、推理或EDA。不能用候选规格完备、P2局部PASS或模型语法有限替代粗粒度系统、完整数值质量与共同底座冻结接收。

## 来源

- `project/rtl/block_connection_p2/block_p2_mother_rom.sv:19–58`：真实P2 ROM和SERVICE/WAIT；`block_p2_mst_top.sv:155–208`：局部服务、M_STORE和T release；`block_p2_s_ctrl.sv:41–85`：ordinary ACK保持。
- `docs/PHASE2_MST_IMPLEMENTATION.md`、`PHASE2_MST_VERIFICATION.md`：P2实现/实测及未覆盖边界；`work/Melodydt/151/phase2-source-lock.json`：7078786源锁。
- `docs/SAMPLE_MODEL_FAMILY_SPEC.md`、`work/Melodydt/151/family-binding-contract.json`：八样本、十层型、四有限语法与永久绑定；均非已编译完整程序。
- `work/Melodydt/151/static-execution-contract.json`：已有静态候选、S/phase保留、root及MEM边界；其通用字段/预算不照搬为本稿最低硬件。
- `docs/SIX_CONNECTION_CONTROL_SPEC.md:71–126`及`ALL_LEGAL_CONNECTION_SPEC.md`：R/T窗口、全合法边/gap与可回访阶段；本稿不改变语义合法集合。
