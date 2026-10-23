# 给师兄 Codex 的实验文案（可复制正文）

以下是实验请求，尚未在师兄电脑执行。用户可直接复制“请求正文”交给师兄的Codex。
来源：Liangruizhi Issue39；先读PR38的架构筛选、PR34精度合同及当前Issue32/PR36。
这份文案不表示师兄已接受新增任务，也不表示其在途工作完成。

## 请求正文

请在 `https://github.com/rayggxia-workspace/LLMHardwareDesign` 推进差异LLM工作负载的GPU实验，
服务于共同问题：哪些计算、状态、通信应固定在Block内，哪些连接留待产品后定制，以及真实约束下的端到端收益。
请自主决定常规实现并记录原因；仅在关键权限/数据或原则性问题无法解决时提问。

### 先核对协作和执行环境

1. 读取最新AGENTS、`.agents/skills/rayggxia-project-collab/SKILL.md`、README、project.json、
   docs/COLLABORATION、docs/STATUS、本人进度、相关Issue/PR/评论和未合并分支交接。
   核验执行者本人获授权的GitHub身份、仓库/remote、当前工作目录/未提交改动及已有运行任务。
   Liangruizhi是本机小模型工作的作者，执行者的实际登录身份按本人授权与项目规则核验。
2. **先恢复Issue32/PR36已有Qwen任务**，复用正在做的修复和结果，不重新开一个同范围任务。
   本机Issue39只做小切片整数/归约/边界记账，不接管GPU。新增Gemma工作若无已有Issue，
   按Skill创建由执行者承担的独立任务、分支与工作目录；Phi后置。保留其他成员的改动/运行任务。
3. 读取PR38中的docs/MODEL_ARCHITECTURE_REVIEW.md、PR34中的INTEGER_PRECISION_CONTRACT.md、
   GPU_CAPTURE_CONTRACT.md和capture.schema.json；未合并依赖用明确commit/PR版本，不假设已在main。
   实际执行源码、dirty状态、依赖commit、模型/数据版本都固定后再运行。
4. 仅用师兄本次获授权的16GB GPU及本地目录，单次只驻留一款模型。记录GPU/驱动/CUDA/
   框架/量化库、可用显存和峰值allocated/reserved。内存下界不是可运行保证；先保留约2GiB裕量。

### 模型顺序与作用

| 顺序 | 模型 | 实验目的与范围 |
| --- | --- | --- |
| 1，已有任务 | Qwen/Qwen2.5-3B-Instruct | 普通全局GQA、KV增长、QKV bias、矩阵/RQ边界，复用已有权重与修复 |
| 1，已有任务 | Qwen/Qwen3.5-4B | 混合递推/卷积/全局注意力、宽状态与反馈，优先解决已有长状态等价问题 |
| 2，有条件新增 | google/gemma-3-4b-it，纯文本 | 局部/全局注意力、QK norm、多处norm与GELU，增加结构覆盖 |
| 3，策略冻结后 | microsoft/Phi-4-mini-instruct | 融合投影、部分RoPE/LongRoPE及数学/代码质量，唯一默认保留验证 |

Qwen3-0.6B本机已有，不要求师兄重复；Qwen3-4B、Gemma12B、Llama/R1蒸馏及大MoE不列本轮必跑。
Gemma12B若后续做4bit，另立精确W4A16/NF4/GPTQ/AWQ等合同，不混入W8A8主结论。
本轮不宣称原生DeepSeek-R1 MoE/MLA或视觉路径得到端到端验证。

公开配置审查版本：Qwen2.5 `aa8e72537993ba99e69dfaafa59ed015b17504d1`；
Qwen3.5 `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`；
Gemma `093f9f388b31de276ce2de164bdc2081324b9767`；Phi `cfbefacb99257ffa30c83adab238a50856ac3083`。
这些是版本线索，仍需核对本次实际权重/配置/分词器。已有Qwen实验若不同revision，保留并记录差异，
不要为了匹配上述线索重复下载。Gemma本机访问config得到401：仅使用执行者已经获授权的官方访问，
缺权限则记录阻塞并继续Qwen，不代用户接受许可、不用镜像或框架默认配置填空。

### A. 先验正确性，失败时优先定位

- 首先B1、prefix128、teacher-forced追加16；对相同token IDs/mask/position比较完整prefix、
  cached decode和不同chunk，保存误差/finite检查。FP16可作为起点，但要与原生BF16和关键算子FP32
  对照，分别冻结适合各dtype/backend的容忍，不能把FP16称为FP32高精度oracle。
- Qwen3.5优先定位已有长状态不等价：固定相同初始conv/recurrent state、token顺序与chunk边界，
  分别保存卷积历史、递推q/k/v、beta/decay、state更新和全局KV；核dtype/layout、归一化、
  门控、cache_position以及所用chunk/fused kernel。逐步定位第一个分歧，不能用更宽容阈值掩盖错误。
- Gemma按真实config核验局部/全局层表、head_dim、窗口及RoPE；围绕实际窗口w跑w-1/w/w+1，
  不把1024论文值或4096框架默认值代替checkpoint。检查gamma是否为1+weight、pre/post norm、GELU
  及cast顺序。优先memory-efficient SDPA/GQA；保存与小长度eager的数值对照。
- Phi仅允许事先做结构/访问/适配准备，正式trace/质量/性能留到Block策略及接受准则冻结后；
  实测LongRoPE的4095/4096/4097边界与对应实现，记录是否需要整段重算缓存。
- 任一prefix/cached/chunk等价未通过，先保存失败及最小反例，相关长上下文/划分结论保持pending。

### B. 精度与质量，逐因素再组合

