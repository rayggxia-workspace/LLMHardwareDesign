# 步骤1重研究：共同预制底座下的八产品永久绑定合同

本稿为Issue151 / PR152的步骤1正式候选规格，负责人Melodydt。输入e44c4f5，七宏固定643c6012。来源是原family-spec、19项源索引和96条连接义务；不更改模型形状，不执行模型或服务器作业。上传/审查状态与实际整合检查见[工作报告](STEPS_1_3_WORK_REPORT.md)。

## 1. 本次重新确定的前提

共同M1–M10底座必须包含全部受支持产品需要的有源计算、缓冲、控制、ROM与选择能力。M11/M12永久连接已预制的选择/参数端点，确定模型；**不能在定制某模型时重新综合它的控制器，也不通过启动装载控制程序补缺**。有限意味着明确八个现有样本和十层型，不意味着未来同名或未知模型自动可用。

系统有外存；本轮暂不研究其接口和调度，只保留将来闭合的依赖与边界。不再把旧P0的片上credit0当系统永久无外存；也不把外存当无限、零延迟或已实现的spill。完整模型存储/数据可见性仍待后续接收，当前S容量不是完整架构上限。

role/type/尺度/布局主要是编译期契约。目标是让软件把八个完整程序及参数映射到同一套有限控制能力，尽可能消除不必要的通用包头/解释器；不是先要求每条数据都携带旧稿的通用role、type、256bit handle或512bit task，再用通用运行时图引擎解释。是否删除某字段须有明确证明，不能删除真实握手、计数、状态或动态数据选择。

## 2. 真实样本域与“固定”的三个层次

| 样本ID | H/I | Q/KV/D（Attention分支） | 层数 | 源配置max_position |
|---|---|---|---:|---:|
| qwen25 | 2048/11008 | 16/2/128 | 36 | 32768 |
| qwen3 | 1024/3072 | 16/8/128 | 28 | 40960 |
| llama | 2048/8192 | 32/8/64 | 16 | 131072 |
| gemma | 2560/10240 | 8/4/256 | 34 | 131072 |
| phi | 3072/8192 | 24/8/128 | 32 | 131072 |
| qwen35 | 2560/9216 | 16/4/256 | 32 | 262144 |
| granite | 1536/512 | 24/8/64 | 32 | 131072 |
| falcon | 2560/6144 | 10/2/128 | 32 | 131072 |

GDN另为key/query16头、value32头、Dk=Dv128；Falcon另为SSM32头、channel128、state256，不能把其Attention D套到状态分支。Gemma全局层为5/11/17/23/29，其余29层局部；Qwen3.5为[GDN,GDN,GDN,Global]×8。模型真实H/I/头数不缩小，源位置范围不改成硬件已支持范围。

| 层次 | 固定内容 | 不能误认为 |
|---|---|---|
| 共同底座固定 | 叶宏数量/几何/pin、共用顺序器与局部FSM、native-op译码、ROM读取、分支/循环/等待、转换/布局/缓冲/路由选择/驱动 | 为每个产品重新综合一套FSM后仍称同一底座 |
| 产品永久绑定 | 产品入口、精确层表与形状、模式、已接收的格式/尺度/常量、布局/route模板和允许参数域 | M11/M12能凭空新增计算、FIFO、寄存器、译码或CTS |
| 运行时变量 | token/长度/位置、合法prefill/decode分支、KV/state/history数值、MoE ID、等待/错误、计数和必要epoch | 模型固定就不再需要数据相关控制 |

当前仅形成四种有限层语法骨架：DENSE_ATTN_FFN、GDN_FFN、ATTN_MOE、ATTN_SSM_FFN。它们使用同一资源服务，结构选项由产品/层表永久决定；是可编译输入而不是已编译native程序，也不是四种超级指令已经覆盖整个模型。Attention与SSM具有并行数学语义，可以在单M上按固定合法顺序串行物化；不能让两个算法控制器直接并驱同一M/S。

## 3. 共同资源能力的并集

