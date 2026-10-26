# 04｜连续状态与 MoE：Qwen3.5、Falcon 和 Granite 的完整推理链

这三种模型使研究从“几个相邻算子放在哪里”推进到“计算、数值范围和可见状态由谁负责”。以下软件整数、有限服务、RTL及物理层次分别记录。

## 1. Qwen3.5-4B：先确认连续执行参考

### 1.1 为什么不能把窗口清零再拼起来

Qwen3.5文本网络同时有全局注意力KV、短卷积历史和GDN递推矩阵。处理下一段时必须保留三者。若每个窗口把state清零，得到的是几段互不相关计算，不是原连续模型。

Issue32初版FP16短参考通过，但长512/2048部分状态相对L2超过0.02；BF16短参考也失败。后续修复显存后，8192的FP16一次/分块状态误差仍约0.0670345；FP32计算诊断约0.00015652，通过本批门。说明“能跑到8192”和“连续状态一致”是两个结果。[S32](10-evidence-index.md#s32) [S32R](10-evidence-index.md#s32r)

再固定归约树、卷积求和、逐token递推和逐query因果attention，以真实INT8矩阵＋规范FP32辅助执行，所测128+16和512/2048/4096/8192+32的整段/分块输出及比较缓存逐位一致。这解决了**指定语义下的执行延续**，不代表没有浮点，也不指定目标硬件一定采用该软件后端。

### 1.2 原始容量说明什么

24递推层每层FP32 `[1,32,128,128]` 为2MiB，共48MiB；卷积按实际4槽分配共1.5MiB；8个全局层FP16 KV共32KiB/token。因此原条件有49.5MiB固定状态，再加随长度增长的KV。不能因为用了线性注意力，就删掉全局KV或把递推状态视为几个标量。

若想存INT16/INT8，必须另证精度、scale和更新方法；不能直接把48MiB除二或除四当实测新结果。源GPU批次的状态敏感性是量化—反量化后浮点更新，后来的整数R才解决不同的问题。

## 2. Qwen3.5消费者：只看矩阵出口会漏掉什么

### 2.1 从16输出扩到完整hidden

Issue61的layer3 down前16输出提示：动态A/W K128后，最终RQ前最坏误差约0.84%，Y8后约4.83%，输出合同成为主要疑点。Issue64在固定partial上试Y16和tile delta，随后Issue66真正接上完整H2560的残差、layer4 input RMSNorm及下一投影前16输出。[S61](10-evidence-index.md#s61) [S64](10-evidence-index.md#s64) [S66](10-evidence-index.md#s66)

输入是独立校准/评价文本，B1、prefix128+cached32；down完整K9216/N2560。四种出口：静态ACT8、相同物理范围ACT16、base+tile16 delta ACT8、delta后再转K128单位。上游A/W和完整I64对齐归约保持一致。

| 出口 | prefill down/next局部RMSE | decode down/next | 出口饱和prefill/decode |
| --- | --- | --- | --- |
| 静态ACT8 | 3.380% /3.513% | 2.805% /3.150% | 36/1 |
| 同范围ACT16 | 3.010% /3.285% | 1.847% /3.101% | 36/1 |
| tile delta ACT8 | 2.256% /3.261% | 2.202% /3.086% | 0/0 |
| delta再转K128 | 2.256% /3.285% | 2.202% /3.244% | 0/0 |

此表的next是该轮明确的后继探针，不是整模型最终质量；初版RMSNorm仍是FP32桥。ACT16和ACT8端点相同，因此两者饱和次数相同。预先把tile delta统一成K128只省当时协议128B/row，却可能增加下一环节误差，不能默认所有边界都必须统一scale。

### 2.2 整数norm补上了什么

后续整数norm用当前整数行生成X16，U64平方和、明确epsilon和gamma编码、restoring isqrt/divide、RNE，生成fresh A8K128再给下一矩阵。8条件共160行、每行2560通道。同X16时整数norm对浮点norm最坏RMSE约0.000050%；含重编码后约0.05862%。下一投影相对旧FP桥链最大差约0.4975%，说明很小的norm变化也可能改变A8码。

容量检查同时发现：完整I64对齐行20,480B、sum+unit25,600B都超V16KiB。必须两遍源读，或显式spill再读；gamma+norm也不能免费同时驻留。当前动作下界6084/6404 beats不是已调度的真实周期，SFU、依赖和端口争用还要另算。

**划分依据：** 保留 `ALIGN→残差→全H统计→norm→新A8` 的语义责任。它可以物理分片，但完整统计屏障、单位和版本不能省。输出格式必须与真正消费者共同选择。

## 3. Qwen3.5连续整数状态：先发现范围失败

### 3.1 捕获与整数更新

Issue66取layer0、共享Khead0的Vhead0/1，完整K128/V128，非零初态，32步真实连续输入和33个R/conv边界。另接收旧层0/14/30、终点2048/2049/8192/8193的真实状态窗，不拼接互不连续的窗口。

整数顺序明确为：decay及RNE→完整K prediction→value减prediction→beta及RNE→outer更新及RNE→range检查→用新state读出output→同版本发布。S16/S32保持相同物理范围，S32只是更细单位。conv的SiLU和部分输入生成在这个早期阶段仍有FP桥。

| 新32步格式 | 输出局部RMSE | final state局部RMSE | state饱和 |
| --- | ---: | ---: | ---: |
| S16/D15 | 0.64384% | 0.49519% | 0 |
| S16/D31 | 0.64217% | 0.49579% | 0 |
| S32/D15 | 0.05666% | 0.02774% | 0 |
| S32/D31 | 0.05667% | 0.02767% | 0 |

S32降低了短程舍入误差，但旧256步窗里，同范围S16/S32在layer0/end2048都有184次饱和，end8192都有193次。即使某条件输出误差只有约0.04821%，仍是范围失败。[S66](10-evidence-index.md#s66)

### 3.2 三种策略回答三个问题

Issue68固定三策略：static_sat用于诊断会裁掉多少；static_guard越界拒绝，保护旧发布；guard_rescale只观察当前尝试，重编码越界head的旧整数state、单位变粗，再完整重试同token，最多8次，不看未来误差。[S68](10-evidence-index.md#s68)

原六个256步窗×四格式共24源条件：static_sat复现1508次state饱和；guard有8条件提前停、16完整；adaptive全部24完整、零发布饱和，16次重编码波次，新增重编码读写1,572,864B，尚未包括所有备份与重试流量。

固定layer0/end8192 S32/D31：static193次饱和；guard在第4token拒绝；adaptive两波后完成256步，units从[-27,-33]到[-27,-31]，epoch2，重编码自身262,144B读写。输出约0.04821%→0.04724%，不以这点误差改善宣称placement收益：adaptive已改变数值函数。

### 3.3 为什么必须全head，而非每tile各自改scale

head是一个共同单位解释的矩阵。若只把当前tile单位变粗，后续prediction会混合不同单位；若不传完整元数据，就会错误相加。tile可以控制搬运粒度，不能偷偷改变全head数值合同。

重试还必须保留旧合法状态、私有proposal、输出和版本。guard拒绝时零发布饱和，不等于把全部token成功跑完。统计必须同时给提交数、拒绝位置、重标次数和额外读写。

## 4. 从Qwen整数参考到完整双头GDN RTL

Issue104不再用Falcon方程替代Qwen：实际实现两完整128×128头，S32状态非对称上界为32767<<16，Q/K/V对称S16，decay U32Q31、beta U16Q15；prediction/residual/correction/proposal/Y保留I64。[S104](10-evidence-index.md#s104)

真实轨迹含33位中间量，合成边界补到34位。宽乘用radix2^31拆31/31/1位，三次使用同一个S32乘法服务，精确合成后一次RNE；不是将宽量截成S32，也没有免费新增128位乘法器。

| RTL数据 | 完整提交 | 重标波次 | quiet命令周期 | 有等待/peer周期 |
| --- | ---: | ---: | ---: | ---: |
| native32 | 32步 | 0 | 73,441,693 | 87,399,518 |
| portable12非零checkpoint | 12步 | 2 | 30,763,438 | 36,490,030 |

portable最终position7950、version14、units[-27,-31]、numeric_epoch2。position表示处理到哪里，version表示提交代际，epoch表示数值单位更新，它们不是同一个字段。

单16KiB/1RW scratch放不下全部持久状态；固定外部1MiB窗口包含双state、trial、I64 proposal、双Y、metadata/root及32槽系数，实际active709,776B。每轮两个head收齐guard、按同一root发布，不能各头先后独立对外可见。

真实两检查点（普通步/重标步）×两等待的选定门级通过。连续32/12步来自RTL，不能写成全部门级连续。conv/输入投影/L2norm/gate生产、输出gated norm和所有heads不在此核内。Issue109后来将该控制器接入实际共享资源，并补上2048B候选Y真实导出，但下游完整事务消费者仍待实现。[S109](10-evidence-index.md#s109)

## 5. Falcon-H1：用另一种递推检验R不是模型专用框

### 5.1 原生参考与初期反例

固定revision见第02章，BF16原权重转CPU FP32。Issue70独立cal16/eval72，prefill64+decode8，完整hybrid layer，chunk1/8/16，head0完整D128×N256。23项参考门和独立FP64重放通过。每8步清状态的错误实现，输出相对L2约16.8128%，直接说明连续历史不可删。[S70](10-evidence-index.md#s70)

S16与S32存储诊断都出现4次饱和，输出误差约0.606194%/0.606038%。当时更新、conv、SiLU和系数仍浮点，所以不能称整数R，更不能与后来的全32head新合同直接比较。

### 5.2 完整软件整数R分支

Issue72建立 `输入RMSNorm→MuP/in_proj→conv4/SiLU→dt/alpha→32head state/readout→gate→4096共同norm→out_proj/MuP→A+residual+R→H2560 nextnorm`。外部A分支与MLP仍在切口之外。输入、history是I32Q12，gamma/MuP/skip Q20，alpha U32Q31，state S16/S32配每headI16单位，运行内有显式整数LUT/宽算术。[S72](10-evidence-index.md#s72)

| full R策略 | S16 | S32 | 如何解释 |
| --- | --- | --- | --- |
| static_sat | 72提交/9529饱和 | 72/9535 | 程序跑完，但范围失败 |
| static_guard | 仅1步提交 | 仅1步提交 | 保护旧态，未完成72步 |
| 因果重标 | 72提交/0发布饱和 | 72/0 | 51个head事件，25次group epoch |

full S32重标对native局部L2：inputnorm0.0181%、projection2.4868%、scan1.5086%、gatednorm3.1250%、outlinear6.7257%、join3.1516%、nextnorm3.0289%；S16 nextnorm3.0297%。状态加位并未解决主要下游误差，不能用更多状态位替代输出投影研究。

独立接收完整stage/state/unit/epoch；软件checkpoint核73个边界，chunk8/16及prefill64+decode逐码一致。late-consumer失败后旧conv/state不发布，再试恢复正确。这仍是软件事务证据，硬件另验。

### 5.3 只改变输出投影A粒度的受控实验

冻结同一gatednorm输入和W8/静态参数，仅把A8从整row改K512/K256：

| A粒度 | outlinear L2 | nextnorm L2 | 72步partial wire |
| --- | ---: | ---: | ---: |
| 整row K4096 | 6.7257% | 3.0289% | 751,104B |
| K512 | 4.3136% | 1.8675% | 6,008,832B |
| K256 | 3.9044% | 1.6733% | 12,017,664B |

这是声明partial协议下的成本，局部对齐可能改变通信，但需新buffer/端口证明。最大绝对误差并非全面改善，不能只挑L2最小的一栏。完整K先对齐再最终RQ，提前各组RQ是另一函数。

### 5.4 同资源边界比较为什么没定出独立R宏

Issue72比较R32KiB D8、V16KiB D2、R D16+Sspill，完整compute和恢复费用计入。S32条件相对R8，V2慢约0.013574%，D16spill反而快约0.001951%。这是保守串行条件图，不是实际时钟周期，微小差异不足以冻结物理边界。

Issue74对whole/K512/K256分别固定相同函数，再比较nearM/sharedV，近M完整链条件slot节省约0.001007%/0.008010%/0.016005%。不同g之间数值不同，不能把其误差收益称位置收益。[S74](10-evidence-index.md#s74)

### 5.5 Falcon完整head进入RTL

Issue99实际实现一个完整D128×N256 head，32768个S32码、72连续步、全headguard、重标、完整N256 readout和原子root发布；一个16KiB scratch、共享S32乘法。真实position27→28发生重标，单head本地epoch0→1，不能与原32head group epoch25混同。[S99](10-evidence-index.md#s99)

quiet总148,909,146周期，有等待175,736,069；首步2,047,764、重标步3,419,094 quiet周期。两处checkpoint×两等待的真实门级通过。外部state128KiB/head，active mutable656,400B，加72步coeff共843,024B，明确占1MiB窗口。

conv、其他31head和完整4096消费者仍不在该RTL内。后续106/109的R candidate导出和共享资源验证补上另一些接口，没有使全部Falcon分支自动成为端到端电路。

## 6. Granite：先让路由参考自洽

### 6.1 初期为什么不能只保留通过项

Issue70的FP32 full/cached很接近，但eval chunk16的relativeL2约0.00582334、maxabs1.18297，超过事前2e-4/2e-3双门。首集合变化在零基层13/token42：第8/9分数差2.9802e-8，小于logit扰动1.8179e-6，专家7变1；累计10个layer-token集合改变。[S70](10-evidence-index.md#s70)

固定full专家ID、仍用当前logits算softmax后，误差明显回落，支持离散路由放大解释，但不能定位具体kernel根因。原FAIL保留，局部数学只标PARTIAL_DIAGNOSTIC。

Issue72提高router本身到FP64仍使失败移到cached，说明只提高router不够。显式eager专家后，model64条件参考的cal/eval full/cached/chunk四项通过、路由集合0变化；框架norm/RoPE/softmax仍有FP32 cast，所以不称全FP64真值。

### 6.2 冻结hidden后，单独看router精度

同上游hidden，实际40logits重新top8，32层×3执行profile×72token=6912相关行：

| router | top8集合变化/6912 | 证书可保证稳定 |
| --- | ---: | ---: |
| 静态W8A8 | 2040 | 0 |
| 动态row W8A8 | 720 | 0 |
| 静态W16A16 | 9 | 5244 |
| 动态row W16A16 | 6 | 6249 |

校准+评价合计13,824行，保守W8区间证书全部失败，实际全部先W8再W16；不能按“偶尔回退”预算便宜路由。证书不通过不等于每行实际选错，W16变化少也不等于全模型质量接受。[S72](10-evidence-index.md#s72)

W16不是免费能力：K1536粗界需42signed bits，按当前S8 lowering要9份dot及宽重组；Q15gate还要exp2、宽logit差、除法和索引元数据。router权重每层W8/W16为61,440/122,880B，都超过M32KiB。

## 7. Granite完整专家到merge整数链

Issue74取layers0/13、cal/eval各72行。外部切口为真实post-attention residual，不用hidden减MoE倒推。完整链：I32Q12 residual→全H RMSNorm→R8/R16 router→top8/Q15→全部所选expert gate/up W8A8→SiLU/门乘→完整K512量化→down→共同Q12→S64八路merge→0.22系数/残差→nextnorm。8条件、每项43stage/576专家路径，独立数学全部接收。[S74](10-evidence-index.md#s74)

| eval层/路由 | 对native专家集合变化 | MoE L2 | nextnorm L2 |
| --- | ---: | ---: | ---: |
| L0 R8 | 15/72 | 8.4195% | 9.4843% |
| L0 R16 | 0/72 | 7.7125% | 8.6287% |
| L13 R8 | 3/72 | 7.7869% | 1.1581% |
| L13 R16 | 0/72 | 7.7314% | 1.0196% |

L13 R16最终集合虽与native0差，对同一current norm的FP64 router仍有1处差，存在上游和router误差抵消。它说明观察基线的选择很重要：只看最终集合会误判router本身稳健。

整数PASS表示冻结函数正确执行，误差约8.63%等事实并未被消除。中间误差在最后Q12 RNE前已较大；只把mid换更多小数位，动态A8 shift可能同步增加，并不增加有效信息。因此没有盲加“midQ20就会好”的新实验。

## 8. Granite有限端口与容量：修正过的一次重要判断

八份S32专家完整输出共49,152B，放不进V16KiB；S64全hidden累加器12,288B，如果再静态加一份完整6,144B输出也超限。但后者不必同时活跃。

Issue76先缓存8份midA8到S0，释放前端临时量；down用O16小返回，完成八路prefix后分片写外部，最后释放merge再norm。fullH sharedV峰14,224B，保留2160B，因此完整merge实际可以放下。24配置含两层×window128/256/1536×M/V×标签，有限端口/FIFO独立接收通过。[S76](10-evidence-index.md#s76)

这不是给先前错误“找借口”，而是用真实生命周期修正过强的排除结论：不能把所有对象无差别相加，也不能把整输出暂存在Python而不付硬件费用。

每层全部40专家W8仍为94,371,840B，scale614,400B，不能以800M活跃参数名义只存少数权重。两层也不能同时塞进同一EXT128MiB。数据布局和权重分页仍是产品映射问题。

同函数nearM/sharedV每对少5,308,416B协议wire、774,144条件slots，但完整服务近M优势仅约0.0008405%。公共byte microframe策略占约99.75% wire和99.46% slots，掩盖当前放置差；这些巨量字节不是模型不可避免通信，而是保守实现暴露的瓶颈。

由此研究转向局部frame、宽算术与SFU电路，见第07章。后来的约44%局部frame周期降低和A-cache约34.68%链周期降低，各有具体电路原因，不能倒写成“MoE宏融合提升44%”。

## 9. 三种结构共同确定与尚未确定的边界

已经有依据保留的内容：完整K及最终RQ顺序；全hidden/head统计；单位/位置/版本；范围guard和因果重试；旧态与私有态分离；共同提交；动态expert索引和全所选路径；有限端口、scratch和响应holder。

尚不能从这些结果决定：独立R硬宏或V/R合宏；M/V/A物理融合；最终tile大小；ROM片内外；真实SRAM延迟/容量裕量；所有产品只改哪几层金属就可覆盖；全模型纳秒、能耗和成本优势。

下一步应把这些明确责任落实到可计价的真实接口和物理资源。增加更多同构模型，不会自动补上缺失的存储宏、事务消费者缓冲或受限层布线证明。
