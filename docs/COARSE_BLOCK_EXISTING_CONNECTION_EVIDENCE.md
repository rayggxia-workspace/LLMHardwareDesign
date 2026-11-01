# 六种大Block内部连接：已有实现、可借组件与未集成边界

研究父提交`051fddb9a3d2cecd4b76c43d07ec8581db9402ce`，七宏叶源固定`707878621b2add4ed218b8c43df2e95c9a56e2ba`。本轮通过Melodydt GitHub连接只读核验，不改RTL、不运行仿真、不访问服务器或ref-project。

**大Block仍需做内部宏端口同步。**边界变粗后，母控可以只调大Block，但局部控仍要实际产生原生命令、保持/拆拼数据、处理背压和ACK、维护上下文、完成/提交/释放及错误。M11/M12只绑定大Block之间，不会替内部提供MUX、FIFO、控制器或数值转换。

本仓库已有多条历史组合，不能概括成“全仓只有MST”。同时，旧组合使用的M/V/共享算术协议不等于当前七宏原生接口，不能因为module存在就把A_plain/A_gate/F/D/H/X六个完整profile标为完成。

## 1. 核验范围与可复查数量

机器证据见`work/Melodydt/151/island-connection-evidence.json`、目录元数据见`work/Melodydt/151/island-connection-inventory.json`。已列出当前12个指定RTL目录共43个文件；远程读取40个完整文件，并将其余相关核心源的本地字节与GitHub目录blob对应，索引53个当前文件及1个PR133历史源，形成16个组件结论。所有引用固定到父提交或明确标出的历史提交。

`localonly/`保存只供本轮阅读的源码快照，**整个目录禁止上传或纳入正式交付**。正式交付为本Markdown、island-connection-evidence和island-connection-inventory等说明/索引，不是源码副本；PR133状态内嵌在evidence.JSON的PR133字段。索引不保留带token的下载URL或账户邮箱。

## 2. 现在的v2有限组合确实连接了什么