下表是八产品逻辑需求及全合法角色域条件义务的目录，**不是每项都对每个模型必需，也不是最终物理宏数、已实现的新模块或PPA结论**。当前一类一个七宏只是研究参照。预制冻结时必须接收实际能力/数量/路线；未用某能力的产品可以不调用或按已实现方式停用，不能后做有源修补。

| 能力ID | 逻辑归属 | 功能 |
|---|---|---|
| C01_MATRIX | M | 分块投影/QK/PV/跨K累加，单结果上下文 |
| C02_RMS | N | 完整范围RMS、gamma/原值回放 |
| C03_SOFTMAX | N | 完整行统计、EXP保存及概率回放 |
| C04_VECTOR | E | 偏置/残差/缩放/选择等S16基础算术 |
| C05_ROPE | E+常量/布局 | 相邻pair旋转、部分范围与频率来源 |
| C06_PACK | 外侧适配+E子集 | 四S32/八S16/两S16等载体拆拼和tail |
| C07_LAYOUT | 外侧适配 | M n-major、Slice/Transpose/Repeat/有界Gather |
| C08_REPLAY | S/临时存储服务 | 原值/EXP/gamma/分支结果物化与回放 |
| C09_STATIC_CONTROL | 共同预制控制 | 固定ROM/共享局部FSM/有界循环及事件等待 |
| C10_SILU_GATE | G | 两lane SiLU及紧邻门乘 |
| C11_GELU_GATE | G | GELU_tanh及门乘 |
| C12_QK_NORM | N | 按真实头维度分别归一化 |
| C13_RMS0_PARAMS | 参数/外侧适配 | gamma=1+weight，不能冒充N新mode |
| C14_SIGMOID_GATE | G | Sigmoid输出门，绑定gated/ungated尺度 |
| C15_CONV4 | R | 四tap深度卷积、history候选与保存 |
| C16_GDN | R | GDN key/query/update/readout |
| C17_SSM | R | SSM状态、逐元素decay载入、inject/skip |
| C18_COEFF | 新增数值能力待确定 | 负指数/dt/decay/inject及范围/精度 |
| C19_ROUTER | N+外侧索引 | 40选8 ID、selected score及专家数据索引 |
| C20_WIDE_MERGE | 新增宽算术待确定 | 八专家共同单位加权归并和gain |
| C21_STATE_VERSION | R外侧状态控制 | 多tile状态/history/位置版本与发布 |
| C22_FORK_JOIN | 外侧有限保持 | 固定分支配对/生存期/不同完成延迟 |
| C23_CONV_BIAS | 新增或已证明分解待确定 | Falcon卷积bias在SiLU前正确加到共同单位 |
| C24_LONG_SOFTMAX | 新增算法/资源方案待确定 | 若接收超过65535的完整逻辑行，原N计数不足 |
| C25_WIDE_CONVERT | 条件化复用/专用分解/额外能力待定 | 若某合法角色路线确需宽转换，优先复用M.op5等已有操作；不能以E13冒充S64，也不强制独立通用单元 |
| C26_FULL_MODEL_BOUNDARY | 待补全产品工作流 | embedding/位置mask/末Norm/LM head/采样边界 |
| C27_MUP | 参数+数值链 | Falcon分段MuP/K与分支输入输出独立缩放 |
| C28_SOFTPLUS | G+后续数值链 | QwenGDN/Falcon的dt Softplus，后续decay不由G直接提供 |

M/N/E/G/R内部已有的算子不自动形成组合；所选路线若需要额外布局、NUM、状态版本或控制逻辑，仍须真实实现验收。C25是全合法角色域的条件宽转换义务，不是从八模型形状推导出的独立单元要求；优先复用M.op5量化出口、已证明位提取/重排、E13覆盖子集或专用分解，仍不足时才增加实际能力。C24也只在永久接收大于65535完整Softmax行时触发，不能把源config上限当已接收工作负载。两者在每产品JSON单列conditional，不计为已证明必需单元。外存接入有源边界需在真正冻结前确定，本轮不展开。

## 4. 逐产品绑定

以下逐项列出共同能力、永久参数和动态变量。H/I/头/层表与上游FamilySpec逐字段一致；source小图仍只有B1/S2/FP32/no-cache，没有完整程序/整数质量结论。

