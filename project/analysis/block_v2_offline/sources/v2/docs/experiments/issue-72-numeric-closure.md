# Issue72：路由精度、连续整数R与完整消费者闭环

负责人 Liangruizhi；[Issue72](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/72) / [PR73](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/73)，分支 task/72-numeric-closure，基于 PR71@f4d2c46。日期2026-10-24 UTC+08。本文严格区分软件整数数学、局部数值误差、条件服务与物理实现。

## 本轮结论

六个逻辑模板 M/V/A/R/S/D 继续保留。新增证据支持把路由精度与回退、R状态单位/代际和完整消费者归约作为必须保留的接口义务，仍不能固定独立R宏、V/R合宏或全系统PPA。

1. Granite较高精度参考在原门限下自洽，但不是部署必须FP64，也不是所有算子均FP64。W8动态router仍频繁改变top8，W16大幅降低但未消除；当前保守选择性证书导致所有行回退，不能按“稀少重算”设计便宜路由。
2. Falcon完整整数R分支可在当前72步以因果重标完成且零发布状态饱和。它覆盖真实输入归一化、完整投影、持续卷积、全部32head递推和完整4096维消费者，Attention运算和MLP仍在明确切口之外。S16/S32误差接近，不支持仅增加state位宽解决当前数值误差。
3. 完整conv+R checkpoint/续接已独立接收，包含消费者失败后不发布的协议候选。数值正确不等于硬件原子性或模型质量通过。
4. 20配置完整compute条件服务和10对标签零差对照已独立通过。真实部署的时隙差小于0.02%，不足以支持独立R或V/R合宏；不得用旧COPY日历替代完整算术服务。

## 冻结条件和已有成果复用

已核本人GitHub Liangruizhi/182389313、目标origin和写权限，读取最新任务/PR/评论/未合并交接。成员55/63范围不接管；只读复用Issue70权重/真实输入，无新模型或其他机器任务，Phi封存。全部模型、实际张量、数值和服务执行均在本人CPU服务器 node13/node14 的 c96 分区，目录 /public/home/yuzelu/RuizhiLiang/issue72-numeric-closure-20261024，Slurm前缀 lrz-i72-。本机仅源码、小合成测试、元数据整理和传输。其他成员89448/node3未中断。

| 模型 | 固定revision | 本轮范围 | 验收 |
| --- | --- | --- | --- |
| Granite-3.1-3B-A800M-Instruct | a02780686e08a03fe0d2679a293b5c74a90efa89 | 两文本各72token、完整32层路由、full/cached/chunk16及冻结hidden router | 新参考和768整数记录独立接收；整MoE整数链/质量未执行 |
| Falcon-H1-3B-Instruct | 01087ec4c132d7f186908716b3530ea187f062a1 | 原cal16/eval72、layer0完整Mamba2分支，32×128×256状态 | 12数学条件、6连续执行产物独立接收；Attention/MLP切口外 |
| 已有Qwen/Llama/Gemma | 见原Issue59/61/64/66/68 | 只复用原条件与结论 | 不重复下载/整模型实验；原失败与位宽不改写 |

Falcon补采实际shard SHA977e5fada35522cebf1c2a046dcbd52fbe019f5c4ff77c49840d063aaf0cdbd6、4,971,004,584B，与Issue70官方LFS/下载回执一致；本机只核元数据对应，实际hash由服务器producer读取权重计算。Torch2.10CPU / Transformers5.20.2 / NumPy2.2.6既有环境，无新安装。

## Granite：先稳定参考，再比较整数路由

旧门限 relativeL2≤2e-4 且 maxabs≤2e-3 保持。native32 eval chunk16仍FAIL（0.00582334 / 1.182970）；router64仅将FAIL移到cached（0.00582258 / 1.182962），不能说明只提高router精度足够。原grouped_mm不支持Double的90182失败保留；改为显式eager专家backend，并以native32_eager同输入对照核backend替换。

model64显式eager的cal/eval full对cached和chunk16四项均过原门，32层路由集合变化为0，独立接收90203 PASS。框架仍在RMSNorm统计/rsqrt、RoPE及attention softmax强制FP32 cast，故称“model64条件参考”，不是全FP64数学真值或硬件合同。native32_eager仍FAIL，保留原失败。

整数实验冻结上游hidden，不量化专家；四候选为静态/当前row动态power2激活scale×W8A8/W16A16，权重per-output、I16 exponent、RNE对称饱和。实际重新排序40 logits选top8；精确整数tie才按ID。下表分母为32层×3执行profile×72token=6912，存在profile相关性，不当作6912独立样本：

