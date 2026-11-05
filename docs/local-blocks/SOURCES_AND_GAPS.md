# 来源、数值合同及接收边界

本目录服务于[局部可定制 Block 提案](../LOCAL_BLOCK_DESIGN.md)。图中每一步都指定功能归属；“有对应原语”和“该模型已经逐位/质量/物理验收”是不同事实。下表把差异集中列清，避免在图里用一个没有具体原因的“待补齐”框代替判断。

## 1. 固定输入及来源优先级

| 输入 | 固定版本与具体用途 | 证据限制 |
| --- | --- | --- |
| 用户在本次讨论确认的宗旨 | Block 内外都可后定制；3～4 宏局部公约数；各 S 分管所属 Block；母控程序不预知候选模型目录 | 这是设计约束，不是已有 RTL/物理结果 |
| [精简算子图](../model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md) | 基线 `4b1df2c7`，Git blob `b2822ee854c12ef2fa94722f32fceb51afcb2573`；§7 Qwen、§8 Granite、§9 Falcon、§10 缓存/状态 | 单层 FP32 prefill 语义/导出核对，不是当前七宏的整数质量；不自动包含非零旧状态 decode 的验证 |
| [实际宏合同](../BLOCK_V2.md) | 同基线，blob `bb023563c6372438cc8bb912b7e52edb7fe7c0cc` | 只能按其端口、数值、上下文、命令和工作域调用 |
| [叶宏结果](../BLOCK_V2_RESULTS.md) | 同基线，blob `46154899f368e161797ce0690696a0a0167d2057` | M/N/E/G/S/T 六块通过；R 未完成；不含本 PR 新 Block、私有 S32KiB 或 M11/M12 系统资格 |
| [R 研究源码](../../project/rtl/block_library_v1/block_v1_r.sv) | 同基线，blob `6483793b0a183906e7410a0fe3b1ae0eabb1b109` | 只用来核对原语/格式/提交行为，不能引用为已验收 R |
| [模型实验分析](../model-analysis/MODEL_EXPERIMENT_ANALYSIS.md) | 同基线；回溯模型/数值批次 | 原整数候选与当前宏合同可能不同，不能串接两个批次的局部成功当整链通过 |
| [PR152 图控制规格](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/55243d2c58626547d0d452bfb25fa79b7499b486/docs/H1_GRAPH_CONTROL_SPEC.md) | 本次读回 PR152 head `55243d2c58626547d0d452bfb25fa79b7499b486`，图合同 blob `6dc9c0f2543017c83e119cc74766d69bc9242a52` | 有界 A/F 图和静态服务/容量分析；不能代表三模型、R/MoE 或通用图控制已通过 |
| [PR152 互联边界](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/55243d2c58626547d0d452bfb25fa79b7499b486/docs/COARSE_BLOCK_INTERCONNECT_BOUNDARY_PLAN.md) | 同 head，blob `6bfa9b5d1cad8b6865960c32478fe8ac184db78c` | 旧主候选岛内固定、固定母控网、跨岛后制；本文将局部主要数据连接也纳入后制候选，不回写其历史结果 |
| [Falcon 整数 R 分支合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/88e9c4b2c3bb1b93b7155ba87ad11853e6c15512/project/experiments/closure/FALCON_CLOSURE.md) / [整数闭包记录](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/88e9c4b2c3bb1b93b7155ba87ad11853e6c15512/docs/experiments/issue-72-numeric-closure.md) | 历史固定 commit `88e9c4b2c3bb1b93b7155ba87ad11853e6c15512` | I32Q12 数据、I32Q20 dt、U32Q31 decay 等整数候选，不能移植成当前 G/N 的 S16 合同而声称不变 |

PR152 本次读回为 open、未合并，其最新说明已有真实 G1 A→F→F 切片、存储 ACK/DMA/母顺序器进展；不能沿用旧时点笼统说“该 PR 完全没有 RTL”。但这份进展也不证明本文全模型或新局部可定制边界。相关工作继续由原任务负责，本 PR 只引用其固定证据。

完整本地输入 SHA-256、Git blob、来源 URL 与图文件摘要见 [manifest.json](manifest.json)。图源与渲染工具版本也在该文件；历史远程材料仍用固定 commit 链接，不复制为本轮新实现。

## 2. 三个模型的标识

