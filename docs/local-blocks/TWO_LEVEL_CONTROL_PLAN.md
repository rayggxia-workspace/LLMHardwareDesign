# Block 组网与母控／局控综合方案 v0.2

2026-11-05 13:27，Asia/Shanghai（UTC+08:00）。负责人 Melodydt。[Issue179](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/179) / [Draft PR180](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/180)。R6 基线 13e577c54c3042ecd139461db03e7f4a662643c7，设计来源 PR176 08f2ea20。

本方案把 Block 组成、四类互连、两级 ISA、程序装载和执行串成一条完整路径。v0.2 是文档方案版本，**不改变 ISA v0.1 的机器编码**。[完整编码合同](CONTROL_ISA_V0_1.md)、[机器规范与参考工具](../../project/control_isa_v0_1/README.md)、[容量研究](CONTINUATION_RESEARCH.md)分别保留详细定义。关联工作的在线状态固定在16:25的[来源快照](../../work/Melodydt/179/control-summary-sources.json)，不是服务器实时监测。

### 持续执行与文档约定（2026-11-05）

用户授权逐步完成R3、R4和R5，每完成一步即增补本Markdown并更新同目录固定名称TWO_LEVEL_CONTROL_PLAN.pdf，不新增重复方案文件；实现、测试和证据文件可按任务需要维护。RTL及控制模型仿真全部放在获授权服务器，文档渲染与静态检查可以在本机执行。
2026-11-05用户进一步明确允许触发额外额度；继续授权的R4全部工作。任务保持真实状态；未配置聊天结束后的自动监测。

### R6.1 任务 IR 与目标合同（2026-11-05 13:09 CST）

新增[任务 IR](../../project/control_r6_v0_1/README.md)和机器可读目标表。当前路线为 host255 到 LC0（边11）及 LC0 到 LC1（边12）。每个局控有一个 RAW16 对象和一个在途服务。任务输入声明三端镜像 ID、S 地址、两段传输、存储 ACK 依赖、消费者 READY 与母控完成等待分组。三端沿用 R4 的 ABI 65537、拓扑 393400001 和容量 profile 0x17630001。

两份样例使用联合等待和分组等待。分组样例包含 16KiB 私有 S 的最后一个 16B 对象，另一个样例覆盖不同 bank 和局控令牌顺序复用。静态检查准入 2 份样例、拒绝 18 份非法输入，并确认重新排序对象与传输声明得到相同的图。覆盖非法路线、越界和未对齐 S 地址、缺 ACK 或循环依赖、令牌冲突、非法寄存器及完成信用丢失。PR176 仍为 08f2ea20。R6.2 将从 IR 组装三端镜像，R6.3 验证实际服务器执行。

### R6.2 三端程序镜像生成（2026-11-05 13:14 CST）

编译入口从任务 IR 生成母控、LC0 和 LC1 的小端二进制镜像，打包到现有装载清单结构，记录 IR、目标表、清单和各镜像的 SHA-256。母控先调用消费者，取回 READY，再调用生产者。LC0 等到首段 RX 完成才执行 TX，随后等目的端确认才释放对象。末尾完成等待由 IR 的分组决定。

两份[生成样例](../../project/control_r6_v0_1/README.md)通过现有镜像和 bundle 准入检查。联合版母控为 5 条指令，等待掩码 0x14。分组版为 6 条，连续等待 0x40 和 0x80。LC0 与 LC1 镜像分别为 496B 和 432B，母控分别为 224B 和 240B。重复生成的文件逐字节一致，重新排序对象和传输声明后三端机器码一致。[构建索引](../../work/Melodydt/179/control-r6-build-index.json)记录大小、镜像 ID、输入输出 SHA 和编译环境。实际 RTL 联跑进入 R6.3。

### R6.3 独立检查与服务器镜像联跑（2026-11-05 13:27 CST）

独立检查器从三端镜像字节解码，核对原始 IR、manifest 和 SHA，检查 S 对象地址、端点、服务令牌、READY 值及母控完成分组。现有装载准入接受 6 份已重新计算 SHA 的变体，新增的 IR 对照全部拒绝，覆盖合法但错误的 S 地址、传输边、局控令牌、READY 标量、母控寄存器和等待分组。服务器重建两套镜像与 R6.2 交付逐字节一致。18 份非法 IR 按预期拒绝。

| 服务器场景 | 实际观测 | 周期 |
|---|---|---:|
| 联合等待连续两任务 | 2 个成功结果。LC0 地址 496，LC1 地址 8192 | 2181 |
| 分组等待与返回背压 | 2 个成功结果。LC0 地址 16368，LC1 地址 144。母控分别回收 0x40、0x80 | 2506 |
| 分组等待丢失发送 ACK | 目的端已存储。母控进入隔离，成功结果为 0 | 5233 |

三例合计 9920 周期和 15 次真实 DMA 描述符完成。实际母控、双局控、双私有 S、DMA 及双向 FIFO 执行生成的镜像。观察器检查三端程序装载和读回、READY 与调用参数、各服务的原生 S 地址、传输数据、ACK、信用释放和终态。硬件目标限定为 RAW16/P 的两条既定路线、每块一个对象及一个在途服务，外部存储使用 64 字有限测试对端。

作业 97286 在 node27、debug、4 核完成，退出码 0:0，耗时 11 秒。源码快照 aed997981c52576e52524471c60db1a4bc66cb85，R6.2 基线 76e301eec6ed7536f763ebab8bc2270f10939ff5。Python 3.10.12，Verilator 5.042，G++ 11.4.0，Singularity 4.3.4。核验 162 份源码输入、17 份归档证据及 9 份装载字序文件还原的镜像。结果包 SHA-256 为 3c0144fd5af0d2fc798fdbb708f81a7a3662cba39afec75399a8aa43dccdae0a。[验证索引](../../work/Melodydt/179/control-r6-validation-index.json) · [RTL 报告](../../work/Melodydt/179/control-r6-rtl-report.json)

### R4.4 当前进展：协调复位与重新准入（2026-11-05 12:53 CST）

R4.1～R4.4当前有界控制研究步骤全部交付，等待独立审查／合并；不是完整Block或生产硬件资格。新增可综合cohort_reset_controller，按RESET、QUIET、RELOAD、RUN、POISON顺序控制复位及准入。8bit成员位0..7依次为MC、LC0、LC1、适配器、各S仲裁／feeder、DMA、双向CDC FIFO、外部响应队列。RESET_REQ携带严格递增的32bit sequence／generation／epoch；ACK带sequence／epoch和非零bitmap，拒绝旧身份／重复位。至少4核心复位周期且所有成员确认后才解除reset，额外连续3个quiet周期后才进入装载；缺ACK不超时放行。运行错误立即撤销准入并保留隔离，只有新的协调复位请求才能丢弃旧义务。

实际复位线覆盖母控／两局控、两个RAW16适配器／DMA bridge、各私有S及feeder、真实DMA、请求／响应FIFO和外部peer队列；PM响应槽也清空，payload与PM数组内容保留。loader随后对三份完整镜像重新WRITE16／实际READ16逐字回对／VERIFY／PREPARE，generation匹配、三端prepared和provider quiet才统一deploy。旧镜像有效性和任务／对象资格失效，不能用残留RAM内容替代重装；新epoch内连续两个job保持task_sequence递增，cohort复位后序号从1重新开始。

ACK在本集成中来自可信管理测试wrapper：实际观察至少8个核心周期、至少2个外部时钟复位边沿及各provider公开返回口为空后才发送全成员证书。协调器RTL检查证书和装载门，**未实现生产管理帧serializer、复位树或真实HBM／M／G计算provider的ACK传输**。额外quiet周期不是任意无tag旧响应的数学证明；生产provider必须保证本cohort之外也无旧响应可进入。当前实际实例集合只覆盖RAW16传输服务，M/G活动计算、完整Block、物理reset/CDC及MTBF仍须外部集成验收；不从本轮仿真推广资格。

服务器97280已通过17个场景；随后独立checker补强“局控成功终态晚于真实服务ACK、母控结果晚于两端终态及信用释放”，RTL完全不改。最终97281／mdt-r4179／node27／debug／4核COMPLETED0:0、17秒：6/6实际cohort复位／重装集成、11/11协调器RTL边界、4错误轨迹突变拒绝。集成共24048采样边沿，包含正常完成后复位、外部STORE响应扣留、FIFO持有旧响应、半装载禁止准入、DMA坏物理ID sticky poison及TX ACK丢失后的恢复；每例新generation2／epoch2下实际完成job8、job9。4次从S的独立原生客户口读回已提交旧数据，确认payload保留；旧镜像有效位／旧响应清空，全量新写后传输使用新job数据。边界测试覆盖缺／旧／重复ACK、不静默、缺装载／半装载／旧generation、旧epoch reset及运行故障；四突变为缺成员、半装载准入、旧START epoch、旧结果epoch，均拒绝。

最终实验commitc53d773000466aa9d33814afb35e34e37642f4c1，输入包SHA e930c68ff402d7a91d40b06cfb44772fd8561926d61b53a2f70458cd54a225f7，证据包SHA 68281a51fd9ca2a41b54041ede96d8c898805b23e2ce60d96e0055b43fdcbdbd；149输入源及26输入／输出／日志逐项核验。前次97280的148源／26证据同样核验，只有README及独立checker与最终源不同；未重复计场景。[实际复位报告](../../project/control_r4_v0_1/reset_report.json)、[两次作业证据](../../work/Melodydt/179/control-r4-reset-evidence.json)及[可复现命令](../../project/control_r4_v0_1/README.md)记录版本和边界。服务器目录/public/home/yuzelu/Melodydt/issue179-r4-real-ecd6f49/r006，源码source，日志slurm-97281.log，结果results/reset；当前无未结束作业，无自动监测。工具同R4.2／3，镜像完整SHA仍待核实。

| 本轮验收组 | 实际通过 | 资格范围 |
|---|---|---|
| R4.1 来源／接口静态检查 | 14/14 | 不属于RTL功能场景 |
| R4.2 真实私有S集成 | 10/10 | 实际MC／2LC／2S，有限route |
| R4.3 真实DMA集成＋桥接边界 | 12/12＋10/10 | 实际DMA／2FIFO；边界bench用显式peer |
| R4.4 协调复位集成＋协调器边界 | 6/6＋11/11 | 可信provider证书和实际全量重装 |

本轮定义的49个RTL场景最终49/49通过（100%），不是覆盖率或完整系统通过率。各阶段错误轨迹突变为8／8／4，20次均拒绝；旧173软件检查、164既有RTL场景及R5软件模型保留原证据，本轮未重跑或重复计数。两次R4.3失败分别为参数索引告警、bench timescale缺失，记录保留，不计作最终全量成功。未执行综合、STA、物理／功耗、完整数值模型或全ISA硬件验收。

PR176开始及每阶段／上传前仍08f2ea20，正文和三类讨论未变；本分支已含其全部提交，无新差异需要合入。PR178 cdbb3d53、PR182 24e20d13的6份依赖RTL保持原blob。每阶段分别更新原Markdown及同名PDF，并通过原任务分支／PR180交付；R4.1 commit179c1f79，R4.2 62148314，R4.3 5886269a，最终R4.4 SHA见PR回执。Issue179整体in_progress（R6／R7及通用能力仍待），Draft／待指定审查人／未合并；登记PR5 pending，board.json仍404且缺Projects条目工具，看板unverified／同步pending，管理员待指定。按当前授权本轮停在R4补强完成处，不自动开展R6／R7。

### R4.3 历史交付：真实DMA、双局控与私有S（2026-11-05 12:33 CST）

新增可综合raw16_dma_bridge，与R4.2适配器串接；实际母控、两局控、两私有16KiB S、PR182 hbm_group_dma及两份异步FIFO共同执行既有二进制。DMA配置1组／2S／8槽／每S单信用、单外部channel；核心与外部时钟以5ns／3ns半周期建模独立时钟比例，不是300／500MHz时序资格。P的RX／TX客户仍2／3，实际S完全由DMA驱动，无行为RAM代替局部S。外部存储是64×128bit有限native协议peer，不是AXI、JEDEC HBM或PHY。

