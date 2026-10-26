# Block v1 Nangate45 原生层预制与 M11 M12 定制互联实施计划

日期：2026-10-26，中国标准时间。状态：待用户审查。项目：rayggxia-workspace/LLMHardwareDesign。

本计划确定第一版可硬化的共享计算 Tile、真实存储和事务接口，使用 Nangate45 原生全部金属层完成预制 Block，再自行定义 M11/M12 完成后定制 Block 互联。用户审查计划后开始实现；当前不启动服务器探测、RTL实验、工艺修改或布局布线。

## 1 用户确认的制造与资源边界

| 项目 | 本次采用的定义 |
| --- | --- |
| 预制 Block | Nangate45 原生 metal1–metal10 全部允许用于块内信号、供电、时钟和固定接入；不要求清空原生高层 |
| 新增互联 | 自建研究用 metal11、metal12，以及连接 M10/M11 的 via10、连接 M11/M12 的 via11 |
| 冻结部分 | 有源单元及位置朝向、M1–M10、via1–via9、M10 接入 landing、固定 PG/CTS、预制缓冲与寄存资源 |
| 后定制部分 | M11/M12、via10/via11，以及计划明确允许的新增层图形；不能借后定制修改固定 M10 来补 enclosure |
| 当前实施范围 | 第一版 Block 库与接入能力；底座最终阵列规模不在本轮一次性定死 |
| 服务器并行 | 本任务以 6 个节点为基础、最多扩至 8 个节点；这是本任务预算，不是共享账号的总任务或节点限制 |
| 节点内部 | 在实际分配 CPU、RAM、工具线程、许可证和 I/O 约束内并行，避免串行闲置和资源超配 |

此前讨论的“M1–M8 固定、M9/M10 定制”属于其他任务方案，本计划由上述用户要求替代，不作为本轮主方案或默认回退。

## 2 Nangate45 原生层核验与扩展定位

已核对官方 OpenROAD-flow-scripts 固定提交 `64939f3717ad7c694199ba04cb98924b98022868`：technology LEF 的最高 ROUTING 层为 `metal10`，原生连接定义到 `via9`；config.mk 的最高布线层为 metal10，OpenRCX 规则声明 `LayerCount 10`。官方默认 IO 层为 M5/M6。

| 资料 | 固定来源 |
| --- | --- |
| 原生层与 via | [NangateOpenCellLibrary.tech.lef](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/64939f3717ad7c694199ba04cb98924b98022868/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef) |
| 平台布线、IO 与库设置 | [config.mk](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/64939f3717ad7c694199ba04cb98924b98022868/flow/platforms/nangate45/config.mk) |
| 原生轨道 | [make_tracks.tcl](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/64939f3717ad7c694199ba04cb98924b98022868/flow/platforms/nangate45/make_tracks.tcl) |
| 早期 RC 设置 | [setRC.tcl](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/64939f3717ad7c694199ba04cb98924b98022868/flow/platforms/nangate45/setRC.tcl) |
| 十层提取模型 | [rcx_patterns.rules](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/64939f3717ad7c694199ba04cb98924b98022868/flow/platforms/nangate45/rcx_patterns.rules) |
| 原生几何检查 | [FreePDK45.lydrc](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/64939f3717ad7c694199ba04cb98924b98022868/flow/platforms/nangate45/drc/FreePDK45.lydrc) |

实施开始时还需核对授权服务器实际安装的平台、工具与这些文件的版本差异，封存实际输入清单。此处核实的是官方基线，不假定服务器安装字节完全相同。

新增层应命名为本项目的 Nangate45 十二层研究扩展。它使用明确的几何、电气和介质假设，不宣称 Nangate45 原生已有 M11/M12，也不把研究规则等同于代工厂新增工艺资格。原平台只读，扩展配置与技术文件进入独立 overlay 和版本目录。

## 3 第一版 Block 与数值接口

### 3.1 物理组织

