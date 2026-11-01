# 六行大Block配置的岛内同步与实施顺序

Issue151 / PR152；输入研究提交`051fddb9a3d2cecd4b76c43d07ec8581db9402ce`，叶源固定PR144 `707878621b2add4ed218b8c43df2e95c9a56e2ba`。本轮只读integrated中的P2、宏数量表和粗粒度合同，生成研究计划；没有实现新RTL、运行仿真/服务器/EDA或修改正式包/远端。P2是已测有限原型，P3—P7没有因本稿开始或完成。

## 1. 仍须小宏同步，只是同步责任移到岛内

A_plain/A_gate/F/D/H/X是六行**功能资源配置**，不是原生七宏已经能直接拼成六块硬核。M1/N1等串行数量是条件参考；每岛仍须有本地CTRL和真实适配、MUX、保持/回放及错误处理。母控发完整子层任务并管理依赖、分配、跨岛事件和发布门，本地CTRL再把任务展开为M/N/E/G/R/S/T的原生命令、流式拍数、tile循环、ACK、commit及release。母控不逐op/逐字同步，也不替本地接收每个payload。

共同M1–M10必须在冻结前包含实际选用的母控/CPU（若采用）、本地控制/ROM、NUM、MEM/IO、MUX/arbiter/寄存器/中继/CDC和clock/reset。M11/M12只被动连已存在的端点、永久选程序/参数/合法路线；不能在定制时补适配、CPU、buffer或CTS。程序来自预制有限家族/入口，运行时装载tensor、传长度/位置/已接收地址参数不等于启动装入新控制程序。当前没有证明需要通用CPU，更没有现成CPU/MEM/NUM可由命名取得。

## 2. 岛内固定互联主候选

先采用**S物化＋端点适配**作为一般路径，保留原生S loader→M的A128/B512快路；并不默认建一个七宏全交叉的大总线或49条专线。每种selected route的有源MUX、ready返回、源保持和目的收集都在岛内预制。语义合法的路线缺硬件时标implementation/mapping gap，不能把它改成非法。

```text
芯片母控 ─任务/依赖→ 岛内local CTRL＋预制程序ROM
                       │ 原生op/phase/route/counter
            ┌──────────┴───────────────────┐
            │ M N E G R T端点capture/gather/拆拼 │
            │           ↕ S唯一普通owner       │
            │   S storage＋既有loader ─A/B→ M  │
            └────输入/输出fragment及事件端点─────┘
```

S普通口由一个S_CTRL/helper独占。其他本地服务通过有界请求/响应交互访问它；不是多个小控直接并驱S。loader描述符及done_take也由明确的本地owner控制。S普通请求与wide loader竞争真实bank；母控WAIT、本地等别的宏时，已接收的S响应仍能先捕获、take和排空。不能占着一个S response等第二个S read。

端点buffer按所选操作披露，而不是重新强制通用handle/type包：例如E FMA需要A/B/C时，先收齐最多3个128bit操作数（48B），再发E并保留128bit结果；G gated路径可先捕获x/gate各128bit，再拆成两S16一拍的32bit输入，按有效数收集输出；N gamma回放需要data/aux及其组计数；每份holding/回放/参数表都须另计成本。可静态证明不需的操作数不强加，但未有生存期证明不能把几份物理保持当一份。

物化是保守基线，不是限制所有路线只能走S。直接旁路或双buffer可作为明确优化，需完整握手、范围、反压及资源证据。岛内实现可以是wrapper/local CTRL中的逻辑；目前没有独立物理bridge宏，也不能把这些逻辑说成现有七叶内部已经提供。

## 3. 七宏各自真正需要什么同步