| 图谱名称 | 本次采用的关键参数 | 解释 |
| --- | --- | --- |
| Qwen3.5-4B | H2560、I9216、32层，3GDN/1Attention；全局 Q16/KV4/D256；GDN key16/value32/D128、conv4 | 使用精简图第7节的语义和层序列 |
| Falcon-H1-3B | H2560、I6144、32层；Attention Q10/KV2/D128；SSM head32、channel128、state256 | 使用第9节；注意力与 SSM 是同层两支，非交替层 |
| Granite 图谱（原文标题 Granite-3.3B） | H1536、32层、Q24/KV8/D64、40专家 top8、每专家 I512 | 项目不同历史材料出现 Granite-3.3B、Granite3.1-3B-A800M 等称呼；本提案只绑定该图谱配置，不承诺这些发布权重互相等价 |

流程图重点为一层/一个 token 的受限分块执行。Embedding、末端 LM head、完整生成循环、整段 KV、host/MEM/PHY 及端到端质量未在图中实现。多 token prefill 要有新调度/存储轨迹；不能凭单 token 示意声称全上下文吞吐。

## 3. 现有宏能直接做什么，哪些必须显式处理

| 项目 | 当前合同的确定事实 | 本提案的具体处理与资格 |
| --- | --- | --- |
| M 的矩阵格式 | 两侧 S8/S16；S16 精确数位分解，双 S16 9 次发射；K≤32/命令，S64 完整累加，显式最终 RNE；一份完整结果上下文 | INT8 权重投影可使用 M；QK/PV 可用 S16 路径。组尺度/对齐/溢出须编译绑定，不能把“INT8 GEMM”当覆盖全部矩阵格式。不同用途串行或用不同 P 实例 |
| N 的 Softmax/Norm | S16 输入；单统计上下文，长度1～65535；Softmax 输出非负 S16 Q1.14；gamma Q5.10；S 外部回放 | QK scores 转成 N 的 Q5.10；Norm 按原始平方单位配置 epsilon，RMS0 的 gamma=1+weight 在参数生成时显式形成；有效因果前缀可用长度控制，不虚构 mask 指令 |
| G 的函数域 | 两路 S16 Q5.10；SiLU/Sigmoid/GELU/Softplus 有固定域/尾部行为；Sigmoid Q1.14，其余 Q5.10；没有通用 EXP | 门乘需要按各输出尺度配置 E；函数域及饱和事件留痕。G 不能单独完成 `exp(dt·A)`；N 的内部 Softmax EXP 也不是通用系数 EXP 接口 |
| E 与 R 的格式 | E 基本算术八路 S16；op13 可把四个 S32 按 RNE 右移转 S16；不含通用 S32/S64 算术。R 读出 S32，Q/K/B/C 为 S16 Q1.14，β/decay 为 UQ1.31 | R 输出→E op13→N/G 的转换路径存在原语。具体移位/共同单位必须由选定整数合同给出；不能不经转换就把 S32 裸接 N。β Q1.14 到 UQ1.31 的移17位/打包由新增预制适配负责，仍未实现验收 |
| Qwen 的系数生成 | G 没有任意域 EXP；A_log/权重固定但 a 随 token 变化 | 候选由**运行时按 a 索引**模型参数表，表由模型确定后生成/加载，MEM 保存、C0.S 缓存，局控做有界索引/请求。不是把所有 decay 离线算成常量，也不是按模型 ID 选程序。域、步长、索引舍入、误差、表容量与加载协议必须单独冻结/实测 |
| Falcon dt/decay 表 | 历史整数候选按头有 dt/alpha 联合表，输入域[-32,32]、步长1/256，约4MiB；外部浮点仅为参考 | 可借鉴“表是参数数据”的方法；当前 S16 输入、输出尺度及 clip 规则不同，不能直接引用原误差/质量。系数服务、真实表和端点是新增固定资源需求，不是免费的 C 内模块 |
| Falcon 注入次序 | 历史候选 `RNE(dt·B)→×X`，当前 R SSM 接口对 inject 再乘 B（若给 dtX 则另一舍入次序） | **当前原样串接不能逐位等价。** 选项为 M/外部真实格式路径先形成原顺序的注入，或修改 R 合同并重验数值/物理；本 PR 不替实现任务选定两者，不把分配图当通过 |
| Falcon 卷积/系数 | 模型 conv4 带 bias，B/C 历史候选为32位，而 R 系数为 S16Q14，G/N 也是16位 | bias 在声明尺度下显式加入，B/C 重新量化或扩宽 R 需落实。现有原语名“conv/SSM”不证明这些差异已消失；R 本来就未合格 |
| Qwen/Falcon 归一化顺序 | Qwen GDN 为每 value head128 Norm 后门乘；Falcon 为门乘后跨4096 Norm | 本图分别采用 C→U→C 和 C门乘→U→P；不在 R 内固化某一层顺序 |
| Granite TopK/分派 | N 支持最多40选8，但输出 ID，不自动输出选中 logits/搬运专家 | U.S 保留 logits，局控 gather 分数→N Softmax8；母控/参数地址服务处理 ID。必须有真实动态任务/权重访问，不能在测试里固定八专家 |
| Granite 加权归并 | M 能 S16×S16→S64，E 不能通用宽归并；历史 MoE 专家返回可能 S32 | 本图明确选择**统一尺度 S16 专家返回**的候选合同，M 归并后一次 RNE。坚持历史 S32 返回时该路径不适用，必须补宽格式能力并重新核算，不声称质量等价 |
| S/T | 当前 S16KiB 四 bank 标准单元、端口/feeder 有冲突；T6KiB 单批单读游标 | 新 P.S32KiB、私有化接口、RX/本地调度都需重验；T 不能充当任意缓存/fork 队列。端点 holding 不占用图中已满的 payload 空间 |
| 状态发布 | R active/shadow 是局部状态；COMMIT 清 output_valid | 先读出、后本地 commit；新分片存 private next，母控在全部消费者成功后发布 next 根。全局版本/回滚/MEM 仍是新增服务，不能从单 R 的 commit 推导 |

