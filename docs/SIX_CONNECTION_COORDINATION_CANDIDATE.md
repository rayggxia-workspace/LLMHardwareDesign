# 七宏连接的候选协调与适配架构审查

> 当前系统设计以[全合法连接总方案v0.3](SIX_CONNECTION_SYSTEM_DESIGN.md)及[原生接口审计](RTL_NATIVE_CONNECTION_AUDIT.md)为准；本文保留第一阶段固定来源，不能将其通用描述用于覆盖当前原生命令合同。

> 集成更新：本研究分支已实际合入PR144固定643c6012的七宏RTL，见[当前实现基线](SEVEN_BLOCK_RESEARCH_BASELINE.md)。下文旧5e/aac来源仍是历史合同/资格引用，不是当前分支缺少RTL；接口相同，新增系统硬件仍未实现。

> 第二阶段补充：用户已确认同一底座在M11/M12确定模型、成品无需任意改图。当前主候选已收敛为固定产品ROM选择＋两级控制，见[总方案](SIX_CONNECTION_SYSTEM_DESIGN.md)与[控制规格](SIX_CONNECTION_CONTROL_SPEC.md)。下文保留第一阶段通用任务表候选的审查背景，不表示运行时可换图是当前需求。

Issue #151 辅助研究草稿；日期为 2026-10-31，Asia/Shanghai。研究基线为 PR #144 的 `5e787714362d957b79c2997141cf05eeebb85afc`。本文中的控制器、外置 wrapper、存储搬运器及统一事件接口均为候选角色，不能视为当前已存在的硬件或已经确定的新宏类型。本次仅阅读源码和形成方案，没有运行 RTL、SystemC、综合或物理实验。

## 1. 优先保持叶宏的条件与候选分工

候选起点是“固定协调控制器 + 每类宏的预制协议适配器 + 明确的有限数据搬运/缓冲资源”。不同定制版本加载不同任务表；任务表只能引用该产品实际连接并通过接口检查的端口路径，不能在运行时重接数据导线。

```text
任务表、物理连接清单、存储分配表
                 |
         固定协调控制器
       命令 |     ^ 完成/错误事件
            v     |
      每宏协议适配器
            |
     原生 M/N/E/G/R/S/T

数据沿已定制的物理路径、预制缓冲或存储中转通路传输。
```

| 层次 | 候选职责 | 与当前叶宏的关系 |
|---|---|---|
| 协调控制器 | 依赖计数、任务发射、资源占用、数据版本、发布/释放策略 | 新的系统支持逻辑；不由现有 `busy` 信号自动形成 |
| 每宏 wrapper | 将统一任务翻译为原生操作序列；持有任务标签、长度/尾包、寄存响应并形成事件 | 首先评估放在叶宏外，以保留现有叶宏源码和端口 |
| 数据 bridge/搬运器 | 分/拼包、有效元素计数、明确的基址/步长、数据与元数据对应、有限队列及背压 | 新能力需真实 RTL 和硬化；不假设 PR #133 的旧桥已覆盖全部角色 |
| 原生宏内部 | 本宏算术、流水、银行、统计、状态和事务生命周期 | 保持现有合同；若需新操作、精度或端口，建立新叶宏版本 |
| 定制金属 | 已预制端点之间的导线和通孔 | 不能补出寄存器、FIFO、选择器、地址生成或调度逻辑 |

“外置 wrapper”首先是 RTL/架构归属，尚不等于独立 hard macro。后续可以独立硬化为桥接/控制宏，也可以与叶宏共同硬化为扩大后的宏；后一种会改变物理边界，须按新版本重做相关验收。独立硬化则仍需计入其面积、PG/CTS、M10 接点及宏间布线。保留叶宏 RTL 也不免除新负载、新路径的系统 STA 和电气检查；若接口驱动范围不够，可能仍要形成新的叶宏驱动版本。

