# Issue64：多模型划分方案v2与决策实验

2026-10-24，Asia/Shanghai；负责人Liangruizhi；[Issue64](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/64)/[PR65](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/65)。新工作树D:/Projects/LLMHardwareDesign-blockv2，task/64-block-v2，基于PR62@30fcd63。其他成员Issue32/55/63范围已核，不接管其GPU/物理/通信适配器。

本轮任务不是再扩模型，而是综合既有结果并验证真正改变边界的分叉。[具体方案v2](../BLOCK_PARTITION_V2.md)逐Block给计算/状态/接口/预连线，并分开语义义务、能力候选和物理归属。旧v1三处正文混淆已修正：完整K不一律INT32、PV并非一律I64、Gemma文本已接入。不同实验合同不拼成统一模型排名，旧FP证据/失败保持条件。

## 1. 来源与执行

现有CPU服务器c96/node13，无GPU；新目录/public/home/yuzelu/RuizhiLiang/issue64-block-v2-20261024，所有数值/服务均Slurm lrz-*，外部权重/原张量只读。不触其他成员作业，启动前资源核实：实际540675563520B内存，当时available约437GB，存储可用约12TB；这些是准备时快照，不是性能测量条件。每数值作业申请2CPU，OMP/MKL/OpenBLAS各1线程，两轮独立目录并行，不覆盖既有phase/output。

主测输入直接复用Issue61固定captured/encoded及其模型revision/source/env/SHA；不新下载/完整模型加载。Llama所需capture02和numeric04在原manifest逐文件SHA通过后，以input-source01.zip实际上传本人新服务器目录llama/；含9.15MB浮点捕获与13.80MB编码，不含完整模型权重。此处让这些具体旧输入可在服务器复用，不等于其他旧大归档/所有GPU原始数据共享问题都已解除。

A源码46c0b46e46f786c785489ce8b316bc0a72fd3d28；B frozen源码commit3a6416dffe932ea47e2e0141c7ff1006e7769b7e，attention源来自de63c7a，PV helper仍是Issue61/bounds.py原SHA。源桥接FP32、离线scale/LUT编译、整数候选、误差参考和服务模型分别记录。运行版本Python3.12.7/NumPy2.2.6；本机接收NumPy2.5.4，不因此称另一个模型推理参考。

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

成本不是“每row1B就免费”：这是一组16输出tile的delta，可能使下一Linear形成K16单位，需ALIGN_REDUCE或转回K128再量化。后继完整N、残差、norm和新误差尚未验证。旧诊断Llama heldout prefill行delta[-3,0]，32行搜索495次、7920个RNE/比较项；最低完整acc/unit/scale/output行buffer约192B。本轮64B外header+32B坐标+16B指数+16B Y8的协议，单row显式delta使包128B→192B，Y16也为192B；只有已预留字段才能仍为128B。坐标或scale已驻留的另一协议可能使Y8/Y16均128B，此结论不外推。Y16进入W8矩阵至少3个S8基础积和移位/对齐，1/3计数仅基础算术下界，不等于消费者周期。

90048/90049均COMPLETED0:0，9秒/8秒。metrics/summary/outputs.npz逐字节相等。独立接收不导入生产实现，逐点重放两轮各410112码、4272row delta、1092032个Fraction候选项，1080指标及156汇总组；Llama12 case的acc/unit/base/参考与原NPZ核对，改实际码并重写SHA仍被数值oracle拒绝。上游三主测partial不在本接收重复下载，绑定原完整Issue61独立核对及输入SHA，不声称重新证明其全部源acc。

## 3. B：整数概率闭包与条件PV32

同14个真实GQA层/长度组，KV8/16×2个LUT，共56条件。Q8动态行scale、KV原校准固定逐头；没有从评价重新拟合。运行整数链：3段S8 limb QK16/I32，scaling U32Q30离线编译→受检S64乘/重定标S32Q12；实际mask/max；exp[-16,0]最近偶数索引查表U32Q30；U64 sum、(exp<<15)/sum的U64 RNE及SatP15；Psum守卫；固定Vscale下的3/9段S8 PV32。所有QK/PV全值比独立I64，概率有Fraction见证。完整模型norm/RoPE/state以及源FP32→S32Q20尚非整数实现；离线math.exp生成表和FP64误差参考均在候选热路径外。

