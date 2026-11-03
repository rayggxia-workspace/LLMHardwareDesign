# 六配置大Block的宏连接、同步缺口与实现路线

Issue151 / PR152，负责人Melodydt。固定研究输入051fddb9a3d2cecd4b76c43d07ec8581db9402ce，七宏来源707878621b2add4ed218b8c43df2e95c9a56e2ba。本轮核对当前源码、既有证据和六配置需求，不实现新RTL或运行新仿真；已有组件、有限组合实测、候选合同和完整profile验收分别记录。

## 1. 大Block仍需端口同步，只是责任局部化

大Block本地控制器负责七宏之间的接单、操作数收集、结果保持、阶段/计数、保存/回放和资源释放；母控负责完整子层任务与跨岛依赖。现有叶宏内部已有各自状态机，新增工作主要在叶端口外侧。当前P2使用同一时钟，ready/valid协调不等于需要额外CDC；未来引入异步时钟域时须另做真实CDC与复位合同。

不能要求所有宏同拍开始/结束。S请求接受不等于ACK完成，loader done不等于M计算完成，M EXEC应答不等于张量，N统计结束不等于概率/归一化回放结束，R局部COMMIT不等于整层状态发布，T某批末字也不等于完整子层完成。暂停时valid/data和sideband必须保持，恢复后恰好消费一次。

角色、类型、尺度和布局仍主要在编译期证明；硬件保留实际op/phase、MUX、holding、地址/计数与转换。128bit同宽只是载体相同，不能省去命令译码、多操作数配对、返回类型过滤或布局处理。M11/M12不会自动生成这些有源能力。

## 2. 推荐的固定岛内互联形式

先采用S物化/回放、有限operand capture/gather和每叶端点适配作为通用参照，保留S loader→M的专用A128/B512供数快路。逻辑上的M→N通常可以实现为M读回/合法量化→holding→S→N请求，不要求为每个宏对建立独立物理总线。五功能类/六配置也不等于49条直接全互联。

```text
输入/权重/KV/state服务 -> S及有限保持
                          ├ loader A128/B512 -> M
                          ├ gather -> E(A/B/C128)
                          ├ gather -> N(data/aux128,op/count/param)
                          ├ 拆包/配对 -> G(X/Gate各32)
                          └ 参数/索引/数值转换 -> R或NUM

M/N/E/G/R/NUM结果 -> 返回类型过滤/保持/合包 -> S或T
T -> 岛出口/接收存储/MEM -> 输入可见与释放确认
```

这张图是待实现的共享服务边界，当前没有通用岛内交换网络。可证明格式/生命周期匹配的局部快路可以绕过S，例如已量化M输出经holding拆成G两lane输入；不强制每个值先合满八lane或先写S。所有快路需保留唯一owner、背压、tail和数值证据，不能把逻辑依赖记成已直连。

## 3. 必须支持的端口与存储连接能力

