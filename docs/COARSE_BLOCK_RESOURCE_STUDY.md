# 粗粒度计算岛：粒度、资源、流量与物理边界评估

输入研究提交`1cc43a9`，使用该包已选择的PR144 `707878621b2add4ed218b8c43df2e95c9a56e2ba`叶源码与八样本目录。此稿只做静态研究，不改RTL、正式包、服务器或远端，不宣称PPA改善、全模型准入或共同底座冻结。计算脚本、输入SHA、逐模型数字分别见`build_coarse_block_bounds.py`、`coarse-block-bounds.json`和`coarse-block-tables.md`。

## 1. 建议目标：同构全七类计算岛，子层功能作为profile

主候选采用用户提出的层级：每个预制计算岛内部含M/N/E/G/R/S/T及局部控制；母控调度岛；M11/M12永久绑定岛间路线、有限产品入口和参数。岛内有源MUX、保持/拆拼、地址形成、控制、buffer及clock/reset必须先制成。把七宏画进同一方框不会自动增加这些能力。

建议保留五种子层级功能profile：A完整attention、F FFN、D GDN、H Falcon attention+SSM hybrid、X MoE。LINEAR/MST只是岛内可复用基础核。**五种profile不等于五种物理岛，也不等于必须有五个岛**；一个岛可按预制程序依次执行不同profile。七种宏type也不等于每类只能放一个物理instance；先以每类一个为可分析基线，再根据并发、带宽和物理证据决定复制。

尤其，同一个M可以先后计算Q/K/V/O、gate/up/down，但不能同时执行它们。M两个输入bank允许预取，不是两个执行M；两个bank共享一份merged结果上下文。M11/M12只选已有能力，不允许因为某产品缺少buffer、MUX或第二个M，定制时再补有源单元。

八样本映射按真实层型选择：Qwen2.5、Qwen3、Llama、Gemma、Phi主要A+F；Qwen3.5的8层global gated attention用A+F，24层GDN用D+F；Granite用A+X；Falcon每层H+F。QK norm、Gemma六处Norm/RMS0、Phi部分RoPE、query gate等是profile内部的有限变体，不能因轮廓相似而删除。

## 2. A/B/C三种粒度的比较

| 候选 | 灵活性与绑定 | 资源/空闲 | 边界流量 | 主要风险 |
|---|---|---|---|---|
| A 每岛全七类，可增加实例 | 任一同构岛可执行有限A/F/D/H/X；产品换入口和参数 | R等在部分profile不用，但保持跨产品映射自由；同一M时间复用 | 以H维子层输入/输出为主，I维、score/EXP及H内部fork/join可留岛内 | 局部控制、共享资源冲突、buffer/MEM与功率密度；全七类不代表算力比例合理 |
| B projection/attention/FFN/state/MoE异构子集 | 可以删掉类型，但每类数量、位置和路由在预制时锁定 | 非状态产品可省R；多型号之间更容易出现类型资源闲置或不足 | 若切在QK/Softmax/PV或gate/up/activation/down之间，反而导出大中间张量 | 被固定type分布限制；projection单元不宜机械成为外部粗边界 |
| C 整层封装 | 一次job可涵盖attention/state+FFN和Norm/residual | 若一层一物理岛可大量复制；若一岛复用多层仍需要持久权重/状态MEM | 最小化层内激活切边，但MEM/KV/状态流量仍在 | 层差异、工作集、局部程序与错误发布范围最大；可能降低多个岛的并行调度自由 |

主候选A提供统一物理资源，按子层profile定义程序及对外合同；B作为删宏成本/能力对照，C作为更大封装对照。C不必等于按模型层数物理展开：一个整层engine也能时间复用多层，但背后必须有各层权重、KV与状态，不能把逻辑层数当物理岛数或相反。

## 3. 一个全七类岛至少包含多少显式存储

由原生数组得到的**S+T+双R银行payload底数**为：