本研究route使用DMA外存窗口：host输入先DMA LOAD到S0；S0真实读后DMA STORE到外存，再由消费者DMA LOAD到S1，最后才确认目的收存及返回源ACK。窗口地址由适配器外部提供，本fixture为40bit(job×64)、源TX／目的RX用+16；完整32bit job不截断，有限peer只验job7／8。route payload用于和DMA实际S写响应比较，不把它直接写入S。该路径检验真实DMA完成语义，不能当成已实现的M11/M12直连或完整网络。

每S一份141bit完整block／kind／token／service_sequence／job／epoch／task_sequence映射，与16bit单调tag分别保存。结果待接收时上下文不变；tag耗尽隔离且不回绕。LOAD须观测真实S写响应，STORE须观测真实S读及外部写响应，之后还要收到匹配tag、status0、word1的DMA completion才向局控适配器完成。错误字数／tag／过早完成／重复原生响应／protocol_error都保留上下文并poison；外部status导致DMA error3／0确认字，未伪造S写或局控ACK。错误物理ID使DMA sticky protocol_error，整个cohort撤销部署而隔离，须协调复位。

最终97279／mdt-r4179／node27／debug／4核COMPLETED0:0、17秒：12/12真实DMA集成，18759采样边沿、25个成功descriptor；另10/10桥接RTL边界（显式有限DMA响应peer）及8项错误轨迹突变全部通过／拒绝。覆盖连续job、READY先行、全包信用、两端不同task_sequence、返回背压、实际S与外部存储数据、双向CDC包守恒、外部错误／坏物理ID隔离；桥接测试专测32bit高位身份、40bit外部地址、16KiB末字、descriptor／result保持、错误tag／word／status／提前completion、重复S ACK、标签耗尽及admit门。独立检查器逐项关联descriptor、原生S、两端FIFO包、外部ACK、DMA completion和局控数据事实；旧控制checker不改。

97277失败于SLOTS2触发上游固定3bit索引告警，改为默认8槽而不关告警／不改依赖；97278的12集成已通过，独立桥接bench因新增模块缺timescale编译失败，补声明后97279全量重跑通过。139输入源、最终65份输入／输出／日志及两失败索引SHA已核；实验commitd0f029329b86257368b3196678efeda9fc31b477，输入包639b959d430a381ee154f5005a5b36a7c803d12a1824809c6e2b52132837cbf6，证据包6db8dd269cd8e3ff4e75c2c9578a5d3e30beca48cce80cb3062c43fe9d59f745。工具与R4.2相同，镜像完整SHA仍待核实。[实际报告](../../project/control_r4_v0_1/real_dma_report.json)及[三次作业证据](../../work/Melodydt/179/control-r4-dma-evidence.json)保存实际命令／输入输出版本；服务器目录/public/home/yuzelu/Melodydt/issue179-r4-real-ecd6f49/r004，日志slurm-97279.log，结果results/real_dma。

PR176仍08f2ea20，PR178／182固定版本未变化；R4.3有界真实DMA控制门通过。下一步R4.4实现cohort协调复位、旧响应flush、全量重装及新generation／epoch重新准入；RX-close、一般死锁自由、完整Block／数值／物理仍不在本门内。原方案／PDF原位更新，整体Issue in_progress，Draft／待审查／未合并，登记pending、看板unverified／同步pending，无后台监测。

### R4.2 历史交付：实际局控与真实私有S（2026-11-05 12:16 CST）

新增可综合lc_raw16_s_adapter，复用原MC／LC、配置PM和旧独立控制checker，替换整个有限payload provider；实际实例化两套PR178私有16KiB S及仲裁／feeder，未改6份依赖RTL或控制核心。P的RX走client2、TX走client3，普通服务每端一份上下文；适配器没有payload RAM，RX等真实S写响应才给route收存确认，TX读取真实S。真实S写响应／读响应与局控数据事实逐个对应，ACK发送、源ACK接受、对象valid／WAIT／DROP和母控结果继续按原检查器交叉验证。feeder实例在本轮未发计算装载，M／G数据通路不是本轮测试对象。

服务器作业97276／mdt-r4179／debug／4核／node27，COMPLETED0:0、52秒；10/10真实S集成场景通过，16531个采样边沿，17次真实写ACK、8次实际读及1268个响应背压边沿。覆盖正常、强背压、无reset双job、R7高位scalar、返回背压、受阻CALL独立返回、READY前错误、错误后两端不同task_sequence再次执行、缺TX ACK及RX不可关闭隔离。原4项网络突变及新增4项原生S错误轨迹（删ACK、错写ACK、背压数据改变、提前收存事实）全部拒绝。最后两种场景保留传输义务并poison，不伪造RX-close或成功。没有修改旧checker以接受新结果。

实验源码commit47271c38001158b3174a16387b9ffec0913993e1，输入归档SHA-256为7ca7d2bb1cf5dd5038ca1ad8070769f64c871974ffbb86eeadebfd76d1e79c35，证据包SHA为d517d3920bed55bf64e25755dff960d8ac6da32d0edc5178ef8c02780dfa53b4；130输入源及45份输入／输出／日志全部核验。工具为Verilator5.042、G++11.4.0、Python3.10.12和Singularity4.3.4，镜像orfs-26Q1.sif完整SHA待核实（未执行大镜像哈希）。[实际报告](../../project/control_r4_v0_1/real_s_report.json)及[证据索引](../../work/Melodydt/179/control-r4-real-s-evidence.json)记录实际命令和文件SHA；独立实验commit与PR提交不同。

服务器目录/public/home/yuzelu/Melodydt/issue179-r4-real-ecd6f49/r001，日志slurm-97276.log，结果results/real_s。PR176仍08f2ea20；R4.1依赖冻结继续有效。R4.2真实S控制门通过，不代表完整Block、真实M11/M12、数值、CDC或物理验收。旧164 RTL／173软件沿用原证据；本轮10个真实S环境场景单列，不重复计入旧10个有限SRAM环境。下一步R4.3接真实DMA和双向CDC FIFO，再R4.4协调复位／全量重装。原Markdown／同名PDF继续原位维护；Issue整体in_progress，Draft待审查／未合并，登记pending／看板unverified，未配置后台监测。

### R4.1 历史交付：真实 provider 接口冻结（2026-11-05 12:03 CST）

本轮按用户新授权推进R4.1至R4.4；历史第13／14步只通过有限peer控制门，现补真实私有S、DMA及协调复位。PR176仍08f2ea20，PR178固定cdbb3d53，PR182固定24e20d13；后两者open／未合并。将6份原始RTL按原路径逐字纳入本分支，只读依赖，不修改其设计；来源commit、Git blob及SHA-256见[机器合同](../../project/control_r4_v0_1/contract.json)。PR178三种P4／N4／N5是16KiB私有S配置，不是三个完整Block；P的32KiB仍是候选。当前5类完整Block交付数仍为0，本分支不承担完整Block实现。

私有S普通口128bit、10bit字地址，16B对象地址须先校验64bit byte base低4位及16KiB范围，再转word地址。P的M／G／RX／TX客户号0／1／2／3；N4普通计算0／1及RX2／TX3，N5普通计算0／1／2及RX3／TX4。普通口同一时刻只持有一份命令／owner，响应背压期间不接受下一普通请求；feeder另有真实共享bank仲裁。请求接收只预约，真实写响应才代表写完成，写响应数据为已存数据，TX须读回真实S。局控到服务适配器以及适配器到私有S固定预连；这些控制线不依靠M11/M12生成。跨Block的route仍是研究传输合同，真实M11/M12／串行flit不在本轮验收范围。

DMA接入保持现有ISA，RAW16的一次服务只搬一个128bit字；外部地址40bit、局部字地址10bit、word count11bit、descriptor tag16bit。适配器每S保留一份完整block／job／epoch／task_sequence／service_sequence／token／kind上下文，tag仅索引，禁止截断32bit身份；同cohort内16bit tag递增不回绕，耗尽须隔离并协调复位。LOAD须等真实S写响应，STORE须等外部写响应，completion必须核对tag／状态／确认字数。错误2为描述符拒绝、3为外部响应错误；protocol_error是持续隔离条件，写副作用不回滚。

协调复位域必须覆盖母控、两局控、适配器、各S仲裁／feeder、DMA、双向CDC FIFO及外部响应队列；只复位局控或DMA不足以排除无tag旧响应。S reset保留payload，清owner／持有响应／feeder，控制对象valid及旧PM资格必须失效；所有可信provider完成flush／reset并确认、额外静默、全量重装／实际读回／VERIFY／PREPARE、新generation／epoch之后才可重新准入。没有确认时保持隔离，不用timeout伪造完成。后续外部存储为有限协议peer，不能把它的flush证据推广为真实HBM控制器资格。

本步完成6份依赖来源和关键端口静态检查；管理结构通过，尚未启动本轮服务器RTL仿真。既有164个不同RTL场景与173软件检查沿用旧证据，不重复计数。下一步R4.2实现真实S适配器，验证写ACK／读回／背压／连续任务；R4.3扩两局控及真实DMA，R4.4实现复位与重新准入。每步继续原位更新本报告和同名PDF。Issue179整体in_progress、PR180 Draft／待指定审查人／未合并；登记PR5 pending，看板unverified／同步pending（缺board.json和Projects条目工具），处理人待指定。

### 第15步历史交付：五类控制profile与非零状态（04:43 CST）

**R5有界控制研究产物已交付；新增profile仍是candidate合同／软件模型，未扩展现有RTL资格。** 新目录control_profiles_v0_1保留既有ISA v0.1的128bit指令、操作码及九类记录，不修改P注册ABI。研究镜像使用未分配给硬件的native_abi_id／capacity_profile_id=0x17950001、topology_id=0x17950002，deployable=false；当前P RTL只接受ABI65537，不可直接装入这些镜像。P=M/G/S、U=N/E/S、C=R/G/E/S、F=G/E/S、J=E/S/T，mask分别41／38／60／44／100，未知服务或不可达资源被拒绝。表内路线只是candidate可达性合同，不能生成不存在的M11/M12导线。

软件控制器从WRITE16／实际READ16回对的二进制按PC取指，任务／对象／128B执行描述符逐16B读完；G_PARAM等待实际参数响应，G_CALL锁存GPR，L_ARG读锁存参数。已验证母／局控前向BRANCH、有限回跳LOOP、MOVI、ADDI有符号立即数及溢出拒绝、零计数／步数上限。模型最多3局控／2全局任务，每端1个PM、1服务／token、1返回槽、1个16B scratch、最多8holding channel；S地址上限16KiB但仅模型化16B对象，外部状态handle最多16个。model tick不是硬件周期；N/E/G/T/R仅处理opaque版本标记，数学运算／Q转换／舍入／饱和仍为外部服务合同。

候选服务仍通过L_EXEC的execution记录编码：compute为service0、native_op=0xF100+旧ISA资源ID，count1／stride16；native0动作0普通scratch、1读old写next、2消费者receipt、4读next，动作2／4的native1为消费者位1或2。发布是R逻辑适配器service5／native_op0xF1FF／native0=3，不新增ISA操作码，**这些数值不是现有宏真实cmd_op**。状态动作parameter_ref4096／parameter_bytes32，字0..7依次old、next、expected_generation、consumer_mask、transaction_id、local_iterations、optional_path、mother_iterations；全uint32小端，前五字绑定事务身份，后三字用于控制流。参数区不可变，GPR可以随程序更新。真实adapter参数sideband／ABI映射仍待实现。

状态示例从非零handle5／generation7／payload0x12345678开始，实际OLD_READ后写next9；U／F实际NEXT_READ、scratch写／ACK及成功终态全部完成后，母控才调用C的独立发布任务入口1。发布是provider原子改root，不是G_WAIT本身。正常连续job不reset并保留任务序号／S内容／状态，第二job以old9写next13；错误后可排空的job也能继续。任何已offered的发布义务不可撤回，因此取消后仍可能提交；发布后错误或ACK丢失必须按UNKNOWN处理，不能声称old仍有效。持久事务journal查询及幂等重试确认结果后，才允许释放无消费者／旧响应引用的old。句柄是外部状态存储标识，不代表R原生context数或完整R数值模型。

