# 八样本粗粒度Block功能类与宏实例数量候选

任务Issue151 / PR152，负责人Melodydt。研究输入a37e37cad757af5bfc94ed65db3e2e728023c251，七宏来源707878621b2add4ed218b8c43df2e95c9a56e2ba。本轮给出可审查的功能类别、实例整数表与调度/容量前提；不修改RTL，不以该表宣称完整模型映射、数学最小性、吞吐最优或物理接收。

## 1. 数量口径与结论

对仓库八样本的十种decoder层型，采用五个完整子层功能类：A Attention、F Dense FFN、D GDN、H Falcon混合mixer、X MoE。普通Attention不需要G，Qwen3.5全局Attention需要输出Sigmoid门，故A有plain/gate两个资源变体，共六行配置。一个功能类可以多次调用，同一个物理Block也可时分执行多个已预制profile；层数、调用数与物理实例数分开。

主表按面积优先的串行参考方案计数：每Block最多一个前台任务，计算阶段复用现有宏；完整输入、残差、中间张量、权重、KV/state/history通过已正确实现的存储/搬运服务分片保存和回放。当前MEM/NUM/完整本地控制尚有缺口，所以这些是有条件的资源构造方案，不是只接好七类宏就已可跑完整模型。

S按16KiB普通/宽访问及单loader宏计，T按6KiB临时输出批次宏计；各1是本方案的分片工作区与提交接口选择，并非所有可能实现都必须各1。M/N/E/G/R各1表示串行复用的选择，也不证明不能用别的算术组合少配某类型。并行度没有被固定成最优值。

数量按宏顶层边界计：N内部group单元不是额外一个N，S内部storage和feeder不是两个S，R的active/shadow不是两个R，M内部多条乘法lane也不是多个M。一个逻辑局控可以含多个FSM/helper/顺序器；P2名为mother_rom的模块是当前小核顺序器，不凭名字等同于未来全芯片母控已经实现。

## 2. 每个Block的七宏数量

| 功能资源变体 | M | N | E | G | R | S | T | 叶宏总数 | 本地CTRL另计 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_plain 普通Attention | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 5 | 1 |
| A_gate 带输出门Attention | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 6 | 1 |
| F Dense FFN | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 6 | 1 |
| D GDN mixer | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 | 1 |
| H Falcon Attention+SSM mixer | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 | 1 |
| X 完整MoE子层 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 6 | 1 |

每个物理Block一个本地CTRL，芯片母控另计1个。NUM、格式/布局/pack、喂数选路、参数/程序ROM、输入/输出接收、状态根、共享MEM接口、clock/reset/PG及物理中继均不藏进上表的宏数。

六行只有三种七宏数量签名：M/N/E/S/T；加G；再加R。相同数量不代表完整硬件相同，A_gate/F/X仍需不同程序、缓冲和数值能力；只有其能力并集已真实预制和验收，才可共用同一物理包装。

## 3. 各类为什么这样配

### A_plain：普通Attention

- M1：顺序完成Q/K/V（或融合QKV）、QK、PV和输出投影。多个矩阵算子不机械对应多个M。M本身是多乘法lane的矩阵宏；切换用途前须保存仍需的结果。
- N1：顺序承担输入RMS/RMS0、源模型需要的Q/K逐头Norm、Softmax统计/EXP/概率回放及规定postNorm。N内部已有EXP/除法/开方能力，Softmax不需要另配G。每个组完成或保留其合法阶段锁，不能随意覆盖N上下文。
- E1：按已接收格式执行偏置/缩放、RoPE、mask/select及最终残差。源数据宽度/尺度不足以直接进入E时，仍须真实转换或宽算术路径。
- G0/R0：普通Attention没有G输出激活门，也不使用R递推状态。Gemma的GELU位于F，不能因此给Gemma的A额外配G；RoPE在E。
- S1/T1：工作tile、回放/搬运与分片输出。完整KV、score/EXP、残差不假设全驻留S。

