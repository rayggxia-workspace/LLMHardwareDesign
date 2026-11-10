# 共享X / group128-S32 的控制适配准备

Refs [Issue250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250)。
本目录是**不可部署的候选服务合同与独立事务轨迹检查器**，不是生产控制RTL、整数计算模型、SystemC周期模型或物理验收。生产RTL没有修改。新增适配器、池监督器、端点和控制线都须实现并验收，不能由JSON字段推导“已有硬件支持”。

**当前产品候选选择NoPool**：`private_s_candidate.json`描述普通S128、两份256B A tile及每P16B earlycopy hold。`contract.json`的共享池及SYS_X是保留的对照合同，不能同时装进唯一首版底座。以下共享池章节用于解释对照和历史准备；选NoPool后删去32KiB共享池及其FIFO/系统服务端点，私有S不扩。

## 输入事实与候选选择

- 数值依据：[PR249 S32台账](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/85fe7989b11a95725c9b1bc6daee085f74a500b8/docs/experiments/issue-248-followup-design-ledger.md)。W8A16、K16×N8、每128项应用FP16 scale并RNE到持续S32/Q16；Mid为S32；必要暂态宽乘积另推导，不保留S128/S64状态。旧PR251的S128部分和合同不能直接执行。
- 共享池依据：[PR243真实pair](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/63089fb910d26ce37ae31a14dd4ef39c80c4ca6a/project/rtl/shared_s/pu_p_shared_pair.sv)及[共享A32说明](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/63089fb910d26ce37ae31a14dd4ef39c80c4ca6a/docs/experiments/issue-247-shared-a32-native.md)。现有是双reader、只读不可变A池、全局64B/拍、每P32B/拍；不支持通用Mid/B/部分和。新三P仲裁、第三组FIFO及新M装载格式尚未联合实现。
- 本候选不复制独立4KiB X/P，不开启会复制私有SRAM的`true_private_RW`。共享池本身新增32KiB是真实容量；三P FIFO、适配器和监督器也要计面积，不能称零面积。
- P/U/C/F/J各只有一种候选实现，仍是独立叶宏、局控标准单元和必要适配器的控制分组。九个组不成为九个大硬框。新增选择、仲裁、scale/RNE、缓冲和控制属于M1–M10有源底座；M11/M12只连预留真实端点。
- 本次登记16个投影上下文/P、257项G小表作为可测试候选，不宣布上下文数量、ROM实现及表面积已经定案。权重缓冲架构由独立联合gate决定。

## 编码、目标与有限资源

保留64位`G_CALL/G_WAIT/G_END`、`L_EXEC/L_WAIT/L_END`框架；新动作是注册服务，不是新增执行opcode。当前PR180准入子集不能等同完整ISA文档表。`contract.json`中的ABI编号和service号只是本候选本地分配，未获生产ABI分配。

执行描述符仍为128字节，通过已有`parameter_ref/parameter_bytes`引用不可变256字节参数记录。记录包含版本、ABI/topology/capacity/numeric/layout标识、完整事务身份和服务参数。native0携带参数schema标签，native1..7保持零。不偷偷复用旧profile保留位。**本目录没有字节codec**，字段能容纳不等于现有局控已会解析。

九个compute group ID为P0–P2、U0–U1、C0、F0、J0–J1。`SYS_X`是共享资源/服务，不是第六种计算Block。给出两个绑定：

1. **本轮候选**：母控`G_CALL`路由到固定池监督FSM；它接收相同task身份和版本化服务描述符，保持完成直到`G_WAIT`消费，不增一颗可编程LC或程序SRAM。候选端点ID9，MC若让九组和此服务同时常驻，需十个有界目标表项。
2. 替代绑定：ID9由独立小服务控制器执行相同有界LC程序。它多出程序存储、取指和局控面积，本轮不选。

两者都需要新增生产接收端，现有`G_CALL`不能凭空调用池。最终是否采用十常驻端点须联合gate批准；当前[母控端口](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/63089fb910d26ce37ae31a14dd4ef39c80c4ca6a/project/rtl/mother_control_v1/mc_ports.svh)只有两resident目标，不能宣称无需修改。