另提出独立64B小端管理帧（尚无RTLserializer／MMIO）：version16@0、kind8@2、participant8@3、reset_sequence32@4、epoch32@8、generation32@12、cohort_bitmap64@16、transaction32@24、status16@28、flags16@30、value0..3各32@32..44，48..63保留0；kind128..132为RESET_REQ／ACK／RELEASE／QUERY／REPLY。cohort包括母控、各局控、adapter、实际列出的各provider、feeder、transport／ingress及MEM／journal接口。模型要求provider实际复位／未来旧响应清空后ACK、所有成员确认、额外quiet step、全量镜像重装／读回、新generation／epoch和UNKNOWN查询后才准入；拒绝伪ACK／错epoch／重复／缺成员／半装载／过早释放。无tag原生口仍依赖可信provider合同，quiet tick不证明真实CDC／复位时序；reset不抹掉已提交状态／journal。

最终97246／mdt-lc179p／node27／debug／1核COMPLETED0:0、3秒：34模型执行／12231 model ticks／1263退休／153服务、30镜像拒绝、6组114复位／查询检查及4错误轨迹拒绝。97244因独立checker遗漏CANCEL事件失败；97245早期模型通过，97246新增显式OLD_READ／NEXT_READ并把读值用于版本标记，重新执行全部场景。113输入源、34完整轨迹与cohort报告SHA已核，原始结果仅服务器保存。[实际模型报告](../../project/control_profiles_v0_1/profiles_report.json)、[cohort报告](../../project/control_profiles_v0_1/cohort_report.json)、[验证／作业索引](../../work/Melodydt/179/control-profiles-validation.json)与[源码索引](../../work/Melodydt/179/control-profiles-sources.json)可追溯；[静态编码示例](../../project/control_profiles_v0_1/examples.json)覆盖五类，所有镜像SHA等于最终服务器实际用例，本机仅静态导出，未执行模型仿真。

PR176开始／上传前仍08f2ea20、正文及三类讨论未变；R源任务PR167仍c97353cf／open，未重新验收其物理包。R3受限P／R4实际双局控的164不同RTL场景和173旧软件检查保持原证据，代码未变，本轮没有冒称重跑。按用户“直到R5”，本次交付后停止自动研究；R6控制IR生成、R7成本／真实接入未开展。R5新指令／profile的RTL、真实native适配、provider复位／CDC、原生S／RX-close／flit、完整Block／数值及物理仍待相应实现验收；Issue研究整体保持in_progress，Draft待审查／未合并，不标done。

### 第14步历史交付：实际母控＋两个局控集成（04:09 CST）

本步实际实例化同一mc_min_controller与两份lc_min_controller（Block ID0／1），不改两个控制DUT源码。3份二进制镜像各经配置口完整写入／实际读回／VERIFY／PREPARE后才统一deploy。母控CALL与局控接单、局控返回与母控接受逐周期核对64B全包／信用的原子一致性；实际局控取指产生READY／终态，没有用子协议peer代替。未实现完整Block；原生S、数据链路与存储由有限peer提供。

每个局控外接16KiB实际数组及单在途服务；网络只有每端一个RX arm、一份TX payload与一个ACK状态。先调用消费者，实际OPEN／RX／MOVI／REPORT发READY，母控G_EVENT消费后才CALL生产者；host255→0写入、生产者TX读取其SRAM、0→1实际写接收SRAM、ACK发送／源接受依次发生，才有相应服务完成和WAIT／DROP／终态。独立checker把两端服务／数据事实、母控信用和线上全包交叉关联，拒绝单靠接单或busy消失算完成。

新增10集成场景共15395个采样边沿、4错误轨迹突变拒绝，最终97243／mdt-lc179n／node27／debug／4核COMPLETED0:0、27秒。覆盖无reset连续job、R7高位scalar传参、返回背压、某目标CALL受阻时另一目标终态继续、READY前错误、错误后再次执行且端点task_sequence不同，以及缺TX ACK／错误后的RX无法关闭。后两者保留服务／对象／任务义务并隔离，**不返回伪造成功或伪造CANCELLED**。错误后的再次执行证明链路按job／epoch／edge配对，再绑定每端真实task_sequence；不能要求两端序号相等。数据仍使用每job独立的有限测试payload，不含计算数值正确性证明。

集成显式配置MC／LC无进展阈值4096周期，LC取消排空阈值128；原最小DUT默认值未改。该参数是本次实例配置，不是完整系统延迟保证。97238先通过25局控／26母控回归及前9集成，末例测试台把运行期故障提前作用于配置读回；97239实际进入正确取消／隔离，但独立观察器误以为取消进入排空时一定清IREG。修正为有未完义务时保留IREG、终态接受后才清除，再由97243回归25局控＋10集成通过。母控26场景的源／checker与97238相同，按SHA关联；未把前两作业写成整体成功。106源／61实际日志／4编译日志SHA核验；既有173软件及其他局控证据保持，当前164个不同RTL场景不重复计数。

[网络实际报告](../../project/control_rtl_min_v0_1/network_report.json)、[验证／作业索引](../../work/Melodydt/179/control-network-validation.json)与[源码索引](../../work/Melodydt/179/control-network-sources.json)保留完整追溯。PR176开始／上传前仍08f2ea20、正文／三类讨论无变化。**R4有界母控＋双局控控制集成门已满足**，不是一般死锁自由、真实S／Block或物理资格。下一步R5研究P/U/C/F/J能力profile、分支／循环、非零old／next、消费者义务与提交、取消／协调复位；新增模型／合同与实际RTL资格分开记录，未知native服务继续拒绝。

### 第13步历史交付：母控取指与双端协议切片（03:46 CST）

新增功能母控mc_min_controller.sv，从实际4736B单口PM取128bit指令，执行G_CALL／WAIT／EVENT／MOVI／END；最多256条、2个目标、8个完成令牌，START后先读完最多2条事件绑定。母控接口81信号／2722位，编码仍为既有ISA v0.1；32令牌与更多目标属于候选扩展。镜像完整写入／实际读回、VERIFY／PREPARE后，还需匹配外部deploy generation及有效局控镜像ID；运行中改写禁止，部署或目标快照撤销进入POISONED。此profile声明scalar_parameter_words=0，START参数必须为0，母控寄存器清零；G_PARAM尚未实现，不能把START并行字段默认为寄存器初始化。

G_CALL先预约目标／完成空间，锁存当前R0..R7及job／epoch／单目标递增task_sequence／image／topology／token，64B整包接受后才退休。已经offered的CALL不可因异步错误撤回；等待该CALL时，另一子端返回仍独立接收。每目标仅一个READY槽与一个终态槽（共4×64B），不依赖无限队列。G_EVENT消费先前实际接受的READY，scalar写母控寄存器，再由后续CALL参数快照读出；G_WAIT仅在选中终态已到达且其声明READY已消费后回收token／目标。无reset的两个job维持task_sequence递增，并重新清寄存器／job状态。

子端ERROR停止新发普通任务，保留已offered CALL／PM握手，对仍未终态的已接受任务发身份匹配CANCEL；必须实际接收所有义务的终态，再释放并给主机错误。abort期间可丢弃已归属READY，但不伪造G_EVENT退休。无法排空、错误返回身份或运行中撤销部署则隔离，保留任务／信用，不伪造全局完成。主机结果含job／epoch／START序号、首错误来源、母控错误PC、子端错误PC／task_sequence，以及确认读写字节饱和汇总、计数溢出和数值saturation标志；整组结果在背压时保持。

服务器97234／mdt-lc179m／node27／debug／4核COMPLETED0:0、9秒；26场景共12218个采样边沿（22执行／4配置与START拒绝），4项错误轨迹突变拒绝。覆盖先消费者READY再生产者、32bit高位scalar和R7参数、连续job、单端CALL背压时独立回收另一端、首错取消／有序排空／再次job、缺终态／错误身份隔离、未使能目标／重复token／非法opcode／PC越界／未消费READY／PM错误与前缀计数溢出。独立checker依据输入PM实际读回、全包身份、寄存器语义和信用义务重建，负向装载／START用TB断言单独记账。

97230因新TB整数逻辑位宽告警失败；97231的错误注入早于第二CALL发出；97232／97233在负向START测试结束后落入正向计数断言。修正TB边界后97234通过；母控RTL自首快照未改，所有失败源码／日志保留，没有关闭检查。94源文件和26日志／编译日志SHA已核；此前173软件＋128局控RTL的源集合未变，关联既有证据，不假称本轮重新执行。[母控报告](../../project/control_rtl_min_v0_1/mother_report.json)、[验证索引](../../work/Melodydt/179/control-mother-validation.json)、[源码索引](../../work/Melodydt/179/control-mother-sources.json)区分独立服务器commit与PR提交。

PR176开始／上传前仍08f2ea20，正文及三类讨论无变化。**R4尚未完成**：本步2个子端是有限协议peer，尚未接实际LC RTL；有限peer的取消闭合不等于真实RX可关闭。下一步连接母控＋两个现有局控＋有限SRAM／ACK链路，验证接收先行、真实局控READY／终态、两job和取消／隔离，再进入R5五类控制profile／状态。原生S、32bit flit串行化、RX-close、真实provider复位、完整Block与物理未测试。

### 第12步历史交付：RAW16收发、ACK与READY读值（02:44 CST）

受限P控制原型现执行9类局控指令：OPEN、M clear EXEC、RX、TX、WAIT、MOVI、DROP、READY REPORT和END；同一RTL执行既有生产者／消费者镜像及派生寄存器／地址变体，不改变ISA编码。RX／TX从实际PM读完64B传输描述符，校验RAW16、方向、对象／端口、计数、版本与研究拓扑393400001的固定路线（host255→0、0→1）。路线准入不创建任何M11/M12导线，也不是物理可达性资格。

有限存储peer只有16KiB SRAM、一个在途服务与一个16B接收槽。RX实际写入peer SRAM并发送ACK后才完成；TX读取该SRAM，在接收槽真实存下数据、源侧接受ACK后才完成。WAIT消费实际完成的RX令牌后，局控才设置逻辑对象数据valid；未经声明的TX返回4，已声明但数据未valid的TX返回7，DROP必须等令牌消费／实际ACK。两任务无reset使用不同payload，验证不会把前一任务数据当作新输入。该存储／ACK是行为peer证据，**不是原生S RTL、真实链路或完整Block**；本步也未测试32bit控制flit／数据头串行传输。

READY从MOVI寄存器实际读scalar，整包回传；R0／R7、0xFEDCBA98高位值与未写R0的初值均有外部观测，补齐第11步的值读回欠项。服务错误已知后禁止新发READY；已经offered的READY背压保持。取消消息在锁存READY期间保持不接单，先让该包实际接受，再接收CANCEL并按服务→令牌→对象顺序排空；调用方必须独立消费返回，不能等待取消接单才读READY。

新增25场景和4项错误轨迹突变全部通过：正常／背压、连续任务、16KiB末字、寄存器读值、RX写错、TX接收ACK后的错误前缀、READY背压期间取消、描述符／端口／路线／计数／invocation／全零记录拒绝，以及错误身份响应／缺TX ACK进入POISONED。错误后已发生的存储副作用不会被回滚；未完成任务／对象不释放。RX-close／真实provider协调复位仍未实现；若RX不能完成只能有界隔离，待外部cohort复位。

服务器97227先通过173既有检查及103旧RTL，随后因新TB整数逻辑位宽警告FAILED1:0；修正显式比较后97228通过前22场景，但“TX未valid”测试先命中未声明输出的错误4。拆成权限4与状态7两个独立用例后，97229／mdt-lc179x／node27／debug／4核COMPLETED0:0、14秒。三个快照的控制RTL及旧回归源SHA完全相同，最终仅三份新测试文件变化；没有关闭警告或修改旧checker以通过。当前128个RTL场景与173软件检查分别可追溯，部分失败作业不被写成整体成功。[实际报告](../../project/control_rtl_min_v0_1/transfer_report.json)、[验证／作业索引](../../work/Melodydt/179/control-transfer-validation.json)和[源码索引](../../work/Melodydt/179/control-transfer-sources.json)保留输入／输出／日志SHA。

PR176开始及上传前仍08f2ea20、正文与三类讨论无变化。**R3首个受限P控制profile已达到进入R4的门槛**；通用ISA、更多profile、原生S适配、RX-close和真实系统集成仍是后续工作，不能标成完整控制器／Block完成。下一步自动开始R4：母控从二进制取指，连接两个局控，验证先调用消费者、消费READY后调用生产者、有限返回空间、ACK依赖、两job无reset及错误排空；再进入R5五类profile／状态研究。

