# W5-IF v0.1：八样本的粗端点边界审计

输入计划提交`f9a90c845504b198cc3265106e03c67902382ebb`；读取`control-boundary-714cab4/integrated`的FamilySpec、永久绑定表、六配置、172角色合同与三层互联计划。本文只提出有限家族合同需求和协议可实现性审阅，不新增RTL、unit tests、仿真、远程状态或物理结论。机器表及选定输入SHA见[机器模型审计](../work/Melodydt/151/w5-if-family-audit.json)。

## 1. 可以共同冻结什么

六个完整子层配置的主数据边界都是`[B,Sq,H]` hidden张量：A_plain/A_gate/D/H输出包含对应mixer的规定postNorm/尺度及第一次残差，F/X输出包含第二次残差。这个**逻辑边界**已能从八样本源图确定，但完整hidden张量的整数位宽、Fin、布局和误差预算还没有统一接收。源图实际导出是B1/S2/FP32/no-cache，不是S16、decode、所有prefill或完整模型已验收。

因此v0.1可确定数据保活、真正stored ACK、分片/tail、release、任务完成与错误/partial等语义；不能把A8/F8出口的8个S16 Fin10推广成所有产品hidden均为Q10。A8入口是Q/K/V小张量，不含完整hidden→QKV/cache；F8入口还含x与三份小权重，投影输入为S8 Fin7；两者并非现成可裸接的完整hidden端点。

产品选择/程序/格式和布局尽量由预制有限程序与M11/M12永久绑定确定，**不要求每包携带通用role、dtype/Fin、shape或大型handle**。能否省略某字段仍需编译证明：实际count、源占用、未完成消费者、late-response排空/代际及动态MoE ID不能因为静态算法图而消失。完整八产品程序必须在共同有源底座冻结前接收；不能给未知模型自动兼容，也不能以每产品重综合控制器替代共同底座。

## 2. 八模型真实hidden与分片口径

下表S16只是容量算例，未冻结为产品整数格式；word为128bit payload字。I是内部FFN维度，不能用H替代。

| 样本 | H | I | 完整子层组合 | 单token假设S16字节/word |
|---|---:|---:|---|---:|
| Qwen2.5 | 2048 | 11008 | A_plain→F | 4096 / 256 |
| Qwen3 | 1024 | 3072 | A_plain(Q/K Norm)→F | 2048 / 128 |
| Llama重建图 | 2048 | 8192 | A_plain→F | 4096 / 256 |
| Gemma local/global | 2560 | 10240 | A_plain→F，保留额外Norm | 5120 / 320 |
| Phi | 3072 | 8192 | A_plain→F，融合/部分RoPE | 6144 / 384 |
| Qwen3.5 | 2560 | 9216 | [D→F,D→F,D→F,A_gate→F]×8 | 5120 / 320 |
| Granite | 1536 | 512/专家 | A_plain→X，40选8 | 3072 / 192 |
| Falcon | 2560 | 6144 | H→F | 5120 / 320 |

Llama图为配置重建/随机参数，不能称原checkpoint资格；Granite保留图册Granite-3.3B别名与实际Granite-3.1-3B-A800M名称边界。八模型共十种decoder层型，不包括embedding、finalNorm、LM head、sampling、MTP或多模态外围。

最大观察H=3072。在**B1、一个token、S16、纯payload**条件下，6144B恰好等于T的384×128bit容量；native T自身owner/generation等元数据在payload外。若协议OFFER额外一拍在外侧解析、不写入T，该拍不应占这384字；若实现把header也存进T，容量必须重新计算。即使纯payload恰好fit，也不能推出有第二缓冲、接收与计算重叠或完整工作集可驻留。

prefill必须按`B*Sq*H*元素字节`计算。Phi B1/Sq2/S16 hidden为12288B，至少两个T payload批；FP32源的一行也为12288B，不能用6144B作为统一frame上限。source max_position_embeddings只是源配置位置范围，不是已接收的B/Sq/context上限；所有产品的硬件准入上限仍待绑定。

## 3. 已明确通用边界／按profile扩展／具体未知

