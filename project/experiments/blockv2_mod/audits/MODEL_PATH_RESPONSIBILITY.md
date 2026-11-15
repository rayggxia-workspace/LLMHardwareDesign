# 多模型到 blockv2-mod 的责任审计

审计日期：2026-11-15。代码基线：f2eadc48a9964bc75d29cae1c81d7cea07424d27。远端 Slurm 作业 115214，COMPLETED / 0:0，41 秒。此作业是编译能力审计，不是模型执行或性能评估。

## 证据范围

现有 benchmark 是 10 种模型/层类型，各有 raw、simplified 两种 ONNX 导出，共 20 张图。它们是 B1S2、FP32 的 decoder 层导出，不是 20 个完整 LLM。Llama 的来源记录 checkpoint_loaded=false，不能用于训练权重质量结论。Gemma local/global、Qwen3.5 global/linear 分别代表不同层类型。

本轮读取所有图的全部 task。10 张 raw 图分别有 57、75、57、95、95、67、84、117、77、212 个含未知维度的 value，阻断地址布局，均为 unknown dimensions，不能说只是空张量。其后端能力主要以对应 simplified 图追查。对 simplified 图逐任务进行 operand lowering，并尝试全部候选绑定/编码，使用原图布局和存储信息；为独立定位错误，移除了该任务的调度依赖。它不证明整图可调度，不检查全部跨任务生命周期，也不取代整图执行。

| 图 | 全部 task | 至少一个可编码候选 | 仅地址视图 | 无可编码候选/降级失败 |
|---|---:|---:|---:|---:|
| qwen25 | 42 | 8 | 22 | 12 |
| qwen3 | 43 | 13 | 21 | 9 |
| llama | 51 | 6 | 21 | 24 |
| gemma_local | 57 | 20 | 21 | 16 |
| gemma_global | 57 | 20 | 21 | 16 |
| phi | 53 | 8 | 30 | 15 |
| qwen35_global | 54 | 11 | 28 | 15 |
| qwen35_linear | 97 | 11 | 31 | 55 |
| granite | 62 | 7 | 30 | 25 |
| falcon | 137 | 18 | 52 | 67 |

“候选编码成功”不是该算子/整图数值验收通过；失败数按 task 计，不按候选数量计。summary.json 中 candidate_failures 按候选尝试计，两者不能混用。

此前完整 Qwen 短程执行验收仍有效，但它不能证明上述另一种 ONNX 导出形式已经通过通用入口。当前这 20 张 benchmark 图没有新生成并执行成功的整图包。

## 已确定的责任边界

### A. Algo1 前端和实现候选

1. raw 图 shape 子图常量传播、场景尺寸绑定、推导及活跃 value 布局。修改 frontend/canonicalize 和 compiler/value_layout.py。未知维度不是 RTL 缺能力。
2. 数学语义统一：Gemm 的转置/alpha/beta/bias；RMSNorm 的不同展开；RoPE 的旋转子图；GELU、独立 SiLU；多输出 Split/TopK。修改 canonicalize、compiler/operand_recipes.py 及 compiler/native_macro_graph.py。不能因 Pow/Sqrt/Div 没有独立 recipe，就把完整 RMSNorm 拆成新增硬件需求。
3. 保留操作数位置和重复使用：例如 qwen35_linear 的平方 Mul 在 task.inputs 中只列一次同一 tensor，details.operation.inputs 保留两次。通用逐元素 lowering 必须用有序操作数语义，不能用依赖集合替代操作数列表。
4. 任意合法步长、广播、分段、尾块和实际地址。修改 compiler/native_macro_add_candidates.py、native_macro_concat_candidates.py、native_local_projection_candidates.py、native_macro_storage.py。现有 Add/Concat 候选要求 128 元素整行，projection 要求 128 列输出；这些不是宏算术能力的直接结论。
5. 当前 Attention recipe 要求 mask 是常量，且可见位置严格是从零开始的连续前缀。benchmark 的 mask 是图输入。固定场景可显式绑定因果/窗口 mask；数据相关 mask 则必须生成真正读 mask 的指令。不能把 runtime mask 默认为因果 mask。Gemma 滑窗需要起点和结束位置/索引集合，不能只保存 context 长度。
6. 常量 Gather/ScatterND 优先变成编译期地址变换或显式搬运；运行时索引必须保留运行时语义。
7. 批量/动态权重 MatMul、Conv、Einsum、CumSum 等形成有依赖的宏调用序列。既有 M 路径为 W8A16 静态打包权重，不能直接用于任意 S32 动态矩阵；已有 E32 点积路径应作为另一候选。
8. 图级 state/KV 的跨调用输入输出、提交和最后一次读取后的释放，属于 Algo1 的计划及场景契约；不能把 S2 图里展开的两步宣称为任意长度循环已经支持。

