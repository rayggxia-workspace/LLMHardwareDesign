# Granite3.1-3B-A800M最小实验

Issue70；此页记录生产协议，实际执行与结果须以manifest/作业回执为准。

官方config为40专家、top8、H1536、专家中间512、32层，含完整GQA。MoE新增的路由、稀疏权重访问、分发/收集、不同expert输出scale合并将检验V/M/S/D边界；不新增固定“专家宏”假设。

`granite.py capture --model MODEL_DIR --binding BINDING.json --out NEW --threads 8`
冻结B1/prefill64+teacher-forced cached decode8，独立校准/评价固定文本，chunk16对照。CPU FP32由原始BF16权重cast，仅layer0完整MoE转存。核验完整expert路径重放，失败不接受后续量化证据。源码binding要求`commit`与`granite_sha256`，可加`model_revision`；model所有权重和配置运行时逐文件SHA，安装HF实现另存并SHA。

官方参考：[模型config](https://huggingface.co/ibm-granite/granite-3.1-3b-a800m-instruct/raw/main/config.json)、[HF实现](https://github.com/huggingface/transformers/blob/main/src/transformers/models/granitemoe/modeling_granitemoe.py)。运行时实现以manifest SHA为准，不能把动态网页main当固定版本证据。布局只支持两种明确形式并以完整MoE输出重放确认。

参考完整/cached/chunk门：relative L2≤2e-4且max abs≤2e-3；仅参考一致性，非语言能力、全模型量化或目标硬件接受标准。性能测量未执行。

`granite.py numeric --capture CAPTURE_DIR --binding NUMERIC_BINDING.json --out NEW`

数值最小集为评价prefill位置60–63、decode位置64–67，每token完整top8路径；两种激活scale（独立calibration前64token固定的tensor scale、动态token-row scale），两种路由（FP固定仅诊断、W8A8 router重算top8）。W为每expert每output行maxabs对称INT8、A为对称INT8[-127,127]；RNE ties-even，实际饱和单列；完整K的INT32最坏界先检查，软件用NumPy INT64算dot以便检查，不称原生INT8内核。H1536 dot上界127²×1536=24,774,144；专家down K512更小。未分K则不能将不同单位的partial sum直接相加。

完整专家gate/up和down均做整数dot；中间dequant/SiLU/门乘/重新选A scale、router scale转换/softmax仍是显式FP64桥。不能据此称全整数MoE。动态与静态激活都保存其scale来源、溢出、饱和与真实路由翻转。

增加共同单位合并候选：仅根据校准MoE输出最大值，选power-of-two unit，使校准值约占23bits；各expert down的S32结果以Q31 multiplier和int16 shift转换为共同S32（饱和/RNE明确），路由权重Q0.15；S64权重乘积/8路求和，RNE15及S32饱和得到输出。该方案对宽乘和64bit合并有需求，尚未提供8bit单元lowering周期，不能当成已支持硬件。Q31参数生成和scale选择仍用浮点，元数据/运算成本明确待资格验证。

输出`metrics.json`（8个phase候选、误差/负载/逻辑字节）、`witnesses.npz/json`（32实际完整K dot、32实际RQ、每4个候选一个token完整8×1536共同单位合并）。独立receiver验证后才可称见证通过；不从小样本或零饱和推断全模型质量通过。逻辑数据量分别列A8、S32、route id/weight、FP64 scale与Q31/shift；未测header/物理beat、权重驻留和多播，不能将其当硬件端口/周期结论。完整40专家层权重原FP32约377MB，大文件仅授权服务器存储，仓库保存位置/SHA。

## 原生chunk失败的最小定位

`granite_diagnose.py --model MODEL_DIR --capture FAILED_CAPTURE --binding JSON --out NEW --threads 8`

binding含`commit`与`granite_diagnose_sha256`。严格核原失败manifest、全部artifact及原模型文件SHA，复用其72个评价token、原模型revision、原框架实现SHA、FP32/eager和原门；不重下权重，不改原capture。

四个独立profile：原生full72、原生cached64+8、原生chunk16、chunk16固定full-run每层每token专家ID（当前logits重新softmax）。最后一个是**改变路由算法的反事实诊断控制**，不能替换原生参考或声称PASS。保存32层每token router输入/logits/top8 ID/weight、MoE和层输出以及LM logits；比较首个集合变化层、top8/9 margin、输入/输出误差和固定ID后剩余差异。固定ID显著压低误差只能支持路由非连续性放大，不能证明全部误差来自特定浮点算子或据此放宽门。原失败和全模型质量/硬件未验状态持续保留。

数值入口默认拒绝FAIL capture。只有显式`numeric --diagnostic-failed-chunk`，并逐项核验原阈值未变、cal/eval完整cached及MoE replay均过、cal chunk16过、仅evaluation.chunk16失败，才允许复用完整layer0真实FP32张量做局部整数/结构诊断。输出状态固定为`PARTIAL_DIAGNOSTIC`，`reference_qualification.capture_status=FAIL`、`chunk_reference_accepted=false`和完整原失败/阈值链均写入manifest与metrics；独立receiver同样须显式接受这个收窄范围。此开关不修改原捕获、不放宽门、不使chunk/整图参考或全模型量化质量通过。

独立定位接收：`verify_diagnose.py --diagnostic DIAG_DIR --capture ORIGINAL_FAIL_DIR --producer FROZEN_DIAG_PY --capture-producer FROZEN_CAPTURE_PY --binding JSON --out NEW`。binding含`commit`、`verify_diagnose_sha256`。此接收器不导入生产脚本，逐一核实际源码、两个manifest与全部artifact SHA；从routes.npz重核四profile×32层全部native top8分数集合/顺序（精确tie允许任一合法cutoff选择）、FP32 softmax权重、固定ID身份、96个路由比较记录、首变化层/margin和完整LM误差，并将full layer0/末token logits链接回原失败capture实际张量。结果只写`DIAGNOSTIC_WITNESS_VERIFIED`，强制保留原FAIL与反事实不属于reference，不能据控制组数值接近而改门或替换参考。
