# 用现有七宏运行LLM（Issue153）

2026-11-01数值修复：仍在PR154；Llama依用户要求暂缓。同一candidate-v10代码r35的七个真实完整文本模型均通过既定短输入数值门，包含原失败Qwen2.5与Granite；旧r31/r32/r33负结果保留。新增N8激活/专家高低项权重、动态尺度SiLU，精度改善及额外存储/命令代价见[持续处理记录](../../../docs/SYSTEMC_NUMERICAL_REPAIR.md)。仅短输入证据，不代表普遍质量、长状态或硬件验收。

新增路径保留真实融合投影、模型专属RoPE、Gemma四处归一化、Qwen按头GDN及Falcon并行Attention/SSM。完整状态按8通道块在单个R上轮转；GDN每层2MiB、Falcon每层4MiB是外部模拟存储，R容量保持不变。R的S32输出与S16向量之间的RNE/二进制尺度转换是单列计数的软件格式服务，不代表已经实现相应硬件。N的EXP以零锚点取得负指数并转UQ1.31，精度仍受原表约束。

`model_support.py`只加载文本检查点，逐张量严格核验；Gemma视觉塔、Qwen视觉塔及MTP明确排除。RoPE参数覆盖本次文本token位置；没有证明多模态或长上下文。本轮A_log的指数和有效gamma准备为静态参数变换，运行时向量计算仍走宏命令。

问题排查与覆盖情况见[逐步记录](../../../docs/SYSTEMC_LLM_INFERENCE_JOURNAL.md)，原始数值回执在[results](results/)。本目录增加控制/存储适配器，没有改七宏、RTL或物理流程。`continuation-r9`为四种真实检查点首轮，`continuation-r12`保留一次不理想的七模型回归，`continuation-r10`明确是随机小配置结构测试；各轮源/程序/输入/输出绑定在对应index/audit中。Llama未绑定真实检查点，按用户要求暂缓。

## 程序分别做什么

- `runtime.hpp`：七个真实SC_THREAD及深度1命令/响应FIFO；M矩阵分块，N归一化/Softmax/TopK，E逐元素/移位/RoPE，G激活，S有限回放，T有限结果交接。Tensor的raw为S16；有外部`lane_e`时真实值为`raw[i] × 2^lane_e[i]`，否则使用统一exponent。
- `llm_bench.cpp`：完整embedding→所有decoder层→最终norm→完整词表→greedy token回送；支持本轮七种具体配置。Phi融合QKV/gate-up、Gemma局部/全局注意力与四norm、Qwen3.5 GDN/Attention门控、Falcon并行SSM/Attention分别实现，不将它们套成普通Qwen。
- `gdn_bench.cpp`：单R轮转Qwen3.5的32头×16个value块，逐步读写外部完整状态；输入边界已由参考准备，不是完整Qwen3.5。
- `tools/export_checkpoint.py`：只读已有真实检查点、量化权重、导出tokenizer输入、独立原权重FP32参考。
- `tools/validate_inference.py`：比较逐层隐藏状态和logits，解码实际输出；如输入prefix分叉，以积木实际prefix重跑FP32参考。
- `tools/export_gdn.py` / `validate_gdn.py`：真实首层投影产生的R输入和官方递推真值、完整状态/读出误差检查。

PyTorch只在导出/独立参考阶段使用。C++模拟器不链接torch，不用主机浮点矩阵乘法提供任何层的结果。主机的外存寻址、参数准备和**数值尺度选择**仍是显式软件服务；这不是无外部控制器的完整芯片。

## 数值修正版与验收

修正版使用`LLM_PRECISE_ADAPTER=1`，旧默认路径仍用于历史对照；`tools/run_regression.sbatch`显式设置该选项。实现包括M宽累加后再舍入的残差相加、安全15位幅度、融合Norm、Softmax差值保护、RoPE旋转裕量及小Softplus范围归约。Falcon还修正B/C的R接口尺度补偿，并删除旧导出器错误覆盖的注意力缩放。已有旧Falcon导出要用`repair_falcon_metadata.py OLD NEW`创建修正版，不能只换模拟器而继续使用错误metadata。

门限由`tools/assess_numerics.py RUN/validation.json`独立判定，返回0=通过、1=数值失败；输入损坏另报错。要求所有处理位置Top1一致、独立greedy序列一致、logits cosine≥.999且rel-L2≤5%、每个已记录hidden cosine≥.995且rel-L2≤10%。Slurm成功和token吻合不能替代这些检查。最终r35证据在`results/continuation-r35/`；旧r31及N8候选r28/r33均为5/7，负结果单独保留，未拼接择优。

可选N8权重格式使用`metadata.txt`中的`weight_group_rows 8`和`weights.scales`：每行`参数名 组数 e0 e1 ...`，组数为输出行数向上除8；raw仍是S16，按组解释指数。`requantize_groups.py OLD NEW`从原始矩阵重新导出，非矩阵参数保持原导出字节，严格绑定源SHA；不会从旧量化值虚构精度。`run_grouped_weights.sbatch`运行该候选，其单独使用没有通过全部七模型，不替代原导出默认。缺失必需尺度表或专家边界不对齐时拒绝运行。

r35复现必须同时设置`LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1`，见`tools/run_accurate_silu.sbatch`。稠密/MoE采用小块激活尺度；R系列保持uniform状态合同。`export_expert_residuals.py GROUPED_OLD NEW`从原权重求Granite专家高项残差，追加`.low`参数及其N8指数；`weight_residual_terms 2`必须与索引/尺度配套。专家矩阵高低项多周期合并后一次舍入，增加权重和MAC。精度路径未默认开启，旧入口继续用于历史对照。