### qwen25：Qwen2.5-3B base

- 有限层语法：qwen25_attention×36；完整层表在JSON，不生成任意层排列。
- Norm范围：qwen25_attention: RMS(2048×1), RMS(2048×1)。
- 源算法/候选映射要求的共同能力：`C01_MATRIX, C02_RMS, C03_SOFTMAX, C04_VECTOR, C05_ROPE, C06_PACK, C07_LAYOUT, C08_REPLAY, C09_STATIC_CONTROL, C10_SILU_GATE, C22_FORK_JOIN, C26_FULL_MODEL_BOUNDARY`，不是已编译的物理单元下界。
- 宽转换与超过65535整行的处理单列条件义务，均未证明本产品必须有独立通用单元。
- 永久绑定：精确模型/层表、H/I/头与投影几何、Norm/激活/RoPE模式；整数参数、权重布局/身份及buffer路径须在程序接收时补齐。
- 运行时保留：`token_values, request_length_and_current_position_within_accepted_limits, prefill_or_decode_branch_of_fixed_program, KV_contents_and_legal_window_progress, quantization_scale_if_data_dependent_scheme_is_accepted, ready_valid_latency_and_completion_errors, local_counters_and_buffer_occupancy`。
- 共同控制器可复用，完整程序/ROM偏移/参数范围仍未编译接收；程序字数为null。
- 产品阻塞门：`NUMERIC_PER_EDGE, WHOLE_MODEL_BOUNDARY, COMPLETE_PROGRAM, PROGRAM_STORAGE, MEMORY_INTEGRATION, SYSTEM_IMPLEMENTATION`。

### qwen3：Qwen3-0.6B

- 有限层语法：qwen3_attention_qk_norm×28；完整层表在JSON，不生成任意层排列。
- Norm范围：qwen3_attention_qk_norm: RMS(1024×1), RMS(128×16), RMS(128×8), RMS(1024×1)。
- 源算法/候选映射要求的共同能力：`C01_MATRIX, C02_RMS, C03_SOFTMAX, C04_VECTOR, C05_ROPE, C06_PACK, C07_LAYOUT, C08_REPLAY, C09_STATIC_CONTROL, C10_SILU_GATE, C12_QK_NORM, C22_FORK_JOIN, C26_FULL_MODEL_BOUNDARY`，不是已编译的物理单元下界。
- 宽转换与超过65535整行的处理单列条件义务，均未证明本产品必须有独立通用单元。
- 永久绑定：精确模型/层表、H/I/头与投影几何、Norm/激活/RoPE模式；整数参数、权重布局/身份及buffer路径须在程序接收时补齐。
- 运行时保留：`token_values, request_length_and_current_position_within_accepted_limits, prefill_or_decode_branch_of_fixed_program, KV_contents_and_legal_window_progress, quantization_scale_if_data_dependent_scheme_is_accepted, ready_valid_latency_and_completion_errors, local_counters_and_buffer_occupancy`。
- 共同控制器可复用，完整程序/ROM偏移/参数范围仍未编译接收；程序字数为null。
- 产品阻塞门：`NUMERIC_PER_EDGE, WHOLE_MODEL_BOUNDARY, COMPLETE_PROGRAM, PROGRAM_STORAGE, MEMORY_INTEGRATION, SYSTEM_IMPLEMENTATION`。

### llama：Llama-3.2-1B-Instruct（本图为配置重建/随机参数）