| 能力 | 端口和同步工作 | 当前可确认的起点 | 仍缺的通用能力 |
| --- | --- | --- | --- |
| S普通读写 | 128bit req/ready、valid/take；写也有ACK | block_p2_s_ctrl已在真实S上验证单在途读写/保持/reset | 多来源owner/入口分配、布局地址、并发宽窄仲裁场景和大任务生命周期 |
| S loader→M | A128/B512，bank/row/tile/fmt/half；done单独消费 | P2真实连接v2 M，S8 K8/N8小例实测 | S16/多tile/reuse_b/独立A-B停顿、通用装载/保存布局与完整profile调度 |
| M→保持→S/T | cmd/rsp；区分ACK/status/payload；op3/op5等不同输出格式 | P2的op3四包S64写S并收ACK，再从S填T | 通用op5量化/拆包/tail/数值策略、M结果重用与其它目的出口 |
| S↔E | gather A/B/C三路128，op/shift，out128/error/saturated | E原生模块和单宏端点存在 | E_CTRL、操作数快照/配对、尾lane、返回保存及现v2组合实测 |
| S↔G | X/Gate各32，fn/gated，输出32；可连续流水 | G原生两lane/四级流水存在 | 128↔32拆拼、gate/up同源配对、在途/尾部/重用计数和集成 |
| S↔N | data/aux各128，op/count/param，rsp128 | N已有Norm/Softmax/TopK原生操作与内部算术 | N_CTRL整组phase、raw/EXP/gamma回放、统计/IDs/factor过滤、保存与头/组身份 |
| S↔R/NUM | cmd index/op/data128，S32候选、参数/history/state | R原生命令和单宏状态机存在；数值/宽服务有历史组件可借 | 当前ABI下转换、参数/版本/导入导出/不可取消窗口、NUM与完整状态后备服务 |
| S↔T及T出口 | BEGIN/顺序写/SEALED/COMMIT/read/take/RELEASE | P2四字T生命周期和外部ready背压实测 | 任意受接收长度的分片、通用入口写S/stored ACK、同T重用/跨岛/回路 |
| S物化/同S重入 | 保存residual、mid、score/EXP、布局/gather/重放 | 原生访问和P2固定地址保存可复用 | 不覆盖活数据的allocator/slot计划、同端口等待环消除、完整参数范围 |
| MEM/参数/版本入口 | 可变延迟、实际存储完成和错误、地址/范围 | 当前仓库有旧缓存/存储/数值组件 | 不等于已有新六profile的MEM/NUM/版本平台；接口和带宽仍待闭合 |

上述“缺”描述的是当前七宏ABI与完整子层服务，不能解释成仓库毫无相关代码。旧shared109/shared106、m106/norm106、shared121/T以及宽算术/缓存等组件的源码、接口差异和可借范围单列于证据审计附录；旧V或旧S协议不能按名字直接记成新N/E/G或新S连接完成。未进入当前树的历史PR专用bridge也不作本分支已有硬件。

## 4. 六配置实际需要哪些逻辑数据依赖

以下箭头表达依赖，可经S/holding/NUM物化，不承诺直接线或全profile已经实现；权重、gamma、RoPE参数、mask、residual等第二/第三操作数同时需要独立可见来源。

| 配置 | 核心依赖 | 额外同步重点 |
| --- | --- | --- |
| A_plain | N→M(QKV)；M→N/E(QK Norm/RoPE)→M(QK)；M→E(score尺度/mask)→N(Softmax)→M(PV/O)→E(residual) | N各组/头回放、KV/GQA/Transpose、M结果与原residual保存、可选postNorm |
| A_gate | A_plain依赖＋M(PV)→G(Sigmoid gate/context)→M(O) | gate与同位置context两源配对、32bit窄流/回包；输出门在Wo前 |
| F | N→M(gate/up)；两份M结果→G门乘→M(down)；M→可选N→E(residual) | 同一个M不同任务的结果先保存；完整I回放；Gemma postNorm；G两源配对 |
| D | M→R(conv)→G；Q/K经Repeat/L2/缩放进入R，V与系数进入R；R(readout)→N→G(SiLU(Z)门)→M→E | R S32转换、head/layout、NUM系数、history/state多tile版本与发布 |
| H | 一次N后fork到Attention及SSM；M→R(conv)→G→R(SSM)；R(readout/skip)→G(SiLU(Z)门)→N→M；两支→E join/residual | 与D不同，Falcon先门乘再全4096 RMS；两支可串行但必须保存；NUM/MuP/bias32/状态发布 |
| X | N→M(router)→N(TopK IDs)；IDs→gather→N(selected8 Softmax)；M专家核→G→M(down)→NUM加权归并→E | ID/rank/prob/专家地址动态对应；只一次preNorm；专家核不重复完整F的Norm/残差 |

普通A没有G/R，F/X没有R，不能为这些配置列必须经过R的逻辑路由。N用于多个阶段不必复制N，但未完成的统计/回放不能被别的阶段覆盖；R同理有不可复用的候选/commit窗口。重复调用同一宏是时间复用，只有输出确实作为后继输入时才记录payload自环，不能把每次重复调用都算一条物理反馈线。