| 主题 | 已明确通用边界 | 按profile扩展 | 具体未知／未准入 |
|---|---|---|---|
| 主数据 | 完整子层hidden输入/输出，包含源图规定残差 | A/D/H第一次残差；F/X第二次；各自postNorm/尺度 | 完整hidden整数位宽/Fin、质量、精确布局、B/Sq范围 |
| 任务与供参 | 有限程序、永久产品入口；数据装载不是bootload控制程序 | 权重、gamma/epsilon、RoPE/mask、状态系数、expert供给 | 参数实际位置、地址/服务、完整ROM及全部产品lowering |
| 生命周期 | accepted、stored ACK、source-release、taskdone分离 | KV、R状态/history、MoE rank归并、MEM持久可见 | 接收预约、缓冲容量、late/duplicate隔离及具体事件编码 |
| 运行时量 | tensor内容和已准入长度/position、在途phase状态 | 动态expert ID/rank；KV/R版本；MEM必要身份 | 最小字段位宽、可省略标签的完整证明 |
| 错误／状态 | 原生命令完成不是粗任务完成，error与sat不同 | R不可撤销commit及root发布；H双支join；X全rank；MEM partial | 扩展编码和实现；reserved opcode不自动提供能力 |
| 物理 | 有源CTRL/MUX/适配/buffer/clock/reset须预制 | 声明路线、fork/join/feedback和独立确认回路 | bus/pin宽度与数量、层/时序、额外存储；未冻结全连接网 |

### 六个profile需要什么

| profile | 数据与参数 | 状态／事件扩展 | 必须保留的边界 |
|---|---|---|---|
| A_plain | hidden、QKV/Wo、RMS/RMS0、源bias/尺度、位置/RoPE、mask/window | 准入缓存模式下KV读写/可见性、长score/EXP重放 | Q宽不一定等于H；Qwen3/Gemma头Norm、Phi部分RoPE、GemmapostNorm不能移除 |
| A_gate | A能力加Qwen3.5 gate/context配对及gate参数 | 完整profile内部应关闭门乘配对；KV仍需独立可见性 | PV后、Wo前Sigmoid门乘；G gated/ungated Sigmoid尺度不同，不能据fn推通用hidden格式 |
| F | hidden、gate/up/down或融合参数、Norm、激活/源MuP/尺度 | 残差保活、gate/up配对、全I mid保存及down累加、参数供给 | GemmaGELU/postNorm、FalconSiLU前MuP与原残差；完整F不是MoE专家核 |
| D | H2560 hidden、qkv/z/beta/a/Wout、conv taps、Norm/L2/系数 | old/next GDN/history、候选保存、本地commit不可取消窗口、整root存储/发布或partial | 源图Repeat16→32后L2、Q独立缩放；每head RMS后再SiLUZ门；L2 epsilon仍未知 |
| H | H2560 hidden、共享inputNorm、Attention/SSM参数、MuP/bias/coefficients | 同token双支到齐、KV+SSM/history的发布/partial、R多tile | H默认完整混合子层；不能直接拆两个普通完整A/SSM岛。SSM先门乘再4096 RMS |
| X | H1536 hidden、router及40专家、Norm、gain及公共数值单位 | selected ID/rank、实际专家数据就绪、8rank到齐、宽merge、partial/error | TopK只ID仍须selected-score gather；动态ID不能编译掉；专家分布到别岛需新增expert内部合同，不裸调完整F |

D/H/X当前只能记录扩展需求，不能称全部profile都已可接收。A_plain/A_gate/F的完整尺寸及数值/存储lowering同样未接收；已有有限切片证明不得变成全profile admission。RMS0是源算法语义，不是凭名称就多出一个native N模式；其gamma有效值与整数epsilon仍需静态配方和独立数值接收。机器表用原角色UID追溯INPUT/WEIGHTS/GAMMA/CONSTANTS/OUTPUT_DRAIN、KV/state及专家供给，没有把172角色改作172条同时执行程序或实现率。

## 4. 不能由hidden宽度推导内部能力