| 边界 | 本地要做的动作 | 现有与缺项 |
|---|---|---|
| M cmd/rsp | valid/ready发令，检查ACK/status；EXEC输出是fault_rows/error，不能写成结果tensor；成功后读op3/op5等实际数据，按目的格式重排/保存；单merged上下文保活 | P2有固定op6/op4/op10/op3→S并逐字ACK；op5格式、跨bank/fmt/append及通用重排的组合验证未闭合 |
| E | 按op收集A/B/C，shift/单位固定，128bit应答保持；E12低64为8S8，E13低64为4S16，不能按同样8S16解释 | E叶存在；与S的gather、tail、结果存储和完整F/A路线未实现验证 |
| G | 32bit双S16流，fn/gated/单位配对；计算accepted与retired数量，所有在途退休后才完成/换上下文；停顿时保留payload/tail | G叶为四级可冻结流，不是单cmd/done；S128拆32与收集、gate配对和错误排空未实现 |
| N | BEGIN/STATS/FINALIZE/EXP保存/回放及gamma的多阶段程序；外部目标长度与各阶段实际计数；BEGIN_GROUP/BEGIN_TOPK不得误覆盖各自仍需context；原score与EXP严格区分 | N叶及原生guard存在；组lease、回放、同S仲裁、完整N↔其他宏往返适配未实现；两类context独立，N0不清TopK |
| R | 按不同op身份位域发令，读op12候选先保存；op7接受后等COPY，不能op8取消已commit；conv history与state两pass导出/ACK和完整root发布 | R叶新源存在但最终资格独立；外侧R_CTRL/NUM、多tile版本、真实old/next存储和失败策略未实现 |
| S | 每读/写都一请求一ACK并保持到take；初始化、结果存储、loader全A/B及done分别计数；共享仲裁独立前进 | 普通S helper和固定loader→M已经P2局部测试；一般竞争、通用loader export/capture、same-S copy等未完成 |
| T | BEGIN规定字数，顺序填满SEALED后commit，读fragment并等末字take→RELEASE；同T重用先保存旧批/释放；sticky error按真实guard处理 | P2测试固定4字及有限反压/reset；通用1..384、同T回路/spool、fork消费和无reset排空未完成 |

握手类型不能强行统一为start/done：M/N/R有命令/响应，E是输入/输出事务，G可多拍在途，S写也回ACK，T是多相租约。外侧可给本地控制统一的有限服务调用，但必须实际执行上述协议和数据转换，不能只改端口名字或接同宽导线。

本地phase完成不一定释放宏：N组和R context可跨本地子程序继续保留；在大Block内部先去E/G/N加工再回R，同一owner维持guard和上下文。若需跨岛/host等待期间保留phase，需单独可接收RESUME/CANCEL的控制通路，不能仅用“空闲才ready”把恢复命令封死。

## 4. 哪些是P2真正已测的起点

当前RTL实际实例化S storage/loader、v2 M、T、独立S helper及21×16bit SERVICE/WAIT/END固定ROM。SERVICE握手只接单，WAIT收到服务响应才前进；M_STORE每包都按M op3应答→128bit保持→S写→S ACK后读下一包；最后四个T字被消费并RELEASE才报告整个程序完成。

固定fixture是S8×S8、row1/tile1/K8/N8、A448/B452/result456、S共192B、T4字64B，输出八个S64。独立RTL证据为helper6场景/141周期、MST13场景/1101周期，共19 CASE_PASS；五个正常批次各16个S请求/ACK、7个M命令/响应、一次loader完成、T4字及release。该证据仅属于固定源码和这些场景；N/E/G/R本轮只有编译门，没有借此获得功能组合通过。

这些路径已有：S普通读写及ACK；Sloader→M供数；M EXEC状态过滤→op3读数→S保存；S→T填充→外部ready/valid sink→release；固定母控局部WAIT、有限错误/反压及协调reset。它们不是一般输入tensor API、完整M/N/E/G/R互联、完整大Block或通用跨岛接口。

迁移岛壳需把literal初值与S地址、0x9884、T4字等单fixture限制替换成**已接收有界参数/数据输入**，同时保留固定程序；建立真正输入存储ACK、输出fragment生存期、独立完成/错误保持、资源预约和唯一owner。S没有初始化有效性元数据，reset也不清RAM；新岛壳要按已预约region/当前任务记录完整输入到齐并存储ACK，未到齐不能启动loader/compute，不能读旧字节当新输入。当前P2 M/T后端仍集中top，S helper才独立；不能说七类_CTRL已分别实现。P2的abort是协调同步reset，既有外部输出前缀和已接受S写不能回滚；无reset停止/排空需另做。

## 5. 岛间不能只用一个done

| 层次 | 必须区分的条件 |
|---|---|
| 接单 | 完整任务参数被接收且资源准入通过，不等于native或tensor完成 |
| fragment ready/sealed | 该有界范围计算、检查、实际存储ACK完成且保持不可变，不等于全子层结束 |
| transfer done | 最后beat被对端端点接收，不等于对端S/MEM存储已ACK |
| stored ACK | 对端指定存储已收到全部有效字节，母控才能关闭对应依赖/发源释放 |
| reusable | 输出租约、所有native/数据响应已关闭，可覆盖槽/接下一任务；保留N/R phase另注明 |
| state/output publish | 完整程序规定的版本/输出可见门；R localcommit、T批次commit和跨岛传输不联合原子 |