| 对象 | 第一版内容 | 封装与成本 |
| --- | --- | --- |
| C8 共享计算 Tile | M/V、Attention、Falcon R、GDN R 四类有界控制器；8 个 S8 乘法 lane；一个 S32→64 服务和两个响应槽；U128 除法/开方 SFU；仲裁、宽 guard/RNE、局部反馈和 D 控制 | 首版整体硬化；内部功能分区不自动变成多个物理宏 |
| S16K | 1024×128 bit、16 KiB、单 1RW、有限响应；无隐含 byte mask 或额外端口 | 使用同一份存储，首选 Tile 内存储叶实例；若采用固定贴邻封装，必须在 P0 二选一锁定。独立核算 Lib/LEF、面积、PG、时序和 OBS |
| T6K 事务接收壳 | 覆盖现有最大 6144 B 输出；保持 provisional 数据，支持 commit/revoke、背压和旧引用释放 | 消费者侧真实实现并计价；若用 8 KiB 实体承载则按 8 KiB 计面积和时钟 |
| 外部桥 | 现有 128 bit、每事务五 beat、有限响应和 generation；明确 fabric 对 root 原子写、effect-once ACK 及协调 reset 的义务 | Tile 内桥和父层端点分别列账；外部权重、KV/state 与 LUT 不当作片内容量 |

当前 C8 是四 profile 单 owner 的研究实现；不追加通用 GEMM、16×16 阵列、通用 V ISA、多 profile 并行或新的模型。M/V/A/R/S/D 保留为逻辑责任，P1–P15 保留为能力覆盖清单。

### 3.2 固定的算法与协议

- M 保持完整 K 归约、部分和与完整结果的区分、原有 scale/RQ/RNE/guard；保留已实现的 A-cache 开关和旁路。
- V 保持完整行统计、流式 gamma、SiLU 和完整 K 量化统计，数据写 ACK 后才发布 scale/valid。
- A 保持当前 Q8/KV16/P15、limb 分解及三遍 materialized 算法；不顺带加入 online softmax、KV append/淘汰或 RoPE。
- Falcon 与 GDN 保持各自的完整 head guard、trial/retry、shadow、epoch、metadata 与 root 发布域；不得把 GDN 两 head 改成独立发布。
- S 的 reset 清响应控制，不假定初始化全部 words；每次读取必须有当前有效性或加载依据。
- D 锁存已接受命令，响应属于原 owner；abort 排空旧请求，generation 不回卷，accept 后 commit-drain 不可取消。
- 输出可见性由真实 T6K 和下游消费协议闭合，不能继续以测试环境永远接收来替代。

功能基线选 [PR113 的电路候选 v2](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/c03ba985e516b006ec2f936175b8588fc0de48af/docs/BLOCK_CIRCUIT_CANDIDATE_V2.md)，固定提交 `c03ba985e516b006ec2f936175b8588fc0de48af`。先沿用原实现，不直接把基于另一顶层的 #110 宽度优化叠入首版。

## 4 自建 M11 M12 技术模型

新增两层是一条独立的实现工作流，不能仅修改 MAX_ROUTING_LAYER 或 LayerCount。以下字段在实现前给出明确数值、单位、出处或外推方法，并固定版本；本计划不填造工艺参数。

| 工作包 | 具体内容 | 验收结果 |
| --- | --- | --- |
| 技术 LEF | metal11/12 的类型、方向、宽度、pitch/offset、spacing、EOL/PRL；via10/11 的 cut、spacing、enclosure、可叠规则和电阻 | 数据库可完整读入；连接与 track 可达；不会覆盖原生层定义 |
| 物理堆栈 | 金属厚度/高度、层间介质、介电常数及电阻模型 | 参数表和假设来源可追溯；M10 到新层的关系明确 |
| 路由平台 | 十二层 tracks、容量和阻挡；块内最高 M10，父层仅 M11/M12 信号走线，允许 via10 访问固定 M10 landing | 针对性测试证明路由器不会偷偷降到原生层绕行 |
| RC 模型 | 覆盖 M10–M11、M11–M12 耦合和 via10/11 电阻的研究提取模型；原生层模型也需纳入整体一致性检查 | 全部新层导体和 via 有 RC 覆盖；能独立读回且单位、连通和总量正确 |
| 版图映射 | 不冲突的 GDS layer/datatype、显示、数据库导出与读回 | LEF/DEF/ODB/GDS 的层及几何对应一致 |
| 几何与连接检查 | 新层及其与原生层的 spacing/cut/enclosure/short/open；更新 DRC 和连通识别 | 原检查器未覆盖的新层不得以旧 deck 的零违例代替 |
| 工具能力测试 | 内部 M10 pin 经 via10 到 M11，再经 via11 到 M12 的读入、路由、提取和检查 | 小测试先通过，再运行完整 Block 和父层 |