| 评价候选 | top8集合改变/6912 | 可证稳定/6912 | 输入饱和元素 |
| --- | ---: | ---: | ---: |
| 校准静态 W8A8 | 2040（29.51%） | 0 | 0 |
| 当前row动态 W8A8 | 720（10.4167%） | 0 | 0 |
| 校准静态 W16A16 | 9（0.1302%） | 5244 | 0 |
| 当前row动态 W16A16 | 6（0.0868%） | 6249 | 0 |

校准和评价合计192个layer/case/profile、13,824行，选择性W8严格区间证书全部失败，全部付W8后再W16；其中1,359行W16仍未被证书保证，12行改变同输入FP64 top8。证书保守性不等于全部路由实际错误，W16低改变率也不等于已接受的模型质量。

全K1536 W8最坏26 signed bits可INT32；W16需42 signed bits，三位base128×三位共9份S8 dot及宽重组，不能由INT8阵列免费得到。选择性当前合计8,493,465,600 S8 MAC，为全部行先W8再9份宽路由，非稀疏回退。每层W8/W16 router权重61,440/122,880B，均超M32KiB。Q15 gate另需8,196B exp2 LUT、log2e宽乘、精确RNE除法、40个共同宽logit、scale和dispatch元数据。各阶段定义见GRANITE_INTEGER.md；2049个LUT由独立Decimal70核验，768记录和真实改码/LUT/选择/gate负例全部接收90210 PASS。整数gate尚未串入expert输出/merge，不能称完整MoE整数化。

## Falcon：不再用浮点更新冒充整数递推

主合同：矩阵W8A8/完整K INT32；数据和conv历史I32Q12，gamma/MuP/skip I32Q20，dt I32Q20，alpha为可编码2^31的U32Q0.31，状态S16/S32+每head I16 exponent。Q31乘数+I16 exponent静态编译，输入scale仅由当前整数row求得。离线LUT/scale生成与运行时整数分开，边界浮点编码和最终误差统计不隐藏。

完整链为 input RMSNorm → MuP/in_proj → conv4/SiLU → dt/alpha → 全32head state/读出 → gate → 4096维共同RMSNorm → out_proj/MuP → 外部A+residual+R → H2560 pre_ff RMSNorm。state模式从原native projected切入，full模式才包含输入norm/投影；两者分列：

| 模式 | 状态位宽 | 静态饱和诊断：提交/饱和 | 静态guard：提交/72 | 因果重标：提交/饱和/head事件/epoch |
| --- | ---: | --- | ---: | --- |
| state cut | 16 | 72 / 9610 | 1 | 72 / 0 / 50 / 24 |
| state cut | 32 | 72 / 9611 | 1 | 72 / 0 / 50 / 24 |
| full R分支 | 16 | 72 / 9529 | 1 | 72 / 0 / 51 / 25 |
| full R分支 | 32 | 72 / 9535 | 1 | 72 / 0 / 51 / 25 |

全部12条件已独立重算完整stage/state/scale/epoch及事后误差，90211–90222均接收PASS，各3个实际改数值/epoch/unit且重写SHA的负例被拒绝。PASS是接收正确记录，包含静态饱和/提前拒绝的失败行为，不是这些条件成功或质量PASS。旧head0四次sat来自不同FP桥/范围，不能与上述全head新合同直接比较。

full S32重标的局部relativeL2：inputnorm0.0181%、projected2.4868%、scan1.5086%、4096 gatednorm3.1250%、outlinear6.7257%、join3.1516%、nextnorm3.0289%。S16 nextnorm3.0297%，状态存储减半不自动降低计算量或解决误差。无已确认应用质量预算，不把这些数字宣布整模型质量通过。由out_proj误差触发的最小后续分叉只改变A8 K粒度，冻结相同整数gatednorm输入，连带重新对齐/下游误差/元数据成本，不能挑评价样本。

### 必须计入的宽度和存储

dtB先RNE12为I32Q20，再与x乘并按state unit重标；不能合成一次三乘舍入。alpha×state可I64；S32×C32完整N256通用最坏需72 signed bits，当前I64候选用实际保守界guard、超界拒绝，不覆盖全码域。冻结phase13/service元数据的71位是漏计最负码边界的笔误，原artifact不覆盖；全码域应72位，实际I64 guard及本批结论不变，见[勘误](../../project/experiments/closure/ERRATA.md)。norm含U128平方和、除法及isqrt；候选位迭代128/64轮，尚无RTL。宽乘按S8 digit和宽shift/add记账。