fragment_last只是本fragment末字，JOB_COMPLETE须覆盖全部fragment/错误/保留phase/state义务。样本最大hidden_size H=3072时单token S16输出6144B刚好填T，S32为12288B需分批；SSM等内部4096维及prefill还需另行分片。S16KiB也不是全部可用计算区。必须在接口冻结时定义有效字节/tail、分片序号/长度来源、目的存储ACK、源CLOSE/release及错误前缀，不能靠统一128bit数据线推断。

母控WAIT仍要收所有岛事件，本地仍要排空S/M/N/R/G/loader/MEM响应。一个producer保留任务/输出时不能等待在同一已占用island新启动consumer；先证明跨job独立buffer，或实际MEM staging→ACK→release再调下游。静态DAG不是物理资源等待图的无死锁证明。某个分支/R tile已localcommit或输出已被接受时，失败须记录partial，不能盲目重试/全token回滚。

## 6. 与P1—P7兼容的实施工作包

相对工作量仅表示工程复杂度：M=一个有界协议/合同面及独立测试；L=多个相连协议、布局/状态和错误恢复；XL=数值、存储/版本或全产品/物理共同闭合。它们不是工期、工时、费用或可相加的测量值，接口/数值未知会改变估计。所有下列包当前均为proposed；只继承P2已明示的有限起点，不宣称后续已执行。

| 包／对应原阶段 | 实际产物与依赖 | 独立测试／退出门 | 相对量 |
|---|---|---|---|
| W0 源/范围和P2剩余门；P1/P2 | 更新051/707源锁、接口/错误/取消表、route/test归属；保留P1历史643与P2实测。无新功能依赖 | 固定byte/参数/数值来源可追溯；P2未覆盖清单仍在；审查不把P2小smoke当整阶段通过 | M |
| W1 可装载tensor的共同岛壳/本地基础适配；P2＋P3入口 | 依赖W0：输入数据与固定程序分离；单S owner、common response capture、E operand gather、G serializer/collector、本地phase/错误保持和参数表骨架；P2回归 | 改数据/合法shape后按独立预期输出；请求未接收与响应未消费均保持；写ACK守恒；M EXEC状态不流入tensor；reset/error/reuse逐边验证 | L |
| W2 双岛传输与host/MEM边界早介入；P5合同前置 | 依赖W1接口：先用MST/复制核做两岛输入/输出fragment、stored ACK/CLOSE、事件采集；定义host数据及未来MEM acceptance/store completion/故障边界；从W1开始与W3/W4并行 | 两端分别停顿，data/fragment/status保持；输入存储ACK才释放源；同岛复用冲突被拒绝/合法物化；部分fragment错误不报成功。小传输通过不等于MEM控制器存在 | L |
| W3 S↔E/G与FFN8基础核；P3 | 依赖W1：E各op所需gather、格式/tail；G双lane/gated配对与在途计数；M→G/E→S→M的FFN8核 | E12/13布局、正负/舍入/饱和/非法op；G fn/gated单位、独立反压/尾部/退休守恒；FFN8每阶段和最终整数匹配。它不含全F的pre/post Norm，不叫完整F | L |
| W4 N phase/replay、RMS/L2及Softmax257；P4 | 依赖W1，可与W3并行：目标长度、raw/EXP/gamma保存/回放、group lease/回访、TopK ID字段；在W3后可补F的Norm门 | 257末项新max、tail1、EXP原码回放、33输出字守恒；计数/早FINALIZE/错版本；epsilon/gamma单位、N0/TopK独立；N结果写ACK后才组完成 | L |
| W5 F/A垂直集成与布局；P3/P4/P5组合 | 依赖W1/W3/W4：F完整preNorm→gate/up/down→规定postNorm/residual；A输入/头Norm、QKV/RoPE/GQA/layout、QK/N/PV、输出门/投影/residual。实际超片上容量时还依赖W10 | 先明示有界切片测试，再对已接收真实模型形状和存储映射验完整子层；不得为“装得下”缩模型。逐边整数参考、M单context跨阶段保活、不同Norm位置/输出门及回放守恒；MEM未闭合则只记切片通过/完整not mapped | XL |
| W6 一般拓扑/同S同T/forkjoin；P5 | 依赖W2/W3/W4：同S copy/重叠规则、loader导出全1024B capture、T回路6144B spool、顺序fork/版本join/条件skip/有初值feedback | 真实完整事务与ACK、独立分支停顿、未选分支不等done、同T先release后BEGIN；资源等待图+仿真/形式；缺路线留gap。49格各一例不作全覆盖分母 | XL |
| W7 必需NUM及数值oracle；P6数值支线 | 数值定义可从W0提前，与W3/W4并行；RTL适配依赖W1。分别闭合D/H系数/宽bias/inject/转换、X宽加权merge等实际所需操作，不凭服务ID创造功能 | 独立高精度/整数oracle及范围/误差/舍入/溢出测试；合法极值/负数/饱和和故障传播；优先复用M op5等已有合法op，不用E16冒充S32 | XL |
| W8 R localphase、history及多tile版本；P6 | 依赖W1/W4/W6及W7所需NUM切片；R最终源资格仍为独立依赖。本地R_CTRL、候选先保存、COPY保护、两pass导出ACK、old/next/root/partial服务；实际大尺寸还依赖W10 | 原生pending/身份/有效位矩阵、SSM因子重载、conv成功后state失败保留history、op7接受后不可撤销；小驻留多tile先验机制，完整128/4096归约及真实全层state/MEM另验，不能用单tile替代 | XL |
| W9 X动态MoE集成；P7的机制/回归支线 | 依赖W3/W4/W6及W7 wide-merge切片，**不依赖R通过**：router40、ID/rank gather、selected8 Softmax、专家表/供给、8次专家核与公共单位宽归并 | ID≠score≠weight，非连续/边界ID、概率/rank配对、重复/错版本和故障；每专家M结果保存后才复用；8项齐全才merge/residual。只跑expert核不算完整X；真实专家存储还依赖W10 | XL |
| W10 真实MEM/host平台与容量闭合；P7，设计从W2前置 | 依赖W1/W2，不必等待W8/W9结束：实现真实地址域、存储/搬运/仲裁/ACK、容量/带宽、故障/晚响应/排空；补大tensor/KV/weights/state/history映射 | 延迟/反压/故障/部分写、先接收≠已存储、reset晚响应、release后复用；真实尺寸和带宽证据。仿真中零延迟数组不能当控制器/PHY通过 | XL |
| W11 完整程序、同底座与PPA接收；P7 | 编译/ROM容量和物理反馈从W1持续开始；最终依赖W5/W6/W7/W8/W9/W10及原叶资格：八产品完整程序/层表/数值与路由，芯片母控和所有有源能力固定，最终PPA | 程序实际编译装入；完整推理边界/质量/活性/性能；至少两个产品M1–M10/PG/CTS一致，M11/M12差异合法；完整STA/PG/DRC等独立审查。不能以SystemC、静态表或叶PPA替代 | XL |

