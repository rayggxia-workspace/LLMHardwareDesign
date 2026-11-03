# H1 v0.1工作报告：有界图、控制表与资源生存期

2026-11-03（Asia/Shanghai），Issue151 / PR152，负责人Melodydt。研究输入`08451c3a563cdb331a3516d83cbf9647cd0554b1`；实际检查器与四份IR源冻结提交为`4b8e5e17cc65db8105dce43d52e93220af6942a9`。本轮是[混合控制主方案](HYBRID_METAL_CONTROL_PLAN.md)的H1/L5前置规格切片：新增离线编译和抽象检查，没有新增RTL、服务器作业、数值计算或物理资格。

结果是三图、四条选择场景在声明的抽象服务和资源上可调度，形成可重算的控制镜像、对象生存期与具体拒绝诊断；**不是三图已经在共同硬件上运行**。共同母顺序器、通用端点、新edge-store集成及真实参数服务仍为GAP。完整训练参数整数A→F质量和旧24项模型准入GAP保持独立。

## 1. 本轮具体改动

| 成果 | 内容及原理 |
|---|---|
| [图与控制规格](H1_GRAPH_CONTROL_SPEC.md) | 定义版本化A/F图IR、对象/参数/路线合同、128bit粗记录、存储和释放事件；把“允许连接”转为有边界的可检查输入 |
| [原生接口与资源审计](H1_NATIVE_RESOURCE_AUDIT.md) | 核对A2真实448字帧、F1真实256字帧、F2两次调用、S/T容量/owner及参数流；区分已测kernel与待实现公共入口 |
| [金属存储/后端输入](H1_METAL_STORAGE_PHYSICAL_INPUT.md) | 拆分产品永久镜像、运行时有源状态与数据槽，列金属位单元/读出/路线的实际后端输入，不把逻辑字节换算成物理面积 |
| [检查器](../scripts/check_h1_graphs.py)及[target/三图IR](../project/experiments/hybrid_control/h1/v0_1/target.json) | 从IR生成lowering、记录/镜像、调度与预算；对错误格式、生命周期及容量返回确定诊断 |
| [机器报告](../work/Melodydt/151/h1/evidence/report.json)与同目录生成物 | 保存三图的program、tables、完整image、schedule和SHA；每个对象都有allocate/free PC和slot映射 |
| [独立静态审查](../work/Melodydt/151/h1/review/independent-review.md) | 另行解码128bit记录和64B header、核对镜像与四路径，运行11项独立拒绝probe；不代替外部PR审查 |

H1 v0.1只支持声明的S16 Fin10、shape `[2,1024]`、token-major自然轴、baseline WFin7/epsilon_code1的A/F DAG及末端二选一。A2是既有完整Sq2 Attention；F2是编译虚拟调用，lower为同一个F1逐行执行。G2只是显式展开两次A/F，不是运行时反馈证明；CALL/RETURN、运行时LOOP、被跳计算分支、D/H/X和状态发布均未由本版本实现。扩展语法和资源域须提升版本及增加正反例，不能从opcode位宽推定已有所有操作。

## 2. 从固定父FSM到可检查粗表的原理

此前AF1024验证一个特定A→双行F父FSM：数据、参数和控制顺序固定。H1保留这些kernel及真实握手约束，将产品层序表达为离线图，再生成同一候选执行架构能够解释的粗表。本轮Python只解释抽象服务事件，不执行M/N/E/G算术，也不将一次“聚合ACK事件”冒充逐拍RTL波形。

必须保持如下顺序：

