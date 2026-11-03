# H1：A2/F1原生帧、三图调度与新增edge-store资源审计

Issue151 / PR152，Melodydt；日期2026-11-03（Asia/Shanghai），本轮研究输入`08451c3a563cdb331a3516d83cbf9647cd0554b1`。本文依据隔离研究包内现有A/F RTL、接口合同和既有服务器回执进行只读审计，新增的是本说明，不修改叶宏、kernel/controller或TB，不启动数值计算、RTL仿真或物理流程。

结论：一个A2实例、一个F1实例，加上**显式新增的一份16KiB edge-store**，在下述固定shape、参数流可进展、单端口串行owner和完整物化的调度条件下，能为三张候选图构造有限槽位安排。三图峰值分别为2、2、3个4096B槽，均不超过4槽。这是容量与生命周期方案，不是通用端点、母顺序器、F2入口或新图RTL已经完成的证据。

当前总方案以[混合控制主候选](HYBRID_METAL_CONTROL_PLAN.md)为准。H0方案交付、H1规格/静态映射、H2共同RTL及H5物理是不同状态；本文不将现有固定kernel资格转成H2或M11/M12资格。

## 1. 命名与现有实现

| 研究名称 | 实际现有模块/能力 | 本文使用方式 |
|---|---|---|
| A2 | `block_w4_afull_top`，H1024、Sq2、Q16/KV8、D128，完整preNorm/QKV/headNorm/RoPE/causal Attention/Wo/原X残差 | 一次处理两个token，输入和输出都含两行hidden |
| F1 | `block_w4_f1024_top`，H1024/I3072，单token RMS/SwiGLU/down/原输入残差 | 每次只处理一行；本轮限定既有Fin10/WFin7基线 |
| F2 | 本文图层的“两行F”逻辑调用 | 必须lower为同一F1的row0、row1两次完整调用；不是已有count2入口，也不新增第二F实例 |
| edge-store | 候选新增16KiB数据存储，4个4096B槽 | 独立于A/F的S、T及参数存储；当前没有共享store/通用端点集成RTL |

A2已有有限完整整数RTL证据；AF1024已有特定A2→两次F1固定组合证据。后者采用专用父FSM、2KiB F gamma FFbank和A_T直接保活，**没有本文的edge-store**，不能把它描述成三图已经运行。QUALITY95979证明官方FP32参考和Fin10 W8的独立F有限回归，未把现有AF1024控制器或本候选F1入口改为可动态切换W8。

## 2. 原生帧与参数合同

所有字均为128bit/16B，compact S16的lane0位于低16bit。以下hidden路径限定S16 Fin10；其它精度、布局、长度、KV cache或任意shape不能由相同位宽推定支持。

| 项目 | A2一次调用 | F1一次调用 | F2一次逻辑调用 |
|---|---:|---:|---:|
| hidden输入 | 两行×128字=256字/4096B | 一行128字/2048B | 两行共256字/4096B |
| 非权重参数装帧 | H gamma128字、Q gamma16字、K gamma16字、两位置系数32字，共192字/3072B | gamma128字/2048B | 同一或指定gamma逐行重放两次，共256字/4096B |
| 实际完整输入帧 | 448字/7168B | 256字/4096B | 两次256字，共512字/8192B；不是一个512字原生帧 |
| hidden输出 | 两行token-major256字/4096B | 一行128字/2048B | row0后row1拼成256字/4096B |
| 权重实际供应 | 6MiB | 9MiB | 18MiB |
| 权重请求/数据拍 | 24576请求×16拍=393216拍 | 36864请求×16拍=589824拍 | 73728请求/1179648拍 |

A2输入0..255为两行X、256..383为H gamma、384..447为Q/K gamma及RoPE系数；后64字实际写S512..575。最后一个字的S写ACK退休才建立`input_stored`，然后才能接受一次start。A2输出为原X残差后的Y，不是context、Wo中间值或Norm结果。

