# Issue70：小MoE与并行Attention/SSM最小实验

2026-10-24 UTC+08；Liangruizhi；Issue70，承接PR69@ab2edaa。先冻结下表，再运行真实模型；实际结果与未通过项见后文，不预写成功。用户仅授权新增Granite与Falcon两模型，Phi封存，成员Issue55/63不接管。

| 决策 | 真实差异/候选 | 最小实验与观测 | 分叉标准 |
| --- | --- | --- | --- |
| G1 路由/专家是否固定连线 | Granite40专家top8，非dense | B1 pre64/decode8，一层完整MoE；W8A8 router重新top8与FP固定路由诊断分列 | 路由会变则保留动态索引/dispatch，固定连接不能只覆盖所见专家 |
| G2 RQ/合并归属 | 8expert down输出单位不同 | 完整K整数dot、两激活scale、共同S32+Q31重标/Q15权重/S64合并 | 不同unit禁止直接INT32相加；宽乘/归约及metadata是资源义务，位置待同资源校准 |
| G3 S/分发缓存 | 稀疏专家集/访问偏斜 | actual routes/shape；独有权重下界与无复用访问量分列；48KiB S32 return与S64acc容量 | V16KiB整物化不可行则tile/stream/显式S，不能赠缓存或以unique bytes冒充带宽 |
| F1 R模板泛化 | Falcon Mamba2与GDN更新不同 | 一个完整hybrid层真实连续输入；FP64 recurrence，S16/S32状态存储诊断 | 不把FP桥候选称整数R；R控制微序列/共享B-C组需显式，完整head超32KiB则分页 |
| F2 跨head消费者 | gate后4096共同RMSNorm | raw scan/gate/gamma与完整归约，存储/重读下界 | 不能各head单独norm后拼接；V16KiB无法整48KiB免费驻留 |
| F3 A/R并行归属 | 同输入分叉、两支汇合、KV增长/SSM固定态 | pre64/decode8、原生chunks1/8/16连续，真实branches/cache；相同wire资源账本/合法传输 | CPU执行顺序非目标并发收益；未过数值门仅结构诊断，宏归属/PPA仍待真实端点 |

Granite官方revision a02780686e08a03fe0d2679a293b5c74a90efa89；Falcon 01087ec4c132d7f186908716b3530ea187f062a1。官方API原字节metadata和SHA在work/Liangruizhi/70/models；服务器网络失败后以本机D盘中转，服务器复核；以LFS SHA/小Git blob核字节并读取safetensors header dtype，不依赖配置推测权重精度。各阶段源码/输入/output SHA及实际实现另冻结。来源为官方模型卡/config与安装Transformers5.20.2，动态main网页不代替固定源。

Granite固定seed20261024、独立cal/eval文本，pre64+teacherforced decode8，数值只取4prefill尾+4decode，共8token完整8expert路径。2激活scale×2路由×2阶段=8个观测；FP64SiLU/softmax、scale编译桥保留。参考一致性预定relativeL2≤2e-4/maxabs≤2e-3，两者均须满足；并非模型质量阈值。

Falcon固定seed7002，独立16校准token及72评价token，pre64+decode8，只一个完整层细采。参考门预定：full/cached最终logits、layer0 chunks outputs/cache relativeL2≤2e-4且maxabs≤1e-2；hybrid join≤2e-6/1e-3；独立FP64 head state/y≤2e-4/1e-3。每项原始误差保留，不事后放宽。S16/S32 storage只作诊断，FP64系数/更新不称真正整数递推，不跨模型移用Issue68同范围S32结论。

所有实际模型/数值与服务均本人CPU服务器新issue70-moe-hybrid-20261024目录Slurm lrz-i70-*，独立out不覆盖，原权重只读复用。启动前只读盘点c96有1344空闲核，node13空闲且约503GB free；其他成员89448/node3未动，两个模型未发现已有目录。每模型先8CPU参考，并行上限不超实际申请；不安装新环境或启动其他机器。

同资源部分仅对相同声明精度/任务比较容量、打包和端口/传输，不把FP桥路径称全整数，也不把有界传输当完整compute。维持V16KiB/R32KiB/M32KiB/S8×32KiB、1RW128bit、32Bheader/16Bbeat、payload1984/FIFO2KiB；宽算术若未校准只列义务/拒绝/条件成本。出现无法实现的候选须明确拒绝。

至少双轮或独立接收；独立Python整数dot/RNE/merge和FP64 recurrence，原始SHA与真实篡改负例分层。大数据与权重留授权服务器，仓库只放精选、结构化指标、源码、命令、日志、版本和SHA索引。登记PR5 pending，看板unverified/同步pending待管理员，审查人待指定；未审查合并非done。