```
S16KiB + T6KiB + R active8KiB + R shadow8KiB = 38KiB = 38912B
t个同构一套七宏岛：38*t KiB
一般实例向量：16*nS + 6*nT + 16*nR KiB（每R含active+shadow）
```

例如8岛304KiB、32岛1216KiB，仅指这三类银行，不是总面积。它们**不是一块可任意分配的38KiB RAM**：S是普通字访问和loader共享的16KiB，T是6KiB单租约顺序事务缓冲，R银行专用于一个有限状态context及候选/SSM factor。底数还未计M A/B缓存、merged/partial、R历史/参数/输出、N TopK与算术、E/G流水/LUT、S loader/响应、局控ROM/MUX/额外capture及物理基础设施。

八样本每token的H维S16向量最大6144B，单独可装满一个T，但这不意味着多token prefill输出或S32向量也能装入同一批次。`2*q*H`、物理128bit字对齐、T的384字上限和任务原子输出边界需分别核对；分成多个T批次本身不会得到全job原子性。

六个样本产品（Qwen2.5/Qwen3/Llama/Gemma/Phi/Granite）没有GDN/SSM，按当前算法R不参与计算。全七类岛仍有每岛16KiB专用R银行；它占上述38KiB**银行字节底数**的16/38≈42.1%，不是面积占比、功耗占比或测得闲置率。若同一芯片只执行这六类之一，重复岛中的R不会因软件不调用而消失；可预制clock/power管理，但其效果仍需实测。保留R的价值是共同底座可映射D/H，取舍必须基于实际产品组合和数量。

P2的419bit只由母控8bit、局部服务142bit、S helper269bit声明字段构成。它验证了固定S8 DOT8→S→T小fixture，不包括完整A/F/D/H/X程序、通用参数接收、版本/credit、多head、buffer或物理开销，不能乘岛数当通用控制budget。

## 4. 单M时间复用对边界选择的硬限制

原生M只有8×8 S64 merged context，且没有从S/MEM恢复merged的命令。因此不能凭“岛内调度”假设下面的任意交错都成立：

- gate/up产生一个I片段，立即在**同一个M**追加Down partial，再用该M算下一片gate/up；后者会覆盖或改变merged，当前Down partial无法原生恢复。
- 同一个M一边保留PV partial，一边算下一段QK；同样需要保存/恢复或不同资源。

单M保守方案是先完整保存当前job需要的mid或score/EXP，再切到Down/PV阶段。其他方案包括明确的重算顺序、增加M实例、增加宽累加/restore能力；都需要独立数值、时序和存储证明，不能作为既有硬件免费能力。

例如Qwen2.5的一个mid S16向量为11008×2=22016B，已经超过整个S16KiB；Llama/Phi的16384B只恰好填满S，尚未留权重、输入或holding。原P0串行预留loader1KiB与T spool6KiB后计算区9KiB更紧。局部生命周期证明可以取消某条路线不需要的预留，但不能无依据删掉存储。**I维不跨M11不等于I不需要存储**，它可以转为岛内额外存储或MEM事务，而这些尚未实现。

## 5. 可计算的FFN、attention及状态界

以下均是B=1、候选S16激活/概率、候选S8权重的字节量。原图FP32/配置bf16不等于已通过S16/S8量化；上下文256/4096只是估计点，不是硬件接纳。逐模型完整数字见计算JSON和表。

流量数字只计命名逻辑切边的元素payload，假设所需合法打包已成立；原生M5的S32 carrier padding、消息framing、重复传输及实际线网复制另计，不能直接当作已测物理bus字节数。

### FFN应避免I维粗切边

若把gate输出、up输出、activation后的mid分别跨岛，每token三条I维S16边合计`6I B`。F profile把这些边留岛内，外部H输入+H输出为`4H B`，但这两数属于不同切边口径，不能直接相减宣称总流量节省率。权重、inputNorm/residual以及MEM读写必须另外计量。