当前 S 是明确的例外：`block_feed_s_macro` 已经把存储和 `block_feed_loader` 封在同一个 S 候选物理边界内。不能在 S 外再次假设一份免费 loader 或把其队列重复记作可用系统缓存。[S 宏源码](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_feed_v1/block_feed_s_macro.sv#L1)

## 2. 统一事件不能只保留一个 done

以下是系统层候选事件，并非各叶宏已经具有的同名端口。wrapper 必须从实际握手、响应和存储确认中产生事件。

| 事件 | 精确定义 | 不能推出什么 |
|---|---|---|
| `cmd_accept` | 原生命令或输入包在 `valid && ready` 的边沿被接受 | 不表示计算完成，也不表示所有输入装完 |
| `compute_done` | 对应操作的运算响应已经形成并完成错误检查 | 不表示结果已搬运；N单条统计命令完成不表示整条向量完成 |
| `data_ready` | 指定版本、有效范围的全部数据已写入目标位置或在目标承诺的保持槽中可消费 | 不表示状态/批次已经发布，也不释放源数据 |
| `publish_done` | 明确的发布/提交条件满足并得到对应确认；对 R、T 使用不同的原生提交动作 | 不表示所有消费者均已消费，也不意味着整个计算图原子提交 |
| `release_done` | 所有承诺消费者已确认消费，允许复用特定缓冲/上下文 | 不表示其他状态、其他银行或同地址新版本也可释放 |

候选任务至少绑定 `task_id、macro_instance、operation、context_id、token/position、tile、input/output slot、format/scale、valid_count、expected_version、dependency events`。字段宽度、队列深度和依赖数量需要受限设计与成本测量，当前不宜预填任意大范围。

现有叶宏多数没有通用 task tag 端口。M/N/R/E 可先限制每个 wrapper 一条原生执行命令在途，由 wrapper 记住关联关系；不能把 SystemC 的 `tag` 字段当成已经存在的 RTL 引脚。G 若保留流水吞吐，需要跟踪每个成功接受包的顺序标签并在输出接受时退休。标签只能在已接受操作及迟到响应全部排空或经协调复位后复用，不能仅改变软件 epoch 就假定旧事务已撤销。

## 3. 各宏已有行为对协调器的约束

### 3.1 M：供数完成、计算完成、结果读出是不同步骤

M 的 A/B 各自握手，执行银行被锁，另一个银行可装载；命令口仍由 `state==IDLE` 和保持响应控制。候选 wrapper 应分别跟踪 A/B 的银行、格式、行数、K tile、B 的 half 顺序和有效位。只有所需操作数装载握手全部完成，才发执行 descriptor。供数器 `done_valid` 表示请求和有限槽已排空，不等于 M 运算完成。[M 接收与锁定](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_m.sv#L38)、[S loader 完成条件](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_feed_v1/block_feed_loader.sv#L107)

当前 M op10 自动进行点积、缩放和行级提交；DRAIN 收齐行数后响应。op3/op5 是后续读出操作，读出、重打包和写入下游都须另计。[M 行提交](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_m.sv#L183)、[M 完成和读出](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_m.sv#L239)

最重要的恢复约束是 **M 只保证失败行保留旧结果，不保证整命令回滚**。`rsp_error` 为 1 时，其他行可能已经成功提交；响应低 8 位是失败行掩码。对于追加型命令，盲目重新发整条命令会给已成功行再次累加。首版应选择：错误即停止该上下文并显式重算，或实现带行有效性/备份的精确恢复协议；在没有实现并验证前不能声称支持透明重试或整命令原子性。

### 3.2 N：要锁的是整个向量上下文

N 的 `cmd_ready` 只表示当前子命令可以进入。Softmax 必须经历 `BEGIN→STATS*→FINALIZE→EXP*→FINISH_EXP→SOFT_REPLAY*`；RMS/L2 经全组统计/因子后才回放。wrapper 应锁定唯一向量上下文，跟踪输入总数、EXP总数、回放总数以及S中的原值、EXP、gamma区域，直到预期回放全部退休才释放。[N 许可条件](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_n.sv#L81)、[N 状态推进](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_n.sv#L134)

不得把每个tile单独FINALIZE当作完整向量归一化。若跨多个tile使用统一均值/分母，必须先完成全组屏障。现有N没有通用上下文保存/恢复接口；首版不应承诺两条任意长向量任意交错。TopK有自己的状态，但复用同一个命令口；其与归一化的并行/交错需单独给出资源兼容规则，不从“独立状态寄存器”推断免费并行。

### 3.3 E/G：有效元素和在途标签不能靠总线位宽推断

E 为单命令多拍结构；op13 每次只把4个S32变成低64位中的4个S16，高64位清零。wrapper须保留4个有效元素这一信息，按下游需要拼接或分批，不能把高64位填零当作另外4个真实元素。[E 接口与op13](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_e.sv#L1)

G是四级流水，`advance=!out_valid||out_ready`时整体推进，否则整体停住。若要保留II=1，wrapper必须为已接受、尚未消费的包保留有界顺序标签/计数，覆盖四级有效payload位置并加上外层队列；首版限成一包在途也可作为验证基线，但需承认吞吐损失。两路激活输入、门值、函数码、是否门乘和对应token/tile必须共同推进；不能用来自不同分支的最新值随意配对。[G 流水与背压](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v2/block_v2_g.sv#L11)

E 128位八S16与G 32位两S16之间的完整八元素搬运，需要明确分四批/重拼、尾包、有限缓冲及接收进度。固定选择低两lane可由接线表达，但按时间选择四组和保持未消费元素需要预制有源逻辑。

### 3.4 R：候选输出、状态提交和下游发布必须分别处理

R EXEC成功形成 `pending_state` 或 `pending_history`，候选输出可读，活动状态尚未改变。COMMIT检查owner、epoch、position与epoch不回绕，随后切换银行角色、更新历史和position/epoch；同时清除候选输出有效性。因此，在COMMIT之前必须已把要保留的读出搬进承诺不会被覆盖的下游槽。[R 命令合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_library_v1/block_v1_r.sv#L142)、[R 完成与提交](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_library_v1/block_v1_r.sv#L249)

卷积可先留下待提交历史，再接收外部激活/归一化后的数据，执行递推并共同提交。若后续递推失败，之前的成功历史候选仍可能存在；wrapper必须显式处理或REVOKE，不能忽略错误而单独提交历史并报告整轮成功。SSM shadow银行被逐元素decay装载占用，每轮因素需重装，不能在资源表里同时把同一8KiB当成可用状态候选和额外因素缓存。

不能把R COMMIT与T COMMIT组合声称为跨宏原子事务。T先提交时R可能提交失败；R先提交后，T发布或外部写回仍可能失败。首版可选择“先保留候选输出、验证提交前提，再按明确次序提交，并把跨提交故障上报为需要恢复的部分完成”；若要求失败后原子回滚、掉电恢复或恰好一次发布，需要额外日志/版本描述符/恢复协议，均不是现有两个COMMIT自动提供的能力。

### 3.5 T：整批保留、单消费者租约

T为384×128位、6KiB；先BEGIN申请1..384字，从0连续写，收齐后SEALED，COMMIT后才读，读完末字后RELEASE。COMMIT后不能REVOKE。它不是环形无限FIFO、不是双份6KiB并发生产/消费，也不支持天然多消费者读指针。[T 状态机](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/5e787714362d957b79c2997141cf05eeebb85afc/project/rtl/block_v1/transaction6k.sv#L23)

wrapper应在发射生产者之前预留输出批次或证明有可完成的排出路径，严格记录words、write_index、read_last和release。对fork，可显式复制到S两个区域，或在新分发bridge中维护每个消费者的确认位；不能把一条read_take简单接给多个可独立暂停的消费者。owner/generation是记录标签，现有commit/revoke/release没有额外身份参数，不构成多主体访问鉴权。

## 4. 六类连接的最小控制差异

| 方案 | 必须由协调层处理的步骤 | 适合放外部预制支持逻辑的功能 | 不能从已有叶宏推出的能力 |
|---|---|---|---|
| 普通注意力 | Q/K/V产生与保留；RoPE布局；QK分块累计；mask/scale；Softmax全组屏障和三遍回放；PV、输出投影及残差join | tensor/tile与KV地址遍历、布局搬运、回放控制、格式及S/T写回适配 | 完整KV访问器、任意Transpose、整模型数值闭包或系统吞吐 |
| 额外Norm | 对各头或全通道范围发起独立N上下文，完成统计再回放；Q/K归一化后再RoPE；输出Norm后再残差 | 可参数化归一化任务模板、gamma分块供给、上下文和地址计数 | 将多个head混统计、或把Falcon4096通道Norm拆成每128通道独立Norm |
| 门控FFN | 保留相同token/tile的gate/up结果；M只有一个实例时顺序执行两投影；两输入就绪才发G；结果再装M做下投影 | 两输入join、有限分/拼包、结果存储生命周期、G的在途标签 | 两个逻辑分支自动意味着有两个M实例；单G输入流自动对齐另一门值 |
| GDN | 卷积候选历史保持；激活/布局和QK L2完成后再执行R；读出经格式适配后N，再与独立Z在G门乘；统一处理历史/状态候选 | R原生命令序列wrapper、上下文/版本跟踪、返回数据搬运、候选输出保留 | G/N/E自动产生任意UQ1.31 decay/beta或S32 injection；R/T跨宏原子提交 |
| SSM混合层 | 卷积/激活及系数供给后执行R；先G门乘，再跨4096通道N；与注意力分支同token汇合后残差 | 可切换任务依赖表、跨分支join、长向量回放和版本槽管理 | 把GDN输出顺序直接套用；把SSM与Attention两个分支完成事件当成同一数据就绪事件 |
| MoE | router结果保存；TopK ID取回所选logits并计算路由Softmax；按动态专家ID访问权重；多次专家计算后按token/tile归并 | 有界ID到地址描述符、gather/搬运、专家循环与加权归并调度 | TopK ID本身已完成专家访问；把所有专家同时驻留/并行执行，或把动态ID改写为运行时金属重连 |

这些差异可以先由不同任务表表达，但任务表解释器、分支/循环和地址生成电路必须实际存在并计价。单纯由host每条原生命令逐次驱动可作为功能原型，不能据此报告自治系统协调器完成。

## 5. 有界性、成本与死锁审查

### 5.1 首版应明确预留和生命周期

发射任务前至少检查：所有前置数据版本有效，目标原生宏/上下文可占用，输入/输出格式合法，输出缓冲或存储范围已预留，完成事件槽可用，实际连接清单包含所选路径。S普通访问与供数宽读共享真实四bank，不能让多个wrapper各自假设独立端口。宽读和窄访问的仲裁及公平性须显式设计。

原型可先按全局保守顺序串行化各阶段，建立正确性基线；随后逐项放开M双银行装载、G流水、独立宏并行和流式边。正确性基线的串行周期不能当作最终性能，后续并行也不能在未核对容量前凭理论峰值计价。

### 5.2 不能仅凭ready/valid保证任意图无死锁

至少需要检查三种循环：数据依赖循环、资源占用循环、ready组合路径循环。R的token递推、卷积历史和KV历史需要初始状态与明确前后版本；图上有环不代表非法，但也不能没有初始数据就等待所有前置事件。不同定制产品必须分别校验任务依赖和实际路径。

输出不足时不能启动一个必须全部写完才能释放关键输入资源的任务。不能让“完成事件发出”依赖已经被数据填满的同一队列；可独立保留事件槽，或在任务开始前预留它。fork必须明确每个消费者的确认，join必须匹配token、tile、format/scale和version。ready反向连线若形成组合环或过长路径，需要预制弹性寄存器/队列断开；金属定制不能新增这些寄存器。

合理的可验证声明是：对声明的六种任务模板、给定容量、调度规则和公平性假设，检查有界等待、计数守恒和终止；不能声明仅凭统一接口即可对任意拓扑、任意停顿和任意容量保证无死锁。下游永久不ready的情形本来就不保证完成。

### 5.3 必须计入的成本

- 控制器任务表/指令存储、取指带宽、依赖表、版本/标签表、计数器、错误状态和队列。
- wrapper命令/响应寄存、G在途标签、分/拼包寄存、尾包有效信息、广播确认和join保存。
- 地址/步长/ID到专家权重地址生成，数据搬运及S端口仲裁；算术系数生成若需要新数值资源，单列为计算能力，不能隐藏在协议bridge里。
- 所有新增hard macro、输出驱动/中继、时钟与电源、M10接口及M11/M12数据和控制线的面积、线长、RC和延迟。
- 保留叶宏但改变系统负载后的完整路径时序、电气、PG和几何接入验证；跨时钟域时另需CDC设计，不能直接套同一时钟的ready/valid。

复位只清控制/有效位而不清整份payload。系统必须协调wrapper、队列、宏、外部访问器的停止/排空/失效过程；外部已经接受的存储写不能仅靠本地reset假定撤销。异常停止、硬复位、已提交状态恢复各有不同保证，首版必须分别描述。

## 6. 后续候选验证清单

1. 任务表静态检查：路径存在、方向/端口/格式匹配、容量与live range、无未初始化读取、唯一写入与版本、N上下文互斥。
2. 逐wrapper原生RTL组合：输入/输出握手守恒、随机背压、尾包、错误、复位；M混合成功/失败行及追加重试负例；G四级在途顺序；N跨批屏障与257/4096等长度回放；R历史候选后递推失败；T未写满/重复索引/提交后撤销/末字释放。
3. 六模板按同一协调RTL执行：普通Attention、QK/PostNorm、FFN双支、GDN、Falcon顺序/双支、MoE动态ID及专家归并；检查每个已发布输出对应正确token/tile/version，所有有限槽最终释放。
4. 功能通过后再综合/物理表征新增支持逻辑及选定系统路径；同源报告队列容量、最坏占用、实际周期、资源和负载范围。SystemC无时钟示例只能辅助算法和事务顺序，不能替代这些检查。

本草稿未实施上述候选验证；管理结构检查 `python scripts/check_project.py` 已通过，仅说明管理文件结构有效。
