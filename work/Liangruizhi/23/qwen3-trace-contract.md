# Qwen3-0.6B：真实前向轨迹与状态放置的首轮合同建议

2026-10-22，仅设计建议；本审查没有安装软件、下载权重、运行模型或修改项目仓库。该实验接续合成代数验证，不重复378个合成配置。

## 目标与固定输入

目标是证明：固定官方权重的真实增量KV执行与完整前缀重算在数值上相容；提取可核验的真实tensor shape、dtype、逻辑驻留状态及边界值，随后用同一trace驱动明确假设的bank账本。CPU墙钟时间只作本次任务耗时记录，不证明芯片速度、能量或Block划分收益。

固定B=1，一条公开自拟文本tokenize后取48个token，保存原文、token IDs和SHA。首先32-token prefill，再teacher-forced输入余下16个token逐步decode；每步不采样、不把argmax送回后续输入。因此即使实现误差改变argmax，后续比较仍是同一输入。第二条不同内容只作保留数值场景；shape资源结论不因换文本就成为跨架构证据。

推荐增加一个有辨别力的调度对照：同一前32个token，改为16+16的chunked prefill，再执行同样16个单token步骤。这样只改变瞬态workspace的粒度，最终持久KV和逻辑输出应一致。它能检验所谓放置收益是否只是固定基线未被允许chunking。若时间允许，再用96+8长度点；总长度均不超过128。

## 身份、数值与版本

只使用官方Qwen/Qwen3-0.6B，固定不可变revision并记录所有下载文件SHA、config/tokenizer/template版本。调研时官方config解析到revision c1899de289a04d12100db370d81485cdf75e47ca，但这不是已下载或验证权重完整性的声明；实际运行须重新核实并记录选定revision。

固定CPU、float32、eval/inference_mode、同一attention backend（优先明确选择eager便于观测）、线程数与PyTorch/Transformers版本。不能用auto dtype后按FP32算bytes。固定输入不依赖generate、sampling或thinking行为；若使用chat template，明确保存enable_thinking设置及最终IDs。查本机已安装模型源码后再绑定hooks，不照搬随版本变化的Cache API。

官方配置为hidden_size1024、intermediate_size3072、28层、16个Q head、8个KV head、head_dim128。故Q线性投影输出宽2048，K/V宽1024；不能用1024/16推导head_dim64。[固定revision配置](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/config.json)

## 独立比较

路径A维护自己的DynamicCache；每次只输入尚未处理的token。路径B对同一完整前缀重新计算，不复用路径A的cache。B可使用全新cache以读出其K/V，但每步都从空状态开始。[官方Cache语义](https://huggingface.co/docs/transformers/en/model_doc/qwen3)

每一步比较末token logits和层0/13/27的末token中间值；cache长度和shape核对全部28层。增量attention_mask覆盖past+new总长度，position_ids以及版本要求的cache_position对应全局位置，不能每步重新从0开始。完整前缀使用0…T−1。参考调用后还须确认没有污染路径A的cache。

建议在运行前声明FP32数值门槛atol=1e-4、rtol=1e-4，报告max_abs、relative-L2、argmax与top-2 gap；任何NaN/Inf直接失败。argmax一致只是辅助，不能替代tensor误差。若失败，应先留存结果并查backend、位置、mask、线程或dtype，不能看完结果后静默放宽阈值。

cache另有两种不同断言：append前已有prefix在append后应逐字节不变；与全前缀重算的对应K/V则按FP32容差比较，因为不同GEMM形状可以产生末位差异。不能混淆二者。

## Hook语义与状态账本

- 全28层记录q_proj/k_proj/v_proj、gate_proj/up_proj、down_proj输入及输出、attention o_proj输入/输出的shape/dtype/numel/itemsize；只保留选定层的数值比较所需切片，其他立即汇总释放。
- q_proj/k_proj hook值处于Q/K norm和RoPE之前，不能称实际attention Q/K。实际cache中的K通常已经过norm/RoPE；V没有这条位置变换。要验证attention核心，须通过版本明确的观察接口捕获实际post-norm/post-RoPE Q及K，或保存norm输出与实际cos/sin后独立重建并标记为derived。不能把raw k_proj直接和cache K比较。
- down_proj前置hook提供真实SiLU(gate)*up结果；down_proj输出是FFN输出。不要仅根据模型类名推断中间值。
- 先用无保存hook的数值路径，再单独做受控trace；核对instrumented与uninstrumented末token logits一致。观测器不改tensor、不替换计算、不在循环中保留所有历史tensor。不把保存trace产生的副本计作模型固有状态。

逻辑KV应由实际cache张量计算。若是FP32，每层每token为2×8×128×4=8192 bytes，28层为229376 bytes/token：T32=7MiB，T48=10.5MiB，T128=28MiB。必须分别报告逻辑有效KV、框架实际storage allocation和临时拼接副本；StaticCache预留容量也不能误叫有效长度。Q及FFN临时态不是跨token持久cache。[缓存原理](https://huggingface.co/docs/transformers/en/cache_explanation)

模型权重、KV持久状态、残差/归一化、FFN临时态、attention临时态、LM head输出和trace副本分别登记。eager CPU实际物化attention scores不证明硬件online schedule也必须物化；旧账本若只包含attention/FFN核心，新增真实层trace后仍应保留scope缺项，不能突然称完整模型成本。

## 三个必要负例

1. 对选定decode步骤把全局position错误重置0，或有意漏掉past mask；至少一个logits／K／中间层比较应拒绝。错误路径使用独立cache，不污染正例。
2. 独立错误cache交换某层KV head，验证比较器确实能发现状态错误，而非只检查shape。
3. 在元数据中误以16个Q head计算KV bytes，独立shape×itemsize公式应拒绝；也测试把projection K冒充post-RoPE cache K的stage标签错误。

以上是实际权重路径的状态与观察负例，不再扩展合成代数扫描。

## 与固定／后期可定制的可证伪连接

先把真实trace投向完全固定的bank容量、port数量、engine位置与总带宽。比较KV长期驻留与FFN/attention短期态的若干明确放置政策，逐bank算生命周期重叠与读写需求；保留外存spill、chunked prefill及tile选择的实际成本。不能把同容量的pooling或新crossbar免费送给某一方案。

固定配置基线应在设计trace中选择一次配置，并拥有其真实存在的软件调度/地址映射自由度。后期可定制方案仅从预声明端点/连接中选择静态配置；每次部署仍须以同一配置服务prefill与decode。阶段切换自动换接线属于预制的运行时可选能力，必须另计硬件资源并给予公平基线，不能冒充静态金属/通孔定制。

把运行时可任意搬移状态/池化的方案单列为乐观上界。若某个固定配置加合法chunking已覆盖全部trace且成本相同，就接受“本轮没有晚期定制优势”的否定结果。若只有按阶段切换接线才能获益，应转化为运行时灵活性需求，而非H2成功。

本轮Qwen不同长度/阶段仍是同一模型的工作负载变化，不能称支持两个不同计算拓扑的物理H2。即便抽象放置模型发现差异，距离制造结论仍缺真实端点、固定有源/时钟/供电、合法路由和物理参数；只可报告所选trace和假设下的容量／通信结果。