M11/M12 首轮建议采用正交优选方向，具体宽度、pitch 和 RC 数值按明确研究假设选定。对关键参数保留低/基准/高敏感性配置，避免收益只依赖一组乐观假设；参数变体不能更改已冻结的原生 Block 几何。

早期可以用显式参数 RC 支持筛选，但应标为估算。最终研究验收需取得覆盖十二层的提取路径及校准/交叉检查；若工具不能支持，则保持该阶段未验收，不能将十层规则直接用于新层，也不能只把 LayerCount 改成 12。可参考 [OpenRCX 官方模型校准流程](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6ea4ca224f3589dd91809933f50f39af66053634/src/rcx/doc/calibration.md)。

## 5 内部 pin 与 M10 固定接入

采用“边缘时钟/窄控制＋允许内部宽数据窗口”的方向，以同版 C8/S16K 的真实端点重新生成候选。PR120 旧 ACT/GEMM 的坐标、外框和绘图分束不直接移植。

```text
块内逻辑或存储端点
    → M1–M10 中真实固定接线及 via1–via9
    → 块内部或边缘的固定 M10 landing
    → 后定制 via10
    → 后定制 M11 / via11 / M12
    → 另一固定 Block 的 M10 landing
```

固定接入须按真实数据束、scale/metadata、byte enable 和握手关系组织；与 PG、CTS、单元/宏 pin、全层 OBS 及 via 栈共同规划。M10 landing 的形状和间距在预制阶段保证，后定制不能增补固定层金属。

首轮只比较两个方案：A 为分组边缘窗口；C* 为少量内部宽数据窗口与边缘控制的混合方案。先选择完整活跃数据束及其控制返回进行局部验证，再决定是否扩展。B 多排布局仅在解释失败或接入压力时追加，不先跑全组合。

| 对照 | 邻接供数 | 父层接入压力 |
| --- | --- | --- |
| A | C8/S16K 完整事务 | 固定父层位置下的远端或高扇出目标 |
| C* | 相同事务、位宽和端口 | 相同父层对象、位置与预算 |

评分包含完整块内线、父层线、via 栈、全部负载、缓冲、时钟和未使用 landing 成本。PR120 的最近追踪端点 L1 减少约 42.4%/52.4% 仅用于筛选；其候选仍有 ACT145/GEMM260 个 pin 的异网相交，不是可直接采用的合法视图。[来源](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/4f91e098127b4320ce50dcb29165a7af1fca559c/docs/experiments/issue-119-pin-xy-candidates.md)

## 6 PG CTS 与有源资源冻结

第一版建议把 Block 内 PG/CTS 及底座公共 PG/clock 主干放在原生固定层，并在共同底座冻结前完成。M11/M12 首轮用于后定制数据信号及跨块命令、控制和握手信号；窄控制位于边缘并不意味着允许改动原生层连接。若后续需要承载时钟或供电，须作为明确新增方案，计入轨道和接入预算。

预制阶段允许必要的 buffer、resize、hold 和 CTS 修复，但全部进入最终库存和面积。后定制阶段禁止新增有源单元、resize、移动实例、改变时钟门控或修改固定层。长线/扇出修复必须使用预先存在且登记的驱动、中继和流水资源；没有这些资源时保留失败，不让父层 repair 自动创造资源。

宏视图保留真实 pin/OBS，不用整层开放或删除导体伪造接入。内部 pin 允许从上方接入，应导出精确合法窗口及其真实金属和 via。

## 7 分阶段实施与进入条件

