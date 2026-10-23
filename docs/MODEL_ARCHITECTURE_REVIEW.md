# 先审查架构，再选择算子与Block实验模型

## 2026-10-23接续：Llama-3.2-1B已纳入本机验证

Issue56/PR57仅复用用户旁支完整下载的固定checkpoint；下文Issue37的“本轮未跑/401”保留为原阶段事实，
不代表本次1B模型不可用或17变体均已跑通。正式合同project/experiments/llama_cross/model.json，
来源/原始BF16 SHA/实际FP32一组GQA4/整数/端口验证见[新报告](experiments/issue-56-llama-cross-model.md)。
16层、2048/8192、32Q/8KV、d64，无单独Q/K norm，Llama3 RoPE；tied embedding实际指针核验通过。
普通GQA语义覆盖增量有限，真实FFN激活与scale粒度风险是本次新证据，不由厂商名称推断必须新建Block。

2026-10-23，Liangruizhi；[Issue37](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/37)、
[PR38](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/38)。
用户最新要求优先架构分析与选型，因此本轮**没有运行新增模型或缩小模型数值实验**；只读取公开
小配置/本地框架代码、进行协议和公式检查。此前Issue33的真实小模型结果保持其原口径。

共同问题仍是：哪些计算、状态与通信应在制造前固定在Block内，哪些连接值得产品确定后定制，
以及在真实容量、端口、布线和时序约束下的端到端收益。厂商数量、模型名称和参数规模不是架构覆盖数。

## 证据和范围