准确SiLU经N的范围归约EXP及M/E的余量修正、4次Newton倒数迭代实现；正端保留小修正，负端动态尺度保留尾量。不能用旧G调用次数断言所有模型必用G；Gemma GELU和递推模型其他函数仍调用G。回执记录实际事务、尺度物化和统一转换，不把扩展host元数据计入S/T原生容量。

新增`diagnose_dense_layer.py`与`diagnose_quantized_model.py`只提供独立诊断，绝不把高精度激活或答案注入SystemC。小结构fixture的通过证据与真实预训练模型分开。当前仅短输入功能/数值证据；长上下文、长递推、多样输入和硬件实现仍需另行验证。

## 编译和自测试

在Linux/WSL，按上一级说明安装本地SystemC3.0.1；在仓库根执行：

```bash
cmake -S project/systemc -B project/systemc/build-llm \
  -DCMAKE_PREFIX_PATH="$PWD/.systemc-deps/install" \
  -DCMAKE_BUILD_TYPE=Release -DBLOCK_SANITIZE=ON
cmake --build project/systemc/build-llm -j4
ctest --test-dir project/systemc/build-llm --output-on-failure
```

新增适配器测试包含M的非整块尺寸、长Softmax、宽SiLU/GELU、RMS/L2及4096维离群值、有限S/T、超过16位ID的词表、跨token K尺度差15bit、两头两步GDN/SSM及skip。四种两层随机结构fixture另由官方框架校验，并在本地UBSan重跑比较完整hidden/logits。UBSan缺失的服务器可明确设OFF；不能把该次运行称为UBSan检查。模型和数据均按本轮实测的x86 little-endian格式，不声称MSVC/任意端序支持。

## 真实检查点运行

`SOURCE`必须是已有并有权读取的检查点目录。导出目录要求尚不存在，避免覆盖旧实验。Python环境需要torch/transformers/safetensors/numpy，已测torch2.10.0+cpu、transformers5.20.2。服务器上的重任务通过Slurm脚本运行。

```bash
python project/systemc/llm/tools/export_checkpoint.py \
  --model "$SOURCE" --out "$CHECKPOINT" \
  --prompt 'The capital of France is' --new-tokens 3
mkdir -p "$RUN"
project/systemc/build-llm/llm_bench "$CHECKPOINT" "$RUN"
python project/systemc/llm/tools/validate_inference.py "$CHECKPOINT" "$RUN"
```

上例导出器用于原Qwen/Granite配置；Phi/Gemma/Qwen3.5/Falcon改用同参数的`tools/export_remaining.py`。该导出器严格加载本地文本参数，逐项检查映射及缺失，不执行远端代码；在实际执行节点先有界顺序只读预取，避免冷mmap瓶颈。

可选第四个命令参数`MAX_STEPS`用于限制处理位置数，属于诊断，不能冒充完整运行。`LLM_FIRST_LAYER_ONLY=1`只导出首层内部trace，不生成整网完成回执。`LLM_TRACE_LAYER=30`保存指定层首步的中间值，仍正常运行全部层。`LLM_NORM_FUSED=1`启用融合缩放gamma适配；默认单位N后E乘gamma，只有单位结果超出S16正幅值范围才右移单位gamma并补偿外部指数，两者误差对照必须读具体回执，不能只凭名字判断更好。

本轮服务器脚本含本任务绝对路径，仅为可复现作业记录；换机器需修改任务ROOT和Python/检查点来源，不能直接向他人目录写入。`run_six.sbatch`在一个8CPU allocation内运行6个独立单线程任务，即完补位；运行前检查真实MemAvailable。`run_compare.sbatch`用于3模型的改进尺度对照。每版源码和构建目录独立，防止tar时间戳导致复用旧对象。

本次`run_regression.sbatch REV`先在8CPU内编译，再以`xargs -P6`动态运行七个独立模型；每个模拟器及参考限制1线程。`audit_regression.sbatch REV`独立在6CPU资源内核对完整权重及输出SHA、层数/词表/记录数/宏事务。`prefetch_checkpoints.sbatch`与`audit_remaining.sbatch`保留首轮94520/94521的实际脚本，不覆盖历史目录或运行输入。

## 输入与输出

`weights.index`每行：`name rows cols exponent byte_offset`；`weights.bin`为little-endian S16。三维MoE权重仅按expert连续展平，expert索引/矩阵切分在控制器明确执行。`metadata.txt`包含真实头数/维数、RoPE theta、模型专属缩放等，缺失/非default RoPE不静默回退。

`systemc_hidden.bin`与`systemc_logits.bin`统一尺度张量依次记录`int32 exponent, uint32 count, int16[count]`；exponent为INT32_MIN时，在count后增加`int32[count]`逐元素指数，再存`int16[count]`。验证器和审计均识别这项显式格式；每个位置的hidden为embedding、各层边界、最后最终norm，共layers+1项。`systemc_receipt.json`记录输入/预测/生成ID、M MAC数学计数、各宏事务/饱和数及主机耗时；`validation.json`保留独立参考、逐步/逐层误差和哈希。

源检查点、量化二进制和完整激活存放本任务服务器目录，禁止误入Git；仓库只收小型回执、权重索引与哈希。源检查点SHA见export receipt，实际执行程序和源码包SHA见run-inputs。

## 能据此得出的结论

可以验证有限积木经显式调度，确实完成多个完整LLM的短序列推理；可以定位数值、缓存、接口和状态轮转问题。旧轮次的量化预测分叉继续保留；r35短输入过门仍不能证明与原模型普遍等价。

没有模拟时钟/链路延迟/DRAM带宽，不提供tokens/s芯片预测，不代替RTL等价或布局布线验收。完整权重、激活、KV、R跨头状态是外存；S仅16KiB，T仅6KiB。稠密及Granite网络R事务数为0是正确的功能映射。