目标合同是**候选W8A8矩阵、INT32累加**。逐项记录W/A/KV/acc/conv/state/probability/norm/scale，
不能把状态默认降成8位。分别报告integer_kernel、integer_reference、fake_quant和浮点回退。

沿用已有预先冻结的校准/评价协议；新增方法在看评价结果前冻结数据revision、文档/样本范围、
SHA、分词/chat模板、随机种子及预算。校准用训练集，评价用不重叠测试集；不能只用前8token。
先权重量化、激活量化、KV、conv/state单独消融，再组合，保留所有失败。动态scale和静态scale分开，
校准冻结的平滑与“在当前评价张量上拟合”分开，后者只能作误差定位。

重点补充：

1. Qwen2系QKV bias：保存acc、真实bias、输入/权重scale和bias量化规则；动态每行A scale对应
   不同bias整数。acc+bias可能需33位，不能套无bias RQ32接口；保存M/r、舍入、饱和/溢出。
2. **post norm/RoPE的Q/K outlier**：本机单头探索发现直接8位K可造成很大注意力输出误差；
   请在独立校准/评价数据核实各层/头的max、分位数、通道分布和attention输出/NLL。
   比较直接量化与预先冻结的逐通道对角平衡候选时，明确乘在RoPE前还是后、GQA头共享约束、
   是否能折进投影/Norm、是否破坏RoPE配对和额外转换成本。不能用本机同张量拟合的改善作为质量验收。
3. **K scale在softmax前、V scale在PV归约内**：保存至少两个不同scale的真实块及完整归约维度；
   若真实scale相同，记录该负例不适用，不人为伪造实测。scale更新/固化时机、部分块追加是否重写旧KV、
   额外流量和缓存版本明确。P15×V8/INT16/宽乘、对齐及除法均有成本，浮点桥接单列。
4. Gemma的有效gamma/中间范围、GELU LUT/定点候选、KV局部与全局dtype分别记录，尚无整数实现的节点
   保留回退标签，不能沿用SiLU合同当作相同函数。

自然文本同模型NLL/困惑度；数学/代码使用固定GSM8K/MATH、HumanEval+/MBPP+的实际选定版本/子集，
冻结生成长度/温度/停止和判分代码。先小pilot定位明显失败，正式结论需配对95%区间和足够样本。
若现有任务尚无冻结门槛，可在看评价前采用拟议工程预算：NLL相对增加≤5%、任务准确率下降≤2百分点，
并报告阈值敏感性；这不是科学通行标准。区间不足以支持预算则inconclusive，不能凭几题通过验收。
整数oracle不一致、未处理overflow或nonfinite要求0，否则该合同失败。不同tokenizer不横排token-NLL。

### C. 实际工作负载和受控比较

通过A及适用的B门槛后，B1、长度512/2048/4096、decode32，Gemma加实际窗口邻域；8192仅显存允许时选做。
一次/分块须同模型、tokens、数值函数和精度；捕获与计时分跑，hook关闭、warmup3、重复5、CUDA同步，
记录TTFT/decode分布和峰值显存。CPU卸载与全GPU分开；OOM、NaN、慢路径、回退均归档。

输出固定token形状套件和同自然问题套件；逐层图加入RQ、bias、缩放、round/sat、pack/unpack、KV追加/状态反馈。
按实际位宽/scale元数据/物理beat记账，提供QK/PV/FFN主要shape、算子调用次数、状态生命周期和读写次数。
Block方案比较使用相同精度、数值函数、总计算库存、bank/端口、有限工作区和外部带宽；GPU吞吐只是backend
测量，未来芯片收益还需本机周期模型/RTL和Issue31物理资格，不能直接把GPU倍数当Block收益。

### D. Phi保留验证与结果交接

只有在主测三类选出的Block库、策略、精度合同/校准配方、连接预算、验收阈值及代码commit全部锁定后，
再正式跑Phi。允许按事先配方校准Phi，但不使用其评价trace/质量/性能调Block策略。失败如实报告泛化限制；
反复调到通过后不能继续称它是原来的独立保留验证。

每组交付包括：源码commit及diff/dirty、配置、模型/分词器逐文件SHA、环境/命令、冻结数据与token IDs/位置/mask、
JSON/CSV质量与性能、逐节点精度/回退、失败/OOM、少量可复查真实张量和一组代表复跑。
少量payload按GPU_CAPTURE_CONTRACT和`llm-precision-capture/1`提交，完整归约维度保留，切片注明原shape/offset。
已有接收命令为 `python -B project/experiments/integer_precision/capture.py <capture包目录> --expected-commit <生产commit> --expected-revision <模型revision>`；
只有显式符合该工具linear命名/无bias合同的包才可加`--replay-linear`，不能声称它能重放任意模型/新RQ33。
若兄方已有不同格式，保留原包和索引，另写有测试的转换器，不能改字段伪装通过。

权重和大trace使用项目约定且有权限的共享存储，Git留位置、大小、版本与SHA；无可用共享位置时保留本地、
注明哪些数据尚无法共享，不把本地保存称远端已交付。按Skill更新本人进度、Issue/有权限的看板，提交PR待审查，
不自合并/不done。交接写清已通过/失败/pending、复跑入口、需要本机方做的整合。最后请向用户报告，
由用户通知本机Codex开始核验最新仓库、PR、成果和SHA后再整合。

## 本机方的分工与接收入口

本机继续Issue39的短输入整数参考/边界记账，不启动师兄电脑或服务器、不重复大权重工作。
师兄反馈到达前，可独立核验整数oracle/协议；结果到达后的主张仍按各自原实验条件整合。
接收前先核对最新Issue/PR及交接，不因本文案已写或PR已打开就认定对方工作完成。