| 阶段 | 工作与输出 | 进入下一阶段的条件 |
| --- | --- | --- |
| P0 输入与合同 | 用户审查；查重建立实施 Issue 和独立分支/工作树；核实际工具/平台；固定源码、算法、资源、存储方案、新层技术定义、时钟/面积/修复预算 | 所有输入有版本和实际可访问位置；新层关键参数有明确假设 |
| P1 并行补齐 | A线完成 T6K 和实际存储适配；B线完成十二层 overlay 与几何/RC 测试；C线维护整数/协议独立接收 | 功能、技术小例子和有限容量各自通过，无免费资源 |
| P2 合格源码与综合 | 完整四 profile、恢复/背压/重标/epoch 回归；综合精确新网表，核库存与映射门级；重提取同版端点 | RTL/网表/端点/库绑定；原数学不变且响应所有权正确 |
| P3 原生层 Block 硬化 | C8/S16K/T6K 与获准 pin 候选并行；placement、PG、CTS、route 和 RCX；内部最高层 M10 | 完整端点 setup/hold、电气、连通、DRC、PG、RC 覆盖合格，全部修复计价 |
| P4 宏视图与叶块冻结 | 最终网表门级、LEF/Lib/寄生/OBS 导出与父层接入自检；固定 M10 landing；规范化叶块冻结清单 | 视图同源，边界寄生无漏计/双计，叶块固定几何和有源库存明确 |
| P4b 最小共同底座冻结 | 为后续产品对照锁定同一组 Tile 实例、位置与朝向；完成父层公共 PG/CTS、全部预制 buffer/中继及固定 M1–M10 引出几何 | 父层与叶块共同进入冻结清单，所有预制有源资源和原生导体一致；不把叶宏冻结当作共同底座冻结 |
| P5 新层定制互联 | 固定同一组 Block 实例/位置/朝向和原生导体；只对 M11/M12 与 via10/11 做不同产品连接 | 路由、层差分、连接、全层 DRC、十二层 RC/STA 和功能回装通过 |
| P6 发布与参数库 | 发布宏、技术 overlay、接口/模式表、成本、失败与敏感性、数据索引 | 可由冻结输入接续；未验部分准确记录，不宣称制造签核 |

首轮研究时钟建议以既有流程的 10 ns 为目标，实际 driver/load、输出负载档、uncertainty、面积与修复上限在 P0 按新实体重新锁定。#109 不继承 #97 的 79,600.5 μm²预算或已经合格的时序。实际存储、T6K、clock、PG、观察逻辑和所有修复应完整列账。

## 8 服务器并行 DAG

```text
用户审查
  ├─ T6K与存储适配 → 四profile RTL/恢复/整数接收 ─┐
  └─ 十二层技术overlay → 几何/连接/RC小例子 ─────┤
                                                 ↓
                                      合格源码、库和综合库存
                                         ├─ 映射门级回归
                                         └─ 独立块/获准候选 P&R
                                                      ↓
                                               详细布线并封存
                                ┌─────────────────────┼──────────────────┐
                                ↓                     ↓                  ↓
                         RCX→STA/电气           DRC/PG/冻结审计     最终网表门级
                                └─────────────────────┼──────────────────┘
                                                      ↓
                                             宏视图与叶块冻结
                                                      ↓
                                      共同底座布局、PG/CTS与中继冻结
                                                      ↓
                                        M11/M12产品互联并行实现
                                                      ↓
                                           回装验收、敏感性、归档
```

映射门级与同源 P&R 可以并行；RCX 必须依赖该候选真实详细布线。最终门级必须针对实际物理最终网表，不能只接收综合初始网表。完整 RCX、最终网表门级和几何/PG审计可在同一冻结结果上并行，汇总时全部成功才接受。

## 9 六节点基础与两节点弹性安排

### 9.1 节点分波

以独立 allocation 槽 N1–N8 表示本任务节点，不代表固定占用集群实际 node1–node8。按当前队列选择 c64/c96；存在可运行任务时以六节点组织吞吐，第七、第八节点用于关键路径或长尾。依赖未满足时不为凑数占节点。