## 5. 哪些是真的已有，哪些尚不能宣称完成

1. 当前M/N/E/G/R/S/T原生module及端口是现存代码。原生ready/valid只保证本宏按自己的合同接收/返回，不提供跨宏的operand gather、地址、phase、数值转换或整任务控制。
2. 当前P2已实例化真实S/loader、v2 M、T、S helper和固定SERVICE/WAIT顺序器；已有ModelSim helper6/MST13共19场景证据。它覆盖的是S8一行一tile、K8/N8、四包S64保存/输出以及列明背压/错误/reset。
3. 当前P2没有实例化N/E/G/R，也没有外部tensor入口、通用跨岛接收器、六profile程序库或通用MEM/NUM。它的M_STORE读op3、地址、loader和Twords固定；不能改名为大Block后自动获得这些功能。
4. 现有legacy共享S32框架、旧M前端/归一化、cache/wide/bridge是可借素材，有自己的受限接口和历史证据；它们不直接变为v2六profile已集成，也不能将target端口t_*当T6K端口。
5. 六个完整大Block及其完整模型/跨岛系统目前均未获组合RTL验收。本轮静态目录只说明需求/源码/差距，不计算打通率或用组件存在代替实际测试。

## 6. 最容易漏掉的具体适配

- M.op3给两个S64；M.op5可按原生模式给不同逻辑宽度，载体中的四S32槽位不能不经解释当八S16。目的G只有两S16 lane，应按目的直接拆包；不强制先合8再拆2。
- E输入最多三个128bit操作数，N有data/aux两份128bit，S普通口只有单请求流。需要先按固定程序收齐所需操作数并冻结，再发一次请求，不让同一事务的A/B来自不同任务。
- G的X与gate、N的raw/EXP/gamma、E的residual、R的key/query/value/decay都需要正确位置和尺度。编译期能证明的标签不必每拍传，但数据相关ID和硬件在途计数不能因此删掉。
- R回复可承载S32或状态；E13只覆盖满足范围/shift合同的四S32→四S16转换子集。S64、系数、宽偏置/归并等缺口应复用合适原生op或新增真实数值能力，不能靠截位/格式声明解决。
- error和saturated应分开处理，按数值合同决定饱和是否可接受；ACK/status/IDs/factor不作为普通张量误写。N TopK返回IDs后还须gather对应score和专家数据。
- T的fragment末字、源数据发出、接收端真正存好、源租约释放、R多tile根发布与母控job完成分开记。producer等未启动consumer、母控又等producer完成的环，需独立接收进展/预留落点或真实MEM staging解决。

## 7. 实施工作包与既有路线的关系