Qwen2.5三条I边为66048B/token、一个mid22016B；Qwen3为18432B与6144B；Falcon为36864B与12288B。Granite的I=512是**每expert**，不是全层I：top8同时保留mid为8192B，但8个H维返回为24576B，已超S16KiB；顺序merge可减少活跃返回，但需要真实累加/存储/路由及数值方案。

三矩阵权重的S8字节估计为`3HI`，S16则为`6HI`，两种都不是已接受量化。Granite每expert约2.25/4.5MiB、40expert一层约90/180MiB；F或X成为一个大Block也不会把这些权重放进16KiB S。可以经MEM分块访问，但本轮没有可用的外存带宽/调度/控制器证据，不能将MEM画成无限速箭头。

### attention粗边界应包含QK、N与PV

若QK→N与N→PV分属岛，score与probability的两个全张量切边为：

```
(b_score+b_prob)*Hq*q*L
S16/S16例：4*Hq*q*L B；prefill q=L，decode q=1
```

以Qwen2.5 Hq=16为例，dense prefill L=256两个切边4MiB，L=4096为1GiB；decode L=4096为256KiB/token。A profile可避免把这些中间结果送到其他计算岛，但并不消除attention计算量、岛内score/EXP保存、KV访问或MEM总线流量。因果三角或在线attention可能改变存储/流量，当前N不提供通用在线分块合并归一化，不能默认为已实现FlashAttention。

score若保留S32或M.op3 S64，切边还会变为`6*Hq*q*L`或`10*Hq*q*L`；必须依据真实数值合同，不能只因bus是128bit就套用同一S16口径。

只考虑单query的score+EXP两个S16向量，完整物化为`4L B`；L4096已用满整个S16KiB，未留任何其他数据。N单上下文统计计数最多65535，不因封装大块而增加；配置最大context更长时需要新的合法分块/合并算法及证明，不能直接把每段单独归一化后拼回。

KV缓存使用真实Hkv，不扩成Hq：候选S16单层`4*Hkv*D*L B`。L4096时Qwen2.5为4MiB，Qwen3为16MiB，均远超S；Qwen3.5只有8层attention，Gemma local层可按window截断，这些差异已在JSON全模型层型求和中保留。Q宽也不能默认H：Qwen3的H1024但Q2048；Gemma H2560但Q2048；Qwen3.5 H2560但Q4096且组合query/gate8192。

### D/H状态必须有真实后备存储

Qwen3.5 GDN每层完整S32 state为2MiB，Falcon SSM每层为4MiB；old+next约4/8MiB，历史另计。全模型GDN24层旧state共48MiB，Falcon32层旧state共128MiB；时间复用一个R不能删除这些持久数据，只是把它们移到后备存储与装载/提交流量中。

`2MiB/8KiB=256`只是R active银行容量比，**不是GDN原生命令数**。自然映射下，GDN length128、每native8列只使用4KiB，32heads×(128/8)=512逻辑tile；SSM length256、每native8channel使用8KiB，同样为512逻辑tile。这些数既不表示512个物理R，也不表示512拍。真实时延还包含装载、跨head处理、Norm/gate、版本与MEM访问。

R成功EXEC的输出可以提交前读，但本地R7接受后不可由R8打断，COPY发布后也不能撤回。全D/H job如果跨多个R逻辑tile，仍需old/candidate后备状态与整job版本发布；封装为岛不自动赋予全job回滚。

## 6. Falcon H留在岛内的利弊

建议把attention与SSM分支、输入fork、各自输出投影/缩放和join置于H profile的局部控制域。可在局部完成数据同源性、位置/版本一致性、错误汇聚，避免把fork/join变成M11上数条必须协调的长路线。举一个明确切边口径：若外部fork同时给两分支各送H，再把两H结果送到外部join，端点传输合计`4*b*H`；合并后单H输入和单H输出为`2*b*H`。b=2、H2560时分别20480B和10240B/token，**只计这些端点传输**，未计权重、KV、SSM state和Norm等，不是整模型带宽减少一半。