单layer完整S32/S16状态4/2MiB，旧态/私有候选/完整I64 proposal、73,728B conv历史和新旧两代、units/epoch/version必须有真实槽位。LUT总4,260,100B、W8权重32,849,920B、矩阵参数67,776B另计；不得塞进V16KiB或以FP32字节除四估计。

### 完整历史与失败恢复

新增逐token分支保留conv历史、R state、units/epoch/version/position私有到完整消费者成功才共同发布。这是当前候选事务协议；并不证明所有Mamba实现必须等待后继norm，解耦提交若有额外队列/信用/回滚可另研。

六个已有/新执行产物覆盖full、chunk8、chunk16、prefill64+逐步decode，并核73个state边界、全部stage码和实体checkpoint。独立接收90224/90226/90227–90230 PASS，各4个SHA重写的state/conv/owner/private-unit负例拒绝。新6c455f6源码的合成late-consumer失败在R私有成功后强制abort，旧branch不漏发布，重试精确恢复；这是软件协议测试，不是RTL证明。

旧批量static_guard的conv_history_final来自全72因果预处理，虽然只提交1个R token，不能将该field当已提交前缀cache；原记录保留，新完整resume才具备共同历史资格。90182和90201（接收端B1 token shape断言错误）失败目录/日志均保留。

## 输出投影的唯一受控粒度分叉

在上述full S32 guard-rescale的同一gatednorm输入上，仅改out_proj A8的K粒度；W8、静态Q31和exponent SHA完全相同，无评价误差拟合。三条件90231–90236实际执行及独立接收PASS，各184,320个宽RQ产品（hi/lo码）、完整K部分和/单位对齐/后继norm核验，各3个SHA重写负例拒绝。whole-row八项逐码重现原baseline。

| A8粒度 | out_linear局部L2 | next_norm局部L2 | 全72步partial wire B | 动态scale wire B |
| --- | ---: | ---: | ---: | ---: |
| 整row K4096 | 6.7257% | 3.0289% | 751104 | 3456 |
| K512（8组） | 4.3136% | 1.8675% | 6008832 | 3456 |
| K256（16组） | 3.9044% | 1.6733% | 12017664 | 4608 |

局部L2改善不构成全面误差支配：K256 out_linear最大绝对误差2.9690高于K512的2.8235；decode nextnorm maxabs由baseline约0.2502升至K256约0.2930。FP参考误差用实值，vs_integer_baseline.max_abs另用Q12码差，不混单位。

完整K先I64对齐/累加，再一次checked I128 Q31乘/RNE；每组提前RQ再相加是另一函数。实际样本最大aligned幅值20/21位、RQ产品51位都可容I64；通用I32输入合同的乘积界约82位，故I128是保守候选能力，不是本样本必须有I128物理乘法器。分组scale按组I16、静态每output 6B，因式分解后不复制G份Q31。上表wire依声明的partial流协议计header/beat，不是不可避免流量下界；output tile/局部对齐可另调度，但必须计缓冲/端口。支持保留M/V mixed-unit归约接口，不能直接据此固定近M重标。

## 同精度、同资源完整compute比较

20个配置均独立接收PASS，各4个真实SHA重写负例（端口、head/unit、norm、RAM）拒绝；10对split/shared label的完整witness SHA、算术/IO/资源/时隙完全相同。source-bound任务要求相同code/unit/epoch/重试轨迹，完整K/32head/4096norm及末提交。压缩loop由独立实现闭式归纳、affine对象范围和mod16余数集合证明物理拍，不靠展开过亿leaf或import producer。此接收不是逐字节内容模拟器或RTL。

库存：M256 16×16但B1仅16有效PE；V/R合计8 S8 lane；单SFU、4,260,100B单128bit 1RW LUT ROM；V16KiB/R32KiB/M32KiB/S8×32KiB、EXT128MiB；各bank 128bit 1RW、单128bit BUS、header32B/beat16B/payload1984B/FIFO2KiB。ROM容量单列，不免费塞进V或既有EXT。VR工作寄存器512B/SFU48B均从aux8KiB扣，未给予额外RAM/端口。

采用保守B1单token串行policy，prefill64也不跨token batch；M输出tile16、Ktile512含权重转置/实际16PE操作。矩阵权重每token重读、全I64 decay/injection/proposal/readout-product各8MiB EXT、全域guard、完整conv/state旧新代、两次clone和失败重试、全部RQ/元数据/ROM请求响应/除法开方计价；不收费observer SHA。入场的常量/LUT/外部encoded cuts已在声明存储就位，setup另计state/history清零和初始units。此不是优化调度或性能下界，不能把条件slot称真实时钟周期。

