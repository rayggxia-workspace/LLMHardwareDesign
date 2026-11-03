# Qwen3-0.6B layer0 数值门：执行与证据边界

以下保留工具作者的微自检和ABI说明；后续服务器真实数据数值/RTL结果见[实际回执报告](QWEN_LAYER0_NUMERIC_RTL_REPORT.md)，不据此接受完整模型质量。

Issue151/PR152，Melodydt；输入 `71c819c2` 对应的新研究包。模型数据仅接受官方 `Qwen/Qwen3-0.6B` 的固定 revision `c1899de289a04d12100db370d81485cdf75e47ca`。本包不修改旧 RTL 或原模型准入表。实际真实数据计算由根代理在服务器 Slurm 启动；本代理已做的是 Python 语法和纯 C++ 数学微自检，没有运行本地 RTL。

## 数据 ABI 与入口

```text
python run_qwen_layer0.py --data-dir EXTRACTOR_OUTPUT --output NEW_RESULTS_DIR --engine-source qwen_layer0_numeric.cpp --threads 8
```

`NEW_RESULTS_DIR` 必须不存在，结果目录不覆盖复用。数据目录 `manifest.json.status` 必须严格为 `COMPLETE_SELECTED_TENSORS_AND_ROWS`。提取器提供11个 layer0 tensor 和少量真实 embedding 行，保存原生 row-major BF16 rawbits 与其精确扩展的 little-endian F32；没有 NumPy、Torch、Tokenizers 依赖。桥接器验证各自长度、SHA，并逐 scalar 验证 `F32bits=BF16bits<<16`；所有数据路径必须留在提取目录内。

11个 tensor 为 input/post-attention RMS gamma、Q/K/V/O 投影、Q/K headNorm gamma、MLP gate/up/down。Q 权重为 `[2048,1024]`，K/V `[1024,1024]`，O `[1024,2048]`，MLP gate/up `[3072,1024]`、down `[1024,3072]`；input/post gamma 为1024、Q/K gamma为128。全部 layer0 共15,730,944个 BF16 值，即31,461,888B BF16 /62,923,776B F32；embedding 行另计。

输入 `token-sequences.json` 有 `token_sequences:[{id,split,pieces,token_ids}]`。当前提取方案为2个 cal prefix 和2个 eval prefix，每个4 token，共16真实行；这是精确 vocab pieces 拼接的工程诊断，没有假装重新执行 BPE，也不是代表性校准语料。工具支持每 prefix 1..16 token、单 batch、位置0..S-1、无 padding、无 KV cache。相同完整 token 序列不能跨 cal/eval，两个 split 都必须存在。

## FP32 参考切口

独立 C++ 引擎执行完整 layer0 语义：input RMS1024；Q16/KV8、每 head128 的 Q/K RMS；split-half RoPE，theta1e6；每两个相邻 Q head 复用一个 KV head；causal score/Softmax/PV；O2048→1024；得到 `Y=X+O(attention)`。F 参考为 `Y+Down(SiLU(Gate(postRMS(Y)))*Up(postRMS(Y)))`，使用真实 post-attention gamma 和三矩阵。

FP32 乘加按每行顺序执行，编译 `-ffp-contract=off`，只并行独立输出行，不改变每行归约顺序。RMS epsilon 为源配置的 `1e-6`。这是独立的 FP32 算法实现；没有对实际 prefixes 与 Torch/ONNX 做输出对照，不声称官方 BF16/SDPA/FlashAttention 或 Torch 的位等价。

算法锚点取根代理提供的官方 Transformers v4.51.0 文件，Git blob `5fec83d47888e44a0f3e0ffb2b067ce08e4712d3`：headNorm L195–196、Q/K 路径 L217–218、split-half L98–102、KV repeat L132–141、scale L179、Attention residual L284–300、postNorm/F residual L303–306。该实现来源与 checkpoint revision 分别记录，不能把实现 tag 当作权重来源。