| 工作包 | 主要产物 | 验收门与路线归属 |
| --- | --- | --- |
| W0 合同与覆盖固定 | 六配置的端点/shape/格式/op/phase、逻辑边与物理hop分开、源码证据 | 不把native/legacy当整链；P1合同/P2剩余门 |
| W1 共同岛壳 | tensor入口、输入完整/存储ACK、capture/gather/serializer、S唯一owner、本地服务/错误保持 | 程序永久固定但数据可变；不把reset后S旧RAM当有效输入；P2补闭合/P3入口 |
| W2 早期双岛与MEM边界 | 两岛fragment、stored ACK/CLOSE、独立事件采集、host/MEM可变延迟合同 | 两端独立停顿/部分错误/源生命周期；从W1与W3/W4并行；P5合同前置 |
| W3 S↔E/G与FFN核 | E_CTRL、G_CTRL、gate/up保存/配对、128↔32、M→G/E→S→M | FFN8逐阶段整数对照/退休计数，不叫无N的完整F；P3 |
| W4 S↔N与回放 | N_CTRL、Norm/Softmax phase、raw/EXP/gamma保存/回放、TopK响应分类 | Norm/Softmax257、tail/new max/错组拒绝；P4，可与W3并行 |
| W5 完整A/F集成 | Norm/投影/布局/门/残差完整程序与存储映射 | 依赖W3/W4；超过片上容量还需W10，切片通过不冒充完整子层 |
| W6 通用拓扑 | 同S/T、copy/export、fork/join、feedback和有限母控等待 | 资源等待环、真实ACK/RELEASE/错误，依赖W2及所需E/G/N；P5 |
| W7 NUM与数值参考 | D/H系数/宽bias/转换、X宽加权归并等实际所需数值服务 | oracle可提前；独立范围/舍入/溢出/反压验证；P6数值支线 |
| W8 R与状态版本 | R_CTRL、conv/history、old/next导入导出与发布，D/H正确Norm/门顺序 | 所需W6/W7切片、COPY保护/部分commit恢复；完整大state另需MEM；P6 |
| W9 MoE动态路径 | TopK ID→score/专家gather、专家核、概率/ID配对、宽归并 | 依赖E/G/N/拓扑/所需NUM，不依赖R资格；专家供给另需MEM；P7支线 |
| W10 真实MEM与容量 | 实际地址/搬运/仲裁/错误/晚响应，weights/KV/state/history映射 | 从W2后并行实施，不等R/X完成；真实容量/带宽，非零延迟仿真数组 |
| W11 完整程序与物理 | 八产品程序/ROM、完整推理/数值质量/活性/性能、同有源底座产品 | 原P7；编译容量/物理反馈从W1持续开始，最终独立接收STA/PG/DRC等 |

W2的接口/接收存储和物理端口预算从W1并行开展，不等A/F全部写完。W7的独立数值参考、MEM需求与格式也应提前准备；表的先后是集成依赖，不强制所有人串行等待。每次先补最小可验证切片，再扩到真实H/I/头/层范围；不能缩形状后宣称完整覆盖，也不能为通过测试删掉合法但缺实现的路径。

局部MUX/桥接/计数/ROM/缓冲全部是预制有源逻辑；暂不要求独立bridge物理宏，先形成可综合模块和独立测试，再按实际布局/时序决定封装。母控/岛数/CDC/中继和固定pin都需冻结前接收；M11/M12只连接预留端点，不能在定制阶段补MUX、FIFO或CTS。

例如F的一段门乘，局控先保存M的gate结果并等S写ACK，再复用同一个M计算up并保存。随后从S分别读对应gate/up字，各自捕获并消费S响应；两份齐全后按两S16 lane发G，直到所有已接收lane退休，合包写S并收ACK，才为M.down提供装载源。M的op5或额外转换必须先满足G的S16尺度/布局；这部分尚未集成。母控只需等待整个F任务，局控执行上述小步骤。只把M/G的valid/ready相接不能完成此流程。

本轮仅交付研究/审计/工作包，不表示W1或P3–P7已经实施。后续仿真可按用户授权在REMOTE_RULES规定的Melodydt任务目录运行并保存commit/工具/配置/输入/输出SHA；当前无新仿真或服务器作业，原P2实际证据保持固定范围。


## 8. 资料与复核入口

- [六配置逐角色依赖](COARSE_BLOCK_REQUIRED_ROUTES.md)与island-variant-routes.json：实际操作数、阶段回放、状态依赖与共享物理跳分别列出。
- [当前树代码与历史组件审计](COARSE_BLOCK_EXISTING_CONNECTION_EVIDENCE.md)与island-connection-evidence.json：当前v2/P2、当前legacy及未进入本树的PR133分开。
- [12个实施工作包](COARSE_BLOCK_SYNC_WORKPACKAGES.md)与island-sync-plan.json：W0–W11细分已有P1–P7，不改写原阶段状态；X的数值依赖不等于必须等待R实现。
- island-connection-index.json、island-connection-inputs.json和island-connection-checks.json记录输入/脚本/产物SHA及真实执行结果。复核命令见[ARCHITECTURE](ARCHITECTURE.md)。这是静态研究交付，无新增RTL或服务器作业。