- 有限层语法：llama_attention×16；完整层表在JSON，不生成任意层排列。
- Norm范围：llama_attention: RMS(2048×1), RMS(2048×1)。
- 源算法/候选映射要求的共同能力：`C01_MATRIX, C02_RMS, C03_SOFTMAX, C04_VECTOR, C05_ROPE, C06_PACK, C07_LAYOUT, C08_REPLAY, C09_STATIC_CONTROL, C10_SILU_GATE, C22_FORK_JOIN, C26_FULL_MODEL_BOUNDARY`，不是已编译的物理单元下界。
- 宽转换与超过65535整行的处理单列条件义务，均未证明本产品必须有独立通用单元。
- 永久绑定：精确模型/层表、H/I/头与投影几何、Norm/激活/RoPE模式；整数参数、权重布局/身份及buffer路径须在程序接收时补齐。
- 运行时保留：`token_values, request_length_and_current_position_within_accepted_limits, prefill_or_decode_branch_of_fixed_program, KV_contents_and_legal_window_progress, quantization_scale_if_data_dependent_scheme_is_accepted, ready_valid_latency_and_completion_errors, local_counters_and_buffer_occupancy`。
- 共同控制器可复用，完整程序/ROM偏移/参数范围仍未编译接收；程序字数为null。
- 产品阻塞门：`NUMERIC_PER_EDGE, WHOLE_MODEL_BOUNDARY, COMPLETE_PROGRAM, PROGRAM_STORAGE, MEMORY_INTEGRATION, SYSTEM_IMPLEMENTATION, LONG_CONTEXT_N, LLAMA_CHECKPOINT`。

### gemma：Gemma-3-4B-it text

- 有限层语法：gemma_local_attention×29, gemma_global_attention×5；完整层表在JSON，不生成任意层排列。
- Norm范围：gemma_local_attention: RMS0(2560×1), RMS0(256×8), RMS0(256×4), RMS0(2560×1), RMS0(2560×1), RMS0(2560×1); gemma_global_attention: RMS0(2560×1), RMS0(256×8), RMS0(256×4), RMS0(2560×1), RMS0(2560×1), RMS0(2560×1)。
- 源算法/候选映射要求的共同能力：`C01_MATRIX, C02_RMS, C03_SOFTMAX, C04_VECTOR, C05_ROPE, C06_PACK, C07_LAYOUT, C08_REPLAY, C09_STATIC_CONTROL, C11_GELU_GATE, C12_QK_NORM, C13_RMS0_PARAMS, C22_FORK_JOIN, C26_FULL_MODEL_BOUNDARY`，不是已编译的物理单元下界。
- 宽转换与超过65535整行的处理单列条件义务，均未证明本产品必须有独立通用单元。
- 永久绑定：精确模型/层表、H/I/头与投影几何、Norm/激活/RoPE模式；整数参数、权重布局/身份及buffer路径须在程序接收时补齐。
- 运行时保留：`token_values, request_length_and_current_position_within_accepted_limits, prefill_or_decode_branch_of_fixed_program, KV_contents_and_legal_window_progress, quantization_scale_if_data_dependent_scheme_is_accepted, ready_valid_latency_and_completion_errors, local_counters_and_buffer_occupancy`。
- 共同控制器可复用，完整程序/ROM偏移/参数范围仍未编译接收；程序字数为null。
- 产品阻塞门：`NUMERIC_PER_EDGE, WHOLE_MODEL_BOUNDARY, COMPLETE_PROGRAM, PROGRAM_STORAGE, MEMORY_INTEGRATION, SYSTEM_IMPLEMENTATION, LONG_CONTEXT_N`。

### phi：Phi-4-mini-instruct

- 有限层语法：phi_fused_partial_rope×32；完整层表在JSON，不生成任意层排列。
- Norm范围：phi_fused_partial_rope: RMS(3072×1), RMS(3072×1)。
- 源算法/候选映射要求的共同能力：`C01_MATRIX, C02_RMS, C03_SOFTMAX, C04_VECTOR, C05_ROPE, C06_PACK, C07_LAYOUT, C08_REPLAY, C09_STATIC_CONTROL, C10_SILU_GATE, C22_FORK_JOIN, C26_FULL_MODEL_BOUNDARY`，不是已编译的物理单元下界。
- 宽转换与超过65535整行的处理单列条件义务，均未证明本产品必须有独立通用单元。
- 永久绑定：精确模型/层表、H/I/头与投影几何、Norm/激活/RoPE模式；整数参数、权重布局/身份及buffer路径须在程序接收时补齐。
- 运行时保留：`token_values, request_length_and_current_position_within_accepted_limits, prefill_or_decode_branch_of_fixed_program, KV_contents_and_legal_window_progress, quantization_scale_if_data_dependent_scheme_is_accepted, ready_valid_latency_and_completion_errors, local_counters_and_buffer_occupancy`。
- 共同控制器可复用，完整程序/ROM偏移/参数范围仍未编译接收；程序字数为null。
- 产品阻塞门：`NUMERIC_PER_EDGE, WHOLE_MODEL_BOUNDARY, COMPLETE_PROGRAM, PROGRAM_STORAGE, MEMORY_INTEGRATION, SYSTEM_IMPLEMENTATION, LONG_CONTEXT_N`。