官方来源：[pinned config](https://huggingface.co/Qwen/Qwen3-0.6B/raw/c1899de289a04d12100db370d81485cdf75e47ca/config.json)，[Transformers v4.51.0 Qwen3](https://github.com/huggingface/transformers/blob/v4.51.0/src/transformers/models/qwen3/modeling_qwen3.py)。

## 有限整数候选

只量化 F(Y)，Attention 仍为 FP32，避免把未实现的大 Attention 整数路径藏进本轮结论。baseline 完全对应当前 F1024 的 S16 Fin10 /S8 Fin7 /epsilon_code1 /M factor1,left0,READright7。

候选域固定为8个组合：baseline；每矩阵按完整权重最大值选无 clip 的 power-of-two WFin（0..15）后，XFin/NormFin 为10/10、12/10、12/12、14/12、14/14；另有 WFin 各少1或多1、X12/Norm12 两个对照。权重尺度只依据固定参数，不使用 eval 激活。不可表示的 M 右移候选被明确排除并记录，不能默改为别的算术。

N 严格使用整数合同：`rad=((sum(xcode²)<<16)//1024)+(epsilon_code<<16)`，`factor=2^38//isqrt(rad)`，`out=RNE(xcode*gammacode*factor,30)`，最后 clipS16。Norm 输出 Fin 由 gammaFin 决定。XFin10/12/14 分别给出 epsilon_code1/17/268，实际 epsilon 为 code/2^(2XFin)，不是统一强写1，也不把舍入0当合法 epsilon。

G 的 gate/up 输入与 mid 输出始终 Fin10。gate/up M READ 右移为 `NormFin+WFin-10`，down 为 `10+WdownFin-XFin`；down、原始 Y 残差、最终输出同 XFin。所有候选 factor1,left0、READright0..63，完整 K 归约后才 RNE/clip；G 数学重建表与原生插值/RNE10/clip 语义一致。

除 baseline 外，候选都需要新的静态 top/profile 常量或预制参数路径。现有叶宏具有 SCALE/READ 参数，不代表现有 F1024 top 已有配置接口；不能只换 weights_version 或 provider 数据就改变 epsilon/shift。当前文件仅是候选数值评估，未授权硬件接受。

## 统计、选择和真实 RTL fixture 导出

`numeric-summary.json` 对每候选分别给 cal/eval 的 input、Norm、gate、up、mid、down、output：元素数、clip数/比例、RMSE、最大绝对误差、relative L2、cosine 和幅值；另列 gamma/三矩阵离线参数 clip。参考向量全零时 relative L2 使用绝对 L2 回退；cosine 在零范数时为 null。候选只按 cal 输出 relative L2 选择，选择完成后才执行 eval 整数量化；没有依据 eval 调参，也没有预设模型质量接受阈值。

导出 baseline 和 cal-selected 的每个 prefix 最后一个 token，至少各包含 cal/eval 行；若 selected 就是 baseline，文件不重复。目录：

```text
rtl_exports/PROFILE/weights-stream.bin       # 9MiB canonical请求顺序，整profile复用
rtl_exports/PROFILE/gate.s8 up.s8 down.s8   # 三个native row-major S8矩阵
rtl_exports/PROFILE/gamma.hex                # 128字
rtl_exports/PROFILE/CASE_posN/input.hex       # X 128字
rtl_exports/PROFILE/CASE_posN/gamma.hex       # gamma小alias
rtl_exports/PROFILE/CASE_posN/norm.hex        # 128字
rtl_exports/PROFILE/CASE_posN/gate.hex        # 384字
rtl_exports/PROFILE/CASE_posN/up.hex          # 384字
rtl_exports/PROFILE/CASE_posN/mid.hex         # 384字
rtl_exports/PROFILE/CASE_posN/down.hex        # 128字
rtl_exports/PROFILE/CASE_posN/output.hex      # 128字（另有expected-output.hex alias）
rtl_exports/PROFILE/CASE_posN/expected-saturated.hex
rtl_exports/PROFILE/CASE_posN/fixture.json
```

每行 hex 是128bit，lane0位于低16bit；二进制数据为 little-endian。canonical 权重流是 gate/up 按384组交替、每矩阵32个 K32 chunk，再 down128组×96chunk；每 chunk tile-major/n-major/K8，16拍×16B，共36,864请求、9,437,184B。实际长度/SHA、静态 N_EPSILON/M_GATE_SHIFT/M_UP_SHIFT/M_DOWN_SHIFT 与各阶段 SHA 写入 `rtl-fixture-index.json`，不是给运行时装程序。

`expected_native_done_saturated` 只 OR native N/M/G/E 算术 clip；离线输入、gamma、权重量化的 clip 单列，不错误冒充硬件 done_saturated。导出 golden 是完整原生整数计算结果，不是把 FP32 最终输出临时量化后伪作整数 oracle。后续服务器 RTL 必须按 profile 常量分别编译并核验 binding，实际 accepted 权重流另验 SHA。

## 本轮证据边界

本地已执行 Python语法检查，以及 MinGW g++14 的纯数值编译/微 selftest：非对称 row-major linear、不同 head 的 RMS、RoPE pos0/pos1 两个 basis、GQA head映射、causal Sq1与Sq2手算、signed RNE、floor sqrt、N输出 gammaFin、全 K 后RNE、G数学值与饱和。它们不替代服务器 g++11.4、真实 checkpoint 数值运行、Torch/ONNX 对照或 RTL 功能验收。

真实 layer0 小 prefix 的整数匹配、FP32 误差、完整模型质量、全词表 logits、端到端生成、共同底座/物理验收均分别记录。本轮没有据此修改旧准入状态，也不声称4个小 prefix代表模型质量。
