# 八样本驱动的粗粒度 Block 划分研究

研究源固定 `1cc43a93a0c985587745ceba5e0d8d425d43a843`，叶宏参考 `707878621b2add4ed218b8c43df2e95c9a56e2ba`，Issue151/PR152，负责人 Melodydt。本子任务只生成文档与机器映射，不改 RTL、不启动仿真或服务器、不接管 Issue153。

建议把**五种逻辑子层 profile**作为母控调度边界：A=完整 Attention 子层，F=完整 Dense FFN 子层，D=GDN mixer，H=Falcon Attention+SSM 混合 mixer，X=完整 MoE 子层。LINEAR/MST、Attention core、SSM branch、Router/Expert/Merge 是可复用的内部核及验证子程序，默认不再增加第六、第七种物理大 Block 类型。

主物理解释保持用户提出的“每个大 Block 内七类小宏配齐”：每个物理包装具有 M/N/E/G/R/S/T、本地控制和预制内部路线/适配。A/F/D/H/X 是该包装永久允许的功能 profile，不等于五个必须各自独占的物理实例，也不等于八个模型各设计一个专用 Block。同一包装若已预制并接收相应程序，可以时分执行多个 profile/多个逻辑层。控制器、MUX、FIFO、格式/布局、缺失数值能力不能靠 M11/M12 连接金属凭空产生。

## 1. 源事实与真实层序列

以下数值直接继承 FamilySpec/config；I 是 dense FFN 宽度，Granite I512 是**每个专家**宽度。D 按源配置/图表读取，不用 H/Qheads 反推。源位置上限32768..262144保留，但不是本硬件已接收的 context，也不是本轮小图验证长度。

| 模型 | H / I | Q头/KV头 / D | 层数与实际层序列 | 本建议的两步子层组合 |
|---|---|---|---|---|
| Qwen2.5-3B | 2048 / 11008 | 16/2 /128 | 全局 attention×36 | A(q25)→F(SiLU) |
| Qwen3-0.6B | 1024 /3072 | 16/8 /128；Q宽2048 | Q/K RMS attention×28 | A(qkRMS)→F(SiLU) |
| Llama-3.2-1B 图配置 | 2048 /8192 | 32/8 /64 | 全局 attention×16 | A(llama)→F(SiLU) |
| Gemma-3-4B text | 2560 /10240 | 8/4 /256；Q宽2048 | `[L,L,L,L,L,G]×5+[L,L,L,L]`；29局部/5全局，G的零基层号5/11/17/23/29 | A(local/global, RMS0)→F(GELU_tanh, postNorm) |
| Phi-4-mini | 3072 /8192 | 24/8 /128 | 融合QKV/部分RoPE层×32 | A(fused/partial)→F(fused gate_up) |
| Qwen3.5-4B text | 2560 /9216 | 全局16/4 /256；Q宽4096 | `[D,D,D,A]×8`，24GDN/8全局attention | D→F 或 A(q_gate)→F |
| Granite 样本 | 1536 /每专家512 | 24/8 /64 | GQA+top8 MoE层×32 | A(gain0.22)→X(top8) |
| Falcon-H1-3B | 2560 /6144 | attention10/2 /128；Q宽1280 | attention+SSM同层混合×32 | H→F(MuP) |

全242个源逻辑层的完整零基层表及其每层两步映射保存在 `coarse-model-map.json/model_rows`，不是仅保存上述压缩表达。按该定义静态展开为 A186次、D24次、H32次、F210次、X32次，共484个**逻辑子层调用**；此计数不是物理实例、native命令数、ROM字数、吞吐量或时延。

模型身份也不合并：Llama 的源证据是文档配置重建/随机参数，没有原检查点；Granite 图册别名Granite-3.3B与报告的Granite-3.1-3B-A800M-Instruct须绑定具体config/权重。有限八样本不意味着未知模型自动可用。