A_plain覆盖Qwen2.5、Qwen3、Llama、Gemma local/global、Phi、Granite的Attention子层，静态展开178次逻辑调用。Qwen3的Q输出宽2048而H1024、Gemma Q宽2048而H2560、Phi部分RoPE/融合QKV等参数保持，不用改变宏数量掩盖几何差异。

### A_gate：带输出门Attention

在A_plain基础上增加G1，在PV后、输出投影前执行Qwen3.5的Sigmoid输出门乘。其余M/N/E/S/T仍可串行复用；覆盖Qwen3.5的8个global层。Falcon的Attention分支没有这一Qwen3.5输出门，完整Falcon计入H。

### F：Dense FFN

M1按preNorm之后的gate、up、down顺序复用；N1负责pre-FFN及Gemma规定post-FFN Norm；G1做SiLU或GELU_tanh及门乘；E1处理已接收单位下的残差/必要尺度；S1/T1完成tile/回放/输出。没有递推state，R0。

单M构造为：先保存Norm输出，逐中间tile计算up并保存，再计算gate并与up配对，经G形成mid，保存完整逻辑mid；全部所需mid可回放后，M切换到down，逐输出tile沿完整I累加，最后完成后处理及残差。不能边让同一M重写gate/up的merged，一边假设它还保留down累加器。Qwen2.5一个mid按S16即22016B，超过S16KiB；本构造需要MEM/spool或另行证明的分片/重算方案。

F在七个非Granite样本中静态展开210次。MoE内部专家不能直接调用完整F，因为F包含preNorm与残差；专家只复用gate/up/激活/down核。

### D：GDN mixer

M1用于qkv/z/beta/a和输出投影；N1用于输入RMS0、按源图Repeat后Q/K L2、逐value-head输出RMS；E1用于规定Q缩放、布局后的向量运算/残差；G1用于SiLU、Sigmoid、Softplus等既有子操作；R1先分组做conv/history，再按head/value列组做GDN update/readout。S1/T1承担分片搬运和输出。

一个R可以时间复用32个value head及列组，不需要按头数或24个GDN逻辑层复制R。但完整单层S32 state为2MiB，GDN自然R tile为128行×8列×4B=4KiB，共512个；8192通道conv history也需后备存储。R中active/shadow容量和局部commit不等于完整子层状态容量/原子性。系数Exp/decay、未知L2 epsilon、宽转换、old/next根及MEM能力另列缺口，G不直接完成全部系数公式。

### H：Falcon混合mixer

保留一次共享输入RMS，在同一个Block内按合法顺序串行执行Attention分支和SSM分支。M1复用各分支投影；N1复用共享Norm、Attention Softmax及SSM输出Norm；E1处理RoPE、分支尺度、join与残差；G1处理SSM SiLU/Softplus等；R1复用conv和SSM状态步骤。两分支结果必须保存，同一token的两支成功后才join并发布。

完整单层state为4MiB，R自然tile为256×8×4B=8KiB，共512个。Falcon卷积bias32、dt/decay/inject、MuP尺度和状态版本服务仍缺，不能把七个宏各1写成已闭合实现。

若要求两分支独立调度，可研究拆成Attention_H包装和SSM_H分支：合计M2/N2/E2/G1/R1/S2/T2、CTRL2，共12叶宏；Attention_H包装保留一次共享输入Norm及最终join/residual，SSM分支直接吃Norm结果。它们不是两个普通完整子层，跨岛Norm/回传/释放/发布仍需新合同。共享N/S/T的cluster又是另一种带仲裁方案，不能在两独立包装计数中免费扣除资源。

### X：MoE子层

M1顺序完成router和8个选中专家的gate/up/down；N1先做一次pre-MoE RMS，再做40选8 TopK和selected8的Softmax；G1做专家SiLU门乘；E1处理源gain/残差及其可覆盖的向量部分；R0。S1/T1保存ID、rank、score/prob和分片结果。

Top8不要求8个M或8个完整F Block；可以按rank串行读取不同专家权重并执行，代价是延迟和权重带宽。N原生TopK只给ID，不包括selected-score gather、专家访问和宽加权归并。所需S32/Q14/S64 NUM、ID/概率配对、真实专家存储及公共单位转换另计；E16不能替代这些宽算术。单M的router结果和各专家结果也必须在覆盖前保存。