F1输入0..127为本行hidden、128..255为gamma，最后一个字的S写ACK后才建立`input_stored`。F1输出已经加上本行原输入残差；不能把F残差误取为A的原X。当前F没有与A相同的独立job admission/generation入口，输入阶段错误可以清帧而不产生子DONE，因此未来共同wrapper必须拥有独立任务义务和失帧检测，不能只等一个不存在的prestart DONE。

F2的row0必须完成输入256字真实写ACK、start、全部计算、128字输出目的写ACK、T实际RELEASE和DONE消费后，才复用F1装row1。F2的整体`INPUT_STORED`事实只有两行各自的完整帧都已真实建立后才成立；row0会在该整体事实之前先运行。局控须锁存已经完成的行事实，不要求两帧同时驻留在一个F的S内，也不新增另一份hidden数组。此内部展开是候选局控工作，不应让母控逐M op或逐S字调度。

F2的输出槽按row0写偏移0..127、row1写偏移128..255。row0完成仅建立部分私有数据；第二行数据和任务终态闭合之前，不发布为完整两行结果。

### 参数身份与数值边界

A2权重口使用job/generation32、seq16、version16、matrix2/head4/group7/chunk6，返回index4。F1使用自身start生成的job16、seq16、version16、matrix2/group9/chunk7，返回index5。A严格拒绝接受的坏/旧/未来tag，F保留原先较旧job/seq排空策略；它们不是统一的MEM或通用图端点协议。F version0不合法，A version0合法。参数身份只标识数据，不改变M READ shift、N epsilon或本地程序。

本轮A/F基线向量及gamma为Fin10，投影/MLP权重为S8 Fin7；A概率Fin14、RoPE系数Fin14。完整K归约后才RNE；N epsilon_code1为`2^-20`，不等于源`1e-6`。这些已测整数profile不接受trained模型质量，也不把W8的独立静态编译验证变成同一F局控已实现多入口。

H gamma、Q/K gamma、RoPE系数、F gamma、权重、参数描述符、程序和控制cache**均不计入本文16KiB edge-store**。既有kernel必须获得完整参数帧和provider服务；如果未来需要gamma bank、参数cache、路由寄存器或版本表，必须另列真实存储/控制成本，不能藏在四个hidden槽或所谓“已有参数”中。

## 3. 原有S/T不能充当共享edge-store

| 资源 | 物理容量与本profile生存期 | owner/释放边界 |
|---|---|---|
| A的S | 16KiB；峰值Norm4096B+work4096B+context8192B=16384B，无额外余量 | LOCAL/E/N独占普通口；N/E直到末个目的写ACK及响应消费才归还owner；loader在独占阶段走宽口供M |
| A的T | 宏为6KiB/384字；先原X256字4096B，真实RELEASE后才新BEGIN最终Y256字4096B | 同时只有一个lease；不能把剩余2KiB当第二事务，不能任意随机读或假定第二读者 |
| F的S | 宏16KiB；本profile预约932字14912B，含原输入、gamma、Norm、完整mid3072、输出及宽容器/scratch | LOCAL/N/G/E独占普通口并消费写ACK；余量不是已经集成的通用结果恢复区 |
| F的T | 宏6KiB；每F1输出128字2048B | 实际输出take后仍须RELEASE，再DONE；不支持保留前次输出并直接BEGIN下一次 |

A同一M的raw累加上下文、N上下文及S/T区域都有明确生命周期。不能在一个尚未完成的M归约中插入另一投影，不能把S loader的宽接口理解成不受owner约束的第二个普通访问口。

“关闭A/F实例”在这里要求当前输出已被目的存储确认、源T真实退休/RELEASE、正常DONE已消费，才可重入。仅看到最后一字、输入ready、数据已捕获或某个令牌均不满足这些条件。

## 4. 新增edge-store的明确成本与最小语义

目标新增一个16KiB S类存储：1024个128bit字，划分为4槽，每槽256字/4096B。候选地址为`slot*256+word_offset`，slot2bit、offset8bit；采用一个普通读写端口、一个受控owner和有界在途事务，不允许多个push-pull源金属短接。初版按串行粗任务安排读写，无需假设同时多读者或双端口。