上表中明确“不适用/不能等价”的项是合同判断；明确“候选、未实现”的项是本轮设计边界，不能改写成未知的“精度可能不够”。若决定继续使用当前所有固定格式，应先给出**一个新的、完整的整数模型合同**并测真实输入/非零状态；不能同时要求保持历史宽整数模型逐位结果，又删掉其必需位宽。

## 4. 每项有状态逻辑拟放在哪里

| 有状态内容 | 物理责任方 | 生命周期/额外成本 |
| --- | --- | --- |
| 程序 PC、循环、粗任务队列、资源记分牌、全局版本和状态根 | 预制 mother/global controller 及其程序/元数据存储 | 程序装载/金属存储、容量、超界拒绝和事件公平性需实现；不属于七宏之一 |
| 局部 PC、微任务队列、头/列/片段计数、宏 busy、S bank owner、回放进度 | 每个 Block 的预制 local controller | 单 Block 内管理端口，不与母控共同驱动宏命令端口 |
| 接收/发送 holding、有效字节/tail、credit、stored ACK、generation/epoch、错误锁存 | 预制 TX/RX/适配器，与其所属 Block 一起计面积 | 消息/数据/ACK 通路必须独立前进；不能假设 M11 上的导线保存状态 |
| 输入、中间量、原始/EXP 回放、残差/分支等待 | 本 Block 的私有 S | 地址表和峰值必须给出；远端仅通过本地 RX 写入 |
| 完整结果批次和消费位置 | J 内 T，或显式另列的交接实例 | 单游标/有限容量，释放后才复用，不假设每个 Block 都暗带 T |
| M 结果/操作数、N 统计、E/G pipeline、R active/shadow/history | 对应原生宏内部 | 按宏合同的有限上下文计数，不拿内部寄存器当未声明通用缓存 |
| 整层 KV/递推 old/next、专家权重/函数系数表 | 显式 MEM/参数服务与外部存储 | 控制器、地址/版本、延迟、带宽、PHY 和存储容量单列；外存不是零成本假设 |

## 5. 本文没有声称的结果

本轮没有编译三个完整整数模型、跑它们的真实 RTL/非零状态轨迹，也没有新 P&R/300MHz/M11/M12 验收。图的解析/渲染与文档来源校验只证明图可读且有源绑定。新的控制、S、端点、路线及数值合同，需要依次接受真实功能与物理证据，不能从六叶宏通过推导三系统通过。