### 第11步历史交付：RAW16逻辑对象预约与释放（02:06 CST）

局控开始执行L_OPEN／L_DROP，支持一个静态RAW16对象槽；从外部PM完整收齐64B对象描述符后检查版本、ID、类型、格式、长度／容量、ABI、保留字段、16B对齐及16KiB范围。OPEN只建立预约，不生成有效数据；重复OPEN、未预约DROP、活对象下END和错误描述符均明确报错。正常DROP须已无在途服务；取消时先真实完成并清理服务令牌，再产生对象清理trace，最后才返回终态。无法排空时POISONED继续持有对象／任务义务，不能提前释放。

同时接入L_MOVI及8×32bit寄存器声明，并测试合法退休／非法寄存器拒绝；**本步没有寄存器值的外部读回，不能据此宣称MOVI数值语义已完成验收**，下一步由L_REPORT读值和收发轨迹补证。对象缓存64B及寄存器32B只是RTL声明payload，不是综合／面积结果；第6步688B为历史下界，不能作为当前总成本。

实现中发现“描述符非零表示已经装载”会让全零非法记录反复读取；执行与对象描述符均改用显式loaded位。两个整记录全零测试都返回错误5，未出现无限重取或虚构服务。旧ISA／镜像／软件模型和第6步边界checker未改；第9步fault观察器增加默认关闭的扩展退休hook，只有先通过对象生命周期检查的新profile使用，原始采样不修补；旧故障场景实际回归通过。

服务器97225／node27／debug／4核COMPLETED0:0：173既有检查、76原控制／适配器场景和最初26对象场景通过。只增全零执行描述符场景后，RTL及其余仿真源SHA不变；97226同资源COMPLETED0:0，27对象场景及3错误轨迹突变通过。最终合计103个当前RTL场景按各报告分别计数，另原26例重跑不重复计入；源码／输入与日志／编译SHA见[验证索引](../../work/Melodydt/179/control-object-validation.json)、[实际报告](../../project/control_rtl_min_v0_1/object_report.json)和[源码索引](../../work/Melodydt/179/control-object-sources.json)。两次作业均成功，r001为未提交的准备快照。

PR176开始及上传前核验仍08f2ea20，正文与三类讨论未变。当前对象版本固定1、长度16B、静态地址、单槽；尚无真实S数据访问／数据valid、RX/TX或完整Block资格。下一步补RAW16有限存储peer、收发／ACK与READY报告，并核验寄存器读值，再进入R4母控多局控及R5五类profile／状态；R3整体尚未完成。

### 第10步历史交付：接入现有M RTL的严格服务适配器（01:45 CST）

新增lc_m_clear_adapter，固定连接局控服务口与M原生cmd／rsp口，仅支持已登记M_CLEAR_ALL_VALID，ISA／描述符编码不变。接单时保存token、service_sequence、job、epoch和task_sequence；完整检查资源／描述符／ABI／对象字段后，发送cmd_op=6、index=0、data=0。命令背压时保持tuple；收到真实M响应后才生成带原身份的服务响应，返回背压时保持。错误资源返回4、描述符／ABI错误5、native错误或非零意外返回数据9，拒绝路径不向M发命令。

M原生响应无tag，适配器只允许一个在途命令；窗口外迟到响应、provider许可被撤销均poison，不把旧响应贴上新任务标签，不撤回已保持的原生命令。provider_released是外部前置合同，本步没有实现真实cohort协调器。当前只允许独占M、没有外部读者／消费者的clear场景；适配器不能替共享M使用者判断清除是否安全。M的数据口在本测试绑零，不做乘加数值验证。

最终服务器作业97224／mdt-lc179a／node27／debug／4核，COMPLETED0:0。10个协议peer场景、5个连接现有block_v2_m的RTL场景通过，新增3569采样边沿；5次真实M命令与5次真实响应均按次关联，局控完成严格晚于native响应接受。覆盖空程序、清有效位、背压、两任务无reset及运行CANCEL；3项适配器错误轨迹突变拒绝。另173软件／合同检查及61个原控制RTL场景继续通过。97223仅因原生端口日志使用共享阻塞cycle计数而相差一拍失败，修正日志编号后通过；适配器及M源未因此修改。

现有M源码blob d91ffdf904bc77c19d5d0ecfd4cd11560b44a417与注册接口一致，作为未修改依赖使用；未新增／改写基础宏。75个输入源文件、76个场景日志与5个编译日志SHA核对，详见[实际报告](../../project/control_rtl_min_v0_1/adapter_report.json)、[源码索引](../../work/Melodydt/179/control-adapter-sources.json)和[验证／作业索引](../../work/Melodydt/179/control-adapter-validation.json)。原方案Markdown及同名PDF继续原位更新。

PR176开始及上传前核验仍08f2ea20，正文与三类讨论无变化。本步不是完整Block集成，也没有证明GEMM／S存取／系统复位／模型数值／物理。R3整体仍待有限对象、RAW16／RX／TX和其他服务控制；下一步先落实对象窗口与寄存器／生命周期，再补收发与事件，随后R4母控多局控与R5五类profile／状态。

### 第9步历史交付：运行异常、有界等待与有限peer恢复（01:25 CST）

第9步补齐当前M clear控制子集的运行错误路径。CALL在接单前检查目标、epoch、序号和镜像／拓扑身份；错误消息保持不接单，不虚构关联终态。L_EXEC的保留字段、资源不可用、令牌越界和描述符索引分别拒绝；描述符／ABI、非法指令、PM读错、活令牌下END及max_steps均有实际RTL错误路径。先保存控制错误，后收到的native错误优先；整包终态包含独立预期的错误码及error_pc。

运行中已接单服务继续排空，故障不能假装撤回服务；完成后才产生一次错误终态。另增128周期无握手进展期限：PM响应缺失、已保持的PM／服务请求不接收或服务不响应时进入POISONED；任务、令牌和保持的请求仍归本控制器，禁止新接单／配置／假完成。期限不针对终态返回背压；可用端点持续进展时也不因此提前判失败。取消的原128周期排空期限保持，两个期限均可参数化；未验收全系统实时性。

所有仿真在服务器：最终97222／mdt-lc179f／node27／debug／4核，COMPLETED0:0。173既有软件／合同检查、10原RTL、22取消及29新增故障场景通过；6项故障轨迹突变、6项取消轨迹突变均拒绝。新增覆盖四种CALL身份拒绝、控制错误与native错误优先级、六种隔离场景、一次错误后无reset复用及一次隔离后复位／完整重装。故障轨迹周期数、输入／日志／报告SHA及全部作业见[验证索引](../../work/Melodydt/179/control-fault-validation.json)；[实际报告](../../project/control_rtl_min_v0_1/fault_report.json)与[源码快照](../../work/Melodydt/179/control-fault-sources.json)可追溯。

97219因RTL位宽警告失败，修正比较位宽而未关闭警告；97220为新增观察器在CALL接收边沿过早按运行态判互锁，97221为突变测试选中了尚未形成保持义务的首次offer。修正观察器／突变取样点后全部通过；三个失败日志均保留，旧边界checker及ISA／镜像／软件模型未改。

恢复证据仅包括控制器与有限PM／服务peer同时复位；RAM保留但valid清除，必须新release、完整写入／读回及部署后才接下一个epoch。没有证明真实无tag宏已经清空旧响应，也没有实现系统provider复位协调器。PR176开始及上传前核验仍08f2ea20，正文与三类讨论无变化。R3整体尚未完成：下一步服务适配器与有限对象／收发，随后R4多局控母控、R5五类profile／状态；完整Block与数值／物理仍为外部集成门。

### 第8步历史交付：局控取消与有界排空（01:00 CST）

第8步已完成局控CANCEL与有界排空RTL，ISA和第6步92信号合同保持原编码。取消时阻止新取指／服务请求，已offered请求保持完整tuple直到接单，实际PM／服务响应完成后才清理令牌；清理不是伪造WAIT／END退休。重复取消不重复返回；已锁存DONE／ERROR保持不变；native错误优先于取消状态11。排空期限128周期届满进入POISONED，保持未完成义务，不虚构任务终态或释放返回信用，后续仍需外部cohort复位。

所有仿真在服务器运行：97218／mdt-lc179c／node27／debug／4核，COMPLETED0:0。173既有软件／合同检查、10原RTL场景和22取消场景通过；取消轨迹18719边沿，19例安全结束、3例预期隔离；6项破坏轨迹的负向检查全部拒绝。97216／97217因testbench把POISONED场景继续按READY收尾而失败，记录保留；未关闭位宽警告、未修改旧checker。新checker仅补齐取消时native错误终态对未退休IREG的合法丢弃，并增加独立取消发射、信用、整包及隔离检查。

结果为[取消运行报告](../../project/control_rtl_min_v0_1/cancel_report.json)、[源码与输入](../../work/Melodydt/179/control-cancel-sources.json)和[验证／作业索引](../../work/Melodydt/179/control-cancel-validation.json)。62个实验源文件与下载日志SHA已核对，行为peer没有变成真实宏或完整Block。CANCEL错误身份拒绝、同拍响应／取消、既有服务接单、已完成令牌、END解码／锁存、重复取消、取消后连续任务和3种隔离均有实际DUT证据。

下一步自动继续第9步：运行态非法指令／字段／描述符、PM错误、步数界限、故障与取消竞态、异常排空和复位后的重新准入；之后继续R3适配器／对象／收发，再进入R4／R5。R3整体、真实provider复位、母控RTL、真实M／S／完整Block及物理尚未完成。

### 第7步实际交付：最小功能局控RTL（23:47 CST）

本轮实现第一份功能局控DUT，直接执行既有208B空任务和368B M clear镜像；保持ISA v0.1、旧镜像和第6步机器合同不变。[实现／能力与复现](../../project/control_rtl_min_v0_1/README.md)、[研究说明](LOCAL_CONTROL_MIN_RTL_V0_1.md)、[实际报告](../../project/control_rtl_min_v0_1/run_report.json)为入口。R3初始切片已产生实际RTL轨迹，R3整体尚未完成。

开始、恢复与上传前核PR176仍08f2ea20，正文／评论／review／逐行评论无变化；[同步记录](../../work/Melodydt/179/pr176-sync.json)保留本轮检查，不修改PR176或其他任务分支。
功能范围为配置完整写入／实际读回／PREPARE＋外部deploy、CALL、任务／执行描述符收齐、单128bit程序口、PC取指、L_EXEC／L_WAIT／L_END与终态整包保持。母控仍是外部发送peer，M是服务行为模型，未实现宏间数据拓扑或真实M计算。

服务器公钥认证已验证，宿主Verilator存在GLIBC不兼容；现有ORFS 26Q1容器内Verilator5.042、G++11.4及Python3.10.12可用。最终Slurm作业97215在node27、debug分区4核完成，退出0:0；10场景3926边沿，其中5份执行轨迹3061边沿通过未修改的独立checker，实际13次退休／4服务接单／6终态。173项既有软件／合同检查通过；两类证据分开计，不把管理CI当业务验证。
97211／97212／97213的位宽、testbench信用保持和execution ABI字节偏移错误均留存；97214先通过7例，97215补充候选失败失效、空闲撤销许可和错误BEGIN保留提交。源码实验commit、输入／输出SHA、实际命令、日志／结果位置见[验证索引](../../work/Melodydt/179/control-min-validation.json)。

限制：只支持严格P／M clear子集、1任务／1在途服务；不支持CANCEL、对象、RX/TX、RAW16、循环／分支或完整cohort恢复。真实适配器／无tag迟到响应、四态仿真、综合／面积／频率／功耗、完整Block、母控RTL与系统物理未验收。
下一步先补局控取消／异常排空与服务适配器验证，再扩有限S、RAW16和RX/TX，之后研究母控与多局控协同；完整Block继续由外部实现任务提供。研究in_progress、PR180 Draft／未合并，审查人待指定；登记PR5 pending，看板unverified／同步pending，无后台监测。

固定PDF版本：[TWO_LEVEL_CONTROL_PLAN.pdf](TWO_LEVEL_CONTROL_PLAN.pdf)。

## 0. 本分支责任边界与当前可研究范围（17:05 CST 修订）