源证据：[配置/层型总表](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L31)、[FamilySpec](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/work/Melodydt/151/family-spec.json)、[永久绑定合同](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/work/Melodydt/151/family-binding-contract.json)。三份正式原图说明在1cc与原39bd的blob相同；本研究保留旧source-index及原始配置固定链接，不把旧导出重新标为本轮实验。

## 2. 五个 profile 的确切大输入/大输出

符号 X 是层输入，Y 是第一处残差之后，O 是第二处残差之后；均为 `[B,Sq,H]`。权重、Norm/位置参数及KV/state/history是独立的数据/状态依赖，不能因只画激活主线就删除。profile只定义功能与所有权，不冻结本轮未研究的外存引脚/调度。

| profile | 大输入→大输出 | 必须内收的工作 | 源图中不能跨错的边界 |
|---|---|---|---|
| A | X→Y，加KV版本依赖 | 输入Norm、QKV及bias、Q/K Norm、RoPE/布局/GQA、KV可见性、QK/Softmax/PV、可选输出门、Wo、post-attn Norm/gain、residual1 | Gemma post-attn RMS0在Wo后且在Add(X,·)前；Qwen3.5 Gate在PV后且在Wo前；Granite gain在residual前 |
| F | Y→O | pre-FFN Norm、gate/up融合或独立投影、源激活和门乘、完整I的down投影、post-FFN Norm/gain、residual2 | Gemma的post-FFN RMS0在down后/Add(Y,·)前；Falcon gate MuP在SiLU前，output MuP在down后 |
| D | X+旧GDN状态/history→Y+next候选 | RMS0、四路投影、卷积/SiLU、QK重复/L2/Q缩放、beta/decay、全状态递推、每value-head RMS、Z门、Wout、residual1 | **RMS128每head后才乘SiLU(Z)**；没有Softmax/RoPE；全组版本发布不能等同单R tile commit |
| H | X+KV/旧SSM状态/history→Y+next候选 | 共享input RMS、attention与SSM两路、各自MuP/输出scale、同token join、residual1 | **SiLU(Z)门乘后才做跨4096 RMS**；先Add(attention,SSM)，再Add(X,mixed)；不把两个分支各做独立输入Norm |
| X | Y→O，加动态IDs/专家数据依赖 | 一次pre-MoE RMS、router40、TopK8/selected-logit gather、Softmax8、8专家循环、宽加权归并/gain、residual2 | native TopK只ID，不能冒充selected logits/概率；专家内部不新增Norm；0.22在归并后/residual前 |

这样 A/D/H 自己保存第一条残差 X，F/X 自己保存第二条残差 Y，母控不需要在两个小叶宏间编排每一包。跨不同物理大 Block 时主要激活边界是 Y；同一包装复用时 Y可本地保留，但真实容量/保活/地址和错误处理仍要落实。大 Block 边界没有把score/EXP/QKV/FFN中间I的完整物化义务变成不存在。

## 3. 十层型的差异，如何保留在本地 profile

### A 的七种实例绑定

Qwen2.5：A内普通input RMS2048，三路Q/K/V线性投影各自带bias，bias必须在后续RoPE等变换前；无Q/K头Norm。F内普通pre-FFN RMS2048与SiLU门控。不是将三个bias移到最终残差。[源图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L48)

Qwen3：A内input RMS1024，Q投影2048/K和V各1024；Q按16组128、K按8组128做普通RMS，再RoPE。F内pre-FFN RMS1024；不能把Q宽改成H或把Q/K Norm折到一次hidden Norm。[源图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L86)

Llama：A内input RMS2048，无Q/K头Norm，全64通道RoPE；Llama3频率规则属于位置cos/sin来源，层内旋转拓扑相同不能证明频率可共用。F内pre-FFN RMS2048。该配置图不继承真实检查点整模型质量。[源图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L120)