候选MC每端点一条活动task和一份保持terminal；P LC最多四个执行token，其余组一token；池cfg一slot、每P一条LOAD和一个reader控制请求。token不能因超时、错误ACK或后续任务覆盖而释放。若实际需要更多并发或较少表项，必须改容量版本并重新测控制瓶颈。

每P最多一个active LOAD加一个prepared LOAD，两者分别占一份64B派生元数据slot。任务级不可变模板最多256B/P，需计实际驻留/取参硬件成本；不能在每个K128重复读取256B参数记录却把取参记作零拍，也不能隐藏无限描述符预填。模板FSM在本P控制准备calendar上串行派生下一条命令，与其他P的SRAM服务并行，不占池全局读端口。准备、接受、A/B完成、返回保持、retire是不同事件；retire候选为末次A握手后额外1拍，检查器只查先后，实际1/2/4拍准备敏感性尚非RTL实测。

与共享性能候选对齐：一LOAD覆盖row1的K128/A256B、16个128bit容器、四次64B池读、八次32B新M握手。每P四个64B槽的容量包含尚未返回的预约；每个64B的两次32B握手都结束后才释放该槽。下一LOAD可准备但须等上一条retire才能accepted。读tag包含完整身份、P、descriptor generation、K128 group、beat64和half32，禁止把不同row或不同tag的128bit容器拼成K16。本候选不含multirow；不是把旧tiles=4接口标签改成16就完成新M适配。

## 共享对象全寿命与完成事件

```text
BEGIN → FILL(真实逐笔写ACK全部收齐) → SEAL
       → P0/P1/P2各自可多次LOAD，同一X跨gate/up/多输出组复用
       → 各reader END_READ(最后发出的sequence等于计划LOAD总数)
       → RELEASE_REQUEST(关闭全部新LOAD) → drain → RELEASE_DONE
```

SEAL快照包含每P预定LOAD总数，不能只保存三位reader mask。同一P允许在同一epoch中间停顿后再次LOAD；一次完成、当前idle或M完成都不表示X已无后续用途。每次LOAD有单独sequence、基址、长度和对象版本，范围做扩展位宽比较。只有编译/运行时已经作出“不再读取此对象”的确定声明才能END_READ。实际动态分支若不能事先确定次数，应另定义可证明的reader会话关闭协议，不能默认为本静态合同已覆盖。

END_READ允许已有LOAD继续排空，但拒绝后续新LOAD。RELEASE等所有声明、预定计数、被接受的读、FIFO、A握手、LOAD结果保持和返回消费全部结束。否则，旧pair仅按已接受LOAD判断idle的做法可能在第三P或下一个tile尚未发起时提前释放。

三个寿命必须分开：

| 对象/事件 | 真正结束条件 |
|---|---|
| 单次共享A源读租约 | 最后A容器被新M操作数入口真实接受，内部读/FIFO及LOAD返回义务排空 |
| 整个共享X对象 | 所有reader显式END_READ并满足RELEASE排空；不必等待已完成操作数复制的M算术 |
| 本地B及结果/写S租约 | B真实写回执及M读取完成；最终结果保持到目的S每个128bit字真实写ACK，分别结束 |

`P_LOAD_SHARED_JOIN`同时完成共享A与本地B，不以A done代替整个LOAD done。一个8路S32结果占两个128bit字，第二字未ACK不能释放源；NX16的两字输出沿用同一原则。request ready/接单、done_data出现均不自动等于目的stored ACK。

## 新M/G服务与控制归属

`M_GROUP128_S32`带context、连续group index、K尾数、FP16 scale、A scale、bias、数值profile及布局。`raw_group_first/last`是M原始组点积的边界，`projection_first/final`是后级scale/RNE管理的整投影16-context边界，二者不能混用。raw M只需一份八lane组累加器；16份持续S32状态属于下游控制/scale，不假定raw M已有16份上下文。组内原始S32点积与组后RNE后的持续S32/Q16是两种不同语义；每组先转换，再累加，bias只在final加一次，溢出返回错误。本目录只检查事件先后，**不验证数值、暂态位宽、scale/bias细节或RNE实现**。精确向量和实际layout仍是前置联合gate。

PR243旧M的原生op13/14表示另一种累加context协议，不能当新K16/FP16scale服务已经实现。现有shared pool的rows/tiles到旧M装载协议也不能直接套到新M；需实现并验证32B A/拍、group128、lane顺序和尾片重排适配。