代价是单M情况下两支projection时间复用，不能宣称物理并行；join前必须保留某一支结果，局部MUX、buffer、程序与控制活动增加。若H profile需要同时运行两支，可增加M实例或两个岛，必须以相同实例数和吞吐目标分别比较。独立attention/SSM岛更容易给两支分配不同数量资源，也可能复用已有A/D类能力，但增加全局同步与边界搬运。

H还需明确错误及状态发布顺序：一支失败时不能把另一支局部R提交当作全job已成功，也不能因协调reset就假设恢复旧state。先保护所有所需结果/候选后备版本，再发布全job完成；已被外部接收的流数据无法撤回。若要求任务级原子输出，T容量/多批次协议也必须匹配整个输出及提交边界。

## 7. prefill与decode不能只看一种调度

prefill有多query，可利用M多row、head/tile并行和岛间流水，但score切边随L²增长，KV、weights和临时保存仍重要。decode每步通常只有一个新query，attention切边随L线性，R/state逐token依赖突出；小batch下权重与状态供给可能限制可用算力，具体瓶颈须按实际MEM/带宽测量，不能凭封装大小确定。

相同物理岛可用不同的预制prefill/decode程序与参数路径；这仍属于固定模型的执行阶段选择，不是M11以后再制造控制器。这里引用的原八样本算子图导出为短FP32且use_cache=false，其cached decode未验证；Issue153另有独立SystemC结果，不能直接转为新岛的RTL或物理资格。新岛仍需相应参考/RTL场景后才能授予支持。

## 8. 实施与公平验证步骤

1. 冻结A/F/D/H/X各自的精确边界、family变体、shape/L/B范围、单位/舍入、状态与错误发布语义；把未知数值、MEM、宽算术和版本能力明确留gap。
2. 先把已有P2 MST包装成岛内LINEAR核，保留19场景作为回归，再实现N/E/G/R局控、固定线路/MUX与真实holding；不把MST fixture程序扩名为通用island程序。
3. 做单岛F/A垂直验证，特别证明单M merged上下文生命周期与mid/score保存；随后D/H跨tile状态及X TopK→地址→真实expert数据→merge。测试尾部、不同lane/格式、背压、重复job、错误和reset。
4. 对两个及以上相同岛实现真实跨岛请求/响应、buffer/credit、版本/结束/排空协议；证明fork/join与同资源重入无死锁。外部MEM独立接入，不借本稿假定其已存在可运行接口。
5. 用两个不同有限模型/模式在**同一份预制RTL/布局**上改变永久入口/参数/连接证明可定制，不能每产品重综合删宏或插buffer后仍称同底座。
6. 做物理比较的两套公平实验：首先保持全局宏实例清单、存储/算术能力、频率/角、IO约束、线负载与工作负载一致，只比较flat、island与整层分区/控制位置；异构B若真正删宏，就不属于这套“仅改分区”的实验。另做同产品覆盖/吞吐目标的成本实验，允许B删宏或A增加M/R/存储，但把全部变化实例、能力范围、MEM及流量计入，不能把删宏/增资源的差异全归因于层级。两套口径不可混为一谈。
7. 记录实际局部/全局线长、绕线拥塞、WNS/TNS、setup/hold/电气违例、clock/reset/PG开销、活动/空闲功耗及各profile吞吐/延迟。大Block可能减少全局协调，也可能增加局部拥塞/功率密度和难访问pin，结论由真正布局布线和负载测量给出。

此轮没有启动MobaXterm/服务器/仿真/EDA作业。可复跑的计算命令：

```
python -B -X utf8 work/Melodydt/151/build_coarse_block_bounds.py --root . --output-dir work/Melodydt/151
python -B -X utf8 work/Melodydt/151/verify_coarse_block_bounds.py --root . --output-dir work/Melodydt/151
```

实际完成八模型、十层类型的整数容量/切边计算和来源哈希检查，57项独立字节/单位/样本边界检查通过；这不证明完整程序可编译、定点质量、外存带宽或任何PPA改进。正式部署/实验前仍需按REMOTE_RULES与本人目录/来源追溯规则另行实施。