两表分别step1/128、1/256，2049/4097项，8196/16388B。相对同编码Q/K/V、FP64softmax再P15的输出，最坏新增relativeRMSE分别约0.0747%/0.0436%；不是原生模型总误差下降。KV8 Qwen2.5仍约12.50%，KV16约0.58%，换整数softmax不解决KV精度问题，不能作模型品牌难度排名。

head256 scaling是2幂可合并RNE shift；head128需要检查过的S64乘法或signed32的5个radix128 digit×常量4非零digit（20个S8积）及宽合并候选。U64除法候选64步恢复除法，不是现有S8阵列自动支持。ROM单读，不能8lane免费8查表；8196B超V8KiB4B，16388B超16KiB4B，A20KiB候选可容纳。省端点常量是需另冻结的优化，未执行。recompute-exp三遍score与物化exp是两份替代成本，不相加或漏计。

90050/90051均COMPLETED0:0，68秒，各56条件全执行/范围通过；每轮7106560 QK32及1474560 PV32值全比I64，27850概率Fraction见证。计数包含不同profile/被mask矩形的重复计算，不是优化算子MAC下界。整数Psum在实际候选下成立，比原FP64 exp/div假设更进一步，但不覆盖变页Vscale/online未归一化O/任意长度。90055独立接收实际COMPLETED0:0/14秒，不导入生产attention/bounds函数：先验证两轮所有artifact SHA和字节相同，再独立重算一整轮7106560个QK/score/exp/P15、1474560个PV、34990个score Fraction见证、392指标；Decimal50重建6146个LUT项无差。概率producer的27850 Fraction见证与这里score见证不是同一计数。第二轮由全文件一致绑定，不称接收再次逐点重算。内存中改P码负例被拒绝，不冒充实际文件改码再重写SHA负例。

精选包携带两份实际NPZ（Q25 T128 KV16/Gemma local T4096 KV16）及两LUT，本机独立重放381440个QK/score/exp/P15和61440个PV、1987 Fraction、14指标；完整56 NPZ留在服务器full包。完整与精选接收边界分别记在work64回执。

## 4. C：完整attention子图的条件服务对照

正式源码24336c45e2e1622fd86de29a9a788a9e032d42d4，执行前后均检查service.py和rq_ports/model.py SHA。90056/90057均COMPLETED0:0，186/185秒；每轮576 schedules/96优化配对，6科学文件字节一致。四GQA组：Gemma local0/global5为2Q×d256、Q25为8Q×d128、Q35为4Q×d256；T128/1024、q1/4、KV8/16、exp II1/8/32，三组织×fifo/critical。

从已发布Q/K/V开始到输出/consumer；投影、source量化、KV追加、生产者布局形成、R/整图不在内。两侧同16×16 S8阵列、8lane、一个wide服务、M32KiB、A32KiB、A20KiB单读ROM、S8×32KiB1RW、128bit bus、2KiB FIFO/credit。score S32Q12、exp U32Q30、sum U64、P15；PV使用portable I64及条件O16输出，不能称B的PV32/原生FP质量验收。

消费端K/V transpose与digit pack实际入图，保守scalar byte-enable模型KV8每元素3周期、KV16为10周期，消耗同AC1RW/vector/control；完整GQA各头按声明顺序执行，KV按头重读，两侧一致。head128按20个S8基础积/宽合并候选计scale；两遍EXP前的宽差、clamp/index均收费，U64 div每元素64周期候选，exp II仅未校准敏感性。没有免费宽乘/除法/多读ROM或第二阵列。