`G_S32_SMALL_TABLE`登记表hash/项数与数值版本；不能把旧S16 G直接标成S32。临时S64乘积后立刻RNE为S32不等于保存S64 Mid。其结果done与stored类别分别定义；去S的路径照实等待写ACK。

## 取消、隔离与重新启动

完整身份含generation/job/epoch/object_version及服务ticket；池8bit epoch仅由适配器绑定，不能代替完整身份。同低8位的新epoch也不能接受旧ACK。wrap只允许全局排空后换generation。

依据[现有恢复合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5a691e182466fb4a2d48da7ca31a1ae6ed9156ba/project/control_main64_recovery_v1/README.md)：halt后不再接受新native工作；已接受valid与写义务保持，真实ACK照常消费。超时进入quarantine，仍保留owner和credit；只能显式排空重试，不能强制释放。P、池、适配器须协调复位；不擦SRAM但撤销有效性，新generation/epoch完整重装。失败LOAD可部分写操作数、失败两字store可留下第一字；**没有原子回滚，也不从中断PC继续**，重新运行前须完整重装/重写范围。

## 精确生产修改点与验收顺序

| 改动位置 | 所需改动及验收 |
|---|---|
| 新`project/rtl/mother_control_native/` | 保留旧两resident模块；新profile为九group索引及真实至少四resident任务/terminal/token/event容量，保持G_WAIT精确匹配与派发回压。NoPool不增加SYS_X路由 |
| PR180 native服务适配/任务编译器 | 注册新ABI/service，解析参数，拒绝旧ABI/数值/布局，生成BEGIN至END_READ/RELEASE与context顺序；LC实际源closure须先固定，不能改一个文档就宣布接入 |
| 共享池对照：`project/rtl/shared_s/shared_a_pool32.sv`, `pu_p_shared_pair.sv` | 三reader、公平仲裁、会话计数与全组reset只属于反事实pool实验；NoPool首版不装共享池及其FIFO |
| `project/rtl/pu_leaf_base/pu_p_group.sv`, `pu_p_store_control.sv` | 新M格式LOADjoin、B reuse身份、ACK和部分失败失效；保持true_private_RW=0真实端口争用 |
| 新M group128/scale/RNE/G适配器 | 数值向量、部分前缀、first/continue/final、context持有和第二字ACK；不继承旧M/G资格 |
| DDR及X普通S128前端 | 有限W返回预约、U→3P逐片真实写ACK、X/A lease、cancel/reset；NoPool没有共享池监督器 |
| 顶层资源/端点合同 | 独立宏、LC标准单元和新增主动逻辑计账；真实宏旁pin、静态数据/握手/ACK网并集，P&R与300MHz另验 |

先通过数值/接口与性能gate，再实现生产服务及控制回放；通过取消/背压/错身份/重复ACK/二字提交测试后进入真实SRAM联合RTL；之后综合、P&R、300MHz和端点验收。协议检查器通过不是这些gate通过。

## 本目录检查器的边界与复跑

### 已有可执行候选RTL

- `rtl/bounded_service_guard.sv`：LC内部的两份command metadata与**独立2×32B result FIFO**、并行native/目的提交FSM。首结果等待S两字ACK时，第二native及结果可以进入；满则背压。完整512bit ticket仅用于内部保护/验证，原生宏仍用真实既有窄接口和有限owner寄存器，不是建议给每颗宏新增512bit pin。
- `rtl/private_a_tile_frontend.sv`：真实2×256B寄存器、同kk多M只读重放、planned/issued/completed与END_USE、W_READY/A_READY JOIN、一个S128读在途。copy-prefix只由真实目的写ACK推进，允许逐片生产消费，但不足16个返回字不能宣称A_READY。W可提前完成，错误kk/slot generation/use sequence被拒绝；A槽在最后实际M消费且关闭后释放。取消后已提出S读保持，回执排空后部分A失效；重试须新generation并重装。
- `rtl/early_copy_3p.sv`：一个U普通S128读在途、每P一个16B保持槽，P写真实ACK后更新各自prefix；U预取可与旧P ACK等待并行，但响应只能在有限保持容量允许时接收。没有无限返回缓冲或普通口双端口。32bit tag是本地适配器保存的请求身份，S宏不因此新增tag管脚。
- `rtl/native_s128_mux2.sv`：copy写和A读共用一个真实普通S128口，只有两份owner/tag元数据，无新增data FIFO。使用原S两响应容量，请求被反压时保持选择和载荷，按真实顺序应答恢复本地tag，S不新增tag管脚。
- 原两个testbench仍用保守单事务S模型检查错误身份/取消/迟到ACK。`rtl/tb_native_s_a_copy.sv`另接**原local_s_base及每实例四颗真实bank行为视图**，从U普通口初始化，完成三P复制、逐片ACK放行A读、同kk复用与双owner占用。没有LC程序、DDR、M/G算术或新物理实现。

