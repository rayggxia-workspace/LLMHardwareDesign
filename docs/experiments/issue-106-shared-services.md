# Issue106：M/A/Falcon R 的真实共享服务银行

2026-10-25，Liangruizhi。Issue106；task/106-shared-services；独立目录 D:/Projects/LLMHardwareDesign-shared-services。102 PR105 a62cffbf 与99 PR103 8c51f5df均已发布且CI成功，本任务合并后实施；PR审查/合并由主会话处理，不自行done。

## 当前结论与边界

已获得完整切片L2证据：专用Granite V/M链、完整8头materialized GQA、Falcon单head状态控制器，共用**实际唯一16KiB 128bit 1RW、8个S8乘法、1个S32乘法服务、1个SFU、1个外部桥**。先前独立预算切片已经在这三个profile上成为真实同一份硬件。两种等待模式的7命令交替运行、27命令恢复均独立逐值通过，8个数值/协议真实重SHA负例与2个实际库存负例被拒绝。

选定raw门级已通过：两等待模式各INIT→完整M0→完整8头A→完整R0共4记录，与同driver RTL的全部字段、周期、IO完全相等，并再次接受独立原数值oracle；没有将RTL-only Q注入或完整恢复套件写成门级资格。真实宏、时序、物理预算、全模型数据链、通用V ISA/GEMM、KV append/online、GDN104接入与制造后定制均未完成。不能称全部M/V/A/R/S/D库已正确完成，也不能继承98对其他网表的物理结果。

## 实际资源抽离

shared106 是唯一资源拥有者；m106/a106/r106/norm106/mfront106/attention106仅保留原数值控制和局部寄存，原97/102/99源文件未改。M与A的8个S8乘法移到同一bank；norm内部SFU也真正移出。S32保留原mul84两个64bit有限响应槽，每拍只有一个实际S32乘法。

同一owner lease从cmd接受保持到完整结果导出和DONE ACK，期间没有其他owner使用资源。M/A的完整结果和R candidate Y通过同一S端口读出，背压期间数据保持。R先导出128个候选Y再允许accept/reject；accept后root128bit提交不可取消。切换不是多核并行或无代价crossbar。

输出sink是另一个明确接口边界：M/A export前缀在status0 DONE前属于provisional，abort须丢弃该lease前缀；R为candidate再accept。当前C++接收器保存M6KiB/A4KiB/R512B向量，属于环境/测量存储，最大6KiB不在core逻辑面积或16KiB银行内。未来真实下游需提供事务暂存/提交或可撤销流式消费，未在本任务实现或物理计价；不能把导出完成称后继全硬件流水线完成。

所有三套controller、行寄存、宽比较/RNE/shift、地址选择、状态/scale元数据和D导出/排空都进入综合。独立库存结果：125,966.694 µm² logic-only、85,355个mapped cell、9,397 DFF_X1；generic寄存10,752bit（含wrapper中的寄存），另有131,072bit单1RW行为memory。**未包括SRAM/ROM宏、物理互连和环境fabric。** 该逻辑面积已超过98旧网表79,600.5 µm²预算，不能扩大旧预算后宣称物理通过。

环境仍有限：最多两个128bit数据+32bit tag响应槽，至少320bit加控制；32bit请求/响应epoch为sideband，不混入5个128bit beat的payload费用。LUT是外部128KiB C0，所有查表付外部事务；Falcon backing固定1MiB。M、A、R数据窗口分别04/05/06，原字节只重定位，不碰程序或LUT窗口。详见[冻结协议](../../project/experiments/shared_services/PROTOCOL.md)。

## 数值与最小输入

- M：原74/97的L0 token0和L13 token71原始gate/up I32Q12，由实际RTL产生SiLU、MID、每专家整512最小δ和A8，再完成K512/8专家/H1536实际M、重定标、merge/residual、93流式norm。没有host中间结果。
- A：102原Qwen2.5-3B、L0/KVhead0、8Q×d128的真实full position0和**实际cached** position128，长度1/129。Q8/KV16、3limb QK、S32Q12 score、expQ30/U64sum/P15、9limb PV与原函数一致。三遍materialized，非online。
- R：99原Falcon head0 D128×N256全32,768个S32状态，从空白INIT到连续STEP0/1跨M/A lease。完整head guard、RNE、局部单位/epoch和128个Y全部独立bigint核验。不是32head/4096norm/conv或GDN。

INIT→M0→Afull→R0→Acached→M5→R1仅是不同真实工作负载的资源切换，不是同一模型端到端数据链。输入复制前核验旧manifest/文件SHA，原payload未改。独立oracle回到97原张量、102原捕获与编码和99标量数学，而非只比较两个新仿真器。

## 端口、缓冲与周期

下表为无等待模式实际回执，S读包含真实结果导出，外部每事务5×128bit=80B。另一等待模式保持相同数值、事务、S端口、乘法和SFU次数，周期独立记录。

| 命令 | D实际cycles | S读/写行 | 外部事务 | S32次数 | SFU次数 | 导出字节 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| INIT | 98,701 | 0 / 0 | 8,225 | 0 | 0 | 0 |
| M0 | 6,004,003 | 395,776 / 2,432 | 412,032 | 33,280 | 1,538 | 6,144 |
| A full1 | 8,292 | 784 / 528 | 272 | 8 | 8 | 4,096 |
| R STEP0 | 2,047,823 | 148,000 / 33,026 | 73,923 | 98,688 | 0 | 512 |
| A cached129 | 892,772 | 54,544 / 35,728 | 35,088 | 1,032 | 1,032 | 4,096 |
| M5 | 6,003,993 | 395,776 / 2,432 | 412,032 | 33,280 | 1,538 | 6,144 |
| R STEP1 | 2,047,823 | 148,000 / 33,026 | 73,923 | 98,688 | 0 | 512 |