### B. 已有宏能力及服务 RTL

文件相对于 project/experiments/blockv2_mod/。

- rtl/macros/e_s32_mac_native.sv 已有 ADD2/ADD3、PRODUCT、CONVERT、MIN/MAX、比较、SELECT、MASK 和 MAC_BEGIN/STEP/END。它们并未全部作为独立服务开放。
- rtl/services/e32_dot_service_controller.sv 已有 EMD1：K=1..65535、1..4 个输出、4B 对齐、非负可配置步长、S32 系数后缩放。K=1 提供乘法组合路线；与常量一做点积提供求和路线；4 点深度卷积可逐通道用 K=4 点积构造。尚需地址/输出搬运/量化及整图验证。这不是已验收的新候选。
- 因而 Mul、ReduceSum、Conv、Einsum 报缺 recipe，不能直接推出必须增加乘法器、归约宏或卷积宏。优先补 Algo1，必要时为效率开放 E 的通用操作服务。
- 如增加通用 E 服务，修改/新增 rtl/services 中控制器，更新 rtl/control/e32_service_cluster.sv、hardware/native_control_routes.py、service-controller-contracts.json、描述符和 TLM。复用现有 E 宏口，控制器不得藏计算核心。
- rtl/services/gated_s32_service_controller.sv 将 cmd_gated 固定为 1；原 g_s32 宏具有 in_gated，并可输出独立激活。独立 SiLU 可选择给现有 gated 服务提供常量 one，或在服务描述符开放非 gated 模式。后者是服务控制修改，不是新增 SiLU 核心。
- rtl/services/n32_service_controller.sv 和 rtl/macros/n_s32_mod.sv 当前公开 Softmax、RMSFactor、Argmax，元素数<=4096，scalar 结果提交到 SRAM。N 内部有 exp/div/root，不等于可独立 CALL Exp/Div/Sqrt。
- Sigmoid 可考察两元素 Softmax，Tanh 可考察 2*sigmoid(2x)-1；这只是组合设计路线，尚未证明当前定点格式、搬运、截断误差和整图质量满足要求，不能标为完成。
- Softplus/独立 Exp 的合格实现尚未落实。责任是数值实现选择：已有宏指令组合/有界近似，或明确扩展 N/G 宏模式及契约。若选择后者，需同时改 n_s32_mod.sv、n_s32_reduction_engine.sv 或 G 宏及服务控制；不能在 TLM 用 Python 实现后冒充硬件已有服务。
- 现有 DRL1/DWS1 调用搬运 512B 整行。先用独占 padding、分配布局、已有 E 地址访问解决合法情形；确需短片段/非对齐写入时，应增加通用 parent 搬运/合并控制及描述符，保留 SRAM 128bit 和 DDR 512bit 宏端口。不得直接删除对齐校验让相邻数据被覆盖。
- rtl/services/indexed_gather_service_controller.sv 支持运行时索引，但表行跨度是 2 的幂、搬运按 64B 对齐、一次最多16KiB。高维专家表可考虑编译成分块、padding 的表布局；不能把 rank>2 一概当新 RTL。动态选择 M 打包权重的地址，目前没有被证实可由现有静态 projection 描述符表达。

### C. 分模型结论和实施位置

