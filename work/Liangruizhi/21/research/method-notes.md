# 首轮算子／Block边界实验：方法审查建议

2026-10-22。仅为可执行实验合同与一手方法调研；未修改项目仓库、GitHub或服务器，未运行正式实验。本轮范围为推理 prefill/decode；训练只列结构约束，不执行训练。

## 首先要分开的三个决定

1. 算子数学／执行调度：哪些中间结果整张物化、逐tile保留、重算或流式消费。
2. 物理候选边界：哪些算子／存储／原语归属于同一个Block，哪些通路预连线。
3. 资源与通信实现：多少MAC／向量归约资源、哪些SRAM银行及端口、FIFO／交叉开关／链路、位置与技术参数。

软件kernel fusion改变1，不能直接证明2。跨Block的FIFO／流式边界也可能避免DRAM物化；同一Block内部也可能因容量、端口或调度而需要spill。未知的物理距离、buffer、mux、clock/PG、RC、能量参数不能默认为零。

## 推荐第一轮可证伪问题

问题不是“哪个Block划分最优”，而是：在声明的固定资源、精度、tile和输入场景下，哪些分区仍可执行；不同方案在边界通信、片上驻留与物化流量之间形成什么不可支配集合；结论是否因执行策略或服务窗口假设改变。

对小图枚举候选分区P，独立枚举执行策略S。对比P时固定S的数学、tile、重算次数、权重/KV驻留、MAC总吞吐及辅助算子资源；对比S时固定P。若只枚举连通／相邻算子簇或手工候选，明确搜索范围，不称全局最优。

每个配置至少记录：

- 总MAC数量与声明的MAC吞吐预算；exp/reduction/非线性操作数量及未校准延迟。
- HBM读写bytes，按输入、输出、权重、KV及中间物化分类。
- 跨Block bytes、Block内bytes、每条逻辑边和每侧端口的tile burst bytes；块内流量不是免费资源。
- 全局及逐Block／bank的max-live bytes；持久状态、权重tile、累加器、残差、分叉等待、双缓冲/FIFO分别列出。
- 数值误差、硬约束失败原因、采用的参数假设、未建模项。

SRAM总量相等不足以证明公平：bank布局、端口数、共享方式和读写带宽也须相同，或作为明确的独立设计轴。并发分支不得各自获得完整总MAC吞吐。新增FIFO／双缓冲占用同一总存储预算；不能“融合后免费多出一个缓冲”。

未建cycle调度时，可以给必要下界 max(MAC/Pmac, HBM_bytes/Bhbm, link_bytes/Blink)，但这不是可实现延迟。服务窗口未定义时只报burst字节，不报真实峰值GB/s；也不能从bytes直接推pin数。

## 三组可在本机NumPy验证的微实验

### A. FFN／SwiGLU：分区与物化分离

比较整张中间物化、按中间维tile累加输出；两种调度均允许跨Block声明FIFO streaming。FFN计算为 Y=SiLU(X W1) W2；SwiGLU为 Y=(SiLU(X Wg) * (X Wu)) Wd。对每个隐藏维tile计算贡献后累加Y，与独立整矩阵表达式对照。

建议微规模：M=1/8/32，D=16/32，F=32/64/96，隐藏tile=1/4/8/16，三个固定seed。它们是合成代数案例，不对应真实模型质量或宏性能。

必须保留Xtile、Y累加器及实际同时驻留的Wg/Wu/Wd和激活tile；中间结果移出SRAM会产生显式HBM事件。小M/decode可能主要搬权重，大M/prefill可能充分复用权重；每次重读权重都记账。输入/输出共用存储仅在依赖与原值已无消费者时允许。

主反例：若“分块+stream”和“合块+stream”HBM流量相同，则物化减少来自调度，不是物理融合的独占收益。另取分叉同时驻留超过bank容量、串行执行可放下的例子，反驳“大Block／并发永远更好”。

### B. Attention：materialization／online streaming，prefill／decode分开

以QK^T、稳定softmax、PV为数学参考；实现逐key tile更新running max、normalizer和未归一化output的online softmax。prefill用q_len=kv_len=16/32/64并加因果mask；decode用q_len=1、kv_len=16/64/256。head_dim=8/16，query tile=1/4/8，key tile=1/4/16。先单head，不能据此声称已覆盖GQA/MQA。

显式记录Q tile、K/V tile、score/probability tile（若复用需声明）、running max/sum、output累加器和KV持久状态。attention核心若不含QKV投影，应明确这些投影的权重与成本在范围外，不称完整Transformer层。完整KV可在外存，不等于可从容量与交通账本消失；每次扫描、追加和读写都记录。

主反例：M=1时score矩阵只是1×L，不能套用prefill的L×L物化收益；KV读取仍随上下文增长。另用极端logits、非整除tile、长短混合长度、全mask行（明确拒绝或定义行为），检验稳定性与尾tile。无需把FlashAttention GPU加速比移植为本项目速度。

### C. MoE：先做动态通信压力场景，可选小型前向正确性

