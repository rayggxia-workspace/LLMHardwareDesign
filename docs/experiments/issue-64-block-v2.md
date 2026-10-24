# Issue64：多模型划分方案v2与决策实验

2026-10-24，Asia/Shanghai；负责人Liangruizhi；[Issue64](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/64)/[PR65](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/65)。新工作树D:/Projects/LLMHardwareDesign-blockv2，task/64-block-v2，基于PR62@30fcd63。其他成员Issue32/55/63范围已核，不接管其GPU/物理/通信适配器。

本轮任务不是再扩模型，而是综合既有结果并验证真正改变边界的分叉。[具体方案v2](../BLOCK_PARTITION_V2.md)逐Block给计算/状态/接口/预连线，并分开语义义务、能力候选和物理归属。旧v1三处正文混淆已修正：完整K不一律INT32、PV并非一律I64、Gemma文本已接入。不同实验合同不拼成统一模型排名，旧FP证据/失败保持条件。

## 1. 来源与执行

现有CPU服务器c96/node13，无GPU；新目录/public/home/yuzelu/RuizhiLiang/issue64-block-v2-20261024，所有数值/服务均Slurm lrz-*，外部权重/原张量只读。不触其他成员作业，启动前资源核实：实际540675563520B内存，当时available约437GB，存储可用约12TB；这些是准备时快照，不是性能测量条件。每数值作业申请2CPU，OMP/MKL/OpenBLAS各1线程，两轮独立目录并行，不覆盖既有phase/output。

主测输入直接复用Issue61固定captured/encoded及其模型revision/source/env/SHA；不新下载/完整模型加载。Llama所需capture02和numeric04在原manifest逐文件SHA通过后，以input-source01.zip实际上传本人新服务器目录llama/；含9.15MB浮点捕获与13.80MB编码，不含完整模型权重。此处让这些具体旧输入可在服务器复用，不等于其他旧大归档/所有GPU原始数据共享问题都已解除。

A源码46c0b46e46f786c785489ce8b316bc0a72fd3d28；B frozen源码commit3a6416d（完整SHA见binding），attention源来自de63c7a，PV helper仍是Issue61/bounds.py原SHA。源桥接FP32、离线scale/LUT编译、整数候选、误差参考和服务模型分别记录。运行版本Python3.12.7/NumPy2.2.6；本机接收NumPy2.5.4，不因此称另一个模型推理参考。

## 2. A：固定输入和完整归约，只改变最终输出

冻结180编码case：Llama K128A配Wout/W128的12个既有诊断case；Gemma/Qwen2.5/Qwen3.5相同两个profile的168个q/o/down真实case。保留原A8/W8/单位/acc/bias和FP参考，全部K、前16输出。6个输出合同共1080条件，每轮410112个最终码逐点用独立Fraction RNE核。baseline Y8必须精确复制已存原输出。

6合同为Y8校准max、原2xcal、4xcal；同范围Y16、4xcal范围Y16；整数每row/tile delta Y8。所有候选事前冻结，评价FP参考只用于算误差，不选择delta/scale。旧评价数据已经观察，本轮是诊断，不叫新heldout或应用质量接受。Y16精确端点与Y8相同：step/256，code[-32768,32512]，避免把正端点32767偷增范围。动态delta从-16..16作最细无饱和整数比较；全零行固定delta0。

| 所选down动态A128/W128最坏误差 | 原Y8 | 同范围Y16 | 整数delta Y8 |
| --- | ---: | ---: | ---: |
| Llama layer0 | 5.3938% | 4.8113% | 4.9264% |
| Gemma layer0 | 3.8103% | 2.8839% | 3.1049% |
| Gemma layer5 | 3.9995% | 3.7700% | 3.8393% |
| Qwen2.5 layer0 | 3.3716% | 2.9560% | 3.0896% |
| Qwen3.5 layer3 | 4.8287% | 0.8400% | 2.4865% |

Qwen3.5明显为输出精度瓶颈；Llama原5.39%失败不改写，新合同在同旧样本改善不能算独立模型质量。Gemma q/o同范围Y16仍有21/5次饱和，扩大范围的Y16或动态delta才消除本批该饱和；扩大Y8会损分辨率，缩小Y8又可引入新饱和，全部失败保留。

成本不是“每row1B就免费”：这是一组16输出tile的delta，可能使下一Linear形成K16单位，需ALIGN_REDUCE或转回K128再量化。后继完整N、残差、norm和新误差尚未验证。旧诊断Llama heldout prefill行delta[-3,0]，32行搜索495次、7920个RNE/比较项；最低完整acc/unit/scale/output行buffer约192B。单row显式delta使线上包128B→192B，Y16也为192B；只有已有header预留字段才能仍为128B。Y16进入W8矩阵至少3个S8基础积和移位/对齐，1/3计数仅基础算术下界，不等于消费者周期。

