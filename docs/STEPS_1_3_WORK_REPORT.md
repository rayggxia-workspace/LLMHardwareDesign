# Issue151前三步工作报告：仓库样本、角色连接与片上资源合同

> 2026-11-01 用户边界澄清：**系统有外存，本阶段暂不研究其实现与调度，保留接入灵活性。**本文的片上准入、EXT credit=0/valid=0、无DMA/自动spill仅属于P0片上验证profile，不构成产品永久无外存约束。片上容量缺口只限制P0，不代表完整系统必须全片上驻留。后续地址域、MEM服务和完成语义扩展见[边界与N接口澄清](MEMORY_SCOPE_AND_N_INTERFACE_CLARIFICATION.md)。

状态：**可评审规格交付，尚未实现系统RTL、冻结底座或验收整模型运行**。任务[Issue151](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/151)，交付[PR152](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/152)，负责人Melodydt。输入设计commit `39bd7bf66c47e17c18aa39483c1d974a1e079aa2`；叶宏字节继续采用PR144固定643c6012，未改叶宏源码。

## 1. 本轮授权和交付层次

用户要求开始前三步：确定有限家族域、细化全部合法连接、形成统一外侧接口和资源合同。当前只考虑仓库已有八个样本；无法确定的规模以明确方法作保守估计；**暂不考虑外存**；产品仍仅靠M11/M12永久绑定，不依赖控制程序启动装载。

本轮形成三类可复核材料：

| 步骤 | 交付入口 | 交付性质 |
| --- | --- | --- |
| 1 样本域 | [样本FamilySpec](SAMPLE_MODEL_FAMILY_SPEC.md)及family-spec.json | 八模型/十层型的配置、算子特征、范围与证据/估计分开 |
| 2 合法连接 | [角色账本](SAMPLE_LEGAL_CONNECTION_LEDGER.md)及edge-ledger.json | 完整角色候选槽、规范配方、语义前提、原生guard与缺口 |
| 3 系统合同 | [片上接口/资源](SAMPLE_ONCHIP_SYSTEM_CONTRACT.md)及onchip-contract.json | 字段、事件、lease、信用/容量、无外存准入与候选规模 |

上述JSON及验证工具位于`work/Melodydt/151/`。全局[全合法连接规格](ALL_LEGAL_CONNECTION_SPEC.md)和[总方案](SIX_CONNECTION_SYSTEM_DESIGN.md)继续记录总体目标；本报告及片上合同是当前阶段的准入依据。旧v0.3中的外存方案只保留历史/后续研究身份，不参与本阶段映射，不能成为容量不足时的隐含后路。

## 2. 步骤1：从有限家族概念落实到仓库样本

固定集合为Qwen2.5-3B、Qwen3-0.6B、Llama-3.2-1B、Gemma-3-4B、Phi-4-mini、Qwen3.5-4B、Granite-3.3B、Falcon-H1-3B；Gemma区分局部/全局，Qwen3.5区分GDN/全局，因此八模型对应十个导出层型。没有用同一家族名称自动纳入其他尺寸或后续模型。

本轮读取配置、精简/完整算子图说明、导出脚本与必要图JSON。证据分三层：

- 配置值：H/I、层数、Q/KV头数、D、位置上限、专家和递推维度等，绑定固定路径/commit/Git blob/SHA-256。
- 图推导：例如真实Split/Reshape/Tile轴序、state形状和卷积通道；记录节点或公式，不凭模型名称猜测。
- 规划估计：尚无编译/综合证据的控制存储、槽数和元数据预算，给估计方法及裕量，不写成现有硬件或实测上限。

实际导出的原生层图使用B=1、序列长2、FP32、无cache；原配置位置上限分别达到32768至262144。导出成功不能证明最大上下文、完整自回归或本项目定点质量。Llama样本为配置重建与固定随机参数，其余指定层的来源按原报告保留；Qwen3.5递推及Granite专家导出适配也单列，不能把图导出替代实现验收。

原有泛化风险得到约束：Qwen3与Falcon的Q_heads×D不等于H，不能用H/Q_heads重算D；Gemma RMS0、Phi部分RoPE、Qwen3.5输出门/头复用、Granite路由、Falcon门乘/Norm顺序均由具体样本卡约束。Qwen3.5 Q/K 16→32的连续头复用已在该固定ONNX的Reshape/Tile轴序取得证据。实际图先RepeatHeads后L2；旧语义示意的反序只能作为另证等价的优化。L2 epsilon常量payload未包含在图JSON，不能借用RMS epsilon。Falcon conv还确认有bias而R无bias口，新增显式偏置数值缺口。这些均不构成数值或物理验收。

## 3. 步骤2：从49格下钻到角色和配方