[P2最小顶层](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/project/rtl/block_connection_p2/block_p2_mst_top.sv#L71)真实实例化S普通口helper、`block_feed_s_macro`、`block_v2_m`及`transaction6k`。

| 路线/同步 | 已有实际内容 | 不能扩张的结论 |
|---|---|---|
| S内部storage→loader | 原生storage+feeder实连，有限队列与A/B背压 | loader不是通用外部512bit DMA |
| S.loader→v2 M | P2直接接A128/B512及bank/row/tile/wide/half/ready | done只表示装载排空，不是EXEC完成；多个M要另加选择器 |
| M→S | 区分配置/EXEC ACK与M3 rawS64，保存四个128bit结果字并消费S写ACK | 没有因此实现M→N/E/G/R的所有格式与数值转换 |
| S→T | 普通S读、holding、按index连续写T，之后commit | T不是任意格式转换器或无限output buffer |
| T→外部流 | 背压保持，末字take后显式release，再完成job | 没有因此实现通用T→S writer、fork或同T整批重入 |
| 端口owner与异常 | 单在途S helper、固定SERVICE/WAIT母顺序器、局部状态机、错误过滤及协调reset | 不是完整指令ABI、所有profile程序、无复位取消或通用调度器 |

[S普通口源码](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/project/rtl/block_feed_v1/block_feed_s16k.sv#L12)中写ACK为din回显；[loader L107–108](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/project/rtl/block_feed_v1/block_feed_loader.sv#L107)等全部请求/响应/A/B排空才done。S.busy只代表feeder，不能判断普通口响应是否空。

保留的[真实ModelSim回执](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/work/Melodydt/151/phase2-rtl-evidence/run-receipt.json)记录19场景：6个S helper、13个固定S8 K8/N8 MST场景。7078786只标识原生叶宏来源；三份P2新RTL和两份TB运行时尚未提交，由回执输入SHA追溯，随后随1cc43a93交付。五份文件的当前051字节与该真实run输入SHA匹配。**本轮未在051下重新执行**；N/E/G/R在该P2套件只编译，不因编译变成功能通过。[P2状态](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/work/Melodydt/151/phase2-verification-status.json)仍为`P2_fully_accepted=false`，完整矩阵、MEM和物理未完成。

## 3. 当前树中已经存在的legacy组合

| 当前固定路径 | 真实内容/可借部分 | 与当前七宏/六profile的差距 |
|---|---|---|
| `block_feed_v1/block_feed_pair.sv` L27–65 | S→旧feedM→T的可综合测试fixture；明确active capture MUX与A/B stall | 实例是`block_feed_m`；不是v2M，非全功能大Block |
| `shared_services/m106.sv` L18–76 | 已有Vprep→Mfront→Norm的阶段控制、S/外址访问、owner/version/epoch、drain | 固定旧数据布局及算术服务，不是v2M_CTRL或完整新F/X |
| `shared_services/norm106.sv` L1–33、40–65 | S读写、gamma流入、外接S32乘法及U128 SFU、Norm多遍控制 | S32数据与旧数值公式，不是v2N count/S16/aux ABI |
| `shared_services/shared106.sv`、`shared_gdn/shared109.sv` | 已有真实服务MUX、互斥controller lease、共享S/S32/SFU/MEM link、epoch及排空 | 三/四个旧profile，非当前六profile七宏结构；程序/数值需迁移 |
| `block_v1/shared121.sv` L35–70 | 真实shared109输出→T6K，成功commit、错误/reject撤销、release前阻挡core ACK | 旧core输出协议与固定owner对应字数，不是通用T/S桥 |
| `shared_services/r106.sv`、`shared_gdn/gdn109.sv` | 旧Falcon/GDN有限状态核、外部old/candidate页、宽算术与发布/排空控制 | old单位/精度/上下文、固定head范围与native R S32/8lane/owner32不同 |
| `block_library_v1/block_v1_reassembled.sv`及`block_v1_vs.sv` | 旧VS共享银行和byte乘法拆分/重组 | [旧README](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/project/experiments/block_v1/README.md#L1)明确裸M8/混合VS为历史试验，不作为当前最终七宏边界 |

这些模块证明已有控制与组合经验可复用，不能说所有同步都要从零发明。以下几项接口差异必须在迁移时明确处理：

1. **旧feedM与v2M针脚相似、命令不兼容。**旧`block_feed_m` L216–221的op4是MERGE：factor[31:0]、shift[38:32]、clear[39]；v2M op4是SET_SCALE：factor[15:0]、left_shift[20:16]，EXEC为op10。旧op5的shift字段也与v2不同。复制pair驱动时必须重写命令/数值逻辑。
2. **更早的`block_v1_m`连cmd_data都是128bit**，通过op0/1加载A/B；当前v2为cmd_data64并有独立A128/B512通道。名称“M”不构成ABI兼容。
3. **`m106`并不直接驱动v2M。**其接口为cmd/start/ack与32bit外址、owner/version/epoch；内部`mfront106`固定K512、8个已选专家、H1536，连接byte_a/b64→byte_p128的8S8乘法服务。`vprep97`固定8×512 SiLU及整行量化；没有实现当前X的完整router/TopK/全部投影。
4. **`norm106`输入是4×S32/128、gamma S32，h只接1536或2560。**它用U128 sum/rad/numer/den，`rad=(mean+eps)<<40`、`numer=abs(x*gamma)<<12`后除法/RNE；当前v2N输入count1..8的S16、gamma位于aux，采用因子及RNE30路径。即使都叫RMS，也不能复用旧数值回执直接授予新N资格。
5. **旧store82写ACK=0且ready=!valid**，不能同拍消费旧响应并接受新请求；新S写ACK=din，ready允许消费换新但受wide读仲裁。可借S owner/FSM思想，不能假设ACK载荷和吞吐相同。

旧[四profile协议](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/051fddb9a3d2cecd4b76c43d07ec8581db9402ce/project/experiments/shared_gdn/PROTOCOL.md#L1)限定完整两个K128/V128 GDN head、互斥服务银行与真实外部状态页，并保留门级pilot超时等失败记录。旧bench/receiver在仓库存在，但本轮未重跑、未重新授予当前六profile或物理资格。旧文档中的阶段快照不能覆盖当前独立任务的实时验收。

## 4. 现存算术与外部桥应怎样借

| 组件 | 已有能力 | 不应声称的能力 |
|---|---|---|
| `runtime_cache/mul84.sv` L1–27 | signed32×32→S64；两个有限响应槽；SHARE1为一个共享乘法器及选择 | 不是v2E16接口，也未自动提供宽累加/完整NUM |
| `runtime_cache/sfu84.sv` L1–37 | 有限U128除法/开方服务 | PROFILE1无隐藏乘法器；op0使用的乘法常量为0，不能当通用128乘法 |
| `gdn_state/wide104.sv` L1–20 | 通过外接S32服务做checked I64×受限factor lowering，带取消/排空 | 明确拒绝I64_MIN与b超[-32768,32768]；不是任意S64×S32/Q31，也不是完整WACC |
| `wide_service/memory_link.sv` L1–30 | 单在途半双工128bit packet bridge、addr32、请求/应答头及holding | `t_*`表示target endpoint，不是T6K；无内部通用error/epoch，后者由shared框架另做；不是已接好的新MEM平台 |

可把这些视作NUM/MEM原语候选，先保留原范围、单位、舍入、溢出和握手，再做新owner/接口适配、与当前oracle及错误路径验证。不能一方面把旧资源说成不存在，另一方面又不计代价地称新NUM/MEM已经完成。

## 5. PR133的2×131bit bridge不是当前memory_link

本轮Melodydt连接实际查询PR133：`open`、`merged=false`、head=`b1864046b1adfa5101cff3235742b4068aa78ee3`，base=`task/121-block-v1-twelve-layer`。元数据快照见island-connection-evidence.json的PR133字段。

历史小RTL文件[linkclose_bridge.sv](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/b1864046b1adfa5101cff3235742b4068aa78ee3/project/rtl/block_v1/linkclose_bridge.sv#L1)定义`linkclose_elastic WIDTH=131`的`bank[0:1]`，及`linkclose_bridge`，保存capture/error/saturated/data并驱动旧T写入。当前051的`project/rtl/block_v1/`只列出shared121与transaction6k，未含该文件。其历史M/T/S driver加强及物理链路资格只属于该固定来源，不在本轮转移、也不重审大体积物理数据。

当前`memory_link`是32bit地址/128bit外部事务packet FSM，协议、模块、源码与131bit弹性队列均不同。当前`native_glue.py`也只是把shared121切成shared109与T6K叶边界的映射glue生成器，不是该131bit桥、更不是新v2通用连接生成器。

另一个容易误读的名字是`bench_store_handoff.cpp`：它通过`HANDOFF_T`选择编译T或S的单个Device，分别测公开端口；没有同时实例化T/S互连，不能据此称通用T→S writer已有。

## 6. 新六profile具体还要落哪些内部连接族

每条都可选S/MEM中转或经证明的固定直连，不要求49条宏对都造一条专线，也不强制所有边都穿过额外E/NUM。

- **所有profile共用：**S/MEM→M装载；M结果→存储；各消费者的S/MEM读写及ACK归属；最终payload→T及消费/release。已有P2只覆盖其中固定MST切片。
- **A_plain/A_gate：**M score→N3所需原score路径，N6概率→M PV导入，E RoPE/缩放/残差与M/N交换，Norm多遍存储/回放；gate型另需G输入配对、32bit拆拼及G→O投影。N3和N6、EXP与probability必须区分。
- **F：**M gate/up→G两支配对（必要时先转换），G mid→M Down；前后N及残差E。M5已S16且F匹配时只需取字段/拆包，不自动新增通用算术；整mid保存与Down重放仍有容量/调度前提。
- **D/H：**M/N/E/G与R的S32/Q14/Q31/单位适配、系数/inject算术、R候选读出/本地commit/全job版本与MEM导出。R7不可被R8中断、提交后不可回滚，不能用profile方框隐去全状态后备存储。
- **X：**router score→N TopK，ID→受控地址与真实selected-score/expert gather，selected score→Softmax，expert M/G数据链→NUM宽加权归并；控制地址/ID不当普通数值裸接。
- **允许的反馈/导出：**同S复制、同T整批重入、loader一般导出、fork/join都要有真实保持槽、取走规则和有界生命周期。旧协议可以参考，但P2未把这些一般服务实现完毕。

## 7. 实现顺序建议

1. 在已有原生合同上实例化六profile的role/格式/尺度/上下文/完成事件与唯一owner；只保存真正运行时所需控制，不要求通用role随包标签。
2. 复用P2普通S helper与M/loader/T顺序基础，增加真实请求/数据MUX、响应归属和有限holding；M2/M3的单loader选择与竞争单列。
3. 完成E/G端点与128↔32拆拼、配对、尾部/错误/背压，建立有真实中间保存位置的FFN8基础核；完整F还需下一步N及真实参数/存储映射。
4. 完成N多阶段owner、同组score/EXP/gamma回放及存储，加入A_plain/A_gate；旧norm控制经验迁移后按新N公式重新验。
5. 按明确范围适配mul84/SFU/wide104等NUM/MEM候选，同时补缺失能力；完成R owner、状态页/根发布，建设D/H，不直接复用旧gdn109数值资格。
6. 接入X的受控ID、gather、40专家数据与宽merge，验证rank/概率/版本一致，保留全部合法但未映射的缺口。
7. 按每连接族的背压、错误、取消/重置、重复运行、容量及重入做真实RTL组合；再验完整profile和多Block。功能通过之后另做物理端点/长线/clock/reset/PG，旧资格不自动继承。

本轮只有源码/目录/回执的静态核验，没有产生新RTL、仿真或物理通过结论。