用户明确：**本分支只研究母控／局控，不负责 P/U/C/F/J 完整 Block 实现。** 前版将“完整 P Block 集成”和“完整组合物理”列入本任务执行步骤，范围过大；本节及第9节修订为控制研究主线。Block 组成和数据连接保留为控制研究的输入背景，不构成本分支的 Block 实现承诺。

目前具备基础宏接口、私有 S 协议、控制 ISA 和容量参考，足以开展接口建模、指令语义、装载／取指、任务与事件调度、对象／上下文生命周期及控制器验证。完整 Block RTL 不必作为这些工作的启动前提。尚未冻结的端口／延迟／端点应写成有版本的假设或待确认项，得到实现方接口后再核对。

| 责任 | 本分支交付／使用方式 |
|---|---|
| 母控与局控研究 | 控制结构、ISA／描述符、镜像装载与准入、程序生成／检查、二进制执行模型、任务／事件／错误协议及相应控制 RTL 验证 |
| Block 接口模型 | 将 Block 视为资源与端点合同；用协议 peer／行为模型表达命令接受、有限延迟、背压、完成和错误，仅用于控制验证 |
| 基础宏、私有 S 与完整 Block 实现 | 由各实现任务提供并接收；本分支不新增／重构计算宏、S 容量或完整 Block 数据通路。新完整 Block 集成责任人／任务待指定 |
| 系统／物理／模型质量 | 保留完整验收要求，作为后续外部集成门；本分支输出接入合同、控制轨迹和控制资源成本，不用模型／peer 通过代替真实系统通过 |

验证分别记录“静态编码检查、二进制控制模型、控制 RTL＋协议 peer、真实实现集成”。例如测试包含三份宏 peer 并不表示 P Block 已实现；只有命令／状态协议匹配，也不等于数值计算或物理互连已验收。外部 Block 接入可以在相应实现可用后联合开展，不能将待交付外部实现当作当前控制研究停滞的理由。

当前已从接口表推进到受限P控制RTL：实际装载、取指并执行九类局控指令，具有M clear适配器及有限RAW16收发／ACK证据；下一步母控与两个局控协同。这里的P是控制验证profile，不是本分支实现产品P Block。

### 第1步实际交付（17:39 CST）

已按用户要求在研究开始检查 PR176 head／说明／评论／review，仍为08f2ea20，无新增变化；上传前再次核对并保存[同步回执](../../work/Melodydt/179/pr176-sync.json)。后续每次开始／恢复和上传前均执行此项，不创建后台监测。

[控制接口合同 v0.1](CONTROL_INTERFACE_CONTRACT_V0_1.md)与[机器可读参考](../../project/control_contract_v0_1/README.md)建立6模块149原生端口、12个P服务、2个16KiB研究profile及静态字段检查。母控／局控消息边界单列；G流式、M结果上下文和S真实确认分别建模。其他类型保留目录，原生服务仍待登记。只完成第1步P接口基线，R1整体／R2及控制RTL仍待执行。

### 每轮研究与方案同步要求

按用户要求，每轮研究必须把目标、PR176版本／差异、产物、实际验证、结论／限制和下一步补入本方案；与Issue、个人进度和交接一起保持一致，保留历史证据。更新方案是交付条件，不把未执行工作写为完成；恢复研究和上传前仍须核PR176。

### 第2步实际交付（18:21 CST）

已建立[控制用例与预期轨迹](CONTROL_REFERENCE_CASES_V0_1.md)和[参考目录](../../project/control_cases_v0_1/README.md)：空任务、单M清有效位、接收先行16B交接三组程序，7段／29指令／464B及11份分离记录720B；3条正常和1条非正常peer错误参考，共72条观察。

27组轨迹属性／拒绝检查通过；它读取人工观察事实，不执行PC，输出明确未执行指令／未测试RTL／未生成完整镜像。它是后续执行器的独立预期依据，**不等于R2执行器已经完成**。第一步的P接口静态合同仍保留，G参考S32容器相对紧凑S16占2倍payload，不转移旧容量资格。

研究结论：接收侧写确认后可生成ACK，但源必须实际收到匹配ACK才能退休TX及释放对象；接收token此用例采用更保守的“写确认＋ACK发送接受”完成点。M单服务与返回身份／服务序号分离，错误不能被成功DONE隐藏。下一步为完整镜像、配置装载／有效互锁及错误恢复合同，再实现从二进制运行的控制模型。

PR176开始核对仍08f2ea20、无新讨论，上传前再次核对并保存[同步记录](../../work/Melodydt/179/pr176-sync.json)；[本轮来源](../../work/Melodydt/179/control-case-sources.json)与[验证](../../work/Melodydt/179/control-case-validation.json)提供实际回执。最终发布SHA见PR180，避免同文件自引用提交循环。

### 第3步实际交付（19:14 CST）

目标为完整镜像装配、配置装载／有效互锁和失败恢复。本轮开始核PR176仍08f2ea20，正文与讨论未变；上传前再次核对并记入[同步记录](../../work/Melodydt/179/pr176-sync.json)，没有待同步设计差异。

[镜像与装载合同](CONTROL_IMAGE_LOADING_V0_1.md)和[参考实现](../../project/control_image_v0_1/README.md)交付3个cohort、7份完整镜像，共2080B（896B头＋464B指令＋720B描述符）；manifest绑定实际SHA与配套版本，不能只凭短image ID判断兼容。沿用ISA v0.1编码，没有新增运行指令；typed配置API已定义，真实配置总线／MMIO编码仍待冻结。

单bank采用BEGIN使全部旧valid失效、连续WRITE16、逐目标VERIFY、全cohort COMMIT后READY；START前再次核实际字节。运行中禁写，复位保留RAM但清valid，须provider协同复位确认后完整重装；软件generation不能识别无tag宏旧响应。五类任务／数据／返回／上下文／无tag义务分别阻止排空确认。

新增30组镜像／装载检查通过；修正第2步G_EVENT→R0=1→后续CALL arg0=1的参考错误并新增1组回归，轨迹现28组，连同ISA8组／接口15组共81组通过，管理检查另计。[来源](../../work/Melodydt/179/control-image-sources.json)与[验证](../../work/Melodydt/179/control-image-validation.json)保存实际命令／SHA。原27组通过的历史记录保留，不将其升级为执行证据。

结论：软件参考可拒绝半装载、错误身份／段／对端、校验后损坏和运行改写；START仅entry_admitted，不执行PC，未验证RTL／Block／物理或实际provider复位。下一步直接读取这7份二进制，独立实现有界母控／局控PC执行模型并产出轨迹，与人工oracle对照；仍不负责完整Block实现。

### 第4步实际交付（19:46 CST）

本轮目标为从完整二进制取指、真实产生控制轨迹的有限模型；开始核PR176仍08f2ea20，正文／评论／review无变化，上传前再核并保存[同步记录](../../work/Melodydt/179/pr176-sync.json)。不实现完整Block。

[执行模型说明](CONTROL_EXECUTION_MODEL_V0_1.md)及[代码](../../project/control_exec_v0_1/README.md)新增母控／局控PC、寄存器、令牌、对象和整包holding，描述符从镜像段读取。运行端不读取cases.json／golden，不按案例名选脚本；人工参考仅在执行结束后检查实际观察。改变机器码中的MOVI会改变READY／CALL，独立oracle能识别差异。

以既有7镜像运行9次（3正常、3背压、1非正常M错误、同一Machine连续2job），共100次指令退休／193观察，独立属性、接受payload及退休PC比较通过。有限16KiB S bytearray实际保存／复制数据，写确认后生成ACK；源收到ACK才完成TX／释放。新26组检查含8随机种子×3案例、缺输入／永久背压及改变机器码；连同既有81组共107组通过，管理检查另计。[来源](../../work/Melodydt/179/control-exec-sources.json)／[验证](../../work/Melodydt/179/control-exec-validation.json)保存版本、实际命令与SHA。

本轮instructions_executed=true仅指软件解释器；没有控制／宏／S RTL执行，tick不是硬件周期。支持首个直线profile14类指令、M op6和RAW16；其他服务、循环分支、运行取消及provider协同复位仍未覆盖。ModelBound仅为实验界限，不生成成功终态、不证明硬件死锁；非法包通过模型异常拒绝，不当作已实现完整硬件错误恢复。

下一步补R2运行取消／排空／poison、provider复位确认及迟到响应隔离，再冻结局控RTL的周期级接口、有限队列和配置写口互锁。R2整体与RTL未标完成，研究保持in_progress。

### 第5步实际交付（20:58 CST）

本轮补R2的取消、poison、模型cohort协同复位及无tag迟到响应；开始核PR176仍08f2ea20、正文／评论／review未变，上传前再核并记[同步历史](../../work/Melodydt/179/pr176-sync.json)。ISA、既有镜像／人工参考／9次执行报告保持不变。

[恢复研究说明](CONTROL_RECOVERY_PLAN_V0_1.md)与project/control_exec_v0_1新增RecoveryMachine、有限独立native响应源、复位协调器及独立检查。CANCEL沿用task_message.kind=1；停止新发射，保留已offered的valid／payload；可排空时ERROR/status11，不能排空时status13、清valid并关闭响应准入。实际native错误status9优先；已锁存DONE不改写。已写S不回滚，取消包报告观测确认的字节数。

9组取消／poison实验（7安全排空、2poison）及各自恢复共18次运行，取消53次／恢复115次指令退休，含2个完整模型cohort复位；新增30组、累计137组检查通过。旧9次执行报告和既有镜像可逐字重建。[来源](../../work/Melodydt/179/control-recovery-sources.json)／[验证](../../work/Melodydt/179/control-recovery-validation.json)记录实际工具、输入／输出SHA和范围。

关键结论：无tag旧响应在新命令等待期间可能与合法响应完全相同，软件epoch不能识别；模型不利用observer_origin当硬件tag。隔离保障依赖provider确认、清全部未来响应、适配器／controller／transport等实际空闲，以及完整重装后才解除门控。7／11个复位参与者只覆盖一／两局控模型，真实Block还须补G、feeder、仲裁等清单。RX关闭及RESET_ACK均是拟议peer合同，没有硬件实现资格。

下一步冻结首个局控RTL的周期级接口、状态机、配置写口互锁与完整provider复位确认清单，再用同一14类直线profile做RTL＋有限peer对照。R2通用指令／更多服务、真实provider／Block／物理仍未完成，研究in_progress、PR Draft。

### 第6步实际交付（21:54 CST）

本轮形成R3入口的[局控RTL接口与状态机候选](LOCAL_CONTROL_RTL_CONTRACT_V0_1.md)，开始核PR176仍08f2ea20、正文／评论／review无变化，上传前再核并记[同步历史](../../work/Melodydt/179/pr176-sync.json)。这不是共同底座或物理pin已冻结。

[机器合同与端口声明](../../project/control_rtl_contract_v0_1/README.md)定义92个逻辑信号、9个生命周期／13个顺序机状态及转移guard；配置与取指／描述符共用单128bit端口，禁止同拍响应/refill，WAIT最早在完成响应下一拍消费。内部配置BEGIN/WRITE16/READ16/VERIFY_PASS/PREPARE/ABORT与运行ISA分离；local PREPARE须等待匹配cohort部署许可才可接CALL。

明确1任务、1对象、1在途服务、1 IREG、无prefetch，以及独立事件／终态holding各1槽。程序存储8320B之外，payload寄存器下界688B，控制元数据／适配器／物理成本另计。512bit整包边界与外层候选32bit×16flit分开，不能用第一flit或中间缓存接收替代端到端接单。

新增36组边界检查，连同既有137组共173组；4份人工期望时序829采样边沿＋1个flit示例通过。生成的SystemVerilog只有interface/modport／常量，没有功能DUT。本机PATH无iverilog/verilator/yosys，HDL编译／lint／仿真未执行，不能把这些人工时序当RTL结果。[来源](../../work/Melodydt/179/control-rtl-sources.json)／[验证](../../work/Melodydt/179/control-rtl-validation.json)记录实际工具、输入／输出SHA。

下一步实现首个功能局控RTL切片：配置／单口仲裁、CALL／任务描述符、FETCH／IREG、空任务与M clear的EXEC/WAIT/END及稳定返回；再扩RX/TX、取消与真实provider接入。R3功能实现、完整Block与物理均未完成，研究in_progress、PR Draft。