## 执行日志：来源与传输

首轮服务器90152/90153下载失败（URLError，登录节点官方及镜像metadata连接超时），原始失败保留。依赖90154/90155未执行，核对本人job后取消，以新任务替代。未改变TLS或系统网络配置。2026-10-24约15:10 UTC+08，本机D盘官方固定版本下载完成：Granite 6,602,372,644B、Falcon 6,304,067,182B（含配置/tokenizer）；四个BF16权重分片均与官方LFS SHA256一致，小文件与官方Git blob匹配。仅传输中转，未在本机加载模型；新server models-relay目录将再经Slurm复核，之后只读使用。ModelScope公开镜像完成元数据/HEAD备用调查但未采用，不能称其字节已验收。

源码生产/独立接收/传输共59项边界测试通过，check_project通过；这不是实际模型数值验收。传输审计已补Falcon先gate后norm的首扫gate及三输入residual+A+R汇合，避免少计通信。实际结果、Slurm和SHA后续追加，不覆盖原失败。

## 服务器实际结果与验收

本批模型加载、实际张量数学、COPY/端口实验及接收均在授权CPU服务器node13执行；本机仅D盘下载、官方SHA核验、中转和小合成测试。原始BF16权重转CPU FP32作参考，不称BF16内核运行。框架使用记录的PyTorch Mamba参考回退，无GPU测量。原始数据、逐phase源码/命令、精选包及SHA入口见[统一索引](../../project/experiments/architecture_extensions/results/issue-70/index.json)。

| 模型 | 实际最小集 | 验收与边界 |
| --- | --- | --- |
| Granite-3.1-3B-A800M-Instruct | B1 pre64/decode8；完整layer0 40选8 MoE；8评价token，2激活scale×2路由×2阶段；4profile全32层chunk归因 | 原捕获FAIL：唯一eval chunk16未过门。局部32完整K dot、32 RQ、4完整8×1536合并独立数学通过，保持PARTIAL_DIAGNOSTIC；全层归因见证独立核验。不称整图参考/质量通过 |
| Falcon-H1-3B-Instruct | B1 cal16/eval72，pre64/decode8；完整hybrid层、native chunk1/8/16；head0完整D128×N256；16分层投影输出 | FP32 native/FP64参考23项原门及独立重算/篡改负例通过。S16/S32仅FP64更新下的整数状态存储，均4次饱和；不称全整数R或应用质量通过 |
| 同资源端口 | Granite8、Falcon16个完整COPY/PORT-IO配置，各双轮 | 两套科学artifact SHA一致；独立核全部字节、地址、逐访问128bit物理拍、端口/FIFO、完整消费者依赖及真实篡改负例。Granite继续PARTIAL；未含算术、完整权重/KV操作，非E2E或PPA |

### Granite：动态路由与公共单位

评价cached对full relative L2=5.8339e-7、maxabs=2.8104e-5，完整layer0 MoE重放6.66e-8/4.77e-7；eval chunk16却达0.00582334/1.18297，超过原2e-4/2e-3双门。没有删chunk、换输入或放宽阈值。诊断完整重现：首路由集合变化在零基layer13/token42，第8/9分数差2.9802e-8，小于logit扰动1.8179e-6，专家7换成1；累计10个layer-token集合变化。固定full专家ID、仍用当前logit重新softmax的反事实控制使误差回落到5.9657e-7/3.0518e-5，支持离散路由放大解释；不能证明具体kernel根因或替代原生参考。独立接收128个profile-layer及LM误差、top8/margin/原capture回链通过，原FAIL保留。

失败后显式收窄局部诊断：仅当校准/评价cached、完整MoE重放及校准chunk均过原门，唯一评价chunk失败，才允许诊断开关；默认仍拒绝。numeric与transport透传FAIL，COPY或整数数学通过不升级参考资格。

| layer0实际重算路由 | prefill局部relative L2 | decode局部relative L2 | 路由/饱和 |
| --- | ---: | ---: | --- |
| 动态row A8 | 4.5003% | 5.2063% | 本8token集合0变；input/mid/RQ/merge饱和0 |
| 校准tensor A8 | 9.8067% | 11.1028% | 4个prefill token中1个换专家；饱和0 |

这是软件整数dot＋浮点非线性/scale桥，非应用质量门；layer0小样本稳定不能否定layer13敏感性。共同power2 S32、Q31乘子/INT16 shift、uint16 Q0.15权重和受检S64合并相对各自FP桥额外relative L2约3.4e-5–4.7e-5，不能忽略总量化误差。K1536/512的S8×S8全K dot最坏绝对界24,774,144/8,258,048，可INT32；宽重标/门乘/求和另计，目标宽算术未实现。