## 4. 八模型如何使用这些Block

| 仓库样本 | 准确层型组合 | 静态逻辑层数 | 物理数量解释 |
| --- | --- | ---: | --- |
| Qwen2.5 | A_plain→F | 36 | 可复用同一批A/F能力，不等于36个A与36个F |
| Qwen3 | A_plain(Q/K RMS)→F | 28 | Q/K额外Norm由N1分阶段完成 |
| Llama图配置 | A_plain→F | 16 | 图为配置重建/随机参数，非原检查点资格 |
| Gemma | A_plain(local/global,RMS0)→F(GELU_tanh/postNorm) | 29 local＋5 global | 两种Attention参数/窗口，不必各配一套宏 |
| Phi | A_plain(融合QKV/部分RoPE)→F(融合gate_up) | 32 | 融合投影与split由程序/布局处理 |
| Qwen3.5 | [D→F,D→F,D→F,A_gate→F]×8 | 24 GDN＋8 global | R1可逐tile/逐层复用，完整状态存储另计 |
| Granite | A_plain→X | 32 | 40专家选8，单M可串行专家核 |
| Falcon | H→F | 32 | H包含Attention/SSM两分支，不再额外重复算完整A |

242逻辑层共484子层调用：A_plain178、A_gate8、F210、D24、H32、X32。这些是静态层序列展开，不是宏实例数、程序ROM字数、全部运行时job数或吞吐证明。

## 5. 全芯片的资源组织算例

本节说明复用，未确定最终数量或性能目标：

| 组织算例 | M | N | E | G | R | S | T | 叶宏数 | 局控/母控 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 一个全七类型Block，串行所有profile | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 7 | 1/1 |
| 一个非R包＋一个含R包 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 13 | 2/1 |
| 五功能各放一个，A采用gate能力并兼容plain | 5 | 5 | 5 | 5 | 2 | 5 | 5 | 32 | 5/1 |

两包或五包是增加资源和调度并行机会的算例，不是功能下界。非R包可预制A_plain/A_gate/F/X；含R包支持D/H，也可在ROM、数值和路线并集接收后复用A/F等，让无R模型仍能使用其M/N/E/G/S/T。相同宏BOM不足以证明所有profile程序和附加能力已存在。

五包32叶相对五个全七包35叶仅在数量上少3个R；仅R主bank数组少3×16KiB=48KiB，S/T/R分离主数组从190KiB降至142KiB。未计R辅助数组、其它宏/控制/NUM、路线和时钟，不把这个差值当芯片面积或同吞吐节省率。若普通Attention另独占plain包装，则还要另算其5叶，不能既享有专用plain又不计那份实例。

## 6. 并行增配需要什么依据

无频率、tokens/s、batch/context和MEM带宽目标，无法从模型名唯一确定最优M/N/G/R数量。给出1不等于性能够用，给出2也不代表吞吐翻倍。

指定一个直接分块算例：单query行、Qwen2.5 H2048/I11008、M每次K≤32/N≤8，gate/up/down合计264192次EXEC；down逐8输出列回放mid的逻辑读取量为5636096B。它们不含loader、读回、ACK、数位展开、数值服务或MEM延迟，也不是cycles或外存实际总线流量。这个量级说明M1表用于明确串行构成，不能当实用吞吐已足够的推荐。

- FFN两M算例可由M_P交替做gate/up、M_D保留下游down累加上下文；完整H输出通常分多tile，仍需mid重放或重算，不能自动省去完整逻辑mid保存。
- Attention多M可将投影、QK、PV或输出任务分配到独立上下文，但N、KV/score存储和供数也可能成为瓶颈，必须联合算。
- 一个S宏只有一个loader、一个A128和一个B512出口。多个M共享它需真实的喂数路由、owner和仲裁；每M配独立S可减少这类共享，但增加数组和端口，仍需跨S搬运。
- 多N只在独立归一化/Softmax组真正重叠时有意义；多G按实际门控lane吞吐配置；多R应按state处理周期/通道和MEM反馈选择，不能按逻辑层数直接复制。