## 1. 总体选型及证据边界

推荐采用“固定硬件与控制归属、后制主要数据通路、离线生成程序、空闲装载、两级异步任务执行”。

| 层次 | 本方案的处理方式 | 当前性质 |
|---|---|---|
| 基础宏与 Block | 基础宏组成五类有局部性的 Block，每块私有 S、一个局控 | P/U/C/F/J 组成及实例数为候选，尚未冻结成硬件 |
| 固定硬件 | 母控、局控、程序存储电路、适配器、有限队列／选择器、驱动、时钟复位及测试电路均在 M1–M10 预制 | 延续 PR176 边界；新增资源须实现并计价 |
| 固定控制连接 | 局控始终管理所属宏；建议块内命令／状态连接优先在 M1–M10 预连，母控与 Block 使用共同控制网络 | 本轮推荐；实际 pin、金属分层及 RC 尚未定版 |
| 可定制数据连接 | 块内宏间、Block 间主要数据端点及配套握手／确认用 M11/M12、via10/via11 后绑定 | 研究中的新增层，不能当作 Nangate45 原生已支持 |
| 程序 | 离线工具按模型、资源和真实连通图编译母控／局控镜像；运行时由母控调用本地任务 | 已有有限编码／装载／二进制解释执行参考；完整编译器、硬件装载器与新控制RTL未实现 |
| 宏级断电 | 保留为后续可选研究，本阶段不设计电源开关、保持单元或电源管理指令 | 用户本轮明确暂缓；不计入节能成果 |

“控制归属固定”不等于“控制线已经全部布在低层”。若物理实现必须让某些固定控制线使用 M11/M12，它们应在各产品中保持相同绑定，并计入公共布线／RC 成本。后制导线不能新增选择器、缓存、仲裁或驱动。

## 2. 基础宏与五类 Block

### 2.1 基础宏职责

以下是当前项目的有界能力，不表示任意大模型算子均可直接执行；数值格式、舍入、饱和和状态协议仍以固定原生版本为准。

| 基础宏 | 主要组成／职责 | 使用边界 |
|---|---|---|
| M | 64 个 S8 乘法器，支持 S8／S16 两侧；S40 部分和、缩放流水及 64 份 S64 完整结果 | 单实例只有一个完整结果上下文；先显式装载／累加／读出，不能并存多个任意矩阵任务 |
| N | 统计、EXP、除法／平方根及归一化缩放；Softmax、RMS／L2、有限 40 选 8 TopK | 统计与回放有阶段约束；不是任意归约引擎 |
| E | 8 路 S16 基础算术、局部配对 RoPE、舍入饱和及 S8 打包 | 不自动提供通用 S32／S64 向量归并 |
| G | 2 路 S16 激活及可选紧邻门乘，四级流水，II=1 | 输入格式和双路配对必须满足原合同 |
| R | S32 状态、active／shadow 版本、GDN／SSM／四抽头卷积 | 新 R256／R1024 独立结果在 PR167；接入本方案仍须登记 ABI、时序和状态合同 |
| S | 四 bank 工作存储及实际 feeder，提供本块对象存放和回放 | 现有标准单元实现为 16KiB，不是 SRAM 编译宏；普通口与宽 feeder 存在 bank 争用 |
| T | 6KiB 有限片段交接、保持、背压与完成／释放 | 容量有限，不替代无限输出缓存或通用跨块交换网络 |

基础合同见 [BLOCK_V2](../BLOCK_V2.md)。main 已接收六宏与 PR167 新 R 的资格边界应分开记录，不能用独立宏结果授予新组合资格。

### 2.2 Block 的具体组成

每个数字表示一个独立物理实例；局控、程序存储、适配及收发等辅助电路另计。

| Block | 基础宏组成 | 宏数量 | 主要局部工作 | PR176 的工作 S 候选 |
|---|---|---:|---|---:|
| P：矩阵与函数 | M×1 + G×1 + S×1 | 3 | 投影、gate／up、激活门乘、down、有限加权矩阵归并；可旁路 G | 32KiB |
| U：统计与变换 | N×1 + E×1 + S×1 | 3 | 归一化、Softmax、TopK、缩放及配对变换 | 16KiB |
| C：卷积与状态 | R×1 + G×1 + E×1 + S×1 | 4 | 卷积、递推状态、激活门乘、格式转换及 old／next 管理 | 16KiB，R 内部状态另计 |
| F：函数与向量 | G×1 + E×1 + S×1 | 3 | 激活、门乘、逐元素处理与局部旁路 | 16KiB |
| J：汇合与交接 | E×1 + S×1 + T×1 | 3 | 分支等待、残差相加、必要缩放及片段交接 | 16KiB，另有 T 6KiB |

C Block 使用 blk_c 等名称，避免与旧研究中名为 C 的控制宏混淆；母控／局控分别称 global_ctrl／local_ctrl。

示例池为 P×3、U×2、C×1、F×1、J×2，共 **9 个 Block、28 个基础宏、9 个局控、1 个母控**。基础宏清单为 M3／N2／E6／G5／R1／S9／T2，不跨 Block 复用同一字母实例。

此候选池工作 S 为 **192KiB**，T 为 **12KiB**；PR178 当前九实例验证的是每块 16KiB，共 **144KiB、36 bank、3 feeder**。两者不是同一容量实现，P 的 32KiB 仍需新设计和验证。宏内部存储、控制存储、队列、MEM 权重／KV／系数／状态另计。

### 2.3 每个 Block 的辅助组成

每块另外包含任务入口、局控取指／译码、对象表、资源记分牌、原生宏适配器、本地 S helper、TX／RX、反向确认及终态保持。首个原型建议每块一个活动任务；不是所有宏只能串行工作，已发出的独立计算、搬运和返回可在资源允许时重叠。

## 3. 四类连接方案

### 3.1 连接总表

| 连接对象 | 传递内容 | 建议连接方式 | 后制金属的作用 |
|---|---|---|---|
| Block ↔ Block | 张量片段、帧身份、背压和目的存储确认 | 源 TX／持有对象 → 静态端点路线 → 目的 RX／私有 S helper；必要反向确认单列 | 用 M11/M12 绑定本产品需要的路线；不假设任意两块天然互通 |
| 同 Block 的基础宏 ↔ 基础宏 | 操作数、结果及配套 valid／ready／ACK | 经真实宽度／数值格式适配、holding 与预制端点直通或经私有 S 回放 | 主要数据绑定可后制；有限高复用预连可保留并计价 |
| 母控 ↔ Block 局控 | CALL／CANCEL、参数、READY／PROGRESS、DONE／ERROR | 固定寻址和归属的共同控制网络；首轮候选命令／返回各 32bit 有序链路 | 不随模型改变管理关系；必要高层公共线计入路线成本 |
| 局控 ↔ 所属基础宏 | 命令、配置、地址／计数、完成、饱和和错误状态 | 局控 → 固定宏适配器 → 原生宏端口；优先在 M1–M10 固定预连 | 不用可定制数据路线决定“哪个局控能控制哪个宏”；实际层分配待物理验证 |

本表中的“固定”表示各产品共享的逻辑连接和归属，不表示已有逐根 wire 或最终布局。时钟、复位、测试和供电网络单列规划，不能因无数据边就认为宏完全没有任何连接。

### 3.2 Block 之间：静态数据端点与确认闭环

首版采用可检查的点到点静态数据边；一个端点的多目的选择、复制或多源仲裁必须已有预制硬件，不将多个有源输出直接短接。若多条边复用有限端口，编译器必须遵守已声明的仲裁／带宽／并发限制。

跨块传输建议按有界片段执行：目的局控先预约私有 S 窗口、启动 RX 并报告 READY；母控再允许源任务发出。目的 RX 检查 job／epoch／edge／invocation／fragment／对象版本，实际完成本地写入后返回 stored ACK；源对象在确认前保持有效。局部 valid／ready 接受一个字，不等于整片已经存入目的 S。

返回与 ACK 必须能在等待期间继续前进。一个块背压不应占住所有其他块的完成路径；首版 TX／RX 每方向一笔在途，控制返回空间在发任务前预约。该规则待 R2／R4 用有限队列和真实背压验证，不预先声称一般死锁自由。

数据帧头／ACK 的 ISA 研究格式各 64B，若使用 128bit 链路各需 4 个有效字；实际数据链路位宽仍按物理 profile 接收。块内原生流可以选较小专用握手，但不能省略对应适配、holding 和确认职责。

### 3.3 基础宏之间：同一个 P 的两种产品绑定

| 拓扑候选 | 局控执行重点 | 必须真实存在的硬件 |
|---|---|---|
| S→M→S | 预约输入／输出窗口，供数，启动 M，读出并等待 S 写入完成 | S feeder、M 端口适配、M 输出到 S 的接收与写入路径 |
| S→M→G→S | 先准备 S 接收和 G，再启动 M，等待全链排空和存储完成 | 上述资源及 M→G 格式适配、匹配的 G 双输入与反压路径 |
| 同一版金属覆盖两条路径 | 程序选择已有旁路／端点，复用相同控制核 | 已预制的有限选择器、独立驱动和合法端点 |

这些是拟验证的绑定，不是已实现的直连链。M 的 S64 读出／舍入与 G 的输入 Q5.10 不兼容时，须按登记服务显式转换，不能只画一根线。

M11/M12 在制造时确定连接。同一芯片从 Attention 切换到 FFN／GDN 时只切程序和参数；若需要多种数据路径，静态金属及预制选择资源必须同时覆盖它们。程序不能建立一条未接通的物理通道。

### 3.4 母控与 Block：调用本地任务

母控发送粗任务而非逐拍宏控制。32bit 命令与返回方向独立，64B 消息至少需要 16 个有效 flit；包内不交织、背压保持。逻辑为母控寻址各局控，实际点到点／树／共享总线选择及队列深度待比较，不能把九路独占网络当作免费硬件。

CALL 消息携带目标 Block、常驻任务描述符索引、完成令牌、job／epoch／任务序号、程序／拓扑 ID 和 8 个 32bit 参数。局控返回准备、进度、成功或错误。控制链路不承担全部张量数据，权重／KV 等由显式 MEM 服务提供。

### 3.5 局控与基础宏：固定控制，可编程时序

以 P 为例，局控始终具有对本块 M、G、S 的命令／状态访问能力。改成旁路 G 的数据绑定后，程序不调用 G，控制所有权无需改变。每个适配器将通用服务翻译为固定原生协议，保持命令直到真实接受，并把真实完成／错误返回给局控。

宏类型、资源 mask、可用端点和 ABI 随部署 profile 固定；M/N 的上下文 owner 与命令 busy 分开管理。busy 清零不表示累加／统计上下文可以被其他任务覆盖。共享宏、远端 S 裸访问或跨局控迁移所有权不属于首版能力，需要另行定义仲裁和状态隔离。

## 4. 母控和局控硬件分工

| 部分 | 固定硬件组成 | 执行职责 |
|---|---|---|
| 母控 | 程序顺序器、任务／令牌表、事件槽、参数入口、命令与返回队列、错误／终态单元 | 图级依赖、层／头／token 循环、Block 任务调度、参数快照和状态根发布 |
| 局控 | 微程序顺序器、PC／标量寄存器、对象表、资源／上下文记分牌、宏适配器、S helper、TX／RX、终态保持 | 本块宏操作、对象地址／分片、回放、等待真实完成、确认与释放 |
| 配置装载器 | 配置请求接口、目标寻址、存储写入／读回、有效标志及启动互锁 | 在空闲时写入母控／局控镜像；装载协议为本轮建议，尚未实现 |

首轮候选：母控 32 个完成令牌、32 个标量事件槽、8 个 32bit 标量寄存器；每局控 8 个完成令牌、16 个对象、8 个 32bit 标量寄存器。实际 Block 数和表深度受容量 profile 限制，不按指令字段最大值自动实例化。

程序顺序发射，有界执行器异步推进。G_WAIT／L_WAIT 只停相应顺序器，不能停掉 RX／TX、S 服务、宏响应或控制返回。首版 S 对象静态分配，局控在 OPEN 时核对实际地址、对齐、容量和活对象重叠；母控不再维护另一套裸 RAM 分配器。