若用现有S叶宏承载，普通口有req/ready、valid/take及128bit数据，写操作也必须消费真实ACK；原生S没有error pin，不能虚构新增硬件故障检测。可复用现有单在途S helper的机制，但共享owner、槽位/版本管理、TX/RX与控制连接仍需新增实现。edge-store的宽loader能力不在本方案中使用，不能靠未证明的端口并行性计算吞吐。

每槽至少需要以下候选控制事实，其具体编码和寄存位数尚未由本文冻结：

- 空闲、保留/私有写入、完整可读、释放中的生命周期；有效长度和版本/任务归属。
- 生产者关联、预期字数、已存储进度、错误/poison和实际消费者集合。
- fork各消费者的输入存储完成事实；slot引用/别名的生存期。
- owner请求/响应关联、背压保持及协调reset后的有效性清理。

以上metadata、ACK/事件保持、TX/RX holding、MUX/仲裁、地址生成、局控/母控和控制存储都在16KiB payload容量之外。本文不以“只加一S”声称有源面积只增加一颗RAM。

### 不可合并的三种确认

1. **kernel输出进入edge-store**：源T字保持，RX防重复捕获并发真实edge S写，只有该写ACK完成后才能退休对应源字；整帧写完后，源仍须实际RELEASE/DONE才能再次运行。
2. **edge对象进入kernel**：TX从edge S读取并保持，按目标原生帧将hidden与参数正确装入；捕获并非目标整帧已存储。只有目标公开的完整`INPUT_STORED`事实建立，才能确认该消费者不再依赖相应输入对象。
3. **edge对象回收**：所有实际消费者均已建立所需`INPUT_STORED`且没有未完成读取/别名引用，才释放槽；不必等消费者整个运算DONE，但不能用输入ready代替此条件。

AF1024用锁定F入口的ready重新开放观察逐字ACK，是固定接口证明，不是上述共享端点已经实现。H2必须验证新的真实存储路径、ACK保持、owner迁移、错误/partial和取消行为；母控处于WAIT时这些服务仍须前进。

## 5. 三图的可构造串行安排

以下a/b/c/d均为两行hidden对象，大小4096B。结果槽可以在生产者启动前保留，但只有真实完整存储和规定的关闭条件完成后才作为完整图结果使用。初始hidden由明确输入端装入A2；若另选择先存到edge-store，也须单列该初始对象的读写，不能静默增加常驻副本。

### G1：A2→F2

| 阶段 | 槽0 | 槽1 | 关键门 |
|---|---|---|---|
| A2生成a | a私有→完整 | 空闲或为b保留 | a的256写ACK后源A T退休/RELEASE/DONE |
| F1处理a.row0 | a保留 | b.row0私有 | F0完整stored→RUN→结果写ACK→RELEASE/DONE |
| F1装入a.row1 | a保留→可回收 | b.row0保留 | F1.row1的hidden及gamma全部实际stored；此时整个F2输入已建立 |
| F1完成row1 | 空闲 | b完整 | 第二行目的写ACK及F1 RELEASE/DONE后F2闭合 |

峰值为a+b两槽8192B。输入a不能在row0完成后即释放，因为row1尚未装入。无需额外4KiB Y数组，也不能把F2说成现有单次双行kernel。

### G2：A2→F2→A2→F2，同物理A/F重入

| 步骤 | 输入/输出 | 候选槽绑定 | 回收/重入条件 |
|---|---|---|---|
| A0 | 外部X→a | a=槽0 | A0输出全部存储、T释放、DONE关闭 |
| F0两行lowering | a→b | b=槽1 | a在两行输入均stored后释放；F0两次T/DONE闭合 |
| A1 | b→c | c复用槽0的新版本 | b仅在A1完整448字帧实际stored后释放；A0必须已关闭 |
| F1两行lowering | c→d | d复用槽1的新版本 | c在两行输入均stored后释放；F0必须已关闭 |

只需两个物理槽ping-pong，峰值8192B；a/c、b/d是不同对象/版本，不是覆盖仍有引用的数据。同名A/F实例的复用不保留旧M/N/T上下文。本安排没有把旧S/T批次重新打开，也不依赖T输出回放；需要的中间值已真正物化在新edge-store。