对照必须分别报告同实例分区实验与同吞吐目标资源实验；增加S/M或删R所产生的变化不能全部归因于大Block层次。

## 7. 七宏数量之外必须另外记账

每Block还要本地CTRL/程序参数ROM、native唯一owner与phase锁、局部MUX/pack/layout、输入/输出保持、分片计数和ACK/释放、固定喂数线路；母控、命令/完成端点、MEM/host接口、状态根/版本及clock/reset/PG另计。R_T局部提交不提供跨tile/跨Block全局原子性。

一S/一T只覆盖被接收的工作分片。S16KiB和T6KiB不存完整权重/KV/state；例如H最大3072时，一token hidden的S16输出6144B恰为T上限，S32输出12288B已经要分批，多token更要分片。大批次的fragment_last不等于完整job完成。MEM还未闭合的完整profile保留unmapped，算法合法性不因此被删。

当前N/G等宏仍为完整既有实现。A/F不用TopK时，N的TopK阵列可能闲置；不调用某op不会在M11阶段删除已制造单元。裁剪须在预制前按该物理位置跨全部有限产品映射的需求并集处理，并重新核验共享数据通路、测试/恢复op和物理资格。本轮没有制作任何裁剪宏或新物理视图。

## 8. 完整推理外围边界

本次五功能类覆盖的是已有十种decoder层图。embedding/参数gather、最终Norm/LM head、logit后处理、采样/EOS与host/MEM平台须另外明确。它们可以复用部分M/N/E/S/T和共享服务，不要求未经分析就额外复制整套七宏；当前图证据不足以给出已接收的专用外围BOM。

N原生TopK最多40项且ID16bit，不能不经额外分块/全局ID和采样算法就当任意大vocab sampler；R是递推宏，也不是随机数发生器。若采样放host，要在完整系统合同声明。现有Issue153的SystemC结果保持其独立范围，不能直接变成本表粗Block的RTL/物理资格。

## 9. 验证与下一步

本表的数量来自源算法映射、原生宏接口与给定串行调度，而非新RTL、仿真或综合结果。需要接收完整参数范围、每边数值/舍入、MEM/NUM/版本服务、全程序/ROM、资源准入/无等待环、性能和物理后，才能冻结实际BOM。

建议先用这六张参考配置做本地程序/存储调度，保留P2小MST回归；先完成A/F两个垂直子层和双Block传递，再补D/H/X的系数、状态和宽归并。资源并发优化按真正瓶颈逐项增配，不取消原P2矩阵或提前进入已完成P3–P7状态。用户的服务器仿真授权保留，按REMOTE_RULES仅在本人Melodydt目录开展；本轮没有新仿真/服务器部署或作业。


## 10. 本轮材料及证据入口

- [模型与变体映射](BLOCK_VARIANT_MODEL_MAPPING.md)：六配置每宏用途/关键op、十层型与242层完整序列；机器表work/Melodydt/151/block-variant-models.json。
- [串行/并发资源构造](BLOCK_RESOURCE_SCHEDULES.md)：M1中间值保存、M2/M3及S喂数条件、1/2/5包总量和逻辑访问字节；resource-baselines.json。
- [局控和共享资源归属](BLOCK_CONTROL_OWNERSHIP.md)：CTRL、H完整/拆分、共享端口及固定底座约束；block-control-sizing.json。
- 本轮来源与脚本/产物SHA见block-sizing-inputs.json、block-sizing-checks.json、block-sizing-verification.json，复现命令见[ARCHITECTURE](ARCHITECTURE.md)。它们是研究一致性证据，不作新仿真或完整硬件接收。

研究仍沿用Issue151/PR152。服务器仿真授权继续按REMOTE_RULES本人Melodydt目录执行；本轮没有创建服务器目录、上传文件或提交作业。原P2剩余验收和P3–P7状态不变；审查、远端提交、登记与看板状态以本轮PR回执为准。
