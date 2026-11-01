# 用现有七宏运行LLM（Issue153）

2026-11-01续办：仍在PR154；用户暂缓Llama，新增Phi/Gemma/Qwen3.5/Falcon的文本路径正在验证。导出入口为`tools/export_remaining.py`，R连接见`recurrent.hpp`。新增代码尚不等于四种完整推理已通过，以逐步记录和实际结果为准。

新增路径保留真实融合投影、模型专属RoPE、Gemma四处归一化、Qwen按头GDN及Falcon并行Attention/SSM。完整状态按8通道块在单个R上轮转；GDN每层2MiB、Falcon每层4MiB是外部模拟存储，R容量保持不变。R的S32输出与S16向量之间的RNE/二进制尺度转换是单列计数的软件格式服务，不代表已经实现相应硬件。N的EXP以零锚点取得负指数并转UQ1.31，精度仍受原表约束。

`model_support.py`只加载文本检查点，逐张量严格核验；Gemma视觉塔、Qwen视觉塔及MTP明确排除。RoPE参数覆盖本次文本token位置；没有证明多模态或长上下文。本轮A_log的指数和有效gamma准备为静态参数变换，运行时向量计算仍走宏命令。

问题排查与八模型覆盖情况见[逐步记录](../../../docs/SYSTEMC_LLM_INFERENCE_JOURNAL.md)，原始数值回执在[results](results/)。本目录增加控制/存储适配器，没有改七宏、RTL或物理流程。Qwen3、Qwen2.5、Granite已有真实全网络自回归执行；Qwen3.5仅有真实权重R边界验证，其余模型不能标成已推理。

## 程序分别做什么

- `runtime.hpp`：七个真实SC_THREAD及深度1命令/响应FIFO；M矩阵分块，N归一化/Softmax/TopK，E逐元素/移位/RoPE，G激活，S有限回放，T有限结果交接。Tensor的真实值为`raw × 2^exponent`，raw是S16。
- `llm_bench.cpp`：完整embedding→所有decoder层→最终norm→完整词表→greedy token回送。支持Qwen2/Qwen3的本轮配置和Granite MoE；不偷偷把未适配的其他family当作Qwen。
- `gdn_bench.cpp`：单R轮转Qwen3.5的32头×16个value块，逐步读写外部完整状态；输入边界已由参考准备，不是完整Qwen3.5。
- `tools/export_checkpoint.py`：只读已有真实检查点、量化权重、导出tokenizer输入、独立原权重FP32参考。
- `tools/validate_inference.py`：比较逐层隐藏状态和logits，解码实际输出；如输入prefix分叉，以积木实际prefix重跑FP32参考。
- `tools/export_gdn.py` / `validate_gdn.py`：真实首层投影产生的R输入和官方递推真值、完整状态/读出误差检查。

PyTorch只在导出/独立参考阶段使用。C++模拟器不链接torch，不用主机浮点矩阵乘法提供任何层的结果。主机的外存寻址、参数准备和**数值尺度选择**仍是显式软件服务；这不是无外部控制器的完整芯片。

## 编译和自测试

在Linux/WSL，按上一级说明安装本地SystemC3.0.1；在仓库根执行：

```bash
cmake -S project/systemc -B project/systemc/build-llm \
  -DCMAKE_PREFIX_PATH="$PWD/.systemc-deps/install" \
  -DCMAKE_BUILD_TYPE=Release -DBLOCK_SANITIZE=ON
cmake --build project/systemc/build-llm -j4
ctest --test-dir project/systemc/build-llm --output-on-failure
```

新增适配器测试包含M的非整块尺寸、长Softmax、宽SiLU、RMS、有限S/T、超过16位ID的词表、跨token K尺度差15bit。UBSan缺失的服务器可明确设OFF；不能把该次运行称为UBSan检查。模型和数据均按本轮实测的x86 little-endian格式，不声称MSVC/任意端序支持。

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

可选第四个命令参数`MAX_STEPS`用于限制处理位置数，属于诊断，不能冒充完整运行。`LLM_FIRST_LAYER_ONLY=1`只导出首层内部trace，不生成整网完成回执。`LLM_NORM_FUSED=1`启用融合缩放gamma适配；默认单位N后E乘gamma，两者的误差对照必须读具体回执，不能只凭名字判断更好。

本轮服务器脚本含本任务绝对路径，仅为可复现作业记录；换机器需修改任务ROOT和Python/检查点来源，不能直接向他人目录写入。`run_six.sbatch`在一个8CPU allocation内运行6个独立单线程任务，即完补位；运行前检查真实MemAvailable。`run_compare.sbatch`用于3模型的改进尺度对照。每版源码和构建目录独立，防止tar时间戳导致复用旧对象。

## 输入与输出

`weights.index`每行：`name rows cols exponent byte_offset`；`weights.bin`为little-endian S16。三维MoE权重仅按expert连续展平，expert索引/矩阵切分在控制器明确执行。`metadata.txt`包含真实头数/维数、RoPE theta、模型专属缩放等，缺失/非default RoPE不静默回退。

`systemc_hidden.bin`与`systemc_logits.bin`按张量依次记录`int32 exponent, uint32 count, int16[count]`；每个位置的hidden为embedding、各层边界、最后最终norm，共layers+1项。`systemc_receipt.json`记录输入/预测/生成ID、M MAC数学计数、各宏事务/饱和数及主机耗时；`validation.json`保留独立参考、逐步/逐层误差和哈希。

源检查点、量化二进制和完整激活存放本任务服务器目录，禁止误入Git；仓库只收小型回执、权重索引与哈希。源检查点SHA见export receipt，实际执行程序和源码包SHA见run-inputs。

## 能据此得出的结论

可以验证有限积木经显式调度，确实完成多个完整LLM的短序列推理；可以定位数值、缓存、接口和状态轮转问题。仍有量化预测分叉，不能只凭输出可读就宣称与原模型等价。

没有模拟时钟/链路延迟/DRAM带宽，不提供tokens/s芯片预测，不代替RTL等价或布局布线验收。完整权重、激活、KV、R跨头状态是外存；S仅16KiB，T仅6KiB。稠密及Granite网络R事务数为0是正确的功能映射。