旧49类宏对保留为索引。本轮枚举23个数据源角色×27个数据目的角色，共621个候选槽，另有23源×20受控参数角色，共460个参数候选槽。**1081是待规则处理的候选槽数量，不是1081条合法/已实现连接。**

区别如下：M.op3两S64不等于M.op5四S32；N Norm/EXP/概率/ID/统计记录/factor不是一个“N128”；E12与E13低64bit的元素数不同；G gated/ungated的尺度不同；R输出、active state/history与meta不混用；S普通读、写回显、loader A/B分别登记，T保留原写入schema和有效数。

样本连接义务另见[sample-connection-obligations.json](../work/Melodydt/151/sample-connection-obligations.json)：按八模型/十层型绑定真实H/I/上下文及R特征到具体槽/配方，保留未接受的定点/容量/实现条件。它不缩小621+460角色域，也不冒充完整整数图。

每个槽引用规范配方和前提：导出/应答分类→字段/ID语义解析→必要数值转换→布局/拆拼→片上保持/搬运→目的导入。重复共享规则集中定义，避免把同一段转换描述复制千遍，也避免无限cast/绕路使覆盖分母不可定义。若算法有意多次量化，则作为独立算子节点而非透明适配。

合法性与实现分轴。缺NUM_CONVERT、系数服务或新适配器时保留实现gap；片上空间不足保留容量gap；缺数值/上下文证明时保留条件，不将全部槽涂绿。EXP不能裸当最终概率，但无损复制可以保留合法EXP lineage；ID不能裸当score，但显式gather与受检查的整数语义可形成其他合法路径。受控参数先做PARAM_BIND范围/保留位/身份检查，禁止将payload直接透传整条命令。

## 4. 步骤3：无外存的外侧合同与容量闭合

原生宏端口保持，外侧统一task、typed handle、completion event和context lease。唯一局部控驱动对应原生口；S普通访问和loader描述符归S_CTRL，M A/B仍由S loader提供。母控执行预制样本程序/有界循环，M11/M12永久绑定入口和参数。普通原生命令握手、compute_done、data_ready、publish_done、release_done分开；data_ready需要结果保存与写确认，不能只看busy下降。

同一上下文的RESUME与新context重入分开。N可保持一组统计/回放阶段，R可在原生允许的pending_history阶段回访；新BEGIN/OPEN前才处理旧上下文。R pending_state仍不能装新参数。fork记录消费者引用，join按任务/版本/位置配对，反馈具有初值和显式存储延迟。

外侧逻辑记录拟为handle256bit、task512bit、event/lease/PARAM_BIND各256bit，预制微指令128bit；拟经64bit控制flit分包传输（task8拍、event4拍），不是给每个宏增加512根并行控制pin。新控制存储逻辑预算32KiB，程序/参数ROM合计保守预算2MiB，均有项数/字宽/裕量公式，尚未编译/综合，不能当作现有RAM。

片上资源分为“原生已存在”和“新控制候选”。S=16384B、T=384×16=6144B、R active/shadow各8192B不会被逻辑描述符放大。本轮保守S规划预留loader快照1024B及T整批spool6144B，剩余计算区9216B；互斥复用必须另给调度证据，默认不偷算。

loader通用导出还需要独立1024B capture候选，另计标签。若只在S中预留快照而不加capture，又坚持loader/普通S访问串行，会出现“捕获槽满→loader不能done→S写被阻止”的等待环。因此先接完整A/B义务、取得done，再写S快照；未使用的一支必须排空或显式丢弃。该前端capture不是S已有的192B loader队列。

单T回路先把整批暂存片上，最后take后release，再以新generation BEGIN；不能同时将单T当两个租约。完整state/history根的发布、R局部commit和T批次commit仍是不同事件，无联合自动回滚。片上状态版本区若不够，准入返回容量缺口，不提供隐藏外存地址。

## 5. 保留真实规模后的容量结果

下表由[需求推导脚本](../work/Melodydt/151/derive_sample_memory.py)读取固定config计算。激活S16、权重S8、状态S32都是规划场景；它们不代表这些模型的定点质量已验收。S8权重是展示容量缺口的较小存储场景，不是精度或容量保守上界；需求JSON同时列S16权重（两倍字节），FP32导出数据还会更大。KV按B=1、配置最大位置、每层K/V均S16估算；仅列一个全局注意力层，未把它伪称完整峰值内存。