### qwen35：Qwen3.5-4B text

- 有限层语法：qwen35_global_gated_attention×8, qwen35_gdn×24；完整层表在JSON，不生成任意层排列。
- Norm范围：qwen35_global_gated_attention: RMS0(2560×1), RMS0(256×16), RMS0(256×4), RMS0(2560×1); qwen35_gdn: RMS0(2560×1), L2(128×32), L2(128×32), RMS(128×32), RMS0(2560×1)。
- 源算法/候选映射要求的共同能力：`C01_MATRIX, C02_RMS, C03_SOFTMAX, C04_VECTOR, C05_ROPE, C06_PACK, C07_LAYOUT, C08_REPLAY, C09_STATIC_CONTROL, C10_SILU_GATE, C12_QK_NORM, C13_RMS0_PARAMS, C14_SIGMOID_GATE, C15_CONV4, C16_GDN, C18_COEFF, C21_STATE_VERSION, C22_FORK_JOIN, C26_FULL_MODEL_BOUNDARY, C28_SOFTPLUS`，不是已编译的物理单元下界。
- 宽转换与超过65535整行的处理单列条件义务，均未证明本产品必须有独立通用单元。
- 永久绑定：精确模型/层表、H/I/头与投影几何、Norm/激活/RoPE模式；整数参数、权重布局/身份及buffer路径须在程序接收时补齐。
- 运行时保留：`token_values, request_length_and_current_position_within_accepted_limits, prefill_or_decode_branch_of_fixed_program, KV_contents_and_legal_window_progress, quantization_scale_if_data_dependent_scheme_is_accepted, ready_valid_latency_and_completion_errors, local_counters_and_buffer_occupancy, state_history_values, recurrent_owner_epoch_position, candidate_commit_or_revoke_result, numeric_epoch_or_F_if_adaptive_rescale_is_accepted`。
- 共同控制器可复用，完整程序/ROM偏移/参数范围仍未编译接收；程序字数为null。
- 产品阻塞门：`NUMERIC_PER_EDGE, WHOLE_MODEL_BOUNDARY, COMPLETE_PROGRAM, PROGRAM_STORAGE, MEMORY_INTEGRATION, SYSTEM_IMPLEMENTATION, LONG_CONTEXT_N, GDN_L2_EPSILON, RECURRENT_NUMERIC, R_QUALIFICATION`。

### granite：Granite-3.1-3B-A800M-Instruct（图册别名Granite-3.3B）

- 有限层语法：granite_top8_moe×32；完整层表在JSON，不生成任意层排列。
- Norm范围：granite_top8_moe: RMS(1536×1), RMS(1536×1)。
- 源算法/候选映射要求的共同能力：`C01_MATRIX, C02_RMS, C03_SOFTMAX, C04_VECTOR, C05_ROPE, C06_PACK, C07_LAYOUT, C08_REPLAY, C09_STATIC_CONTROL, C10_SILU_GATE, C19_ROUTER, C20_WIDE_MERGE, C22_FORK_JOIN, C26_FULL_MODEL_BOUNDARY`，不是已编译的物理单元下界。
- 宽转换与超过65535整行的处理单列条件义务，均未证明本产品必须有独立通用单元。
- 永久绑定：精确模型/层表、H/I/头与投影几何、Norm/激活/RoPE模式；整数参数、权重布局/身份及buffer路径须在程序接收时补齐。
- 运行时保留：`token_values, request_length_and_current_position_within_accepted_limits, prefill_or_decode_branch_of_fixed_program, KV_contents_and_legal_window_progress, quantization_scale_if_data_dependent_scheme_is_accepted, ready_valid_latency_and_completion_errors, local_counters_and_buffer_occupancy, top8_expert_ID_values, rank_probability_values, expert_completion_progress`。
- 共同控制器可复用，完整程序/ROM偏移/参数范围仍未编译接收；程序字数为null。
- 产品阻塞门：`NUMERIC_PER_EDGE, WHOLE_MODEL_BOUNDARY, COMPLETE_PROGRAM, PROGRAM_STORAGE, MEMORY_INTEGRATION, SYSTEM_IMPLEMENTATION, LONG_CONTEXT_N, GRANITE_ALIAS, MOE_WIDE_NUMERIC`。