P新服务不需要旧`FEED_*`端口：A从普通S128读入外部tile寄存器，再以32B供新M。故可候选使用main已验收`local_s_base`，不自动继承旧P/M profile或旧feeder程序。实际多客户仲裁、地址窗、读写响应容量/RTT与物理仍要重验。

`provider_capabilities.json`将P的G32_SILU与C/F的原G16_MULTI分开；C/F保留SiLU/Sigmoid/GELU_tanh/Softplus原数值合同。P guard只登记P_S32 provider，拒绝C/F provider、旧S16、非SiLU新S32函数。R/E/N也不能自动升级S32，未登记的转换和函数不得通过。

### 尚需集成的控制与费用

`bounded_serial_m_guard.sv`是原guard的独立stream候选，原guard端口不变。其RF SOP绑定既有command，在原2×32B结果FIFO预留位置，两个128bit数据flit直接写该位置，末拍捕获与发布同拍；没有额外32B应答装配FIFO。INPUT EOP单独确认，不完成range；CONTINUE无S数据，FINAL/SPILL等待两次真实S写ACK。其它control帧直通native调度FSM，本模块不冒充完整ABORT/全DMA取消协调。`serial_guard_contract.json`固定内部256bit期望metadata、ABI和未覆盖边界。Slurm102169十八次真实local_s_base/原bank测试通过，含INPUT末拍背压、错session/metadata、短帧/缺EOP、错S ACK、取消和SPILL。逐flit/SACK/terminal时间线见`serial-guard-102169.json`。M在该bench中是帧peer，尚非实际M数值或局控程序联合覆盖。

`early_copy_source_router.sv`将一次copy的源绑定到U/P0/P1/P2之一，直到该copy真实ACK排空后才允许释放/换源。`native_s128_mux3.sv`令P的copy源读、copy目的写和A读共用同一个普通S128口，仍只保存两份owner/tag，不增加数据FIFO或S端口。Slurm102150以原四个local_s_base和共十六个SRAM行为bank验证全部四源×六seed×三初态72次；102155以18次检查held offer、错tag、错release key和换源后的旧ACK。逐拍记录和失败史见`generic-source-102150.json`及run-index。这里不包括动态a_shift的提交目录，不能把data ACK当作scale ACK。

旧profile的MC只有两resident slots。新`project/rtl/mother_control_native/`已实现独立九resident/十六token/九event候选及真实128bit传输，程序单测见`work/YUZE-LU/250/control/mc-native/`；母控与新局控的真实PM/128bit程序控制已联合通过102226，尚未联合实际数值native provider/全局DDR队列，新增service guard不代替这些集成。

完整decode约三百万M group不能依赖MC逐group派发大描述符。需要任务级模板和LC/native有限range FSM生成kk/col、W record、context地址及A lease。新MC image-v3已增加有界G_ADDI64/G_LOOP并逐项验证942scope控制展开；LC仍以新注册service FSM运行范围，不免费生成整段FFN；可保留L_EXEC/L_WAIT框架，由新注册service FSM实现循环，但其寄存器/PM取参、准备周期和端口必须实测。**现已用真实新LC程序接入typed P RANGE和root六票record迭代器；整投影/FFN outer仍未实现，不能混称同一服务。**

W input-consumed与result-stored是两种独立ACK。前者须匹配W bank/gen/record/use并在最后真实M操作数消费后释放输入；后者必须用独立结果身份，目的ACK不能误用已复用的W bank generation。旧性能模型曾将Bbank live/free绑结果ACK；提前释放是实现/模型变化，需要重新校准，不能把旧9.223 token/s照搬。其余G/向量S服务的旧64B费用也尚未全部校准为原生128bit路径。