| 分波 | N1–N2 | N3 | N4 | N5 | N6 | N7–N8 弹性 |
| --- | --- | --- | --- | --- | --- | --- |
| 功能与技术资格 | 四profile、恢复、背压回归分片 | 独立整数/SAT/协议接收 | 技术overlay、via和RC小例子 | 存储适配、接口与容量 | 综合准备/已冻结基线重放 | 关键失败复核或有独立依赖的工作包 |
| 综合与端点 | 独立块及获批实现候选综合 | 映射门级 | 同版 pin/OBS 和层审计 | 存储/事务壳回归 | 独立库存/数值接收 | 关键路径综合或长尾门级 |
| 物理阶段 | C8及获准pin候选 | S/T物理任务或接入验证 | 合格候选独立重放 | 已完成候选的RCX/STA | 最终网表门级/PG审计 | 剩余独立候选或最慢作业 |
| 后定制与发布 | 不同产品互联/回装 | 提取与敏感性 | 完整STA/电气 | 固定几何/DRC/PG审计 | 独立接收和参数汇总 | 关键路径/长尾；结束后释放 |

上述槽位随 DAG 动态复用，不把“某节点专门做一次小检查”变成长期闲置保留。候选数由研究问题和审查范围决定，不为占满八节点而增加变体。

### 9.2 节点内部并行

| 实际分配资源 | 可采用的起始配比 | 适用条件 |
| --- | --- | --- |
| 64 CPU | 4×16 核，或 8×8 核 | 独立综合、轻量布局或回归分片，内存总峰值可容纳 |
| 96 CPU | 8×12 核，或 5×18 核 | 独立任务能够使用这些线程；留出的 CPU 不虚报为已使用 |
| 重型 route/RCX | 每节点先 1 个重任务，按 MaxRSS/可用RAM决定是否再并行轻任务 | 优先保证内存和 I/O，实测后扩大同节点并发 |
| 单线程仿真/oracle | 多个独立输入/等待条件/工作负载进程 | 每实例独立目录和结果，不能只给一个进程申请很多核 |

运行时对每个进程显式设置工具线程、OpenMP/BLAS线程，按实际 AllocCPUS、RAM 和峰值记录进行装箱。所有子任务并发的 CPU 和内存之和不得超过 allocation；仅节点标称有96核不代表本任务已获96核。

### 9.3 统一调度与资源规则

1. 使用一个 dispatcher 统一提交和登记本 `run_id` 的作业，Agent 提供任务 manifest，不各自无协调 sbatch。
2. 六个基础节点槽、两个弹性槽；排队作业先预留对应槽，已分配与准备启动的总需求不得超过八节点。不能把每个子 Agent 都当成各有八节点。
3. 此限制只覆盖本任务；同账号其他任务不被取消、重命名、限流或修改，也不为了抢占节点而干预其他成员。
4. 根据项目规则，c64 实际节点1–12、c96节点13–26按队列选择；其余96核debug仅用于能在30分钟内完成的探针。长门级、正式P&R和RCX使用c64/c96。
5. 任务名使用当前成员缩写，如 `yzl-bv1-*`；全部新数据进入当前成员获授权的独立 Issue/时间戳目录，禁止覆盖历史结果或其他成员活动目录。
6. 对实际需要的商业许可证使用全局令牌；不足时不占住节点空等。开源工具不凭空假设许可证瓶颈。
7. 提取、大包解压、归档、传输设置全局I/O限流，先以两路重I/O任务起步，按实测吞吐调整；原始数据尽量在节点本地scratch处理后汇回授权存储，scratch路径以集群规则为准。
8. 每个正式阶段预先记录合理walltime、恢复点和失败判定；不对长P&R套用debug30分钟上限，也不因运行较久随意取消。重试需区分工具错误、资源不足和真实实现失败，保留原输出。
9. 尚无可运行依赖或全部工作完成时释放节点。资源利用率、CPU-hours、峰值RAM、I/O和等待原因进入运行摘要。

本节按当前仓库 `docs/REMOTE_RULES.md` 制定。实施前再次核对规则及真实节点资源；本计划不修改集群配置，不假设有独占整机权限。

## 10 验证矩阵和停止扩展条件