### falcon：Falcon-H1-3B-Instruct

- 有限层语法：falcon_attention_ssm_hybrid×32；完整层表在JSON，不生成任意层排列。
- Norm范围：falcon_attention_ssm_hybrid: RMS(2560×1), RMS(4096×1), RMS(2560×1)。
- 源算法/候选映射要求的共同能力：`C01_MATRIX, C02_RMS, C03_SOFTMAX, C04_VECTOR, C05_ROPE, C06_PACK, C07_LAYOUT, C08_REPLAY, C09_STATIC_CONTROL, C10_SILU_GATE, C15_CONV4, C17_SSM, C18_COEFF, C21_STATE_VERSION, C22_FORK_JOIN, C23_CONV_BIAS, C26_FULL_MODEL_BOUNDARY, C27_MUP, C28_SOFTPLUS`，不是已编译的物理单元下界。
- 宽转换与超过65535整行的处理单列条件义务，均未证明本产品必须有独立通用单元。
- 永久绑定：精确模型/层表、H/I/头与投影几何、Norm/激活/RoPE模式；整数参数、权重布局/身份及buffer路径须在程序接收时补齐。
- 运行时保留：`token_values, request_length_and_current_position_within_accepted_limits, prefill_or_decode_branch_of_fixed_program, KV_contents_and_legal_window_progress, quantization_scale_if_data_dependent_scheme_is_accepted, ready_valid_latency_and_completion_errors, local_counters_and_buffer_occupancy, state_history_values, recurrent_owner_epoch_position, candidate_commit_or_revoke_result, numeric_epoch_or_F_if_adaptive_rescale_is_accepted`。
- 共同控制器可复用，完整程序/ROM偏移/参数范围仍未编译接收；程序字数为null。
- 产品阻塞门：`NUMERIC_PER_EDGE, WHOLE_MODEL_BOUNDARY, COMPLETE_PROGRAM, PROGRAM_STORAGE, MEMORY_INTEGRATION, SYSTEM_IMPLEMENTATION, LONG_CONTEXT_N, CONV_BIAS_NUMERIC, RECURRENT_NUMERIC, R_QUALIFICATION`。


### 需要在上述逐模型表中具体保留的差异

- Qwen2.5有三路QKV bias；Qwen3的Q宽2048而H1024，另有每头Q/K RMS；Llama没有Q/K头Norm，其图是重建配置/随机权重。
- Gemma是GELU_tanh、六处RMS0，局部window1024与全局层不同位置频率；不能用一份“普通RMS+SiLU”程序冒充。
- Phi是融合QKV与gate_up后Slice，RoPE仅96/128、其余32旁路；LongRoPE参数必须绑定源配置，不能用仅层内乘加图证明频率生成。
- Qwen3.5全局Q_gate宽8192，每头Q256+门256；Sigmoid门在PV后。GDN则qkv8192/z4096/beta32/a32、Conv8192×kernel4，无bias；状态[B,32,128,128]，先每head128 RMS后门乘。实际ONNX先Repeat16→32再L2，头映射floor(vhead/2)有Reshape/Tile证据；只计算16组L2是另需证明的优化。Q独立乘1/sqrt128，K不乘。
- Granite每token40选8，每专家I512，两个残差分支gain0.22、Attention multiplier0.015625；图没有shared expert。专家身份是动态数据，专家算法是固定循环，不应为每个动态ID编译一份新控制器。
- Falcon投影8736=Z4096+XBC4608+dt32，XBC再拆4096/256/256，B/C一组广播32头；Conv4608×kernel4有bias，R无bias口。状态[B,32,128,256]，先SiLU(Z)门乘再跨4096 RMS；K pre-RoPE scale与多处MuP不能合成一个万能系数。