| 对照 | 实际结果 | 可以得出的结论 |
| --- | --- | --- |
| split vs colocated_control | 96/96最佳策略周期、流量与工作完全相同 | 只改同宏标签不能制造收益 |
| split vs colocated_stream | 完成周期减少0.0833343%–0.1674616%，均值0.1103583% | 本协议只省内部M↔A header；payload、RAM、同bus/FIFO/credit保留，未校准条件模型不决定物理边界 |
| 最大配对Q25 T1024/q1/KV8/expII1 | 8560768→8546432模型周期，wire少229376B | 只是声明图的完成时间，不能乘层数换算芯片加速 |
| 最小配对Q35 T128/q4/KV16/expII32 | 3379160→3376344，wire少49152B | 量化位宽/pack/SFU会改变内部与通信占比，不能只用少字节选同宏 |

每组织各选已声明fifo/critical较优，不是全局最优调度。C中Gemma local/global的同shape图相同，因T≤1024未越窗口，不能称本服务测出窗口周期收益。共同的保守pack/U64 div/逐头重读可能掩盖其他实现的通信收益；未对这些假设做RTL标定或优化下界，不能推广“合宏都无用”。本轮使M+A从直觉必合改为保留产品可配连接，下一判别优先布局/SFU/真实端口资格。

独立work64/audit_service.py不导入producer或scheduler，核两轮SHA/6文件字节一致，重构96个策略配对，检查3实际轨迹的依赖、资源互斥、端口范围、packet/stream与有限credit、全GQA工作量；4个实际轨迹变异负例和3个手写负例均拒绝。轨迹无policy字段，以独立cycles/busy/traffic/operations匹配同配置统计，存在多解时保留，不认证调度算法本身。正式回执service-independent.json PASS。首版接收误假设policy字段而KeyError，已记录并修正，无生产结果改动。

## 5. 数据、失败、复现与交付

[统一索引](../../project/experiments/block_decisions/results/issue-64/index.json)记录全部source commit、输入索引、Slurm和成果。完整full-results01.zip保存在本人服务器目录，240391397B/178成员，SHA-256 3c19c87eed6191f957e46ef58085dd47f9bea5dbffbda91472e1f9407dd9b71c；不含完整权重，也不重复所有Issue61原始捕获。仓库精选包10079937B/57成员，SHA-256 2feae3548b4343a92975480778686e6fc14909c017d260e5419410d0994a86ab，含完整A/C科学结果、B全部指标/仅2实际NPZ和源快照。接收器核外SHA、56索引成员和6源文件对应原冻结Git blob，PASS；它不代替数值接收。

90052/53/54启动器引用错误，在Python前FAILED127:0，日志和失败保留；shlex.quote修复，同一不可变源/输入以90055/56/57完成。90058归档COMPLETED0:0/7秒。服务草稿score/exp格式在任何服务器运行前已改正，旧commit保留；没有用未运行草稿的数据。work64/failures.json区分启动失败、接收器元数据错误与源草稿修正。

结构/业务检查、独立接收实际命令和范围见[运行说明](../../project/experiments/block_decisions/README.md)、work64/validation.json、[交接](../handoffs/2026-10-24-issue-64-block-v2.md)。旧FP/BF16证据和原误差失败不改写成INT8；本轮没有GPU测时、完整整数模型质量或目标RTL/PPA。

PR65基于未合并PR62，交付待审查/合并，Issue in_review而非done；审查人待指定。登记management-hub PR5 pending；缺board.json/Projects能力，看板unverified/同步pending，管理员待指定。具体最终源码commit以PR head/交接回执为准，执行源固定在binding中，不因文档提交改写历史运行版本。

剩余只保留：①16输出tile动态scale/ACT16的真实后继消费者；②Qwen3.5连续R整数合同及同库存归属；③校准布局/SFU/真实端点后的物理配对；④方案冻结后的Phi独立验证。详见v2第8节，不盲扩模型矩阵、不重复Issue55/63。未获得目标RTL/时序/PPA与同资源整图证据时，不宣称最终最优方案或端到端收益。