固定E=4、top-k=2、总专家权重、总MAC/SRAM/总通信预算，比较均衡路由与全token偏向同一专家对。记录dispatch/combine、gate/index元数据、重复token副本、每expert峰值驻留、最大负载与外部权重重读。相同总bytes不代表相同热点压力。

若运行NumPy前向，以逐token逐expert参考对照分组执行后的加权combine，保留原token顺序和每条assignment。容量不够应排队或记失败；不能为了满足资源静默丢token。路由是输入场景，不得改变路由后再声称同一工作负载。首轮不必实现完整MoE模型或训练。

## 裕量与Pareto

首轮使用多目标向量而非任意加权评分：HBM bytes、跨Block bytes、max-live、最大侧负载、计算/重算量。报告非支配候选及硬约束失败。

headroom_S=1-max_live/S只在S及其bank/端口模型明确后计算；接口需给定服务窗口才能得到所需带宽。0/10/20%预留可以作为敏感性假设扫描，不能称工艺保证或无成本加带宽。对形状、prefill/decode比例、长上下文和MoE热点记录最差可行性；未优化过的形状作为独立保留场景，不能事后调参数后仍叫盲测。

没有过程／能量表时保留action counts。若以后 E=sum_i count_i * energy_i，energy_i需要技术或测量来源；先给break-even参数区间，不凭空指定线能量和SRAM访问能量后选“最佳架构”。

## 至少六个关键负例

1. 同图同schedule，仅改Block标签，却自动减少HBM物化：应被公平性断言拒绝。
2. 固定总MAC预算，并行两分支各拿总吞吐：资源账本应拒绝。
3. 忘记W tile、KV、Y累加或双缓冲而使容量刚好通过：显式事件的max-live核对应抓到。
4. 同总流量的均衡／热点MoE被赋予相同所有端口压力：每侧／每expert统计应不同。
5. streaming attention变更tile次序、尾tile、mask或极端logits导致结果错／NaN：独立稳定整矩阵参考应拒绝。
6. 减少物化靠重算却不计额外MAC／权重读，或FP16存储被宣传为已验证FP16算术：账本／证据状态应拒绝。

训练只保留约束登记：反向/转置路径、dX/dW累加与规约、activation保存或checkpoint重算、参数/梯度/优化器状态及必要权重版本。未执行训练，不宣称训练功能、训练占用或吞吐已经验证。

## 一手方法文献与适用边界

| 方法 | 一手来源 | 对本实验的启发与限制 |
|---|---|---|
| Timeloop | https://accelergy.mit.edu/timeloop.pdf | 将workload、architecture、mapping分开，并核对各级容量/带宽；好mapping是公平比较的前提。不能把不同mapping结果当纯分区收益。 |
| Accelergy | https://accelergy.mit.edu/paper.pdf | action counts与技术相关energy reference table分开；未取得有效组件表时只保留计数，不报已校准能量。 |
| ZigZag | https://arxiv.org/abs/2007.11360 | 内存层次、各operand不均匀映射、实际/所需带宽及单双端口/双缓冲影响；总SRAM bytes相同不代表实现条件相同。 |
| MAESTRO | https://arxiv.org/abs/1805.02566 | 用数据映射、复用、occupancy理解dataflow与硬件能力；不是从算子图自动推导物理宏边界的证明。 |
| DeFiNES | https://arxiv.org/abs/2212.05344 | 深度优先／跨层调度应同时纳入权重、激活及每级数据移动，不能只看DRAM或激活容量。 |
| LoopTree | https://arxiv.org/abs/2409.13625 | 联合探索tiling、retention、recomputation，比较buffer、流量、计算及代价；最直接的fusion方法基线入口。 |
| FlashAttention | https://arxiv.org/abs/2205.14135 | 精确attention的IO-aware tiling和online normalization；属于算法／调度证据，不是物理Block合并的独占证据。其backward节说明重算与保存统计的取舍，本轮不执行backward。 |
| Megatron-LM | https://arxiv.org/abs/1909.08053 ; https://research.nvidia.com/labs/adlr/MegatronLM/ | MLP首GEMM列切、第二GEMM行切可使局部非线性后无需中间collective，但输出仍需规约。这是逻辑sharding/通信匹配，不证明应制成同一宏。 |
| PipeDream | https://www.microsoft.com/en-us/research/uploads/prod/2019/08/pipedream.pdf | 划分需算参数、激活、拓扑与带宽，训练还存在双向数据与版本状态。本轮只能借鉴约束，不能挪用其训练吞吐结论。 |
| GShard | https://arxiv.org/abs/2006.16668 | MoE gate、expert capacity、dispatch/combine及AllToAll有独立成本和语义。其overflow策略会改变哪些token获专家计算，不能作为本实验免费省通信手段。 |

调研核对了论文摘要及相应方法正文的相关段落；未安装或运行这些框架，未复现其测量。以上首轮合同是据这些方法提出的研究建议，不是文献已经证明本项目Block划分有收益。