Gemma局部与全局：A各包含input RMS0(H2560)、Q RMS0(8×256)、K RMS0(4×256)、Wo之后的post-attention RMS0(H2560)，共四个源site；F包含pre-FFN RMS0和down之后的post-FFN RMS0，共两个源site。RMS0是gamma=1+weight的参数语义，不是新建/强改普通RMS模式。A局部只访问causal window1024，theta10000；A全局使用全前缀，theta1000000/linear factor8。F为GELU_tanh门而非SiLU。相同小图节点数不证明真实长上下文存储成本相同。[源图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L154)

Phi：A中的一次融合QKV输出5120，必须拆为Q3072/K1024/V1024；它不是三路相加。无QK头Norm，RoPE96/128、其余32旁路，保留LongRoPE48个频率因子来源。F中融合gate_up输出16384再拆8192/8192。物理M可分tile执行，但必须证明它实现原拼接/split及已接收舍入语义。[源图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L231)

Qwen3.5全局：A内input RMS0与Q/K head RMS0，Q_gate总宽8192必须先按16个头各512，再每头拆Q256/Gate256；Q宽4096，不是2560。K/V各1024；Q/K只旋转64/256，剩192旁路。Sigmoid门乘在PV形成4096 context后/Wo前，不能搬到QK分数前。F内pre-FFN RMS0与普通SiLU门控。[源图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L276)

Granite：A内attention score固定乘0.015625，不能替换为默认1/sqrt64；Wo之后乘0.22再residual1。第一处input RMS留在A；第二处pre-FFN RMS归X，专家循环不额外做一次Norm。[源图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L408)

### D：Qwen3.5 GDN

GDN投影qkv8192=Q2048+K2048+V4096，另有Z4096、beta32、a32。qkv通路先8192通道k4因果深度卷积（无bias）再SiLU/split。16个key/query头对应32个value头，轴布局证据支持 `key_head=floor(value_head/2)`。实际ONNX是Repeat16→32再L2，每组128；文字图折叠成L2后repeat。只算16组L2是另需证明的优化，本建议不据此改原图；L2 epsilon仍未知，不能借input RMS的epsilon。

只有Q额外乘1/sqrt128，K不乘。beta由Sigmoid，decay依赖动态Softplus/Exp系数；G/N并不因此覆盖任意宽通用Exp。状态为 `[B,32,128,128]`；完成全value-head读出后，各128维普通RMS（gamma=weight），再乘SiLU(Z)，Wout4096→2560后residual1。D与F之间仅以Y连接，F仍做自己那次pre-FFN RMS0。卷积history更新要包含旧history和当前投影尾部，不能只保存当前token。[源图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L327)、[真实Repeat/L2 JSON](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/39bd7bf66c47e17c18aa39483c1d974a1e079aa2/docs/model-analysis/graphs/results/native04/qwen35_linear/simplified.graph.json)

### H：Falcon混合mixer

H只对X做一次普通RMS2560，然后以同一份不可提前覆盖的N分叉。Attention分支独立保留attn_in=1、K在RoPE前的0.044194...缩放、全128通道RoPE、GQA×5、QK后1/sqrt128及Wo后attn_out0.15。

SSM分支先ssm_in0.5，投影8736并应用z/x/B/C/dt五段不同MuP，拆Z4096/XBC4608/dt32。XBC通路4608通道k4卷积**有bias**，bias必须在SiLU前；再拆X4096/B256/C256，B/C从1组广播到32头。R卷积没有bias operand，不能凭“全七宏齐全”就假设宽bias路径已存在。dt经dt_bias/Softplus/Clip，源上界为正无穷，不能编造一个已接受有限数值上限。

SSM状态 `[B,32,128,256]`，读出加D skip之后先乘SiLU(Z)，再跨整个4096做一次普通RMS，Wout4096→2560再ssm_out0.088388...。这与D的Norm/门顺序和归约范围都相反。两分支都到齐后按源顺序 `Mixed=Add(A_scaled,M_scaled); Y=Add(X,Mixed)`。单M的大包装只能固定合法顺序串行物化两个分支；“数学并行”不等于一颗M可同时归两个子控。若未来多M才另评物理并行。