| 样本 | 一份FFN mid S16 | 一层门控FFN权重S8 | 一层KV在配置位置上限 |
| --- | ---: | ---: | ---: |
| Qwen2.5 | 22016B | 64.5MiB | 32MiB |
| Qwen3 | 6144B | 9MiB | 160MiB |
| Llama | 16384B | 48MiB | 256MiB |
| Gemma | 20480B | 75MiB | 512MiB（全局层） |
| Phi | 16384B | 72MiB | 512MiB |
| Qwen3.5 | 18432B | 67.5MiB | 1GiB（全局层） |
| Granite | 1024B/专家 | 90MiB/40专家 | 256MiB |
| Falcon | 12288B | 45MiB | 128MiB |

Granite单专家权重也需2.25MiB。即使忽略其他投影/embedding，表中最小的一层FFN权重也远超S16KiB。输入/权重在片上已初始化可用于有界算子测试，但这种假设不是完整模型的权重驻留或取数方案。

Qwen3.5单层GDN state按32×128×128×4=2MiB，old+next为4MiB；Falcon单层SSM state按32×128×256×4=4MiB，old+next为8MiB。卷积历史还分别需要96KiB与54KiB/层，另计输出、系数与元数据。这些不能因单R active有8KiB就全部视为驻留。

仅raw/EXP双缓存放计算区、输出放T的全物化Softmax，按当前分区算出的容量上限为2304元素（并不等于模型上下文支持上限）；额外活跃数据会进一步收紧。

N原生统计计数至多65535；配置全局上下文超过该值的样本还存在完整Softmax能力/计划缺口，不能用小图长度2掩盖。Gemma局部窗口1024与全局层分开判断。需求JSON另给“把所有层视为全局且不淘汰”的KV保守上界，它会高估混合/局部模型，明确不是精确峰值，也不作为新增片上存储已存在的证据。

因此本阶段可定义和核验的是片上连接原语、有限驻留tile与小组合的合同；**现有原生资源不具备八模型完整片上推理的容量证明**。若后续要全模型运行，需在用户范围内另行选择片上资源规模或调整驻留/调度，当前没有以外存自动补足，也没有删除真实模型形状。

## 6. 改动与动机对照

| 之前 | 本轮变化 | 原理与动机 |
| --- | --- | --- |
| 有限家族只是原则 | 固定八样本、十层型，逐字段附来源/估计 | 给允许域真实分母，防止family_id无限泛化 |
| 49宏对为粗索引 | 621数据槽＋460参数槽及共享配方/guard | 对齐原生角色，避免同宽误接与命令透传 |
| 存储空间可能写S/外存 | 当前合同仅片上、无自动spill，明确容量拒绝 | 不让缺省资源掩盖连接/控制成本 |
| 控制字段与队列规模未具体化 | 位宽、容量、credit、所有者及估计方法落入合同 | 便于后续RTL实现、计价与独立检查 |
| 容量按小例展示 | 保留真实H/I/位置/state并计算需求 | 避免缩形状后宣称模型可映射 |
| 图/接口候选容易混成实现 | 来源、推导、估计、RTL、系统/物理验收分层 | 管理检查、静态账本、SystemC都不能替代新RTL组合 |

## 7. 实际验证、追溯与交付状态

本轮实际执行命令、工具版本、输入固定ref/文件指纹、脚本内容SHA、输出位置/指纹及未执行项见[检查回执](../work/Melodydt/151/steps123-checks.json)、[规格验证](../work/Melodydt/151/steps123-verification.json)和[source-index](../work/Melodydt/151/family-source-index.json)。运行时新增脚本尚未提交，执行代码以内容SHA固定，交付commit由PR读回绑定，输入39bd7bf不冒充新增脚本的执行commit。

管理、来源字节、配置公式、角色账本、字段/容量/无外存准入的检查分别列出。没有运行RTL/SystemC、真实模型推理、综合/P&R或新物理资格，没有服务器作业；R资格仍受原实施任务限制。新增系统RTL实现数量不因本轮规格交付增加。

当前成果为前三步的可审查规格及验证材料，审查人待指定、PR未合并，Issue交付保持in_review而非done。有限家族完整控制程序编译、精度接受、实际RTL和物理冻结仍是后续工作。登记/看板状态在PR与[交接](handoffs/2026-10-31-issue-151-six-connections.md)分别回执，不能把文件上传等同于在线接入完成。

## 8. 2026-11-01边界修正

系统有外存，当前暂不研究。此前将P0片上评估限制写成系统限制的表述已由文首澄清覆盖。模型完整运行不要求权重/KV/state永久全片上；容量表只报告P0缺口。外存集成尚未研究，不能据此宣称已解决带宽、搬运或一致性。新增[澄清](MEMORY_SCOPE_AND_N_INTERFACE_CLARIFICATION.md)同时说明N的单顶层、多命令和异构128bit输出。本轮不改变模型形状、配方分母、原生容量或七宏RTL；实际增量检查以memory-scope-checks/verification为准，旧31文件交付和70例回执作为历史保留。