90048/90049均COMPLETED0:0，9秒/8秒。metrics/summary/outputs.npz逐字节相等。独立接收不导入生产实现，逐点重放两轮各410112码、4272row delta、1092032个Fraction候选项，1080指标及156汇总组；Llama12 case的acc/unit/base/参考与原NPZ核对，改实际码并重写SHA仍被数值oracle拒绝。上游三主测partial不在本接收重复下载，绑定原完整Issue61独立核对及输入SHA，不声称重新证明其全部源acc。

## 3. B：整数概率闭包与条件PV32

同14个真实GQA层/长度组，KV8/16×2个LUT，共56条件。Q8动态行scale、KV原校准固定逐头；没有从评价重新拟合。运行整数链：3段S8 limb QK16/I32，scaling U32Q30离线编译→受检S64乘/重定标S32Q12；实际mask/max；exp[-16,0]最近偶数索引查表U32Q30；U64 sum、(exp<<15)/sum的U64 RNE及SatP15；Psum守卫；固定Vscale下的3/9段S8 PV32。所有QK/PV全值比独立I64，概率有Fraction见证。完整模型norm/RoPE/state以及源FP32→S32Q20尚非整数实现；离线math.exp生成表和FP64误差参考均在候选热路径外。

两表分别step1/128、1/256，2049/4097项，8196/16388B。相对同编码Q/K/V、FP64softmax再P15的输出，最坏新增relativeRMSE分别约0.0747%/0.0436%；不是原生模型总误差下降。KV8 Qwen2.5仍约12.50%，KV16约0.58%，换整数softmax不解决KV精度问题，不能作模型品牌难度排名。

head256 scaling是2幂可合并RNE shift；head128需要检查过的S64乘法或signed32的5个radix128 digit×常量4非零digit（20个S8积）及宽合并候选。U64除法候选64步恢复除法，不是现有S8阵列自动支持。ROM单读，不能8lane免费8查表；8196B超V8KiB4B，16388B超16KiB4B，A20KiB候选可容纳。省端点常量是需另冻结的优化，未执行。recompute-exp三遍score与物化exp是两份替代成本，不相加或漏计。

90050/90051均COMPLETED0:0，68秒，各56条件全执行/范围通过；每轮7106560 QK32及1474560 PV32值全比I64，27850概率Fraction见证。计数包含不同profile/被mask矩形的重复计算，不是优化算子MAC下界。整数Psum在实际候选下成立，比原FP64 exp/div假设更进一步，但不覆盖变页Vscale/online未归一化O/任意长度。正式独立接收结果与数据SHA稍后回填，不凭生成JSON即称接收完成。

## 4. C：完整attention子图的条件服务对照

待最终冻结源码/Slurm实际结果回填。该服务边界从已发布Q/K/V到整数输出/consumer；投影、source量化、KV追加、生产者布局形成、R/整图不在内。两侧同一M阵列、8lane、A32KiB/20KiB单口ROM、S8×32KiB1RW、同128bit bus/FIFO/credit，GQA每个共享头和所有PV limb必须实际入图。split与仅改物理标签colocated_control应完全零差；colocated_stream只在声明条件下省内部M↔A报文header，payload、内存读写、同bus/credit保留，不能称纯合宏已测物理收益。

实际K/V消费端pack/transpose成本、score spill两读、sum/div/Psum/全PV和consumer都必须记。exp II是未校准非零敏感性，同组织双方相同，策略各自优化但非全局最优。结果只能说明该明确服务/协议假设下的差异，不决定M+A物理最优，也不继承E2a百分比。

## 5. 交付与剩余问题

完整数据保存在本人授权服务器目录，仓库提交源码、配置、结构化指标/精选实际样本和SHA索引。正式接收、服务与归档完成后更新统一结果索引和恢复命令。PR65基于未合并PR62；待指定审查人，不自合并或done。登记management-hub PR5 pending；缺board.json/Projects能力，看板状态unverified/同步pending，管理员待指定。

下一项真正分叉是16输出tile动态scale跨入下一矩阵/残差/norm的代价；E3真实Qwen3.5连续状态的整数格式及公平归属仍未执行；物理只对剩余一对候选协调Issue55/63。Phi保持封存，冻结方案后独立验证。未获得目标RTL/时序/PPA与整图收益时，本版只交付有证据的方案和明确边界，不宣称问题全部解决。