1. **ARM先接任务义务**：共同wrapper绑定岛、row、参数、上下文、输出槽及返回信用。现有F1没有这种公共admission接口；这是H2新能力。
2. **LOAD/WAIT_INPUT只建立hidden部分事实**：hidden已经经过真实目的S写ACK，不等于gamma等参数齐备，也不等于原生整帧`input_stored`。不能据此提前START或FREE源对象。
3. **PARAM/WAIT_PARAM完成整帧**：A2为hidden256字+参数192字，F1为hidden128字+gamma128字。整帧实际stored后，该消费者才不再依赖输入edge；最后一个消费者满足后才FREE源槽，再发本次原生START。
4. **STORE逐字确认后源退休**：源T保活，目的edge S请求和真实写ACK完成后才消费对应源字。整帧存储确认、CLOSE、实际T RELEASE及DONE是不同事实；关闭前禁止重入该kernel实例。
5. **外部输出也需关闭**：SETOUT/EXPORT之后等待声明的真实出口确认，再CLOSE_OUTPUT、HALT；不能在仍有活输出槽时提前报告母程序成功。最终出口硬件确认方式仍须H2定义。

F2尤其不能被误解成“先把两行都装进单F，再整体RUN”。row0必须先stored、RUN、输出存储、T释放和DONE消费，才复用F1处理row1；整体F2 INPUT_STORED是两行历史事实的合取，发生时row0已运行。局控须锁存这些行事实，而不是偷加另一份4KiB输入数组，也不能让母控逐M op/逐S字展开这段程序。

源T和edge对象是两级lease：源T在目的edge已存储后退休并关闭；edge版本继续保留，直到它的全部实际消费者整帧stored。A的单读指针T不承担fork回放。母控WAIT时，RX/TX、S helper、参数返回和ACK/事件必须独立进展，否则图的计算依赖无环也可能资源死锁；这一前提尚未由真实RTL证明。

## 3. 同一目标资源下的三图

目标为`AF_EDGE16K_SERIAL_CANDIDATE`：一个A2、一个F1和**新增一份16KiB edge S**，即M2/N2/E2/G1/R0/S3/T2，共12叶。原AF1024的11叶实跑不是这个12叶共同底座的实现证据。edge S划4个4096B槽、单普通口owner，一字数据在途、一个ACK槽和一个事件槽；粗kernel任务最多一个active。母控、局控、TX/RX holding、metadata、参数服务和控制存储另计。

正式机器程序先把真实初值x IMPORT到edge槽，确认存储后才交给消费者。对象描述符数量可以多于四个物理槽；只有旧版本实际释放后，槽才能重用，不允许用不同描述符掩盖两个同时存活张量重叠。

| 图 | 数据与控制含义 | 实际原生调用 | edge峰值 | kernel权重流 |
|---|---|---:|---:|---:|
| G1 A2→F2 | 完整A输出物化，F两行顺序展开 | A1/F1×2，共3次 | 2槽/8192B | 24MiB |
| G2 A2→F2→A2→F2 | 同一A和F关闭后重入，不复制kernel | A2/F1×4，共6次 | 2槽/8192B | 48MiB |
| G3 A2→fork(F2-left,F2-right)→SELECT | 两个参数身份不同F2均实际执行，再按接单时捕获并保持的p选择输出别名 | A1/F1×4，共5次 | 3槽/12288B | 42MiB |

G3不是ADD，也不跳过未选分支。两个F计算分支串行占用同一F；源a保留到两支所需两行输入都已实际stored。b/c都完整且对应kernel已释放/DONE后，p只选择一个对象的别名，安全回收另一对象，不额外复制4096B结果。若以后改为复制或提前发布，须重新计搬运、槽及关闭义务。

F1每行实际供应9MiB权重，即F2要18MiB；A2要6MiB。同version不自动形成缓存命中。A2另有3072B非权重参数帧，F2 gamma两行重放共4096B；这些参数、权重本体、descriptor/control cache不装进edge的四个hidden槽。当前参数提供者仅为抽象公平服务，不证明真实MEM容量/带宽、缓存或故障恢复。

## 4. 控制表预算怎样得到