## 5. 指令架构与编码

### 5.1 两级 ISA

保持 ISA v0.1：固定 **128bit＝16B**，小端存储，母控／局控操作码分区，NOP 共用。PC 是指令索引；内存字节地址为 instruction_offset + 16×PC。

| 字段 | bit 范围 | 宽度 | 用法 |
|---|---|---:|---|
| opcode | 127:120 | 8 | 指令种类 |
| flags | 119:112 | 8 | v0.1 固定为 0 |
| a／b／c／d | 111:104／103:96／95:88／87:80 | 各 8 | 寄存器、任务、对象、令牌等索引；d 当前为 0 |
| imm | 79:64 | 16 | v0.1 固定为 0 |
| x／y | 63:32／31:0 | 各 32 | 立即数、跳转或描述符索引，按各指令定义 |

未用字段和保留字节为 0，未知操作码、角色错误、超界索引和非法跳转必须拒绝。精确操作数字段由 [ISA 合同](CONTROL_ISA_V0_1.md)和 [isa.json](../../project/control_isa_v0_1/isa.json)定义；本节不是第二套编码规范。

| 编码 | 指令 | 角色 | 作用 |
|---|---|---|---|
| 0x00 | NOP | 共用 | 无操作 |
| 0x10 | G_CALL | 母控 | 调用目标 Block 的常驻任务，发送参数快照 |
| 0x11 | G_WAIT | 母控 | 等待并消费指定全局完成令牌 |
| 0x12 | G_EVENT | 母控 | 接收匹配的标量事件 |
| 0x13 | G_MOVI | 母控 | 写标量立即数 |
| 0x14 | G_LOOP | 母控 | 有界计数循环 |
| 0x15 | G_BRANCH | 母控 | 条件前向跳转 |
| 0x16 | G_PARAM | 母控 | 从有界不可变 job 参数区读取标量 |
| 0x1E | G_FAIL | 母控 | 显式错误结束入口 |
| 0x1F | G_END | 母控 | 检查全部任务／事件／输出义务后结束 |
| 0x40 | L_OPEN | 局控 | 预约并检查本地对象窗口 |
| 0x41 | L_EXEC | 局控 | 按执行描述符启动原生服务 |
| 0x42 | L_RX | 局控 | 启动片段接收 |
| 0x43 | L_TX | 局控 | 启动片段发送 |
| 0x44 | L_WAIT | 局控 | 等待并消费局部完成令牌 |
| 0x45 | L_MOVI | 局控 | 写标量立即数 |
| 0x46 | L_ADDI | 局控 | 标量加立即数 |
| 0x47 | L_ARG | 局控 | 读取调用参数 |
| 0x48 | L_LOOP | 局控 | 有界计数循环 |
| 0x49 | L_DROP | 局控 | 检查消费／传输义务后释放对象 |
| 0x4A | L_REPORT | 局控 | 报告 READY／PROGRESS 标量事件 |
| 0x4B | L_BRANCH | 局控 | 条件前向跳转 |
| 0x4E | L_FAIL | 局控 | 显式局部故障入口 |
| 0x4F | L_END | 局控 | 满足令牌、资源与输出义务后完成任务 |

例如 G_CALL a=2,b=0,c=1 调用 Block 2 中的任务描述符 1，使用完成令牌 0。128bit 字为 0x10000200010000000000000000000000；内存字节顺序为：

```text
00 00 00 00 00 00 00 00 00 00 00 01 00 02 00 10
```

指令字不是任务消息本身。G_CALL 由发送单元展开为 64B 消息，带上当前参数和版本身份；不携带整段局控程序。

### 5.2 描述符与原生能力

| 记录 | 大小 | 内容 |
|---|---:|---|
| object | 64B | S 对象地址、长度、格式、版本与释放策略 |
| task | 64B | entry_pc、步骤预算、资源／对象需求、参数引用与状态保留声明 |
| execution | 128B | 原生资源／服务、源目的对象、偏移、count、上下文和 native 参数字 |
| transfer | 64B | 端口／peer、对象、分片、偏移、大小及版本 |
| event_binding | 16B | 事件源和消息种类绑定 |
| task_message | 64B | CALL／CANCEL、目标、任务索引、令牌、身份及 8 个参数 |
| event_message | 64B | READY／PROGRESS／DONE／ERROR、确认字节和错误位置 |
| image_header | 128B | 角色、各段偏移与数量、程序／拓扑／ABI／容量版本 |
| data_header | 64B | 数据帧或 stored ACK 的边、分片、对象与确认信息 |

M/N/E/G/R 的原生命令不各占一组通用 opcode，而由 L_EXEC 引用 execution 记录，交给对应宏适配器解释。native0..7 只有绑定已登记的 native ABI／service／native_op 才有含义；codec 能打包这些字段，不证明宏支持该组合。

循环入口计数必须大于 0，零次由前向条件分支绕过；后向跳转只通过有界 LOOP。每任务和镜像有非零 max_steps；WAIT 停顿不重复计步。设备／链路无进展和取消的超时策略另外规定，不能把步骤预算当作物理超时。

## 6. 程序来源、存储与装载

### 6.1 谁生成程序

离线编译工具读取模型／任务 IR、数值合同、宏能力和原生 ABI、Block 库存、真实数据端点图、S／程序容量与版本，输出：

1. 母控 G_* 程序和事件／调度信息。
2. 各 Block 的 L_* 程序、任务入口及对象／执行／传输描述符。
3. 对象布局、参数与 MEM 服务引用。
4. 金属连接需求及部署清单，绑定完整 SHA-256 和程序／拓扑／ABI／容量 ID。

先做映射／数值降级与地址／生存期分析，再编码；无法满足格式、容量、上下文或实际连通性的图应被拒绝。本地程序可有多个任务入口，同一段程序也可由不同参数复用。底座不预存有限模型 ID 对应的完整程序目录。

当前已有编码规范、codec、P接口注册、独立轨迹、有限镜像装载参考及第4步二进制执行切片；完整图编译、其他native服务、通用部署检查与更多指令语义仍待R1／R2／R6。

### 6.2 存在哪里

建议首个可执行版本采用空闲装载程序 RAM；这是逻辑存储角色，不预先声称已有 SRAM 宏或合格物理实现。它与保存张量的私有 S 分开计账；指令和描述符的物理端口、容量、面积／功耗须实现后接收。

| 每局控的静态内容 | 候选容量 | 字节 |
|---|---:|---:|
| 指令 | 256×16B | 4096 |
| 对象描述符 | 16×64B | 1024 |
| 执行描述符 | 16×128B | 2048 |
| 传输描述符 | 8×64B | 512 |
| 任务描述符 | 8×64B | 512 |
| 合计 | — | 8192 |

九局控为72KiB；母控若指令256×16B、事件绑定32×16B，另4.5KiB，共 **76.5KiB静态控制内容预算**。第3步若另存10个128B镜像头，再加1.25KiB为77.75KiB。均不含参数、活动对象／令牌、队列、holding、配置接口及PG／CTS；尚未证明适配所有模型或最优面积。

真实金属 ROM 保留为后续对照，届时需要合法位单元／译码／读出及物理证据；仿真 hex 仅是输入文件，不是金属 ROM 实现。

### 6.3 谁装载，母控是否发送程序

首版推荐由主机／启动侧软件经统一配置装载器寻址母控与各局控的程序存储。配置路径与运行时任务路径在逻辑上分开，装载器及互锁电路也须在 M1–M10 预制并计价；配置总线的协议、位宽、地址表和外部接口尚未冻结。

```text
模型 + 资源/数值/真实连通图
             │ 离线编译
             ▼
母控镜像 + 各局控镜像 + 参数 + 部署清单
             │ 主机通过配置装载器写入
             ▼
母控本地程序存储        各 Block 本地程序/描述符存储
             │ 运行时发送 CALL + 参数
             └──────────────────────► 局控从本地 entry_pc 取指
```

也可以研究由母控转发镜像，但这属于装载通路。本版 G_CALL 不搬运完整程序，24 条运行 ISA 中没有新增装载操作码。下述装载动作是配置协议需求，不能当作已冻结的 MMIO 地址或机器指令。

### 6.4 装载和更新顺序

1. 停止受影响任务域的新接单；将任务、数据、返回及无 tag provider 排空，处理仍归本块的对象／原生上下文，确认可以改镜像。
2. 清除相关镜像有效标志，进入 LOADING；写程序、各描述符段和部署身份。首版单 bank 期间不执行原镜像，不假设免费双缓冲。
3. 读回核验字节；检查镜像 magic／角色／版本、段对齐与范围、PC、容量／资源、原生 ABI 和真实拓扑。主机可承担完整 SHA 与重型静态检查，硬件保留准入／边界互锁；若需片上 SHA，应另计硬件。
4. 仅在全部检查通过后提交有效标志／版本，进入 READY；一次 job 所需的母控及局控镜像必须版本相容后才能启动。
5. 运行时禁止改活动镜像。失败或中途复位后保持不可准入；RAM 内容不因复位自动成为有效程序。更新时需要状态丢弃或转存则显式完成，不把旧数据视作新对象。

第3步建立了[完整镜像与配置装载参考](CONTROL_IMAGE_LOADING_V0_1.md)软件基线；第7～12步已实际验证受限局控的写入／读回／PREPARE＋外部deploy互锁，通用配置接口及真实cohort协调仍待。断电保持、持久回滚、热更新或多镜像调页尚未具备。

## 7. 指令执行与任务生命周期

### 7.1 母控调用到局控取指

1. 母控从自身镜像取指，处理依赖／循环／参数；在 G_CALL 前预约目标接单能力和最终返回空间。
2. G_CALL 复制母控 R0..R7 为参数快照，绑定任务序号和完成令牌；整个消息接受后建立任务义务并推进 PC。
3. 局控验证消息身份和镜像／拓扑版本，按 task_descriptor 读取本地任务描述符，检查资源与 max_steps，把 PC 设置为 entry_pc。
4. 局控逐条取 L_* 指令；OPEN／EXEC 等接受时求值并快照地址／count／偏移，后续寄存器修改不得改变在途操作。
5. L_EXEC／RX／TX 启动有界执行器；L_WAIT 等待真实完成并消费令牌。等待期间其他服务继续前进。
6. L_DROP 前检查全部消费者和传输义务；L_END 前确认服务令牌已消费、输出已确认、应释放资源已释放，才发 DONE。
7. 母控用 G_EVENT 消费准备／进度，G_WAIT 消费完成令牌；全部子任务、事件和最终输出义务结束后 G_END。

### 7.2 接收先行的跨 Block 示例

母控先调用消费者；消费者 OPEN 目的窗口、L_RX 准备接收，随后 L_REPORT READY。母控 G_EVENT 得到准备事实后再调用生产者。生产者完成计算并 L_TX，消费者实际写 S 后回 ACK；生产者收到确认才释放源对象。两方完成后母控消费各自令牌，再调度后继任务。

这是控制顺序示意；完整可执行程序仍需已登记的宏原生描述符、合法端点和 MEM 参数服务。[示例编码](../../project/control_isa_v0_1/examples.json)展示已有骨架，不授予模型或旧 RTL 兼容资格。

### 7.3 状态、错误和完成

局控对象遵循“预约→写入中→可读→消费／外送→可释放”；原地覆盖必须先结束全部旧读。首个 P 原型的 retained_object_mask／retained_context_mask 均为 0；后续 C 的递推状态必须按 job／epoch／版本和原生 R 提交合同接收。

局部 R 提交只改变本地状态。整层 MEM old／next 的根由母控在全部分片及消费者成功后发布；错误保留 old 根。错误时停止新发射，继续安全排空；不能安全排空则 poison 任务域并协调复位。已写 RAM／外存不假设可回滚。

终态成功／错误及确认前缀一次锁存，背压期间保持到接受；硬复位取消、错误结束和成功 DONE 分开报告。取消不能撤回已经对外可见的写入。

## 8. 当前研究进度

本任务进度更新至 R6。PR176 已复核，PR178／182 为 R4 的依赖快照，PR167／152／163 为注明的历史快照。完整 Block 的交付状态以各自实现任务为准。