Slurm102100源`20769643f`两套bench各六seed严格`--Wall --assert`通过，补全CMD/请求/ACK/A消费周期CSV。Slurm102110源`057a301f1`实际SRAM集成六seed×三初态18/18通过，完整源、CSV及失败史见`work/YUZE-LU/250/control/rtl-run-index.json`。bank原DELAY=3ns保留，功能时钟10ns；这不是新300MHz STA证据。仅对导入base有意空wide输出和原bank行为blocking赋值使用精确文件级lint例外，候选警告仍fatal。

`native-s-102110.json`记录512B源到三P复制首U请求至最后目的ACK164–169拍，包含有意5+seed拍响应背压；每tile实际16笔S128读，同kk第二次M使用无新读，三次M共24个32B容器。正常native S请求至响应2拍。slot0命令至终端89–94拍、slot1为167–172拍包含prefix/前tile等待，不能当固定计算费。时间线只供native性能重新校准，不外推token/s或能耗。

`private_s_candidate.json`是性能gate中的**替代研究候选**，不表示冻结两套底座：以原预算两个K128/A256B slot从既有S原128bit口预取X，不增加共享池、不复制4KiB X，不开启true_private_RW。A_LOAD可在W_READY前接受，独立W填充与A槽准备并行；M仅在相同job/epoch/kk/slot generation的A_READY/W_READY JOIN后读取。A槽直到第八次32B真实M握手才可释放。X源S窗口仍有容量和寿命，全部计划A片段实际读回后才可关闭；S普通客户与A片段读共用一个calendar，转向代价不免费。若最终选择此候选，则SYS_X和共享32KiB/FIFO一并从硬件清单删除。

`private_a_protocol.py`用一个P的有限两slot抽象检查这项替代协议，包括A先于W预取、S端口争用、错误kk、早释A及取消时保留已接受读。它不是A加载前端RTL，也不证明两候选的性能、面积相等。

`audit_protocol.py`独立检查接受/提交/关闭/排空顺序，不引用生产编译器。它保守地把每P抽象成一个操作数bank，不模拟两bank重叠；GROUP_RNE/B_COMMITTED等事件的真实性需未来RTL监视器证明。部分失败失效及字节codec是待实现项，不能把本检查器正例当已有错误恢复覆盖。

按项目规则在Slurm执行：复制本目录到授权远端目录后`sbatch --export=ALL,CONTROL_SOURCE_DIR=/absolute/source/directory slurm.sbatch`。采用c64 6×10分配，六个独立协议case分片；每片只有一Python进程，报告实际CPU秒，不人为填满核。输出包含每例接纳/拒绝原因、source/contract SHA和Slurm身份。它不产生token/s、功耗或面积。

`native_lc_contract.json`规定独立的新LC profile。Slurm102217六seed×三初态18PASS：真实1KiB mutable PM、352字节boot CRC、20次header/table128bit读取和3次64bit取指、实际两64B DDR fetch/124cycle CRC、零复制typed P decoder和六票range。已修复并增加pre-boot session提前烧版本、无效config误撤认证、非零CANCEL参数负例。services2/3明确拒绝，INPUT不满足L_WAIT。

Slurm102226又将实际16KiB SRAM母控PM及真实四flit128bit CALL/return接入上述局控，18PASS。每trial四CALL/一CANCEL/四真实LC terminal，验证普通/head范围、service2拒绝，以及错误源返回触发MC真实CANCEL而不是释放P owner；held range offer与其完成未排空时不能全局结束。LC91次PM读取，MC56次PM读取含14次host readback。首成功scope CALL EOP到return EOP224–229拍含有限record peer，不是M执行时间。完整周期/包SHA/失败史见`work/YUZE-LU/250/control/native-lc-control-102226.json`及run-index。

此联合仍用finite record-completion peer，未声称真实M/G/量化/SACK数值路径、wholeFFN outer、全局DDR调度、五类provider、物理300MHz或整模型token/s已经通过。实际`bounded_serial_m_guard`只有一个native active，第二command可以预存且第二计算可重叠首SACK；它尚不能在首RF EOP前提前发第二EXEC，不能套用leaf裸pending理论II。