两模式完整7命令D总周期分别17,103,407/20,314,135；相同S读1,142,880行、写107,172行、外部1,015,495事务、结果导出21,504B。外部数据payload16,247,920B、五beat线上81,239,600B，另有32bit epoch侧带。等待增加周期而不改变数值和实际库存；这是同一电路对服务背压的受控比较，不是不同物理边界的PPA收益。

M每次重新生成4KiB A缓存，A会覆盖该区域；R每STEP重新载入系数/状态行，持久状态保存在外部双bank/root。跨lease不能免费保留S缓存。M/A/R暂存没有通过简单划三个16KiB小核伪装共享。

M/A实际结果导出分别384/256次S读；无等待占768/512拍。相对自身controller active计数，D再加1/4拍。R的旧字段`compute_cycles`实际是controller active，已包含OFFER中的64拍candidate导出和决定等待，不能再次相加；R的D计数再加1拍。这只是行为周期分项，选择器物理延迟/频率仍未测。不同库存的旧三核面积和不用于同资源加速比。

## 恢复、版本与已修问题

最终每模式27条命令：M link/S32、A已接受store/SFU/export、R已接受write共6次真实abort；所有已接受服务effect-once排空，之后才局部reset或结束取消。2次stale响应、实际epoch max注入、12拍拒新cmd、终止同tag排空、协调硬reset与R RESTORE均接收。门级不复用Q注入资格。

A注册owner/version/地址/单位/有效长度跨M/R和softabort保留；同version换scale、回旧version、换owner均拒绝且零service副作用。实际cached快照重新绑定version3，再回full源为version4；不能假定地址与scale相同就意味着host可偷偷换快照。length仍是调用方已提交有效前缀，RTL不证明KV append。

根审查发现首次原型cfg响应遇soft_abort时公开valid为0但内部take仍可能消费，已修复为同资格门控。读、写ACK各4拍冲突保持后唯一ACK并可继续完整命令，真实测试通过；reset时service_accept亦被屏蔽。旧phase1/2原型源/执行保留。phase3旧23命令、phase5旧27命令不覆盖；最终phase6使用收紧快照版本的driver，RTL仍同字节。

INIT继承99的**破坏性空白配置**，不能把INIT中止称STEP式旧状态保全。本批只对空白授权image INIT，STEP/reject/abort保留旧已发布state/Y/root；硬reset须协调fabric，当前共享top仅验证空闲协调reset后RESTORE，未新增mid-commit硬故障资格。128bit原子root与ACK effect-once是外部接口义务，非物理原子性证明。同epoch恶意重复响应不在接口保障内，epoch是lease代号而非每事务ID。

## 可复查入口与剩余边界

实际RTL `4ec4bcf`（后续数值RTL不变）；正常driver同提交，最终恢复driver `ee770a1`；唯一库存/门级工具 `3ad6f81`，归档分析工具 `f3c8fd5`。七阶段168个源码条目已与原Git blob逐字节核对，完整包与精选包在服务器、精选在PC均独立字节接收通过。最终交付只去掉a106.sv第39行三个空格，work106/format-addendum.json保存唯一纯空白差异和old/new SHA；正式数值/map/gate收据继续绑定真实旧源码，不替换为新SHA。

运行仅本人服务器 `/public/home/yuzelu/RuizhiLiang/issue106-shared-services-20261025`；全部实际命令、作业及条件写入work106 execution。先`python -B scripts/check_project.py`；数学/RTL/map/gate/归档仅服务器；PC只源码/报告/metadata/字节接收。

下一步按104独立交付接收GDN控制器，作为明确新增profile接入同服务，不重跑大模型；对宽控制/状态寄存与选择器真实面积定位后决定是否共享进一步的宽算术。新的物理预算、宏/PVT、制造后连接仍需单独资格和项目约束。

## 交付与实际检查

41个本人Slurm作业全部COMPLETED/exit0；无科学作业失败或取消。旧原型与被替代的恢复输入版本原样保存，不能把已修cfg原型写成当前合格实现。完整运行argv及最终Slurm见[execution](../../work/Liangruizhi/106/execution.json)，包含阶段源码、CPU资源、输出目录；current归档/接收作业日志由最终补充回执记录，避免归档正在写的自身日志。

[结果索引](../../project/experiments/shared_services/results/issue-106/index.json)、[汇总](../../project/experiments/shared_services/results/issue-106/summary.json)、[门级回执](../../project/experiments/shared_services/results/issue-106/gate-receipt.json)提供精确绑定。完整包留授权服务器delivery01/full-results.zip：41,646,013B/439成员，SHA-256 `e0b0b81d0b34eedfd332cf39d6585c918c06710d97aa0f46e486856fd39e4009`；精选163,973B/91成员，SHA-256 `febc28393354fa6f05c5d9e5f17ceb75a4c2cc80f2d2ac6398938082c1c00e9b`，随仓库交付。精选不能替代完整原输入/日志数学重放。

管理结构、源码静态语法及累计diff检查见work106最终local-checks。本地已整理；主会话负责push/PR与在线状态，当前不称远端已上传、已审查、已合并或done。登记PR5 pending，看板配置/read:project缺项unverified/同步pending；按既定管理员交接。


发布回执（2026-10-25）：[PR108](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/108)已上传；Issue106 in_review，待独立审查，未合并/done。报告、索引、门级回执和库验收表与原Git字节读回一致，见work/Liangruizhi/106/remote-readback.json；登记PR5 pending、看板unverified/同步pending。共享服务/宏/物理仍未完成。