| 模型/层 | 实际特殊需求 | Algo1 要补 | RTL 责任/判定 |
|---|---|---|---|
| Qwen2.5 | 三个带 bias Gemm、RoPE 展开、输入 mask | Gemm→合法 MatMul+Add；RoPE 识别或一般逐元素候选；mask 场景绑定；Concat 片段 | 未发现因此必须修改算术宏的证据；细粒度搬运按共享方案处理 |
| Qwen3 | Q/K RMSNorm、RoPE、输入 mask | 保留额外归一化；逐元素/旋转识别与地址、mask | 已有 N/E/M/G 可作为目标；不是专门增加 Qwen3 宏 |
| Llama | RMSNorm 以 Pow→Mean→Add→Sqrt→Div→Mul 展开，非128片段 | 识别真实 RMSNorm 子图、量化 epsilon/gamma；分段打包 | 不应为这些 Pow/Div 单独新增宏；搬运服务若需要扩展由 parent 承担 |
| Gemma local/global | 多处归一化；MLP Tanh 型激活；local 滑窗 | GEMMA 激活表达式、分段广播；local mask 的窗口起点；大向量 tile | Tanh 合格数值实现待闭环，不能套 SiLU；若走 N Softmax+E 组合先补编译，若扩模式则宏/服务/TLM同步 |
| Phi | 独立 SiLU、切片/拼接、广播 | 独立激活候选、分段 Add/Concat、RoPE/mask | G 核心已有激活，选择现有 gated+one 或开放服务 gated 位；不需据此增加乘法核心 |
| Qwen3.5 global | 输出 Sigmoid gate、切片、归一化 | gate 子图、广播、mask | Sigmoid 的组合/模式数值闭环；服务接口不能假定存在 |
| Qwen3.5 linear | 8192通道、kernel4深度卷积；L2 norm；状态递推、Softplus/Exp | Conv步长；Split多输出；常量Gather/ScatterND；ReduceSum；状态版本与提交；32列小投影尾块 | Conv优先 E点积；L2是sum不是mean，不可直接冒充RMS；Softplus/Exp实现待落实；本图两个ScatterND索引是常量，无证据要求动态scatter RTL |
| Granite MoE | 40专家选8、TopK双输出、运行时Gather专家权重、批量MatMul | TopK值/索引、tie规则；rank3专家表分块；运行时选择、加权归并、动态/批量MatMul；40列小投影 | N已有Argmax但未形成完整TopK路径；动态选M权重可能要扩projection控制器的索引地址路径。静态展开全部专家+mask也可作为昂贵备选，不能伪装稀疏执行 |
| Falcon混合层 | Mamba深度卷积4608通道kernel4、CumSum3、Einsum5、Softplus/Exp、Pad/Where | scan状态、五种收缩式、padding/view/mask、RMS识别、状态持久化与生命周期 | 点积/加法/选择优先现有E；新增服务按实际需要；非线性数值实现待落实。不能把含Mamba的图塞进纯Attention模板 |

Qwen3.5 linear 的 L2 归一化可研究通过 RMS 的 epsilon 和输出系数变换实现，但有限精度下不是自动等价，必须验证。Gemma S2 可能尚未进入真正滑窗区；Falcon 即使外部 S=2，内部 padding 可到128，不能从输入长度推断内部资源需求。

Granite 的门控投影输入 [2,1536]、输出 [2,40]；TopK输出 [2,8]。专家表为 [40,1024,1536] 和 [40,1536,512]。这是真正的数据相关路径。qwen35_linear 的 Gather 多为轴2上的常量时刻索引，ScatterND 索引也为常量；两类索引不能共用“硬件缺动态路由”结论。

### D. TLM 和同一计划

现有 tlm/macro_provider_registry.py 只注册底座声明的服务并校验选中的连接。新服务需同步 tlm/macro_scalar_services.py、必要的 macro_numeric.py 和资源时序；已有 EMD1/NSV1/GSM1 组合只增加 Algo1 指令时，应继续用既有服务模型执行，不能新增模型专用整算子 Python shortcut。

计划产物必须统一绑定：source graph、hardware清单、service ABI、layout、候选连接、指令包和plan hash。一个新增实现候选必须同时包含实际宏租用、parent适配器、搬运、依赖/完成语义及成本。TLM只执行选中的包，不自己选择专家、分块或改连线；硬件服务的运行时索引行为则必须由该包的描述符明确指定。

PR185边界保持：P/U/C/F/J是控制归属，只有宏是硬边界。上述控制扩展均不能预接U→P，不应为每种模型制造一套block引出信号。算术修改若必要必须显式进入宏版本；parent仅控制、搬运、格式适配。

## 未关闭项与完成判据

本轮确定的是缺口位置、责任和可行实现方向，不声称已完成十类模型闭环。尚未决定且验证的重点是非线性精度、动态专家高效路径、细粒度搬运及长期状态；它们不能从缺recipe直接推导出“必改某算术核心”。

实施顺序：通用语义/布局/尾块 → 既有服务组合 → 必要parent服务 → 有数值依据的宏扩展。每类模型必须从原图经统一Algo1入口生成完整计划、连接和指令包，再由TLM执行同包并核对全部输出/状态。不得用逐任务通过替代整图通过，不跑禁止的P512/D128长作业。

证据：
- audits/model_path_gaps.py 和对应 sbatch
- evidence/model-path-gaps-115214/summary.json
- 逐任务完整JSON位于远端同目录（含source_model_sha256、操作、shape、所有候选错误），artifact-index.json记载大小和SHA256