- Ncontroller当前count≤257、word_index/words_hold为6bit、最大使用33字；H3072需384字，Falcon内部4096 Norm需512字，不能仅放宽count guard就扩成完整Norm控制。native N统计总数16bit/65535也不能直接处理任意源配置长context，须限定准入或独立证明新分段算法。
- H3072的S16原值、gamma、目的各6144B，三份相离区域共18432B，超过S16KiB。T能装一行不等于N三数组能驻留。H2560虽三份15360B，也没有因此解决其余工作区、权重和prefill。
- Qwen2.5 I11008的S16 mid为22016B；Qwen3.5组合Q/gate8192为16384B，已占整个S；Falcon SSM投影8736为17472B。实际布局、下游回放和单M上下文不能靠H≤3072规避。
- D/H完整state在候选S32或源FP32四字节口径下分别为B1的2MiB/4MiB；若采用完整old/privateNext双版本方案，再按双份并另加history估算。具体版本存储/发布策略仍待接收，不能把现有R tile/COPY当整个state容量或原子提交。MoE八专家回传/宽加权累计同样不由hidden一行容量覆盖。
- 权重/系数/位置/mask和KV/state供给可以走预制MEM或参数服务，但这些数据来源必须真实存在；主hidden端点不隐含MEM、NUM或PHY已实现。具体服务、地址域、带宽和持久ACK仍是扩展缺口。

参数供给可按已接收计划流式进行。任务准入要求的是其声明版本在真实可达存储中成立、供给路径能进展且局部chunk有预约，不能误解为全部矩阵/40专家必须先驻本地S，或全部参数必须跟在hidden帧内。B8 COPY示例不包含这套参数供给能力。

## 5. 对协议候选的独立实现审阅

协议作者当前提出CMD/EVT各64bit候选、128bit payload+last/5bit validbytes、同流首拍40bit OFFER且validbytes=0、独立ACK64、CLOSE走CMD。首个算例COPY_H8_S16_FIN10只有一字16B，不是完整hidden固定Q10。具体字段与物理pin仍是候选，不能因可编码就称已冻结。

最终三件套已明确：OFFER只在EXPECT_HEADER阶段解析为控制，不写nativeT payload、不作为空tensor；EXPECT_PAYLOAD再次收到validbytes=0的header属于phasefault，不能丢弃后假装重同步。线上的header+payload共两拍，而nativeT只存一字payload。插入/解析、保持与反压选择需要预制TX/RX有源逻辑，M11/M12不能补。STORED_ACK只在真正payload写ACK后发出，目的RX槽提前预约，source最后释放/CLOSE要与全部消费者义务一致。

一个active任务、一个RX槽和全局一个在途fragment是W2有界候选，不能自动推广到全家族存储或无死锁。若producer等待T release才能JOB_DONE，而母控等producer JOB_DONE才启动consumer，即有资源等待环；应让RX预约、ACK/事件排空独立于local RUN和母控WAIT，或使用已证明的中转存储。普通data的顺序完成不能替代D/H root、H双支或X rank的扩展完成条件。

已读取最终`protocol/contract.md`、[通道及候选编码](../work/Melodydt/151/w5-if-protocol-channels.json)与[因果时序例](../work/Melodydt/151/w5-if-example-traces.json)：六组trace覆盖成功、有限背压、重复header phasefault、写ACK待回时失败/partial、严格prestart取消、命令拒绝。CMD传输接受不等于任务准入或RUN；CMD_REJECT必须使用被拒CMD自身的key，不可误结算active task；TASK_PUBLISH/OUTPUT_PUBLISHED在B8均保留且不支持。失败ACK不会被当作REMOTE_STORED/正常CLOSE，既有写不能回滚。JSON中CMD/EVT/ACK为64bit候选，effective分别53/48/46bit，OFFER40bit，各字段位表无重叠且填满各自载体；候选编码与文档、trace语义一致，未发现family级阻断。

以上只构成文档语义、字段和容量的一致性审阅；没有新增单元测试，也没有RTL/服务器执行、活性证明或物理验收。v0.1具体示例仅SOURCE_COPY_H8/SINK_READ_H8，不是把原八模型H缩成8；当前没有任何完整A_plain/A_gate/F/D/H/X因此获得receive admission。所有产品完整程序、运行时边界、缓冲和有源能力必须在底座冻结前被接受，M11只永久选择已有端点/程序/参数与被动路线。协议三件套的本地SHA记录在机器审计文件，区别于f9a90c8既有来源锁。