候选粗记录为128bit/16B：opcode8、flags8、a/b/c各16、imm32、next16、aux16。字段按opcode检查命名空间、保留值、长度/范围和后继；编码后再解码读回。产品镜像还包含64B头、每对象64B描述、每参数引用32B及每路线16B。参数引用摘要只是符号身份，不能冒称真实权重SHA；路线的ACK宽度占位0表示H2待定，不是零宽ACK硬件。

| 图 | 存储的程序条数/字节 | 对象表 | 参数引用表 | 路线表 | header | 完整候选镜像 |
|---|---:|---:|---:|---:|---:|---:|
| G1 | 48/768B | 192B | 64B | 96B | 64B | **1184B** |
| G2 | 88/1408B | 320B | 128B | 96B | 64B | **2016B** |
| G3 | 81/1296B | 256B | 96B | 96B | 64B | **1808B** |

G3镜像同时存放p的两个末端选择路径，因此存储81条；每个具体p场景执行75条。两个F计算分支在两种场景都执行，不能把“只走一条SELECT末路”写成只运行一个F分支。

共同逻辑上界候选为：

```text
64B header + 256×16B records + 17×64B objects
           + 16×32B parameter references + 6×16B routes
= 5856B = 46848 logical bits
```

每产品分别占用同一候选容量，不把三个镜像简单相加，也不以平均需求取代最大需求。16调用、17对象等上限同时受256记录等其它上限约束，不能保证任意16调用都能装入。

5856B不是已实现或物理合格的ROM，也不一定由同一阵列承载；不含权重/gamma/系数、参数缓冲、运行时PC/owner/事件/版本等状态、本地程序、通用fault handler、译码/读出/holding/测试及布线面积。普通RTL ROM、tie端口或软件hex都不证明M11/M12逐位可编码。位单元、地址译码、读周期、扇出/landing、定制通孔、读回及几何/STA仍须后端验证，不能在产品金属阶段临时新增有源控制或修复buffer。

## 5. 实际验证与来源

实际源冻结与远端5文件blob/内容读回记录见[source-commit-receipt.json](../work/Melodydt/151/h1/source-commit-receipt.json)。源码提交为`4b8e5e17cc65db8105dce43d52e93220af6942a9`；检查器SHA256为`341d13be96edd24ced7bc42b1c88a0a6363ea9bcd7cecd7a4f6eef0ccd25c0cf`。该提交绑定检查器、target及三图IR；本报告和后续资料的最终commit以PR回执为准，不把实跑/检查源码替换成后续文档提交。

已执行的离线主检查命令为：

```text
python -B -X utf8 scripts/check_h1_graphs.py --root . --out work/Melodydt/151/h1/evidence
```

[机器报告](../work/Melodydt/151/h1/evidence/report.json)记录实际Python3.12.14、标准库抽象检查器、输入及产物SHA。结果为三图、四条场景、28项正式预期拒绝通过；拒绝覆盖格式/Fin/轴、未定义读、缺入口、参数ABI、容量、返回信用、早FREE、重入、整帧前START、重复EXPORT、非法跳转及不支持的运行时反馈等。

[独立审查](../work/Melodydt/151/h1/review/independent-review.md)另检查三图四路径、128bit记录与header解码，并通过11项独立拒绝probe。审查中实际发现并修复了释放在途目的槽后重新分配、目标容量/owner/记录宽不一致，以及重复EXPORT的问题；正式源码和28拒绝例保留这些防线。独立审查r01的唯一失败是其预期诊断名过于宽泛，r02仅修审查预期；两份记录保留，不把历史失败覆盖为成功。

这里的PASS是离线编译/抽象事件和预算检查。没有启动RTL编译/仿真、服务器任务、M/N/E/G数值、综合/P&R或物理签核；不是所有图正确性/硬件活性证明，也不是外部PR审查批准。原54份runtime/旧source-lock与八样本旧24项模型GAP保持；QUALITY95979及AF1024既有资格不因本轮图规格扩大。

## 6. 风险与H2工作包