目录涵盖此前会话与PR26提到的17个具体变体，见[机器可读目录](../project/experiments/model_selection/catalog.json)。
12个官方配置按模型revision固定并保存原字节/SHA；Gemma3两款、Meta Llama三款的config访问401，
保留官方元数据/家族证据和缺口，不用镜像、其他checkpoint或框架默认值冒充目标配置。
Gemma家族结构依据[官方技术报告](https://arxiv.org/html/2503.19786v1)；
DeepSeek依据[官方模型卡](https://huggingface.co/deepseek-ai/DeepSeek-R1)和固定配置；
Phi依据[官方模型卡](https://huggingface.co/microsoft/Phi-4-mini-instruct)和固定配置。
Llama家族参考[官方论文](https://arxiv.org/abs/2407.21783)，具体门控checkpoint仍待核。
Gemma/Phi实现语义只审阅本机已安装Transformers4.57.6，不据其默认构造器证明真实权重行为。

本方案接续PR26@2cd9ca15的功能目录；**不修改原作者文档/进度，不把MoE/MLA从待覆盖清单删除**。
用户此次要求是资源受限的先分析再筛选，因而本轮明确主测、复用、保留验证和暂缓范围。

## 架构差异及划分意义

| 家族/候选 | 计算图、状态和通信的特点 | 真正新增的划分问题 |
| --- | --- | --- |
| Qwen2 / Qwen2.5 | 普通全局GQA、RMSNorm、SwiGLU、RoPE；框架Q/K/V投影有bias；KV随长度增长。sliding_window字段不等于已启用 | INT32部分和、bias后更宽加法与RQ；QK/softmax/PV边界；GQA共享KV读口及prefill/decode复用 |
| Qwen3 dense（0.6B/4B） | 普通GQA加Q/K head norm；实际head_dim可能不同于hidden_size/nQ | QK归一化与重缩放靠近哪一端；格式转换和额外归约。4B增加规模，未形成另一个注意力类别 |
| Qwen3.5（0.8B/4B） | 线性Gated DeltaNet、短卷积和周期全注意力混合；递推矩阵/卷积历史及部分层KV并存，含门控/部分RoPE | 宽状态读改写归属、跨token反馈、状态端口与暂存；不能只因状态容量不随S增长就宣称低带宽/低误差 |
| Gemma3（4B/12B） | 家族为5局部:1全局注意力、局部跨度1024；QK norm、多处pre/post RMSNorm与GELU门控FFN。两规模的真实config尚未获权核验 | 局部环形缓存与全局增长缓存应否分bank/端口；1024边界和静态连接；多次归约、GELU替代SiLU所需数值/宽算术成本 |
| Phi-4-mini-instruct | 普通GQA；框架中融合QKV/gate-up投影；部分RoPE和LongRoPE。checkpoint为phi3架构，不能从名称猜模型实现 | 融合投影是否只需编译调度/scale分组；旋转/直通通道能否共用可编程向量单元；位置边界的系数/格式代价 |
| Llama3 / Llama3.2 1B、3B | dense GQA、RMSNorm、SwiGLU、RoPE；不同SKU的头数、宽度、共享embedding与位置参数不同 | 适合作跨家族可迁移性检验；仅增加同构规模通常不足以证明新Block类别。Meta授权和准确配置须先闭合 |
| DeepSeek-R1本体 | DeepseekV3骨架的MLA与MoE；配置256路由专家选8、共享专家、分组选择；发布配置还含FP8描述 | latent压缩/展开放置、router/top-k、dispatch/gather、热点/队列与专家驻留，是独立架构轴；FP8不是W8A8 |
| R1-Distill-Qwen / R1-Distill-Llama | 继承学生Qwen或Llama的dense图，保留各自GQA/FFN/位置编码；训练/权重与生成行为改变 | 可测推理分布、长答案与量化质量；**不能代表教师R1的MLA/MoE或专家通信** |
| Qwen3-30B-A3B | MoE加GQA/QK norm，128专家选8；与R1的MLA+分组路由不同。约3B激活不等于只需3B权重 | 可隔离“MoE有/无MLA”；路由实现/索引重排/背压仍需预制能力，静态金属只决定可达路径 |

“模块不同”不自动等于“物理Block不同”。例如Phi的融合QKV可能只是同一矩阵库的任务分组，
Gemma多处norm也可能分时复用向量资源；只有在固定端口、容量、转换、宽算术服务和关键路径下
出现可验证差异，才有理由把模块分为不同Block或增加固定连接。

### 当前整数合同尚未覆盖的关键接口

- **Qwen2系的QKV bias**：本地4.57.6实现是bias=True，而已有Issue33的RQ32明确无bias。
  两个INT32相加可能需要33位；逐行动态激活scale还会使bias的acc域整数值依行变化。
  要增加有明确定标、溢出/舍入和成本的bias节点，不能直接把浮点Linear成功当C1整数模型已支持。
- **norm存参语义**：Gemma框架以`1+weight`为实际gamma，并在float归约/乘gamma后转回；
  Phi以直接gamma及不同转换顺序实现。现有s16/f14 gamma范围未必容纳Gemma有效gamma，
  不能只因名称都叫RMSNorm就逐位共用。GELU也不是SiLU，需独立近似与宽操作成本。
- **块级KV scale进入归约**：若K/V按token-block变化scale，QK不同logit须先恢复可比较尺度；
  `sum_t p_int*v_int*scaleV(block(t))`不能把scaleV移到整个和外。
  必须分组累加/对齐、显式RQ/宽归约并重新验证softmax/PV质量；仅KV张量误差低还不够。

这些耦合说明，应先建立算子/状态/scale图和数值合同，再决定能否用模型做公平Block评估。

## 训练方法如何影响本研究

预训练/SFT/RL/蒸馏首先改变权重、激活离群值、输出长度、路由/状态分布与误差容忍；
不能从训练标签直接推出新硬件算子。R1的蒸馏不会把MLA/MoE转移进dense学生；
Qwen3的思考模式主要改变输入模板/生成轨迹，不能算新的矩阵结构。
原checkpoint、QAT checkpoint和事后4bit量化是不同证据条件：若权重也改变，不能把质量差异
都归因于位宽或Block划分。须固定模型/权重版本，分别标注训练结构、量化算法和执行格式。
数学/代码题还会放大长生成的误差传播，但任务得分不能代替状态/端口/连接分析。

## 关键尺寸与容量反例

以下是公开配置推导，B1、KV每元素2B，不是显存实测；不含scale、打包、工作区、临时分数、
backend副本或分配器。标准全局GQA逻辑KV为`2*L*S*nKV*head_dim*b`，不能用于MLA或直接用于全部混合层。

| 候选 | 已核配置特点 | S8192的逻辑KV/候选状态 |
| --- | --- | --- |
| Qwen2.5-3B-Instruct | L36，nQ16/nKV2，d128，H2048 | KV288MiB |
| 已有Qwen3-0.6B | L28，nQ16/nKV8，显式d128，H1024 | KV896MiB；H/nQ=64不能代替d128 |
| Qwen3.5-4B | L32，其中8层全局、24层递推；全局nKV4/d256 | KV256MiB；若采用标准每value-head GDN的FP32状态，另有固定48MiB；卷积逻辑历史约1.125MiB，K槽分配候选1.5MiB |
| Phi-4-mini | L32，nQ24/nKV8，d128，H3072 | KV1GiB |
| Gemma3、Meta原版 | config访问缺失 | 本轮不给伪精确全模型数字；公式/家族模式可分析，运行前必须核实际层表和维度 |

这个反例说明**小参数模型未必有更小KV**，已有0.6B不能按参数比例代替Qwen2.5-3B。
Qwen3.5的48MiB是明确布局/格式假设，不是已采集的真实状态分配；还要验证kernel是否展开/重复、
读取次数和全注意力KV。MLA也必须说明实际保存latent还是展开K/V，不凭名字直接套压缩容量。

官方metadata中的完整checkpoint元素数约为Gemma4B 4.30B、Gemma12B 12.19B、Phi3.84B。
若全部为16位，仅payload约8.60/24.37/7.67 GB；12B理想4bit约6.09GB，另加非4bit张量、
scale/zero-point/codebook、反量化、KV/激活/工作区。它们不是16GB可运行保证。
Qwen3-30B-A3B理想4bit payload已约15.27GB，MoE的“激活3B”不能替代完整存储预算；
R1本体即使理想4bit也远超16GB，因此不安排其完整权重基准。

## 建议的最小集合及取舍

**首轮主测三类、只新增一款主测权重**：

1. **Qwen2.5-3B-Instruct**：普通全局GQA基线，复用师兄Issue32既有工作，不据其正在运行推断已通过。
2. **Qwen3.5-4B**：混合递推/卷积/全局KV，复用同一任务，检验宽状态与反馈划分。
3. **Gemma3-4B-IT**：有条件主测，补局部/全局和GELU/norm轴。先授权/配置/后端校验，才进入新实验。

**保留已有Qwen3-0.6B**：本机数值/接口回归，提供普通注意力和QK norm实际样本，
不再增加Qwen3-4B必跑。它不替代3B/4B真实形状、端口压力或质量结论。

**仅一款保留验证，默认Phi-4-mini-instruct**：等划分策略和精度门槛锁定后，用不同家族的融合投影、
部分RoPE及数学/代码分布检查迁移。可按预注册训练配方校准该模型的scale，但不使用其评价集调Block策略。
Llama3.2-1B/3B或R1-Distill-Qwen-1.5B是替代/后续质量holdout，**不是再新增三个必跑项**；
替换须在查看其评价成绩前，依据授权/资源/协议原因登记。这里的保留验证指未用于调参的真实数值和工作负载，
不是未知架构盲测；允许事先审查Phi结构与正确性适配，但不能用其trace/质量/性能调Block策略。
若必须报告Llama或DeepSeek品牌的实际得分，需要另行完成对应权重实验，不能用Phi或家族分析代签。

Gemma12B四位暂缓：优先验证4B的结构价值，12B先作为规模/部署扩展；不混入同精度W8A8主对照。
Qwen2、Qwen2.5-0.5B、Qwen3.5-0.8B复用已有资料/可选调试，不新增必跑。
MoE/MLA保留配置/算子与映射压力轴，但当前**不宣称完整模型覆盖**。若研究主张扩展为原生MoE/MLA
端到端收益，应先解决数据/规模/精度和资源条件，再单独立项；不能用dense蒸馏填空。

这个集合按“全局GQA／混合递推／局部全局＋不同非线性”筛选，再留一次跨家族验证，
不是按厂商数排序，也不是计算出的唯一最优选择。代码仅检查显式覆盖与主观标明的追加工作成本，
不把set-cover筛查当科学证明。Gemma若未获权，应报告该覆盖轴pending，不能默默换镜像或删掉失败。

## 实验必须回答的可证伪问题

| 假设 | 受控比较 | 失败/否证条件 |
| --- | --- | --- |
| H1 完整INT32部分和局部保存有收益 | 同W/A、INT32、RQ、scale、端口/容量，内部K归约与跨Block部分和 | 转换/缓冲/关键路径抵消收益，或某真实形状容量/时序失败 |
| H2 近端RQ值得制造前固定 | 同一RQ库存，矩阵近端与共享向量侧；真实64B beat、元数据/动态scale单列 | 流量减少但端到端无改善，或归约路径搬回造成更差；不预设近端必胜 |
| H3 状态按生命周期分bank可减少争用 | 普通全局KV、Gemma局部/全局、Qwen3.5递推/卷积状态分开建图；同精度/总资源/私有工作区 | 复制、端口、反馈或静态不可达/时序余量使可行域消失 |
| H4 同一基础库可支持不同norm/FFN/位置路径 | Gemma GELU/多处norm、Phi融合/部分RoPE与Qwen基线；量化/转换节点不省略 | 未定义的宽乘/LUT/除法或重缩放导致质量失败/资源超额，需要新固定能力 |
| H5 少量产品后定制连接足够 | 制造前冻结库/端口；按模型训练集选连接预算；冻结后看保留模型 | 保留模型需要新增运行时不可用路径/有源资源，不能用运行中改金属修复 |

划分目标先以质量/正确性为约束，再比较端到端周期、存储和物理代价。所有形状失败、低利用率、
不能映射、OOM和质量不通过均保留，不能只统计赢家或事后改benchmark删除难例。

## 分阶段协议与停止条件

**A：接入与浮点正确性门槛。** 固定实际模型ID/revision、配置/权重/分词器SHA、纯文本范围、
框架/后端与chat模板；原生BF16优先，FP16只是待验证替代，不能称FP32高精度oracle。
抽取关键算子FP32参照，检查有限值、prefix/cached/chunk、KV/状态位置及Phi RoPE、Gemma窗口边界。
起步B1/S128/T16；实际窗口1023/1024/1025；Phi位置4095/4096/4097/8192按真实LongRoPE实现核对。
只记录FP16/BF16具体后端的差异，未过此门槛不跑长上下文或把错误归因于划分。

**B：精度与质量门槛。** 继承Issue33候选W8A8/INT32，各KV/state/probability/norm格式独立；
所有宽算术、scale产生、LUT/转换及浮点回退显式。先做权重、激活、KV、递推状态的单因素消融，
再组合。INT32溢出、整数oracle不一致或非有限值立即失败；P7长行全零等失败不能被浮点桥接掩盖。
校准使用不可变版本的训练文档，评价使用不重叠测试文档；冻结样本/长度/SHA/量化规则，不能沿用
前8token作为充分校准。部署4bit另设W4A16/NF4/GPTQ/AWQ/GGUF的精确合同，未实现的解包/转换不免费。

质量由**同模型同tokenizer同数据的BF16/FP32参照**评估：自然文本NLL/困惑度、数学GSM8K/MATH子集、
代码HumanEval+/MBPP+固定版本与执行环境；不拿不同tokenizer的token-NLL直接横向排序。
数学/代码生成预算、prompt/chat、采样种子/温度/停止/截断规则固定，性能teacher-forced与自由生成分开。
先小样本pilot筛明显失败，正式评价须有足够样本和配对95%区间；不足时记inconclusive。
拟议工程容忍为NLL相对增加≤5%、任务准确率绝对下降≤2百分点；这不是公认科学阈值，
需在看评价结果前审查冻结并做阈值敏感性。小算子低误差不等于该质量门槛通过。

**C：受控性能/划分。** 仅在A/B通过后，B1下S512/2048/4096，Gemma窗口邻域必测，8192按实际显存可选。
16GB按实际free VRAM和峰值检查，拟留2GiB裕量，不凭权重下界保证装得下；不在同卡同时常驻多模型。
确认memory-efficient attention/正确GQA路径，避免完整S²注意力张量和全层hook驻留；捕获与计时分跑。
计时3次warmup、5次重复、CUDA同步，记录P50/分布、峰值allocated/reserved、TTFT和逐token decode。
若卸载CPU则单列部署合同，不能与全GPU路径混为性能证据。OOM先缩数据采集/分块并保留失败，
不能静默改精度、层数、模型或预算制造可比结果。

分为两套工作负载：固定token形状控制硬件压力；相同自然文本/问题控制任务语义。
不同tokenizer导致两者不可能完全同一，必须同时记录文本/词元/SHA与实际长度。
冻结同资源、同数值函数、同外存/端口/打包后，再对比Block策略；保持原FP32证据不改标签。

**D：保留验证。** 主测选策略、精度合同/Block库/连接预算后固定全部选择，在Phi上直接应用；
若失败，报告泛化限制。上表H4中的Phi部分只在此阶段验证，不在主测阶段使用其评价数据选择资源。
修改方案后需新保留集/新轮次，不能把同一holdout反复调到通过后仍称独立验证。

GPU时间仅说明该工作负载/backend，不能直接证明未来Block的收益。划分阶段还要以同一精度合同
生成实际状态/转换图，在相同库存下校准矩阵/RQ/向量服务、bank端口与有限私有暂存；随后关联H2的
固定引脚/布线可达、电气/宏端口和setup/hold余量。只有物理条件与端到端模型都闭合，才报告硬件收益；
仅合成周期或GPU吞吐通过时保持对应证据层级，不接管Issue31/35的物理任务。

## 继续工作的入口

接续更新：用户已在Issue39授权本机适合实验，局部数值配置见kv_scale/experiment.json；
本页及model_selection/plan.json的关闭标志保留为Issue37架构阶段快照，不覆盖新的局部授权。
实际本机结果见experiments/issue-39-kv-scale-boundary.md；完整候选模型接入/质量门槛仍未通过。

可机读方案在[plan.json](../project/experiments/model_selection/plan.json)，新增数值实跑当前关闭。
师兄Issue32/PR36仍优先其Qwen修复，本轮只核其任务范围，没有整合其结果或改变分工。
Gemma/Meta授权与实际配置、适用backend、正式数据版本/样本/SHA、质量门槛审查和GPU排期未闭合，
因此此文件是可审查的实验设计，**不是“所选模型已经验证没问题”**。
本机资料与检查交接在docs/handoffs/2026-10-23-issue-37-model-selection.md；等待用户通知后再整合兄方证据。

## 本轮检查回执

正式源码946281b9a90dd36b130e691c60667b9f7d1e4d32，source_dirty=false。
`run_checks.py`记录管理结构、8个协议/容量已知值测试、whitespace通过；
`analyze.py`只枚举覆盖与推导逻辑容量，结果在work/Liangruizhi/37/screen.json。
独立审计17个源文件版本绑定及3份原始日志SHA，结果audit.json；逐文件索引manifest.json。
所有新增数据只是架构筛查，不是模型、质量或硬件实验。Issue/PR待审查/合并，不done；
登记PR5 pending，缺board配置/Projects工具，看板unverified/同步pending。