H后接F：F内pre-FFN普通RMS2560，gate投影后0.353553...再SiLU，up无此gate缩放，down后0.078125，再residual2。不同MuP位置不能粗暴合并成一个万能scale，固定点重排尤其需要数值证明。[源图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L481)

### X：Granite MoE

X内一次pre-MoE RMS1536后router40，TopK8产生运行时ID/rank。源算法还需selected logits再Softmax8；当前N TopK只返回ID，因此必须保留40 logits并按ID真实取数，不能把ID改解释为logit/概率。随后选择全部40专家域中所选8个专家权重，每专家I512/fused gate_up1024，SiLU门乘后down1536；按rank把专家输出与路由概率配对，宽加权累加，完整8项到齐后乘0.22，再residual2。选中8专家不意味着其他32永久可删除，也不意味着新增shared expert。

Router、Expert、Merge保留内部核边界以单独验证/将来扩展，但主母控仍调一个X调用，避免把每次动态rank都变成外部大Block调度和M11往返。单M结果上下文必须在下一专家覆盖前导出；全七宏仍缺通用宽加权NUM/格式接受与专家数据供给。若以后决定分开多个物理大Block，需要新的资源/队列/通信比较，不能将内部子程序名字当作已存在物理数量。[源图](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_SIMPLIFIED.md#L438)

## 4. 完整decoder层与子层大Block的比较

| 取舍 | 完整decoder-layer调用 | 本建议A/D/H→F/X子层调用 |
|---|---|---|
| 母控粒度 | 每层一个调用，内部含mixer与tail | 每层两个完整子层调用 |
| 边界激活 | 层X/O；Y天然内部 | 若分配不同包装，Y跨一次边界；同包装复用可内部保留 |
| 本地状态 | 同时纳入Norm/mixer/FFN或MoE全部存活区、状态与取消范围 | 各子层责任更清楚；FFN无需理解KV/state，mixer无需理解MoE专家循环 |
| 样本差异 | 一个完整层程序必须纳入十层型及其Norm/门/残差差异 | A/F共享大部分dense，D/H/X保留各自特殊流程 |
| 并行与资源 | 一套七宏仍只有一M；完整层包装不会凭空并行 | 可先同一包装时分；只有独立物理包装/资源才可能重叠，数量尚待选 |
| 验证边界 | 整层错误/状态与所有中间数据一次闭合，覆盖面大 | 可按有意义子层构建独立整数/状态/握手参考，再拼层 |
| 推荐定位 | 可作为五profile之上的本地复合程序/长期封装选项 | 当前更适合作为有限复用接口与分阶段接收边界 |

两者都可合理，源算法没有强制某种物理边界。推荐子层并非否定完整层：若最终容量/存储/程序/数值证明充分，可在同一大包装把两个子层程序嵌成一个decoder-layer入口，无需把算法重新改写成只有一种Norm或门顺序。不要为了减少母控调用而提前假定整层token原子回滚；R各tile commit、KV可见性、专家返回、输出已被下游接受等边界不同。

公平比较须固定总M/N/E/G/R/S/T和额外NUM/缓存/控制容量。一个完整层包装（7叶）与两个子层物理包装（14叶）不能直接当等面积方案比较。当前484调用只是静态逻辑展开；实际物理大Block数与PPA都未测定。

## 5. 七宏齐全与按类型选子集

主方案每个物理大Block都配齐七类，即使A/F/X不调用R，也保持相同底座包装；用已预制的本地有限程序及永久参数选择profile。这样接口/内部可用资源较规则，时分复用和后续profile组合容易统一，但未用R等资源的面积/漏电代价必须实测，不能声称已优化。

异构子集作为对照：A若覆盖Qwen3.5输出门需要M/N/E/G/S/T；F包含pre/post Norm，**也需要N**，其计算需求为M/N/E/G/S/T；D/H需求覆盖全七类；X为M/N/E/G/S/T加必要索引/宽数值能力。内部Expert kernel才可没有N，因为pre-MoE Norm在X父级一次完成；不能把整个F/X说成“不需要Norm”。T是否必须每profile独占、S容量/实例如何分配也属于未冻结的物理设计取舍，表中的子集不是最小硬件证明。

若选择异构，所有类型、实例数、local controller/适配、端口和路由资源仍须在共同M1–M10冻结前预制，M11/M12只在可用大Block之间固定连接和永久选择；不能按每个产品重新综合删宏后仍称相同底座。两种包装都不能消除缺失的Exp/宽bias/宽weighted merge、layout/gather、完整存储与版本服务。

## 6. 容量、数值、控制和证据边界

大shape原样保留。若用4B元素作规划，GDN一份全状态为2MiB、最少3tap history96KiB；Falcon SSM一份全状态4MiB、最少history54KiB。它们不是原生S16KiB能够驻留的量，old/next版本还会进一步增加；framework实际cache按k还是k−1存储仍须接口确认。Granite40专家一层权重元素94371840，即使按S8场景也约90MiB；不是I512就能把全部专家放到S。

系统有外存，但本轮不展开接口/PHY/搬运/调度，也不假定无限带宽或零延迟。逻辑上归本地控制器所有的state，并不表示所有字节都位于本地S。profile的weights/KV/state/history供给和输出可见性必须留作真实资源/完成依赖，在冻结前闭合。

Norm与RMS0、GDN L2、gated Sigmoid尺度、M输出四S32载体、E有限pack、G两lane、M单result上下文、N整组回放/计数、R多tile状态版本与T提交释放的既有约束仍然存在。共同底座软件可离线证明role/格式/布局，硬件不默认运行时通用类型系统；但真实count/valid/ready/等待/错误、MoE ID、位置、state及必要epoch仍动态。固定模型不等于无动态控制，也不意味着各子控制器可同时驱动同一M/S。

本轮来源仅有代表层的B1/S2/FP32/no-cache验证，完整带历史decode及全网络未由这些图证明。已完成P2最小MST只是一段S8×S8 K8/N8 raw-S64链，不能继承为A/F/D/H/X实现或完整投影已通。[原始图验证边界](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/model-analysis/COMPUTATION_GRAPHS_FULL.md#L31)、[P2有限RTL边界](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/1cc43a93a0c985587745ceba5e0d8d425d43a843/docs/PHASE2_MST_VERIFICATION.md)。

## 7. 机器映射与实际一致性检查

`coarse-model-map.json`包含8个model row、10个layer-type row、5个mother-visible profile row、6个内部kernel row，以及96个原sample obligation的粗放置索引。每个Norm源site逐字段保留且只分配一次owner；每层的两条残差归各自profile。原`projection_result_cast`义务的valid_elements为FFN I，分配tail F/X；原`residual_add`是能力汇总，候选owner明确列mixer与tail，不伪造为一条具体残差边。96义务不是完整整图，也不是完整控制程序或物理覆盖分母。

`build_coarse_model_map.py`从四份固定输入JSON生成该映射及`coarse-model-checks.json`，仅做研究一致性，program_words/物理实例数不估造。当前313项检查通过，含源H/I/头/位置/全层序列、所有Norm字段/唯一owner、两处残差、96义务ID与242层/484调用计数。`--check`重新生成并逐字节比较，不改已写文件；正式复算只需已提交的四份family JSON，无须重新上传原始图。另对19份旧源快照重算SHA/blob与原索引匹配，见`model-source-checks.json`；这项本地附加来源核验不作为正式生成器对raw文件的依赖。未运行推理、RTL/SystemC、服务器或EDA。

```powershell
python -B -X utf8 work/Melodydt/151/build_coarse_model_map.py --root . --output-dir work/Melodydt/151
python -B -X utf8 work/Melodydt/151/build_coarse_model_map.py --root . --output-dir work/Melodydt/151 --check
```

整合后可使用`--root . --output-dir <独立复算目录>`（`--input-root`为兼容别名），工具不依赖本机绝对输入路径。在线上传/审查/合并、本人进度与看板由根任务统一交付，本子任务不声称已远端完成。