8专家S32输出49,152B不能整放V16KiB；S64全向量累加12,288B加一份S32输出6,144B也超V。tile256/512账本4,706/9,314B仅通过容量。一个完整专家W8=2,359,296B，不能免费驻M32KiB。朴素逐坐标Q31/shift参数73,728B/token大于输出49,152B；参数因式分解/epoch驻留是后续候选，不把此朴素协议称不可避免的下界。当前多跳COPY逻辑252,002B、wire258,384B/token；调度60,260–69,599声明服务时隙为搬运义务，不是MoE延时。相同调度单bank/轮转布局无差异，不能外推真实bank无价值。

### Falcon：参数化R与跨head消费者

full/cached末logits误差1.2343e-6/1.5259e-5，完整层chunk1/8/16及四类cache、FP64 head状态/输出、hybrid join共23项原门经独立接收通过。每8步清状态反例输出relative L2=16.8128%，不能把短窗重置当连续推理。owner/position/version/epoch描述符只是分析合同，非原生硬件epoch证明。

cal16固定unit：S16=2^-12、S32=2^-28，范围均约[-8,8)，72步均4次饱和；输出relative L2=0.606194%/0.606038%，maxabs约7.033。S32最终state relative L2仅3.5885e-6也不能掩盖中途输出误差。FP64 softplus/exp/conv/SiLU、系数乘及状态更新仍在，未做Mamba2因果重定标，不继承Qwen GDN逐位结论。

投影W8A8（K2560、选16输出）静态/动态row误差2.7194%/1.7483%，激活饱和3/0，最坏INT32界41,290,240。它未串入后续MuP/conv/state/gatednorm，不能拼称“W8A8＋S32完整链0.606%”。原report scale字节硬按size×8有误：接收实际静态FP64数组576B/唯一8B；动态FP32数组288B，明确选FP64才576B。原report/NPZ/SHA保持，修正代码和[errata](../../project/experiments/architecture_extensions/FALCON_ERRATA.md)独立记录；这些为见证元素payload，不含NPY/ZIP头，也不是目标scale格式。

单head128×256：FP32=128KiB、S16=64KiB，均超R32KiB。旧D16×完整N256的S32 old/new已占满32KiB，没aux；本轮FP32 D8/S16 D16分页各保留old/new8KiB+aux8KiB，共24KiB，仅证容量与COPY义务。完整32层FP32状态单独128MiB，加实际conv/KV72/owner为141,296,384B，超过旧EXT128MiB。S16单代总74,189,568B仅通过容量，不含全部shadow/权重，且数值仍有饱和。

gate后4096维单group RMSNorm跨32head完整归约，不能各head独立norm再拼。raw/gate/gamma三面48KiB，含输出/reduce共65,544B超V16KiB。当前不物化pre-gated向量的双扫源/输出逻辑98,304B；residual+A+R三读一写40,960B，完整驻留含descriptor41,024B也超V。tile256/512可分块但完整归约barrier不能删。实际多跳norm/join COPY payload251,968B、wire259,872B，未含完整消费者算术。FP32 state copy与S16 candidate分列，不以2倍字节差作同精度划分收益。

### 对划分的收敛与剩余分叉

保留M/V/A/R/S/D六逻辑模板，不新增每expert专属Block或每head独立norm硬件。

- 制造前需支持：M受检全K累加和partial/complete标记；V或受限控制单元的topk/dispatch、unit对齐和宽merge服务；R参数化二维state tile、连续history、range/owner/epoch和受控提交；S单口与有限FIFO仲裁。具体算术/端口数量仍需RTL/实现成本资格。
- 必须保留的跨Block接口：动态expert ID/gather/scatter、scale粒度和生命周期；R→V完整gatednorm分组/完成事件；residual+A+R同token同版本三输入join。
- 留产品确定：expert权重的S分布/dispatch路径、M/V的RQ和merge归属、V/R共享与否、state backing与多跳。参数缓存、复制、广播均付库存和epoch成本。
- 尚未冻结：独立R宏、V/R合宏、近M RQ、精确tile、片外容量/带宽与E2E收益。本批是约束/反例收敛，未给全整数消费者链、长上下文质量或PPA证明。

真正剩余的是Granite高精度路由/稳定性合同与完整质量、RQ参数因式分解/驻留；Falcon因果range/重定标及W8→MuP→conv→state→完整gatednorm链；还有同算术资源下真实端点/布局时序。列为后续候选，不重复下载或扩大模型矩阵。本次最小集已执行，阴性结果保留；Issue70/PR71待审查合并，非done。