| 维度 | 必需检查 |
| --- | --- |
| 数学 | 原四profile的完整整数输出、中间阶段和state；完整归约/RNE/guard/scale不变 |
| 协议 | quiet/背压、最后一拍保持、中途abort、迟到响应、owner切换、终止epoch、root生效但ACK延迟、commit后不可取消 |
| 存储 | 真实延迟/冲突/RMW/响应保持/canary/生命周期；scratch不与持久state混算 |
| 新层工具 | M10→via10→M11→via11→M12可读写、可路由、可提取、可检查；非法via/spacing/断线负例被拒 |
| 物理 | 全部端点setup/hold、actual≤limit的严格cap/slew、DRC/连通/PG/RC覆盖；没有限值的类别明确列出 |
| 视图与寄生 | RTL/网表/Lib/LEF/ODB/SPEF同源；全拼接与分层边界小例子一致；M10–M11耦合不漏计/双计 |
| 固定底座 | 不同产品的固定单元和M1–M10几何一致；定制变化仅在M11/M12、via10/11 |
| 公平成本 | 相同功能、算术、容量、端口和比较预算；全部landing、via、buffer、PG/CTS、空闲资源计价 |

固定性使用规范化清单比较：cell master/坐标/朝向，原生普通导体和PG/CTS形状、via1–via9、M10 landing，以及固定连通分量。父层网络别名变化不能误报为几何变化；只比较整个ODB文件哈希也不能替代冻结审计。

出现以下情况，停止扩展当前候选并报告原因：新增层模型无法被提取/检查工具覆盖；必须修改固定 M10 或新增有源资源才能连通；真实存储或事务壳超出已锁预算；数值/提交不一致；完整时序或严格电气不通过。可保留通过验收的边缘pin方案发布首版，内部窗口失败另记，不无限追加候选或放宽验收。

## 11 交付目录和来源

审查后，正式任务在仓库查重并关联真实 Issue；源代码、配置和报告进入项目正式目录，辅助材料进入当前成员 work 目录。此审查稿单独保存在本地，不混入当前 #116 尚未提交的文件。

| 交付物 | 建议内容 |
| --- | --- |
| v1规格 | Block资源、数值模式、四profile范围、端口、外存义务、时钟/面积/修复预算 |
| 技术overlay | 十二层tech/track/via/RC/DRC/映射及参数与来源表，原生平台保持只读 |
| 宏与接口 | RTL/网表、Lib/LEF、pin/access/OBS、M10 landing、时钟/供电与存储视图 |
| 物理证据 | DEF/ODB/SPEF索引，时序/电气/DRC/PG/连通、精确网表门级与负例 |
| 冻结清单 | 所有有源资源、位置朝向、固定几何、连通分量、允许定制层/via |
| 并行执行 | DAG、task manifest、allocation/jobID、线程/RAM、依赖/失败/重试、源码输入输出SHA |
| 结果与复现 | Block参数库、A/C*完整层次成本、两产品互联/敏感性、命令和输入输出位置 |

大型数据库和原始trace保留获授权存储，仓库只收必要代码、配置、摘要、精选证据和精确索引。实现提交经项目要求的PR审查，不自行合并或宣告制造验收。

研究背景固定来源：[PR118 教程](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/f15f0a02cb171f7d5f569032e0df9c6493b8769e/docs/research-handbook/README.md)、[PR113 电路候选](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/c03ba985e516b006ec2f936175b8588fc0de48af/docs/BLOCK_CIRCUIT_CANDIDATE_V2.md)、[PR111 研究物理](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/111)、[PR120 pin候选](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/120)。这些来源的研究范围与本计划的新增十二层实现分别登记。

## 12 当前审查要点

- [ ] M1–M10全部用于预制，M11/M12与via10/11后定制；不再套用原生高层让给定制的方案。
- [ ] 第一版采用C8共享Tile、同一份S16K与真实T6K，保留四profile单owner和已有数值合同。
- [ ] 自建两层按研究技术overlay实现，补齐几何/RC/验证能力，参数和外推假设先锁定。
- [ ] 采用边缘与局部内部窗口的有限对照，先验证接入再冻结具体XY。
- [ ] 本任务采用六节点基础、最多八节点，统一dispatcher和节点内受控并行。
- [ ] 审查后开始实现；本轮只交付计划文件。