| 固定精度（wide factor1） | 部署 | 条件slots | 相对同精度R8 | wire B |
| --- | --- | ---: | ---: | ---: |
| S16 | R32KiB D8 | 15815908351 | 基准 | 17650716160 |
| S16 | V16KiB D2 | 15817871039 | +0.012410% | 17674172928 |
| S16 | R32KiB D16 + S spill | 15815596703 | -0.001970% | 17646524416 |
| S32 | R32KiB D8 | 15970826051 | 基准 | 18360320576 |
| S32 | V16KiB D2 | 15972993923 | +0.013574% | 18387060288 |
| S32 | R32KiB D16 + S spill | 15970514403 | -0.001951% | 18356128832 |

R8占R32768B；V2占V14336B；R16占R24576B+S0 32768B，其他库存相同。S16按声明先widen32再算，仅state存储/IO减少，不是S16天生无窄算术收益。EXT S16/S32实际76,905,024/85,293,632B，单layer均合法，不代表全32层可部署。D16 spill轻微更快的反例保留，不能先定R8必胜。

将所有VR字节操作服务成本（包括宽算术、重排/复制、guard和控制；M/SFU/port不缩放）统一乘factor2/4时，S32 R8/V2差异缩至0.007919%/0.004320%；该VR服务成本变化远超当前部署差异；此敏感性未单独隔离某一宽乘的因果贡献。2,365,194,240个矩阵S8 MAC及284,955,136个mul32等三部署完全相同。没有证据由这些微小条件差异推出独立R宏、V/R合宏或真实PPA。新K分组out_proj是另一数值函数，未纳入本whole-row服务，禁止套用本表周期给它排名。

旧pilot 90237是未补norm I128 shift/除法RNE成本的版本，90238接收端把合法4B/8B stride过度限制为16B整倍而FAIL；保留原目录/日志，仅新版90239之后配置入比较。修正后按实际余数证明物理拍，没有放宽容量或接受坏访问。

## 可确定的合同与下一步

- 保留六逻辑模板，固定完整K mixed-unit归约/RQ顺序、完整共享norm/归约barrier、状态owner/unit/epoch/version、guard/重试和共同历史恢复义务。
- Granite精度/回退资源须继续验证；不按已观察expert固定连接，不把W8集合改变直接等同质量失败，亦不称W16已质量通过。完整MoE整数gate→expert down/merge尚未闭合。
- 当前Falcon bounded R分支整数数学/连续性闭合；模型Attention/MLP、完整应用质量、长序列稳定性和全码域宽度均未验收。
- M/V/R/S物理宏归属保持候选。优先校准真实宽算术/SFU/ROM及同精度grouped-RQ微实现，再联合合法M预填批处理和state分页重新比较；不再盲加模型。
- 物理工具/库/工艺资格由相关工程任务接续，不接管成员55/63，不把普通分层或抽象时隙当PPA。

## 归档、实际验证与交付

[统一索引](../../project/experiments/closure/results/issue-72/index.json)含逐phase源commit/SHA、实际Slurm和接收路径。103个本人服务器作业：100 COMPLETED，3 FAIL保留（90182 Double kernel、90201 token shape、90238 stride checker）；另一次Slurm依赖提交拒绝无job，检查20份已完成接收后无依赖重新提交90280成功。

完整包9,898,974,561B/1096成员仅授权服务器：/public/home/yuzelu/RuizhiLiang/issue72-numeric-closure-20261024/delivery01/full-results.zip，SHA-256 80e0b598039256f576bc6280d1f677713df5d5b36b8ff8ec1e22f35ee7c60197。精选2,480,138B/286成员在仓库（metadata-only），SHA 165d57d6050e0ef0e8775d7d081175d35e8bb85fffcc163db3f08d6bb547c883。两包在服务器逐成员字节验收，精选在本机再次逐成员验收；这不替代独立服务器数学。43个phase源blob逐一对原Git commit SHA通过。完整包含执行产物/负例和归档前日志；collector/验包后续收据另在统一索引，不伪称在自身快照内。原Issue70数据/权重属明确外部输入，解包本批不能省略其SHA复核。

本机90项新边界测试、80项原architecture_extensions回归、python -B scripts/check_project.py及git diff --check通过。没有本机模型/真实张量数学或其他机器任务。命令、接收与恢复详见[交接](../handoffs/2026-10-24-issue-72-numeric-closure.md)和closure/README.md。

本地与服务器成果已整理，使用同一PR73交付待审查合并，不自行合并或提前done。登记management-hub PR5 pending；无board.json/Projects能力，看板unverified、同步pending待管理员；审查人待指定。以上是架构合同进一步收敛，物理宏与端到端收益尚未定稿。