W2和W10不把MEM拖到所有算子之后：前者早定可变延迟/存储ACK语义及小双岛传输，后者实际接口/带宽/错误实现可平行推进。W7数值定义也应早做，避免R/X接口做到一半才发现缺失宽算术。W11的ROM编译/容量及后端反馈是贯穿工作流，不是最后才首次估算；但最终接收仍等所有真实产物。

完整F依赖N，故“先FFN8核、再N回放、再完整F/A”与原P3/P4一致；N与E/G开发可并行。H完整一岛优先于拆分双分支的控制比较：先保证一次inputNorm、单M串行两支及完整state/输出门，之后拆分另验回传/共享存储/活性，不能靠12叶BOM推断自动并行或无死锁。

## 7. 交付证据和本轮真实状态

每个退出门需固定源码/工具/配置、输入数据/seed、独立期望与SHA、准确命令、日志/输出SHA、退出码/coverage/错误处置。静态检查只能证明规格一致；软件参考、RTL功能、LEC/网表、数值质量及物理接收分别记录。实际服务器实验须按既有授权、REMOTE_RULES和作业启动/结束回执执行，本轮无作业号，不声称后台监控。

本轮`python scripts/check_project.py`管理检查PASS，本目录`check_island_sync_plan.py`完成18项工作包依赖/范围/算术静态检查PASS，回执为`island-sync-checks.json`。复算命令：`python -B -X utf8 work/Melodydt/151/check_island_sync_plan.py --directory work/Melodydt/151 --report docs/COARSE_BLOCK_SYNC_WORKPACKAGES.md --receipt work/Melodydt/151/island-sync-checks.json`。这些不验证RTL或活性。本轮只产生本说明和JSON计划/静态检查；没有把P3或任一新工作包状态改为已实施。完整程序数、真实MEM/NUM实现、一般岛内互联与粗Block物理资格仍按其实际缺口维护。实例BOM和所有相对工作量均待后续实测修订，不擅派负责人或工期。

来源：integrated的`PHASE2_MST_IMPLEMENTATION.md`、`PHASE2_MST_VERIFICATION.md`、`SEVEN_MACRO_INTERFACE_ROADMAP.md`（其P1历史正文结合头部P2进展说明读取）、`COARSE_BLOCK_MACRO_BOM.md`、`COARSE_BLOCK_CONTROL_CONTRACT.md`、`COARSE_BLOCK_MODEL_MAPPING.md`及`project/rtl/block_connection_p2/`真实三RTL。