| H2工作包 | 必须形成的真实实现/验收 |
|---|---|
| 共同任务wrapper与局部入口 | ARM先承担义务；hidden部分SACK与完整参数帧stored分开；A2组帧、F2两行历史事实/输出拼接；F prestart失帧也有父错误终态 |
| edge-store及TX/RX | 新S、单owner/helper、一字在途、ACK/事件独立保持；真实目的写ACK后源T退休，所有消费者整帧stored后FREE；无RAM旁路造数据 |
| 参数/身份与编号 | 解析产品参数引用，适配A generation32与F job16、不同版本/旧流策略；按图预算F start数，G2/G3需4次，不能照抄AF1024只预留2次的guard；复位/晚返回需明确隔离 |
| 固定母顺序器与表读取 | 实际取指/字段/PC范围/holding；同一RTL实例图只更换合法产品表/路线内容，先G1再G2/G3，验证p捕获、别名和未选对象回收 |
| 错误及复用 | 背压、返回重复/错关联、错误/partial、取消、reset、编号边界、poison和held终态；源RELEASE/DONE前不重入，已输出前缀不回滚 |
| 后端可行性并行输入 | 确定金属编码/译码/读出/路线与全部预制有源成本；控制表逻辑容量不能先当已可制造结构 |

H2测试应从真实S/T和kernel行为观察ACK/释放，再与H1表和对象生存期对照；母控WAIT期间辅助服务不得停住其所等待的返回。公平性、外部永久背压和参数进展必须作为明确前提。当前正常路径模型不执行通用fault handler，不能声称错误处理程序容量或最大恢复延迟已经闭合。

后续H3再扩运行时循环/被跳分支、反馈及一般拓扑的版本化语义与覆盖。L4-QUALITY-AF的真实训练参数完整整数AF oracle、代表性新cal/holdout和独立产品误差/clip阈值继续并行；本轮不据图可调度接受trained质量。R/NUM、D/H、MoE、MEM及共同底座物理也保持各自退出门。

## 7. 交付与PDF状态

继续复用Issue151/PR152、`task/151-six-connection-study`→`task/143-seven-block-v2`。源码上传及5项读回不等于外部审查/合并或Issue整体完成；本轮没有自合并。工作包是隔离API部分副本，不能把本地资料存在写成main已更新或共同硬件已冻结。

用户要求每完成一步覆盖同一现有本地交流PDF，不创建新版本、不上传PDF或发送他人。本报告**不预报PDF覆盖及QA完成**；最终实际文件SHA、页数、覆盖和QA状态统一见[本轮PDF最终索引](../work/Melodydt/151/h1/local-PDF-index.json)，由根任务在实际结果形成后记录。

H1 v0.1交付的是有边界的规格、可重算镜像和抽象调度证据；下一执行门为H2真实共同控制/端点切片，所有未实现、未映射、物理及质量项继续显式保留。

## 本轮附带修复：W5历史文档与当前方案分开验指纹

首次交付检查在当前输入08451c3上发现继承性失败：H0 v0.6更新了控制合同正文及层级文档补记，旧W5-IF来源锁仍要求它们逐字匹配旧版本。旧锁和54runtime没有改变；quality基线上的原检查仍465项通过。
本轮保持当前v0.6政策，不把它回退成穷举产品ROM；保存两文档精确历史快照和有序变换manifest。check_w5_if.py继续对历史内容执行原SHA/字节/blob检查，额外对当前文档的SHA、每段原文范围及完整变换重建做精确核验；只对显式登记的docs文件使用此规则，原生代码一律按当前源匹配旧锁，不允许历史fallback。
当前W5-IF已525项/22原锁通过，两份文档变换有证据；新旧锁文件没有重写。拒绝被篡改当前正文/历史快照/变换、对原生源误用fallback的独立检查见review目录。该修复只处理文档版本关系，不重授算法、RTL或物理资格。