| 工作 | 已有证据／当前进度 | 尚未具备的能力 |
|---|---|---|
| main 六基础宏 | main 4b1df2c7 已接收 M/N/E/G/S/T 独立宏，原范围含 300MHz 适用最终门 | 不等于新 Block、控制、层级时序或 M11/M12 系统通过 |
| PR176：Block 宗旨 | 08f2ea20，五候选、私有 S 方向、三模型两层图及 13 张图，文档提案已提交；open／未合并 | 新局控、32KiB P.S、实际组网及模型执行未实现 |
| PR180：本任务 | R4 真实存储与复位验证，R5 五类候选模型，R6 生成两套镜像并通过三项 RTL 场景 | 当前 RAW16/P 控制资格。R7 成本与外部集成待执行，PR 为 Draft |
| PR178：私有 S | cdbb3d53，P4／N4／N5三种16KiB私有S叶级配置最终交付；本分支固定4份源码及source blob | 不是三个完整Block；P32KiB仍待，PR open／未合并；物理结果沿用来源证据 |
| PR167：新 R | c97353cf；R256／R1024 各 16 项独立物理门及 192 项最终网表功能通过，状态 payload 分别 2／8KiB；open／待审查 | 未合并；本 ISA／新 Block 适配、层级时序及 M11/M12 系统资格不自动转移 |
| PR152：已有控制切片 | 55243d2c；线性 G1、真实 edge S ACK、单 F 两次服务、连续两 job 和 89 项不同定向检查 | 是旧表／旧接口的有界切片，不是本 ISA 或五种新局控的完整实现 |
| PR163：原组合物理 | 64b7c85；最新说明 checkpoint72，有限路线／诊断有进展 | 仍无完整零冲突全图、几何／PG／三档 RC 下 300MHz 联合通过；Draft／open |

“已交付编码工具”只表示位编码／记录打包有参考和检查，不表示已经把完整大模型编译成能在芯片运行的程序。各任务保留原负责人、分支、目录和作业；本任务不接管 PR178／167／163。

容量研究还指出 Qwen input＋完整 gate＋up 同时驻留为 **41KiB**，超过 32KiB；完整 Mid＋input 或 gate＋input 为 **23KiB**。16KiB 方案须显式分片／重放，F0 满额及 Falcon J0 仅余 1KiB 等边界仍在，不能用控制指令掩盖存储不足。

## 9. 接下来的研究步骤与验收门

| 阶段 | 研究工作 | 进入下一阶段的可验证条件 | 状态 |
|---|---|---|---|
| R0 方案与编码参考 | 本综合方案、五类组成／连接、ISA 编码、参考工具和容量边界 | 文档与机器规范一致、来源／进度可追溯，软件检查如实交付 | 方案／编码基线已交付；控制RTL进展见R3，完整Block为外部任务 |
| R1 合同与装载基础 | 固定宏／私有S版本及原生字注册；控制连接／真实端点；容量／数值／对象；完整镜像／部署检查、配置接口／有效互锁 | 服务真实端口对应；错误ABI、缺路线、越界、半装载／运行改写均拒绝；资源账完整 | P接口、有限镜像和最小局控装载互锁已交付；通用拓扑、其他服务及完整硬件合同待完善 |
| R2 二进制执行模型 | 直接读取镜像的母控／局控解释器；有限S／队列／端口／上下文；装载／版本、背压／错误／复位 | 与独立参考比较；不能依靠无限队列或TB注入内部RAM；READY／ACK／释放和错误终态 | 14类直线切片及有条件取消／复位已模型验证；通用指令／其他服务、真实provider确认仍未完成 |
| R3 局控RTL与接口验证 | 取指、装载准入、对象／上下文及适配；有限协议peer表达P profile | 同一控制RTL执行不同程序，配置／命令／返回／版本／背压／错误与连续任务有实际DUT证据 | 首个受限P profile通过：9局控指令，128当前RTL场景、173软件检查；原生S／通用能力及系统接入尚待，不扩大为完整控制器资格 |
| R4 母控与多局控协同 | 母控取指、双LC／私有S、真实DMA／FIFO、ACK依赖及协调复位／重装 | READY先行、实际存储ACK、连续job、有限信用、错误隔离、旧响应flush及新epoch准入 | R4.1～R4.4有界门通过：49/49新RTL、14/14静态；provider生产ACK／M11/M12／完整Block及物理仍为外部门 |
| R5 五类控制 profile 与状态 | 用资源／原生 ABI profile 研究 U/F/J/C 的控制序列、分支／循环、old／next、取消／协调复位；数值转换作为外部服务合同 | 资源可达性、非零初始控制状态、提交条件、消费者义务、错误前缀和终态保持通过；计算数值正确性另由实现／模型任务验证 | 有界研究交付：5类candidate合同／二进制模型，34执行／30拒绝／114cohort／4突变；非零old/next、消费者／提交／UNKNOWN查询；新增RTL与真实native/reset仍待 |
| R6 控制程序生成与检查 | 从有界任务 IR／模型控制需求生成 G_*／L_* 程序、描述符和依赖；MEM／原生运算沿用外部合同，研究新增未预存合法控制图 | 同控制硬件和合法拓扑换程序；程序 SHA、资源／对象／上下文检查和独立控制轨迹正确；拒绝不支持映射。完整数值编译／模型质量为外部任务 | R6.1～R6.3 通过。两套生成镜像、3/3 RTL 场景、4 个成功任务及 1 个预期隔离 |
| R7 控制成本与外部集成交接 | 记录控制器、程序存储、协议状态和接口的资源／带宽需求；形成真实 Block 接入和物理约束／验收清单；必要时独立表征控制逻辑 | 控制成本有来源；完整 Block 数据通路／M11/M12／PG／三档 RC／300MHz 和模型质量验收保留为外部门，处理任务待指定；不计为本分支已实现 | 待执行；完整系统验收由外部集成负责 |

第1～15步历史门及R5候选模型保留，当前新增R4.1～R4.4将有界传输控制连接到真实私有S／DMA并验证可信cohort reset。当前9局控／5母控指令和RAW16服务资格不扩大为全ISA／五种完整Block。R4 服务器作业均已结束。用户已授权 R6，R7 仍待执行。每阶段核对 PR176。

## 10. 本轮交付与恢复入口

R6.1～R6.3 已交付任务 IR、三端镜像生成、独立检查和服务器 RTL 联跑。原 Markdown 与同名 PDF 逐步更新。R6.1 与 R6.2 分别为 237955a4 和 76e301ee，最终提交与远端读回见 PR180。

本地独立部分 API 工作副本为 D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/179/control-r6-13e577c/delivery。服务器 97286 已结束，源码、日志、结果和校验和见[验证索引](../../work/Melodydt/179/control-r6-validation-index.json)。恢复时核对 Issue179、PR180、PR176、本人进度及交接。R7 为控制成本和外部集成。

PR180 为 Draft，Issue179 保持 in_progress。登记 PR5 待合并。board.json 缺失且连接器无 Projects 条目能力，看板待管理员核验。

## 11. 逐轮研究进展

| 轮次 | 实际交付与验证 | 当前边界／下一步 |
|---|---|---|
| R0，d6429607 | 两级方案、24操作码／9记录、编码参考及8测试 | proposed，未执行硬件 |
| 综合／范围修订，614cdab4／df3e7a26 | 完整连接／装载执行说明；明确本分支只研究控制 | 完整Block与系统物理为外部门 |
| 第1步，afd96b35 | 6模块149端口、12个P服务、2 profile；15新＋8既有测试 | P接口基线；实际运行前置条件仍待验证 |
| 第2步，add63270 | 3组程序、29指令、4条参考轨迹；当时27组新检查 | 第3步纠正CALL arg0并增回归；独立参考不等于DUT通过 |
| 第3步，本轮父add63270，最终提交见PR180回执 | 7份完整镜像2080B、配置准入／恢复软件模型；30新增＋1轨迹纠正回归，累计81组 | 没有PC／RTL执行；下一步独立二进制PC执行模型 |
| 第4步，本轮父8cb31090，最终提交见PR180回执 | 二进制PC解释器＋有限peer；9次运行100退休／193观察，26新增、累计107组 | 软件取指执行，RTL仍未执行；下一步取消／协同复位／旧响应隔离 |
| 第5步，本轮父c22dde69，最终提交见PR180回执 | 9取消／poison＋9恢复，2模型复位cohort；新增30、累计137组 | 无tag隔离依赖provider合同，未授予硬件资格；下一步局控RTL接口与状态机 |
| 第6步，本轮父e079924c，最终提交见PR180回执 | 92信号／状态机候选，单口与信用合同；36新增、累计173组 | 人工时序非DUT，HDL未编译；下一步功能局控RTL最小切片 |
| 第7步，本轮父41777f1d，最终提交见PR180回执 | 最小功能LC RTL＋行为peer；10场景3926边沿，5执行轨迹3061边沿独立核验，173既有检查 | R3最小子集，非真实M／Block；下一步取消／异常排空和服务适配器，再扩RAW16／RX/TX |
| 第8步，本轮父a54cbc4，最终提交见PR180回执 | CANCEL／有界排空RTL；服务器173既有检查＋10原RTL＋22取消场景、18719取消边沿，6项轨迹破坏均拒绝 | 19安全结束、3预期隔离；下一步运行异常与恢复，再继续R3～R5；方案／PDF固定文件持续更新 |
| 第9步，本轮父96b8280，最终提交见PR180回执 | 当前子集运行故障／128周期无进展隔离，服务器173既有＋10原＋22取消＋29故障，12项轨迹突变拒绝 | 有限peer复位／完整重装后新epoch成功；下一步适配器／对象与收发，R3整体、R4／R5未完成 |
| 第10步，本轮父af680f3，最终提交见PR180回执 | 严格M clear适配器；服务器173既有＋61原控制RTL＋10协议peer／5真实M场景，3轨迹突变拒绝 | 现有M源未改，5次真实命令／响应；下一步对象窗口／寄存器／收发事件，R3整体、R4／R5仍待 |
| 第11步，本轮父ddac1c8，最终提交见PR180回执 | 单RAW16预约／DROP／取消释放、显式loaded位；服务器173既有＋76原RTL＋27对象场景、3新突变拒绝 | 没有S数据或寄存器值读回证据；下一步RX/TX／ACK／READY，R3整体、R4／R5仍待 |
| 第12步，本轮父76fc765，最终提交见PR180回执 | 受限P／RAW16九局控指令；173既有＋103原RTL＋25新收发，4项新轨迹突变拒绝 | 寄存器读值、有限SRAM写后ACK及连续任务通过；原生S／通用能力仍待，下一步R4再R5 |
| 第13步，本轮父2384c31，最终提交见PR180回执 | 母控5类指令、2目标／8token，26场景12218边沿，4突变拒绝 | 双子端peer；R4实际双局控尚待，之后R5；原方案／PDF原位维护 |
| 第14步，本轮父dc23b38，最终提交见PR180回执 | 实际母控＋2LC，10集成15395边沿／4突变拒绝，25局控与26母控回归证据 | R4有界门满足；非原生S／完整Block，下一步R5五类控制profile与状态 |
| 第15步，本轮父2e6d211，最终提交见PR180回执 | R5五类candidate，34执行12231 model ticks／1263退休／153服务、30拒绝、114cohort与4突变拒绝 | R5有界研究交付；新增RTL／native／真实复位仍待，按用户边界停止；R6／R7未执行 |
| R4.1，父ecd6f49 | 源版本／端口／全身份／复位合同，14静态通过，6依赖逐字一致 | commit179c1f79；不等于RTL仿真 |
| R4.2，父179c1f79 | 真实S10集成／8突变拒绝，97276通过 | commit62148314；非完整Block |
| R4.3，父62148314 | 真实DMA12集成＋10桥接／8突变拒绝，97279最终通过 | commit5886269a；外部MEM为有限peer |
| R4.4，父5886269a | 真实复位6集成＋11协调器／4突变拒绝，97281最终通过 | 最终SHA见PR180；可信provider证书，非生产复位树／物理资格 |
| R6.1，父13e577c5 | RAW16/P 任务 IR。2 份准入、18 份拒绝 | commit237955a4 |
| R6.2，父237955a4 | 联合及分组等待镜像可重复生成，现有装载准入通过 | commit76e301ee |
| R6.3，父76e301ee | 6 份镜像变体拒绝，作业97286完成3个RTL场景 | 最终提交见PR180。下一步R7 |