## 5. 哪些role字段可消除，靠什么证明

静态role不等于没有控制状态。下表是条件化的软件证明义务；本轮没有完成这些编译证书，也没有自动删除字段。证明成立后可以选择更小的具体硬件编码，无需通用类型系统。

| 证明ID | 候选消除字段 | 必要证明 | 必须保留 |
|---|---|---|---|
| P01_ROLE | generic_role_id | 每个静态节点的源op/目的operand、阶段及唯一owner已由完整程序证明；只允许已接收产品入口。 | native_opcode, local_phase, payload_ready_valid, error |
| P02_TYPE | generic_dtype_id, generic_frac_bits_header | 逐边logical/carrier格式、尺度、转换和所有producer/consumer已编译；该边不使用动态重定标。 | native_wide_half_flags, native_shift, saturation_policy, dynamic_numeric_epoch_if_required |
| P03_LAYOUT | per_packet_layout_id, per_packet_shape_descriptor | shape/布局/别名与循环覆盖已离线证明，目标缓冲/尾字独占，只有受界定长度可变。 | address_or_index_counter, actual_valid_count, native_tail_count, write_ack_wait |
| P04_ORDER | per_packet_task_id | 每资源单一owner、响应按序且归属唯一，复位/取消后已排空；不存在未归属迟到响应。 | outstanding_or_phase_state, accepted_vs_completed_count, drain_state, epoch_if_stale_possible |
| P05_BUFFER | generic_handle_id, generic_refcount_table | 本产品固定buffer图已证明生命周期，fork消费者集合/数目固定，无外部共享别名或提前覆盖。 | buffer_occupied_or_phase, pending_consumer_bits_if_needed, last_consumer_release, write_visibility |
| P06_ROUTER_RANGE | ID_type_tag, redundant_ID_range_check_if_formally_proven | N.TOP_LOAD的ID只由固定0..39序列产生；TopK只复制这些ID，来源路径及地址公式已证明。 | selected_expert_ID_values, rank, rank_completion_mask, expert_data_ready |
| P07_OWNER | per_packet_model_id, general_runtime_resource_dispatch_table | 产品由永久选择锁定，原生端口唯一owner，完整静态时间/事件顺序不发生多源竞争。 | native_owner_fields_where_required, local_request_hold, resource_busy_or_validity, event_wait |
| P08_JOIN | general_join_key_comparator_if_unnecessary | 两分支始终由同一静态调用产生，位置/迭代归属由本地索引与排空证明，缓冲不会混代。 | per_branch_arrival_bits, stable_operand_storage, iteration_or_position, failure_drain |

例如，固定程序选择“M op5→E13→G”时，当前阶段和产品常量可以确定四S32的解释及shift，无需每包发送role/type/F。若M op5已夹取逻辑S16，也可采用已证明的位提取/重排，E13 shift0并非所有路线必选。一个E13响应的四S16低64可直接拆成两个G的32bit包，或以N count4消费；只有目的/存储布局要求紧凑八S16时才合并两半包。目的驱动的选择/保持、实际有效数和握手仍须实现，不预设一定有八元素合包器。硬件真正使用的opcode/shift/count没有因此消失。

N的STATS/EXP/REPLAY可由固定地址/阶段和原值不变性证书保证lineage，无需每包通用tensor ID；但实际长度可能变化，stats/EXP/replay计数、完整组屏障和写确认仍要存在。N busy也不是整组lease是否可切换的证明。

固定MoE TopK输入ID恰为0..39时，软件/形式证明可以避免重复的ID类型检查甚至冗余范围比较；实际TopK选出的8个ID、rank与probability及等待进度仍是运行时值，不能固定为8个专家。QwenGDN/Falcon即使模型固定，state内容、位置、候选/提交结果也不断变化。