### G3：A2→fork(F2a,F2b)→runtime p SELECT/phi

两个F2都必须实际运行，参数身份分别为Pa/Pb；p仅选择完整b或c，不做ADD、混合或额外数值转换，也不把未选分支跳过执行。SELECT/phi的条件、输出别名及引用管理是H2待实现控制能力，不是已经存在的宏op或母控。

| 阶段 | 槽0:a | 槽1:b | 槽2:c | 关键事实 |
|---|---|---|---|---|
| A2完成 | 完整，消费者集合{F2a,F2b} | 为b保留 | 为c保留或空闲 | A T实际释放/DONE后可重入，但a仍属于edge-store |
| F2a两行完成 | 保留，F2a输入已stored | 完整b | 保留 | a仍有F2b这个消费者，不能回收 |
| F2b装row1 | 两行输入均stored后可回收 | 完整b | row0及正在生成的row1 | F2b参数/gamma仍须按其身份真实供应 |
| F2b关闭 | 空闲 | 完整b | 完整c | 两个F2都已真实关闭，p才选择输出别名 |
| SELECT | 空闲 | 依p保留或回收 | 依p保留或回收 | 未选对象无其它引用才回收；所选槽保活至下游规定完成 |

保守峰值为a/b/c三个槽12288B，第四槽未被当作隐藏的参数、控制或输出副本。phi通过已预制地址选择/路由和别名规则指向b或c，**不自动产生第四个4096B复制结果**；如果实现选择物理复制，必须另计槽、搬运和真实ACK，不能沿用本表的零复制语义。

本图没有新增算术kernel，也不证明条件/别名控制已经实现。若任一必执行分支错误，不能擅自退化成选择另一个成功分支；错误路径由完整控制规格明确接收。外部最终消费者的完成合同也必须另定，host `out_ready`不能伪称通用REMOTE_STORED。

## 6. 参数流量与传输下界

| 图 | A2调用 | F1实际调用 | 权重流量 | 非权重参数装帧供应 |
|---|---:|---:|---:|---:|
| G1 | 1 | 2 | 6+18=24MiB | A3072B+F4096B=7168B |
| G2 | 2 | 4 | 12+36=48MiB | A6144B+F8192B=14336B |
| G3 | 1 | 4 | 6+36=42MiB | A3072B+F8192B=11264B |

这些是现有kernel实际请求/帧的流量；不包含hidden和协议header/metadata，也不暗示已有真实MEM、参数缓存、带宽或能量结论。即使同version，F每行仍重新供应9MiB；两个分支的参数身份不同，更不能把共享权重当免费条件。若未来预制缓存并证明命中/容量，可单独改变该流量，当前不借用edge-store承担它。

一个完整4096B边对象写入edge-store需要256次普通写及真实ACK；每个两行消费者至少读取256个字。按本方案完整物化，G1/G2/G3分别形成2/4/3个结果对象；内部图边分别消耗a一次、a/b/c各一次、a两次。故不含外部初始输入和最终输出导出的edge普通口数据访问下界分别为：

- G1：512写+256读=768次；若最终b也从edge导出，再加256读。
- G2：1024写+768读=1792次；最终d导出再加256读。
- G3：768写+512读=1280次；SELECT不复制，所选对象导出再加256读。

每次请求仍有响应/holding/owner开销，不能将这些访问数直接当周期、带宽或PPA。单端口安排可串行完成，但没有吞吐目标就不宣称最优；不要求A/F同时计算，也不声称加S后性能自动提高。

## 7. 已有基础与H2实际缺口

| 范围 | 当前已有 | 尚缺/本轮不实施 |
|---|---|---|
| 算术与固定kernel | A2与F1基线RTL、单S owner、loader→M、N/E/G外侧controller、有限真实T生命周期 | 公共可调用入口与统一任务义务；不能用模块存在代替新图集成 |
| A2装帧 | 一体448字流和完整stored | hidden/参数独立端点的实际组帧、参数引用/身份与元数据适配 |
| F2 lowering | AF1024已有一个特定两F调用父FSM实例 | 可被共同程序调用的F2局部入口、row进度/整体stored/输出拼接、失帧与双ID预算 |
| edge-store | 可借S普通口及单在途helper机制 | 新S实例、单owner仲裁、4槽版本/引用、TX/RX holding、源SACK退休和返回事件保持 |
| 三图控制 | 已有候选图/指令语义研究 | 同一固定母顺序器/本地入口及控制表、G2重入、G3 fork/SELECT别名、取消/poison/reset和回收 |
| 参数与外存 | 有序weight provider与真实数据流验证 | A/F不同job域的映射和有限ID准入、参数服务/缓存、真实MEM及带宽 |
| 永久绑定 | M1–M10/M11–M12分工候选 | 金属可编码控制存储、预制端点/路线、译码/读回和几何/STA/PPA证明 |

目标资源为A2的M1/N1/E1/S1/T1、F1的M1/N1/E1/G1/S1/T1，再加edge S1，即**M2/N2/E2/G1/R0/S3/T2，共12个叶实例**。A/F各局控、新母顺序器、共享store controller、端点/参数适配、metadata及控制存储另计。这只是H1的共同目标候选，不称现有物理共同底座冻结。

H2验收至少需要：相同固定RTL实例图运行三种表/路线内容；真实edge写ACK后源退休；所有消费者INPUT_STORED后槽回收；A/F实际RELEASE/DONE后重入；G3两分支不同参数均真实执行、p选择与未选引用回收；背压、非法字段/版本、prestart错误、取消/reset、有限ID耗尽及前缀不回滚。不能用软件计数、直接赋RAM或替换synthetic结果代替这些路径。

## 8. 直接来源与证据范围

- [A2原生接口/生存期](rtl-contracts/AFULL_PORTS_AND_LIFETIME.md)§1–7及[A2实现/实跑报告](W4_AFULL_IMPLEMENTATION.md)。源码[block_w4_afull_top.sv](../project/rtl/block_connection_w4/block_w4_afull_top.sv)：输入及metadata L114–120、共享owner L195–215、原生控制 L235–285、T事务 L290–310、输入ACK L366–370、最终释放 L551。
- [F1实现与资源](W4_F1024_IMPLEMENTATION.md)及[整数合同](W4_F1024_NUMERIC_CONTRACT.md)。源码[block_w4_f1024_top.sv](../project/rtl/block_connection_w4/block_w4_f1024_top.sv)：不同公共ABI L4–18、stored/start/version/ID门 L102–105、S地址路由 L141–147、最后帧ACK L291–295、实际T释放后DONE L387–388。
- [既有AF1024固定组合合同](rtl-contracts/AF1024_PORTS_AND_LIFETIME.md)及[34CASE/12流实跑报告](W4_AF1024_IMPLEMENTATION.md)：2KiB gamma FFbank、两F调用、逐字目的SACK后A_T退休、不同provider和父任务义务。它不是本文新增共享store的实现证据。
- [S原生封装](../project/rtl/block_feed_v1/block_feed_s_macro.sv)L4–29、[S16KiB存储](../project/rtl/block_feed_v1/block_feed_s16k.sv)L6–36、[S helper](../project/rtl/block_connection_p2/block_p2_s_ctrl.sv)L41–84：读写应答、普通/宽口仲裁、写ACK及单在途保持；原生没有error输出。
- [T6KiB](../project/rtl/block_v1/transaction6k.sv)L1、27–39、51–68：384字、单消费者lease、计数/owner/generation及实际RELEASE。
- [QUALITY参考及W8有限回归](L4_QUALITY_REFERENCE_W8_REPORT.md)：95979的官方参考28项、独立F8fixture/56标记范围，不接受本三图、trained整数AF质量或共同底座物理。

本文不重写原有实跑source、失败记录、54份runtime/旧锁或八样本旧24GAP。新增4槽容量安排与调度推导可以作为H1图/资源检查器的输入，必须通过H2真实集成和独立验证后才能提升实现状态。