若后续接受dense FFN动态量化或数据相关的因果重定标，scale以及必要的F/numeric_epoch会成为少量真实数值控制状态，不能应用“尺度永远固定”的删除证明。该条件变量在全部八产品表中保留，不默认只影响R模型。本轮尚无这些数值方案的完整接收结果。外存迟到响应/复位排空协议没有确定，故不能以本地单在途证明宣称全系统不需要任何tag或generation；也不在此引入强制通用tag头。

## 6. 完整程序的预制前接收门

每个产品都必须在**同一个共同底座冻结之前**提供并接收以下材料，不是只选一个样本通过，也不能先冻结底座后再为其他产品重综合controller：

1. 具体模型/config/权重与完整产品工作流身份；补清embedding、位置/mask、末Norm/LM head/采样等源图外边界。Llama图的随机参数和Granite别名不能被模糊处理。
2. 固定层语法的完整实例、源维度/合法运行范围、每边数值和布局、原生op/bitfield、资源唯一所有者与必要算法分解。
3. 用共同控制ISA/局部FSM真实编译出来的全部程序与永久参数；没有未解析NUM/转换/存储原语；ROM字数/地址/表域由实际编译结果测得，不估造program长度。
4. 资源/临时区/回放/状态生命周期与动态分支证明；外存边界后续需闭合请求/数据可见性/完成语义，不能凭“系统有外存”跳过。
5. 独立整数参考、组合功能、错误/取消/复位、活性与共用底座/永久选择的物理接受证据。单宏资格、source B1/S2和96条义务都不能代替。

当前JSON中八产品`complete_program_compiled=false`、`complete_program_accepted=false`，program_words/ROM_offset均null，完整已编译/已接收集合为空。若有一产品没有通过，应该阻止“支持全部八产品”的底座冻结结论，明确缩减受支持产品集合需另行评审；不能把它的profile标非法来隐藏缺口。未知模型不因落在某个品牌或大致形状范围就自动被接收。

## 7. 未知、阻塞与边界

具体产品门在JSON逐项索引。共同未知包括：每边整数格式/尺度/误差、完整产品程序和ROM容量、前后端模型工作流、外存数据完成依赖、新系统RTL/物理。GDN L2 epsilon未知，不能借RMS epsilon；R beta/decay/inject与状态单位及重定标未闭合；Falcon conv bias要保留宽数值路径；MoE宽归并/共同单位/gain待oracle。R跟踪候选仍未最终合格。

源config max_position只是原模型位置配置上限，不是已接收的硬件context上限；旧query1/context256是P0候选，不作为本稿永久参数。保留真实H/I/头/状态尺寸，容量不足是实现/映射缺口，不因当前S16KiB就永久排除系统有外存的模型，也不声称外存已补足。

## 8. 可复核检查与交付状态

工具`work/Melodydt/151/build_family_binding_contract.py`从输入包三JSON生成本合同；`--check`只读核对8产品/10层型、真实维度/完整层表、Norm/Attention/R/MoE源特征逐字段等值、96义务逐产品无丢失、共享能力引用、8项条件消字段证明、永久绑定/无bootload/无产品重综合、外存范围与未编译状态，并检查输入SHA未漂移。它是研究一致性检查，不是native程序编译器、整数oracle或RTL测试。

工具不依赖本机草稿层级：`--input-root`默认当前目录，`--output-dir`默认工具所在目录；生成和`--check`均针对所选输出目录。整合到正式work目录后可在独立目录复算，避免覆盖正式文件，例如：

```text
python -X utf8 work/Melodydt/151/build_family_binding_contract.py --input-root . --output-dir work/Melodydt/151/recompute-family
python -X utf8 work/Melodydt/151/build_family_binding_contract.py --input-root . --output-dir work/Melodydt/151/recompute-family --check
```

上面是整合后复算入口，不冒充已在正式目录执行。产物只记录repository-relative输入路径和内容SHA，不嵌入输入/输出绝对目录；同字节输入应生成同字节JSON/报告。实际本轮运行入口仍在隔离drafts/family，输入为该任务integrated快照。

该生成器检查三份输入JSON与19项来源索引；19份原始快照的字节检查、其他静态检查及远端交付另由本轮整合回执记录，不把索引检查当模型复现。未执行推理、RTL/SystemC、服务器或EDA。
